import logging

from fastapi import BackgroundTasks

from app.models.base import SessionLocal
from app.repositories.design_document_repository import DesignDocumentRepository
from app.services.design_document_service import DesignDocumentService

logger = logging.getLogger(__name__)


def schedule_generate_design_document(
    background_tasks: BackgroundTasks, tenant_id: int, document_id: str
) -> None:
    """Schedule design document generation as a background task."""
    background_tasks.add_task(_run_generate, tenant_id, document_id)


def _run_generate(tenant_id: int, document_id: str) -> None:
    db = SessionLocal()
    design_repo = DesignDocumentRepository(db)
    try:
        design = design_repo.get_by_document_id(document_id, tenant_id)
        if design is None:
            logger.warning(
                "Background design generation skipped: design doc for document %s not found",
                document_id,
            )
            return
        if design.status != "running":
            logger.warning(
                "Background design generation skipped: design status=%s (expected running)",
                design.status,
            )
            return

        service = DesignDocumentService(db)
        service.execute_generate(tenant_id, document_id)
    except Exception:
        logger.exception("Background design generation crashed for document %s", document_id)
        try:
            design_repo.update_status(
                document_id,
                tenant_id,
                "failed",
                error_message="后台任务执行异常",
            )
        except Exception:
            logger.exception(
                "Failed to mark design document %s as failed after crash", document_id
            )
    finally:
        db.close()
