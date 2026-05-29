"""Database model for FC Requirement Specification document."""

import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.models.base import Base, TenantMixin, TimestampMixin


class FcRequirementDocument(Base, TenantMixin, TimestampMixin):
    __tablename__ = "fc_requirement_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    project_number = Column(String(100), nullable=True)
    author = Column(String(100), nullable=True)
    version = Column(String(20), nullable=True)
    status = Column(String(50), nullable=True)
    purpose = Column(Text, nullable=True)
    scope = Column(Text, nullable=True)
    definitions = Column(Text, nullable=False, default="[]")
    overview = Column(Text, nullable=True)
    functional_requirements = Column(Text, nullable=False, default="[]")
    non_functional_requirements = Column(Text, nullable=False, default="[]")
    notes = Column(Text, nullable=True)
    supporting_documents = Column(Text, nullable=False, default="[]")
