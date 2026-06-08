"""Requirement quality checker based on G-C050 standards."""

import logging
import re
from typing import Any

from app.agent.violation import Violation

logger = logging.getLogger(__name__)

_MAX_DESCRIPTION_LEN = 500
_MIN_DESCRIPTION_LEN = 10

# G-C050 §4.13 明确的 — ambiguous words and symbols
_AMBIGUOUS_WORDS = ["各自的", "适当", "尽量", "相应的", "合理的", "必要时"]
_AMBIGUOUS_SYMBOLS = ["/", "~"]

# G-C050 §4.14 可验证的 — weak words that make requirements unverifiable
_WEAK_WORDS = [
    "所有",
    "总是",
    "立即",
    "从不",
    "经常",
    "相当的",
    "一般来说",
    "快",
    "慢",
    "可能",
    "大概",
    "左右",
    "等等",
    "易于",
    "方便",
    "充足",
    "足够",
]

# G-C050 §4.2 完整性 — TBD patterns indicating incomplete requirements
# Note: removed \b word boundaries because they fail when markers are
# surrounded by CJK characters (both sides are \w in Unicode mode).
_TBD_PATTERNS = [
    re.compile(r"TBD", re.IGNORECASE),
    re.compile(r"待确定"),
    re.compile(r"待定"),
    re.compile(r"后续补充"),
    re.compile(r"待讨论"),
]

# G-C050 §4.2 完整性 — calibration quantity format: 标定量名称（默认值xxx,可标定）
_CALIBRATION_PATTERN = re.compile(r"[一-龥\w]+\s*（\s*默认值\s*[\d.]+\s*,\s*可标定\s*）")

# G-C050 §4.14 可验证的 — quantifiable patterns (numbers with units/time/range)
_QUANTIFIABLE_PATTERNS = [
    re.compile(r"\d+\s*(ms|s|min|h|us|ns|MHz|Hz|kHz|V|A|Ω|°C|mm|cm|m|km|g|kg|mg|ml|l|%)"),
    re.compile(r"\d+\s*[~到至]\s*\d+"),
    re.compile(r"[±±+-]\s*\d+\.?\d*"),
    re.compile(r"\d+\.?\d*\s*以内"),
    re.compile(r"\d+\.?\d*\s*以上"),
    re.compile(r"\d+\.?\d*\s*以下"),
    re.compile(r"不少于\s*\d+"),
    re.compile(r"不超过\s*\d+"),
    re.compile(r"至少\s*\d+"),
    re.compile(r"至多\s*\d+"),
]

# G-C050 §4.1 不可分割性 — conjunctions suggesting multiple requirements merged
_MERGE_INDICATORS = [
    "并且",
    "同时",
    "以及",
    "又",
    "还",
    "另外",
    "此外",
    "同时需要",
    "且需",
    "还需",
]

# G-C050 §4.6 可实现性 — untestable / unimplementable phrases
_UNTESTABLE_PHRASES = [
    "根据需求",
    "按需",
    "视情况而定",
    "必要时",
    "尽可能",
    "如果能",
    "在适当的时候",
]


