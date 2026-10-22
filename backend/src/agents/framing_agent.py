"""Problem Framing Agent (spec.md User Story 1; FR-001).

Turns a raw, informal problem description into a structured problem statement plus 2-3 candidate
problem statements. Confidentiality screening (src.services.confidentiality_screen) MUST be run on
the raw input before it reaches this agent's prompt — see src.orchestration.pipeline.
"""
import json

from src.agents.base import build_agent, run_agent_turn_with_retry

_INSTRUCTION = """You are the Problem Framing Agent for Cotality's research paper assistant.
Given a rough, informal description of a work problem, produce:
1. A concise "context" paragraph (why this problem matters).
2. Exactly 3-4 clear "problem" statements (1-2 sentences each), with each statement on a separate line.

Respond ONLY as compact JSON with keys: context, problem.
Do not invent specific company, customer, or dataset names beyond what the user provided.
"""

_QUESTION_INSTRUCTION = """You are the Research Question Agent for Cotality's research paper assistant.
You will receive exactly one problem statement selected by the user. Suggest 3-7 focused, answerable
research questions that address only that selected problem statement. Do not broaden the scope to
other problems or introduce unsupported company, customer, or dataset details.

Respond ONLY as compact JSON with the key research_questions, whose value is a list of strings.
"""


def _agent():
    return build_agent(name="framing_agent", instruction=_INSTRUCTION)


def _question_agent():
    return build_agent(name="research_question_agent", instruction=_QUESTION_INSTRUCTION)


async def frame_problem_statement(*, paper_id: str, redacted_input: str) -> dict:
    """Returns {"context": str, "problem": str}.

    `redacted_input` MUST already have any confirmed-confidential spans redacted/generalized.
    """
    raw_output = await run_agent_turn_with_retry(
        _agent(), user_id="system", session_id=f"framing-{paper_id}", message=redacted_input
    )
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        # Fail closed with a usable fallback rather than surfacing a broken response to the user.
        parsed = {
            "context": "",
            "problem": raw_output.strip(),
        }
    return parsed


async def suggest_research_questions(*, paper_id: str, selected_problem_statement: str) -> list[str]:
    """Suggests questions scoped exclusively to the user's selected problem statement."""
    raw_output = await run_agent_turn_with_retry(
        _question_agent(),
        user_id="system",
        session_id=f"framing-{paper_id}-questions",
        message=selected_problem_statement,
    )
    parsed = json.loads(raw_output)
    questions = parsed.get("research_questions") if isinstance(parsed, dict) else None
    if not isinstance(questions, list) or not all(isinstance(question, str) for question in questions):
        raise ValueError("The research question agent returned an invalid response.")
    return questions
