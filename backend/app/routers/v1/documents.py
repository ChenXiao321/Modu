from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.dependencies import CurrentTenant
from app.exceptions import ModuException
from app.models.base import get_db
from app.schemas.documents import (
    DocumentStatusResponse,
    StandardResponse,
    UploadChunkRequest,
    UploadCompleteRequest,
    UploadInitRequest,
    UploadInitResponse,
)
from app.services.document_service import DocumentService

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
