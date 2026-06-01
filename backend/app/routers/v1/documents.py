from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.dependencies import CurrentTenant
from app.exceptions import DocumentNotFoundError, DocumentNotReadyError, ModuException
from app.models.base import get_db
from app.schemas.design_review import (
    ResolveCommentRequest,
    ReviewCommentRequest,
    RollbackRevisionRequest,
    SaveRevisionRequest,
)
from app.schemas.documents import (
    DocumentStatusResponse,
    StandardResponse,
    UploadChunkRequest,
    UploadCompleteRequest,
    UploadInitRequest,
    UploadInitResponse,
)
from app.schemas.requirements import ConfirmFieldRequest
from app.services.code_generation_service import CodeGenerationService
from app.services.design_document_service import DesignDocumentService
from app.services.design_review_service import DesignReviewService
from app.repositories.document_repository import DocumentRepository
from app.repositories.fc_requirement_repository import FcRequirementRepository
from app.repositories.software_detailed_design_repository import SoftwareDetailedDesignRepository
from app.services.document_parse_service import DocumentParseService
from app.services.document_service import DocumentService
from app.tasks.generate_code import schedule_generate_code
from app.tasks.generate_design_document import schedule_generate_design_document
from app.tasks.parse_document import schedule_parse

router = APIRouter(prefix="/documents", tags=["Documents"])


def _wrap(data: dict | None = None) -> dict:
    return {
        "success": True,
        "data": data,
        "error": None,
        "trace_id": "",
    }


@router.post("/upload/init", response_model=StandardResponse)
def upload_init(
    tenant_id: CurrentTenant,
    req: UploadInitRequest,
    db: Session = Depends(get_db),
) -> dict:
    svc = DocumentService(db)
    result = svc.init_upload(tenant_id, req.filename, req.file_size_bytes, req.file_type)
    return _wrap(result)


@router.post("/upload/chunk", response_model=StandardResponse)
def upload_chunk(
    tenant_id: CurrentTenant,
    document_id: Annotated[str, Form()],
    chunk_index: Annotated[int, Form()],
    checksum: Annotated[str, Form()],
    chunk_data: Annotated[UploadFile, File()],
    db: Session = Depends(get_db),
) -> dict:
    svc = DocumentService(db)
    data = chunk_data.file.read()
    result = svc.upload_chunk(tenant_id, document_id, chunk_index, data, checksum)
    return _wrap(result)


@router.post("/upload/complete", response_model=StandardResponse)
def upload_complete(
    tenant_id: CurrentTenant,
    req: UploadCompleteRequest,
    db: Session = Depends(get_db),
) -> dict:
    svc = DocumentService(db)
    result = svc.complete_upload(tenant_id, req.document_id, req.total_chunks, req.sha256)
    return _wrap(result)


@router.get("/{document_id}/status", response_model=StandardResponse)
def get_document_status(
    tenant_id: CurrentTenant,
    document_id: str,
    db: Session = Depends(get_db),
) -> dict:
    svc = DocumentService(db)
    result = svc.get_status(tenant_id, document_id)
    return _wrap(result)


