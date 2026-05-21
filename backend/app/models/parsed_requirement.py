import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class ParsedRequirement(Base, TenantMixin, TimestampMixin):
    __tablename__ = "parsed_requirements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    requirement_id = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    chapter = Column(String(100), nullable=True)
    asil_level = Column(String(10), nullable=True)
    parent_requirement_id = Column(
        String(36), ForeignKey("parsed_requirements.id"), nullable=True, index=True
    )

    document = relationship("Document", backref="requirements")
    children = relationship(
        "ParsedRequirement",
        backref="parent",
        remote_side=[id],
        lazy="selectin",
    )
