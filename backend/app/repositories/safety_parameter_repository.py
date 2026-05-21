from typing import List

from sqlalchemy.orm import Session

from app.models.safety_critical_parameter import SafetyCriticalParameter


class SafetyParameterRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, parameter: SafetyCriticalParameter) -> SafetyCriticalParameter:
        self.db.add(parameter)
        self.db.commit()
        self.db.refresh(parameter)
        return parameter

    def get_by_document(self, document_id: str, tenant_id: int) -> List[SafetyCriticalParameter]:
        return (
            self.db.query(SafetyCriticalParameter)
            .filter(
                SafetyCriticalParameter.document_id == document_id,
                SafetyCriticalParameter.tenant_id == tenant_id,
            )
            .order_by(SafetyCriticalParameter.parameter_id)
            .all()
        )

    def delete_by_document(self, document_id: str, tenant_id: int) -> int:
        rows = (
            self.db.query(SafetyCriticalParameter)
            .filter(
                SafetyCriticalParameter.document_id == document_id,
                SafetyCriticalParameter.tenant_id == tenant_id,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return rows
