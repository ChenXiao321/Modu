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


class DocumentNotReadyError(ModuException):
    def __init__(self, document_id: str, reason: str) -> None:
        super().__init__(
            error_code="DOCUMENT_NOT_READY",
            message=f"文档未就绪: {reason}",
            detail={"document_id": document_id, "reason": reason},
        )


class FieldNotFoundError(ModuException):
    def __init__(self, field_id: str) -> None:
        super().__init__(
            error_code="FIELD_NOT_FOUND",
            message=f"OCR 字段不存在: {field_id}",
            detail={"field_id": field_id},
        )


class FieldAlreadyConfirmedError(ModuException):
    def __init__(self, field_id: str) -> None:
        super().__init__(
            error_code="FIELD_ALREADY_CONFIRMED",
            message=f"OCR 字段已被确认: {field_id}",
            detail={"field_id": field_id},
        )


class PipelineNotBlockedError(ModuException):
    def __init__(self, document_id: str) -> None:
        super().__init__(
            error_code="PIPELINE_NOT_BLOCKED",
            message=f"流水线未阻塞，无需确认: {document_id}",
            detail={"document_id": document_id},
        )


class PipelineBlockedError(ModuException):
    def __init__(self, document_id: str, reason: str) -> None:
        super().__init__(
            error_code="PIPELINE_BLOCKED",
            message=f"流水线阻塞，无法继续: {reason}",
            detail={"document_id": document_id, "reason": reason},
        )


class DesignDocumentNotFoundError(ModuException):
    def __init__(self, document_id: str) -> None:
        super().__init__(
            error_code="DESIGN_DOCUMENT_NOT_FOUND",
            message=f"设计文档不存在: {document_id}",
            detail={"document_id": document_id},
        )


class DesignDocumentNotReadyError(ModuException):
    def __init__(self, document_id: str, reason: str) -> None:
        super().__init__(
            error_code="DESIGN_DOCUMENT_NOT_READY",
            message=f"设计文档尚未就绪: {reason}",
            detail={"document_id": document_id, "reason": reason},
        )


class InvalidSectionKeyError(ModuException):
    def __init__(self, section_key: str) -> None:
        super().__init__(
            error_code="INVALID_SECTION_KEY",
            message=f"无效的章节 key: {section_key}",
            detail={"section_key": section_key},
        )


class RevisionNotFoundError(ModuException):
    def __init__(self, revision_id: str) -> None:
        super().__init__(
            error_code="REVISION_NOT_FOUND",
            message=f"修订记录不存在: {revision_id}",
            detail={"revision_id": revision_id},
        )


class CommentNotFoundError(ModuException):
    def __init__(self, comment_id: str) -> None:
        super().__init__(
            error_code="COMMENT_NOT_FOUND",
            message=f"评审意见不存在: {comment_id}",
            detail={"comment_id": comment_id},
        )


class CommentAlreadyResolvedError(ModuException):
    def __init__(self, comment_id: str) -> None:
        super().__init__(
            error_code="COMMENT_ALREADY_RESOLVED",
            message=f"评审意见已被解决: {comment_id}",
            detail={"comment_id": comment_id},
        )


class PendingCommentsExistError(ModuException):
    def __init__(self, document_id: str, count: int) -> None:
        super().__init__(
            error_code="PENDING_COMMENTS_EXIST",
            message=f"存在 {count} 条未解决的评审意见，无法提交审查",
            detail={"document_id": document_id, "pending_count": count},
        )


class PipelineStatusInvalidError(ModuException):
    def __init__(self, document_id: str, current_status: str, expected_status: str) -> None:
        super().__init__(
            error_code="PIPELINE_STATUS_INVALID",
            message=f"当前流水线状态 '{current_status}' 不允许执行此操作，期望: {expected_status}",
            detail={"document_id": document_id, "current_status": current_status, "expected_status": expected_status},
        )


_EXCEPTION_STATUS_CODES: dict[str, int] = {
    "FILE_TOO_LARGE": 413,
    "UNSUPPORTED_FILE_TYPE": 415,
    "DOCUMENT_NOT_FOUND": 404,
    "DOCUMENT_NOT_READY": 409,
    "CHUNK_UPLOAD_FAILED": 400,
    "CHUNK_CHECKSUM_MISMATCH": 400,
    "MERGE_FAILED": 400,
    "FIELD_NOT_FOUND": 404,
    "FIELD_ALREADY_CONFIRMED": 409,
    "PIPELINE_NOT_BLOCKED": 409,
    "PIPELINE_BLOCKED": 409,
    "DESIGN_DOCUMENT_NOT_FOUND": 404,
    "DESIGN_DOCUMENT_NOT_READY": 409,
    "INVALID_SECTION_KEY": 400,
    "REVISION_NOT_FOUND": 404,
    "COMMENT_NOT_FOUND": 404,
    "PENDING_COMMENTS_EXIST": 409,
    "PIPELINE_STATUS_INVALID": 409,
    "COMMENT_ALREADY_RESOLVED": 409,
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
