import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models.base import Base, get_db
from app.models.design_document import DesignDocument
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


class TestDesignReviewRouter:
    def _seed_doc_and_design(self, test_db, pipeline_status="in_design", design_status="completed"):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="completed",
            pipeline_status=pipeline_status,
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        test_db.add(doc)
        test_db.commit()
        test_db.refresh(doc)

        design = DesignDocument(
            tenant_id=1,
            document_id=doc.id,
            status=design_status,
            asil_level="B",
            sections={
                "overview": {
                    "content": "Original overview",
                    "polarion_trace_id": "POL-DSGN-001",
                },
                "test_strategy": {
                    "content": "Test strategy content",
                    "polarion_trace_id": "POL-DSGN-002",
                },
            },
        )
        test_db.add(design)
        test_db.commit()
        test_db.refresh(design)
        return doc, design

    # ------------------------------------------------------------------
    # GET /design-review
    # ------------------------------------------------------------------
    def test_get_design_review_success(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db)
        res = client.get(
            f"/api/v1/documents/{doc.id}/design-review",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["document_id"] == doc.id
        assert data["pipeline_status"] == "in_design"
        assert data["pending_comments_count"] == 0
        assert data["design_document"]["status"] == "completed"

    def test_get_design_review_document_not_found(self, client):
        res = client.get(
            "/api/v1/documents/8e16dbb9-e991-4750-9030-bb3a00245e86/design-review",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    # ------------------------------------------------------------------
    # POST /design-revisions
    # ------------------------------------------------------------------
    def test_save_design_revision_success(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db)
        payload = {
            "section_key": "overview",
            "revised_content": "Revised overview content",
            "author": "张三",
        }
        res = client.post(
            f"/api/v1/documents/{doc.id}/design-revisions",
            json=payload,
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["section_key"] == "overview"
        assert data["original_content"] == "Original overview"
        assert data["revised_content"] == "Revised overview content"
        assert data["author"] == "张三"

    def test_save_design_revision_invalid_section(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db)
        payload = {
            "section_key": "invalid_section",
            "revised_content": "content",
            "author": "张三",
        }
        res = client.post(
            f"/api/v1/documents/{doc.id}/design-revisions",
            json=payload,
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 400
        assert "INVALID_SECTION_KEY" in res.json()["error"]["code"]

    def test_save_design_revision_design_not_completed(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db, design_status="running")
        payload = {
            "section_key": "overview",
            "revised_content": "content",
            "author": "张三",
        }
        res = client.post(
            f"/api/v1/documents/{doc.id}/design-revisions",
            json=payload,
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 409
        assert "DESIGN_DOCUMENT_NOT_READY" in res.json()["error"]["code"]

    # ------------------------------------------------------------------
    # GET /design-revisions
    # ------------------------------------------------------------------
    def test_get_design_revisions_success(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db)
        # Save two revisions
        payload1 = {
            "section_key": "overview",
            "revised_content": "Revision A",
            "author": "张三",
        }
        client.post(
            f"/api/v1/documents/{doc.id}/design-revisions",
            json=payload1,
            headers={"X-Tenant-ID": "1"},
        )
        payload2 = {
            "section_key": "overview",
            "revised_content": "Revision B",
            "author": "李四",
        }
        client.post(
            f"/api/v1/documents/{doc.id}/design-revisions",
            json=payload2,
            headers={"X-Tenant-ID": "1"},
        )

        res = client.get(
            f"/api/v1/documents/{doc.id}/design-revisions?section_key=overview",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["section_key"] == "overview"
        assert len(data["revisions"]) == 2
        assert data["revisions"][0]["revised_content"] == "Revision B"
        assert "--- original" in data["revisions"][0]["diff"]

    def test_get_design_revisions_invalid_section(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db)
        res = client.get(
            f"/api/v1/documents/{doc.id}/design-revisions?section_key=bad_section",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 400
        assert "INVALID_SECTION_KEY" in res.json()["error"]["code"]

    # ------------------------------------------------------------------
    # POST /review-comments
    # ------------------------------------------------------------------
    def test_add_review_comment_success(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db)
        payload = {
            "section_key": "overview",
            "comment_text": "建议补充时序图",
            "author": "张三",
        }
        res = client.post(
            f"/api/v1/documents/{doc.id}/review-comments",
            json=payload,
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["comment_text"] == "建议补充时序图"
        assert data["author"] == "张三"
        assert data["resolved_at"] is None

    def test_add_review_comment_invalid_section(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db)
        payload = {
            "section_key": "bad_key",
            "comment_text": "text",
            "author": "张三",
        }
        res = client.post(
            f"/api/v1/documents/{doc.id}/review-comments",
            json=payload,
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 400
        assert "INVALID_SECTION_KEY" in res.json()["error"]["code"]

    # ------------------------------------------------------------------
    # GET /review-comments
    # ------------------------------------------------------------------
    def test_get_review_comments_success(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db)
        # Add two comments to overview, one to test_strategy
        for text, section in [("C1", "overview"), ("C2", "overview"), ("C3", "test_strategy")]:
            client.post(
                f"/api/v1/documents/{doc.id}/review-comments",
                json={"section_key": section, "comment_text": text, "author": "张三"},
                headers={"X-Tenant-ID": "1"},
            )

        res = client.get(
            f"/api/v1/documents/{doc.id}/review-comments?section_key=overview",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["section_key"] == "overview"
        assert len(data["comments"]) == 2

    # ------------------------------------------------------------------
    # PATCH /review-comments/{comment_id}/resolve
    # ------------------------------------------------------------------
    def test_resolve_review_comment_success(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db)
        create_res = client.post(
            f"/api/v1/documents/{doc.id}/review-comments",
            json={"section_key": "overview", "comment_text": "建议", "author": "张三"},
            headers={"X-Tenant-ID": "1"},
        )
        comment_id = create_res.json()["data"]["id"]

        res = client.patch(
            f"/api/v1/documents/{doc.id}/review-comments/{comment_id}/resolve",
            json={"resolved_by": "李四"},
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["resolved_by"] == "李四"
        assert data["resolved_at"] is not None

    def test_resolve_review_comment_not_found(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db)
        res = client.patch(
            f"/api/v1/documents/{doc.id}/review-comments/2c5ff810-c8b8-486e-abb8-4ace7556e79d/resolve",
            json={"resolved_by": "李四"},
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 404
        assert "COMMENT_NOT_FOUND" in res.json()["error"]["code"]

    # ------------------------------------------------------------------
    # POST /design-review/submit
    # ------------------------------------------------------------------
    def test_submit_design_review_success(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db, pipeline_status="in_design")
        res = client.post(
            f"/api/v1/documents/{doc.id}/design-review/submit",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["pipeline_status"] == "design_reviewed"
        assert data["submitted_at"] is not None

    def test_submit_design_review_with_pending_comments_blocked(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db, pipeline_status="in_design")
        client.post(
            f"/api/v1/documents/{doc.id}/review-comments",
            json={"section_key": "overview", "comment_text": "未解决", "author": "张三"},
            headers={"X-Tenant-ID": "1"},
        )

        res = client.post(
            f"/api/v1/documents/{doc.id}/design-review/submit",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 409
        assert "PENDING_COMMENTS_EXIST" in res.json()["error"]["code"]

    def test_submit_design_review_invalid_pipeline_status(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db, pipeline_status="ready")
        res = client.post(
            f"/api/v1/documents/{doc.id}/design-review/submit",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 409
        assert "PIPELINE_STATUS_INVALID" in res.json()["error"]["code"]

    # ------------------------------------------------------------------
    # POST /design-revisions/{revision_id}/rollback
    # ------------------------------------------------------------------
    def test_rollback_to_revision_success(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db)
        save_res = client.post(
            f"/api/v1/documents/{doc.id}/design-revisions",
            json={"section_key": "overview", "revised_content": "Revised", "author": "张三"},
            headers={"X-Tenant-ID": "1"},
        )
        revision_id = save_res.json()["data"]["revision_id"]

        res = client.post(
            f"/api/v1/documents/{doc.id}/design-revisions/{revision_id}/rollback",
            json={"author": "李四"},
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["revised_content"] == "Original overview"
        assert data["original_content"] == "Revised"

    def test_rollback_to_revision_not_found(self, client, test_db):
        doc, design = self._seed_doc_and_design(test_db)
        res = client.post(
            f"/api/v1/documents/{doc.id}/design-revisions/2c5ff810-c8b8-486e-abb8-4ace7556e79d/rollback",
            json={"author": "李四"},
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 404
        assert "REVISION_NOT_FOUND" in res.json()["error"]["code"]

    # ------------------------------------------------------------------
    # Race-condition / concurrency scenarios
    # ------------------------------------------------------------------
    def test_rapid_double_submit_blocked(self, client, test_db):
        """Two rapid sequential submits: second must be rejected."""
        doc, design = self._seed_doc_and_design(test_db, pipeline_status="in_design")
        r1 = client.post(
            f"/api/v1/documents/{doc.id}/design-review/submit",
            headers={"X-Tenant-ID": "1"},
        )
        assert r1.status_code == 200
        assert r1.json()["data"]["pipeline_status"] == "design_reviewed"

        r2 = client.post(
            f"/api/v1/documents/{doc.id}/design-review/submit",
            headers={"X-Tenant-ID": "1"},
        )
        assert r2.status_code == 409
        err_code = r2.json()["error"]["code"]
        assert err_code in ("PIPELINE_STATUS_INVALID", "DESIGN_REVIEW_LOCKED")

    def test_rapid_revision_chain_consistency(self, client, test_db):
        """Rapid sequential saves must produce a correct original_content chain."""
        doc, design = self._seed_doc_and_design(test_db)
        for content in ["Rev A", "Rev B", "Rev C"]:
            res = client.post(
                f"/api/v1/documents/{doc.id}/design-revisions",
                json={"section_key": "overview", "revised_content": content, "author": "张三"},
                headers={"X-Tenant-ID": "1"},
            )
            assert res.status_code == 200

        res = client.get(
            f"/api/v1/documents/{doc.id}/design-revisions?section_key=overview",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        revisions = res.json()["data"]["revisions"]
        assert len(revisions) == 3
        # newest first
        assert revisions[0]["original_content"] == "Rev B"
        assert revisions[0]["revised_content"] == "Rev C"
        assert revisions[1]["original_content"] == "Rev A"
        assert revisions[1]["revised_content"] == "Rev B"
        assert revisions[2]["original_content"] == "Original overview"
        assert revisions[2]["revised_content"] == "Rev A"

    def test_resolve_already_resolved_comment_blocked(self, client, test_db):
        """Resolving an already-resolved comment must be rejected."""
        doc, design = self._seed_doc_and_design(test_db)
        create_res = client.post(
            f"/api/v1/documents/{doc.id}/review-comments",
            json={"section_key": "overview", "comment_text": "建议", "author": "张三"},
            headers={"X-Tenant-ID": "1"},
        )
        comment_id = create_res.json()["data"]["id"]

        r1 = client.patch(
            f"/api/v1/documents/{doc.id}/review-comments/{comment_id}/resolve",
            json={"resolved_by": "李四"},
            headers={"X-Tenant-ID": "1"},
        )
        assert r1.status_code == 200

        r2 = client.patch(
            f"/api/v1/documents/{doc.id}/review-comments/{comment_id}/resolve",
            json={"resolved_by": "王五"},
            headers={"X-Tenant-ID": "1"},
        )
        assert r2.status_code == 409
        assert r2.json()["error"]["code"] == "COMMENT_ALREADY_RESOLVED"
