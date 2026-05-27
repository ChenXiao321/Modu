import uuid

from sqlalchemy import Column, ForeignKey, String, Text

from app.models.base import Base, TenantMixin, TimestampMixin


class DesignRevision(Base, TenantMixin, TimestampMixin):
    __tablename__ = "design_revisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    design_document_id = Column(
        String(36), ForeignKey("design_documents.id"), nullable=False, index=True
    )
    document_id = Column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    section_key = Column(String(50), nullable=False, index=True)
    author = Column(String(100), nullable=False)
    original_content = Column(Text, nullable=False)
    revised_content = Column(Text, nullable=False)
