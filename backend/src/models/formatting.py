"""Formatting compliance report (spec.md: Formatting Compliance Report; FR-013/FR-014)."""
import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from src.models.enums import ComplianceStatus, Venue


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FormattingComplianceReport(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    paper_id: uuid.UUID = Field(foreign_key="paper.id", index=True)
    venue: Venue
    generated_at: datetime = Field(default_factory=_utcnow)


class ComplianceCheck(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    report_id: uuid.UUID = Field(foreign_key="formattingcompliancereport.id", index=True)
    requirement: str
    status: ComplianceStatus
    detail: str | None = Field(default=None)
