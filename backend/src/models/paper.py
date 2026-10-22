"""Paper aggregate + ProblemStatement (spec.md Key Entities: Paper, Problem Statement)."""
import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from src.models.enums import ProblemStatementStatus, Stage, Venue


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Paper(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_user_id: str = Field(index=True)
    title: str
    current_stage: Stage = Field(default=Stage.FRAMING)
    target_venue: Venue | None = Field(default=None)
    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ProblemStatement(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    paper_id: uuid.UUID = Field(foreign_key="paper.id", index=True)
    raw_input: str
    refined_statement: str = ""
    research_questions_json: str = "[]"  # JSON-encoded list[str]; SQLite has no native array type
    status: ProblemStatementStatus = Field(default=ProblemStatementStatus.DRAFT)
    confirmed_at: datetime | None = Field(default=None)
