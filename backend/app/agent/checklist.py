"""Checklist validation layer for Agent workflow steps."""

import logging
import re
from typing import Any

from app.agent.quality_checker import RequirementQualityChecker
from app.agent.violation import Violation

logger = logging.getLogger(__name__)

_ASIL_LEVELS = {"A", "B", "C", "D", "QM"}
_MAX_TREE_DEPTH = 10
_MAX_REQUIREMENT_ID_LEN = 50


class BuiltInRules:
    """Hard-coded validation rules that cannot be overridden by user checklists."""

    @staticmethod
    def validate_requirement_id(req_id: str) -> list[Violation]:
        violations: list[Violation] = []
        if not req_id:
            violations.append(
                Violation(
                    rule_id="BUILTIN-001",
                    severity="error",
                    message="requirement_id is empty",
                    suggestion="Assign a unique requirement ID (e.g., SW-REQ-001).",
                )
            )
            return violations
        if len(req_id) > _MAX_REQUIREMENT_ID_LEN:
            violations.append(
                Violation(
                    rule_id="BUILTIN-002",
                    severity="error",
                    message=f"requirement_id exceeds max length {_MAX_REQUIREMENT_ID_LEN}: {req_id}",
                    suggestion=f"Shorten the ID to ≤ {_MAX_REQUIREMENT_ID_LEN} characters.",
                )
            )
        if not re.match(r"^[A-Za-z0-9\-_\.]+$", req_id):
            violations.append(
                Violation(
                    rule_id="BUILTIN-003",
                    severity="warning",
                    message=f"requirement_id contains invalid characters: {req_id}",
                    suggestion="Use only alphanumeric, hyphen, underscore, and dot characters.",
                )
            )
        return violations

    @staticmethod
    def validate_asil_level(asil: str | None) -> list[Violation]:
        if asil is None:
            return []
        if asil.upper() not in _ASIL_LEVELS:
            return [
                Violation(
                    rule_id="BUILTIN-004",
                    severity="error",
                    message=f"Invalid ASIL level: {asil}. Must be one of {_ASIL_LEVELS}.",
                    suggestion="Correct the ASIL level to A, B, C, D, or QM.",
                )
            ]
        return []

    @staticmethod
    def validate_tree_depth(nodes: list[dict], current_depth: int = 1) -> list[Violation]:
        violations: list[Violation] = []
        if current_depth > _MAX_TREE_DEPTH:
            violations.append(
                Violation(
                    rule_id="BUILTIN-005",
                    severity="error",
                    message=f"Requirement tree depth exceeds maximum limit ({_MAX_TREE_DEPTH}).",
                    suggestion="Flatten deeply nested requirements or split into separate documents.",
                )
            )
            return violations
        for node in nodes:
            children = node.get("children") or []
            if children:
                violations.extend(
                    BuiltInRules.validate_tree_depth(children, current_depth + 1)
                )
        return violations

    @staticmethod
    def validate_no_cycles(nodes: list[dict], ancestor_ids: set[str] | None = None) -> list[Violation]:
        violations: list[Violation] = []
        if ancestor_ids is None:
            ancestor_ids = set()
        for node in nodes:
            req_id = node.get("requirement_id")
            if req_id and req_id in ancestor_ids:
                violations.append(
                    Violation(
                        rule_id="BUILTIN-006",
                        severity="error",
                        message=f"Circular reference detected for requirement_id: {req_id}.",
                        suggestion="Remove the circular parent-child relationship.",
                    )
                )
            children = node.get("children") or []
            if children:
                new_ancestors = set(ancestor_ids)
                if req_id:
                    new_ancestors.add(req_id)
                violations.extend(BuiltInRules.validate_no_cycles(children, new_ancestors))
        return violations

    @staticmethod
    def validate_required_fields(node: dict) -> list[Violation]:
        violations: list[Violation] = []
        if not node.get("requirement_id"):
            violations.append(
                Violation(
                    rule_id="BUILTIN-007",
                    severity="error",
                    message="Requirement node is missing 'requirement_id'.",
                    suggestion="Every requirement must have a unique ID.",
                )
            )
        if not node.get("description"):
            violations.append(
                Violation(
                    rule_id="BUILTIN-008",
                    severity="error",
                    message="Requirement node is missing 'description'.",
                    suggestion="Every requirement must have a description.",
                )
            )
        return violations

    @classmethod
    def validate_requirement_tree(cls, nodes: list[dict]) -> list[Violation]:
        """Run all built-in rules against a requirement tree."""
        violations: list[Violation] = []

        # Collect all nodes flat for ID/ASIL/field checks
        def collect(node_list: list[dict]) -> list[dict]:
            flat: list[dict] = []
            for n in node_list:
                flat.append(n)
                children = n.get("children") or []
                flat.extend(collect(children))
            return flat

        all_nodes = collect(nodes)
        seen_ids: set[str] = set()
        for node in all_nodes:
            req_id = node.get("requirement_id")
            violations.extend(cls.validate_required_fields(node))
            if req_id:
                violations.extend(cls.validate_requirement_id(req_id))
                if req_id in seen_ids:
                    violations.append(
                        Violation(
                            rule_id="BUILTIN-009",
                            severity="error",
                            message=f"Duplicate requirement_id: {req_id}.",
                            suggestion="Ensure every requirement ID is unique.",
                        )
                    )
                seen_ids.add(req_id)
            asil = node.get("asil_level")
            violations.extend(cls.validate_asil_level(asil))

        violations.extend(cls.validate_tree_depth(nodes))
        violations.extend(cls.validate_no_cycles(nodes))
        return violations

    @classmethod
    def validate_flat_requirements(cls, requirements: list[dict]) -> list[Violation]:
        """Run built-in rules against a flat requirement list (before hierarchy)."""
        violations: list[Violation] = []
        seen_ids: set[str] = set()
        for req in requirements:
            req_id = req.get("requirement_id")
            description = req.get("description")
            if not req_id or not description:
                violations.append(
                    Violation(
                        rule_id="BUILTIN-010",
                        severity="error",
                        message="Flat requirement missing requirement_id or description.",
                        suggestion="Ensure every extracted requirement has both ID and description.",
                    )
                )
                continue
            violations.extend(cls.validate_requirement_id(req_id))
            if req_id in seen_ids:
                violations.append(
                    Violation(
                        rule_id="BUILTIN-009",
                        severity="error",
                        message=f"Duplicate requirement_id in flat list: {req_id}.",
                        suggestion="Ensure every requirement ID is unique.",
                    )
                )
            seen_ids.add(req_id)
            asil = req.get("asil_level")
            violations.extend(cls.validate_asil_level(asil))
        return violations

    @classmethod
    def validate_fc_identification(cls, output: dict) -> list[Violation]:
        """Validate FC identification step output."""
        violations: list[Violation] = []
        fc_list = output.get("fc_list")
        if not isinstance(fc_list, list) or not fc_list:
            violations.append(
                Violation(
                    rule_id="BUILTIN-011",
                    severity="error",
                    message="fc_list is missing or empty.",
                    suggestion="At least one Functional Component (FC) must be identified.",
                )
            )
            return violations

        seen_fc_ids: set[str] = set()
        for idx, fc in enumerate(fc_list):
            if not isinstance(fc, dict):
                violations.append(
                    Violation(
                        rule_id="BUILTIN-012",
                        severity="error",
                        message=f"fc_list[{idx}] is not a dict.",
                        suggestion="Each FC must be a JSON object.",
                    )
                )
                continue
            fc_id = fc.get("fc_id")
            if not fc_id:
                violations.append(
                    Violation(
                        rule_id="BUILTIN-013",
                        severity="error",
                        message=f"fc_list[{idx}] missing fc_id.",
                        suggestion="Every FC must have a unique fc_id (e.g., FC-001).",
                    )
                )
            else:
                if fc_id in seen_fc_ids:
                    violations.append(
                        Violation(
                            rule_id="BUILTIN-014",
                            severity="error",
                            message=f"Duplicate fc_id: {fc_id}.",
                            suggestion="Ensure every FC ID is unique.",
                        )
                    )
                seen_fc_ids.add(fc_id)
                if not re.match(r"^FC-\d+$", str(fc_id)):
                    violations.append(
                        Violation(
                            rule_id="BUILTIN-015",
                            severity="warning",
                            message=f"fc_id format warning: {fc_id}. Expected format: FC-NNN.",
                            suggestion="Use FC- followed by digits (e.g., FC-001).",
                        )
                    )

            if not fc.get("fc_name"):
                violations.append(
                    Violation(
                        rule_id="BUILTIN-016",
                        severity="error",
                        message=f"FC {fc_id or idx} missing fc_name.",
                        suggestion="Every FC must have a name.",
                    )
                )
            if not fc.get("description"):
                violations.append(
                    Violation(
                        rule_id="BUILTIN-017",
                        severity="error",
                        message=f"FC {fc_id or idx} missing description.",
                        suggestion="Every FC must have a description.",
                    )
                )

            asil = fc.get("asil_level")
            violations.extend(cls.validate_asil_level(asil))

            assigned = fc.get("assigned_requirements")
            if not isinstance(assigned, list) or not assigned:
                violations.append(
                    Violation(
                        rule_id="BUILTIN-018",
                        severity="warning",
                        message=f"FC {fc_id or idx} has no assigned_requirements.",
                        suggestion="Each FC should be assigned at least one requirement.",
                    )
                )

        return violations

    @classmethod
    def validate_detailed_design(cls, output: dict) -> list[Violation]:
        """Validate detailed design step output."""
        violations: list[Violation] = []

        if not output.get("project_number"):
            violations.append(
                Violation(
                    rule_id="BUILTIN-019",
                    severity="warning",
                    message="project_number is missing.",
                    suggestion="Include a project number for traceability.",
                )
            )

        fc_architecture = output.get("fc_architecture")
        if not isinstance(fc_architecture, dict):
            violations.append(
                Violation(
                    rule_id="BUILTIN-020",
                    severity="error",
                    message="fc_architecture is missing or not a dict.",
                    suggestion="fc_architecture must be a JSON object describing the FC modules.",
                )
            )
        else:
            fc_modules = fc_architecture.get("fc_modules")
            if not isinstance(fc_modules, list) or not fc_modules:
                violations.append(
                    Violation(
                        rule_id="BUILTIN-021",
                        severity="error",
                        message="fc_architecture.fc_modules is missing or empty.",
                        suggestion="At least one FC module must be defined.",
                    )
                )

        detailed_design = output.get("detailed_design")
        if not isinstance(detailed_design, list) or not detailed_design:
            violations.append(
                Violation(
                    rule_id="BUILTIN-022",
                    severity="error",
                    message="detailed_design is missing or empty.",
                    suggestion="At least one FC must have detailed design entries.",
                )
            )

        safety_design = output.get("safety_design")
        if isinstance(safety_design, dict):
            redundancy = safety_design.get("redundancy_measures")
            fault = safety_design.get("fault_handling")
            if not redundancy or not fault:
                violations.append(
                    Violation(
                        rule_id="BUILTIN-023",
                        severity="warning",
                        message="safety_design missing redundancy_measures or fault_handling.",
                        suggestion="ASIL-C/D modules must include redundancy and fault handling.",
                    )
                )

        return violations


