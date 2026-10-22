"""Core pipeline orchestrator (constitution Principle VI; spec.md FR-016/FR-018/FR-019).

This module is the single place that: (1) always runs the Confidentiality Screening Agent before
any content reaches an external tool/LLM call, (2) enforces stage gates before persisting a stage
transition, and (3) writes a StageAuditLogEntry for every agent/tool action and every user approval.
No agent output here is ever auto-published — every mutating call still requires an explicit
follow-up user action (accept/approve) per constitution Principle I.
"""
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlmodel import Session, select

from src.agents import citation_agent, confidentiality_agent, drafting_agent, formatting_agent, literature_agent
from src.agents import originality_agent
from src.agents.framing_agent import frame_problem_statement, suggest_research_questions as frame_research_questions
from src.config import get_settings
from src.models import (
    CitationVerificationResult,
    ComplianceCheck,
    ConfidentialityFlag,
    ContentBlock,
    ContentOrigin,
    DraftSection,
    FlagResolution,
    FormattingComplianceReport,
    LiteratureSource,
    OriginalityFinding,
    OriginalityStatus,
    Paper,
    ProblemStatement,
    ProblemStatementStatus,
    SectionType,
    Stage,
    Venue,
    VerificationStatus,
)
from src.orchestration.audit import record
from src.orchestration.stage_gates import gate_for_transition, open_confidentiality_flags
from src.services.originality_check import OriginalitySource


class StageBlockedError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _mask(text: str, spans: list[str]) -> str:
    masked = text
    for span in spans:
        masked = masked.replace(span, "[REDACTED]")
    return masked


def _screen_and_flag(session: Session, *, paper_id, field: str, text: str) -> tuple[str, list[ConfidentialityFlag]]:
    """Runs the Confidentiality Screening Agent, persists flags, and returns a masked-safe copy.

    The masked copy is what may be sent to any external tool/LLM call (spec.md FR-002). The flags
    remain `open` until the user explicitly resolves them (FR-003), which gates later transitions.
    """
    matches = confidentiality_agent.screen(text, source_field=field)
    flags: list[ConfidentialityFlag] = []
    new_flags: list[ConfidentialityFlag] = []
    for match, source_field in matches:
        existing = session.exec(
            select(ConfidentialityFlag).where(
                ConfidentialityFlag.paper_id == paper_id,
                ConfidentialityFlag.source_field == source_field,
                ConfidentialityFlag.matched_text == match.matched_text,
            )
        ).first()
        if existing is not None:
            flags.append(existing)
            continue
        flag = ConfidentialityFlag(
            paper_id=paper_id,
            source_field=source_field,
            matched_text=match.matched_text,
            flag_reason=match.reason,
        )
        session.add(flag)
        flags.append(flag)
        new_flags.append(flag)
    if new_flags:
        session.commit()
        for flag in new_flags:
            session.refresh(flag)
        record(
            session,
            paper_id=paper_id,
            stage="cross-cutting",
            agent=confidentiality_agent.AGENT_NAME,
            action=f"flagged {len(new_flags)} possible confidential item(s) in {field}",
            actor=f"system:{confidentiality_agent.AGENT_NAME}",
        )
    safe_text = _mask(
        text,
        [flag.matched_text for flag in flags if flag.resolution != FlagResolution.CONFIRMED_SAFE],
    )
    return safe_text, flags


# --- Paper lifecycle -------------------------------------------------------------------------


def create_paper(session: Session, *, owner_user_id: str, title: str) -> Paper:
    paper = Paper(owner_user_id=owner_user_id, title=title)
    session.add(paper)
    session.commit()
    session.refresh(paper)
    record(
        session,
        paper_id=paper.id,
        stage=Stage.FRAMING,
        agent="system",
        action="paper created",
        actor=owner_user_id,
    )
    return paper


# --- User Story 1: Problem framing -----------------------------------------------------------


