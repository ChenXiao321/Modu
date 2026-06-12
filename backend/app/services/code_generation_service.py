import json
import logging
import os
import re
import tempfile
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
from app.integrations.llm_client import LiteLLMClient, LLMClient, MockLLMClient
from app.models.document import Document
from app.models.generated_code_file import GeneratedCodeFile
from app.repositories.document_repository import DocumentRepository
from app.repositories.generated_code_file_repository import GeneratedCodeFileRepository
from app.repositories.software_detailed_design_repository import SoftwareDetailedDesignRepository
from app.templates.code import CodeGenerator

logger = logging.getLogger(__name__)

# Default author used until Auth module is implemented.
# TODO: Replace with CurrentUser.name when Auth module lands.
_DEFAULT_AUTHOR = settings.code_author_default


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
        # Lock the document row to prevent concurrent triggers (TOCTOU protection)
        doc = (
            self.db.query(Document)
            .filter(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
            .with_for_update()
            .first()
        )
        if doc is None:
            raise DocumentNotFoundError(document_id)
        if doc.parse_status != "completed":
            raise DocumentNotReadyError(document_id, "文档解析尚未完成")
        if doc.pipeline_status not in ("design_reviewed", "code_generated"):
            expected = "design_reviewed"
            raise PipelineStatusInvalidError(document_id, doc.pipeline_status, expected)
        if doc.pipeline_status == "code_generation_running":
            raise DocumentNotReadyError(document_id, "代码生成任务已在进行中")

        # Delete old code files in the same transaction as status update
        self.db.query(GeneratedCodeFile).filter(
            GeneratedCodeFile.document_id == document_id,
            GeneratedCodeFile.tenant_id == tenant_id,
        ).delete(synchronize_session="fetch")

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
        author = _DEFAULT_AUTHOR

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

            # Extract module name from fc_architecture
            fc_arch = sdd_data.get("fc_architecture") or {}
            modules = fc_arch.get("fc_modules") or []
            if not modules:
                raise ValueError("fc_architecture 中没有 FC 模块，无法确定模块名")
            module_name = modules[0].get("module_name", "Gp_Unknown")

            # Extract requirements trace mapping from detailed_design
            trace_mapping = self._extract_trace_mapping(sdd_data.get("detailed_design") or [])

            # Read ASIL information from design document
            module_asil = self._resolve_asil_from_design(document_id, tenant_id)
            asil_context = self._build_asil_context(module_asil, fc_arch)

            # Read code generation configuration
            template_version = settings.code_template_version
            naming_convention = settings.code_naming_convention

            # Step 1: Generate FC framework using deterministic templates
            generator = CodeGenerator()
            with tempfile.TemporaryDirectory() as tmpdir:
                generator.generate_files(
                    module_name, author, tmpdir, template_version=template_version
                )
                module_dir = os.path.join(tmpdir, module_name)

                # Read framework content
                framework: dict[str, str] = {}
                for filename in sorted(os.listdir(module_dir)):
                    filepath = os.path.join(module_dir, filename)
                    with open(filepath, encoding="utf-8") as f:
                        framework[filename] = f.read()

            # Step 2: Construct design text including FC framework
            design_text = json.dumps(
                {
                    "module_name": module_name,
                    "fc_architecture": fc_arch,
                    "detailed_design": sdd_data.get("detailed_design") or [],
                    "safety_design": sdd_data.get("safety_design") or {},
                    "overview": sdd_data.get("overview") or "",
                    "fc_framework": framework,
                },
                ensure_ascii=False,
                indent=2,
            )

            # Step 3: Run LLM agent to fill business logic into FC framework
            code_data = self._execute_code_generation_workflow(
                tenant_id,
                document_id,
                design_text,
                doc.original_filename,
                author,
                template_version=template_version,
                naming_convention=naming_convention,
                trace_mapping=trace_mapping,
                asil_level=module_asil,
                asil_context=asil_context,
            )

            # Persist generated files in a single transaction
            files = code_data.get("files") or []
            for f in files:
                record = GeneratedCodeFile(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    file_path=f["file_path"],
                    file_type=f["file_type"],
                    content=f["content"],
                    template_version=template_version,
                    naming_convention=naming_convention,
                    polarion_trace_id=self._derive_polarion_trace_id(f, trace_mapping),
                    asil_level=module_asil,
                )
                self.db.add(record)

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
                "template_version": f.template_version,
                "naming_convention": f.naming_convention,
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
            "template_version": f.template_version,
            "naming_convention": f.naming_convention,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }

    def _execute_code_generation_workflow(
        self,
        tenant_id: int,
        document_id: str,
        document_text: str,
        filename: str,
        author: str,
        template_version: str = "1.0.0",
        naming_convention: str = "mixed",
        trace_mapping: dict[str, list[str]] | None = None,
        asil_level: str = "QM",
        asil_context: dict | None = None,
    ) -> dict:
        """Run the 2-step code generation agent workflow."""
        template_dir = Path(__file__).parent.parent / "agent" / "prompts"
        steps = build_code_generation_steps(
            template_dir,
            template_version=template_version,
            naming_convention=naming_convention,
            trace_mapping=trace_mapping,
            asil_level=asil_level,
            asil_context=asil_context,
        )

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

    @staticmethod
    def _extract_trace_mapping(detailed_design: list[dict]) -> dict[str, list[str]]:
        """Extract function_name -> requirement_ids mapping from detailed_design."""
        trace_mapping: dict[str, list[str]] = {}
        for item in detailed_design:
            if not isinstance(item, dict):
                continue
            # New format: fc_id -> functions[]
            if "functions" in item:
                for func in item.get("functions", []):
                    name = func.get("function_name")
                    reqs = func.get("assigned_requirements")
                    if name and reqs and isinstance(reqs, list):
                        trace_mapping[str(name)] = [str(r) for r in reqs]
            # Backward compatibility: old flat format
            elif "function_name" in item:
                name = item.get("function_name")
                reqs = item.get("assigned_requirements")
                if name and reqs and isinstance(reqs, list):
                    trace_mapping[str(name)] = [str(r) for r in reqs]
        return trace_mapping

    @staticmethod
    def _derive_polarion_trace_id(
        file_dict: dict, trace_mapping: dict[str, list[str]]
    ) -> str | None:
        """Derive file-level polarion_trace_id from content and trace_mapping."""
        content = file_dict.get("content", "")
        # Parse all TRACE-ID markers from content
        matches = re.findall(r"/\*\s*TRACE-ID:\s*([^*]+)\*/", content)
        trace_ids = []
        for m in matches:
            ids = [t.strip() for t in str(m).split(",") if t.strip()]
            trace_ids.extend(ids)
        trace_ids = list(dict.fromkeys(trace_ids))  # dedup preserving order
        if trace_ids:
            return ",".join(trace_ids)

        # Fallback: aggregate requirement IDs from trace_mapping for this file.
        fallback_ids: list[str] = []
        for reqs in (trace_mapping or {}).values():
            fallback_ids.extend(reqs)
        fallback_ids = list(dict.fromkeys(fallback_ids))
        if fallback_ids:
            return ",".join(fallback_ids)

        # Final fallback: module-level trace ID
        return "POL-CODE-MODULE"

    def _resolve_asil_from_design(self, document_id: str, tenant_id: int) -> str:
        """Read module-level ASIL from DesignDocument and normalize to A/B/C/D/QM."""
        from app.repositories.design_document_repository import DesignDocumentRepository

        design_repo = DesignDocumentRepository(self.db)
        design = design_repo.get_by_document_id(document_id, tenant_id)
        if design is not None and design.asil_level:
            return self._normalize_asil(design.asil_level)
        return "QM"

    @staticmethod
    def _normalize_asil(raw: str) -> str:
        """Normalize ASIL strings such as 'ASIL-B', 'b' to 'B'. Defaults to QM."""
        if not raw:
            return "QM"
        val = str(raw).upper().replace("ASIL-", "").replace("ASIL_", "").strip()
        if val in {"A", "B", "C", "D"}:
            return val
        return "QM"

    @staticmethod
    def _build_asil_context(module_asil: str, fc_arch: dict) -> dict:
        """Build ASIL context dict for prompt injection."""
        fc_asil_mapping: dict[str, str] = {}
        for mod in fc_arch.get("fc_modules") or []:
            fc_id = mod.get("fc_id")
            fc_asil = mod.get("asil_level")
            if fc_id and fc_asil:
                fc_asil_mapping[str(fc_id)] = CodeGenerationService._normalize_asil(fc_asil)

        coverage_targets = settings.asil_coverage_targets.get(module_asil, {})
        coverage_targets_display = ""
        if coverage_targets:
            parts = [f"statement={coverage_targets.get('statement')}%"]
            if "branch" in coverage_targets:
                parts.append(f"branch={coverage_targets.get('branch')}%")
            if "mcdc" in coverage_targets:
                parts.append(f"MC/DC={coverage_targets.get('mcdc')}%")
            coverage_targets_display = ", ".join(parts)

        return {
            "fc_asil_mapping": fc_asil_mapping,
            "coverage_targets": coverage_targets,
            "coverage_targets_display": coverage_targets_display,
        }

    def _mark_failed(
        self, document_id: str, tenant_id: int, error_message: str
    ) -> None:
        """Mark code generation as failed and rollback pipeline status if needed."""
        # Clean up any partially created code files
        self.db.query(GeneratedCodeFile).filter(
            GeneratedCodeFile.document_id == document_id,
            GeneratedCodeFile.tenant_id == tenant_id,
        ).delete(synchronize_session="fetch")

        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is not None and doc.pipeline_status == "code_generation_running":
            doc.pipeline_status = "design_reviewed"
            doc.block_reason = None
            self.db.commit()
            self.db.refresh(doc)
