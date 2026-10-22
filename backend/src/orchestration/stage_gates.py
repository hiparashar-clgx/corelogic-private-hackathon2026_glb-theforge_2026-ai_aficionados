"""Stage-gate enforcement (constitution Principle VII; spec.md FR-011/FR-015).

Each function returns `None` if the gate passes, or a human-readable blocking reason string if it
does not. The orchestration layer refuses a stage transition whenever any relevant gate returns a
reason.
"""
from sqlmodel import Session, select

from src.models import (
    ConfidentialityFlag,
    FlagResolution,
    OriginalityFinding,
    OriginalityStatus,
    Paper,
    Stage,
    VerificationStatus,
)
from src.models.literature import CitationVerificationResult, LiteratureSource


def open_confidentiality_flags(session: Session, paper_id) -> list[ConfidentialityFlag]:
    return list(
        session.exec(
            select(ConfidentialityFlag).where(
                ConfidentialityFlag.paper_id == paper_id,
                ConfidentialityFlag.resolution == FlagResolution.OPEN,
            )
        )
    )


def selected_sources(session: Session, paper_id) -> list[LiteratureSource]:
    return list(
        session.exec(
            select(LiteratureSource).where(
                LiteratureSource.paper_id == paper_id,
                LiteratureSource.selected == True,  # noqa: E712
            )
        )
    )


def unverified_citations(session: Session, paper_id) -> list[LiteratureSource]:
    sources = selected_sources(session, paper_id)
    unverified = []
    for source in sources:
        latest = session.exec(
            select(CitationVerificationResult)
            .where(CitationVerificationResult.literature_source_id == source.id)
            .order_by(CitationVerificationResult.checked_at.desc())
        ).first()
        if (
            source.manually_accepted
            and source.verification_status == VerificationStatus.UNVERIFIED
            and latest is not None
            and latest.status == VerificationStatus.UNVERIFIED
        ):
            continue
        if (
            source.verification_status != VerificationStatus.VERIFIED
            or latest is None
            or latest.status != VerificationStatus.VERIFIED
        ):
            unverified.append(source)
    return unverified


def open_originality_findings(session: Session, paper_id) -> list[OriginalityFinding]:
    return list(
        session.exec(
            select(OriginalityFinding).where(
                OriginalityFinding.paper_id == paper_id,
                OriginalityFinding.status == OriginalityStatus.OPEN,
            )
        )
    )


def gate_for_transition(session: Session, paper: Paper, target_stage: Stage) -> str | None:
    """Returns a blocking reason, or None if the transition to `target_stage` is allowed."""
    open_flags = open_confidentiality_flags(session, paper.id)
    if open_flags:
        return f"{len(open_flags)} unresolved confidentiality flag(s) must be redacted/generalized/confirmed-safe first."

    if target_stage == Stage.DRAFTING:
        if not selected_sources(session, paper.id):
            return "Select and verify at least one literature source before drafting."
        unverified = unverified_citations(session, paper.id)
        if unverified:
            return (
                f"{len(unverified)} literature source(s) selected for drafting are pending or failed verification. "
                "Verify, correct, exclude, or remove them on the literature survey page before drafting."
            )

    if target_stage == Stage.FORMATTING:
        if paper.target_venue is None:
            return "Select a target publisher/venue before applying formatting."
        unverified = unverified_citations(session, paper.id)
        if unverified:
            return f"{len(unverified)} citation(s) failed verification and must be resolved (FR-011)."
        open_findings = open_originality_findings(session, paper.id)
        if open_findings:
            return f"{len(open_findings)} originality finding(s) are unresolved and must be rewritten or justified (FR-011)."

    if target_stage == Stage.READY_FOR_SUBMISSION:
        unverified = unverified_citations(session, paper.id)
        if unverified:
            return f"{len(unverified)} citation(s) failed verification and must be resolved (FR-011)."
        open_findings = open_originality_findings(session, paper.id)
        if open_findings:
            return f"{len(open_findings)} originality finding(s) are unresolved (FR-011)."

    return None
