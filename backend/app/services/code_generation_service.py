import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.agent.steps import build_code_generation_steps
from app.agent.workflow import AgentWorkflowEngine, WorkflowContext, WorkflowFailedError
from app.config import settings
from app.exceptions import (
    DesignDocumentNotFoundError,
    DocumentNotFoundError,
    DocumentNotReadyError,
    PipelineStatusInvalidError,
)
from app.integrations.llm_client import LLMClient, LiteLLMClient, MockLLMClient
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.generated_code_file_repository import GeneratedCodeFileRepository
from app.repositories.software_detailed_design_repository import SoftwareDetailedDesignRepository

logger = logging.getLogger(__name__)


class CodeGenerationService:
    def __init__(self, db: Session, llm_client: LLMClient | None = None) -> None:
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.sdd_repo = SoftwareDetailedDesignRepository(db)
        self.code_repo = GeneratedCodeFileRepository(db)
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
        if doc.parse_status != "completed":
            raise DocumentNotReadyError(document_id, "文档解析尚未完成")
        if doc.pipeline_status not in ("design_reviewed", "code_generated"):
            expected = "design_reviewed"
            raise PipelineStatusInvalidError(document_id, doc.pipeline_status, expected)
        if doc.pipeline_status == "code_generation_running":
            raise DocumentNotReadyError(document_id, "代码生成任务已在进行中")

        # Delete old code files if any
        self.code_repo.delete_by_document(document_id, tenant_id)

        # Update pipeline status
        doc.pipeline_status = "code_generation_running"
        doc.block_reason = None
        self.db.commit()
        self.db.refresh(doc)

        return {
            "document_id": document_id,
            "status": "code_generation_running",
        }

    def execute_generate(self, tenant_id: int, document_id: str) -> None:
        """Synchronous code generation via Agent workflow."""
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            logger.warning("Code generation aborted: document %s not found", document_id)
            return
        if doc.parse_status != "completed":
            logger.warning(
                "Code generation aborted: document %s parse_status=%s",
                document_id,
                doc.parse_status,
            )
            self._mark_failed(document_id, tenant_id, "文档解析尚未完成")
            return
        if doc.pipeline_status not in ("design_reviewed", "code_generation_running"):
            logger.warning(
                "Code generation aborted: document %s pipeline_status=%s",
                document_id,
                doc.pipeline_status,
            )
            self._mark_failed(
                document_id, tenant_id, f"流水线状态无效: {doc.pipeline_status}"
            )
            return

        try:
            # Load SoftwareDetailedDesign as input
            sdd = self.sdd_repo.get_by_document(document_id, tenant_id)
            if sdd is None:
                raise ValueError("SoftwareDetailedDesign 不存在，无法生成代码")
            sdd_data = self.sdd_repo.to_dict(sdd)
            design_text = json.dumps(
                {
                    "fc_architecture": sdd_data.get("fc_architecture") or {},
                    "detailed_design": sdd_data.get("detailed_design") or [],
                    "safety_design": sdd_data.get("safety_design") or {},
                    "overview": sdd_data.get("overview") or "",
                },
                ensure_ascii=False,
                indent=2,
            )

            # Run 2-step code generation agent workflow
            code_data = self._execute_code_generation_workflow(
                tenant_id, document_id, design_text, doc.original_filename
            )

            # Persist generated files
            files = code_data.get("files") or []
            for f in files:
                self.code_repo.create(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    file_path=f["file_path"],
                    file_type=f["file_type"],
                    content=f["content"],
                )

            # Transition pipeline to code_generated
            doc.pipeline_status = "code_generated"
            doc.block_reason = None
            self.db.commit()
            self.db.refresh(doc)

            logger.info("Code generation completed for document %s", document_id)
        except Exception as exc:
            logger.exception("Code generation failed for document %s", document_id)
            error_msg = str(exc) if str(exc) else "代码生成过程中发生未知错误"
            self._mark_failed(document_id, tenant_id, error_msg)

    def get_code_files(self, tenant_id: int, document_id: str) -> list[dict]:
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)
        files = self.code_repo.get_by_document(document_id, tenant_id)
        return [
            {
                "id": f.id,
                "file_path": f.file_path,
                "file_type": f.file_type,
                "content": f.content,
                "polarion_trace_id": f.polarion_trace_id,
                "asil_level": f.asil_level,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in files
        ]

    def get_code_file_by_id(
        self, tenant_id: int, document_id: str, file_id: str
    ) -> dict:
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)
        f = self.code_repo.get_by_id(file_id, tenant_id)
        if f is None or f.document_id != document_id:
            raise DesignDocumentNotFoundError(file_id)
        return {
            "id": f.id,
            "file_path": f.file_path,
            "file_type": f.file_type,
            "content": f.content,
            "polarion_trace_id": f.polarion_trace_id,
            "asil_level": f.asil_level,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }

    def _execute_code_generation_workflow(
        self,
        tenant_id: int,
        document_id: str,
        document_text: str,
        filename: str,
    ) -> dict:
        """Run the 2-step code generation agent workflow."""
        template_dir = Path(__file__).parent.parent / "agent" / "prompts"
        steps = build_code_generation_steps(template_dir)

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

        code_record = result.get("code_02_code_generation")
        if code_record is None or code_record.output is None:
            raise WorkflowFailedError("code_02_code_generation did not produce output")

        code_data = code_record.output
        if not isinstance(code_data, dict):
            raise WorkflowFailedError("code_02_code_generation output is not a dict")

        return code_data

    def _mark_failed(
        self, document_id: str, tenant_id: int, error_message: str
    ) -> None:
        """Mark code generation as failed and rollback pipeline status if needed."""
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is not None and doc.pipeline_status == "code_generation_running":
            doc.pipeline_status = "design_reviewed"
            doc.block_reason = None
            self.db.commit()
            self.db.refresh(doc)
