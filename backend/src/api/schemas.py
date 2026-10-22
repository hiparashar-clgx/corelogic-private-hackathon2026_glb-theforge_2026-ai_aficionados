"""Pydantic request/response schemas for the API layer (contracts/api-contracts.md)."""
import uuid
from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, field_validator, model_validator

from src.models.enums import (
    ComplianceStatus,
    FlagResolution,
    OriginalityStatus,
    ProblemStatementStatus,
    SectionType,
    Stage,
    Venue,
    VerificationStatus,
)


class PaperCreate(BaseModel):
    title: str


class PaperOut(BaseModel):
    id: uuid.UUID
    owner_user_id: str
    title: str
    current_stage: Stage
    target_venue: Venue | None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StageStatusOut(BaseModel):
    stage: str
    state: str
    reason: str | None = None


class ProblemStatementDraftRequest(BaseModel):
    raw_input: str


class ResearchQuestionsRequest(BaseModel):
    selected_problem_statement: str


class ProblemStatementAcceptRequest(BaseModel):
    refined_statement: str
    research_questions: list[str]


class ProblemStatementOut(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    raw_input: str
    refined_statement: str
    research_questions: list[str]
    status: ProblemStatementStatus
    confirmed_at: datetime | None


class ResearchQuestionsOut(BaseModel):
    research_questions: list[str]


class ConfidentialityFlagOut(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    source_field: str
    matched_text: str
    flag_reason: str
    resolution: FlagResolution
    resolved_by: str | None
    resolved_at: datetime | None


class ConfidentialityFlagResolveRequest(BaseModel):
    resolution: FlagResolution


class LiteratureSurveyRequest(BaseModel):
    query: str
    year_range: str | None = None


def _normalize_source_identifier(value: str) -> str:
    value = value.strip()
    if value.lower().startswith("doi:"):
        value = value[4:].strip()
    if not value or any(character.isspace() for character in value):
        raise ValueError("Enter a DOI or an HTTP(S) source URL without spaces.")
    if value.startswith("10.") and "/" in value:
        return f"https://doi.org/{value}"
    url = urlsplit(value)
    if url.scheme in {"http", "https"} and url.hostname:
        return value
    raise ValueError("Enter a DOI (10.prefix/suffix) or an HTTP(S) source URL.")


class LiteratureSourceUpdateRequest(BaseModel):
    doi_or_url: str

    @field_validator("doi_or_url")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return _normalize_source_identifier(value)


class LiteratureSourceCreateRequest(BaseModel):
    doi_or_url: str
    title: str = ""

    @field_validator("doi_or_url")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return _normalize_source_identifier(value)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()


class LiteratureSourceSelectionRequest(BaseModel):
    selected: bool


class LiteratureSourceManualAcceptanceRequest(BaseModel):
    accepted: bool
    reason: str = ""

    @model_validator(mode="after")
    def require_reason_when_accepting(self) -> "LiteratureSourceManualAcceptanceRequest":
        self.reason = self.reason.strip()
        if self.accepted and not self.reason:
            raise ValueError("Give a reason for manually accepting an unverified source.")
        return self


class LiteratureSourceOut(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    title: str
    authors: list[str]
    year: int | None
    venue: str
    doi_or_url: str
    theme: str
    relevance_summary: str
    verification_status: VerificationStatus
    verification_failure_reason: str | None
    selected: bool = True
    manually_accepted: bool = False
    manual_acceptance_reason: str | None = None


class SectionDraftRequest(BaseModel):
    user_notes: str = ""


class ContentBlockOut(BaseModel):
    id: uuid.UUID
    order: int
    text: str
    origin: str
    accepted: bool


class DraftSectionOut(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    section_type: SectionType
    blocks: list[ContentBlockOut]


class ContentBlockUpdateRequest(BaseModel):
    text: str | None = None
    accepted: bool | None = None


class CitationVerificationResultOut(BaseModel):
    id: uuid.UUID
    literature_source_id: uuid.UUID
    status: VerificationStatus
    failure_reason: str | None


class OriginalityFindingOut(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    draft_section_id: uuid.UUID
    flagged_text: str
    matching_source: str
    similarity_score: float
    is_self_plagiarism: bool
    status: OriginalityStatus
    justification: str | None


class OriginalityResolveRequest(BaseModel):
    status: OriginalityStatus
    justification: str | None = None


class AdvanceStageRequest(BaseModel):
    target_stage: Stage


class FormattingApplyRequest(BaseModel):
    venue: Venue


class ComplianceCheckOut(BaseModel):
    requirement: str
    status: ComplianceStatus
    detail: str | None


class FormattingComplianceReportOut(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    venue: Venue
    generated_at: datetime
    checks: list[ComplianceCheckOut]


class ErrorResponse(BaseModel):
    detail: str
