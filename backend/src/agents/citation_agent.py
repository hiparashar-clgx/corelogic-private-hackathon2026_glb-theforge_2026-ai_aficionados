"""Citation Verification Agent (spec.md User Story 4; FR-009).

Deterministic — verification is a DOI/URL resolution check (src.services.literature_search), not an
LLM judgment call. Kept as a thin "agent" module for parity with the other pipeline stages and to
give it its own audit-log identity (constitution Principle VI).
"""
from src.models.enums import VerificationStatus
from src.services.literature_search import resolve_doi

AGENT_NAME = "citation_verification_agent"


async def verify_citation(doi_or_url: str) -> tuple[VerificationStatus, str | None]:
    if not doi_or_url:
        return VerificationStatus.UNVERIFIED, "No DOI/URL provided"
    resolved = await resolve_doi(doi_or_url)
    if resolved:
        return VerificationStatus.VERIFIED, None
    return VerificationStatus.UNVERIFIED, f"Could not resolve identifier: {doi_or_url}"
