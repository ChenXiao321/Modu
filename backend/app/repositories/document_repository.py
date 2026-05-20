import json
from typing import List

from sqlalchemy.orm import Session

from app.models.document import Document


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, document: Document) -> Document:
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def get_by_id(self, document_id: str, tenant_id: int) -> Document | None:
        return (
            self.db.query(Document)
            .filter(Document.id == document_id, Document.tenant_id == tenant_id)
            .first()
        )

    def update_uploaded_chunks(
        self, document_id: str, tenant_id: int, chunk_index: int
    ) -> Document | None:
        doc = self.get_by_id(document_id, tenant_id)
        if doc is None:
            return None
        chunks: List[int] = json.loads(doc.uploaded_chunks or "[]")
        if chunk_index not in chunks:
            chunks.append(chunk_index)
            doc.uploaded_chunks = json.dumps(chunks)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def update_status(
        self, document_id: str, tenant_id: int, status: str, storage_path: str | None = None
    ) -> Document | None:
        doc = self.get_by_id(document_id, tenant_id)
        if doc is None:
            return None
        doc.upload_status = status
        if storage_path is not None:
            doc.storage_path = storage_path
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def update_checksum(
        self, document_id: str, tenant_id: int, sha256: str
    ) -> Document | None:
        doc = self.get_by_id(document_id, tenant_id)
        if doc is None:
            return None
        doc.sha256_checksum = sha256
        self.db.commit()
        self.db.refresh(doc)
        return doc
