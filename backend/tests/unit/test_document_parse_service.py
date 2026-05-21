import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.document import Document
from app.services.document_parse_service import DocumentParseService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestTriggerParse:
    def test_trigger_parse_success(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type=".pdf",
            file_size_bytes=100,
            upload_status="completed",
            total_chunks=1,
            uploaded_chunks="[0]",
            storage_path="/tmp/test.pdf",
        )
        db_session.add(doc)
        db_session.commit()

        svc = DocumentParseService(db_session)
        result = svc.trigger_parse(1, doc.id)

        assert result["document_id"] == doc.id
        assert result["status"] == "queued"
        assert result["parse_task_id"] is not None

    def test_trigger_parse_document_not_found(self, db_session):
        svc = DocumentParseService(db_session)
        from app.exceptions import DocumentNotFoundError
        with pytest.raises(DocumentNotFoundError):
            svc.trigger_parse(1, "nonexistent-id")

    def test_trigger_parse_not_completed(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type=".pdf",
            file_size_bytes=100,
            upload_status="uploading",
            total_chunks=2,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        svc = DocumentParseService(db_session)
        from app.exceptions import DocumentNotReadyError
        with pytest.raises(DocumentNotReadyError):
            svc.trigger_parse(1, doc.id)


class TestGetParseStatus:
    def test_status_completed(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type=".pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="completed",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        svc = DocumentParseService(db_session)
        result = svc.get_parse_status(1, doc.id)

        assert result["status"] == "completed"
        assert result["progress_percent"] == 100

    def test_status_pending(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type=".pdf",
            file_size_bytes=100,
            upload_status="completed",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        svc = DocumentParseService(db_session)
        result = svc.get_parse_status(1, doc.id)

        assert result["status"] == "pending"

    def test_status_running(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type=".pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="running",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        svc = DocumentParseService(db_session)
        result = svc.get_parse_status(1, doc.id)

        assert result["status"] == "running"
        assert result["progress_percent"] == 50


class TestExecuteParse:
    def test_execute_parse_mock_llm(self, db_session):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("System shall initialize registers.")
            tmp_path = f.name

        try:
            doc = Document(
                tenant_id=1,
                original_filename="test.txt",
                file_type=".txt",
                file_size_bytes=100,
                upload_status="completed",
                parse_status="running",
                total_chunks=1,
                uploaded_chunks="[0]",
                storage_path=tmp_path,
            )
            db_session.add(doc)
            db_session.commit()

            svc = DocumentParseService(db_session)
            svc.execute_parse(1, doc.id)

            reqs = svc.get_requirements_tree(1, doc.id)
            assert len(reqs) > 0
            assert reqs[0]["requirement_id"].startswith("SW-REQ-")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_execute_parse_missing_file(self, db_session):
        doc = Document(
            tenant_id=1,
            original_filename="missing.txt",
            file_type=".txt",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="running",
            total_chunks=1,
            uploaded_chunks="[0]",
            storage_path="/nonexistent/path.txt",
        )
        db_session.add(doc)
        db_session.commit()

        svc = DocumentParseService(db_session)
        svc.execute_parse(1, doc.id)

        db_session.refresh(doc)
        assert doc.parse_status == "failed"

    def test_execute_parse_rejects_duplicate_run(self, db_session):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Some text.")
            tmp_path = f.name

        try:
            doc = Document(
                tenant_id=1,
                original_filename="test.txt",
                file_type=".txt",
                file_size_bytes=100,
                upload_status="completed",
                parse_status="completed",
                total_chunks=1,
                uploaded_chunks="[0]",
                storage_path=tmp_path,
            )
            db_session.add(doc)
            db_session.commit()

            svc = DocumentParseService(db_session)
            # Should silently return because parse_status is already completed
            svc.execute_parse(1, doc.id)

            db_session.refresh(doc)
            assert doc.parse_status == "completed"
        finally:
            Path(tmp_path).unlink(missing_ok=True)
