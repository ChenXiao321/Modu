import hashlib
import json
import os
import re
import shutil
import threading
from pathlib import Path
from uuid import uuid4
from weakref import WeakValueDictionary

from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import (
    ChunkChecksumMismatchError,
    ChunkUploadError,
    DocumentNotFoundError,
    FileTooLargeError,
    MergeFailedError,
    UnsupportedFileTypeError,
)
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository


def _validate_file(filename: str, file_size: int) -> None:
    if file_size > settings.upload_max_size_bytes:
        raise FileTooLargeError(settings.upload_max_size_bytes // (1024 * 1024))

    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_file_extensions:
        raise UnsupportedFileTypeError(filename)


def _get_tenant_path(tenant_id: int) -> Path:
    return Path(settings.upload_storage_path) / str(tenant_id)


def _get_chunks_path(tenant_id: int, document_id: str) -> Path:
    return _get_tenant_path(tenant_id) / "chunks" / document_id


def _get_document_path(tenant_id: int, document_id: str) -> Path:
    return _get_tenant_path(tenant_id) / "documents" / document_id


def _secure_filename(filename: str) -> str:
    filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
    filename = filename.lstrip('.')
    if not filename:
        filename = 'unnamed'
    return filename


def _compute_chunk_checksum(chunk_data: bytes) -> str:
    hash_val = 0
    for b in chunk_data:
        hash_val = (hash_val * 31 + b) & 0xFFFFFFFF
    return format(hash_val, "08x")


def _compute_file_sha256(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


_locks: WeakValueDictionary = WeakValueDictionary()
_locks_lock = threading.Lock()


def _get_lock(key: str) -> threading.Lock:
    with _locks_lock:
        lock = _locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _locks[key] = lock
        return lock


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.repo = DocumentRepository(db)

    def init_upload(self, tenant_id: int, filename: str, file_size: int, file_type: str) -> dict:
        _validate_file(filename, file_size)

        total_chunks = (file_size + settings.upload_chunk_size_bytes - 1) // settings.upload_chunk_size_bytes

        doc = Document(
            tenant_id=tenant_id,
            original_filename=filename,
            file_type=file_type,
            file_size_bytes=file_size,
            upload_status="uploading",
            total_chunks=total_chunks,
            uploaded_chunks="[]",
        )
        doc = self.repo.create(doc)

        chunks_path = _get_chunks_path(tenant_id, str(doc.id))
        chunks_path.mkdir(parents=True, exist_ok=True)

        return {
            "document_id": str(doc.id),
            "chunk_size": settings.upload_chunk_size_bytes,
            "max_chunks": total_chunks,
        }

    def upload_chunk(
        self, tenant_id: int, document_id: str, chunk_index: int, chunk_data: bytes, checksum: str
    ) -> dict:
        doc = self.repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)

        if chunk_index < 0 or chunk_index >= doc.total_chunks:
            raise ChunkUploadError(chunk_index, "分片索引超出范围")

        # 校验分片 checksum
        actual_checksum = _compute_chunk_checksum(chunk_data)
        if actual_checksum != checksum:
            raise ChunkChecksumMismatchError(chunk_index)

        chunk_path = _get_chunks_path(tenant_id, document_id) / f"chunk_{chunk_index}"
        try:
            with open(chunk_path, "wb") as f:
                f.write(chunk_data)
        except OSError as e:
            raise ChunkUploadError(chunk_index, str(e))

        lock = _get_lock(f"{tenant_id}:{document_id}")
        with lock:
            doc = self.repo.update_uploaded_chunks(document_id, tenant_id, chunk_index)
        if doc is None:
            raise DocumentNotFoundError(document_id)

        uploaded = json.loads(doc.uploaded_chunks or "[]")
        progress = int(len(uploaded) / doc.total_chunks * 100)
        return {
            "document_id": document_id,
            "chunk_index": chunk_index,
            "received": True,
            "progress_percent": progress,
        }

    def complete_upload(self, tenant_id: int, document_id: str, total_chunks: int, sha256: str) -> dict:
        doc = self.repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)

        uploaded = json.loads(doc.uploaded_chunks or "[]")
        if len(uploaded) != total_chunks:
            missing = set(range(total_chunks)) - set(uploaded)
            raise MergeFailedError(
                document_id, f"分片不完整，缺少: {sorted(missing)}"
            )

        # 合并分片
        chunks_path = _get_chunks_path(tenant_id, document_id)
        doc_path = _get_document_path(tenant_id, document_id)
        doc_path.mkdir(parents=True, exist_ok=True)
        final_file = doc_path / _secure_filename(doc.original_filename)

        try:
            with open(final_file, "wb") as outfile:
                for i in range(total_chunks):
                    chunk_file = chunks_path / f"chunk_{i}"
                    if not chunk_file.exists():
                        raise MergeFailedError(document_id, f"分片文件缺失: chunk_{i}")
                    with open(chunk_file, "rb") as infile:
                        outfile.write(infile.read())
        except OSError as e:
            raise MergeFailedError(document_id, str(e))

        # 校验 SHA-256
        actual_sha256 = _compute_file_sha256(final_file)
        if actual_sha256 != sha256:
            final_file.unlink(missing_ok=True)
            raise MergeFailedError(document_id, "文件 SHA-256 校验失败")

        # 清理临时分片
        shutil.rmtree(chunks_path, ignore_errors=True)

        self.repo.update_status(document_id, tenant_id, "completed", str(final_file))
        self.repo.update_checksum(document_id, tenant_id, sha256)

        return {
            "document_id": document_id,
            "status": "completed",
            "storage_path": str(final_file),
            "sha256": sha256,
        }

    def get_status(self, tenant_id: int, document_id: str) -> dict:
        doc = self.repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)

        progress = 0
        if doc.total_chunks > 0:
            uploaded = json.loads(doc.uploaded_chunks or "[]")
            progress = int(len(uploaded) / doc.total_chunks * 100)

        return {
            "document_id": document_id,
            "status": doc.upload_status,
            "progress_percent": progress,
            "parse_task_id": doc.parse_task_id,
            "original_filename": doc.original_filename,
        }