@router.post("/{document_id}/parse", response_model=StandardResponse)
def trigger_parse(
    tenant_id: CurrentTenant,
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    svc = DocumentParseService(db)
    result = svc.trigger_parse(tenant_id, document_id)
    schedule_parse(background_tasks, tenant_id, document_id)
    return _wrap(result)


@router.get("/{document_id}/parse/status", response_model=StandardResponse)
def get_parse_status(
    tenant_id: CurrentTenant,
    document_id: str,
    db: Session = Depends(get_db),
) -> dict:
    svc = DocumentParseService(db)
    result = svc.get_parse_status(tenant_id, document_id)
    return _wrap(result)


@router.get("/{document_id}/requirements", response_model=StandardResponse)
def get_requirements(
    tenant_id: CurrentTenant,
    document_id: str,
    db: Session = Depends(get_db),
) -> dict:
    svc = DocumentParseService(db)
    tree = svc.get_requirements_tree(tenant_id, document_id)
    return _wrap({"document_id": document_id, "requirements": tree})


@router.get("/{document_id}/safety-parameters", response_model=StandardResponse)
def get_safety_parameters(
    tenant_id: CurrentTenant,
    document_id: str,
    db: Session = Depends(get_db),
) -> dict:
    svc = DocumentParseService(db)
    parameters = svc.get_safety_parameters(tenant_id, document_id)
    return _wrap({"document_id": document_id, "parameters": parameters})


@router.get("/{document_id}/ocr-results", response_model=StandardResponse)
def get_ocr_results(
    tenant_id: CurrentTenant,
    document_id: str,
    db: Session = Depends(get_db),
) -> dict:
    svc = DocumentParseService(db)
    result = svc.get_ocr_results(tenant_id, document_id)
    return _wrap(result)


@router.post("/{document_id}/ocr-fields/{field_id}/confirm", response_model=StandardResponse)
def confirm_ocr_field(
    tenant_id: CurrentTenant,
    document_id: str,
    field_id: str,
    req: ConfirmFieldRequest,
    db: Session = Depends(get_db),
) -> dict:
    svc = DocumentParseService(db)
    result = svc.confirm_low_confidence_field(tenant_id, document_id, field_id, req.reviewer_name)
    return _wrap(result)


@router.post("/{document_id}/design", response_model=StandardResponse)
def trigger_design_document(
    tenant_id: CurrentTenant,
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    svc = DesignDocumentService(db)
    result = svc.trigger_generate(tenant_id, document_id)
    schedule_generate_design_document(background_tasks, tenant_id, document_id)
    return _wrap(result)


@router.get("/{document_id}/design", response_model=StandardResponse)
def get_design_document(
    tenant_id: CurrentTenant,
    document_id: str,
    db: Session = Depends(get_db),
) -> dict:
    svc = DesignDocumentService(db)
    result = svc.get_design_document(tenant_id, document_id)
    return _wrap(result)


@router.get("/", response_model=StandardResponse)
def list_documents(
    tenant_id: CurrentTenant,
    db: Session = Depends(get_db),
) -> dict:
    svc = DocumentService(db)
    docs = svc.list_documents(tenant_id)
    items = []
    for doc in docs:
        items.append(
            {
                "document_id": doc.id,
                "original_filename": doc.original_filename,
                "file_type": doc.file_type,
                "file_size_bytes": doc.file_size_bytes,
                "upload_status": doc.upload_status,
                "parse_status": doc.parse_status,
                "pipeline_status": doc.pipeline_status,
                "block_reason": doc.block_reason,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
        )
    return _wrap({"items": items, "total": len(items)})


# ---------------------------------------------------------------------------
# Design Review endpoints (Story 2.2)
# ---------------------------------------------------------------------------

@router.get("/{document_id}/design-review", response_model=StandardResponse)
def get_design_review(
    tenant_id: CurrentTenant,
    document_id: str,
    db: Session = Depends(get_db),
) -> dict:
    svc = DesignReviewService(db)
    result = svc.get_review_context(tenant_id, document_id)
    return _wrap(result)


@router.post("/{document_id}/design-revisions", response_model=StandardResponse)
def save_design_revision(
    tenant_id: CurrentTenant,
    document_id: str,
    req: SaveRevisionRequest,
    db: Session = Depends(get_db),
) -> dict:
    svc = DesignReviewService(db)
    result = svc.save_revision(
        tenant_id, document_id, req.section_key, req.revised_content, req.author
    )
    return _wrap(result)


@router.get("/{document_id}/design-revisions", response_model=StandardResponse)
def get_design_revisions(
    tenant_id: CurrentTenant,
    document_id: str,
    section_key: str,
    db: Session = Depends(get_db),
) -> dict:
    svc = DesignReviewService(db)
    result = svc.get_revision_history(tenant_id, document_id, section_key)
    return _wrap(result)


@router.post("/{document_id}/review-comments", response_model=StandardResponse)
def add_review_comment(
    tenant_id: CurrentTenant,
    document_id: str,
    req: ReviewCommentRequest,
    db: Session = Depends(get_db),
) -> dict:
    svc = DesignReviewService(db)
    result = svc.add_review_comment(
        tenant_id, document_id, req.section_key, req.comment_text, req.author
    )
    return _wrap(result)


@router.get("/{document_id}/review-comments", response_model=StandardResponse)
def get_review_comments(
    tenant_id: CurrentTenant,
    document_id: str,
    section_key: str,
    db: Session = Depends(get_db),
) -> dict:
    svc = DesignReviewService(db)
    result = svc.get_review_comments(tenant_id, document_id, section_key)
    return _wrap(result)


@router.patch("/{document_id}/review-comments/{comment_id}/resolve", response_model=StandardResponse)
def resolve_review_comment(
    tenant_id: CurrentTenant,
    document_id: str,
    comment_id: str,
    req: ResolveCommentRequest,
    db: Session = Depends(get_db),
) -> dict:
    svc = DesignReviewService(db)
    result = svc.resolve_review_comment(tenant_id, document_id, comment_id, req.resolved_by)
    return _wrap(result)


@router.post("/{document_id}/design-review/submit", response_model=StandardResponse)
def submit_design_review(
    tenant_id: CurrentTenant,
    document_id: str,
    db: Session = Depends(get_db),
) -> dict:
    svc = DesignReviewService(db)
    result = svc.submit_design_review(tenant_id, document_id)
    return _wrap(result)


@router.post("/{document_id}/design-revisions/{revision_id}/rollback", response_model=StandardResponse)
def rollback_to_revision(
    tenant_id: CurrentTenant,
    document_id: str,
    revision_id: str,
    req: RollbackRevisionRequest,
    db: Session = Depends(get_db),
) -> dict:
    svc = DesignReviewService(db)
    result = svc.rollback_to_revision(tenant_id, document_id, revision_id, req.author)
    return _wrap(result)


# ---------------------------------------------------------------------------
# FC Requirement Specification endpoints
# ---------------------------------------------------------------------------

@router.get("/{document_id}/fc-requirement", response_model=StandardResponse)
def get_fc_requirement(
    tenant_id: CurrentTenant,
    document_id: str,
    db: Session = Depends(get_db),
) -> dict:
    doc_repo = DocumentRepository(db)
    doc = doc_repo.get_by_id(document_id, tenant_id)
    if doc is None:
        raise DocumentNotFoundError(document_id)
    if doc.parse_status != "completed":
        return _wrap({"status": doc.parse_status or "pending", "fc_spec": None})

    fc_repo = FcRequirementRepository(db)
    fc_doc = fc_repo.get_by_document(document_id, tenant_id)
    if fc_doc is None:
        return _wrap({"status": "not_found", "fc_spec": None})

    return _wrap({"status": "completed", "fc_spec": fc_repo.to_dict(fc_doc)})


# ---------------------------------------------------------------------------
# Software Detailed Design endpoints
# ---------------------------------------------------------------------------

@router.get("/{document_id}/detailed-design", response_model=StandardResponse)
def get_detailed_design(
    tenant_id: CurrentTenant,
    document_id: str,
    db: Session = Depends(get_db),
) -> dict:
    doc_repo = DocumentRepository(db)
    doc = doc_repo.get_by_id(document_id, tenant_id)
    if doc is None:
        raise DocumentNotFoundError(document_id)

    design_repo = SoftwareDetailedDesignRepository(db)
    design = design_repo.get_by_document(document_id, tenant_id)
    if design is None:
        return _wrap({"status": "pending", "design": None})

    return _wrap({"status": design.status, "design": design_repo.to_dict(design)})


# ---------------------------------------------------------------------------
# Code Generation endpoints
# ---------------------------------------------------------------------------

@router.post("/{document_id}/code-generation", response_model=StandardResponse)
def trigger_code_generation(
    tenant_id: CurrentTenant,
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    svc = CodeGenerationService(db)
    result = svc.trigger_generate(tenant_id, document_id)
    schedule_generate_code(background_tasks, tenant_id, document_id)
    return _wrap(result)


@router.get("/{document_id}/code-files", response_model=StandardResponse)
def get_code_files(
    tenant_id: CurrentTenant,
    document_id: str,
    db: Session = Depends(get_db),
) -> dict:
    svc = CodeGenerationService(db)
    files = svc.get_code_files(tenant_id, document_id)
    return _wrap({"document_id": document_id, "files": files})


@router.get("/{document_id}/code-files/{file_id}", response_model=StandardResponse)
def get_code_file(
    tenant_id: CurrentTenant,
    document_id: str,
    file_id: str,
    db: Session = Depends(get_db),
) -> dict:
    svc = CodeGenerationService(db)
    result = svc.get_code_file_by_id(tenant_id, document_id, file_id)
    return _wrap(result)
