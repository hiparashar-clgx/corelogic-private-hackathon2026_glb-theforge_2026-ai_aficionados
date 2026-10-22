"""Confidentiality Screening Agent (spec.md User Story 6; FR-002/FR-003; constitution Principle V).

Deterministic heuristic screening (src.services.confidentiality_screen) run before ANY content is
sent to another agent's external tool call or included in an export. Kept as its own "agent" module
so it has a distinct identity in the audit log, matching plan.md's agent list.
"""
from src.services.confidentiality_screen import ScreeningMatch, screen_text

AGENT_NAME = "confidentiality_screening_agent"


def screen(text: str, *, source_field: str) -> list[tuple[ScreeningMatch, str]]:
    """Returns a list of (match, source_field) pairs for the caller to persist as ConfidentialityFlag rows."""
    return [(match, source_field) for match in screen_text(text)]
