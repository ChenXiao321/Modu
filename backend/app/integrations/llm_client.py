from abc import ABC, abstractmethod


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


class MockLLMClient(LLMClient):
    """
    Mock LLM client for MVP development and testing.
    Returns deterministic simulated requirements based on document text length.
    """

    def extract_requirements(self, document_text: str, filename: str) -> list[dict]:
        text_length = len(document_text)
        base_id = f"SW-REQ-{text_length % 1000:03d}"

        return [
            {
                "requirement_id": base_id,
                "description": (
                    f"System shall process input signals from {filename} "
                    f"with deterministic timing constraints."
                ),
                "chapter": "3.1",
                "asil_level": "B",
                "parent_requirement_id": None,
                "children": [
                    {
                        "requirement_id": f"{base_id}-01",
                        "description": (
                            "The module shall initialize all hardware registers "
                            "to safe default values within 100ms after power-on."
                        ),
                        "chapter": "3.1.1",
                        "asil_level": "B",
                        "parent_requirement_id": base_id,
                        "children": [],
                    },
                    {
                        "requirement_id": f"{base_id}-02",
                        "description": (
                            "The module shall monitor supply voltage and trigger "
                            "safe state if voltage drops below 4.5V."
                        ),
                        "chapter": "3.1.2",
                        "asil_level": "B",
                        "parent_requirement_id": base_id,
                        "children": [],
                    },
                ],
            },
            {
                "requirement_id": f"{base_id}-FUNC",
                "description": (
                    "System shall provide diagnostic interface for fault detection "
                    "and reporting via standard UDS services."
                ),
                "chapter": "4.2",
                "asil_level": None,
                "parent_requirement_id": None,
                "children": [
                    {
                        "requirement_id": f"{base_id}-FUNC-01",
                        "description": (
                            "DTC shall be stored in non-volatile memory "
                            "with timestamp and occurrence counter."
                        ),
                        "chapter": "4.2.1",
                        "asil_level": None,
                        "parent_requirement_id": f"{base_id}-FUNC",
                        "children": [],
                    }
                ],
            },
        ]

    def extract_safety_parameters(self, document_text: str, filename: str) -> list[dict]:
        """Return deterministic mock safety-critical parameters."""
        # Seed-based deterministic selection to keep tests stable
        text_length = len(document_text)

        parameters = [
            {
                "parameter_id": "SW-REQ-SAF-001",
                "name": "供电电压阈值",
                "value": "4.5",
                "unit": "V",
                "tolerance": "±0.1",
                "chapter": "3.2.1",
                "source_page": 42,
            },
            {
                "parameter_id": "SW-REQ-SAF-002",
                "name": "工作温度范围",
                "value": "-40 ~ 150",
                "unit": "°C",
                "tolerance": None,
                "chapter": "3.2.2",
                "source_page": 43,
            },
            {
                "parameter_id": "SW-REQ-SAF-003",
                "name": "看门狗喂狗周期",
                "value": "50",
                "unit": "ms",
                "tolerance": "±5",
                "chapter": "3.3.1",
                "source_page": 48,
            },
            {
                "parameter_id": "SW-REQ-SAF-004",
                "name": "初始化超时时间",
                "value": "100",
                "unit": "ms",
                "tolerance": "+10/-0",
                "chapter": "3.1.1",
                "source_page": 38,
            },
        ]

        # Deterministically return a subset; short/empty docs may get zero params
        count = min(len(parameters), text_length % 4)
        return parameters[:count]

    def extract_ocr_fields(self, document_text: str, filename: str) -> list[dict]:
        """Return deterministic mock OCR fields with confidence scores."""
        text_length = len(document_text)

        fields = [
            {
                "field_id": "OCR-FIELD-0001",
                "extracted_text": "4.5V ±0.1",
                "normalized_value": "4.5",
                "confidence": 0.98,
                "field_type": "voltage",
                "source_page": 42,
            },
            {
                "field_id": "OCR-FIELD-0002",
                "extracted_text": "-40 ~ 150°C",
                "normalized_value": "-40~150",
                "confidence": 0.96,
                "field_type": "temperature",
                "source_page": 43,
            },
            {
                "field_id": "OCR-FIELD-0003",
                "extracted_text": "50 ms (±5)",
                "normalized_value": "50",
                "confidence": 0.72,
                "field_type": "timing",
                "source_page": 48,
            },
            {
                "field_id": "OCR-FIELD-0004",
                "extracted_text": "l00ms init timeout",
                "normalized_value": "100",
                "confidence": 0.65,
                "field_type": "timing",
                "source_page": 38,
            },
            {
                "field_id": "OCR-FIELD-0005",
                "extracted_text": "3.3V reference",
                "normalized_value": "3.3",
                "confidence": 0.91,
                "field_type": "voltage",
                "source_page": 45,
            },
        ]

        # Return a stable subset for testing: always return fields 1-3 to ensure
        # both high-confidence and low-confidence fields are present.
        count = min(len(fields), 3)
        return fields[:count]