async def draft_problem_statement(session: Session, *, paper_id: uuid.UUID, raw_input: str) -> ProblemStatement:
    safe_text, _flags = _screen_and_flag(session, paper_id=paper_id, field="raw_input", text=raw_input)

    result = await frame_problem_statement(paper_id=str(paper_id), redacted_input=safe_text)
    statement = ProblemStatement(
        paper_id=paper_id,
        raw_input=raw_input,
        refined_statement=f"{result.get('context', '')}\n\n{result.get('problem', '')}".strip(),
        research_questions_json="[]",
    )
    session.add(statement)
    session.commit()
    session.refresh(statement)
    record(
        session,
        paper_id=paper_id,
        stage=Stage.FRAMING,
        agent="framing_agent",
        action="drafted problem statement",
        actor="system:framing_agent",
    )
    return statement


async def suggest_research_questions(
    session: Session, *, paper_id: uuid.UUID, selected_problem_statement: str
) -> list[str]:
    safe_statement, _flags = _screen_and_flag(
        session,
        paper_id=paper_id,
        field="selected_problem_statement",
        text=selected_problem_statement,
    )
    if open_confidentiality_flags(session, paper_id):
        raise StageBlockedError("Resolve confidentiality flags before generating research questions.")
    return await frame_research_questions(
        paper_id=str(paper_id),
        selected_problem_statement=safe_statement,
    )


def accept_problem_statement(
    session: Session,
    *,
    paper_id: uuid.UUID,
    statement_id: uuid.UUID,
    refined_statement: str,
    research_questions: list[str],
    actor: str,
) -> ProblemStatement:
    open_flags = open_confidentiality_flags(session, paper_id)
    if open_flags:
        raise StageBlockedError(
            f"{len(open_flags)} unresolved confidentiality flag(s) must be resolved before accepting."
        )

    statement = session.get(ProblemStatement, statement_id)
    if statement is None or statement.paper_id != paper_id:
        raise ValueError("Problem statement not found for this paper")
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise ValueError("Paper not found")

    statement.refined_statement = refined_statement
    statement.research_questions_json = json.dumps(research_questions)
    statement.status = ProblemStatementStatus.ACCEPTED
    statement.confirmed_at = datetime.now(timezone.utc)
    paper.current_stage = Stage.LITERATURE_SURVEY
    paper.version += 1
    paper.updated_at = datetime.now(timezone.utc)
    session.add(statement)
    session.add(paper)
    session.commit()
    session.refresh(statement)
    record(
        session,
        paper_id=paper_id,
        stage=Stage.FRAMING,
        agent="framing_agent",
        action="problem statement accepted by user",
        actor=actor,
    )
    return statement


def resolve_confidentiality_flag(
    session: Session, *, flag_id: uuid.UUID, resolution: FlagResolution, actor: str
) -> ConfidentialityFlag:
    flag = session.get(ConfidentialityFlag, flag_id)
    if flag is None:
        raise ValueError("Confidentiality flag not found")
    flag.resolution = resolution
    flag.resolved_by = actor
    flag.resolved_at = datetime.now(timezone.utc)
    session.add(flag)
    session.commit()
    session.refresh(flag)
    record(
        session,
        paper_id=flag.paper_id,
        stage="cross-cutting",
        agent=confidentiality_agent.AGENT_NAME,
        action=f"flag resolved as {resolution.value}",
        actor=actor,
    )
    return flag


# --- User Story 2: Literature survey ----------------------------------------------------------


async def run_literature_survey(
    session: Session,
    *,
    paper_id: uuid.UUID,
    problem_statement: str,
    query: str,
    research_questions: list[str],
    year_range: str | None = None,
) -> list[LiteratureSource]:
    user_query = query.strip()
    safe_user_query = (
        _screen_and_flag(session, paper_id=paper_id, field="survey_query", text=user_query)[0]
        if user_query
        else ""
    )
    safe_questions = [
        _screen_and_flag(session, paper_id=paper_id, field="survey_query", text=question.strip())[0]
        for question in research_questions
        if question.strip()
    ]
    open_flags = open_confidentiality_flags(session, paper_id)
    if open_flags:
        raise StageBlockedError("Resolve confidentiality flags before running an external literature search.")

    found = await literature_agent.run_literature_survey(
        paper_id=str(paper_id),
        problem_statement=problem_statement,
        query=safe_user_query,
        research_questions=safe_questions,
        year_range=year_range,
    )
    created: list[LiteratureSource] = []
    for item in found:
        source = LiteratureSource(
            paper_id=paper_id,
            title=item.title,
            authors_json=json.dumps(item.authors),
            year=item.year,
            venue=item.venue,
            doi_or_url=item.doi_or_url,
            theme=item.theme,
            relevance_summary=item.relevance_summary,
            verification_status=VerificationStatus.PENDING,
        )
        session.add(source)
        created.append(source)
    session.commit()
    for source in created:
        session.refresh(source)
    record(
        session,
        paper_id=paper_id,
        stage=Stage.LITERATURE_SURVEY,
        agent="literature_survey_agent",
        action=f"found {len(created)} source(s)",
        actor="system:literature_survey_agent",
    )
    return created


