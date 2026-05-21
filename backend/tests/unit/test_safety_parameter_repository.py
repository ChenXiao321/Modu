import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.safety_critical_parameter import SafetyCriticalParameter
from app.repositories.safety_parameter_repository import SafetyParameterRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestSafetyParameterRepository:
    def test_create_and_get(self, db_session):
        repo = SafetyParameterRepository(db_session)
        param = SafetyCriticalParameter(
            tenant_id=1,
            document_id="doc-1",
            parameter_id="SW-REQ-SAF-001",
            name="供电电压阈值",
            value="4.5",
            unit="V",
            tolerance="±0.1",
            chapter="3.2.1",
            source_page=42,
        )
        created = repo.create(param)
        assert created.id is not None
        assert created.parameter_id == "SW-REQ-SAF-001"

        params = repo.get_by_document("doc-1", 1)
        assert len(params) == 1
        assert params[0].name == "供电电压阈值"

    def test_tenant_isolation(self, db_session):
        repo = SafetyParameterRepository(db_session)
        repo.create(
            SafetyCriticalParameter(
                tenant_id=1,
                document_id="doc-1",
                parameter_id="SW-REQ-SAF-001",
                name="电压",
                value="5",
                unit="V",
            )
        )
        repo.create(
            SafetyCriticalParameter(
                tenant_id=2,
                document_id="doc-1",
                parameter_id="SW-REQ-SAF-001",
                name="电压",
                value="5",
                unit="V",
            )
        )
        assert len(repo.get_by_document("doc-1", 1)) == 1
        assert len(repo.get_by_document("doc-1", 2)) == 1

    def test_delete_by_document(self, db_session):
        repo = SafetyParameterRepository(db_session)
        repo.create(
            SafetyCriticalParameter(
                tenant_id=1,
                document_id="doc-1",
                parameter_id="SW-REQ-SAF-001",
                name="电压",
                value="5",
                unit="V",
            )
        )
        repo.create(
            SafetyCriticalParameter(
                tenant_id=1,
                document_id="doc-1",
                parameter_id="SW-REQ-SAF-002",
                name="温度",
                value="150",
                unit="°C",
            )
        )
        deleted = repo.delete_by_document("doc-1", 1)
        assert deleted == 2
        assert len(repo.get_by_document("doc-1", 1)) == 0

    def test_order_by_parameter_id(self, db_session):
        repo = SafetyParameterRepository(db_session)
        repo.create(
            SafetyCriticalParameter(
                tenant_id=1,
                document_id="doc-1",
                parameter_id="SW-REQ-SAF-003",
                name="温度",
                value="150",
                unit="°C",
            )
        )
        repo.create(
            SafetyCriticalParameter(
                tenant_id=1,
                document_id="doc-1",
                parameter_id="SW-REQ-SAF-001",
                name="电压",
                value="5",
                unit="V",
            )
        )
        params = repo.get_by_document("doc-1", 1)
        assert params[0].parameter_id == "SW-REQ-SAF-001"
        assert params[1].parameter_id == "SW-REQ-SAF-003"
