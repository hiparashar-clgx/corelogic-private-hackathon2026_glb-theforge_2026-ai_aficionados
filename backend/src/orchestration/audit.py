"""Audit log helper (constitution Principle VI; spec.md FR-018)."""
from sqlmodel import Session

from src.models import StageAuditLogEntry


def record(
    session: Session, *, paper_id, stage: str, agent: str, action: str, actor: str
) -> StageAuditLogEntry:
    entry = StageAuditLogEntry(paper_id=paper_id, stage=stage, agent=agent, action=action, actor=actor)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry
