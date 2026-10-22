"""Originality/Plagiarism Agent (spec.md User Story 4; FR-010/FR-011/FR-012; constitution Principle II).

Similarity detection is deterministic (src.services.originality_check); Gemini is used only to
propose rewrite suggestions for flagged passages, never to decide pass/fail itself.
"""
from src.agents.base import build_agent, run_agent_turn_with_retry
from src.services.originality_check import OriginalitySource, SimilarityMatch, find_similar_passages

AGENT_NAME = "originality_agent"

_REWRITE_INSTRUCTION = """You are the Originality Agent for Cotality's research paper assistant.
You will be given a flagged passage that is too similar to an existing source. Rewrite it so the
meaning is preserved but the wording is original, and remind the author to keep/add a proper
citation to the matching source. Respond with only the rewritten passage text.
"""


def check_originality(
    passage: str, corpus: list[OriginalitySource], *, threshold: float
) -> list[SimilarityMatch]:
    return find_similar_passages(passage, corpus, threshold=threshold)


def _rewrite_agent():
    return build_agent(name="originality_rewrite_agent", instruction=_REWRITE_INSTRUCTION)


async def suggest_rewrite(*, paper_id: str, flagged_text: str, matching_source: str) -> str:
    message = f"Flagged passage: {flagged_text}\nMatching source: {matching_source}"
    return await run_agent_turn_with_retry(
        _rewrite_agent(), user_id="system", session_id=f"originality-{paper_id}", message=message
    )