# --- User Story 3: Drafting -------------------------------------------------------------------


async def generate_section_draft(
    session: Session,
    *,
    paper_id: uuid.UUID,
    section_type: SectionType,
    problem_statement: str,
    sources_context: str,
    user_notes: str = "",
) -> DraftSection:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise StageBlockedError("Paper not found.")
    blocking_reason = gate_for_transition(session, paper, Stage.DRAFTING)
    if blocking_reason:
        raise StageBlockedError(blocking_reason)

    safe_notes, _flags = _screen_and_flag(session, paper_id=paper_id, field=f"notes:{section_type}", text=user_notes)
    open_flags = open_confidentiality_flags(session, paper_id)
    if open_flags:
        raise StageBlockedError("Resolve confidentiality flags before drafting with these notes.")

    generated_text = await drafting_agent.draft_section(
        paper_id=str(paper_id),
        section_type=section_type.value,
        problem_statement=problem_statement,
        sources_context=sources_context,
        user_notes=safe_notes,
    )

    section = session.exec(
        select(DraftSection).where(DraftSection.paper_id == paper_id, DraftSection.section_type == section_type)
    ).first()
    if section is None:
        section = DraftSection(paper_id=paper_id, section_type=section_type)
        session.add(section)
        session.commit()
        session.refresh(section)

    existing_blocks = session.exec(
        select(ContentBlock).where(ContentBlock.draft_section_id == section.id)
    ).all()
    # Never overwrite blocks the user has already accepted (FR-008).
    if not any(b.accepted for b in existing_blocks):
        for block in existing_blocks:
            session.delete(block)
        session.commit()
        new_block = ContentBlock(
            draft_section_id=section.id,
            order=0,
            text=generated_text,
            origin=ContentOrigin.SYSTEM_GENERATED,
            accepted=False,
        )
        session.add(new_block)
        session.commit()

    section.updated_at = datetime.now(timezone.utc)
    session.add(section)
    session.commit()
    session.refresh(section)
    record(
        session,
        paper_id=paper_id,
        stage=Stage.DRAFTING,
        agent="drafting_agent",
        action=f"drafted section {section_type.value}",
        actor="system:drafting_agent",
    )
    return section


def update_content_block(
    session: Session, *, block_id: uuid.UUID, text: str | None, accepted: bool | None, actor: str
) -> ContentBlock:
    block = session.get(ContentBlock, block_id)
    if block is None:
        raise ValueError("Content block not found")
    if text is not None:
        block.text = text
        block.origin = ContentOrigin.USER_AUTHORED
    if accepted is not None:
        block.accepted = accepted
    session.add(block)
    session.commit()
    session.refresh(block)

    section = session.get(DraftSection, block.draft_section_id)
    if section is not None:
        record(
            session,
            paper_id=section.paper_id,
            stage=Stage.DRAFTING,
            agent="user",
            action="content block edited/accepted",
            actor=actor,
        )
    return block


# --- User Story 4: Citation verification & originality -----------------------------------------


async def verify_all_citations(session: Session, *, paper_id: uuid.UUID) -> list[CitationVerificationResult]:
    sources = session.exec(
        select(LiteratureSource).where(LiteratureSource.paper_id == paper_id, LiteratureSource.selected == True)  # noqa: E712
    ).all()
    results: list[CitationVerificationResult] = []
    for source in sources:
        status, reason = await citation_agent.verify_citation(source.doi_or_url)
        result = CitationVerificationResult(
            literature_source_id=source.id, status=status, failure_reason=reason
        )
        session.add(result)
        source.verification_status = status
        source.verification_failure_reason = reason
        if status == VerificationStatus.VERIFIED:
            source.manually_accepted = False
            source.manual_acceptance_reason = None
        session.add(source)
        results.append(result)
    session.commit()
    for result in results:
        session.refresh(result)
    record(
        session,
        paper_id=paper_id,
        stage=Stage.VERIFICATION,
        agent=citation_agent.AGENT_NAME,
        action=f"verified {len(results)} citation(s)",
        actor=f"system:{citation_agent.AGENT_NAME}",
    )
    return results


