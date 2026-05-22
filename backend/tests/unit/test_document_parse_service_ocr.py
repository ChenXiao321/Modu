import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.document import Document
from app.models.ocr_extraction_result import OcrExtractionResult
from app.exceptions import FieldNotFoundError, PipelineNotBlockedError
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
def ocr_doc(test_db: Session):
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


@pytest.fixture
def non_ocr_doc(test_db: Session):
    doc = Document(
        tenant_id=1,
        original_filename="spec.docx",
        file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_size_bytes=1024,
        upload_status="completed",
        storage_path="/data/uploads/spec.docx",
        parse_status="running",
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)
    return doc


class TestIsOcrDocument:
    def test_pdf_detected_as_ocr(self, test_db: Session, ocr_doc: Document):
        svc = DocumentParseService(test_db)
        assert svc._is_ocr_document(ocr_doc) is True

    def test_word_not_ocr(self, test_db: Session, non_ocr_doc: Document):
        svc = DocumentParseService(test_db)
        assert svc._is_ocr_document(non_ocr_doc) is False

    def test_manual_override_true(self, test_db: Session, ocr_doc: Document):
        ocr_doc.is_scan_document = "true"
        test_db.commit()
        svc = DocumentParseService(test_db)
        assert svc._is_ocr_document(ocr_doc) is True

    def test_manual_override_false(self, test_db: Session, ocr_doc: Document):
        ocr_doc.is_scan_document = "false"
        test_db.commit()
        svc = DocumentParseService(test_db)
        assert svc._is_ocr_document(ocr_doc) is False

    def test_image_by_extension(self, test_db: Session):
        doc = Document(
            tenant_id=1,
            original_filename="photo.jpg",
            file_type="image/jpeg",
            file_size_bytes=1024,
            upload_status="completed",
        )
        test_db.add(doc)
        test_db.commit()
        svc = DocumentParseService(test_db)
        assert svc._is_ocr_document(doc) is True


class TestPersistOcrResults:
    def test_enforces_field_id_format(self, test_db: Session, ocr_doc: Document):
        svc = DocumentParseService(test_db)
        raw = [
            {"field_id": "ANY", "extracted_text": "4.5V", "confidence": 0.98},
            {"field_id": "THING", "extracted_text": "3.3V", "confidence": 0.91},
        ]
        svc._persist_ocr_results(1, ocr_doc.id, raw)

        results = (
            test_db.query(OcrExtractionResult)
            .filter(OcrExtractionResult.document_id == ocr_doc.id)
            .order_by(OcrExtractionResult.field_id)
            .all()
        )
        assert len(results) == 2
        assert results[0].field_id == "OCR-FIELD-0001"
        assert results[1].field_id == "OCR-FIELD-0002"

    def test_rejects_invalid_confidence(self, test_db: Session, ocr_doc: Document):
        svc = DocumentParseService(test_db)
        raw = [{"extracted_text": "x", "confidence": 1.5}]
        with pytest.raises(ValueError, match="confidence"):
            svc._persist_ocr_results(1, ocr_doc.id, raw)

    def test_rejects_empty_extracted_text(self, test_db: Session, ocr_doc: Document):
        svc = DocumentParseService(test_db)
        raw = [{"extracted_text": "  ", "confidence": 0.9}]
        with pytest.raises(ValueError, match="extracted_text"):
            svc._persist_ocr_results(1, ocr_doc.id, raw)


class TestUpdatePipelineBlockStatus:
    def test_ocr_document_with_low_confidence_blocked(self, test_db: Session, ocr_doc: Document):
        svc = DocumentParseService(test_db)
        with patch("app.services.document_parse_service.TextExtractor.extract") as mock_extract:
            mock_extract.return_value = "Sample OCR text with voltage 4.5V"
            svc.execute_parse(1, ocr_doc.id)

        test_db.refresh(ocr_doc)
        assert ocr_doc.pipeline_status == "blocked"
        assert "低置信度" in (ocr_doc.block_reason or "")

    def test_non_ocr_document_ready(self, test_db: Session, non_ocr_doc: Document):
        svc = DocumentParseService(test_db)
        with patch("app.services.document_parse_service.TextExtractor.extract") as mock_extract:
            mock_extract.return_value = "Some requirements text"
            svc.execute_parse(1, non_ocr_doc.id)

        test_db.refresh(non_ocr_doc)
        assert non_ocr_doc.pipeline_status == "ready"

    def test_in_design_protected(self, test_db: Session, ocr_doc: Document):
        ocr_doc.pipeline_status = "in_design"
        test_db.commit()
        svc = DocumentParseService(test_db)
        svc._update_pipeline_block_status(1, ocr_doc.id)
        test_db.refresh(ocr_doc)
        assert ocr_doc.pipeline_status == "in_design"


class TestConfirmLowConfidenceField:
    def test_confirm_unblocks_pipeline(self, test_db: Session, ocr_doc: Document):
        svc = DocumentParseService(test_db)
        with patch("app.services.document_parse_service.TextExtractor.extract") as mock_extract:
            mock_extract.return_value = "Sample OCR text with voltage 4.5V"
            svc.execute_parse(1, ocr_doc.id)

        res = svc.get_ocr_results(1, ocr_doc.id)
        low_conf = next(f for f in res["fields"] if f["confidence"] < 0.95)

        result = svc.confirm_low_confidence_field(1, ocr_doc.id, low_conf["field_id"], "张三")
        assert result["review_status"] == "confirmed"
        assert result["reviewed_by"] == "张三"

    def test_confirm_requires_blocked_status(self, test_db: Session, ocr_doc: Document):
        svc = DocumentParseService(test_db)
        ocr_doc.pipeline_status = "ready"
        test_db.commit()

        with pytest.raises(PipelineNotBlockedError):
            svc.confirm_low_confidence_field(1, ocr_doc.id, "OCR-FIELD-0001", "张三")

    def test_confirm_nonexistent_field(self, test_db: Session, ocr_doc: Document):
        svc = DocumentParseService(test_db)
        ocr_doc.pipeline_status = "blocked"
        test_db.commit()

        with pytest.raises(FieldNotFoundError):
            svc.confirm_low_confidence_field(1, ocr_doc.id, "OCR-FIELD-9999", "张三")


class TestGetOcrResults:
    def test_running_returns_empty(self, test_db: Session, ocr_doc: Document):
        svc = DocumentParseService(test_db)
        ocr_doc.parse_status = "running"
        test_db.commit()
        res = svc.get_ocr_results(1, ocr_doc.id)
        assert res["fields"] == []

    def test_failed_returns_empty(self, test_db: Session, ocr_doc: Document):
        svc = DocumentParseService(test_db)
        ocr_doc.parse_status = "failed"
        test_db.commit()
        res = svc.get_ocr_results(1, ocr_doc.id)
        assert res["fields"] == []

    def test_completed_returns_fields(self, test_db: Session, ocr_doc: Document):
        svc = DocumentParseService(test_db)
        with patch("app.services.document_parse_service.TextExtractor.extract") as mock_extract:
            mock_extract.return_value = "Sample OCR text with voltage 4.5V"
            svc.execute_parse(1, ocr_doc.id)

        res = svc.get_ocr_results(1, ocr_doc.id)
        assert len(res["fields"]) > 0
