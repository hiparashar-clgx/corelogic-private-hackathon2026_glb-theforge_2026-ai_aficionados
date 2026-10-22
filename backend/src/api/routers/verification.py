"""Citation verification + originality check endpoints (User Story 4)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from src.api.deps import get_current_user_id, get_session
from src.api.schemas import (
    CitationVerificationResultOut,
    OriginalityFindingOut,
    OriginalityResolveRequest,
)
from src.agents.originality_agent import suggest_rewrite
from src.models import OriginalityFinding
from src.orchestration.pipeline import check_originality, resolve_originality_finding, verify_all_citations

router = APIRouter(tags=["verification"])


def _finding_to_out(finding: OriginalityFinding) -> OriginalityFindingOut:
    return OriginalityFindingOut(
        id=finding.id,
        paper_id=finding.paper_id,
        draft_section_id=finding.draft_section_id,
        flagged_text=finding.flagged_text,
        matching_source=finding.matching_source,
        similarity_score=finding.similarity_score,
        is_self_plagiarism=finding.is_self_plagiarism,
        status=finding.status,
        justification=finding.justification,
    )


@router.post("/papers/{paper_id}/citations:verify", response_model=list[CitationVerificationResultOut])
async def verify_citations(paper_id: uuid.UUID, session: Session = Depends(get_session)):
    results = await verify_all_citations(session, paper_id=paper_id)
    return [
        CitationVerificationResultOut(
            id=r.id, literature_source_id=r.literature_source_id, status=r.status, failure_reason=r.failure_reason
        )
        for r in results
    ]


@router.post("/papers/{paper_id}/originality:check", response_model=list[OriginalityFindingOut])
async def run_originality_check(paper_id: uuid.UUID, session: Session = Depends(get_session)):
    findings = await check_originality(session, paper_id=paper_id)
    return [_finding_to_out(finding) for finding in findings]


@router.get("/papers/{paper_id}/originality-findings", response_model=list[OriginalityFindingOut])
def list_originality_findings(paper_id: uuid.UUID, session: Session = Depends(get_session)):
    findings = session.exec(
        select(OriginalityFinding).where(OriginalityFinding.paper_id == paper_id)
    ).all()
    return [_finding_to_out(finding) for finding in findings]


@router.post("/originality-findings/{finding_id}:rewrite-suggestion")
async def rewrite_suggestion(finding_id: uuid.UUID, session: Session = Depends(get_session)):
    finding = session.get(OriginalityFinding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Originality finding not found")
    suggestion = await suggest_rewrite(
        paper_id=str(finding.paper_id), flagged_text=finding.flagged_text, matching_source=finding.matching_source
    )
    return {"suggestion": suggestion}


@router.post("/originality-findings/{finding_id}:resolve", response_model=OriginalityFindingOut)
def resolve_finding(
    finding_id: uuid.UUID,
    body: OriginalityResolveRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
):
    try:
        finding = resolve_originality_finding(
            session, finding_id=finding_id, status=body.status, justification=body.justification, actor=user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _finding_to_out(finding)
