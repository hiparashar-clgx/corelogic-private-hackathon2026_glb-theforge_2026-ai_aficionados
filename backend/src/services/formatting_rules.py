"""Formatting compliance checks per venue (spec.md FR-014; research.md FR-023 decision: IEEE/ACM/arXiv)."""
from dataclasses import dataclass

from src.models.enums import Venue

_WORD_LIMITS = {
    Venue.IEEE: {"abstract": 250},
    Venue.ACM: {"abstract": 250},
    Venue.ARXIV: {"abstract": 300},
}

_REQUIRED_SECTIONS = {
    Venue.IEEE: ["abstract", "introduction", "related_work", "methods", "results", "discussion", "conclusion"],
    Venue.ACM: ["abstract", "introduction", "related_work", "methods", "results", "discussion", "conclusion"],
    Venue.ARXIV: ["abstract", "introduction", "methods", "results", "conclusion"],
}


@dataclass
class ComplianceResult:
    requirement: str
    passed: bool
    detail: str | None = None


def check_compliance(venue: Venue, sections: dict[str, str]) -> list[ComplianceResult]:
    results: list[ComplianceResult] = []

    for required in _REQUIRED_SECTIONS[venue]:
        present = required in sections and sections[required].strip()
        results.append(
            ComplianceResult(
                requirement=f"Required section present: {required}",
                passed=bool(present),
                detail=None if present else f"Missing or empty section: {required}",
            )
        )

    limits = _WORD_LIMITS.get(venue, {})
    for section, limit in limits.items():
        word_count = len(sections.get(section, "").split())
        passed = word_count <= limit
        results.append(
            ComplianceResult(
                requirement=f"{section.title()} \u2264 {limit} words",
                passed=passed,
                detail=None if passed else f"{section} is {word_count} words (limit {limit})",
            )
        )

    return results
