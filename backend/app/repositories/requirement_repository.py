from typing import List

from sqlalchemy.orm import Session

from app.models.parsed_requirement import ParsedRequirement


class RequirementRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, requirement: ParsedRequirement) -> ParsedRequirement:
        self.db.add(requirement)
        return requirement

    def create(self, requirement: ParsedRequirement) -> ParsedRequirement:
        self.db.add(requirement)
        self.db.commit()
        self.db.refresh(requirement)
        return requirement

    def get_by_document(self, document_id: str, tenant_id: int) -> List[ParsedRequirement]:
        return (
            self.db.query(ParsedRequirement)
            .filter(
                ParsedRequirement.document_id == document_id,
                ParsedRequirement.tenant_id == tenant_id,
            )
            .all()
        )

    def get_roots_by_document(self, document_id: str, tenant_id: int) -> List[ParsedRequirement]:
        return (
            self.db.query(ParsedRequirement)
            .filter(
                ParsedRequirement.document_id == document_id,
                ParsedRequirement.tenant_id == tenant_id,
                ParsedRequirement.parent_requirement_id.is_(None),
            )
            .all()
        )

    def delete_by_document(self, document_id: str, tenant_id: int) -> int:
        # Delete children first to avoid FK constraint violations on self-referential key
        children = (
            self.db.query(ParsedRequirement)
            .filter(
                ParsedRequirement.document_id == document_id,
                ParsedRequirement.tenant_id == tenant_id,
                ParsedRequirement.parent_requirement_id.isnot(None),
            )
            .all()
        )
        for child in children:
            self.db.delete(child)

        parents = (
            self.db.query(ParsedRequirement)
            .filter(
                ParsedRequirement.document_id == document_id,
                ParsedRequirement.tenant_id == tenant_id,
                ParsedRequirement.parent_requirement_id.is_(None),
            )
            .all()
        )
        for parent in parents:
            self.db.delete(parent)

        self.db.commit()
        return len(children) + len(parents)
