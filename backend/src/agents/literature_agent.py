"""Literature Survey Agent (spec.md User Story 2; FR-004/FR-005/FR-006).

Wraps the Semantic Scholar tool call and asks Gemini to select/theme already-retrieved,
verifiable sources — it never invents citations itself (constitution Principle III).
"""
import json

from src.agents.base import build_agent, run_agent_turn_with_retry
from src.services.literature_search import FoundSource, LiteratureSearchError, search_semantic_scholar

_INSTRUCTION = """You are the Literature Survey Agent for Cotality's research paper assistant.
You will be given a user query, research questions, a problem statement, and a numbered list of real,
already-retrieved sources with their titles, authors, year, venue, and abstracts. Select ONLY sources
that are directly relevant to the query and clearly help answer at least one research question.
If no research questions are supplied, assess relevance against the query and problem statement.
Use the full abstract when available; a missing abstract alone is not a reason to exclude a source
whose title clearly establishes relevance. Never invent evidence not present in its metadata.
Exclude tangential matches, generic background, and papers whose title/abstract does not support a
clear connection. If none qualify, return an empty list. Group selected sources into themes and give
each a concise relevance_summary explaining the specific connection to the query or a research question.

Respond ONLY as compact JSON: a list of objects with "source_index" (the exact integer index from
the input list), "theme", and "relevance_summary". Do not include an index unless the source meets
the relevance criteria. Do not invent or modify source metadata.
"""


def _agent():
    return build_agent(name="literature_survey_agent", instruction=_INSTRUCTION)


async def run_literature_survey(
    *,
    paper_id: str,
    problem_statement: str,
    query: str,
    research_questions: list[str],
    year_range: str | None = None,
) -> list[FoundSource]:
    search_queries = dict.fromkeys(
        text.strip() for text in [query, *research_questions] if text.strip()
    )
    retrieved: list[FoundSource] = []
    seen_identifiers: set[str] = set()
    for search_query in search_queries:
        candidates = await search_semantic_scholar(search_query, year_range=year_range)
        for source in candidates:
            identifier = source.doi_or_url.strip().casefold()
            if identifier and identifier not in seen_identifiers:
                seen_identifiers.add(identifier)
                retrieved.append(source)
    if not retrieved:
        return []

    payload = {
        "query": query,
        "research_questions": research_questions,
        "problem_statement": problem_statement,
        "sources": [
            {
                "source_index": index,
                "title": source.title,
                "authors": source.authors,
                "year": source.year,
                "venue": source.venue,
                "abstract": source.abstract or source.relevance_summary,
            }
            for index, source in enumerate(retrieved)
        ],
    }
    raw_output = await run_agent_turn_with_retry(
        _agent(),
        user_id="system",
        session_id=f"survey-{paper_id}",
        message=json.dumps(payload),
    )
    try:
        selected = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise LiteratureSearchError("Literature sources could not be reliably filtered for relevance.") from exc
    if not isinstance(selected, list):
        raise LiteratureSearchError("Literature relevance filter returned an invalid response.")

    filtered: list[FoundSource] = []
    seen_indices: set[int] = set()
    for item in selected:
        if not isinstance(item, dict):
            raise LiteratureSearchError("Literature relevance filter returned an invalid source selection.")
        index = item.get("source_index")
        theme = item.get("theme")
        relevance_summary = item.get("relevance_summary")
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or index < 0
            or index >= len(retrieved)
            or not isinstance(theme, str)
            or not theme.strip()
            or not isinstance(relevance_summary, str)
            or not relevance_summary.strip()
        ):
            raise LiteratureSearchError("Literature relevance filter returned an invalid source selection.")
        if index in seen_indices:
            continue
        seen_indices.add(index)
        source = retrieved[index]
        filtered.append(
            FoundSource(
                title=source.title,
                authors=source.authors,
                year=source.year,
                venue=source.venue,
                doi_or_url=source.doi_or_url,
                relevance_summary=relevance_summary.strip(),
                theme=theme.strip(),
            )
        )
    return filtered
