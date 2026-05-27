import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


class TemplateLoader:
    """Load and render Jinja2 templates for LLM prompt/output generation."""

    _env: Environment | None = None

    @classmethod
    def _get_env(cls) -> Environment:
        if cls._env is None:
            # Templates live alongside this file under ../templates/
            template_dir = Path(__file__).parent.parent / "templates"
            cls._env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(),
                trim_blocks=True,
                lstrip_blocks=True,
            )
            # Register a json filter so templates can emit raw JSON when needed
            cls._env.filters["tojson"] = json.dumps
        return cls._env

    @classmethod
    def render(cls, template_name: str, **context: object) -> str:
        """Render a template with the given context."""
        env = cls._get_env()
        template = env.get_template(template_name)
        return template.render(**context)
