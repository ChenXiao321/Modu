from pydantic import BaseModel, Field


class RequirementTreeNode(BaseModel):
    id: str
    requirement_id: str
    description: str
    chapter: str | None = None
    asil_level: str | None = None
    children: list["RequirementTreeNode"] = Field(default_factory=list)


class ParseTriggerResponse(BaseModel):
    document_id: str
    parse_task_id: str
    status: str


class ParseStatusResponse(BaseModel):
    document_id: str
    status: str  # pending | running | completed | failed
    progress_percent: int
    message: str | None = None


class SafetyParameterItem(BaseModel):
    id: str
    parameter_id: str
    name: str
    value: str
    unit: str | None = None
    tolerance: str | None = None
    chapter: str | None = None
    source_page: int | None = None


class SafetyParameterListResponse(BaseModel):
    document_id: str
    parameters: list[SafetyParameterItem]


class RequirementListResponse(BaseModel):
    document_id: str
    requirements: list[RequirementTreeNode]


class OcrFieldItem(BaseModel):
    id: str
    field_id: str
    extracted_text: str
    normalized_value: str | None = None
    confidence: float
    field_type: str | None = None
    source_page: int | None = None
    review_status: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None


class OcrResultListResponse(BaseModel):
    document_id: str
    pipeline_status: str
    block_reason: str | None = None
    fields: list[OcrFieldItem]


class ConfirmFieldRequest(BaseModel):
    reviewer_name: str


class ConfirmFieldResponse(BaseModel):
    field_id: str
    review_status: str
    reviewed_by: str
    reviewed_at: str
    pipeline_status: str
    all_confirmed: bool


class DocumentListItem(BaseModel):
    document_id: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    upload_status: str
    parse_status: str | None = None
    created_at: str | None = None
