"""Literature search client (research.md decision: Semantic Scholar primary, CrossRef fallback).

Implements spec.md FR-004 (themed survey with full citation metadata) and FR-005 (never fabricate
a source — if the API can't find/verify something, say so).
"""
from dataclasses import dataclass, field
from html import unescape
import re
import ssl

import certifi
import httpx

try:
    import truststore
except ImportError:  # pragma: no cover - truststore is a production dependency
    truststore = None

from src.config import get_settings

_SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_CROSSREF_WORKS_URL = "https://api.crossref.org/works"


@dataclass
class FoundSource:
    title: str
    authors: list[str]
    year: int | None
    venue: str
    doi_or_url: str
    relevance_summary: str = ""
    theme: str = field(default="general")
    abstract: str = ""


class LiteratureSearchError(Exception):
    """Raised when the external literature search tool is unavailable or errors out.

    Callers MUST surface this to the user rather than silently treating the survey as empty
    (spec.md Edge Cases: "external literature-search ... tool is unavailable/errors out").
    """


def _source_from_crossref(item: dict) -> FoundSource | None:
    doi = item.get("DOI")
    if not doi:
        return None
    date_parts = (item.get("published-print") or item.get("published-online") or {}).get("date-parts", [[]])
    year = date_parts[0][0] if date_parts and date_parts[0] else None
    authors = []
    for author in item.get("author", []):
        name = " ".join(part for part in (author.get("given"), author.get("family")) if part)
        if name:
            authors.append(name)
    return FoundSource(
        title=(item.get("title") or [""])[0].strip(),
        authors=authors,
        year=year,
        venue=(item.get("container-title") or [""])[0],
        doi_or_url=f"https://doi.org/{doi}",
        abstract=unescape(re.sub(r"<[^>]+>", " ", item.get("abstract") or "")).strip(),
    )


async def search_crossref(query: str, *, limit: int = 10, year_range: str | None = None) -> list[FoundSource]:
    params = {"query.bibliographic": query, "rows": limit}
    if year_range and "-" in year_range:
        start, end = year_range.split("-", 1)
        if start.isdigit() and end.isdigit():
            params["filter"] = f"from-pub-date:{start}-01-01,until-pub-date:{end}-12-31"
    headers = {"User-Agent": "ResearchAssist/0.1 (mailto:researchassist@example.com)"}
    try:
        async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
            response = await client.get(_CROSSREF_WORKS_URL, params=params, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LiteratureSearchError(f"CrossRef search failed: {exc}") from exc

    sources = []
    for item in response.json().get("message", {}).get("items", []):
        source = _source_from_crossref(item)
        if source is not None:
            sources.append(source)
    return sources


def _ssl_context() -> ssl.SSLContext:
    """Use the Windows/system trust store, falling back to certifi when unavailable."""
    if truststore is not None:
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return ssl.create_default_context(cafile=certifi.where())


async def search_semantic_scholar(
    query: str, *, limit: int = 10, year_range: str | None = None
) -> list[FoundSource]:
    settings = get_settings()
    headers = {"x-api-key": settings.semantic_scholar_api_key} if settings.semantic_scholar_api_key else {}
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,venue,externalIds,abstract",
    }
    if year_range:
        params["year"] = year_range

    try:
        async with httpx.AsyncClient(timeout=15.0, verify=_ssl_context()) as client:
            response = await client.get(_SEMANTIC_SCHOLAR_SEARCH_URL, params=params, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        try:
            return await search_crossref(query, limit=limit, year_range=year_range)
        except LiteratureSearchError as fallback_exc:
            raise LiteratureSearchError(
                f"Semantic Scholar search failed and CrossRef fallback failed: {fallback_exc}"
            ) from exc

    payload = response.json()
    sources: list[FoundSource] = []
    for item in payload.get("data", []):
        doi = (item.get("externalIds") or {}).get("DOI")
        url = f"https://www.semanticscholar.org/paper/{item.get('paperId')}" if item.get("paperId") else None
        doi_or_url = f"https://doi.org/{doi}" if doi else (url or "")
        if not doi_or_url:
            # No verifiable identifier — skip rather than presenting an unverifiable "citation".
            continue
        sources.append(
            FoundSource(
                title=item.get("title", "").strip(),
                authors=[a.get("name", "") for a in item.get("authors", [])],
                year=item.get("year"),
                venue=item.get("venue") or "",
                doi_or_url=doi_or_url,
                relevance_summary=(item.get("abstract") or "")[:400],
                abstract=item.get("abstract") or "",
            )
        )
    return sources


async def resolve_doi(doi_or_url: str) -> bool:
    """Best-effort check that a DOI/URL resolves to a real record (used by citation verification)."""
    target = doi_or_url
    if not target.lower().startswith("http"):
        target = f"https://doi.org/{target}"
    doi = _extract_doi(doi_or_url)
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=_ssl_context()) as client:
            try:
                response = await client.head(target)
                if response.status_code >= 400:
                    response = await client.get(target)
                if response.status_code < 400:
                    return True
            except httpx.HTTPError:
                if not doi:
                    raise
            # Publisher landing pages (e.g. ACM) often block automated requests with 403, so
            # confirm the DOI against the CrossRef registry instead.
            if doi:
                registry = await client.get(f"{_CROSSREF_WORKS_URL}/{doi}")
                return registry.status_code == 200
            return False
    except httpx.HTTPError:
        return False


def _extract_doi(doi_or_url: str) -> str | None:
    match = re.search(r"(10\.\d{4,9}/\S+)", doi_or_url.strip())
    if not match:
        return None
    if doi_or_url.lower().startswith("http") and "doi.org/" not in doi_or_url.lower():
        return None
    return match.group(1)
