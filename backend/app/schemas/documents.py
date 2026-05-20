from pydantic import BaseModel, Field


class StandardResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: dict | None = None
    trace_id: str = ""


class UploadInitRequest(BaseModel):
    filename: str
    file_size_bytes: int
    file_type: str


class UploadInitResponse(BaseModel):
    document_id: str
    chunk_size: int
    max_chunks: int


class UploadChunkRequest(BaseModel):
    document_id: str
    chunk_index: int


class UploadCompleteRequest(BaseModel):
    document_id: str
    total_chunks: int
    sha256: str


class DocumentStatusResponse(BaseModel):
    document_id: str
    status: str
    progress_percent: int
    parse_task_id: str | None = None
    original_filename: str | None = None
