import logging
import uuid
from typing import List

from sqlalchemy.orm import Session

from app.exceptions import DocumentNotFoundError, DocumentNotReadyError
from app.integrations.llm_client import LLMClient, MockLLMClient
from app.models.document import Document
from app.models.parsed_requirement import ParsedRequirement
from app.repositories.document_repository import DocumentRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.safety_parameter_repository import SafetyParameterRepository
from app.models.safety_critical_parameter import SafetyCriticalParameter
from app.services.text_extractor import TextExtractor, TextExtractorError

logger = logging.getLogger(__name__)

_MAX_TREE_DEPTH = 10
_MAX_REQUIREMENT_ID_LEN = 50


class DocumentParseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.req_repo = RequirementRepository(db)
        self.safety_repo = SafetyParameterRepository(db)
        self.llm_client: LLMClient = MockLLMClient()

    def trigger_parse(self, tenant_id: int, document_id: str) -> dict:
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)
        if doc.upload_status != "completed":
            raise DocumentNotReadyError(document_id, "文档上传尚未完成")
        if doc.parse_status == "running":
            raise DocumentNotReadyError(document_id, "解析任务已在进行中")
        if doc.parse_status == "completed":
            raise DocumentNotReadyError(document_id, "文档已解析完成，请勿重复触发")

        parse_task_id = str(uuid.uuid4())
        self.doc_repo.update_parse_status(document_id, tenant_id, "running", parse_task_id)

        return {
            "document_id": document_id,
            "parse_task_id": parse_task_id,
            "status": "queued",
        }

    def execute_parse(self, tenant_id: int, document_id: str) -> None:
        """Synchronous parse execution. Intended to be run in background."""
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            logger.warning("Parse aborted: document %s not found", document_id)
            return
        if doc.parse_status != "running":
            logger.warning(
                "Parse aborted: document %s parse_status=%s (expected running)",
                document_id,
                doc.parse_status,
            )
            return
        if doc.storage_path is None:
            logger.warning("Parse aborted: document %s has no storage_path", document_id)
            self.doc_repo.update_parse_status(document_id, tenant_id, "failed")
            return

        try:
            text = TextExtractor.extract(doc.storage_path, doc.file_type)
            raw_requirements = self.llm_client.extract_requirements(text, doc.original_filename)

            # Validate depth before touching DB
            self._validate_tree_depth(raw_requirements)

            # Clear old requirements
            self.req_repo.delete_by_document(document_id, tenant_id)

            # Persist tree recursively (MVP: each node committed individually)
            self._persist_requirements(tenant_id, document_id, raw_requirements)

            # Extract and persist safety-critical parameters (best-effort, non-blocking)
            try:
                raw_parameters = self.llm_client.extract_safety_parameters(text, doc.original_filename)
                if raw_parameters is not None:
                    # Delete old params only after successful extraction to avoid data loss on retry
                    self.safety_repo.delete_by_document(document_id, tenant_id)
                    self._persist_safety_parameters(tenant_id, document_id, raw_parameters)
            except Exception:
                logger.exception("Safety parameter extraction failed for document %s", document_id)

            self.doc_repo.update_parse_status(document_id, tenant_id, "completed")
            logger.info("Parse completed for document %s", document_id)
        except TextExtractorError as e:
            logger.error("Text extraction failed for document %s: %s", document_id, e.message)
            self.doc_repo.update_parse_status(document_id, tenant_id, "failed")
        except Exception:
            logger.exception("Unexpected parse failure for document %s", document_id)
            self.doc_repo.update_parse_status(document_id, tenant_id, "failed")

    def _validate_tree_depth(self, nodes: List[dict], current_depth: int = 1) -> None:
        if current_depth > _MAX_TREE_DEPTH:
            raise ValueError(f"需求树深度超过最大限制 ({_MAX_TREE_DEPTH})")
        for node in nodes:
            children = node.get("children") or []
            if children:
                self._validate_tree_depth(children, current_depth + 1)

    def _persist_requirements(
        self,
        tenant_id: int,
        document_id: str,
        raw_requirements: List[dict],
        parent_id: str | None = None,
    ) -> None:
        for raw in raw_requirements:
            req_id = raw.get("requirement_id")
            description = raw.get("description")
            if not req_id or not description:
                raise ValueError("需求条目缺少 requirement_id 或 description")
            if len(str(req_id)) > _MAX_REQUIREMENT_ID_LEN:
                raise ValueError(
                    f"requirement_id 超过最大长度 {_MAX_REQUIREMENT_ID_LEN}: {req_id}"
                )

            req = ParsedRequirement(
                tenant_id=tenant_id,
                document_id=document_id,
                requirement_id=str(req_id),
                description=str(description),
                chapter=raw.get("chapter"),
                asil_level=raw.get("asil_level"),
                parent_requirement_id=parent_id,
            )
            self.req_repo.create(req)
            children = raw.get("children") or []
            if children:
                self._persist_requirements(tenant_id, document_id, children, req.id)

    def get_parse_status(self, tenant_id: int, document_id: str) -> dict:
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)

        status = doc.parse_status
        if status is None:
            status = "pending"

        progress = 0
        if status == "running":
            progress = 50
        elif status == "completed":
            progress = 100
        elif status == "failed":
            progress = 0

        return {
            "document_id": document_id,
            "status": status,
            "progress_percent": progress,
            "message": None,
        }

    def _persist_safety_parameters(
        self,
        tenant_id: int,
        document_id: str,
        raw_parameters: List[dict],
    ) -> None:
        for raw in raw_parameters:
            param_id = raw.get("parameter_id")
            name = raw.get("name")
            value = raw.get("value")
            if param_id is None or name is None or value is None:
                raise ValueError("安全关键参数条目缺少 parameter_id、name 或 value")
            if not str(param_id).strip() or not str(name).strip():
                raise ValueError("安全关键参数条目 parameter_id 或 name 为空字符串")
            if len(str(param_id)) > _MAX_REQUIREMENT_ID_LEN:
                raise ValueError(
                    f"parameter_id 超过最大长度 {_MAX_REQUIREMENT_ID_LEN}: {param_id}"
                )

            source_page = raw.get("source_page")
            if source_page is not None:
                try:
                    source_page = int(source_page)
                except (ValueError, TypeError):
                    source_page = None

            param = SafetyCriticalParameter(
                tenant_id=tenant_id,
                document_id=document_id,
                parameter_id=str(param_id),
                name=str(name),
                value=str(value),
                unit=raw.get("unit"),
                tolerance=raw.get("tolerance"),
                chapter=raw.get("chapter"),
                source_page=source_page,
            )
            self.safety_repo.create(param)

    def get_safety_parameters(self, tenant_id: int, document_id: str) -> list[dict]:
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)
        if doc.parse_status not in ("completed", "running"):
            return []
        params = self.safety_repo.get_by_document(document_id, tenant_id)
        return [
            {
                "id": p.id,
                "parameter_id": p.parameter_id,
                "name": p.name,
                "value": p.value,
                "unit": p.unit,
                "tolerance": p.tolerance,
                "chapter": p.chapter,
                "source_page": p.source_page,
            }
            for p in params
        ]

    def get_requirements_tree(self, tenant_id: int, document_id: str) -> list[dict]:
        roots = self.req_repo.get_roots_by_document(document_id, tenant_id)
        return [self._build_tree_node(r) for r in roots]

    def _build_tree_node(self, req: ParsedRequirement) -> dict:
        return {
            "id": req.id,
            "requirement_id": req.requirement_id,
            "description": req.description,
            "chapter": req.chapter,
            "asil_level": req.asil_level,
            "children": [self._build_tree_node(child) for child in (req.children or [])],
        }
