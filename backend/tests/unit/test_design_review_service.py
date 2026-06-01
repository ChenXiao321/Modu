import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.exceptions import (
    CommentNotFoundError,
    DesignDocumentNotFoundError,
    DesignDocumentNotReadyError,
    DesignReviewLockedError,
    DocumentNotFoundError,
    InvalidSectionKeyError,
    PendingCommentsExistError,
    PipelineStatusInvalidError,
    RevisionNotFoundError,
)
from app.models.base import Base
from app.models.design_document import DesignDocument
from app.models.document import Document
from app.models.parsed_requirement import ParsedRequirement
from app.models.review_comment import ReviewComment
from app.models.software_detailed_design import SoftwareDetailedDesign
from app.repositories.review_comment_repository import ReviewCommentRepository
from app.repositories.software_detailed_design_repository import SoftwareDetailedDesignRepository
from app.services.design_review_service import DesignReviewService


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


class TestDesignReviewServiceBase:
    def _create_doc(self, db_session, pipeline_status="in_design"):
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
        return doc

    def _create_design(self, db_session, doc, status="completed"):
        design = DesignDocument(
            tenant_id=1,
            document_id=doc.id,
            status=status,
            asil_level="B",
            sections={
                "overview": {
                    "content": "Original overview content",
                    "polarion_trace_id": "POL-DSGN-001",
                }
            },
        )
        db_session.add(design)
        db_session.commit()
        return design


class TestGetReviewContext(TestDesignReviewServiceBase):
    def test_get_review_context_success(self, db_session):
        doc = self._create_doc(db_session)
        self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        result = svc.get_review_context(1, doc.id)

        assert result["document_id"] == doc.id
        assert result["design_document"]["status"] == "completed"
        assert result["pipeline_status"] == "in_design"
        assert result["pending_comments_count"] == 0

    def test_get_review_context_document_not_found(self, db_session):
        svc = DesignReviewService(db_session)
        with pytest.raises(DocumentNotFoundError):
            svc.get_review_context(1, "nonexistent-id")

    def test_get_review_context_design_none(self, db_session):
        doc = self._create_doc(db_session)
        svc = DesignReviewService(db_session)
        result = svc.get_review_context(1, doc.id)
        assert result["design_document"]["status"] == "pending"
        assert result["design_document"]["asil_level"] is None
        assert result["design_document"]["sections"] is None

    def test_get_review_context_with_comments(self, db_session):
        doc = self._create_doc(db_session)
        design = self._create_design(db_session, doc)

        comment = ReviewComment(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            comment_text="建议补充",
        )
        db_session.add(comment)
        db_session.commit()

        svc = DesignReviewService(db_session)
        result = svc.get_review_context(1, doc.id)

        assert result["pending_comments_count"] == 1
        assert "overview" in result["review_comments"]
        assert len(result["review_comments"]["overview"]) == 1


class TestSaveRevision(TestDesignReviewServiceBase):
    def test_save_revision_success(self, db_session):
        doc = self._create_doc(db_session)
        design = self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        result = svc.save_revision(1, doc.id, "overview", "New content", "张三")

        assert result["section_key"] == "overview"
        assert result["original_content"] == "Original overview content"
        assert result["revised_content"] == "New content"
        assert result["author"] == "张三"

        # Verify design document updated
        db_session.refresh(design)
        assert design.sections["overview"]["content"] == "New content"

    def test_save_revision_invalid_section_key(self, db_session):
        doc = self._create_doc(db_session)
        self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        with pytest.raises(InvalidSectionKeyError):
            svc.save_revision(1, doc.id, "invalid_key", "content", "张三")

    def test_save_revision_design_not_completed(self, db_session):
        doc = self._create_doc(db_session)
        self._create_design(db_session, doc, status="running")

        svc = DesignReviewService(db_session)
        with pytest.raises(DesignDocumentNotReadyError):
            svc.save_revision(1, doc.id, "overview", "content", "张三")

    def test_save_revision_locked(self, db_session):
        doc = self._create_doc(db_session, pipeline_status="design_reviewed")
        self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        with pytest.raises(DesignReviewLockedError):
            svc.save_revision(1, doc.id, "overview", "New content", "张三")


class TestGetRevisionHistory(TestDesignReviewServiceBase):
    def test_get_revision_history_with_diff(self, db_session):
        doc = self._create_doc(db_session)
        design = self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        svc.save_revision(1, doc.id, "overview", "Revised A", "张三")
        svc.save_revision(1, doc.id, "overview", "Revised B", "李四")

        result = svc.get_revision_history(1, doc.id, "overview")

        assert result["section_key"] == "overview"
        assert len(result["revisions"]) == 2
        assert "--- original" in result["revisions"][0]["diff"]
        assert "+++ revised" in result["revisions"][0]["diff"]

    def test_get_revision_history_invalid_section(self, db_session):
        doc = self._create_doc(db_session)
        self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        with pytest.raises(InvalidSectionKeyError):
            svc.get_revision_history(1, doc.id, "bad_section")


