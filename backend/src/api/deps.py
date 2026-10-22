"""Shared FastAPI dependencies."""
from sqlmodel import Session

from src.db import get_session

__all__ = ["get_session"]


def get_current_user_id() -> str:
    """Stub identity resolution — replace with real SSO/OIDC integration (spec.md FR-025)."""
    return "demo-user"
