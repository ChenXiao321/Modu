import uuid

from sqlalchemy import BigInteger, Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, TimestampMixin


class Document(Base, TenantMixin, TimestampMixin):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    storage_path = Column(String(500), nullable=True)
    upload_status = Column(String(50), nullable=False, default="pending")
    uploaded_chunks = Column(String(500), nullable=False, default="[]")
    total_chunks = Column(Integer, nullable=False, default=0)
    sha256_checksum = Column(String(64), nullable=True)
    parse_task_id = Column(String(100), nullable=True)
