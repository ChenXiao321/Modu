import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.document import Document
from app.services.document_parse_service import DocumentParseService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestDocumentParseServiceSafety:
    def _create_doc(self, session, doc_id: str, status: str = "running"):
        doc = Document(
            id=doc_id,
            tenant_id=1,
            original_filename="test.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            storage_path=None,
            upload_status="completed",
            parse_status=status,
        )
        session.add(doc)
        session.commit()
        return doc

    def test_get_safety_parameters_empty(self, db_session):
        self._create_doc(db_session, "doc-1", status="completed")
        svc = DocumentParseService(db_session)
        params = svc.get_safety_parameters(1, "doc-1")
        assert params == []

    def test_persist_safety_parameters_success(self, db_session):
        self._create_doc(db_session, "doc-1", status="completed")
        svc = DocumentParseService(db_session)
        svc._persist_safety_parameters(
            1,
            "doc-1",
            [
                {
                    "parameter_id": "SW-REQ-SAF-001",
                    "name": "电压",
                    "value": "5",
                    "unit": "V",
                    "tolerance": "±0.1",
                    "chapter": "3.1",
                    "source_page": 10,
                }
            ],
        )
        params = svc.get_safety_parameters(1, "doc-1")
        assert len(params) == 1
        assert params[0]["parameter_id"] == "SW-REQ-SAF-001"
        assert params[0]["unit"] == "V"
        assert params[0]["source_page"] == 10

    def test_persist_safety_parameters_missing_required_field(self, db_session):
        svc = DocumentParseService(db_session)
        with pytest.raises(ValueError, match="缺少 parameter_id、name 或 value"):
            svc._persist_safety_parameters(
                1, "doc-1", [{"parameter_id": "SW-REQ-SAF-001", "name": "电压"}]
            )

    def test_persist_safety_parameters_id_too_long(self, db_session):
        svc = DocumentParseService(db_session)
        with pytest.raises(ValueError, match="超过最大长度"):
            svc._persist_safety_parameters(
                1,
                "doc-1",
                [
                    {
                        "parameter_id": "SW-REQ-SAF-" + "X" * 100,
                        "name": "电压",
                        "value": "5",
                    }
                ],
            )

    def test_persist_safety_parameters_zero_value(self, db_session):
        """H-2: value=0 should be accepted, not rejected by 'not 0' check."""
        self._create_doc(db_session, "doc-1", status="completed")
        svc = DocumentParseService(db_session)
        svc._persist_safety_parameters(
            1,
            "doc-1",
            [
                {
                    "parameter_id": "SW-REQ-SAF-001",
                    "name": "基准电压",
                    "value": 0,
                    "unit": "V",
                }
            ],
        )
        params = svc.get_safety_parameters(1, "doc-1")
        assert len(params) == 1
        assert params[0]["value"] == "0"

    def test_persist_safety_parameters_source_page_string(self, db_session):
        """H-1: source_page as string '42' should be converted to int 42."""
        self._create_doc(db_session, "doc-1", status="completed")
        svc = DocumentParseService(db_session)
        svc._persist_safety_parameters(
            1,
            "doc-1",
            [
                {
                    "parameter_id": "SW-REQ-SAF-001",
                    "name": "电压",
                    "value": "5",
                    "source_page": "42",
                }
            ],
        )
        params = svc.get_safety_parameters(1, "doc-1")
        assert params[0]["source_page"] == 42

    def test_persist_safety_parameters_source_page_invalid_string(self, db_session):
        """H-1: invalid source_page string should be coerced to None."""
        self._create_doc(db_session, "doc-1", status="completed")
        svc = DocumentParseService(db_session)
        svc._persist_safety_parameters(
            1,
            "doc-1",
            [
                {
                    "parameter_id": "SW-REQ-SAF-001",
                    "name": "电压",
                    "value": "5",
                    "source_page": "N/A",
                }
            ],
        )
        params = svc.get_safety_parameters(1, "doc-1")
        assert params[0]["source_page"] is None

    def test_get_safety_parameters_document_not_found(self, db_session):
        """M-1: should raise DocumentNotFoundError when document does not exist."""
        svc = DocumentParseService(db_session)
        from app.exceptions import DocumentNotFoundError
        with pytest.raises(DocumentNotFoundError):
            svc.get_safety_parameters(1, "nonexistent")

    def test_execute_parse_survives_safety_parameter_failure(self, db_session):
        """M-2: safety parameter extraction failure should not fail the whole parse."""
        doc = Document(
            id="doc-1",
            tenant_id=1,
            original_filename="test.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            storage_path="/tmp/test.pdf",
            upload_status="completed",
            parse_status="running",
        )
        db_session.add(doc)
        db_session.commit()
        from unittest.mock import patch
        svc = DocumentParseService(db_session)
        with patch.object(svc, "llm_client") as mock_llm:
            mock_llm.extract_requirements.return_value = []
            mock_llm.extract_safety_parameters.side_effect = RuntimeError("LLM error")
            with patch("app.services.document_parse_service.TextExtractor.extract", return_value="x"):
                svc.execute_parse(1, "doc-1")
        # Parse should complete despite safety parameter failure
        db_session.refresh(doc)
        assert doc.parse_status == "completed"

    def test_execute_parse_preserves_old_safety_params_on_failure(self, db_session):
        """M-2: old safety parameters should be preserved when re-parse fails."""
        doc = Document(
            id="doc-1",
            tenant_id=1,
            original_filename="test.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            storage_path="/tmp/test.pdf",
            upload_status="completed",
            parse_status="running",
        )
        db_session.add(doc)
        db_session.commit()

        # Pre-populate an old safety parameter
        from app.models.safety_critical_parameter import SafetyCriticalParameter
        old_param = SafetyCriticalParameter(
            tenant_id=1,
            document_id="doc-1",
            parameter_id="SW-REQ-SAF-OLD",
            name="旧参数",
            value="99",
        )
        db_session.add(old_param)
        db_session.commit()

        from unittest.mock import patch
        svc = DocumentParseService(db_session)
        with patch.object(svc, "llm_client") as mock_llm:
            mock_llm.extract_requirements.return_value = []
            mock_llm.extract_safety_parameters.side_effect = RuntimeError("LLM error")
            with patch("app.services.document_parse_service.TextExtractor.extract", return_value="x"):
                svc.execute_parse(1, "doc-1")

        db_session.refresh(doc)
        assert doc.parse_status == "completed"
        # Old parameter should still exist
        params = svc.get_safety_parameters(1, "doc-1")
        assert len(params) == 1
        assert params[0]["parameter_id"] == "SW-REQ-SAF-OLD"

    def test_execute_parse_survives_safety_parameter_none(self, db_session):
        """H-1: extract_safety_parameters returning None should not crash."""
        doc = Document(
            id="doc-1",
            tenant_id=1,
            original_filename="test.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            storage_path="/tmp/test.pdf",
            upload_status="completed",
            parse_status="running",
        )
        db_session.add(doc)
        db_session.commit()
        from unittest.mock import patch
        svc = DocumentParseService(db_session)
        with patch.object(svc, "llm_client") as mock_llm:
            mock_llm.extract_requirements.return_value = []
            mock_llm.extract_safety_parameters.return_value = None
            with patch("app.services.document_parse_service.TextExtractor.extract", return_value="x"):
                svc.execute_parse(1, "doc-1")
        db_session.refresh(doc)
        assert doc.parse_status == "completed"

    def test_get_safety_parameters_pending_status(self, db_session):
        """M-3: should return empty list when parse_status is not completed/running."""
        self._create_doc(db_session, "doc-1", status="pending")
        svc = DocumentParseService(db_session)
        params = svc.get_safety_parameters(1, "doc-1")
        assert params == []

    def test_get_safety_parameters_failed_status(self, db_session):
        """M-3: should return empty list when parse_status is failed."""
        self._create_doc(db_session, "doc-1", status="failed")
        svc = DocumentParseService(db_session)
        params = svc.get_safety_parameters(1, "doc-1")
        assert params == []

    def test_get_safety_parameters_running_status(self, db_session):
        """M-3: should return data when parse_status is running."""
        self._create_doc(db_session, "doc-1", status="running")
        svc = DocumentParseService(db_session)
        from app.models.safety_critical_parameter import SafetyCriticalParameter
        db_session.add(
            SafetyCriticalParameter(
                tenant_id=1,
                document_id="doc-1",
                parameter_id="SW-REQ-SAF-001",
                name="电压",
                value="5",
            )
        )
        db_session.commit()
        params = svc.get_safety_parameters(1, "doc-1")
        assert len(params) == 1

    def test_mock_llm_empty_doc_returns_zero_params(self, db_session):
        """M-1: MockLLMClient should return 0 params for empty document text."""
        from app.integrations.llm_client import MockLLMClient
        client = MockLLMClient()
        params = client.extract_safety_parameters("", "empty.pdf")
        assert params == []
