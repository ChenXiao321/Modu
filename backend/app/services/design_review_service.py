import copy
import difflib
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.exceptions import (
    CommentAlreadyResolvedError,
    CommentNotFoundError,
    DesignDocumentNotFoundError,
    DesignDocumentNotReadyError,
    DocumentNotFoundError,
    InvalidSectionKeyError,
    PendingCommentsExistError,
    PipelineStatusInvalidError,
    RevisionNotFoundError,
)
from app.models.design_document import DesignDocument
from app.models.design_revision import DesignRevision
from app.models.review_comment import ReviewComment
from app.repositories.design_document_repository import DesignDocumentRepository
from app.repositories.design_revision_repository import DesignRevisionRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.review_comment_repository import ReviewCommentRepository
from app.repositories.safety_parameter_repository import SafetyParameterRepository

_VALID_SECTION_KEYS = {
    "overview",
    "references",
    "system_architecture",
    "interface_definition",
    "dynamic_behavior",
    "resource_consumption",
    "error_handling",
    "test_strategy",
}

_MAX_COMMENTS_PER_SECTION = 1000


class DesignReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.design_repo = DesignDocumentRepository(db)
        self.revision_repo = DesignRevisionRepository(db)
        self.comment_repo = ReviewCommentRepository(db)
        self.req_repo = RequirementRepository(db)
        self.safety_repo = SafetyParameterRepository(db)

    def get_review_context(self, tenant_id: int, document_id: str) -> dict:
        doc = self.doc_repo.get_by_id(document_id, tenant_id)
        if doc is None:
            raise DocumentNotFoundError(document_id)

        design = self.design_repo.get_by_document_id(document_id, tenant_id)
        design_data = {
            "status": design.status if design else "pending",
            "asil_level": design.asil_level if design else None,
            "sections": design.sections if design else None,
        }

        requirements = self._build_requirements_tree(
            self.req_repo.get_roots_by_document(document_id, tenant_id)
        )

        safety_parameters = self._build_safety_parameters(
            self.safety_repo.get_by_document(document_id, tenant_id)
        )

        all_comments = self.comment_repo.list_by_document(
            document_id, tenant_id, limit=_MAX_COMMENTS_PER_SECTION * len(_VALID_SECTION_KEYS)
        )
        review_comments: dict[str, list[dict]] = {}
        pending_count = 0
        for c in all_comments:
            entry = {
                "id": c.id,
                "section_key": c.section_key,
                "author": c.author,
                "comment_text": c.comment_text,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
                "resolved_by": c.resolved_by,
            }
            review_comments.setdefault(c.section_key, []).append(entry)
            if c.resolved_at is None:
                pending_count += 1

        return {
            "document_id": document_id,
            "design_document": design_data,
            "requirements": requirements,
            "safety_parameters": safety_parameters,
            "review_comments": review_comments,
            "pending_comments_count": pending_count,
            "pipeline_status": doc.pipeline_status,
        }

    def save_revision(
        self, tenant_id: int, document_id: str, section_key: str, revised_content: str, author: str
    ) -> dict:
        if section_key not in _VALID_SECTION_KEYS:
            raise InvalidSectionKeyError(section_key)
        if not revised_content.strip():
            raise InvalidSectionKeyError("revised_content")
        if not author.strip():
            raise InvalidSectionKeyError("author")

        design = self._get_completed_design(tenant_id, document_id, lock=True)
        sections = copy.deepcopy(design.sections) if design.sections else {}
        current_section = sections.get(section_key, {})
        original_content = current_section.get("content", "") if isinstance(current_section, dict) else ""

        revision = DesignRevision(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            design_document_id=design.id,
            document_id=document_id,
            section_key=section_key,
            author=author.strip(),
            original_content=original_content,
            revised_content=revised_content.strip(),
        )
        self.revision_repo.add(revision)

        # Update design document section content
        if isinstance(current_section, dict):
            sections[section_key] = {
                **current_section,
                "content": revised_content.strip(),
            }
        else:
            trace_id = current_section.get("polarion_trace_id", "") if isinstance(current_section, dict) else ""
            sections[section_key] = {"content": revised_content.strip(), "polarion_trace_id": trace_id}
        design.sections = dict(sections)
        self.db.commit()
        self.db.refresh(revision)
        self.db.refresh(design)

        return {
            "revision_id": revision.id,
            "section_key": section_key,
            "original_content": original_content,
            "revised_content": revised_content.strip(),
            "author": author.strip(),
            "created_at": revision.created_at.isoformat() if revision.created_at else None,
        }

    def get_revision_history(
        self, tenant_id: int, document_id: str, section_key: str
    ) -> dict:
        if section_key not in _VALID_SECTION_KEYS:
            raise InvalidSectionKeyError(section_key)

        revisions = self.revision_repo.list_by_section(document_id, tenant_id, section_key)
        result = []
        for r in revisions:
            diff = self._compute_diff(r.original_content, r.revised_content)
            result.append({
                "id": r.id,
                "author": r.author,
                "original_content": r.original_content,
                "revised_content": r.revised_content,
                "diff": diff,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return {
            "section_key": section_key,
            "revisions": result,
        }

    def add_review_comment(
        self, tenant_id: int, document_id: str, section_key: str, comment_text: str, author: str
    ) -> dict:
        if section_key not in _VALID_SECTION_KEYS:
            raise InvalidSectionKeyError(section_key)
        if not comment_text.strip():
            raise InvalidSectionKeyError("comment_text")
        if not author.strip():
            raise InvalidSectionKeyError("author")

        design = self._get_completed_design(tenant_id, document_id)

        comment = ReviewComment(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            design_document_id=design.id,
            document_id=document_id,
            section_key=section_key,
            author=author.strip(),
            comment_text=comment_text.strip(),
        )
        self.comment_repo.add(comment)
        self.db.commit()
        self.db.refresh(comment)

        return {
            "id": comment.id,
            "section_key": section_key,
            "author": author.strip(),
            "comment_text": comment_text.strip(),
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
            "resolved_at": None,
            "resolved_by": None,
        }

    def get_review_comments(
        self, tenant_id: int, document_id: str, section_key: str
    ) -> dict:
        if section_key not in _VALID_SECTION_KEYS:
            raise InvalidSectionKeyError(section_key)

        comments = self.comment_repo.list_by_section(document_id, tenant_id, section_key)
        result = [
            {
                "id": c.id,
                "section_key": c.section_key,
                "author": c.author,
                "comment_text": c.comment_text,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
                "resolved_by": c.resolved_by,
            }
            for c in comments
        ]
        return {"section_key": section_key, "comments": result}

    def resolve_review_comment(
        self, tenant_id: int, document_id: str, comment_id: str, resolved_by: str
    ) -> dict:
        if not resolved_by.strip():
            raise InvalidSectionKeyError("resolved_by")

        comment = self.comment_repo.get_by_id_and_document(comment_id, document_id, tenant_id)
        if comment is None:
            raise CommentNotFoundError(comment_id)
        if comment.resolved_at is not None:
            raise CommentAlreadyResolvedError(comment_id)

        comment.resolved_by = resolved_by.strip()
        resolved = self.comment_repo.resolve(comment)
        self.db.commit()
        self.db.refresh(resolved)
        return {
            "id": resolved.id,
            "section_key": resolved.section_key,
            "author": resolved.author,
            "comment_text": resolved.comment_text,
            "created_at": resolved.created_at.isoformat() if resolved.created_at else None,
            "resolved_at": resolved.resolved_at.isoformat() if resolved.resolved_at else None,
            "resolved_by": resolved.resolved_by,
        }

    def submit_design_review(self, tenant_id: int, document_id: str) -> dict:
        from app.models.document import Document

        doc = (
            self.db.query(Document)
            .filter(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
            .with_for_update()
            .first()
        )
        if doc is None:
            raise DocumentNotFoundError(document_id)

        if doc.pipeline_status != "in_design":
            raise PipelineStatusInvalidError(
                document_id, doc.pipeline_status, "in_design"
            )

        pending = [
            c for c in self.comment_repo.list_by_document(document_id, tenant_id)
            if c.resolved_at is None
        ]
        if pending:
            raise PendingCommentsExistError(document_id, len(pending))

        # Re-check right before commit to close TOCTOU window
        pending_recheck = [
            c for c in self.comment_repo.list_by_document(document_id, tenant_id)
            if c.resolved_at is None
        ]
        if pending_recheck:
            raise PendingCommentsExistError(document_id, len(pending_recheck))

        doc.pipeline_status = "design_reviewed"
        doc.block_reason = None
        self.db.commit()
        self.db.refresh(doc)

        return {
            "document_id": document_id,
            "pipeline_status": doc.pipeline_status,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }

    def rollback_to_revision(
        self, tenant_id: int, document_id: str, revision_id: str, author: str
    ) -> dict:
        if not author.strip():
            raise InvalidSectionKeyError("author")

        revision = self.revision_repo.get_by_id_and_document(revision_id, document_id, tenant_id)
        if revision is None:
            raise RevisionNotFoundError(revision_id)

        design = self._get_completed_design(tenant_id, document_id, lock=True)
        sections = copy.deepcopy(design.sections) if design.sections else {}
        current_section = sections.get(revision.section_key, {})
        current_content = current_section.get("content", "") if isinstance(current_section, dict) else ""

        # Create a new revision record for the rollback action
        rollback_revision = DesignRevision(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            design_document_id=design.id,
            document_id=document_id,
            section_key=revision.section_key,
            author=author.strip(),
            original_content=current_content,
            revised_content=revision.original_content,
        )
        self.revision_repo.add(rollback_revision)

        # Update design document
        if isinstance(current_section, dict):
            sections[revision.section_key] = {
                **current_section,
                "content": revision.original_content,
            }
        else:
            trace_id = current_section.get("polarion_trace_id", "") if isinstance(current_section, dict) else ""
            sections[revision.section_key] = {
                "content": revision.original_content,
                "polarion_trace_id": trace_id,
            }
        design.sections = dict(sections)
        self.db.commit()
        self.db.refresh(rollback_revision)
        self.db.refresh(design)

        return {
            "revision_id": rollback_revision.id,
            "section_key": revision.section_key,
            "original_content": current_content,
            "revised_content": revision.original_content,
            "author": author.strip(),
            "created_at": rollback_revision.created_at.isoformat() if rollback_revision.created_at else None,
        }

    def _get_completed_design(self, tenant_id: int, document_id: str, lock: bool = False) -> DesignDocument:
        query = self.db.query(DesignDocument).filter(
            DesignDocument.document_id == document_id,
            DesignDocument.tenant_id == tenant_id,
        )
        if lock:
            query = query.with_for_update()
        design = query.first()
        if design is None:
            raise DesignDocumentNotFoundError(document_id)
        if design.status != "completed":
            raise DesignDocumentNotReadyError(
                document_id, "设计文档尚未生成完成"
            )
        return design

    def _compute_diff(self, original: str, revised: str) -> str:
        original = original or ""
        revised = revised or ""
        original_lines = original.splitlines(keepends=True)
        revised_lines = revised.splitlines(keepends=True)
        diff = difflib.unified_diff(
            original_lines,
            revised_lines,
            fromfile="original",
            tofile="revised",
        )
        return "".join(diff)

    def _build_requirements_tree(self, roots: list) -> list[dict]:
        result = []
        for r in roots:
            node = {
                "id": r.id,
                "requirement_id": r.requirement_id,
                "description": r.description,
                "chapter": r.chapter,
                "asil_level": r.asil_level,
                "children": self._build_requirements_tree(r.children or []),
            }
            result.append(node)
        return result

    def _build_safety_parameters(self, parameters: list) -> list[dict]:
        return [
            {
                "id": p.id,
                "parameter_id": p.parameter_id,
                "name": p.name,
                "value": p.value,
                "unit": p.unit,
                "tolerance": p.tolerance,
                "chapter": p.chapter,
            }
            for p in parameters
        ]
