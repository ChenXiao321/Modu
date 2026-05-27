import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.design_document import DesignDocument
from app.models.design_revision import DesignRevision
from app.models.document import Document
from app.repositories.design_revision_repository import DesignRevisionRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestDesignRevisionRepository:
    def _create_doc_and_design(self, db_session, pipeline_status="ready"):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="completed",
            pipeline_status=pipeline_status,
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        db_session.add(doc)
        db_session.commit()

        design = DesignDocument(
            tenant_id=1,
            document_id=doc.id,
            status="completed",
            sections={
                "overview": {
                    "content": "Original overview",
                    "polarion_trace_id": "POL-DSGN-001",
                }
            },
        )
        db_session.add(design)
        db_session.commit()
        return doc, design

    def test_create_and_get_by_id(self, db_session):
        doc, design = self._create_doc_and_design(db_session)
        repo = DesignRevisionRepository(db_session)

        revision = DesignRevision(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            original_content="Original overview",
            revised_content="Revised overview",
        )
        created = repo.create(revision)

        assert created.id is not None
        assert created.document_id == doc.id
        assert created.section_key == "overview"

        fetched = repo.get_by_id(created.id, 1)
        assert fetched is not None
        assert fetched.original_content == "Original overview"
        assert fetched.revised_content == "Revised overview"

    def test_list_by_section(self, db_session):
        doc, design = self._create_doc_and_design(db_session)
        repo = DesignRevisionRepository(db_session)

        r1 = DesignRevision(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            original_content="A",
            revised_content="B",
        )
        r2 = DesignRevision(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="李四",
            original_content="B",
            revised_content="C",
        )
        r3 = DesignRevision(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="test_strategy",
            author="王五",
            original_content="X",
            revised_content="Y",
        )
        db_session.add_all([r1, r2, r3])
        db_session.commit()

        results = repo.list_by_section(doc.id, 1, "overview")
        assert len(results) == 2
        # Ordered by created_at desc
        assert results[0].revised_content == "C"
        assert results[1].revised_content == "B"

    def test_list_by_section_returns_empty_for_wrong_tenant(self, db_session):
        doc, design = self._create_doc_and_design(db_session)
        repo = DesignRevisionRepository(db_session)

        revision = DesignRevision(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            original_content="A",
            revised_content="B",
        )
        repo.create(revision)

        results = repo.list_by_section(doc.id, 999, "overview")
        assert results == []

    def test_get_latest_by_section(self, db_session):
        doc, design = self._create_doc_and_design(db_session)
        repo = DesignRevisionRepository(db_session)

        r1 = DesignRevision(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            original_content="A",
            revised_content="B",
        )
        r2 = DesignRevision(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="李四",
            original_content="B",
            revised_content="C",
        )
        db_session.add_all([r1, r2])
        db_session.commit()

        latest = repo.get_latest_by_section(doc.id, 1, "overview")
        assert latest is not None
        assert latest.author == "李四"
        assert latest.revised_content == "C"
