import uuid

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.models.base import Base, TenantMixin, TimestampMixin


class OcrExtractionResult(Base, TenantMixin, TimestampMixin):
    __tablename__ = "ocr_extraction_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), nullable=False, index=True)
    field_id = Column(String(50), nullable=False)
    extracted_text = Column(Text, nullable=False)
    normalized_value = Column(String(255), nullable=True)
    confidence = Column(Float, nullable=False)
    field_type = Column(String(50), nullable=True)
    source_page = Column(Integer, nullable=True)
    review_status = Column(String(20), nullable=False, default="pending")
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
