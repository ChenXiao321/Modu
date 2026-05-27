from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.review_comment import ReviewComment


class ReviewCommentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, comment: ReviewComment) -> ReviewComment:
        self.db.add(comment)
        return comment

    def create(self, comment: ReviewComment) -> ReviewComment:
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def list_by_section(
        self, document_id: str, tenant_id: int, section_key: str, limit: int | None = None
    ) -> list[ReviewComment]:
        q = (
            self.db.query(ReviewComment)
            .filter(
                ReviewComment.document_id == document_id,
                ReviewComment.tenant_id == tenant_id,
                ReviewComment.section_key == section_key,
            )
            .order_by(ReviewComment.created_at.desc(), ReviewComment.id.desc())
        )
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    def list_by_document(
        self, document_id: str, tenant_id: int, limit: int | None = None
    ) -> list[ReviewComment]:
        q = (
            self.db.query(ReviewComment)
            .filter(
                ReviewComment.document_id == document_id,
                ReviewComment.tenant_id == tenant_id,
            )
            .order_by(ReviewComment.created_at.desc(), ReviewComment.id.desc())
        )
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    def get_by_id(
        self, comment_id: str, tenant_id: int
    ) -> ReviewComment | None:
        return (
            self.db.query(ReviewComment)
            .filter(
                ReviewComment.id == comment_id,
                ReviewComment.tenant_id == tenant_id,
            )
            .first()
        )

    def get_by_id_and_document(
        self, comment_id: str, document_id: str, tenant_id: int
    ) -> ReviewComment | None:
        return (
            self.db.query(ReviewComment)
            .filter(
                ReviewComment.id == comment_id,
                ReviewComment.document_id == document_id,
                ReviewComment.tenant_id == tenant_id,
            )
            .first()
        )

    def resolve(
        self, comment: ReviewComment
    ) -> ReviewComment:
        comment.resolved_at = datetime.now(timezone.utc)
        return comment
