import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.agent.steps import build_design_steps
from app.agent.workflow import AgentWorkflowEngine, WorkflowContext, WorkflowFailedError
from app.config import settings
from app.exceptions import (
    DesignReviewLockedError,
    DocumentNotFoundError,
    DocumentNotReadyError,
    PipelineBlockedError,
)
from app.integrations.llm_client import LiteLLMClient, LLMClient, MockLLMClient
from app.models.design_document import DesignDocument
from app.repositories.design_document_repository import DesignDocumentRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.fc_requirement_repository import FcRequirementRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.safety_parameter_repository import SafetyParameterRepository
from app.repositories.software_detailed_design_repository import SoftwareDetailedDesignRepository

logger = logging.getLogger(__name__)

_ASIL_ORDER = {"A": 1, "B": 2, "C": 3, "D": 4}
_MAX_TREE_DEPTH = 10
_TIMEOUT_MINUTES = 10


class DesignDocumentService:
    def __init__(self, db: Session, llm_client: LLMClient | None = None) -> None:
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.design_repo = DesignDocumentRepository(db)
        self.req_repo = RequirementRepository(db)
        self.safety_repo = SafetyParameterRepository(db)
        self.fc_repo = FcRequirementRepository(db)
        self.sdd_repo = SoftwareDetailedDesignRepository(db)
        self.llm_client: LLMClient
        if llm_client is not None:
            self.llm_client = llm_client
        elif settings.llm_provider == "litellm":
            self.llm_client = LiteLLMClient(
                model=settings.llm_model,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url or None,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
        else:
            self.llm_client = MockLLMClient()

    def trigger_generate(self, tenant_id: int, document_id: str) -> dict:
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)
        if doc.parse_status == "failed":
            raise DocumentNotReadyError(document_id, "文档解析失败，无法生成设计文档")
        if doc.parse_status != "completed":
            raise DocumentNotReadyError(document_id, "文档解析尚未完成")
        if doc.pipeline_status == "blocked":
            raise PipelineBlockedError(
                document_id, doc.block_reason or "流水线存在阻塞项未解除"
            )
        if doc.pipeline_status == "design_reviewed":
            raise DesignReviewLockedError(document_id)

        existing = (
            self.db.query(DesignDocument)
            .filter(
                DesignDocument.document_id == document_id,
                DesignDocument.tenant_id == tenant_id,
            )
            .with_for_update()
            .first()
        )
        if existing is not None and existing.status == "running":
            raise DocumentNotReadyError(document_id, "设计文档生成任务已在进行中")

        if existing is not None:
            existing.status = "running"
            existing.sections = None
            existing.asil_level = None
            existing.error_message = None
            self.db.commit()
            self.db.refresh(existing)
            design_task_id = existing.id
        else:
            design_task_id = str(uuid.uuid4())
            design_doc = DesignDocument(
                id=design_task_id,
                tenant_id=tenant_id,
                document_id=document_id,
                status="running",
            )
            self.design_repo.add(design_doc)
            self.db.commit()
            self.db.refresh(design_doc)

        # Ensure SoftwareDetailedDesign record exists for Agent workflow output
        sdd = self.sdd_repo.get_by_document(document_id, tenant_id)
        if sdd is not None:
            self.sdd_repo.delete_by_document(document_id, tenant_id)
        self.sdd_repo.create(
            tenant_id=tenant_id,
            document_id=document_id,
            design_task_id=design_task_id,
        )

        return {
            "document_id": document_id,
            "design_task_id": design_task_id,
            "status": "running",
        }

    def execute_generate(self, tenant_id: int, document_id: str) -> None:
        """Synchronous design document generation via Agent workflow."""
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            logger.warning("Design generation aborted: document %s not found", document_id)
            return
        if doc.parse_status != "completed":
            logger.warning(
                "Design generation aborted: document %s parse_status=%s",
                document_id,
                doc.parse_status,
            )
            self._mark_failed(document_id, tenant_id, "文档解析尚未完成")
            return
        if doc.pipeline_status == "blocked":
            logger.warning(
                "Design generation aborted: document %s pipeline blocked", document_id
            )
            self._mark_failed(
                document_id, tenant_id, f"流水线阻塞: {doc.block_reason}"
            )
            return

        try:
            # Load FC requirement specification as input to design agent
            fc_doc = self.fc_repo.get_by_document(document_id, tenant_id)
            if fc_doc is None:
                raise ValueError("FC 需求规范不存在，无法生成设计文档")
            fc_spec = self.fc_repo.to_dict(fc_doc)
            fc_text = json.dumps(fc_spec, ensure_ascii=False, indent=2)

            # Run 2-step design agent workflow
            design_data = self._execute_design_agent_workflow(
                tenant_id, document_id, fc_text, doc.original_filename
            )

            # Persist Agent output to software_detailed_design
            asil_level = self._resolve_asil_from_design(design_data)
            self.sdd_repo.update_status(
                document_id,
                tenant_id,
                "completed",
                design_data=design_data,
            )

            # Build legacy-compatible sections for frontend
            legacy_sections = self._build_legacy_sections(design_data)

            self.design_repo.update_status(
                document_id,
                tenant_id,
                "completed",
                sections=legacy_sections,
                asil_level=asil_level,
            )

            # Transition pipeline to in_design phase
            doc.pipeline_status = "in_design"
            doc.block_reason = None
            self.db.commit()
            self.db.refresh(doc)

            logger.info("Design document generation completed for document %s", document_id)
        except Exception as exc:
            logger.exception("Design document generation failed for document %s", document_id)
            error_msg = str(exc) if str(exc) else "设计文档生成过程中发生未知错误"
            self._mark_failed(document_id, tenant_id, error_msg)
            # Rollback pipeline status if it was promoted to in_design during a re-trigger
            doc = self.doc_repo.get_by_id(document_id, tenant_id)
            if doc is not None and doc.pipeline_status == "in_design":
                doc.pipeline_status = "ready"
                doc.block_reason = None
                self.db.commit()
                self.db.refresh(doc)

    def _execute_design_agent_workflow(
        self,
        tenant_id: int,
        document_id: str,
        document_text: str,
        filename: str,
    ) -> dict:
        """Run the 2-step design agent workflow and return the detailed design data."""
        template_dir = Path(__file__).parent.parent / "agent" / "prompts"
        steps = build_design_steps(template_dir)

        context = WorkflowContext(
            document_text=document_text,
            filename=filename,
            tenant_id=tenant_id,
            document_id=document_id,
        )

        engine = AgentWorkflowEngine(
            steps=steps,
            llm_client=self.llm_client,
        )

        result = engine.run(context)

        detail_record = result.get("design_02_detailed_design")
        if detail_record is None or detail_record.output is None:
            raise WorkflowFailedError("design_02_detailed_design did not produce output")

        design_data = detail_record.output
        if not isinstance(design_data, dict):
            raise WorkflowFailedError("design_02_detailed_design output is not a dict")

        return design_data

    def _build_legacy_sections(self, design_data: dict) -> dict:
        """Convert new Agent output format to legacy DesignDocument.sections format."""
        base_trace = "POL-DSGN-001"
        overview = design_data.get("overview", "")
        fc_arch = design_data.get("fc_architecture")
        detail = design_data.get("detailed_design")
        safety = design_data.get("safety_design")
        verify = design_data.get("verification_strategy")

        return {
            "overview": {
                "content": overview,
                "polarion_trace_id": f"{base_trace}-001",
            },
            "references": {
                "content": f"Project: {design_data.get('project_number', '')}\nVersion: {design_data.get('document_version', '')}",
                "polarion_trace_id": f"{base_trace}-002",
            },
            "system_architecture": {
                "content": json.dumps(fc_arch, ensure_ascii=False, indent=2) if fc_arch else "",
                "polarion_trace_id": f"{base_trace}-003",
            },
            "interface_definition": {
                "content": json.dumps(detail, ensure_ascii=False, indent=2) if detail else "",
                "polarion_trace_id": f"{base_trace}-004",
            },
            "dynamic_behavior": {
                "content": "See system architecture for state machines and call graphs.",
                "polarion_trace_id": f"{base_trace}-005",
            },
            "resource_consumption": {
                "content": "See detailed design for resource estimates.",
                "polarion_trace_id": f"{base_trace}-006",
            },
            "error_handling": {
                "content": json.dumps(safety, ensure_ascii=False, indent=2) if safety else "",
                "polarion_trace_id": f"{base_trace}-007",
            },
            "test_strategy": {
                "content": json.dumps(verify, ensure_ascii=False, indent=2) if verify else "",
                "polarion_trace_id": f"{base_trace}-008",
            },
        }

    def _resolve_asil_from_design(self, design_data: dict) -> str:
        """Extract highest ASIL from FC modules in design output."""
        fc_arch = design_data.get("fc_architecture") or {}
        modules = fc_arch.get("fc_modules") or []
        levels = set()
        for mod in modules:
            level = mod.get("asil_level")
            if level:
                levels.add(level.upper())
        valid = {l for l in levels if l in _ASIL_ORDER}
        if not valid:
            return "QM"
        return sorted(valid, key=lambda x: _ASIL_ORDER.get(x, 0), reverse=True)[0]

    def _mark_failed(self, document_id: str, tenant_id: int, error_message: str) -> None:
        """Mark both DesignDocument and SoftwareDetailedDesign as failed."""
        self.design_repo.update_status(
            document_id, tenant_id, "failed", error_message=error_message
        )
        try:
            self.sdd_repo.update_status(
                document_id, tenant_id, "failed", error_message=error_message
            )
        except Exception:
            logger.exception("Failed to mark SoftwareDetailedDesign as failed")

    def get_design_document(self, tenant_id: int, document_id: str) -> dict:
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)

        # Prefer new SoftwareDetailedDesign table if available
        sdd = self.sdd_repo.get_by_document(document_id, tenant_id)
        if sdd is not None:
            return self._get_design_from_sdd(sdd, document_id)

        # Fallback to legacy DesignDocument table
        design = self.design_repo.get_by_document_id(document_id, tenant_id)
        if design is None:
            return {
                "document_id": document_id,
                "status": "pending",
                "asil_level": None,
                "sections": None,
                "error_message": None,
            }

        reported_status = design.status
        reported_error = design.error_message
        if reported_status == "running":
            last_update = design.updated_at or design.created_at
            if last_update:
                if last_update.tzinfo is None:
                    last_update = last_update.replace(tzinfo=UTC)
                if (
                    datetime.now(UTC) - last_update
                ).total_seconds() > _TIMEOUT_MINUTES * 60:
                    reported_status = "failed"
                    reported_error = "设计文档生成超时（超过10分钟）"

        return {
            "document_id": document_id,
            "status": reported_status,
            "asil_level": design.asil_level,
            "sections": design.sections,
            "error_message": reported_error,
        }

    def _get_design_from_sdd(self, sdd, document_id: str) -> dict:
        """Build design document response from SoftwareDetailedDesign record."""
        reported_status = sdd.status
        reported_error = sdd.error_message
        if reported_status == "running":
            last_update = sdd.updated_at or sdd.created_at
            if last_update:
                if last_update.tzinfo is None:
                    last_update = last_update.replace(tzinfo=UTC)
                if (
                    datetime.now(UTC) - last_update
                ).total_seconds() > _TIMEOUT_MINUTES * 60:
                    reported_status = "failed"
                    reported_error = "设计文档生成超时（超过10分钟）"

        # Convert stored JSON fields back to dict for legacy sections
        try:
            fc_arch = json.loads(sdd.fc_architecture) if sdd.fc_architecture else {}
        except json.JSONDecodeError:
            fc_arch = {}
        try:
            detail = json.loads(sdd.detailed_design) if sdd.detailed_design else []
        except json.JSONDecodeError:
            detail = []
        try:
            safety = json.loads(sdd.safety_design) if sdd.safety_design else {}
        except json.JSONDecodeError:
            safety = {}
        try:
            verify = json.loads(sdd.verification_strategy) if sdd.verification_strategy else {}
        except json.JSONDecodeError:
            verify = {}

        design_data = {
            "overview": sdd.overview or "",
            "project_number": sdd.project_number or "",
            "document_version": sdd.document_version or "",
            "fc_architecture": fc_arch,
            "detailed_design": detail,
            "safety_design": safety,
            "verification_strategy": verify,
        }
        legacy_sections = self._build_legacy_sections(design_data)

        return {
            "document_id": document_id,
            "status": reported_status,
            "asil_level": self._resolve_asil_from_design(design_data),
            "sections": legacy_sections,
            "error_message": reported_error,
        }

