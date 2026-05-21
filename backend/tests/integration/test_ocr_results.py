import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.main import create_app
from app.models.base import Base, get_db
from app.models.document import Document
from app.services.document_parse_service import DocumentParseService


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


@pytest.fixture
def ocr_document(test_db: Session):
    doc = Document(
        tenant_id=1,
        original_filename="scan_test.pdf",
        file_type="application/pdf",
        file_size_bytes=1024,
        upload_status="completed",
        storage_path="/data/uploads/scan_test.pdf",
        parse_status="running",
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)
    return doc


class TestOcrResultsEndpoint:
    def test_get_ocr_results_success(self, client, ocr_document: Document, test_db: Session):
        svc = DocumentParseService(test_db)
        with patch("app.services.document_parse_service.TextExtractor.extract") as mock_extract:
            mock_extract.return_value = "Sample OCR text with voltage 4.5V"
            svc.execute_parse(1, ocr_document.id)

        res = client.get(f"/api/v1/documents/{ocr_document.id}/ocr-results")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "fields" in data
        assert "pipeline_status" in data
        assert len(data["fields"]) > 0
        assert all("confidence" in f for f in data["fields"])

    def test_get_ocr_results_not_found(self, client):
        res = client.get("/api/v1/documents/nonexistent/ocr-results")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    def test_get_ocr_results_not_parsed(self, client, ocr_document: Document):
        res = client.get(f"/api/v1/documents/{ocr_document.id}/ocr-results")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["fields"] == []

    def test_confirm_field_success(self, client, ocr_document: Document, test_db: Session):
        svc = DocumentParseService(test_db)
        with patch("app.services.document_parse_service.TextExtractor.extract") as mock_extract:
            mock_extract.return_value = "Sample OCR text with voltage 4.5V"
            svc.execute_parse(1, ocr_document.id)

        res = client.get(f"/api/v1/documents/{ocr_document.id}/ocr-results")
        field = next(
            f for f in res.json()["data"]["fields"] if f["confidence"] < 0.95
        )

        confirm_res = client.post(
            f"/api/v1/documents/{ocr_document.id}/ocr-fields/{field['field_id']}/confirm",
            json={"reviewer_name": "张三"},
        )
        assert confirm_res.status_code == 200
        data = confirm_res.json()["data"]
        assert data["review_status"] == "confirmed"
        assert data["reviewed_by"] == "张三"
        assert data["pipeline_status"] == "ready"
        assert data["all_confirmed"] is True

    def test_confirm_field_not_found(self, client, ocr_document: Document, test_db: Session):
        svc = DocumentParseService(test_db)
        with patch("app.services.document_parse_service.TextExtractor.extract") as mock_extract:
            mock_extract.return_value = "Sample OCR text"
            svc.execute_parse(1, ocr_document.id)

        res = client.post(
            f"/api/v1/documents/{ocr_document.id}/ocr-fields/OCR-FIELD-9999/confirm",
            json={"reviewer_name": "张三"},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "FIELD_NOT_FOUND"

    def test_confirm_field_already_confirmed(self, client, ocr_document: Document, test_db: Session):
        svc = DocumentParseService(test_db)
        with patch("app.services.document_parse_service.TextExtractor.extract") as mock_extract:
            mock_extract.return_value = "Sample OCR text with voltage 4.5V"
            svc.execute_parse(1, ocr_document.id)

        res = client.get(f"/api/v1/documents/{ocr_document.id}/ocr-results")
        field = next(
            f for f in res.json()["data"]["fields"] if f["confidence"] < 0.95
        )

        client.post(
            f"/api/v1/documents/{ocr_document.id}/ocr-fields/{field['field_id']}/confirm",
            json={"reviewer_name": "张三"},
        )
        res2 = client.post(
            f"/api/v1/documents/{ocr_document.id}/ocr-fields/{field['field_id']}/confirm",
            json={"reviewer_name": "李四"},
        )
        assert res2.status_code == 409
        assert res2.json()["error"]["code"] == "FIELD_ALREADY_CONFIRMED"

    def test_parse_status_includes_pipeline_status(self, client, ocr_document: Document, test_db: Session):
        svc = DocumentParseService(test_db)
        with patch("app.services.document_parse_service.TextExtractor.extract") as mock_extract:
            mock_extract.return_value = "Sample OCR text"
            svc.execute_parse(1, ocr_document.id)

        res = client.get(f"/api/v1/documents/{ocr_document.id}/parse/status")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "pipeline_status" in data
        assert "block_reason" in data

    def test_pipeline_unblocked_after_all_confirmed(self, client, ocr_document: Document, test_db: Session):
        svc = DocumentParseService(test_db)
        with patch("app.services.document_parse_service.TextExtractor.extract") as mock_extract:
            mock_extract.return_value = "Sample OCR text with voltage 4.5V"
            svc.execute_parse(1, ocr_document.id)

        while True:
            res = client.get(f"/api/v1/documents/{ocr_document.id}/ocr-results")
            data = res.json()["data"]
            if data["pipeline_status"] != "blocked":
                break
            low_conf = next(
                f for f in data["fields"]
                if f["confidence"] < 0.95 and f["review_status"] == "pending"
            )
            client.post(
                f"/api/v1/documents/{ocr_document.id}/ocr-fields/{low_conf['field_id']}/confirm",
                json={"reviewer_name": "工程师"},
            )

        final = client.get(f"/api/v1/documents/{ocr_document.id}/ocr-results")
        assert final.json()["data"]["pipeline_status"] == "ready"
