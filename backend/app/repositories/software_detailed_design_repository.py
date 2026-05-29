"""Repository for SoftwareDetailedDesign persistence."""

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.software_detailed_design import SoftwareDetailedDesign

logger = logging.getLogger(__name__)


class SoftwareDetailedDesignRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        tenant_id: int,
        document_id: str,
        design_task_id: str | None = None,
    ) -> SoftwareDetailedDesign:
        doc = SoftwareDetailedDesign(
            tenant_id=tenant_id,
            document_id=document_id,
            design_task_id=design_task_id,
            status="pending",
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_by_document(
        self,
        document_id: str,
        tenant_id: int,
    ) -> SoftwareDetailedDesign | None:
        return (
            self.db.query(SoftwareDetailedDesign)
            .filter(
                SoftwareDetailedDesign.document_id == document_id,
                SoftwareDetailedDesign.tenant_id == tenant_id,
            )
            .first()
        )

    def update_status(
        self,
        document_id: str,
        tenant_id: int,
        status: str,
        design_data: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        doc = (
            self.db.query(SoftwareDetailedDesign)
            .filter(
                SoftwareDetailedDesign.document_id == document_id,
                SoftwareDetailedDesign.tenant_id == tenant_id,
            )
            .first()
        )
        if doc is None:
            logger.warning(
                "SoftwareDetailedDesign not found for document %s", document_id
            )
            return
        doc.status = status
        if error_message is not None:
            doc.error_message = error_message
        if design_data is not None:
            doc.project_number = design_data.get("project_number")
            doc.document_version = design_data.get("document_version")
            doc.overview = design_data.get("overview")
            doc.fc_architecture = json.dumps(
                design_data.get("fc_architecture") or {}, ensure_ascii=False
            )
            doc.detailed_design = json.dumps(
                design_data.get("detailed_design") or [], ensure_ascii=False
            )
            doc.safety_design = json.dumps(
                design_data.get("safety_design") or {}, ensure_ascii=False
            )
            doc.verification_strategy = json.dumps(
                design_data.get("verification_strategy") or {}, ensure_ascii=False
            )
        self.db.commit()

    def delete_by_document(
        self,
        document_id: str,
        tenant_id: int,
    ) -> None:
        self.db.query(SoftwareDetailedDesign).filter(
            SoftwareDetailedDesign.document_id == document_id,
            SoftwareDetailedDesign.tenant_id == tenant_id,
        ).delete(synchronize_session="fetch")
        self.db.commit()

    def to_dict(self, doc: SoftwareDetailedDesign) -> dict[str, Any]:
        """Serialize model to dict, parsing JSON fields."""
        return {
            "id": doc.id,
            "document_id": doc.document_id,
            "design_task_id": doc.design_task_id,
            "status": doc.status,
            "project_number": doc.project_number,
            "document_version": doc.document_version,
            "overview": doc.overview,
            "fc_architecture": (
                json.loads(doc.fc_architecture) if doc.fc_architecture else {}
            ),
            "detailed_design": (
                json.loads(doc.detailed_design) if doc.detailed_design else []
            ),
            "safety_design": (
                json.loads(doc.safety_design) if doc.safety_design else {}
            ),
            "verification_strategy": (
                json.loads(doc.verification_strategy)
                if doc.verification_strategy
                else {}
            ),
            "error_message": doc.error_message,
        }
