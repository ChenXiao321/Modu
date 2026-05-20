import hashlib
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.exceptions import (
    FileTooLargeError,
    UnsupportedFileTypeError,
    DocumentNotFoundError,
    ChunkUploadError,
    ChunkChecksumMismatchError,
    MergeFailedError,
)
from app.models.base import Base
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def service(db_session):
    return DocumentService(db_session)


class TestValidateFile:
    def test_valid_pdf(self, service):
        # Should not raise
        service.init_upload(1, "test.pdf", 1024, "application/pdf")

    def test_file_too_large(self, service):
        with pytest.raises(FileTooLargeError):
            service.init_upload(1, "test.pdf", settings.upload_max_size_bytes + 1, "application/pdf")

    def test_unsupported_extension(self, service):
        with pytest.raises(UnsupportedFileTypeError):
            service.init_upload(1, "test.exe", 1024, "application/octet-stream")


class TestInitUpload:
    def test_creates_document_record(self, service, db_session):
        with patch("app.services.document_service._get_chunks_path") as mock_path:
            mock_path.return_value = Path(tempfile.mkdtemp())
            result = service.init_upload(1, "chip_manual.pdf", 10 * 1024 * 1024, "application/pdf")

        assert "document_id" in result
        assert result["chunk_size"] == settings.upload_chunk_size_bytes
        assert result["max_chunks"] == 2  # 10MB / 5MB = 2

        doc = db_session.query(Document).filter_by(id=result["document_id"]).first()
        assert doc is not None
        assert doc.original_filename == "chip_manual.pdf"
        assert doc.upload_status == "uploading"


class TestUploadChunk:
    def test_successful_chunk_upload(self, service, db_session):
        with patch("app.services.document_service._get_chunks_path") as mock_path:
            chunks_dir = Path(tempfile.mkdtemp())
            mock_path.return_value = chunks_dir
            init_res = service.init_upload(1, "test.pdf", 1024, "application/pdf")

            doc_id = init_res["document_id"]
            chunk_data = b"test chunk data"
            checksum = hashlib.md5(chunk_data).hexdigest()

            result = service.upload_chunk(1, doc_id, 0, chunk_data, checksum)

            assert result["received"] is True
            assert result["chunk_index"] == 0

            # Verify chunk file exists
            chunk_file = chunks_dir / f"chunk_0"
            assert chunk_file.exists()

    def test_invalid_chunk_index(self, service):
        with patch("app.services.document_service._get_chunks_path") as mock_path:
            mock_path.return_value = Path(tempfile.mkdtemp())
            init_res = service.init_upload(1, "test.pdf", 1024, "application/pdf")

        with pytest.raises(ChunkUploadError):
            service.upload_chunk(1, init_res["document_id"], 999, b"data", "checksum")

    def test_checksum_mismatch(self, service):
        with patch("app.services.document_service._get_chunks_path") as mock_path:
            mock_path.return_value = Path(tempfile.mkdtemp())
            init_res = service.init_upload(1, "test.pdf", 1024, "application/pdf")

        with pytest.raises(ChunkChecksumMismatchError):
            service.upload_chunk(1, init_res["document_id"], 0, b"data", "wrong_checksum")


class TestCompleteUpload:
    def test_successful_merge(self, service, db_session):
        with patch("app.services.document_service._get_chunks_path") as mock_chunks, \
             patch("app.services.document_service._get_document_path") as mock_docs, \
             patch.object(settings, "upload_chunk_size_bytes", 5):
            chunks_dir = Path(tempfile.mkdtemp())
            docs_dir = Path(tempfile.mkdtemp())
            mock_chunks.return_value = chunks_dir
            mock_docs.return_value = docs_dir

            init_res = service.init_upload(1, "test.pdf", 10, "application/pdf")
            doc_id = init_res["document_id"]

            # Upload all chunks
            for i in range(2):
                chunk_data = b"A" * 5
                checksum = hashlib.md5(chunk_data).hexdigest()
                service.upload_chunk(1, doc_id, i, chunk_data, checksum)

            # Compute expected SHA-256
            full_data = b"A" * 10
            expected_sha256 = hashlib.sha256(full_data).hexdigest()

            result = service.complete_upload(1, doc_id, 2, expected_sha256)

        assert result["status"] == "completed"
        assert result["sha256"] == expected_sha256

    def test_incomplete_chunks(self, service):
        with patch("app.services.document_service._get_chunks_path") as mock_path:
            mock_path.return_value = Path(tempfile.mkdtemp())
            init_res = service.init_upload(1, "test.pdf", 10, "application/pdf")

            with pytest.raises(MergeFailedError):
                service.complete_upload(1, init_res["document_id"], 2, "sha256")

    def test_sha256_mismatch(self, service):
        with patch("app.services.document_service._get_chunks_path") as mock_chunks, \
             patch("app.services.document_service._get_document_path") as mock_docs:
            chunks_dir = Path(tempfile.mkdtemp())
            docs_dir = Path(tempfile.mkdtemp())
            mock_chunks.return_value = chunks_dir
            mock_docs.return_value = docs_dir

            init_res = service.init_upload(1, "test.pdf", 5, "application/pdf")
            doc_id = init_res["document_id"]

            chunk_data = b"A" * 5
            checksum = hashlib.md5(chunk_data).hexdigest()
            service.upload_chunk(1, doc_id, 0, chunk_data, checksum)

            with pytest.raises(MergeFailedError):
                service.complete_upload(1, doc_id, 1, "wrong_sha256")


class TestGetStatus:
    def test_existing_document(self, service):
        with patch("app.services.document_service._get_chunks_path") as mock_path:
            mock_path.return_value = Path(tempfile.mkdtemp())
            init_res = service.init_upload(1, "test.pdf", 1024, "application/pdf")

        result = service.get_status(1, init_res["document_id"])
        assert result["status"] == "uploading"
        assert result["progress_percent"] == 0

    def test_nonexistent_document(self, service):
        with pytest.raises(DocumentNotFoundError):
            service.get_status(1, "nonexistent-id")
