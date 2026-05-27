from sqlalchemy.orm import Session

from app.models.design_revision import DesignRevision


class DesignRevisionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, revision: DesignRevision) -> DesignRevision:
        self.db.add(revision)
        return revision

    def create(self, revision: DesignRevision) -> DesignRevision:
        self.db.add(revision)
        self.db.commit()
        self.db.refresh(revision)
        return revision

    def list_by_section(
        self, document_id: str, tenant_id: int, section_key: str, limit: int | None = None
    ) -> list[DesignRevision]:
        q = (
            self.db.query(DesignRevision)
            .filter(
                DesignRevision.document_id == document_id,
                DesignRevision.tenant_id == tenant_id,
                DesignRevision.section_key == section_key,
            )
            .order_by(DesignRevision.created_at.desc(), DesignRevision.id.desc())
        )
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    def get_latest_by_section(
        self, document_id: str, tenant_id: int, section_key: str
    ) -> DesignRevision | None:
        return (
            self.db.query(DesignRevision)
            .filter(
                DesignRevision.document_id == document_id,
                DesignRevision.tenant_id == tenant_id,
                DesignRevision.section_key == section_key,
            )
            .order_by(DesignRevision.created_at.desc(), DesignRevision.id.desc())
            .first()
        )

    def get_by_id(
        self, revision_id: str, tenant_id: int
    ) -> DesignRevision | None:
        return (
            self.db.query(DesignRevision)
            .filter(
                DesignRevision.id == revision_id,
                DesignRevision.tenant_id == tenant_id,
            )
            .first()
        )

    def get_by_id_and_document(
        self, revision_id: str, document_id: str, tenant_id: int
    ) -> DesignRevision | None:
        return (
            self.db.query(DesignRevision)
            .filter(
                DesignRevision.id == revision_id,
                DesignRevision.document_id == document_id,
                DesignRevision.tenant_id == tenant_id,
            )
            .first()
        )
