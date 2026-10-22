"""Section drafting endpoints (User Story 3)."""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from src.api.deps import get_current_user_id, get_session
from src.agents.base import AgentUnavailableError
from src.api.schemas import ContentBlockOut, ContentBlockUpdateRequest, DraftSectionOut, SectionDraftRequest
from src.models import ContentBlock, DraftSection, ProblemStatement, SectionType
from src.orchestration.pipeline import StageBlockedError, generate_section_draft, update_content_block
from src.orchestration.stage_gates import selected_sources, unverified_citations

router = APIRouter(prefix="/papers/{paper_id}/sections", tags=["drafting"])


def _to_out(section: DraftSection, blocks: list[ContentBlock]) -> DraftSectionOut:
    return DraftSectionOut(
        id=section.id,
        paper_id=section.paper_id,
        section_type=section.section_type,
        blocks=[
            ContentBlockOut(id=b.id, order=b.order, text=b.text, origin=b.origin.value, accepted=b.accepted)
            for b in sorted(blocks, key=lambda b: b.order)
        ],
    )


@router.post("/{section_type}:draft", response_model=DraftSectionOut)
async def draft(
    paper_id: uuid.UUID,
    section_type: SectionType,
    body: SectionDraftRequest,
    session: Session = Depends(get_session),
):
    statement = session.exec(select(ProblemStatement).where(ProblemStatement.paper_id == paper_id)).first()
    if statement is None:
        raise HTTPException(status_code=409, detail="Problem statement must exist before drafting a section.")

    blocked_ids = {s.id for s in unverified_citations(session, paper_id)}
    sources = [s for s in selected_sources(session, paper_id) if s.id not in blocked_ids]
    sources_context = "\n".join(
        f"- {s.title} ({s.doi_or_url})"
        + (" [manually accepted; automatic retrieval check failed]" if s.manually_accepted else "")
        for s in sources
    ) or "(no surveyed sources yet)"

    try:
        section = await generate_section_draft(
            session,
            paper_id=paper_id,
            section_type=section_type,
            problem_statement=statement.refined_statement,
            sources_context=sources_context,
            user_notes=body.user_notes,
        )
    except StageBlockedError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc
    except AgentUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    blocks = session.exec(select(ContentBlock).where(ContentBlock.draft_section_id == section.id)).all()
    return _to_out(section, blocks)


@router.get("/{section_type}", response_model=DraftSectionOut)
def get_section(paper_id: uuid.UUID, section_type: SectionType, session: Session = Depends(get_session)):
    section = session.exec(
        select(DraftSection).where(DraftSection.paper_id == paper_id, DraftSection.section_type == section_type)
    ).first()
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    blocks = session.exec(select(ContentBlock).where(ContentBlock.draft_section_id == section.id)).all()
    return _to_out(section, blocks)


@router.patch("/blocks/{block_id}", response_model=ContentBlockOut)
def update_block(
    paper_id: uuid.UUID,
    block_id: uuid.UUID,
    body: ContentBlockUpdateRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
):
    try:
        block = update_content_block(
            session, block_id=block_id, text=body.text, accepted=body.accepted, actor=user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ContentBlockOut(id=block.id, order=block.order, text=block.text, origin=block.origin.value, accepted=block.accepted)
