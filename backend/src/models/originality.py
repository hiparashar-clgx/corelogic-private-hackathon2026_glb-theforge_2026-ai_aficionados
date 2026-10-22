"""Originality/plagiarism finding (constitution Principle II; spec.md FR-010/FR-011)."""
import uuid

from sqlmodel import Field, SQLModel

from src.models.enums import OriginalityStatus


class OriginalityFinding(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    paper_id: uuid.UUID = Field(foreign_key="paper.id", index=True)
    draft_section_id: uuid.UUID = Field(foreign_key="draftsection.id", index=True)
    flagged_text: str
    matching_source: str
    similarity_score: float
    is_self_plagiarism: bool = Field(default=False)
    status: OriginalityStatus = Field(default=OriginalityStatus.OPEN)
    justification: str | None = Field(default=None)
