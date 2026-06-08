"""Shared violation dataclass for agent validation layers."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Violation:
    """A single checklist or quality rule violation."""

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
