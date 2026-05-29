"""Checklist validation layer for Agent workflow steps."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_ASIL_LEVELS = {"A", "B", "C", "D", "QM"}
_MAX_TREE_DEPTH = 10
_MAX_REQUIREMENT_ID_LEN = 50


@dataclass
class Violation:
    """A single checklist violation."""

    rule_id: str
    severity: str  # error | warning | info
    message: str
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion,
        }


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
        elif step_name == "03_asil_verification":
            if isinstance(output, dict):
                reqs = output.get("requirements") or []
                if isinstance(reqs, list):
                    violations.extend(BuiltInRules.validate_flat_requirements(reqs))
        elif step_name == "04_hierarchy_resolution":
            if isinstance(output, list):
                violations.extend(BuiltInRules.validate_requirement_tree(output))

        # Apply user-defined rules (placeholder for future expansion)
        for rule in self.user_rules:
            if rule.get("applies_to") and step_name not in rule["applies_to"]:
                continue
            # User rules could contain a callable or a regex pattern; for now
            # we store them structurally and rely on external rule loaders.

        return violations
