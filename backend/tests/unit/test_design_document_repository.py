import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.design_document import DesignDocument
from app.repositories.design_document_repository import DesignDocumentRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestDesignDocumentRepository:
    def test_create_and_get_by_document_id(self, db_session):
        repo = DesignDocumentRepository(db_session)
        design = DesignDocument(
            tenant_id=1,
            document_id="doc-1",
            status="pending",
            asil_level="B",
            sections={
                "overview": {
                    "content": "Test overview",
                    "polarion_trace_id": "POL-DSGN-001",
                }
            },
        )
        created = repo.create(design)
        assert created.id is not None
        assert created.document_id == "doc-1"
        assert created.status == "pending"

        fetched = repo.get_by_document_id("doc-1", 1)
        assert fetched is not None
        assert fetched.asil_level == "B"
        assert fetched.sections["overview"]["content"] == "Test overview"

    def test_update_status(self, db_session):
        repo = DesignDocumentRepository(db_session)
        repo.create(
            DesignDocument(
                tenant_id=1,
                document_id="doc-2",
                status="running",
            )
        )

        updated = repo.update_status(
            "doc-2",
            1,
            "completed",
            sections={
                "test_strategy": {
                    "content": "Test strategy content",
                    "polarion_trace_id": "POL-DSGN-008",
                }
            },
            asil_level="C",
        )
        assert updated is not None
        assert updated.status == "completed"
        assert updated.asil_level == "C"
        assert updated.sections["test_strategy"]["polarion_trace_id"] == "POL-DSGN-008"

    def test_get_by_document_id_not_found(self, db_session):
        repo = DesignDocumentRepository(db_session)
        result = repo.get_by_document_id("nonexistent", 1)
        assert result is None

    def test_update_status_not_found(self, db_session):
        repo = DesignDocumentRepository(db_session)
        result = repo.update_status("nonexistent", 1, "failed")
        assert result is None

    def test_update_status_with_error_message(self, db_session):
        repo = DesignDocumentRepository(db_session)
        repo.create(
            DesignDocument(
                tenant_id=1,
                document_id="doc-3",
                status="running",
            )
        )

        updated = repo.update_status(
            "doc-3", 1, "failed", error_message="LLM API timeout"
        )
        assert updated is not None
        assert updated.status == "failed"
        assert updated.error_message == "LLM API timeout"
