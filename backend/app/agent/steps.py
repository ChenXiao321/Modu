"""Built-in step implementations for the Agent workflow."""

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.agent.workflow import Step, WorkflowContext
from app.integrations.llm_client import LLMClient, LLMOutputFormatError

logger = logging.getLogger(__name__)

_MAX_DOCUMENT_TEXT_LEN = 12000


def _truncate_document_text(text: str, max_len: int = _MAX_DOCUMENT_TEXT_LEN) -> str:
    """Truncate document text for prompt context, preserving start and end."""
    if len(text) <= max_len:
        return text
    half = max_len // 2
    return text[:half] + f"\n\n...[{{truncated}} {len(text) - max_len} chars omitted]...\n\n" + text[-half:]


def _clean_json_response(raw: str) -> str:
    """Strip markdown fences and surrounding whitespace from LLM JSON output."""
    raw = raw.strip()
    if raw.startswith("```"):
        # Remove opening fence (with optional language tag)
        first_newline = raw.find("\n")
        if first_newline != -1:
            raw = raw[first_newline + 1:]
        else:
            raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3].strip()
    return raw


class DocumentStructureAnalysisStep(Step):
    """Step 1: Analyze document structure and identify key terms."""

    def __init__(self, template_dir: Path) -> None:
        super().__init__(
            name="01_structure_analysis",
            prompt_template="01_structure.j2",
            template_dir=template_dir,
        )

    def build_prompt(self, context: WorkflowContext) -> str:
        from app.integrations.template_loader import TemplateLoader

        return TemplateLoader.render_from_dir(
            self.template_dir,
            self.prompt_template,
            document_text=_truncate_document_text(context.document_text),
            filename=context.filename,
            previous_outputs=context.previous_outputs,
        )

    def parse_output(self, raw: str) -> dict[str, Any]:
        cleaned = _clean_json_response(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMOutputFormatError(
                f"01_structure_analysis: invalid JSON: {exc}", raw_response=raw
            ) from exc

        if not isinstance(data, dict):
            raise LLMOutputFormatError(
                "01_structure_analysis: expected JSON object", raw_response=raw
            )

        # Normalize fields
        chapters = data.get("chapters") or []
        key_terms = data.get("key_terms") or []
        if not isinstance(chapters, list):
            raise LLMOutputFormatError(
                "01_structure_analysis: 'chapters' must be a list", raw_response=raw
            )
        if not isinstance(key_terms, list):
            raise LLMOutputFormatError(
                "01_structure_analysis: 'key_terms' must be a list", raw_response=raw
            )

        return {
            "chapters": chapters,
            "key_terms": key_terms,
            "document_type": data.get("document_type", "unknown"),
        }


class RequirementExtractionStep(Step):
    """Step 2: Extract flat requirements from the document."""

    def __init__(self, template_dir: Path) -> None:
        super().__init__(
            name="02_requirement_extraction",
            prompt_template="02_extract.j2",
            template_dir=template_dir,
        )

    def build_prompt(self, context: WorkflowContext) -> str:
        from app.integrations.template_loader import TemplateLoader

        return TemplateLoader.render_from_dir(
            self.template_dir,
            self.prompt_template,
            document_text=_truncate_document_text(context.document_text),
            filename=context.filename,
            previous_outputs=context.previous_outputs,
        )

    def parse_output(self, raw: str) -> list[dict]:
        cleaned = _clean_json_response(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMOutputFormatError(
                f"02_requirement_extraction: invalid JSON: {exc}", raw_response=raw
            ) from exc

        if not isinstance(data, list):
            raise LLMOutputFormatError(
                "02_requirement_extraction: expected JSON array", raw_response=raw
            )

        # Normalize each requirement
        normalized = []
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                logger.warning("Skipping non-dict requirement at index %d", idx)
                continue
            req_id = item.get("requirement_id")
            description = item.get("description")
            if not req_id or not description:
                logger.warning(
                    "Requirement at index %d missing requirement_id or description", idx
                )
                continue
            normalized.append({
                "requirement_id": str(req_id).strip(),
                "description": str(description).strip(),
                "chapter": item.get("chapter"),
                "asil_level": item.get("asil_level"),
                "parent_hint": item.get("parent_hint"),
            })
        return normalized


class AsilVerificationStep(Step):
    """Step 3: Cross-verify ASIL levels against document declarations."""

    def __init__(self, template_dir: Path) -> None:
        super().__init__(
            name="03_asil_verification",
            prompt_template="03_verify.j2",
            template_dir=template_dir,
        )

    def build_prompt(self, context: WorkflowContext) -> str:
        from app.integrations.template_loader import TemplateLoader

        return TemplateLoader.render_from_dir(
            self.template_dir,
            self.prompt_template,
            document_text=_truncate_document_text(context.document_text),
            filename=context.filename,
            previous_outputs=context.previous_outputs,
        )

    def parse_output(self, raw: str) -> dict[str, Any]:
        cleaned = _clean_json_response(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMOutputFormatError(
                f"03_asil_verification: invalid JSON: {exc}", raw_response=raw
            ) from exc

        if not isinstance(data, dict):
            raise LLMOutputFormatError(
                "03_asil_verification: expected JSON object", raw_response=raw
            )

        requirements = data.get("requirements") or []
        inconsistencies = data.get("inconsistencies") or []
        if not isinstance(requirements, list):
            raise LLMOutputFormatError(
                "03_asil_verification: 'requirements' must be a list", raw_response=raw
            )
        if not isinstance(inconsistencies, list):
            raise LLMOutputFormatError(
                "03_asil_verification: 'inconsistencies' must be a list", raw_response=raw
            )

        return {
            "requirements": requirements,
            "inconsistencies": inconsistencies,
        }


class HierarchyResolutionStep(Step):
    """Step 4: Build the FC Requirement Specification document."""

    def __init__(self, template_dir: Path) -> None:
        super().__init__(
            name="04_hierarchy_resolution",
            prompt_template="04_hierarchy.j2",
            template_dir=template_dir,
        )

    def build_prompt(self, context: WorkflowContext) -> str:
        from app.integrations.template_loader import TemplateLoader

        return TemplateLoader.render_from_dir(
            self.template_dir,
            self.prompt_template,
            document_text=_truncate_document_text(context.document_text),
            filename=context.filename,
            previous_outputs=context.previous_outputs,
        )

    def parse_output(self, raw: str) -> dict[str, Any]:
        cleaned = _clean_json_response(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMOutputFormatError(
                f"04_hierarchy_resolution: invalid JSON: {exc}", raw_response=raw
            ) from exc

        if not isinstance(data, dict):
            raise LLMOutputFormatError(
                "04_hierarchy_resolution: expected JSON object", raw_response=raw
            )

        return self._normalize_fc_spec(data)

    def _normalize_fc_spec(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize and validate FC requirement specification shape."""
        result: dict[str, Any] = {
            "project_number": data.get("project_number"),
            "author": data.get("author"),
            "version": data.get("version"),
            "status": data.get("status"),
            "purpose": data.get("purpose"),
            "scope": data.get("scope"),
            "definitions": self._normalize_definitions(data.get("definitions")),
            "overview": data.get("overview"),
            "functional_requirements": self._normalize_functional_requirements(
                data.get("functional_requirements")
            ),
            "non_functional_requirements": self._normalize_non_functional_requirements(
                data.get("non_functional_requirements")
            ),
            "notes": data.get("notes"),
            "supporting_documents": self._normalize_list_of_strings(
                data.get("supporting_documents")
            ),
        }
        return result

    def _normalize_definitions(self, defs: Any) -> list[dict]:
        if not isinstance(defs, list):
            return []
        result = []
        for d in defs:
            if isinstance(d, dict) and d.get("term") and d.get("definition"):
                result.append({
                    "term": str(d["term"]).strip(),
                    "definition": str(d["definition"]).strip(),
                })
        return result

    def _normalize_functional_requirements(self, reqs: Any) -> list[dict]:
        if not isinstance(reqs, list):
            return []
        result = []
        for cat in reqs:
            if not isinstance(cat, dict):
                continue
            items = self._normalize_tree(cat.get("items") or [])
            if items:
                result.append({
                    "category": str(cat.get("category", "未分类")).strip(),
                    "items": items,
                })
        return result

    def _normalize_non_functional_requirements(self, reqs: Any) -> list[dict]:
        if not isinstance(reqs, list):
            return []
        result = []
        for r in reqs:
            if isinstance(r, dict) and r.get("description"):
                result.append({"description": str(r["description"]).strip()})
            elif isinstance(r, str):
                result.append({"description": str(r).strip()})
        return result

    def _normalize_list_of_strings(self, val: Any) -> list[str]:
        if not isinstance(val, list):
            return []
        return [str(v).strip() for v in val if v]

    def _normalize_tree(self, nodes: list[dict]) -> list[dict]:
        """Recursively normalize requirement tree nodes."""
        result = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            req_id = node.get("requirement_id")
            description = node.get("description")
            if not req_id or not description:
                continue
            children = node.get("children") or []
            if not isinstance(children, list):
                children = []
            result.append({
                "requirement_id": str(req_id).strip(),
                "description": str(description).strip(),
                "chapter": node.get("chapter"),
                "asil_level": node.get("asil_level"),
                "parent_requirement_id": node.get("parent_requirement_id"),
                "children": self._normalize_tree(children),
            })
        return result


def build_default_steps(template_dir: Path) -> list[Step]:
    """Return the default 4-step pipeline."""
    return [
        DocumentStructureAnalysisStep(template_dir),
        RequirementExtractionStep(template_dir),
        AsilVerificationStep(template_dir),
        HierarchyResolutionStep(template_dir),
    ]
