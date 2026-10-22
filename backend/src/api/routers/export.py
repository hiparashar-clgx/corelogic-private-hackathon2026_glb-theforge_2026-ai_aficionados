"""Export endpoint (spec.md FR-020: export at any point, independent of completeness)."""
import json
import re
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from src.api.deps import get_current_user_id, get_session
from src.api.routers.formatting import _compiled_sections
from src.models import LiteratureSource, Paper
from src.orchestration.pipeline import StageBlockedError, prepare_export
from src.services.export_service import ExportReference, order_sections, render_paper_docx

router = APIRouter(prefix="/papers/{paper_id}/export", tags=["export"])


def _content_disposition(title: str) -> str:
    stem = re.sub(r'[\\/:*?"<>|\r\n]+', " ", title).strip() or "paper"
    ascii_stem = stem.encode("ascii", "ignore").decode().strip() or "paper"
    return f'attachment; filename="{ascii_stem}.docx"; filename*=UTF-8\'\'{quote(stem + ".docx")}'


def _references(session: Session, paper_id: uuid.UUID) -> list[ExportReference]:
    sources = session.exec(
        select(LiteratureSource).where(LiteratureSource.paper_id == paper_id, LiteratureSource.selected == True)  # noqa: E712
    ).all()
    return [
        ExportReference(
            doi_or_url=source.doi_or_url,
            title=source.title,
            authors=json.loads(source.authors_json or "[]"),
            venue=source.venue,
            year=source.year,
        )
        for source in sources
    ]


@router.post("")
def export(
    paper_id: uuid.UUID,
    format: str = "docx",
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
):
    if format != "docx":
        raise HTTPException(status_code=400, detail="Only 'docx' is supported in v1")

    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        content = prepare_export(
            session, paper_id=paper_id, title=paper.title, sections=_compiled_sections(session, paper_id), actor=user_id
        )
    except StageBlockedError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc

    docx_bytes = render_paper_docx(
        title=content.title,
        sections=order_sections(content.sections),
        references=_references(session, paper_id),
        venue=paper.target_venue,
    )
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": _content_disposition(content.title)},
    )
