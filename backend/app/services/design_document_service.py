import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List

from sqlalchemy.orm import Session

from app.exceptions import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    PipelineBlockedError,
)
from app.config import settings
from app.integrations.llm_client import LLMClient, LiteLLMClient, MockLLMClient
from app.models.design_document import DesignDocument
from app.repositories.design_document_repository import DesignDocumentRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.safety_parameter_repository import SafetyParameterRepository

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
        if llm_client is not None:
            self.llm_client: LLMClient = llm_client
        elif settings.llm_provider == "litellm":
            self.llm_client: LLMClient = LiteLLMClient(
                model=settings.llm_model,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url or None,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
        else:
            self.llm_client: LLMClient = MockLLMClient()

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

        return {
            "document_id": document_id,
            "design_task_id": design_task_id,
            "status": "running",
        }

    def execute_generate(self, tenant_id: int, document_id: str) -> None:
        """Synchronous design document generation. Intended to be run in background."""
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
            self.design_repo.update_status(
                document_id, tenant_id, "failed", error_message="文档解析尚未完成"
            )
            return
        if doc.pipeline_status == "blocked":
            logger.warning(
                "Design generation aborted: document %s pipeline blocked", document_id
            )
            self.design_repo.update_status(
                document_id,
                tenant_id,
                "failed",
                error_message=f"流水线阻塞: {doc.block_reason}",
            )
            return

        try:
            requirements = self._build_requirements_list(
                self.req_repo.get_roots_by_document(document_id, tenant_id)
            )
            safety_parameters = self.safety_repo.get_by_document(document_id, tenant_id)
            safety_params_list = [
                {
                    "parameter_id": p.parameter_id,
                    "name": p.name,
                    "value": p.value,
                    "unit": p.unit,
                    "tolerance": p.tolerance,
                    "chapter": p.chapter,
                }
                for p in safety_parameters
            ]

            asil_level = self._resolve_asil_level(requirements)
            if asil_level is None:
                asil_level = "QM"

            sections = self.llm_client.generate_design_document(
                requirements=requirements,
                safety_parameters=safety_params_list,
                asil_level=asil_level,
                filename=doc.original_filename,
            )

            _REQUIRED_SECTIONS = {
                "overview",
                "references",
                "system_architecture",
                "interface_definition",
                "dynamic_behavior",
                "resource_consumption",
                "error_handling",
                "test_strategy",
            }
            if not isinstance(sections, dict):
                raise ValueError(f"LLM 返回的 sections 必须为字典，实际类型: {type(sections).__name__}")
            missing = _REQUIRED_SECTIONS - set(sections.keys())
            if missing:
                raise ValueError(f"设计文档缺少章节: {', '.join(missing)}")
            for key, section in sections.items():
                if not isinstance(section, dict):
                    raise ValueError(f"章节 '{key}' 格式错误: 必须为字典，实际类型: {type(section).__name__}")
                if "content" not in section or not isinstance(section["content"], str):
                    raise ValueError(f"章节 '{key}' 缺少 content 字段或类型错误")
                if "polarion_trace_id" not in section or not isinstance(section["polarion_trace_id"], str):
                    raise ValueError(f"章节 '{key}' 缺少 polarion_trace_id 字段或类型错误")

            self.design_repo.update_status(
                document_id,
                tenant_id,
                "completed",
                sections=sections,
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
            self.design_repo.update_status(
                document_id,
                tenant_id,
                "failed",
                error_message=error_msg,
            )
            # Rollback pipeline status if it was promoted to in_design during a re-trigger
            doc = self.doc_repo.get_by_id(document_id, tenant_id)
            if doc is not None and doc.pipeline_status == "in_design":
                doc.pipeline_status = "ready"
                doc.block_reason = None
                self.db.commit()
                self.db.refresh(doc)

    def get_design_document(self, tenant_id: int, document_id: str) -> dict:
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)

        design = self.design_repo.get_by_document_id(document_id, tenant_id)
        if design is None:
            return {
                "document_id": document_id,
                "status": "pending",
                "asil_level": None,
                "sections": None,
                "error_message": None,
            }

        # Lazy timeout check: report stuck running tasks without mutating DB in a GET path
        reported_status = design.status
        reported_error = design.error_message
        if reported_status == "running":
            last_update = design.updated_at or design.created_at
            if last_update:
                if last_update.tzinfo is None:
                    last_update = last_update.replace(tzinfo=timezone.utc)
                if (
                    datetime.now(timezone.utc) - last_update
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

    def _build_requirements_list(
        self, roots: List, _depth: int = 0
    ) -> list[dict]:
        if _depth > _MAX_TREE_DEPTH:
            raise ValueError(
                f"Requirement tree depth exceeds max limit {_MAX_TREE_DEPTH}"
            )
        result = []
        for r in roots:
            node = {
                "requirement_id": r.requirement_id,
                "description": r.description,
                "chapter": r.chapter,
                "asil_level": r.asil_level,
                "children": self._build_requirements_list(r.children or [], _depth + 1),
            }
            result.append(node)
        return result

    def _resolve_asil_level(self, requirements: list[dict]) -> str | None:
        """Extract the highest ASIL level from requirements; return None if none found."""
        levels = set()
        self._collect_asil_levels(requirements, levels)
        valid_levels = {l for l in levels if l in _ASIL_ORDER}
        if not valid_levels:
            return None
        sorted_levels = sorted(valid_levels, key=lambda x: _ASIL_ORDER.get(x, 0), reverse=True)
        return sorted_levels[0]

    def _collect_asil_levels(self, requirements: list[dict], levels: set) -> None:
        for req in requirements:
            level = req.get("asil_level")
            if level:
                levels.add(level.upper())
            children = req.get("children") or []
            self._collect_asil_levels(children, levels)
