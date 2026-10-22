"""Drafting Agent (spec.md User Story 3; FR-007/FR-008).

Generates system-suggested content blocks for a single paper section, grounded in the confirmed
problem statement, literature survey, and any user-supplied notes. Never touches blocks already
marked `accepted` by the user (enforced by the orchestration layer, not this agent).
"""
from src.agents.base import build_agent, run_agent_turn_with_retry

_INSTRUCTION = """You are the Drafting Agent for Cotality's research paper assistant.
Given a section name, the confirmed problem statement, a list of surveyed sources (with
doi_or_url), and optional user notes, write a draft for that section grounded strictly in the
provided material. When you reference a source, cite it by its doi_or_url in square brackets,
e.g. [https://doi.org/10.1000/example]. Do not fabricate results, data, or citations not present
in the input. Keep the draft to 2-4 paragraphs.
"""


def _agent():
    return build_agent(name="drafting_agent", instruction=_INSTRUCTION)


async def draft_section(
    *, paper_id: str, section_type: str, problem_statement: str, sources_context: str, user_notes: str = ""
) -> str:
    message = (
        f"Section: {section_type}\n"
        f"Problem statement: {problem_statement}\n"
        f"Surveyed sources:\n{sources_context}\n"
        f"User notes: {user_notes or '(none)'}"
    )
    return await run_agent_turn_with_retry(
        _agent(), user_id="system", session_id=f"draft-{paper_id}-{section_type}", message=message
    )
