from pydantic import BaseModel, Field


class StandardResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: dict | None = None
    trace_id: str = ""


_MAX_FILENAME_LEN = 255
_MAX_FILE_TYPE_LEN = 100
_MAX_SHA256_LEN = 64
_MAX_TRACE_ID_LEN = 100


class UploadInitRequest(BaseModel):
    filename: str = Field(max_length=_MAX_FILENAME_LEN)
    file_size_bytes: int
    file_type: str = Field(max_length=_MAX_FILE_TYPE_LEN)


class UploadInitResponse(BaseModel):
    document_id: str
    chunk_size: int
    max_chunks: int


class UploadChunkRequest(BaseModel):
    document_id: str = Field(max_length=36)
    chunk_index: int


class UploadCompleteRequest(BaseModel):
    document_id: str = Field(max_length=36)
    total_chunks: int
    sha256: str = Field(max_length=_MAX_SHA256_LEN)


class DocumentStatusResponse(BaseModel):
    document_id: str
    status: str
    progress_percent: int
    parse_task_id: str | None = None
    original_filename: str | None = None
