import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models.base import Base, get_db
from app.models.design_document import DesignDocument
from app.models.document import Document
from app.models.generated_code_file import GeneratedCodeFile
from app.models.software_detailed_design import SoftwareDetailedDesign


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


class TestCodeGeneration:
    def _seed_doc_with_design_reviewed(self, test_db):
        """Seed a document with design_reviewed pipeline status."""
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="completed",
            pipeline_status="design_reviewed",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        test_db.add(doc)
        test_db.commit()
        test_db.refresh(doc)

        design = DesignDocument(
            tenant_id=1,
            document_id=doc.id,
            status="completed",
            asil_level="B",
            sections={
                "overview": {
                    "content": "Overview content",
                    "polarion_trace_id": "POL-DSGN-001",
                },
            },
        )
        test_db.add(design)
        test_db.commit()
        test_db.refresh(design)

        sdd = SoftwareDetailedDesign(
            tenant_id=1,
            document_id=doc.id,
            status="completed",
            project_number="PRJ-001",
            document_version="1.0",
            overview="Test module overview",
            fc_architecture='{"fc_modules": [{"module_name": "MockModule", "asil_level": "B"}]}',
            detailed_design='[{"function_name": "MockModule_Init", "return_type": "void", "parameters": []}]',
            safety_design="{}",
            verification_strategy="{}",
        )
        test_db.add(sdd)
        test_db.commit()
        test_db.refresh(sdd)

        return doc

    # ------------------------------------------------------------------
    # POST /code-generation
    # ------------------------------------------------------------------
    def test_trigger_code_generation_success(self, client, test_db):
        doc = self._seed_doc_with_design_reviewed(test_db)
        res = client.post(
            f"/api/v1/documents/{doc.id}/code-generation",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "code_generation_running"

        # BackgroundTasks in TestClient run synchronously but use a separate
        # SessionLocal bound to the production engine. We manually invoke
        # execute_generate with the test session to verify end-to-end logic.
        from app.services.code_generation_service import CodeGenerationService

        svc = CodeGenerationService(test_db)
        svc.execute_generate(1, doc.id)

        # Verify pipeline status updated
        test_db.refresh(doc)
        assert doc.pipeline_status == "code_generated"

        # Verify code files were generated
        files = (
            test_db.query(GeneratedCodeFile)
            .filter(
                GeneratedCodeFile.document_id == doc.id,
                GeneratedCodeFile.tenant_id == 1,
            )
            .all()
        )
        assert len(files) >= 2
        header_files = [f for f in files if f.file_type == "header"]
        source_files = [f for f in files if f.file_type == "source"]
        assert len(header_files) >= 1
        assert len(source_files) >= 1
        assert "#ifndef" in header_files[0].content
        assert '#include "' in source_files[0].content

        # Verify traceability and template version are embedded
        all_contents = " ".join([f.content for f in files])
        assert "/* TEMPLATE-VERSION:" in all_contents
        assert "/* TRACE-ID:" in all_contents
        assert "MCAL_SPI_READ" in all_contents or "McSpiReadFn" in all_contents

        # Verify new DB fields are populated
        assert files[0].template_version == "1.0.0"
        assert files[0].naming_convention == "mixed"
        assert files[0].polarion_trace_id is not None

        # Verify ASIL annotations and safety mechanisms are embedded
        assert "/* ASIL-LEVEL:" in all_contents
        assert "WDG_REFRESH" in all_contents or "SAFETY_MONITOR" in all_contents
        assert files[0].asil_level == "B"

    def test_trigger_code_generation_invalid_status(self, client, test_db):
        doc = Document(
            tenant_id=1,
            original_filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            upload_status="completed",
            parse_status="completed",
            pipeline_status="in_design",
            total_chunks=1,
            uploaded_chunks="[0]",
        )
        test_db.add(doc)
        test_db.commit()
        test_db.refresh(doc)

        res = client.post(
            f"/api/v1/documents/{doc.id}/code-generation",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 409
        assert "PIPELINE_STATUS_INVALID" in res.json()["error"]["code"]

    def test_trigger_code_generation_document_not_found(self, client):
        res = client.post(
            "/api/v1/documents/8e16dbb9-e991-4750-9030-bb3a00245e86/code-generation",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    # ------------------------------------------------------------------
    # GET /code-files
    # ------------------------------------------------------------------
    def test_get_code_files_success(self, client, test_db):
        doc = self._seed_doc_with_design_reviewed(test_db)
        # Trigger generation via API (validates endpoint)
        client.post(
            f"/api/v1/documents/{doc.id}/code-generation",
            headers={"X-Tenant-ID": "1"},
        )
        # Manually execute with test session to populate data
        from app.services.code_generation_service import CodeGenerationService

        svc = CodeGenerationService(test_db)
        svc.execute_generate(1, doc.id)

        res = client.get(
            f"/api/v1/documents/{doc.id}/code-files",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["document_id"] == doc.id
        assert len(data["files"]) >= 2
        for f in data["files"]:
            assert "template_version" in f
            assert "naming_convention" in f
            assert f["template_version"] is not None
            assert f["naming_convention"] is not None

    def test_get_code_files_document_not_found(self, client):
        res = client.get(
            "/api/v1/documents/8e16dbb9-e991-4750-9030-bb3a00245e86/code-files",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    # ------------------------------------------------------------------
    # GET /code-files/{file_id}
    # ------------------------------------------------------------------
    def test_get_code_file_by_id_success(self, client, test_db):
        doc = self._seed_doc_with_design_reviewed(test_db)
        # Trigger generation via API
        client.post(
            f"/api/v1/documents/{doc.id}/code-generation",
            headers={"X-Tenant-ID": "1"},
        )
        # Manually execute with test session to populate data
        from app.services.code_generation_service import CodeGenerationService

        svc = CodeGenerationService(test_db)
        svc.execute_generate(1, doc.id)

        # Get file list
        list_res = client.get(
            f"/api/v1/documents/{doc.id}/code-files",
            headers={"X-Tenant-ID": "1"},
        )
        file_id = list_res.json()["data"]["files"][0]["id"]

        res = client.get(
            f"/api/v1/documents/{doc.id}/code-files/{file_id}",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["id"] == file_id
        assert data["content"] is not None
        assert data["file_path"] is not None
        assert data["polarion_trace_id"] is not None
        assert data["template_version"] == "1.0.0"
        assert data["naming_convention"] == "mixed"
        assert data["asil_level"] == "B"

    def test_get_code_file_not_found(self, client, test_db):
        doc = self._seed_doc_with_design_reviewed(test_db)
        res = client.get(
            f"/api/v1/documents/{doc.id}/code-files/2c5ff810-c8b8-486e-abb8-4ace7556e79d",
            headers={"X-Tenant-ID": "1"},
        )
        assert res.status_code == 404
