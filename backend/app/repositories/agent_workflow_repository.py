"""Repository for AgentWorkflowRun persistence."""

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_workflow_run import AgentWorkflowRun

logger = logging.getLogger(__name__)


class AgentWorkflowRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        tenant_id: int,
        document_id: str,
        parse_task_id: str | None = None,
    ) -> AgentWorkflowRun:
        run = AgentWorkflowRun(
            tenant_id=tenant_id,
            document_id=document_id,
            status="pending",
            current_step=0,
            steps_data="{}",
            parse_task_id=parse_task_id,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_by_document(
        self,
        document_id: str,
        tenant_id: int,
    ) -> AgentWorkflowRun | None:
        return (
            self.db.query(AgentWorkflowRun)
            .filter(
                AgentWorkflowRun.document_id == document_id,
                AgentWorkflowRun.tenant_id == tenant_id,
            )
            .first()
        )

    def update_status(
        self,
        run_id: str,
        tenant_id: int,
        status: str,
        current_step: int | None = None,
    ) -> None:
        run = (
            self.db.query(AgentWorkflowRun)
            .filter(
                AgentWorkflowRun.id == run_id,
                AgentWorkflowRun.tenant_id == tenant_id,
            )
            .first()
        )
        if run is None:
            logger.warning("AgentWorkflowRun %s not found for status update", run_id)
            return
        run.status = status
        if current_step is not None:
            run.current_step = current_step
        self.db.commit()

    def update_steps_data(
        self,
        run_id: str,
        tenant_id: int,
        steps_data: dict[str, Any],
    ) -> None:
        run = (
            self.db.query(AgentWorkflowRun)
            .filter(
                AgentWorkflowRun.id == run_id,
                AgentWorkflowRun.tenant_id == tenant_id,
            )
            .first()
        )
        if run is None:
            logger.warning("AgentWorkflowRun %s not found for steps_data update", run_id)
            return
        run.steps_data = json.dumps(steps_data, ensure_ascii=False)
        self.db.commit()

    def get_steps_data(
        self,
        run_id: str,
        tenant_id: int,
    ) -> dict[str, Any]:
        run = (
            self.db.query(AgentWorkflowRun)
            .filter(
                AgentWorkflowRun.id == run_id,
                AgentWorkflowRun.tenant_id == tenant_id,
            )
            .first()
        )
        if run is None:
            return {}
        try:
            return json.loads(run.steps_data)
        except json.JSONDecodeError:
            logger.error("Failed to parse steps_data JSON for run %s", run_id)
            return {}