def update_literature_source_identifier(
    session: Session, *, paper_id: uuid.UUID, source_id: uuid.UUID, doi_or_url: str, actor: str
) -> LiteratureSource:
    source = session.get(LiteratureSource, source_id)
    if source is None or source.paper_id != paper_id:
        raise ValueError("Literature source not found")
    if source.verification_status == VerificationStatus.VERIFIED:
        raise StageBlockedError("Only pending or unverified source identifiers can be corrected.")
    source.doi_or_url = doi_or_url
    source.verification_status = VerificationStatus.PENDING
    source.verification_failure_reason = None
    source.manually_accepted = False
    source.manual_acceptance_reason = None
    session.add(source)
    session.add(CitationVerificationResult(
        literature_source_id=source.id,
        status=VerificationStatus.PENDING,
        failure_reason="Source identifier changed; verification required.",
    ))
    record(
        session,
        paper_id=paper_id,
        stage=Stage.LITERATURE_SURVEY,
        agent="user",
        action=f"corrected identifier for literature source {source.id}; verification required",
        actor=actor,
    )
    session.refresh(source)
    return source


def _identifier_key(doi_or_url: str) -> str:
    value = doi_or_url.strip().rstrip("/").lower()
    marker = "doi.org/"
    if marker in value:
        return "doi:" + value.split(marker, 1)[1]
    return value.removeprefix("https://").removeprefix("http://").removeprefix("www.")


def add_manual_literature_source(
    session: Session, *, paper_id: uuid.UUID, doi_or_url: str, title: str, actor: str
) -> LiteratureSource:
    key = _identifier_key(doi_or_url)
    existing = session.exec(select(LiteratureSource).where(LiteratureSource.paper_id == paper_id)).all()
    if any(_identifier_key(s.doi_or_url) == key for s in existing):
        raise StageBlockedError("This DOI or URL is already in the paper's source list.")
    source = LiteratureSource(
        paper_id=paper_id,
        title=title or doi_or_url,
        doi_or_url=doi_or_url,
        theme="Manually added",
        verification_status=VerificationStatus.PENDING,
        selected=True,
    )
    session.add(source)
    session.commit()
    record(
        session,
        paper_id=paper_id,
        stage=Stage.LITERATURE_SURVEY,
        agent="user",
        action=f"manually added literature source {source.id} ({doi_or_url}); verification required",
        actor=actor,
    )
    session.refresh(source)
    return source


def set_literature_source_selection(
    session: Session, *, paper_id: uuid.UUID, source_id: uuid.UUID, selected: bool, actor: str
) -> LiteratureSource:
    source = session.get(LiteratureSource, source_id)
    if source is None or source.paper_id != paper_id:
        raise ValueError("Literature source not found")
    if not selected and source.selected:
        sections = session.exec(select(DraftSection).where(DraftSection.paper_id == paper_id)).all()
        if any(str(source.id) in json.loads(section.citations_json) for section in sections):
            raise StageBlockedError("This source is cited in a draft section and cannot be excluded.")
    if source.selected != selected:
        source.selected = selected
        session.add(source)
        session.commit()
        record(
            session,
            paper_id=paper_id,
            stage=Stage.LITERATURE_SURVEY,
            agent="user",
            action=f"{'included' if selected else 'excluded'} literature source {source.id}",
            actor=actor,
        )
    session.refresh(source)
    return source


def set_literature_source_manual_acceptance(
    session: Session, *, paper_id: uuid.UUID, source_id: uuid.UUID, accepted: bool, reason: str, actor: str
) -> LiteratureSource:
    source = session.get(LiteratureSource, source_id)
    if source is None or source.paper_id != paper_id:
        raise ValueError("Literature source not found")
    if accepted:
        if source.verification_status != VerificationStatus.UNVERIFIED:
            raise StageBlockedError(
                "Only sources that failed verification can be manually accepted. Run verification first."
            )
        source.manually_accepted = True
        source.manual_acceptance_reason = reason
        action = f"manually accepted unverified literature source {source.id} ({source.doi_or_url}): {reason}"
    else:
        if not source.manually_accepted:
            raise StageBlockedError("This source has not been manually accepted.")
        source.manually_accepted = False
        source.manual_acceptance_reason = None
        action = f"revoked manual acceptance of literature source {source.id}"
    session.add(source)
    session.commit()
    record(
        session,
        paper_id=paper_id,
        stage=Stage.LITERATURE_SURVEY,
        agent="user",
        action=action,
        actor=actor,
    )
    session.refresh(source)
    return source


