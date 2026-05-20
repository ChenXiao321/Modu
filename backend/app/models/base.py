from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class TenantMixin:
    tenant_id = Column(Integer, nullable=False, index=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
