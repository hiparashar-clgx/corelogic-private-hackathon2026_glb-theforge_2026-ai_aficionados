"""Paper CRUD + status endpoint (contracts/api-contracts.md "Papers")."""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from src.api.deps import get_current_user_id, get_session
from src.api.schemas import PaperCreate, PaperOut, StageStatusOut
from src.models import Paper
from src.orchestration.pipeline import create_paper, get_paper_status

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("", response_model=PaperOut)
def create(body: PaperCreate, session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)):
    paper = create_paper(session, owner_user_id=user_id, title=body.title)
    return paper


@router.get("/{paper_id}", response_model=PaperOut)
def get(paper_id: uuid.UUID, session: Session = Depends(get_session)):
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.get("/{paper_id}/status", response_model=list[StageStatusOut])
def status(paper_id: uuid.UUID, session: Session = Depends(get_session)):
    try:
        return get_paper_status(session, paper_id=paper_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{paper_id}:advance")
def advance(paper_id: uuid.UUID, body: dict, session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)):
    from src.models import Stage
    from src.orchestration.pipeline import StageBlockedError, advance_stage

    try:
        paper = advance_stage(session, paper_id=paper_id, target_stage=Stage(body["target_stage"]), actor=user_id)
    except StageBlockedError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PaperOut.model_validate(paper)
