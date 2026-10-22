"""Per-stage audit log (constitution Principle VI; spec.md FR-018)."""
import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StageAuditLogEntry(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    paper_id: uuid.UUID = Field(foreign_key="paper.id", index=True)
    stage: str
    agent: str
    action: str
    actor: str  # "system:<agent_name>" or the user id for approvals
    timestamp: datetime = Field(default_factory=_utcnow)
