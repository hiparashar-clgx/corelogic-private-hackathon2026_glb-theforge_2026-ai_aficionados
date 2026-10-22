"""Publisher-format compliance endpoints (User Story 5)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from src.api.deps import get_session
from src.api.schemas import ComplianceCheckOut, FormattingApplyRequest, FormattingComplianceReportOut
from src.models import ComplianceCheck, ContentBlock, DraftSection, FormattingComplianceReport, Paper
from src.orchestration.pipeline import StageBlockedError, apply_formatting

router = APIRouter(prefix="/papers/{paper_id}/formatting", tags=["formatting"])


def _compiled_sections(session: Session, paper_id: uuid.UUID) -> dict[str, str]:
    sections = session.exec(select(DraftSection).where(DraftSection.paper_id == paper_id)).all()
    compiled: dict[str, str] = {}
    for section in sections:
        blocks = session.exec(select(ContentBlock).where(ContentBlock.draft_section_id == section.id)).all()
        compiled[section.section_type.value] = "\n\n".join(b.text for b in sorted(blocks, key=lambda b: b.order))
    return compiled


def _report_to_out(report: FormattingComplianceReport, checks: list[ComplianceCheck]) -> FormattingComplianceReportOut:
    return FormattingComplianceReportOut(
        id=report.id,
        paper_id=report.paper_id,
        venue=report.venue,
        generated_at=report.generated_at,
        checks=[ComplianceCheckOut(requirement=c.requirement, status=c.status, detail=c.detail) for c in checks],
    )


@router.post(":apply", response_model=FormattingComplianceReportOut)
def apply(paper_id: uuid.UUID, body: FormattingApplyRequest, session: Session = Depends(get_session)):
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    sections = _compiled_sections(session, paper_id)
    try:
        report = apply_formatting(session, paper_id=paper_id, venue=body.venue, title=paper.title, sections=sections)
    except StageBlockedError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc

    checks = session.exec(select(ComplianceCheck).where(ComplianceCheck.report_id == report.id)).all()
    return _report_to_out(report, checks)


@router.get("/compliance-report", response_model=FormattingComplianceReportOut)
def latest_report(paper_id: uuid.UUID, session: Session = Depends(get_session)):
    report = session.exec(
        select(FormattingComplianceReport)
        .where(FormattingComplianceReport.paper_id == paper_id)
        .order_by(FormattingComplianceReport.generated_at.desc())
    ).first()
    if report is None:
        raise HTTPException(status_code=404, detail="No formatting report yet")
    checks = session.exec(select(ComplianceCheck).where(ComplianceCheck.report_id == report.id)).all()
    return _report_to_out(report, checks)
