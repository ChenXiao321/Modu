from pydantic import BaseModel, Field


class SaveRevisionRequest(BaseModel):
    section_key: str
    revised_content: str = Field(min_length=1)
    author: str = Field(min_length=1)


class ReviewCommentRequest(BaseModel):
    section_key: str
    comment_text: str = Field(min_length=1)
    author: str = Field(min_length=1)


class ResolveCommentRequest(BaseModel):
    resolved_by: str = Field(min_length=1)


class RollbackRevisionRequest(BaseModel):
    author: str = Field(min_length=1)


class DesignDocumentData(BaseModel):
    status: str
    asil_level: str | None
    sections: dict | None


class RevisionResponse(BaseModel):
    id: str
    section_key: str
    original_content: str
    revised_content: str
    author: str
    created_at: str


class RevisionWithDiffResponse(BaseModel):
    id: str
    section_key: str
    original_content: str
    revised_content: str
    diff: str
    author: str
    created_at: str


class ReviewCommentResponse(BaseModel):
    id: str
    section_key: str
    author: str
    comment_text: str
    created_at: str
    resolved_at: str | None
    resolved_by: str | None


class DesignReviewContextResponse(BaseModel):
    document_id: str
    design_document: DesignDocumentData
    requirements: list[dict]
    safety_parameters: list[dict]
    review_comments: dict[str, list[ReviewCommentResponse]]
    pending_comments_count: int
    pipeline_status: str


class SubmitDesignReviewResponse(BaseModel):
    document_id: str
    pipeline_status: str
    submitted_at: str
