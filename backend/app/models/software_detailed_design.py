"""Database model for Software Detailed Design document."""

import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.models.base import Base, TenantMixin, TimestampMixin


class SoftwareDetailedDesign(Base, TenantMixin, TimestampMixin):
    __tablename__ = "software_detailed_designs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    design_task_id = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    project_number = Column(String(100), nullable=True)
    document_version = Column(String(20), nullable=True)
    overview = Column(Text, nullable=True)
    fc_architecture = Column(Text, nullable=False, default="{}")
    detailed_design = Column(Text, nullable=False, default="[]")
    safety_design = Column(Text, nullable=False, default="{}")
    verification_strategy = Column(Text, nullable=False, default="{}")
    error_message = Column(Text, nullable=True)
