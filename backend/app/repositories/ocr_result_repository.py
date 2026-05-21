from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ocr_extraction_result import OcrExtractionResult


class OcrResultRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, result: OcrExtractionResult) -> OcrExtractionResult:
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def get_by_document(self, document_id: str, tenant_id: int) -> list[OcrExtractionResult]:
        return (
            self.db.query(OcrExtractionResult)
            .filter(
                OcrExtractionResult.document_id == document_id,
                OcrExtractionResult.tenant_id == tenant_id,
            )
            .order_by(OcrExtractionResult.field_id)
            .all()
        )

    def get_low_confidence_count(
        self, document_id: str, tenant_id: int, threshold: float = 0.95
    ) -> int:
        return (
            self.db.query(OcrExtractionResult)
            .filter(
                OcrExtractionResult.document_id == document_id,
                OcrExtractionResult.tenant_id == tenant_id,
                OcrExtractionResult.confidence < threshold,
                OcrExtractionResult.review_status == "pending",
            )
            .count()
        )

    def get_by_field_id(
        self, document_id: str, tenant_id: int, field_id: str
    ) -> OcrExtractionResult | None:
        return (
            self.db.query(OcrExtractionResult)
            .filter(
                OcrExtractionResult.document_id == document_id,
                OcrExtractionResult.tenant_id == tenant_id,
                OcrExtractionResult.field_id == field_id,
            )
            .first()
        )

    def update_review_status(
        self,
        document_id: str,
        tenant_id: int,
        field_id: str,
        reviewer: str,
    ) -> OcrExtractionResult | None:
        from datetime import datetime, timezone

        result = self.get_by_field_id(document_id, tenant_id, field_id)
        if result is None:
            return None
        result.review_status = "confirmed"
        result.reviewed_by = reviewer
        result.reviewed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(result)
        return result

    def delete_by_document(self, document_id: str, tenant_id: int) -> int:
        count = (
            self.db.query(OcrExtractionResult)
            .filter(
                OcrExtractionResult.document_id == document_id,
                OcrExtractionResult.tenant_id == tenant_id,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return count