class ChecklistValidator:
    """Merge user-provided checklists with built-in rules and validate step outputs."""

    def __init__(self, user_rules: list[dict] | None = None) -> None:
        # user_rules: [{"rule_id": "...", "severity": "...", "check": callable, ...}]
        self.user_rules = user_rules or []

    def validate(self, step_name: str, output: Any) -> list[Violation]:
        """Validate the output of a completed step.

        Returns a list of Violation objects. Built-in rules are always evaluated;
        user rules are applied on top.
        """
        violations: list[Violation] = []

        # Built-in rules per step type
        if step_name == "02_requirement_extraction":
            if isinstance(output, list):
                violations.extend(BuiltInRules.validate_flat_requirements(output))
                violations.extend(RequirementQualityChecker.validate_flat(output))
        elif step_name == "03_asil_verification":
            if isinstance(output, dict):
                reqs = output.get("requirements") or []
                if isinstance(reqs, list):
                    violations.extend(BuiltInRules.validate_flat_requirements(reqs))
                    violations.extend(RequirementQualityChecker.validate_flat(reqs))
        elif step_name == "04_hierarchy_resolution":
            if isinstance(output, list):
                violations.extend(BuiltInRules.validate_requirement_tree(output))
                violations.extend(RequirementQualityChecker.validate_tree(output))
        elif step_name == "design_01_fc_identification":
            if isinstance(output, dict):
                violations.extend(BuiltInRules.validate_fc_identification(output))
        elif step_name == "design_02_detailed_design":
            if isinstance(output, dict):
                violations.extend(BuiltInRules.validate_detailed_design(output))

        # Apply user-defined rules (placeholder for future expansion)
        for rule in self.user_rules:
            if rule.get("applies_to") and step_name not in rule["applies_to"]:
                continue
            # User rules could contain a callable or a regex pattern; for now
            # we store them structurally and rely on external rule loaders.

        return violations
