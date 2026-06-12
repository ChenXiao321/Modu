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
from app.services.document_service import _compute_chunk_checksum


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(test_db):
    from app.models.document import Document
    assert "parse_status" in {c.name for c in Document.__table__.columns}

    app = create_app()

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=test_db.bind)
    Base.metadata.create_all(bind=test_db.bind)
    return TestClient(app)


class TestParseFlow:
    def test_trigger_parse_and_get_status(self, client, test_db):
        with patch("app.services.document_service._get_chunks_path") as mock_chunks, \
             patch("app.services.document_service._get_document_path") as mock_docs:
            chunks_dir = Path(tempfile.mkdtemp())
            docs_dir = Path(tempfile.mkdtemp())
            mock_chunks.return_value = chunks_dir
            mock_docs.return_value = docs_dir

            # Upload a small txt file
            init_res = client.post(
                "/api/v1/documents/upload/init",
                json={
                    "filename": "test.txt",
                    "file_size_bytes": 10,
                    "file_type": "text/plain",
                },
                headers={"X-Tenant-ID": "1"},
            )
            doc_id = init_res.json()["data"]["document_id"]

            chunk_data = b"A" * 10
            checksum = _compute_chunk_checksum(chunk_data)
            client.post(
                "/api/v1/documents/upload/chunk",
                data={
                    "document_id": doc_id,
                    "chunk_index": "0",
                    "checksum": checksum,
                },
                files={"chunk_data": ("chunk_0", chunk_data, "application/octet-stream")},
                headers={"X-Tenant-ID": "1"},
            )

            sha256 = hashlib.sha256(chunk_data).hexdigest()
            client.post(
                "/api/v1/documents/upload/complete",
                json={
                    "document_id": doc_id,
                    "total_chunks": 1,
                    "sha256": sha256,
                },
                headers={"X-Tenant-ID": "1"},
            )

            # Trigger parse — mock background task to avoid connecting to modu.db
            with patch("app.tasks.parse_document._run_parse"):
                parse_res = client.post(
                    f"/api/v1/documents/{doc_id}/parse",
                    headers={"X-Tenant-ID": "1"},
                )
                assert parse_res.status_code == 200
                assert parse_res.json()["data"]["status"] == "queued"

            # Manually set parse_status to completed for status and requirements tests
            from app.repositories.document_repository import DocumentRepository
            doc_repo = DocumentRepository(test_db)
            doc_repo.update_parse_status(doc_id, 1, "completed")

            # Query parse status
            status_res = client.get(
                f"/api/v1/documents/{doc_id}/parse/status",
                headers={"X-Tenant-ID": "1"},
            )
            assert status_res.status_code == 200
            assert status_res.json()["data"]["status"] == "completed"

            # Query requirements
            reqs_res = client.get(
                f"/api/v1/documents/{doc_id}/requirements",
                headers={"X-Tenant-ID": "1"},
            )
            assert reqs_res.status_code == 200
            assert reqs_res.json()["data"]["requirements"] == []

    def test_parse_nonexistent_document(self, client):
        res = client.post(
            "/api/v1/documents/2c5ff810-c8b8-486e-abb8-4ace7556e79d/parse",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    def test_list_documents(self, client):
        res = client.get(
            "/api/v1/documents",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        assert "items" in res.json()["data"]
