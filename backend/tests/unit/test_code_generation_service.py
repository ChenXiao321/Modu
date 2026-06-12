from pathlib import Path

from app.agent.steps import CodeSourceGenerationStep, build_code_generation_steps
from app.services.code_generation_service import CodeGenerationService


class TestCodeGenerationService:
    def test_extract_trace_mapping_new_format(self):
        """Extract trace mapping from new detailed_design format (functions nested under fc_id)."""
        detailed_design = [
            {
                "fc_id": "FC-001",
                "functions": [
                    {
                        "function_name": "WdgM_Init",
                        "purpose": "Initialize watchdog module",
                        "assigned_requirements": ["SW-REQ-001", "SW-REQ-002"],
                    },
                    {
                        "function_name": "WdgM_Run",
                        "purpose": "Run watchdog logic",
                        "assigned_requirements": ["SW-REQ-003"],
                    },
                ],
            }
        ]
        mapping = CodeGenerationService._extract_trace_mapping(detailed_design)
        assert mapping == {
            "WdgM_Init": ["SW-REQ-001", "SW-REQ-002"],
            "WdgM_Run": ["SW-REQ-003"],
        }

    def test_extract_trace_mapping_old_format(self):
        """Backward compatibility: extract from flat array format."""
        detailed_design = [
            {
                "function_name": "MockModule_Init",
                "return_type": "void",
                "assigned_requirements": ["SW-REQ-010"],
            }
        ]
        mapping = CodeGenerationService._extract_trace_mapping(detailed_design)
        assert mapping == {"MockModule_Init": ["SW-REQ-010"]}

    def test_extract_trace_mapping_empty(self):
        """Graceful handling when assigned_requirements is missing."""
        detailed_design = [
            {
                "fc_id": "FC-001",
                "functions": [
                    {"function_name": "WdgM_Init", "purpose": "Initialize"},
                ],
            }
        ]
        mapping = CodeGenerationService._extract_trace_mapping(detailed_design)
        assert mapping == {}

    def test_derive_polarion_trace_id_from_content(self):
        """Derive trace ID from function-level TRACE-ID markers in content."""
        file_dict = {
            "content": (
                "/* TRACE-ID: SW-REQ-001 */\n"
                "void WdgM_Init(void)\n{}\n"
                "/* TRACE-ID: SW-REQ-002 */\n"
                "void WdgM_Run(void)\n{}\n"
            )
        }
        result = CodeGenerationService._derive_polarion_trace_id(file_dict, {})
        assert result == "SW-REQ-001,SW-REQ-002"

    def test_derive_polarion_trace_id_dedup(self):
        """Duplicate TRACE-IDs should be deduplicated."""
        file_dict = {
            "content": (
                "/* TRACE-ID: SW-REQ-001 */\n"
                "void WdgM_Init(void)\n{}\n"
                "/* TRACE-ID: SW-REQ-001 */\n"
                "void WdgM_Run(void)\n{}\n"
            )
        }
        result = CodeGenerationService._derive_polarion_trace_id(file_dict, {})
        assert result == "SW-REQ-001"

    def test_derive_polarion_trace_id_fallback(self):
        """Fallback to module-level trace ID when no function markers found."""
        file_dict = {"content": "void WdgM_Init(void)\n{}\n"}
        result = CodeGenerationService._derive_polarion_trace_id(file_dict, {})
        assert result == "POL-CODE-MODULE"

    def test_derive_polarion_trace_id_from_trace_mapping_fallback(self):
        """Fallback to trace_mapping requirement IDs when content markers are absent."""
        file_dict = {"content": "void WdgM_Init(void)\n{}\n"}
        trace_mapping = {"WdgM_Init": ["SW-REQ-001", "SW-REQ-002"]}
        result = CodeGenerationService._derive_polarion_trace_id(file_dict, trace_mapping)
        assert result == "SW-REQ-001,SW-REQ-002"

    def test_normalize_asil_variants(self):
        """ASIL values in various formats normalize to A/B/C/D/QM."""
        assert CodeGenerationService._normalize_asil("ASIL-B") == "B"
        assert CodeGenerationService._normalize_asil("b") == "B"
        assert CodeGenerationService._normalize_asil("ASIL_D") == "D"
        assert CodeGenerationService._normalize_asil("QM") == "QM"
        assert CodeGenerationService._normalize_asil("") == "QM"
        assert CodeGenerationService._normalize_asil("UNKNOWN") == "QM"

    def test_build_asil_context_coverage_display(self):
        """Verify ASIL context includes human-readable coverage target display."""
        context = CodeGenerationService._build_asil_context("B", {"fc_modules": []})
        assert context["coverage_targets_display"] == "statement=90%, branch=80%, MC/DC=50%"

    def test_build_asil_context_qm_display_empty(self):
        """Verify QM ASIL produces empty coverage display."""
        context = CodeGenerationService._build_asil_context("QM", {"fc_modules": []})
        assert context["coverage_targets_display"] == ""

    def test_build_asil_context_normalizes_fc_asil(self):
        """Verify FC-level ASIL values are normalized in the context mapping."""
        fc_arch = {
            "fc_modules": [
                {"fc_id": "FC-001", "asil_level": "ASIL-C"},
                {"fc_id": "FC-002", "asil_level": "d"},
            ]
        }
        context = CodeGenerationService._build_asil_context("B", fc_arch)
        assert context["fc_asil_mapping"] == {"FC-001": "C", "FC-002": "D"}

    def test_build_code_generation_steps_with_config(self):
        """Verify build_code_generation_steps accepts config parameters."""

        template_dir = Path(__file__).parent.parent.parent / "app" / "agent" / "prompts"
        steps = build_code_generation_steps(
            template_dir,
            template_version="2.0.0",
            naming_convention="camelCase",
            trace_mapping={"WdgM_Init": ["SW-REQ-001"]},
        )
        assert len(steps) == 2
        # Verify the second step (CodeSourceGenerationStep) carries config

        assert isinstance(steps[1], CodeSourceGenerationStep)
        assert steps[1].template_version == "2.0.0"
        assert steps[1].naming_convention == "camelCase"
        assert steps[1].trace_mapping == {"WdgM_Init": ["SW-REQ-001"]}

    def test_build_code_generation_steps_with_asil(self):
        """Verify build_code_generation_steps accepts ASIL parameters."""

        template_dir = Path(__file__).parent.parent.parent / "app" / "agent" / "prompts"
        steps = build_code_generation_steps(
            template_dir,
            asil_level="B",
            asil_context={
                "fc_asil_mapping": {"FC-001": "B"},
                "coverage_targets": {"statement": 90},
            },
        )
        assert len(steps) == 2

        assert isinstance(steps[1], CodeSourceGenerationStep)
        assert steps[1].asil_level == "B"
        assert steps[1].asil_context["fc_asil_mapping"]["FC-001"] == "B"

    def test_build_asil_context_with_coverage_targets(self):
        """Verify ASIL context builds correct coverage targets from config."""
        fc_arch = {
            "fc_modules": [
                {"fc_id": "FC-001", "asil_level": "B"},
                {"fc_id": "FC-002", "asil_level": "A"},
            ]
        }
        context = CodeGenerationService._build_asil_context("B", fc_arch)
        assert context["fc_asil_mapping"] == {"FC-001": "B", "FC-002": "A"}
        assert context["coverage_targets"]["statement"] == 90
        assert context["coverage_targets"]["branch"] == 80
        assert context["coverage_targets"]["mcdc"] == 50

    def test_build_asil_context_qm_fallback(self):
        """Verify QM ASIL falls back to empty coverage targets."""
        context = CodeGenerationService._build_asil_context("QM", {"fc_modules": []})
        assert context["fc_asil_mapping"] == {}
        assert context["coverage_targets"] == {}
