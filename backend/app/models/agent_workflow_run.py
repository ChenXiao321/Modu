"""Database model for Agent workflow execution state."""

import uuid

from sqlalchemy import Column, Integer, String, Text

from app.models.base import Base, TenantMixin, TimestampMixin


class AgentWorkflowRun(Base, TenantMixin, TimestampMixin):
    __tablename__ = "agent_workflow_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending")
    current_step = Column(Integer, nullable=False, default=0)
    steps_data = Column(Text, nullable=False, default="{}")
    parse_task_id = Column(String(100), nullable=True)
