"""Literature source + citation verification result (spec.md: Literature Source / Reference)."""
import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from src.models.enums import VerificationStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LiteratureSource(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    paper_id: uuid.UUID = Field(foreign_key="paper.id", index=True)
    title: str
    authors_json: str = "[]"  # JSON-encoded list[str]
    year: int | None = Field(default=None)
    venue: str = ""
    doi_or_url: str
    theme: str = ""
    relevance_summary: str = ""
    verification_status: VerificationStatus = Field(default=VerificationStatus.PENDING)
    verification_failure_reason: str | None = Field(default=None)
    selected: bool = Field(default=True)
    # User override for a source the automatic check could not retrieve (e.g. paywalled); status stays UNVERIFIED.
    manually_accepted: bool = Field(default=False)
    manual_acceptance_reason: str | None = Field(default=None)


class CitationVerificationResult(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    literature_source_id: uuid.UUID = Field(foreign_key="literaturesource.id", index=True)
    status: VerificationStatus
    checked_at: datetime = Field(default_factory=_utcnow)
    failure_reason: str | None = Field(default=None)