def remove_unverified_literature_source(
    session: Session, *, paper_id: uuid.UUID, source_id: uuid.UUID, actor: str
) -> None:
    source = session.get(LiteratureSource, source_id)
    if source is None or source.paper_id != paper_id:
        raise ValueError("Literature source not found")
    if source.verification_status != VerificationStatus.UNVERIFIED:
        raise StageBlockedError("Only unverified literature sources can be removed here.")

    verification_results = session.exec(
        select(CitationVerificationResult).where(
            CitationVerificationResult.literature_source_id == source.id
        )
    ).all()
    for result in verification_results:
        session.delete(result)

    sections = session.exec(select(DraftSection).where(DraftSection.paper_id == paper_id)).all()
    for section in sections:
        citation_ids = json.loads(section.citations_json)
        updated_citation_ids = [citation_id for citation_id in citation_ids if citation_id != str(source.id)]
        if len(updated_citation_ids) != len(citation_ids):
            section.citations_json = json.dumps(updated_citation_ids)
            session.add(section)

    session.delete(source)
    session.commit()
    record(
        session,
        paper_id=paper_id,
        stage=Stage.VERIFICATION,
        agent="orchestration",
        action=f"removed unverified literature source {source.id} ({source.doi_or_url})",
        actor=actor,
    )


async def check_originality(session: Session, *, paper_id: uuid.UUID) -> list[OriginalityFinding]:
    settings = get_settings()
    sources = session.exec(select(LiteratureSource).where(LiteratureSource.paper_id == paper_id)).all()
    corpus = [
        OriginalitySource(identifier=s.doi_or_url, text=s.relevance_summary, is_self_plagiarism=False)
        for s in sources
        if s.relevance_summary
    ]

    sections = session.exec(select(DraftSection).where(DraftSection.paper_id == paper_id)).all()
    findings: list[OriginalityFinding] = []
    for section in sections:
        blocks = session.exec(select(ContentBlock).where(ContentBlock.draft_section_id == section.id)).all()
        for block in blocks:
            matches = originality_agent.check_originality(
                block.text, corpus, threshold=settings.originality_similarity_threshold
            )
            for match in matches:
                finding = OriginalityFinding(
                    paper_id=paper_id,
                    draft_section_id=section.id,
                    flagged_text=block.text,
                    matching_source=match.matching_source,
                    similarity_score=match.similarity_score,
                    is_self_plagiarism=match.is_self_plagiarism,
                )
                session.add(finding)
                findings.append(finding)
    session.commit()
    for finding in findings:
        session.refresh(finding)
    record(
        session,
        paper_id=paper_id,
        stage=Stage.VERIFICATION,
        agent=originality_agent.AGENT_NAME,
        action=f"flagged {len(findings)} originality finding(s)",
        actor=f"system:{originality_agent.AGENT_NAME}",
    )
    return findings


def resolve_originality_finding(
    session: Session,
    *,
    finding_id: uuid.UUID,
    status: OriginalityStatus,
    justification: str | None,
    actor: str,
) -> OriginalityFinding:
    finding = session.get(OriginalityFinding, finding_id)
    if finding is None:
        raise ValueError("Originality finding not found")
    finding.status = status
    finding.justification = justification
    session.add(finding)
    session.commit()
    session.refresh(finding)
    record(
        session,
        paper_id=finding.paper_id,
        stage=Stage.VERIFICATION,
        agent=originality_agent.AGENT_NAME,
        action=f"finding resolved as {status.value}",
        actor=actor,
    )
    return finding


# --- User Story 5: Formatting -------------------------------------------------------------------


