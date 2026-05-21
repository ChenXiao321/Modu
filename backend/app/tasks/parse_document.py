import logging

from fastapi import BackgroundTasks

from app.models.base import SessionLocal
from app.repositories.document_repository import DocumentRepository
from app.services.document_parse_service import DocumentParseService

logger = logging.getLogger(__name__)


def schedule_parse(background_tasks: BackgroundTasks, tenant_id: int, document_id: str) -> None:
    """Schedule document parsing as a background task."""
    background_tasks.add_task(_run_parse, tenant_id, document_id)


def _run_parse(tenant_id: int, document_id: str) -> None:
    db = SessionLocal()
    try:
        # Re-verify document exists and belongs to tenant before parsing
        doc_repo = DocumentRepository(db)
        doc = doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            logger.warning(
                "Background parse skipped: document %s not found for tenant %s",
                document_id,
                tenant_id,
            )
            return
        if doc.parse_status != "running":
            logger.warning(
                "Background parse skipped: document %s parse_status=%s (expected running)",
                document_id,
                doc.parse_status,
            )
            return
        if doc.upload_status != "completed":
            logger.warning(
                "Background parse skipped: document %s upload_status=%s (expected completed)",
                document_id,
                doc.upload_status,
            )
            doc_repo.update_parse_status(document_id, tenant_id, "failed")
            return

        service = DocumentParseService(db)
        service.execute_parse(tenant_id, document_id)
    except Exception:
        logger.exception("Background parse crashed for document %s", document_id)
        try:
            doc_repo = DocumentRepository(db)
            doc_repo.update_parse_status(document_id, tenant_id, "failed")
        except Exception:
            logger.exception(
                "Failed to mark document %s as failed after crash", document_id
            )
    finally:
        db.close()
