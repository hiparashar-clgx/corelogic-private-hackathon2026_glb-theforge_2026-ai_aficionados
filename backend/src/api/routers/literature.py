"""Literature survey endpoints (User Story 2)."""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from src.api.deps import get_current_user_id, get_session
from src.api.schemas import (
    LiteratureSourceCreateRequest,
    LiteratureSourceManualAcceptanceRequest,
    LiteratureSourceOut,
    LiteratureSourceSelectionRequest,
    LiteratureSourceUpdateRequest,
    LiteratureSurveyRequest,
)
from src.models import LiteratureSource, Paper, ProblemStatement, ProblemStatementStatus
from src.orchestration.pipeline import (
    StageBlockedError,
    add_manual_literature_source,
    remove_unverified_literature_source,
    run_literature_survey,
    set_literature_source_manual_acceptance,
    set_literature_source_selection,
    update_literature_source_identifier,
)
from src.services.literature_search import LiteratureSearchError

router = APIRouter(prefix="/papers/{paper_id}", tags=["literature"])


def _to_out(source: LiteratureSource) -> LiteratureSourceOut:
    return LiteratureSourceOut(
        id=source.id,
        paper_id=source.paper_id,
        title=source.title,
        authors=json.loads(source.authors_json),
        year=source.year,
        venue=source.venue,
        doi_or_url=source.doi_or_url,
        theme=source.theme,
        relevance_summary=source.relevance_summary,
        verification_status=source.verification_status,
        verification_failure_reason=source.verification_failure_reason,
        selected=source.selected,
        manually_accepted=source.manually_accepted,
        manual_acceptance_reason=source.manual_acceptance_reason,
    )


@router.post("/literature-survey", response_model=list[LiteratureSourceOut])
async def survey(paper_id: uuid.UUID, body: LiteratureSurveyRequest, session: Session = Depends(get_session)):
    statement = session.exec(
        select(ProblemStatement).where(
            ProblemStatement.paper_id == paper_id, ProblemStatement.status == ProblemStatementStatus.ACCEPTED
        )
    ).first()
    if statement is None:
        raise HTTPException(status_code=409, detail="Problem statement must be accepted before running a survey.")

    try:
        sources = await run_literature_survey(
            session,
            paper_id=paper_id,
            problem_statement=statement.refined_statement,
            query=body.query,
            research_questions=json.loads(statement.research_questions_json),
            year_range=body.year_range,
        )
    except StageBlockedError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc
    except LiteratureSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [_to_out(s) for s in sources]


@router.get("/literature-sources", response_model=list[LiteratureSourceOut])
def list_sources(paper_id: uuid.UUID, session: Session = Depends(get_session)):
    sources = session.exec(select(LiteratureSource).where(LiteratureSource.paper_id == paper_id)).all()
    return [_to_out(s) for s in sources]


@router.post("/literature-sources", response_model=LiteratureSourceOut, status_code=201)
def add_source(
    paper_id: uuid.UUID,
    body: LiteratureSourceCreateRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
):
    if session.get(Paper, paper_id) is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    try:
        source = add_manual_literature_source(
            session, paper_id=paper_id, doi_or_url=body.doi_or_url, title=body.title, actor=user_id
        )
    except StageBlockedError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc
    return _to_out(source)


@router.put("/literature-sources/{source_id}/selection", response_model=LiteratureSourceOut)
def set_source_selection(
    paper_id: uuid.UUID,
    source_id: uuid.UUID,
    body: LiteratureSourceSelectionRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
):
    try:
        source = set_literature_source_selection(
            session, paper_id=paper_id, source_id=source_id, selected=body.selected, actor=user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StageBlockedError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc
    return _to_out(source)


@router.put("/literature-sources/{source_id}/manual-acceptance", response_model=LiteratureSourceOut)
def set_source_manual_acceptance(
    paper_id: uuid.UUID,
    source_id: uuid.UUID,
    body: LiteratureSourceManualAcceptanceRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
):
    try:
        source = set_literature_source_manual_acceptance(
            session, paper_id=paper_id, source_id=source_id,
            accepted=body.accepted, reason=body.reason, actor=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StageBlockedError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc
    return _to_out(source)


@router.delete("/literature-sources/{source_id}", status_code=204)
def remove_unverified_source(
    paper_id: uuid.UUID,
    source_id: uuid.UUID,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
):
    try:
        remove_unverified_literature_source(
            session, paper_id=paper_id, source_id=source_id, actor=user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StageBlockedError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc
    return Response(status_code=204)


@router.patch("/literature-sources/{source_id}", response_model=LiteratureSourceOut)
def correct_source_identifier(
    paper_id: uuid.UUID,
    source_id: uuid.UUID,
    body: LiteratureSourceUpdateRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
):
    try:
        source = update_literature_source_identifier(
            session, paper_id=paper_id, source_id=source_id, doi_or_url=body.doi_or_url, actor=user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StageBlockedError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc
    return _to_out(source)
