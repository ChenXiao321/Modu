"""Repository for FC Requirement Document persistence."""

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.fc_requirement_document import FcRequirementDocument

logger = logging.getLogger(__name__)


class FcRequirementRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        tenant_id: int,
        document_id: str,
        fc_spec: dict[str, Any],
    ) -> FcRequirementDocument:
        doc = FcRequirementDocument(
            tenant_id=tenant_id,
            document_id=document_id,
            project_number=fc_spec.get("project_number"),
            author=fc_spec.get("author"),
            version=fc_spec.get("version"),
            status=fc_spec.get("status"),
            purpose=fc_spec.get("purpose"),
            scope=fc_spec.get("scope"),
            definitions=json.dumps(fc_spec.get("definitions") or [], ensure_ascii=False),
            overview=fc_spec.get("overview"),
            functional_requirements=json.dumps(
                fc_spec.get("functional_requirements") or [], ensure_ascii=False
            ),
            non_functional_requirements=json.dumps(
                fc_spec.get("non_functional_requirements") or [], ensure_ascii=False
            ),
            notes=fc_spec.get("notes"),
            supporting_documents=json.dumps(
                fc_spec.get("supporting_documents") or [], ensure_ascii=False
            ),
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_by_document(
        self,
        document_id: str,
        tenant_id: int,
    ) -> FcRequirementDocument | None:
        return (
            self.db.query(FcRequirementDocument)
            .filter(
                FcRequirementDocument.document_id == document_id,
                FcRequirementDocument.tenant_id == tenant_id,
            )
            .first()
        )

    def delete_by_document(
        self,
        document_id: str,
        tenant_id: int,
    ) -> None:
        self.db.query(FcRequirementDocument).filter(
            FcRequirementDocument.document_id == document_id,
            FcRequirementDocument.tenant_id == tenant_id,
        ).delete(synchronize_session="fetch")
        self.db.commit()

    def to_dict(self, doc: FcRequirementDocument) -> dict[str, Any]:
        """Serialize model to dict, parsing JSON fields."""
        return {
            "id": doc.id,
            "document_id": doc.document_id,
            "project_number": doc.project_number,
            "author": doc.author,
            "version": doc.version,
            "status": doc.status,
            "purpose": doc.purpose,
            "scope": doc.scope,
            "definitions": json.loads(doc.definitions) if doc.definitions else [],
            "overview": doc.overview,
            "functional_requirements": (
                json.loads(doc.functional_requirements) if doc.functional_requirements else []
            ),
            "non_functional_requirements": (
                json.loads(doc.non_functional_requirements)
                if doc.non_functional_requirements
                else []
            ),
            "notes": doc.notes,
            "supporting_documents": (
                json.loads(doc.supporting_documents) if doc.supporting_documents else []
            ),
        }
