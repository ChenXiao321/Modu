import logging
import uuid
from typing import List

from sqlalchemy.orm import Session

from app.exceptions import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    FieldAlreadyConfirmedError,
    FieldNotFoundError,
)
from app.integrations.llm_client import LLMClient, MockLLMClient
from app.models.document import Document
from app.models.ocr_extraction_result import OcrExtractionResult
from app.models.parsed_requirement import ParsedRequirement
from app.repositories.document_repository import DocumentRepository
from app.repositories.ocr_result_repository import OcrResultRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.safety_parameter_repository import SafetyParameterRepository
from app.models.safety_critical_parameter import SafetyCriticalParameter
from app.services.text_extractor import TextExtractor, TextExtractorError

logger = logging.getLogger(__name__)

_MAX_TREE_DEPTH = 10
_MAX_REQUIREMENT_ID_LEN = 50


_OCR_FILE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/tiff",
    "application/pdf",
}


class DocumentParseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.req_repo = RequirementRepository(db)
        self.safety_repo = SafetyParameterRepository(db)
        self.ocr_repo = OcrResultRepository(db)
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

            # Extract OCR fields with confidence for scan/image documents
            if self._is_ocr_document(doc):
                try:
                    raw_ocr_fields = self.llm_client.extract_ocr_fields(text, doc.original_filename)
                    if raw_ocr_fields is not None:
                        self.ocr_repo.delete_by_document(document_id, tenant_id)
                        self._persist_ocr_results(tenant_id, document_id, raw_ocr_fields)
                except Exception:
                    logger.exception("OCR field extraction failed for document %s", document_id)

            # Update pipeline block status based on low-confidence OCR fields
            self._update_pipeline_block_status(tenant_id, document_id)

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
            "pipeline_status": doc.pipeline_status or "ready",
            "block_reason": doc.block_reason,
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

    def _is_ocr_document(self, doc: Document) -> bool:
        """Determine if the document requires OCR confidence scoring."""
        if doc.file_type in _OCR_FILE_TYPES:
            return True
        # Fallback: check filename extension for image types
        lower_name = (doc.original_filename or "").lower()
        if any(lower_name.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".tiff", ".tif")):
            return True
        return False

    def _persist_ocr_results(
        self,
        tenant_id: int,
        document_id: str,
        raw_fields: List[dict],
    ) -> None:
        for raw in raw_fields:
            field_id = raw.get("field_id")
            extracted_text = raw.get("extracted_text")
            confidence = raw.get("confidence")
            if field_id is None or extracted_text is None or confidence is None:
                raise ValueError("OCR 字段条目缺少 field_id、extracted_text 或 confidence")
            if not str(field_id).strip() or not str(extracted_text).strip():
                raise ValueError("OCR 字段条目 field_id 或 extracted_text 为空字符串")
            try:
                confidence = float(confidence)
            except (ValueError, TypeError):
                raise ValueError(f"OCR 字段 confidence 格式无效: {confidence}")
            if not (0.0 <= confidence <= 1.0):
                raise ValueError(f"OCR 字段 confidence 超出范围 [0.0, 1.0]: {confidence}")
            if len(str(field_id)) > _MAX_REQUIREMENT_ID_LEN:
                raise ValueError(f"field_id 超过最大长度 {_MAX_REQUIREMENT_ID_LEN}: {field_id}")

            source_page = raw.get("source_page")
            if source_page is not None:
                try:
                    source_page = int(source_page)
                except (ValueError, TypeError):
                    source_page = None

            result = OcrExtractionResult(
                tenant_id=tenant_id,
                document_id=document_id,
                field_id=str(field_id),
                extracted_text=str(extracted_text),
                normalized_value=raw.get("normalized_value"),
                confidence=confidence,
                field_type=raw.get("field_type"),
                source_page=source_page,
                review_status="pending",
            )
            self.ocr_repo.create(result)

    def _update_pipeline_block_status(self, tenant_id: int, document_id: str) -> None:
        """Update pipeline status based on low-confidence OCR fields."""
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            return

        # Non-OCR documents are always ready
        if not self._is_ocr_document(doc):
            if doc.pipeline_status != "in_design":
                doc.pipeline_status = "ready"
                doc.block_reason = None
                self.db.commit()
            return

        low_conf_count = self.ocr_repo.get_low_confidence_count(document_id, tenant_id, threshold=0.95)
        if low_conf_count > 0:
            doc.pipeline_status = "blocked"
            doc.block_reason = f"存在 {low_conf_count} 个低置信度 OCR 字段未复核"
        else:
            doc.pipeline_status = "ready"
            doc.block_reason = None
        self.db.commit()

    def get_ocr_results(self, tenant_id: int, document_id: str) -> dict:
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)
        if doc.parse_status not in ("completed", "running"):
            return {
                "document_id": document_id,
                "pipeline_status": doc.pipeline_status or "ready",
                "block_reason": doc.block_reason,
                "fields": [],
            }
        fields = self.ocr_repo.get_by_document(document_id, tenant_id)
        return {
            "document_id": document_id,
            "pipeline_status": doc.pipeline_status or "ready",
            "block_reason": doc.block_reason,
            "fields": [
                {
                    "id": f.id,
                    "field_id": f.field_id,
                    "extracted_text": f.extracted_text,
                    "normalized_value": f.normalized_value,
                    "confidence": f.confidence,
                    "field_type": f.field_type,
                    "source_page": f.source_page,
                    "review_status": f.review_status,
                    "reviewed_by": f.reviewed_by,
                    "reviewed_at": f.reviewed_at.isoformat() if f.reviewed_at else None,
                }
                for f in fields
            ],
        }

    def confirm_low_confidence_field(
        self, tenant_id: int, document_id: str, field_id: str, reviewer: str
    ) -> dict:
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)

        field = self.ocr_repo.get_by_field_id(document_id, tenant_id, field_id)
        if field is None:
            raise FieldNotFoundError(field_id)
        if field.review_status == "confirmed":
            raise FieldAlreadyConfirmedError(field_id)

        updated = self.ocr_repo.update_review_status(document_id, tenant_id, field_id, reviewer)
        if updated is None:
            raise FieldNotFoundError(field_id)

        # Recalculate pipeline status after confirmation
        self._update_pipeline_block_status(tenant_id, document_id)

        # Refresh document to get updated pipeline status
        self.db.refresh(doc)
        low_conf_count = self.ocr_repo.get_low_confidence_count(document_id, tenant_id, threshold=0.95)

        return {
            "field_id": field_id,
            "review_status": updated.review_status,
            "reviewed_by": updated.reviewed_by,
            "reviewed_at": updated.reviewed_at.isoformat() if updated.reviewed_at else None,
            "pipeline_status": doc.pipeline_status,
            "all_confirmed": low_conf_count == 0,
        }
