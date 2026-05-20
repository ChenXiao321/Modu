import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models.base import Base, get_db


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(test_db):
    app = create_app()

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_db.bind)
    return TestClient(app)


class TestUploadFlow:
    def test_complete_upload_flow(self, client):
        with patch("app.services.document_service._get_chunks_path") as mock_chunks, \
             patch("app.services.document_service._get_document_path") as mock_docs:
            chunks_dir = Path(tempfile.mkdtemp())
            docs_dir = Path(tempfile.mkdtemp())
            mock_chunks.return_value = chunks_dir
            mock_docs.return_value = docs_dir

            # Step 1: Initialize upload
            init_res = client.post(
                "/api/v1/documents/upload/init",
                json={
                    "filename": "test.pdf",
                    "file_size_bytes": 10,
                    "file_type": "application/pdf",
                },
                headers={"X-Tenant-ID": "1"},
            )
            assert init_res.status_code == 200
            data = init_res.json()["data"]
            doc_id = data["document_id"]
            assert data["chunk_size"] == 5 * 1024 * 1024
            assert data["max_chunks"] == 1  # 10 bytes / 5MB = 1 (ceil)

            # Step 2: Upload chunk
            chunk_data = b"A" * 10
            checksum = hashlib.md5(chunk_data).hexdigest()

            chunk_res = client.post(
                "/api/v1/documents/upload/chunk",
                data={
                    "document_id": doc_id,
                    "chunk_index": "0",
                    "checksum": checksum,
                },
                files={"chunk_data": ("chunk_0", chunk_data, "application/octet-stream")},
                headers={"X-Tenant-ID": "1"},
            )
            assert chunk_res.status_code == 200

            # Step 3: Complete upload
            expected_sha256 = hashlib.sha256(chunk_data).hexdigest()
            complete_res = client.post(
                "/api/v1/documents/upload/complete",
                json={
                    "document_id": doc_id,
                    "total_chunks": 1,
                    "sha256": expected_sha256,
                },
                headers={"X-Tenant-ID": "1"},
            )
            assert complete_res.status_code == 200
            assert complete_res.json()["data"]["status"] == "completed"

            # Step 4: Check status
            status_res = client.get(
                f"/api/v1/documents/{doc_id}/status",
                headers={"X-Tenant-ID": "1"},
            )
            assert status_res.status_code == 200
            assert status_res.json()["data"]["status"] == "completed"
            assert status_res.json()["data"]["progress_percent"] == 100

    def test_file_too_large(self, client):
        res = client.post(
            "/api/v1/documents/upload/init",
            json={
                "filename": "huge.pdf",
                "file_size_bytes": 200 * 1024 * 1024,
                "file_type": "application/pdf",
            },
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "FILE_TOO_LARGE"

    def test_unsupported_file_type(self, client):
        res = client.post(
            "/api/v1/documents/upload/init",
            json={
                "filename": "virus.exe",
                "file_size_bytes": 1024,
                "file_type": "application/octet-stream",
            },
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_chunk_checksum_mismatch(self, client):
        with patch("app.services.document_service._get_chunks_path") as mock_path:
            mock_path.return_value = Path(tempfile.mkdtemp())

            init_res = client.post(
                "/api/v1/documents/upload/init",
                json={
                    "filename": "test.pdf",
                    "file_size_bytes": 10,
                    "file_type": "application/pdf",
                },
                headers={"X-Tenant-ID": "1"},
            )
            doc_id = init_res.json()["data"]["document_id"]

            chunk_res = client.post(
                "/api/v1/documents/upload/chunk",
                data={
                    "document_id": doc_id,
                    "chunk_index": "0",
                    "checksum": "wrong_checksum",
                },
                files={"chunk_data": ("chunk_0", b"data", "application/octet-stream")},
                headers={"X-Tenant-ID": "1"},
            )
            assert chunk_res.status_code == 400
            assert chunk_res.json()["error"]["code"] == "CHUNK_CHECKSUM_MISMATCH"
