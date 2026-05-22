import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.exceptions import DocumentNotFoundError, DocumentNotReadyError, PipelineBlockedError
from app.models.base import Base
from app.models.design_document import DesignDocument
from app.models.document import Document
from app.models.parsed_requirement import ParsedRequirement
from app.models.safety_critical_parameter import SafetyCriticalParameter
from app.repositories.design_document_repository import DesignDocumentRepository
from app.services.design_document_service import DesignDocumentService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestTriggerGenerate:
    def test_trigger_generate_success(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="completed",
            pipeline_status="ready",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        svc = DesignDocumentService(db_session)
        result = svc.trigger_generate(1, doc.id)

        assert result["document_id"] == doc.id
        assert result["status"] == "running"
        assert result["design_task_id"] is not None

        # Verify DB record created
        design = DesignDocumentRepository(db_session).get_by_document_id(doc.id, 1)
        assert design is not None
        assert design.status == "running"

    def test_trigger_generate_document_not_found(self, db_session):
        svc = DesignDocumentService(db_session)
        with pytest.raises(DocumentNotFoundError):
            svc.trigger_generate(1, "nonexistent-id")

    def test_trigger_generate_parse_not_completed(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="pending",
            pipeline_status="ready",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        svc = DesignDocumentService(db_session)
        with pytest.raises(DocumentNotReadyError) as exc_info:
            svc.trigger_generate(1, doc.id)
        assert "解析尚未完成" in str(exc_info.value)

    def test_trigger_generate_parse_failed(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="failed",
            pipeline_status="ready",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        svc = DesignDocumentService(db_session)
        with pytest.raises(DocumentNotReadyError) as exc_info:
            svc.trigger_generate(1, doc.id)
        assert "解析失败" in str(exc_info.value)

    def test_trigger_generate_pipeline_blocked(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="completed",
            pipeline_status="blocked",
            block_reason="存在 2 个低置信度 OCR 字段未复核",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        svc = DesignDocumentService(db_session)
        with pytest.raises(PipelineBlockedError) as exc_info:
            svc.trigger_generate(1, doc.id)
        assert "阻塞" in exc_info.value.message

    def test_trigger_generate_already_running(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="completed",
            pipeline_status="ready",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        design = DesignDocument(
            tenant_id=1,
            document_id=doc.id,
            status="running",
        )
        db_session.add(design)
        db_session.commit()

        svc = DesignDocumentService(db_session)
        with pytest.raises(DocumentNotReadyError) as exc_info:
            svc.trigger_generate(1, doc.id)
        assert "已在进行中" in str(exc_info.value)


class TestExecuteGenerate:
    def test_execute_generate_success(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="completed",
            pipeline_status="ready",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        # Seed requirements with ASIL level
        req = ParsedRequirement(
            tenant_id=1,
            document_id=doc.id,
            requirement_id="SW-REQ-001",
            description="System shall monitor voltage.",
            chapter="3.1",
            asil_level="C",
        )
        db_session.add(req)
        db_session.commit()

        design = DesignDocument(
            tenant_id=1,
            document_id=doc.id,
            status="running",
        )
        db_session.add(design)
        db_session.commit()

        svc = DesignDocumentService(db_session)
        svc.execute_generate(1, doc.id)

        # Refresh from DB
        db_session.refresh(design)
        db_session.refresh(doc)

        assert design.status == "completed"
        assert design.asil_level == "C"
        assert design.sections is not None
        assert "overview" in design.sections
        assert "polarion_trace_id" in design.sections["overview"]
        assert doc.pipeline_status == "in_design"

    def test_execute_generate_document_not_found(self, db_session):
        svc = DesignDocumentService(db_session)
        # Should not raise, just log warning and return
        svc.execute_generate(1, "nonexistent-id")

        # Nothing persisted
        assert DesignDocumentRepository(db_session).get_by_document_id("nonexistent-id", 1) is None

    def test_execute_generate_parse_not_completed(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="pending",
            pipeline_status="ready",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        design = DesignDocument(
            tenant_id=1,
            document_id=doc.id,
            status="running",
        )
        db_session.add(design)
        db_session.commit()

        svc = DesignDocumentService(db_session)
        svc.execute_generate(1, doc.id)

        db_session.refresh(design)
        assert design.status == "failed"
        assert "解析尚未完成" in (design.error_message or "")

    def test_execute_generate_pipeline_blocked(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="completed",
            pipeline_status="blocked",
            block_reason="OCR 低置信度",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        design = DesignDocument(
            tenant_id=1,
            document_id=doc.id,
            status="running",
        )
        db_session.add(design)
        db_session.commit()

        svc = DesignDocumentService(db_session)
        svc.execute_generate(1, doc.id)

        db_session.refresh(design)
        assert design.status == "failed"
        assert "阻塞" in (design.error_message or "")


class TestGetDesignDocument:
    def test_get_design_document_pending(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="completed",
            pipeline_status="ready",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        svc = DesignDocumentService(db_session)
        result = svc.get_design_document(1, doc.id)

        assert result["document_id"] == doc.id
        assert result["status"] == "pending"
        assert result["sections"] is None

    def test_get_design_document_completed(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="completed",
            pipeline_status="in_design",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        design = DesignDocument(
            tenant_id=1,
            document_id=doc.id,
            status="completed",
            asil_level="B",
            sections={
                "overview": {
                    "content": "Overview content",
                    "polarion_trace_id": "POL-DSGN-001",
                }
            },
        )
        db_session.add(design)
        db_session.commit()

        svc = DesignDocumentService(db_session)
        result = svc.get_design_document(1, doc.id)

        assert result["status"] == "completed"
        assert result["asil_level"] == "B"
        assert result["sections"]["overview"]["content"] == "Overview content"

    def test_get_design_document_not_found(self, db_session):
        svc = DesignDocumentService(db_session)
        with pytest.raises(DocumentNotFoundError):
            svc.get_design_document(1, "nonexistent-id")


class TestResolveAsilLevel:
    def test_resolve_asil_level_from_requirements(self, db_session):
        svc = DesignDocumentService(db_session)
        requirements = [
            {
                "requirement_id": "R1",
                "description": "Desc",
                "asil_level": "A",
                "children": [
                    {
                        "requirement_id": "R1-1",
                        "description": "Child",
                        "asil_level": "D",
                        "children": [],
                    }
                ],
            }
        ]
        assert svc._resolve_asil_level(requirements) == "D"

    def test_resolve_asil_level_defaults_to_none(self, db_session):
        svc = DesignDocumentService(db_session)
        requirements = [
            {
                "requirement_id": "R1",
                "description": "Desc",
                "asil_level": None,
                "children": [],
            }
        ]
        assert svc._resolve_asil_level(requirements) is None
