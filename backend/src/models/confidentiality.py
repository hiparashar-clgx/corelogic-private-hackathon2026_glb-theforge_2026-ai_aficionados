"""Confidentiality flag (constitution Principle V; spec.md FR-002/FR-003)."""
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from src.models.enums import FlagResolution


class ConfidentialityFlag(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    paper_id: uuid.UUID = Field(foreign_key="paper.id", index=True)
    source_field: str
    matched_text: str
    flag_reason: str
    resolution: FlagResolution = Field(default=FlagResolution.OPEN)
    resolved_by: str | None = Field(default=None)
    resolved_at: datetime | None = Field(default=None)
