"""Enum types shared across models (see specs/001-research-paper-agents/data-model.md)."""
from enum import StrEnum


class Stage(StrEnum):
    FRAMING = "framing"
    LITERATURE_SURVEY = "literature_survey"
    DRAFTING = "drafting"
    VERIFICATION = "verification"
    FORMATTING = "formatting"
    READY_FOR_SUBMISSION = "ready_for_submission"


class Venue(StrEnum):
    IEEE = "ieee"
    ACM = "acm"
    ARXIV = "arxiv"


class ProblemStatementStatus(StrEnum):
    DRAFT = "draft"
    ACCEPTED = "accepted"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    PENDING = "pending"


class ContentOrigin(StrEnum):
    SYSTEM_GENERATED = "system_generated"
    USER_AUTHORED = "user_authored"


class FlagResolution(StrEnum):
    OPEN = "open"
    REDACTED = "redacted"
    GENERALIZED = "generalized"
    CONFIRMED_SAFE = "confirmed_safe"


class OriginalityStatus(StrEnum):
    OPEN = "open"
    REWRITTEN = "rewritten"
    ACCEPTED_WITH_JUSTIFICATION = "accepted_with_justification"


class ComplianceStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class SectionType(StrEnum):
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
