import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class SafetyCriticalParameter(Base, TenantMixin, TimestampMixin):
    __tablename__ = "safety_critical_parameters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    parameter_id = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    value = Column(String(100), nullable=False)
    unit = Column(String(50), nullable=True)
    tolerance = Column(String(100), nullable=True)
    chapter = Column(String(100), nullable=True)
    source_page = Column(Integer, nullable=True)

    document = relationship("Document", backref="safety_parameters")
