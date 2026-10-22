"""Formatting Agent (spec.md User Story 5; FR-013/FR-014/FR-015).

Applies a venue-specific Jinja2 template (src/templates/) to compile the paper and runs
deterministic structural compliance checks (src.services.formatting_rules). Gemini is not required
for this stage since it is a rules/templating problem, not a generative one.
"""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.models.enums import Venue
from src.services.formatting_rules import ComplianceResult, check_compliance

AGENT_NAME = "formatting_agent"

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=select_autoescape())


def render_formatted_paper(*, venue: Venue, title: str, sections: dict[str, str]) -> str:
    template = _env.get_template(f"{venue.value}.md.jinja")
    return template.render(title=title, sections=sections)


def run_compliance_check(*, venue: Venue, sections: dict[str, str]) -> list[ComplianceResult]:
    return check_compliance(venue, sections)
