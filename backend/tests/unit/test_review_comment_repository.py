import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.design_document import DesignDocument
from app.models.document import Document
from app.models.review_comment import ReviewComment
from app.repositories.review_comment_repository import ReviewCommentRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestReviewCommentRepository:
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
                    "content": "Overview",
                    "polarion_trace_id": "POL-DSGN-001",
                }
            },
        )
        db_session.add(design)
        db_session.commit()
        return doc, design

    def test_create_and_get_by_id(self, db_session):
        doc, design = self._create_doc_and_design(db_session)
        repo = ReviewCommentRepository(db_session)

        comment = ReviewComment(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            comment_text="建议补充时序图",
        )
        created = repo.create(comment)

        assert created.id is not None
        assert created.resolved_at is None

        fetched = repo.get_by_id(created.id, 1)
        assert fetched is not None
        assert fetched.comment_text == "建议补充时序图"

    def test_list_by_section(self, db_session):
        doc, design = self._create_doc_and_design(db_session)
        repo = ReviewCommentRepository(db_session)

        c1 = ReviewComment(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            comment_text="Comment A",
        )
        c2 = ReviewComment(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="李四",
            comment_text="Comment B",
        )
        c3 = ReviewComment(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="test_strategy",
            author="王五",
            comment_text="Comment C",
        )
        db_session.add_all([c1, c2, c3])
        db_session.commit()

        results = repo.list_by_section(doc.id, 1, "overview")
        assert len(results) == 2

    def test_list_by_document(self, db_session):
        doc, design = self._create_doc_and_design(db_session)
        repo = ReviewCommentRepository(db_session)

        c1 = ReviewComment(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            comment_text="Comment A",
        )
        db_session.add(c1)
        db_session.commit()

        results = repo.list_by_document(doc.id, 1)
        assert len(results) == 1
        assert results[0].comment_text == "Comment A"

    def test_resolve(self, db_session):
        doc, design = self._create_doc_and_design(db_session)
        repo = ReviewCommentRepository(db_session)

        comment = ReviewComment(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            comment_text="建议补充时序图",
        )
        repo.create(comment)

        comment.resolved_by = "李四"
        resolved = repo.resolve(comment)
        db_session.commit()
        db_session.refresh(resolved)
        assert resolved is not None
        assert resolved.resolved_at is not None
        assert resolved.resolved_by == "李四"

    def test_get_by_id_and_document(self, db_session):
        doc, design = self._create_doc_and_design(db_session)
        repo = ReviewCommentRepository(db_session)

        comment = ReviewComment(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            comment_text="建议补充时序图",
        )
        repo.create(comment)

        found = repo.get_by_id_and_document(comment.id, doc.id, 1)
        assert found is not None
        assert found.comment_text == "建议补充时序图"

        not_found = repo.get_by_id_and_document(comment.id, "other-doc", 1)
        assert not_found is None
