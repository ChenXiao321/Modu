import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from app.integrations.llm_client import LLMClient, LLMInvocationError, LLMOutputFormatError
from app.integrations.template_loader import TemplateLoader

logger = logging.getLogger(__name__)

MAX_RETRY_PER_STEP = 3


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowContext:
    """Immutable context passed through every step."""

    document_text: str
    filename: str
    tenant_id: int
    document_id: str
    previous_outputs: dict[str, Any] = field(default_factory=dict)

    def with_output(self, step_name: str, output: Any) -> "WorkflowContext":
        """Return a new context with the given step output added."""
        new_outputs = dict(self.previous_outputs)
        new_outputs[step_name] = output
        return WorkflowContext(
            document_text=self.document_text,
            filename=self.filename,
            tenant_id=self.tenant_id,
            document_id=self.document_id,
            previous_outputs=new_outputs,
        )


@dataclass
class StepResult:
    output: Any
    raw_llm_response: str | None = None
    retry_count: int = 0


@dataclass
class StepRecord:
    step_name: str
    status: str  # pending / running / completed / failed
    input_snapshot: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    raw_llm_response: str | None = None
    violations: list[dict] = field(default_factory=list)
    retry_count: int = 0
    error_message: str | None = None


class Step(ABC):
    """Abstract base for a workflow step."""

    def __init__(self, name: str, prompt_template: str, template_dir: Path) -> None:
        self.name = name
        self.prompt_template = prompt_template
        self.template_dir = template_dir

    def build_prompt(self, context: WorkflowContext) -> str:
        """Render the Jinja2 prompt template for this step."""
        return TemplateLoader.render_from_dir(
            self.template_dir,
            self.prompt_template,
            document_text=context.document_text,
            filename=context.filename,
            previous_outputs=context.previous_outputs,
        )

    @abstractmethod
    def parse_output(self, raw: str) -> Any:
        """Parse the LLM raw response into structured output."""
        ...

    def run(
        self,
        llm_client: LLMClient,
        context: WorkflowContext,
        temperature: float = 0.2,
    ) -> StepResult:
        """Execute the step: build prompt, call LLM, parse output."""
        prompt = self.build_prompt(context)
        raw = llm_client._call(
            [
                {"role": "system", "content": "你是一个严格执行指令的Agent步骤执行器。请根据要求输出结构化结果。只输出JSON，不要解释文字。"},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        output = self.parse_output(raw)
        return StepResult(output=output, raw_llm_response=raw)


class AgentWorkflowEngine:
    """Lightweight workflow engine for multi-step requirement extraction."""

    def __init__(
        self,
        steps: list[Step],
        llm_client: LLMClient,
        checklist_validator: "ChecklistValidator | None" = None,
        max_retry: int = MAX_RETRY_PER_STEP,
    ) -> None:
        self.steps = steps
        self.llm_client = llm_client
        self.checklist_validator = checklist_validator
        self.max_retry = max_retry

    def run(
        self,
        context: WorkflowContext,
        on_step_complete: "callable | None" = None,
    ) -> dict[str, StepRecord]:
        """
        Execute all steps sequentially.

        Returns a dict mapping step_name -> StepRecord.
        Raises WorkflowFailedError if a step exhausts all retries.
        """
        steps_data: dict[str, StepRecord] = {}
        current_context = context

        for step in self.steps:
            record = StepRecord(step_name=step.name, status="running")
            steps_data[step.name] = record

            for attempt in range(1, self.max_retry + 1):
                record.retry_count = attempt
                try:
                    result = step.run(self.llm_client, current_context)
                    record.raw_llm_response = result.raw_llm_response
                    record.output = result.output

                    # Checklist validation
                    if self.checklist_validator is not None:
                        violations = self.checklist_validator.validate(step.name, result.output)
                        record.violations = [v.to_dict() for v in violations]
                        errors = [v for v in violations if v.severity == "error"]
                        if errors:
                            if attempt < self.max_retry:
                                logger.warning(
                                    "Step %s attempt %d/%d failed checklist: %s. Retrying...",
                                    step.name,
                                    attempt,
                                    self.max_retry,
                                    [v.message for v in errors],
                                )
                                continue
                            else:
                                logger.error(
                                    "Step %s exhausted retries due to checklist violations.",
                                    step.name,
                                )
                                record.status = "failed"
                                record.error_message = f"Checklist violations: {[v.message for v in errors]}"
                                raise WorkflowFailedError(record.error_message)

                    record.status = "completed"
                    current_context = current_context.with_output(step.name, result.output)
                    if on_step_complete:
                        on_step_complete(step.name, record)
                    break

                except (LLMInvocationError, LLMOutputFormatError) as exc:
                    logger.warning(
                        "Step %s attempt %d/%d LLM error: %s",
                        step.name,
                        attempt,
                        self.max_retry,
                        exc,
                    )
                    if attempt < self.max_retry:
                        continue
                    record.status = "failed"
                    record.error_message = str(exc)
                    raise WorkflowFailedError(f"Step {step.name} failed after {self.max_retry} retries: {exc}") from exc
                except WorkflowFailedError:
                    raise
                except Exception as exc:
                    logger.exception("Step %s unexpected error", step.name)
                    record.status = "failed"
                    record.error_message = str(exc)
                    raise WorkflowFailedError(f"Step {step.name} unexpected error: {exc}") from exc

        return steps_data


class WorkflowFailedError(Exception):
    """Raised when the workflow cannot complete due to step failure."""
