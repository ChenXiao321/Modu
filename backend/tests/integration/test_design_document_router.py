from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models.base import Base, get_db
from app.models.document import Document


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


class TestDesignDocumentEndpoints:
    def _seed_document(self, test_db, parse_status="completed", pipeline_status="ready", block_reason=None):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status=parse_status,
            pipeline_status=pipeline_status,
            block_reason=block_reason,
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        test_db.add(doc)
        test_db.commit()
        test_db.refresh(doc)
        return doc

    def test_trigger_design_document_success(self, client, test_db):
        doc = self._seed_document(test_db)
        with patch("app.tasks.generate_design_document._run_generate"):
            res = client.post(
                f"/api/v1/documents/{doc.id}/design",
                headers={"X-Tenant-ID": "1"},
            )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["document_id"] == doc.id
        assert data["status"] == "running"
        assert data["design_task_id"] is not None

    def test_trigger_design_document_not_found(self, client):
        res = client.post(
            "/api/v1/documents/8e16dbb9-e991-4750-9030-bb3a00245e86/design",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    def test_trigger_design_document_parse_not_completed(self, client, test_db):
        doc = self._seed_document(test_db, parse_status="pending")
        res = client.post(
            f"/api/v1/documents/{doc.id}/design",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 409
        assert "解析尚未完成" in res.json()["error"]["message"]

    def test_trigger_design_document_parse_failed(self, client, test_db):
        doc = self._seed_document(test_db, parse_status="failed")
        res = client.post(
            f"/api/v1/documents/{doc.id}/design",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 409
        assert "解析失败" in res.json()["error"]["message"]

    def test_trigger_design_document_pipeline_blocked(self, client, test_db):
        doc = self._seed_document(test_db, pipeline_status="blocked", block_reason="OCR low confidence")
        res = client.post(
            f"/api/v1/documents/{doc.id}/design",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "PIPELINE_BLOCKED"

    def test_trigger_design_document_already_running(self, client, test_db):
        doc = self._seed_document(test_db)
        # Seed a running design doc
        from app.models.design_document import DesignDocument
        design = DesignDocument(
            tenant_id=1,
            document_id=doc.id,
            status="running",
        )
        test_db.add(design)
        test_db.commit()

        res = client.post(
            f"/api/v1/documents/{doc.id}/design",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 409
        assert "已在进行中" in res.json()["error"]["message"]

    def test_get_design_document_pending(self, client, test_db):
        doc = self._seed_document(test_db)
        res = client.get(
            f"/api/v1/documents/{doc.id}/design",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["document_id"] == doc.id
        assert data["status"] == "pending"
        assert data["sections"] is None

    def test_get_design_document_completed(self, client, test_db):
        doc = self._seed_document(test_db, pipeline_status="in_design")
        from app.models.design_document import DesignDocument
        design = DesignDocument(
            tenant_id=1,
            document_id=doc.id,
            status="completed",
            asil_level="C",
            sections={
                "overview": {
                    "content": "Overview content",
                    "polarion_trace_id": "POL-DSGN-001",
                }
            },
        )
        test_db.add(design)
        test_db.commit()

        res = client.get(
            f"/api/v1/documents/{doc.id}/design",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "completed"
        assert data["asil_level"] == "C"
        assert data["sections"]["overview"]["content"] == "Overview content"

    def test_get_design_document_not_found(self, client):
        res = client.get(
            "/api/v1/documents/8e16dbb9-e991-4750-9030-bb3a00245e86/design",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
