import hashlib
import json
from abc import ABC, abstractmethod

from app.integrations.template_loader import TemplateLoader


class LLMClient(ABC):
    """Abstract interface for LLM-based structured requirement extraction."""

    @abstractmethod
    def extract_requirements(self, document_text: str, filename: str) -> list[dict]:
        """
        Extract structured requirements from raw document text.

        Returns a list of requirement dicts, each with keys:
        - requirement_id: str
        - description: str
        - chapter: str | None
        - asil_level: str | None
        - parent_requirement_id: str | None
        - children: list[dict] (nested requirements)
        """
        ...

    @abstractmethod
    def extract_safety_parameters(self, document_text: str, filename: str) -> list[dict]:
        """
        Extract safety-critical parameters from raw document text.

        Returns a list of parameter dicts, each with keys:
        - parameter_id: str (e.g., SW-REQ-SAF-001)
        - name: str
        - value: str
        - unit: str | None
        - tolerance: str | None
        - chapter: str | None
        - source_page: int | None
        """
        ...

    @abstractmethod
    def extract_ocr_fields(self, document_text: str, filename: str) -> list[dict]:
        """
        Extract OCR fields with confidence scores from document text.

        Returns a list of field dicts, each with keys:
        - field_id: str (e.g., OCR-FIELD-0001)
        - extracted_text: str
        - normalized_value: str | None
        - confidence: float (0.0-1.0)
        - field_type: str | None (voltage, temperature, timing, etc.)
        - source_page: int | None
        """
        ...

    @abstractmethod
    def generate_design_document(
        self,
        requirements: list[dict],
        safety_parameters: list[dict],
        asil_level: str | None,
        filename: str,
    ) -> dict:
        """
        Generate an ASPICE Level 2 design document from structured requirements.

        Returns a dict with section keys, each containing:
        - content: str
        - polarion_trace_id: str

        Sections: overview, references, system_architecture, interface_definition,
        dynamic_behavior, resource_consumption, error_handling, test_strategy
        """
        ...


class MockLLMClient(LLMClient):
    """
    Mock LLM client for MVP development and testing.
    Returns deterministic simulated requirements based on a hash of inputs,
    rendered through Jinja2 templates to align with the production template system.
    """

    def _make_seed(self, document_text: str, filename: str) -> int:
        """Generate a deterministic integer seed from inputs."""
        return int(hashlib.md5(f"{document_text}:{filename}".encode()).hexdigest(), 16)

    def _render_json(self, template_name: str, **context: object) -> list[dict] | dict:
        """Render a template and parse the resulting JSON."""
        raw = TemplateLoader.render(template_name, **context)
        return json.loads(raw)

    def extract_requirements(self, document_text: str, filename: str) -> list[dict]:
        seed = self._make_seed(document_text, filename)
        result = self._render_json(
            "requirements_v1.j2",
            document_text=document_text,
            filename=filename,
            seed=seed,
        )
        assert isinstance(result, list)
        return result

    def extract_safety_parameters(self, document_text: str, filename: str) -> list[dict]:
        # Empty document must return zero params to match test expectations.
        if not document_text:
            return []

        seed = self._make_seed(document_text, filename)
        result = self._render_json(
            "safety_params_v1.j2",
            document_text=document_text,
            filename=filename,
            seed=seed,
        )
        assert isinstance(result, list)
        return result

    def extract_ocr_fields(self, document_text: str, filename: str) -> list[dict]:
        seed = self._make_seed(document_text, filename)
        result = self._render_json(
            "ocr_fields_v1.j2",
            document_text=document_text,
            filename=filename,
            seed=seed,
        )
        assert isinstance(result, list)
        return result

    def generate_design_document(
        self,
        requirements: list[dict],
        safety_parameters: list[dict],
        asil_level: str | None,
        filename: str,
    ) -> dict:
        seed = self._make_seed("", filename)
        result = self._render_json(
            "design_v1.j2",
            requirements=requirements,
            safety_parameters=safety_parameters,
            asil_level=asil_level,
            filename=filename,
            seed=seed,
        )
        assert isinstance(result, dict)
        return result
