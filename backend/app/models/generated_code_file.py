"""Database model for generated code files."""

import uuid

from sqlalchemy import Column, ForeignKey, String, Text

from app.models.base import Base, TenantMixin, TimestampMixin


class GeneratedCodeFile(Base, TenantMixin, TimestampMixin):
    __tablename__ = "generated_code_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # "header" | "source"
    content = Column(Text, nullable=False)
    polarion_trace_id = Column(String(100), nullable=True)
    asil_level = Column(String(10), nullable=True)
