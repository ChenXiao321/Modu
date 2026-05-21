import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.ocr_extraction_result import OcrExtractionResult
from app.repositories.ocr_result_repository import OcrResultRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestOcrResultRepository:
    def test_create_and_get_by_document(self, db_session):
        repo = OcrResultRepository(db_session)
        result = OcrExtractionResult(
            tenant_id=1,
            document_id="doc-1",
            field_id="OCR-FIELD-0001",
            extracted_text="4.5V",
            normalized_value="4.5",
            confidence=0.98,
            field_type="voltage",
            source_page=42,
            review_status="pending",
        )
        created = repo.create(result)
        assert created.id is not None
        assert created.field_id == "OCR-FIELD-0001"

        fields = repo.get_by_document("doc-1", 1)
        assert len(fields) == 1
        assert fields[0].confidence == 0.98

    def test_get_low_confidence_count(self, db_session):
        repo = OcrResultRepository(db_session)
        # High confidence
        repo.create(
            OcrExtractionResult(
                tenant_id=1,
                document_id="doc-2",
                field_id="OCR-FIELD-0001",
                extracted_text="4.5V",
                normalized_value="4.5",
                confidence=0.98,
                review_status="pending",
            )
        )
        # Low confidence, pending
        repo.create(
            OcrExtractionResult(
                tenant_id=1,
                document_id="doc-2",
                field_id="OCR-FIELD-0002",
                extracted_text="l00ms",
                normalized_value="100",
                confidence=0.72,
                review_status="pending",
            )
        )
        # Low confidence, but already confirmed
        repo.create(
            OcrExtractionResult(
                tenant_id=1,
                document_id="doc-2",
                field_id="OCR-FIELD-0003",
                extracted_text="3.3V",
                normalized_value="3.3",
                confidence=0.65,
                review_status="confirmed",
            )
        )

        count = repo.get_low_confidence_count("doc-2", 1, threshold=0.95)
        assert count == 1  # Only the pending low-confidence field

    def test_update_review_status(self, db_session):
        repo = OcrResultRepository(db_session)
        repo.create(
            OcrExtractionResult(
                tenant_id=1,
                document_id="doc-3",
                field_id="OCR-FIELD-0001",
                extracted_text="4.5V",
                normalized_value="4.5",
                confidence=0.72,
                review_status="pending",
            )
        )
        updated = repo.update_review_status("doc-3", 1, "OCR-FIELD-0001", "张三")
        assert updated is not None
        assert updated.review_status == "confirmed"
        assert updated.reviewed_by == "张三"
        assert updated.reviewed_at is not None

    def test_update_review_status_not_found(self, db_session):
        repo = OcrResultRepository(db_session)
        updated = repo.update_review_status("doc-missing", 1, "OCR-FIELD-9999", "张三")
        assert updated is None

    def test_delete_by_document(self, db_session):
        repo = OcrResultRepository(db_session)
        repo.create(
            OcrExtractionResult(
                tenant_id=1,
                document_id="doc-4",
                field_id="OCR-FIELD-0001",
                extracted_text="4.5V",
                normalized_value="4.5",
                confidence=0.98,
                review_status="pending",
            )
        )
        repo.create(
            OcrExtractionResult(
                tenant_id=1,
                document_id="doc-4",
                field_id="OCR-FIELD-0002",
                extracted_text="3.3V",
                normalized_value="3.3",
                confidence=0.91,
                review_status="pending",
            )
        )
        deleted = repo.delete_by_document("doc-4", 1)
        assert deleted == 2
        assert len(repo.get_by_document("doc-4", 1)) == 0

    def test_tenant_isolation(self, db_session):
        repo = OcrResultRepository(db_session)
        repo.create(
            OcrExtractionResult(
                tenant_id=1,
                document_id="doc-5",
                field_id="OCR-FIELD-0001",
                extracted_text="4.5V",
                normalized_value="4.5",
                confidence=0.98,
                review_status="pending",
            )
        )
        # Different tenant should not see the field
        fields = repo.get_by_document("doc-5", 2)
        assert len(fields) == 0
