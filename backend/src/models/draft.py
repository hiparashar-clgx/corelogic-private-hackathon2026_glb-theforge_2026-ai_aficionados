"""Draft section + content blocks (spec.md: Draft Section)."""
import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from src.models.enums import ContentOrigin, SectionType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DraftSection(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    paper_id: uuid.UUID = Field(foreign_key="paper.id", index=True)
    section_type: SectionType
    citations_json: str = "[]"  # JSON-encoded list[str] of LiteratureSource ids
    updated_at: datetime = Field(default_factory=_utcnow)


class ContentBlock(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    draft_section_id: uuid.UUID = Field(foreign_key="draftsection.id", index=True)
    order: int = Field(default=0)
    text: str
    origin: ContentOrigin
    # Accepted blocks are never silently overwritten on regeneration (spec FR-008).
    accepted: bool = Field(default=False)
