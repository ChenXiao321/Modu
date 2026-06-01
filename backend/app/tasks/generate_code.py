import logging

from fastapi import BackgroundTasks

from app.models.base import SessionLocal
from app.repositories.document_repository import DocumentRepository
from app.services.code_generation_service import CodeGenerationService

logger = logging.getLogger(__name__)


def schedule_generate_code(
    background_tasks: BackgroundTasks, tenant_id: int, document_id: str
) -> None:
    """Schedule code generation as a background task."""
    background_tasks.add_task(_run_generate, tenant_id, document_id)


def _run_generate(tenant_id: int, document_id: str) -> None:
    db = SessionLocal()
    doc_repo = DocumentRepository(db)
    try:
        doc = doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            logger.warning(
                "Background code generation skipped: document %s not found",
                document_id,
            )
            return
        if doc.pipeline_status != "code_generation_running":
            logger.warning(
                "Background code generation skipped: pipeline_status=%s (expected code_generation_running)",
                doc.pipeline_status,
            )
            return

        service = CodeGenerationService(db)
        service.execute_generate(tenant_id, document_id)
    except Exception as exc:
        logger.exception("Background code generation crashed for document %s", document_id)
        error_msg = str(exc) if str(exc) else "后台任务执行异常"
        try:
            doc = doc_repo.get_by_id(document_id, tenant_id)
            if doc is not None and doc.pipeline_status == "code_generation_running":
                doc.pipeline_status = "design_reviewed"
                doc.block_reason = None
                db.commit()
        except Exception:
            logger.exception(
                "Failed to rollback pipeline status for document %s after crash", document_id
            )
    finally:
        db.close()
