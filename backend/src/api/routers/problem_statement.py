"""Problem framing + confidentiality flag endpoints (User Story 1 / 6)."""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from src.api.deps import get_current_user_id, get_session
from src.api.schemas import (
    ConfidentialityFlagOut,
    ConfidentialityFlagResolveRequest,
    ProblemStatementAcceptRequest,
    ProblemStatementDraftRequest,
    ProblemStatementOut,
    ResearchQuestionsOut,
    ResearchQuestionsRequest,
)
from src.models import ConfidentialityFlag, Paper, ProblemStatement
from src.orchestration.pipeline import (
    StageBlockedError,
    accept_problem_statement,
    draft_problem_statement,
    resolve_confidentiality_flag,
    suggest_research_questions,
)

router = APIRouter(tags=["problem-statement"])


def _to_out(statement: ProblemStatement) -> ProblemStatementOut:
    return ProblemStatementOut(
        id=statement.id,
        paper_id=statement.paper_id,
        raw_input=statement.raw_input,
        refined_statement=statement.refined_statement,
        research_questions=json.loads(statement.research_questions_json),
        status=statement.status,
        confirmed_at=statement.confirmed_at,
    )


@router.get("/papers/{paper_id}/problem-statement", response_model=ProblemStatementOut | None)
def get_statement(paper_id: uuid.UUID, session: Session = Depends(get_session)):
    if session.get(Paper, paper_id) is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    statement = session.exec(select(ProblemStatement).where(ProblemStatement.paper_id == paper_id)).first()
    return _to_out(statement) if statement is not None else None


@router.post("/papers/{paper_id}/problem-statement:draft", response_model=ProblemStatementOut)
async def draft(paper_id: uuid.UUID, body: ProblemStatementDraftRequest, session: Session = Depends(get_session)):
    statement = await draft_problem_statement(session, paper_id=paper_id, raw_input=body.raw_input)
    return _to_out(statement)


@router.post(
    "/problem-statements/{statement_id}:research-questions",
    response_model=ResearchQuestionsOut,
)
async def suggest_questions(
    statement_id: uuid.UUID,
    body: ResearchQuestionsRequest,
    session: Session = Depends(get_session),
):
    statement = session.get(ProblemStatement, statement_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="Problem statement not found")
    if not body.selected_problem_statement.strip():
        raise HTTPException(status_code=422, detail="A selected problem statement is required.")
    try:
        questions = await suggest_research_questions(
            session,
            paper_id=statement.paper_id,
            selected_problem_statement=body.selected_problem_statement,
        )
    except StageBlockedError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ResearchQuestionsOut(research_questions=questions)


@router.post("/problem-statements/{statement_id}:accept", response_model=ProblemStatementOut)
def accept(
    statement_id: uuid.UUID,
    body: ProblemStatementAcceptRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
):
    statement = session.get(ProblemStatement, statement_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="Problem statement not found")
    try:
        updated = accept_problem_statement(
            session,
            paper_id=statement.paper_id,
            statement_id=statement_id,
            refined_statement=body.refined_statement,
            research_questions=body.research_questions,
            actor=user_id,
        )
    except StageBlockedError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc
    return _to_out(updated)


@router.get("/papers/{paper_id}/confidentiality-flags", response_model=list[ConfidentialityFlagOut])
def list_flags(paper_id: uuid.UUID, session: Session = Depends(get_session)):
    return session.exec(select(ConfidentialityFlag).where(ConfidentialityFlag.paper_id == paper_id)).all()


@router.post("/confidentiality-flags/{flag_id}:resolve", response_model=ConfidentialityFlagOut)
def resolve_flag(
    flag_id: uuid.UUID,
    body: ConfidentialityFlagResolveRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
):
    try:
        return resolve_confidentiality_flag(session, flag_id=flag_id, resolution=body.resolution, actor=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
