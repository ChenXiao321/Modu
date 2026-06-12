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


class TestSafetyParametersIntegration:
    def test_get_safety_parameters_document_not_found(self, client, test_db):
        response = client.get(
            "/api/v1/documents/2c5ff810-c8b8-486e-abb8-4ace7556e79d/safety-parameters", headers={"X-Tenant-ID": "1"}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "DOCUMENT_NOT_FOUND"

    def test_get_safety_parameters_empty(self, client, test_db):
        # Create a document with completed parse status
        doc = Document(
            id="doc-1",
            tenant_id=1,
            original_filename="test.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            upload_status="completed",
            parse_status="completed",
        )
        test_db.add(doc)
        test_db.commit()

        response = client.get("/api/v1/documents/doc-1/safety-parameters", headers={"X-Tenant-ID": "1"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["parameters"] == []

    def test_get_safety_parameters_format(self, client, test_db):
        doc = Document(
            id="doc-2",
            tenant_id=1,
            original_filename="test.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            upload_status="completed",
            parse_status="completed",
        )
        test_db.add(doc)
        test_db.commit()

        from app.repositories.safety_parameter_repository import SafetyParameterRepository
        from app.models.safety_critical_parameter import SafetyCriticalParameter

        repo = SafetyParameterRepository(test_db)
        repo.create(
            SafetyCriticalParameter(
                tenant_id=1,
                document_id="doc-2",
                parameter_id="SW-REQ-SAF-001",
                name="供电电压阈值",
                value="4.5",
                unit="V",
                tolerance="±0.1",
                chapter="3.2.1",
                source_page=42,
            )
        )

        response = client.get("/api/v1/documents/doc-2/safety-parameters", headers={"X-Tenant-ID": "1"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        params = data["data"]["parameters"]
        assert isinstance(params, list)
        assert len(params) == 1
        assert params[0]["parameter_id"] == "SW-REQ-SAF-001"
        assert params[0]["name"] == "供电电压阈值"
        assert params[0]["value"] == "4.5"
        assert params[0]["unit"] == "V"
        assert params[0]["tolerance"] == "±0.1"
        assert params[0]["chapter"] == "3.2.1"
        assert params[0]["source_page"] == 42
