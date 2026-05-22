import uuid

from sqlalchemy import Column, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class DesignDocument(Base, TenantMixin, TimestampMixin):
    __tablename__ = "design_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    status = Column(String(20), nullable=False, default="pending")
    asil_level = Column(String(10), nullable=True)
    sections = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    document = relationship("Document", backref="design_document", uselist=False)
