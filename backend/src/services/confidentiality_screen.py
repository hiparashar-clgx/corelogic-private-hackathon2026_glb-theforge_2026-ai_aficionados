"""Rule/heuristic-based confidentiality & IP screening (constitution Principle V; spec.md FR-002).

This is the mandatory first line of defense run before any content is sent to an external tool
call or included in an export. It is advisory, not a legal compliance guarantee (see research.md
"Confidentiality/DLP screening approach" and spec.md Assumptions) — final responsibility for not
disclosing confidential information remains with the user (constitution Principle I).
"""
import re
from dataclasses import dataclass

# Seed patterns; in production this list should be sourced from a Cotality-maintained
# customer/codename registry (see research.md Outstanding Follow-ups).
_INTERNAL_CODENAME_PATTERN = re.compile(r"\b(project|codename)[\s_-]+[a-z0-9]+\b", re.IGNORECASE)
_CUSTOMER_MARKER_PATTERN = re.compile(
    r"\b(customer|client)\s+(name|id)?\s*[:#]?\s*[a-z0-9][\w\s&.,'-]{1,60}\b", re.IGNORECASE
)
_INTERNAL_DATASET_PATTERN = re.compile(
    r"\b[a-z0-9_]*_(prod|internal|dataset|db)_[a-z0-9_]+\b", re.IGNORECASE
)
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@cotality\.com\b", re.IGNORECASE)


@dataclass
class ScreeningMatch:
    matched_text: str
    reason: str


_RULES: list[tuple[re.Pattern[str], str]] = [
    (_INTERNAL_CODENAME_PATTERN, "possible internal project codename"),
    (_CUSTOMER_MARKER_PATTERN, "possible customer name or identifier"),
    (_INTERNAL_DATASET_PATTERN, "possible internal dataset/database name"),
    (_EMAIL_PATTERN, "internal Cotality email address"),
]


def screen_text(text: str) -> list[ScreeningMatch]:
    """Return all likely-confidential matches found in `text`. Empty list == nothing flagged."""
    matches: list[ScreeningMatch] = []
    for pattern, reason in _RULES:
        for match in pattern.finditer(text):
            matches.append(ScreeningMatch(matched_text=match.group(0), reason=reason))
    return matches