class RequirementQualityChecker:
    """Validate requirements against G-C050 quality standards."""

    # ------------------------------------------------------------------
    # Single-requirement checks
    # ------------------------------------------------------------------

    @classmethod
    def validate_atomicity(cls, description: str, req_id: str | None = None) -> list[Violation]:
        """G-C050 §4.1 不可分割性 — each requirement should describe one behavior."""
        violations: list[Violation] = []
        if not description:
            return violations
        found = [w for w in _MERGE_INDICATORS if w in description]
        if len(found) >= 2:
            violations.append(
                Violation(
                    rule_id="G050-401",
                    severity="warning",
                    message=f"Requirement {req_id or ''} may describe multiple behaviors (merge indicators: {', '.join(found)}).",
                    suggestion="Split into separate requirements unless merging improves readability.",
                )
            )
        return violations

    @classmethod
    def validate_completeness(cls, description: str, req_id: str | None = None) -> list[Violation]:
        """G-C050 §4.2 完整性 — no TBD, all necessary info included."""
        violations: list[Violation] = []
        if not description:
            return violations
        for pattern in _TBD_PATTERNS:
            if pattern.search(description):
                violations.append(
                    Violation(
                        rule_id="G050-402",
                        severity="error",
                        message=f"Requirement {req_id or ''} contains incomplete marker (TBD/待确定/待定).",
                        suggestion="Replace TBD with concrete values or conditions before accepting.",
                    )
                )
                break
        return violations

    @classmethod
    def validate_understandability(cls, description: str, req_id: str | None = None) -> list[Violation]:
        """G-C050 §4.3 可理解性 — clear, structured, not overly complex."""
        violations: list[Violation] = []
        if not description:
            return violations
        if len(description) > _MAX_DESCRIPTION_LEN:
            violations.append(
                Violation(
                    rule_id="G050-403",
                    severity="warning",
                    message=f"Requirement {req_id or ''} description is too long ({len(description)} chars).",
                    suggestion="Break into shorter sentences or split into sub-requirements.",
                )
            )
        # Check for deeply nested logic (multiple 如果/或者/并且)
        depth_indicators = description.count("如果") + description.count("或者") + description.count("并且")
        if depth_indicators >= 4:
            violations.append(
                Violation(
                    rule_id="G050-403b",
                    severity="warning",
                    message=f"Requirement {req_id or ''} has deeply nested logic ({depth_indicators} conditional operators).",
                    suggestion="Use structured lists or state diagrams instead of complex nested sentences.",
                )
            )
        return violations

    @classmethod
    def validate_unambiguous(cls, description: str, req_id: str | None = None) -> list[Violation]:
        """G-C050 §4.13 明确的 — no ambiguous words or symbols."""
        violations: list[Violation] = []
        if not description:
            return violations
        for word in _AMBIGUOUS_WORDS:
            if word in description:
                violations.append(
                    Violation(
                        rule_id="G050-413",
                        severity="warning",
                        message=f"Requirement {req_id or ''} contains ambiguous word: '{word}'.",
                        suggestion="Replace with precise, quantifiable description.",
                    )
                )
        for sym in _AMBIGUOUS_SYMBOLS:
            if sym in description:
                violations.append(
                    Violation(
                        rule_id="G050-413b",
                        severity="warning",
                        message=f"Requirement {req_id or ''} contains ambiguous symbol: '{sym}'.",
                        suggestion="Replace '/' with '或' and '~' with explicit range (e.g., '0至100').",
                    )
                )
        return violations

    @classmethod
    def validate_verifiable(cls, description: str, req_id: str | None = None) -> list[Violation]:
        """G-C050 §4.14 可验证的 — quantifiable, no weak words."""
        violations: list[Violation] = []
        if not description:
            return violations
        for word in _WEAK_WORDS:
            if word in description:
                violations.append(
                    Violation(
                        rule_id="G050-414",
                        severity="error",
                        message=f"Requirement {req_id or ''} contains unverifiable weak word: '{word}'.",
                        suggestion="Replace with quantifiable thresholds (e.g., '2s内' instead of '立即').",
                    )
                )
        has_quantifiable = any(p.search(description) for p in _QUANTIFIABLE_PATTERNS)
        if not has_quantifiable:
            violations.append(
                Violation(
                    rule_id="G050-414b",
                    severity="warning",
                    message=f"Requirement {req_id or ''} lacks quantifiable acceptance criteria.",
                    suggestion="Add explicit numeric thresholds, ranges, units, or time bounds.",
                )
            )
        return violations

    @classmethod
    def validate_feasibility(cls, description: str, req_id: str | None = None) -> list[Violation]:
        """G-C050 §4.6 可实现性 — implementable and testable."""
        violations: list[Violation] = []
        if not description:
            return violations
        for phrase in _UNTESTABLE_PHRASES:
            if phrase in description:
                violations.append(
                    Violation(
                        rule_id="G050-406",
                        severity="error",
                        message=f"Requirement {req_id or ''} contains untestable phrase: '{phrase}'.",
                        suggestion="Replace with concrete, measurable conditions.",
                    )
                )
        return violations

    @classmethod
    def validate_conciseness(cls, description: str, req_id: str | None = None) -> list[Violation]:
        """G-C050 §4.10 简洁性 — no redundant or irrelevant info."""
        violations: list[Violation] = []
        if not description:
            return violations
        # Check for trailing notes that are conclusions/explanations rather than requirements
        if "因此" in description or "所以" in description or "综上所述" in description:
            violations.append(
                Violation(
                    rule_id="G050-410",
                    severity="info",
                    message=f"Requirement {req_id or ''} contains conclusion words (因此/所以/综上所述).",
                    suggestion="Move conclusions to remarks; keep requirement description concise.",
                )
            )
        return violations

    @classmethod
    def validate_description(cls, description: str, req_id: str | None = None) -> list[Violation]:
        """Run all single-requirement quality checks on a description."""
        violations: list[Violation] = []
        if not description or len(description.strip()) < _MIN_DESCRIPTION_LEN:
            violations.append(
                Violation(
                    rule_id="G050-000",
                    severity="error",
                    message=f"Requirement {req_id or ''} description is too short or empty.",
                    suggestion="Provide a clear, complete requirement description.",
                )
            )
            return violations
        violations.extend(cls.validate_atomicity(description, req_id))
        violations.extend(cls.validate_completeness(description, req_id))
        violations.extend(cls.validate_understandability(description, req_id))
        violations.extend(cls.validate_unambiguous(description, req_id))
        violations.extend(cls.validate_verifiable(description, req_id))
        violations.extend(cls.validate_feasibility(description, req_id))
        violations.extend(cls.validate_conciseness(description, req_id))
        return violations

    # ------------------------------------------------------------------
    # Tree-level checks
    # ------------------------------------------------------------------

    @classmethod
    def validate_consistency(cls, nodes: list[dict]) -> list[Violation]:
        """G-C050 §4.4 一致性 — detect duplicate requirement_ids within tree."""
        violations: list[Violation] = []
        seen_ids: dict[str, int] = {}

        def _collect_ids(node_list: list[dict]) -> None:
            for n in node_list:
                req_id = n.get("requirement_id")
                if req_id:
                    seen_ids[req_id] = seen_ids.get(req_id, 0) + 1
                children = n.get("children") or []
                if children:
                    _collect_ids(children)

        _collect_ids(nodes)
        for req_id, count in seen_ids.items():
            if count > 1:
                violations.append(
                    Violation(
                        rule_id="G050-404",
                        severity="error",
                        message=f"Duplicate requirement_id in tree: {req_id} (appears {count} times).",
                        suggestion="Ensure every requirement ID is unique across the entire tree.",
                    )
                )
        return violations

    @classmethod
    def validate_traceability(cls, nodes: list[dict]) -> list[Violation]:
        """G-C050 §4.12 可追溯性 — check ID format and parent linkage."""
        violations: list[Violation] = []
        id_pattern = re.compile(r"^SW-REQ-\d{3}(-\d{2})?$")

        def _check(node_list: list[dict], parent_id: str | None = None) -> None:
            for n in node_list:
                req_id = n.get("requirement_id")
                if req_id and not id_pattern.match(req_id):
                    violations.append(
                        Violation(
                            rule_id="G050-412",
                            severity="warning",
                            message=f"Requirement ID '{req_id}' does not match expected format SW-REQ-NNN or SW-REQ-NNN-NN.",
                            suggestion="Use SW-REQ- followed by exactly 3 digits, optionally -NN for sub-items.",
                        )
                    )
                # chapter traceability
                chapter = n.get("chapter")
                if not chapter:
                    violations.append(
                        Violation(
                            rule_id="G050-412b",
                            severity="info",
                            message=f"Requirement {req_id or ''} missing chapter/source reference.",
                            suggestion="Add the source document chapter to enable traceability.",
                        )
                    )
                children = n.get("children") or []
                if children:
                    _check(children, req_id)

        _check(nodes)
        return violations

    @classmethod
    def validate_requirement(cls, req: dict) -> list[Violation]:
        """Run all checks against a single requirement node (flat or tree)."""
        violations: list[Violation] = []
        req_id = req.get("requirement_id")
        description = req.get("description")
        violations.extend(cls.validate_description(description, req_id))
        return violations

    @classmethod
    def validate_tree(cls, nodes: list[dict]) -> list[Violation]:
        """Run all G-C050 checks against a requirement tree."""
        violations: list[Violation] = []
        violations.extend(cls.validate_consistency(nodes))
        violations.extend(cls.validate_traceability(nodes))

        def _walk(node_list: list[dict]) -> None:
            for n in node_list:
                violations.extend(cls.validate_requirement(n))
                children = n.get("children") or []
                if children:
                    _walk(children)

        _walk(nodes)
        return violations

    @classmethod
    def validate_flat(cls, requirements: list[dict]) -> list[Violation]:
        """Run all G-C050 checks against a flat requirement list."""
        violations: list[Violation] = []
        seen_ids: set[str] = set()
        for req in requirements:
            req_id = req.get("requirement_id")
            if req_id:
                if req_id in seen_ids:
                    violations.append(
                        Violation(
                            rule_id="G050-404",
                            severity="error",
                            message=f"Duplicate requirement_id in flat list: {req_id}.",
                            suggestion="Ensure every requirement ID is unique.",
                        )
                    )
                seen_ids.add(req_id)
            violations.extend(cls.validate_requirement(req))
        return violations

    @classmethod
    def summarize(cls, violations: list[Violation]) -> dict[str, Any]:
        """Return a summary of violations grouped by severity."""
        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]
        infos = [v for v in violations if v.severity == "info"]
        return {
            "total": len(violations),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "info_count": len(infos),
            "errors": [v.to_dict() for v in errors],
            "warnings": [v.to_dict() for v in warnings],
            "infos": [v.to_dict() for v in infos],
            "pass": len(violations) == 0,
        }