def apply_formatting(
    session: Session, *, paper_id: uuid.UUID, venue: Venue, title: str, sections: dict[str, str]
) -> FormattingComplianceReport:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise ValueError("Paper not found")
    paper.target_venue = venue
    session.add(paper)
    session.commit()

    blocking_reason = gate_for_transition(session, paper, Stage.FORMATTING)
    if blocking_reason:
        raise StageBlockedError(blocking_reason)

    formatting_agent.render_formatted_paper(venue=venue, title=title, sections=sections)
    checks = formatting_agent.run_compliance_check(venue=venue, sections=sections)

    report = FormattingComplianceReport(paper_id=paper_id, venue=venue)
    session.add(report)
    session.commit()
    session.refresh(report)
    for check in checks:
        session.add(
            ComplianceCheck(
                report_id=report.id,
                requirement=check.requirement,
                status="pass" if check.passed else "fail",
                detail=check.detail,
            )
        )
    session.commit()

    paper.current_stage = Stage.FORMATTING
    session.add(paper)
    session.commit()
    record(
        session,
        paper_id=paper_id,
        stage=Stage.FORMATTING,
        agent=formatting_agent.AGENT_NAME,
        action=f"formatted for {venue.value}",
        actor=f"system:{formatting_agent.AGENT_NAME}",
    )
    return report


# --- Export ---------------------------------------------------------------------------------------


@dataclass
class ExportContent:
    title: str
    sections: dict[str, str]


def prepare_export(
    session: Session, *, paper_id: uuid.UUID, title: str, sections: dict[str, str], actor: str
) -> ExportContent:
    """Final confidentiality screen over the compiled document before generating an export file.

    New matches are persisted as flags so the user can resolve them like any other flag; the export
    is blocked while any flag is open, and redacted/generalized spans are masked in the exported copy.
    """
    safe_title, _ = _screen_and_flag(session, paper_id=paper_id, field="export:title", text=title)
    safe_sections = {
        key: _screen_and_flag(session, paper_id=paper_id, field=f"export:{key}", text=body)[0]
        for key, body in sections.items()
    }
    open_flags = open_confidentiality_flags(session, paper_id)
    if open_flags:
        raise StageBlockedError(
            f"Resolve {len(open_flags)} open confidentiality flag(s) before downloading the paper."
        )
    record(
        session,
        paper_id=paper_id,
        stage="cross-cutting",
        agent="export",
        action="paper exported as docx",
        actor=actor,
    )
    return ExportContent(title=safe_title, sections=safe_sections)


# --- Stage transitions & status ------------------------------------------------------------------


def advance_stage(session: Session, *, paper_id: uuid.UUID, target_stage: Stage, actor: str) -> Paper:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise ValueError("Paper not found")

    blocking_reason = gate_for_transition(session, paper, target_stage)
    if blocking_reason:
        raise StageBlockedError(blocking_reason)

    paper.current_stage = target_stage
    paper.version += 1
    paper.updated_at = datetime.now(timezone.utc)
    session.add(paper)
    session.commit()
    session.refresh(paper)
    record(
        session,
        paper_id=paper_id,
        stage=target_stage,
        agent="orchestration",
        action=f"advanced to {target_stage.value}",
        actor=actor,
    )
    return paper


@dataclass
class StageStatus:
    stage: str
    state: str  # "done" | "in_progress" | "blocked"
    reason: str | None = None


def get_paper_status(session: Session, *, paper_id: uuid.UUID) -> list[StageStatus]:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise ValueError("Paper not found")

    order = [
        Stage.FRAMING,
        Stage.LITERATURE_SURVEY,
        Stage.DRAFTING,
        Stage.VERIFICATION,
        Stage.FORMATTING,
        Stage.READY_FOR_SUBMISSION,
    ]
    current_index = order.index(paper.current_stage)
    statuses: list[StageStatus] = []
    for index, stage in enumerate(order):
        if index < current_index or stage == paper.current_stage == Stage.READY_FOR_SUBMISSION:
            statuses.append(StageStatus(stage=stage.value, state="done"))
        elif index == current_index:
            reason = gate_for_transition(session, paper, order[index + 1]) if index + 1 < len(order) else None
            statuses.append(
                StageStatus(stage=stage.value, state="blocked" if reason else "in_progress", reason=reason)
            )
        else:
            statuses.append(StageStatus(stage=stage.value, state="pending"))
    return statuses
