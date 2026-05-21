from fastapi import Request
from fastapi.responses import JSONResponse


class ModuException(Exception):
    def __init__(self, error_code: str, message: str, detail: dict | None = None) -> None:
        self.error_code = error_code
        self.message = message
        self.detail = detail or {}


class FileTooLargeError(ModuException):
    def __init__(self, max_size_mb: int) -> None:
        super().__init__(
            error_code="FILE_TOO_LARGE",
            message=f"文件大小超过限制（最大 {max_size_mb}MB）",
            detail={"max_size_mb": max_size_mb},
        )


class UnsupportedFileTypeError(ModuException):
    def __init__(self, filename: str) -> None:
        super().__init__(
            error_code="UNSUPPORTED_FILE_TYPE",
            message=f"不支持的文件格式: {filename}",
            detail={"filename": filename},
        )


class ChunkUploadError(ModuException):
    def __init__(self, chunk_index: int, reason: str) -> None:
        super().__init__(
            error_code="CHUNK_UPLOAD_FAILED",
            message=f"分片 {chunk_index} 上传失败: {reason}",
            detail={"chunk_index": chunk_index, "reason": reason},
        )


class ChunkChecksumMismatchError(ModuException):
    def __init__(self, chunk_index: int) -> None:
        super().__init__(
            error_code="CHUNK_CHECKSUM_MISMATCH",
            message=f"分片 {chunk_index} 校验失败",
            detail={"chunk_index": chunk_index},
        )


class MergeFailedError(ModuException):
    def __init__(self, document_id: str, reason: str) -> None:
        super().__init__(
            error_code="MERGE_FAILED",
            message=f"文件合并失败: {reason}",
            detail={"document_id": document_id, "reason": reason},
        )


class DocumentNotFoundError(ModuException):
    def __init__(self, document_id: str) -> None:
        super().__init__(
            error_code="DOCUMENT_NOT_FOUND",
            message=f"文档不存在: {document_id}",
            detail={"document_id": document_id},
        )


_EXCEPTION_STATUS_CODES: dict[str, int] = {
    "FILE_TOO_LARGE": 413,
    "UNSUPPORTED_FILE_TYPE": 415,
    "DOCUMENT_NOT_FOUND": 404,
    "CHUNK_UPLOAD_FAILED": 400,
    "CHUNK_CHECKSUM_MISMATCH": 400,
    "MERGE_FAILED": 400,
}


async def modu_exception_handler(request: Request, exc: ModuException) -> JSONResponse:
    status_code = _EXCEPTION_STATUS_CODES.get(exc.error_code, 400)
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "detail": exc.detail,
            },
            "trace_id": "",
        },
    )
