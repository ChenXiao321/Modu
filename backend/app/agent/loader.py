"""Load user-provided process documents and checklists from disk."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_PROCESSES_DIR = Path(__file__).parent / "processes"
_DEFAULT_CHECKLISTS_DIR = Path(__file__).parent / "checklists"


def _load_markdown_file(path: Path) -> str:
    """Read a Markdown file; return empty string if missing or unreadable."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        logger.warning("Failed to read Markdown file: %s", path)
        return ""


def _load_json_file(path: Path) -> dict[str, Any] | list[Any]:
    """Parse a JSON file; return empty dict on failure."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, (dict, list)):
                return data
            return {}
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to parse JSON file: %s", path)
        return {}


def load_process_documents(directory: Path | None = None) -> dict[str, str]:
    """Scan the processes directory and load all Markdown process documents.

    Returns a dict mapping filename (without extension) -> content.
    """
    dir_path = directory or _DEFAULT_PROCESSES_DIR
    if not dir_path.exists():
        logger.info("Processes directory does not exist: %s", dir_path)
        return {}

    docs: dict[str, str] = {}
    for path in sorted(dir_path.glob("*.md")):
        content = _load_markdown_file(path)
        if content:
            docs[path.stem] = content
    logger.info("Loaded %d process document(s) from %s", len(docs), dir_path)
    return docs


def load_checklists(directory: Path | None = None) -> list[dict[str, Any]]:
    """Scan the checklists directory and load all checklist files.

    Supports both .md (free-form text, parsed heuristically) and .json
    (structured rule definitions).

    Returns a list of rule dicts.
    """
    dir_path = directory or _DEFAULT_CHECKLISTS_DIR
    if not dir_path.exists():
        logger.info("Checklists directory does not exist: %s", dir_path)
        return []

    rules: list[dict[str, Any]] = []

    # JSON checklists take precedence for structured rules
    for path in sorted(dir_path.glob("*.json")):
        data = _load_json_file(path)
        if isinstance(data, list):
            rules.extend(data)
        elif isinstance(data, dict) and "rules" in data:
            rules.extend(data["rules"])

    # Markdown checklists are parsed heuristically for now
    for path in sorted(dir_path.glob("*.md")):
        content = _load_markdown_file(path)
        if not content:
            continue
        # Simple heuristic: lines starting with "- [ ]" or "- [x]" are checklist items
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith(("- [ ]", "- [x]")):
                text = stripped[5:].strip()
                if text:
                    rules.append({
                        "rule_id": f"USER-MD-{path.stem}-{len(rules)}",
                        "severity": "warning",
                        "message": text,
                        "source": str(path),
                    })

    logger.info("Loaded %d checklist rule(s) from %s", len(rules), dir_path)
    return rules


def get_step_config(process_docs: dict[str, str], step_name: str) -> dict[str, Any]:
    """Extract step-specific configuration from loaded process documents.

    For MVP, returns an empty dict; future versions can parse structured
    frontmatter from Markdown to provide per-step constraints.
    """
    return {}
