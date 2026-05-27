from sqlalchemy.orm import Session

from app.models.design_document import DesignDocument


class DesignDocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, design_doc: DesignDocument) -> DesignDocument:
        self.db.add(design_doc)
        return design_doc

    def create(self, design_doc: DesignDocument) -> DesignDocument:
        self.db.add(design_doc)
        self.db.commit()
        self.db.refresh(design_doc)
        return design_doc

    def get_by_document_id(
        self, document_id: str, tenant_id: int
    ) -> DesignDocument | None:
        return (
            self.db.query(DesignDocument)
            .filter(
                DesignDocument.document_id == document_id,
                DesignDocument.tenant_id == tenant_id,
            )
            .first()
        )

    def update_status(
        self,
        document_id: str,
        tenant_id: int,
        status: str,
        sections: dict | None = None,
        asil_level: str | None = None,
        error_message: str | None = None,
    ) -> DesignDocument | None:
        doc = self.get_by_document_id(document_id, tenant_id)
        if doc is None:
            return None
        doc.status = status
        if sections is not None:
            doc.sections = sections
        if asil_level is not None:
            doc.asil_level = asil_level
        if error_message is not None:
            doc.error_message = error_message
        self.db.commit()
        self.db.refresh(doc)
        return doc
