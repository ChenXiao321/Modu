"""Repository for GeneratedCodeFile persistence."""

import logging

from sqlalchemy.orm import Session

from app.models.generated_code_file import GeneratedCodeFile

logger = logging.getLogger(__name__)


class GeneratedCodeFileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        tenant_id: int,
        document_id: str,
        file_path: str,
        file_type: str,
        content: str,
        polarion_trace_id: str | None = None,
        asil_level: str | None = None,
    ) -> GeneratedCodeFile:
        record = GeneratedCodeFile(
            tenant_id=tenant_id,
            document_id=document_id,
            file_path=file_path,
            file_type=file_type,
            content=content,
            polarion_trace_id=polarion_trace_id,
            asil_level=asil_level,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_by_document(
        self,
        document_id: str,
        tenant_id: int,
    ) -> list[GeneratedCodeFile]:
        return (
            self.db.query(GeneratedCodeFile)
            .filter(
                GeneratedCodeFile.document_id == document_id,
                GeneratedCodeFile.tenant_id == tenant_id,
            )
            .order_by(GeneratedCodeFile.file_path.asc())
            .all()
        )

    def get_by_id(
        self,
        file_id: str,
        tenant_id: int,
    ) -> GeneratedCodeFile | None:
        return (
            self.db.query(GeneratedCodeFile)
            .filter(
                GeneratedCodeFile.id == file_id,
                GeneratedCodeFile.tenant_id == tenant_id,
            )
            .first()
        )

    def delete_by_document(
        self,
        document_id: str,
        tenant_id: int,
    ) -> None:
        self.db.query(GeneratedCodeFile).filter(
            GeneratedCodeFile.document_id == document_id,
            GeneratedCodeFile.tenant_id == tenant_id,
        ).delete(synchronize_session="fetch")
        self.db.commit()