class TestAddReviewComment(TestDesignReviewServiceBase):
    def test_add_review_comment_success(self, db_session):
        doc = self._create_doc(db_session)
        self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        result = svc.add_review_comment(1, doc.id, "overview", "建议补充", "张三")

        assert result["comment_text"] == "建议补充"
        assert result["author"] == "张三"
        assert result["resolved_at"] is None

    def test_add_review_comment_invalid_section(self, db_session):
        doc = self._create_doc(db_session)
        self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        with pytest.raises(InvalidSectionKeyError):
            svc.add_review_comment(1, doc.id, "bad", "text", "张三")

    def test_add_review_comment_locked(self, db_session):
        doc = self._create_doc(db_session, pipeline_status="design_reviewed")
        self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        with pytest.raises(DesignReviewLockedError):
            svc.add_review_comment(1, doc.id, "overview", "建议补充", "张三")


class TestResolveReviewComment(TestDesignReviewServiceBase):
    def test_resolve_success(self, db_session):
        doc = self._create_doc(db_session)
        design = self._create_design(db_session, doc)

        comment = ReviewComment(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            comment_text="建议补充",
        )
        db_session.add(comment)
        db_session.commit()

        svc = DesignReviewService(db_session)
        result = svc.resolve_review_comment(1, doc.id, comment.id, "李四")

        assert result["resolved_by"] == "李四"
        assert result["resolved_at"] is not None

    def test_resolve_not_found(self, db_session):
        doc = self._create_doc(db_session)
        self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        with pytest.raises(CommentNotFoundError):
            svc.resolve_review_comment(1, doc.id, "nonexistent", "李四")

    def test_resolve_locked(self, db_session):
        doc = self._create_doc(db_session, pipeline_status="design_reviewed")
        design = self._create_design(db_session, doc)

        comment = ReviewComment(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            comment_text="建议补充",
        )
        db_session.add(comment)
        db_session.commit()

        svc = DesignReviewService(db_session)
        with pytest.raises(DesignReviewLockedError):
            svc.resolve_review_comment(1, doc.id, comment.id, "李四")


class TestSubmitDesignReview(TestDesignReviewServiceBase):
    def test_submit_success(self, db_session):
        doc = self._create_doc(db_session, pipeline_status="in_design")
        self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        result = svc.submit_design_review(1, doc.id)

        assert result["pipeline_status"] == "design_reviewed"
        assert result["submitted_at"] is not None

    def test_submit_with_pending_comments_blocked(self, db_session):
        doc = self._create_doc(db_session, pipeline_status="in_design")
        design = self._create_design(db_session, doc)

        comment = ReviewComment(
            tenant_id=1,
            design_document_id=design.id,
            document_id=doc.id,
            section_key="overview",
            author="张三",
            comment_text="未解决的意见",
        )
        db_session.add(comment)
        db_session.commit()

        svc = DesignReviewService(db_session)
        with pytest.raises(PendingCommentsExistError) as exc_info:
            svc.submit_design_review(1, doc.id)
        assert "1" in str(exc_info.value)

    def test_submit_invalid_pipeline_status(self, db_session):
        doc = self._create_doc(db_session, pipeline_status="ready")
        self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        with pytest.raises(PipelineStatusInvalidError):
            svc.submit_design_review(1, doc.id)

    def test_submit_document_not_found(self, db_session):
        svc = DesignReviewService(db_session)
        with pytest.raises(DocumentNotFoundError):
            svc.submit_design_review(1, "nonexistent-id")

    def test_submit_updates_sdd_status(self, db_session):
        doc = self._create_doc(db_session, pipeline_status="in_design")
        self._create_design(db_session, doc)

        sdd = SoftwareDetailedDesign(
            tenant_id=1,
            document_id=doc.id,
            status="completed",
        )
        db_session.add(sdd)
        db_session.commit()

        svc = DesignReviewService(db_session)
        result = svc.submit_design_review(1, doc.id)

        assert result["pipeline_status"] == "design_reviewed"
        db_session.refresh(sdd)
        assert sdd.status == "reviewed"


class TestRollbackToRevision(TestDesignReviewServiceBase):
    def test_rollback_success(self, db_session):
        doc = self._create_doc(db_session)
        design = self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        # First save a revision
        rev = svc.save_revision(1, doc.id, "overview", "Revised content", "张三")

        # Rollback to that revision
        result = svc.rollback_to_revision(1, doc.id, rev["revision_id"], "李四")

        assert result["revised_content"] == "Original overview content"
        assert result["original_content"] == "Revised content"

        # Verify design document reverted
        db_session.refresh(design)
        assert design.sections["overview"]["content"] == "Original overview content"

    def test_rollback_not_found(self, db_session):
        doc = self._create_doc(db_session)
        self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        with pytest.raises(RevisionNotFoundError):
            svc.rollback_to_revision(1, doc.id, "nonexistent", "张三")

    def test_rollback_locked(self, db_session):
        doc = self._create_doc(db_session, pipeline_status="design_reviewed")
        design = self._create_design(db_session, doc)

        svc = DesignReviewService(db_session)
        with pytest.raises(DesignReviewLockedError):
            svc.rollback_to_revision(1, doc.id, "nonexistent", "张三")
