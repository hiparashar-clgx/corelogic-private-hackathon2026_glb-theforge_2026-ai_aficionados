"""Document export (docx) — spec.md FR-020: export/download at any point, any stage."""
import html
import io
import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from docx import Document

from src.models.enums import SectionType, Venue

SECTION_ORDER: list[str] = [section.value for section in SectionType]

_SECTION_TITLES = {
    SectionType.ABSTRACT.value: "Abstract",
    SectionType.INTRODUCTION.value: "Introduction",
    SectionType.RELATED_WORK.value: "Related Work",
    SectionType.METHODS.value: "Methods",
    SectionType.RESULTS.value: "Results",
    SectionType.DISCUSSION.value: "Discussion",
    SectionType.CONCLUSION.value: "Conclusion",
}
_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
_BRACKET_PATTERN = re.compile(r"\[([^\[\]]+)\]")
_DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s\]]+")
_MARKDOWN_HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.*)$")


@dataclass(frozen=True)
class ExportReference:
    doi_or_url: str
    title: str
    authors: list[str] = field(default_factory=list)
    venue: str = ""
    year: int | None = None


def _normalize_identifier(value: str) -> str:
    """DOIs match regardless of URL prefix (drafts sometimes mangle it); other URLs match verbatim."""
    doi = _DOI_PATTERN.search(value)
    if doi:
        return doi.group(0).rstrip("/.").lower()
    return value.strip().rstrip("/.").lower()


def order_sections(sections: dict[str, str]) -> list[tuple[str, str]]:
    """Canonical paper order; unknown section keys keep their relative order at the end."""
    known = [(key, sections[key]) for key in SECTION_ORDER if key in sections]
    extra = [(key, body) for key, body in sections.items() if key not in SECTION_ORDER]
    return known + extra


def _number_references(
    sections: list[tuple[str, str]], references: Iterable[ExportReference]
) -> tuple[list[tuple[str, str]], list[ExportReference]]:
    """Replace inline [doi_or_url] markers with IEEE-style [n] and order references by first use."""
    by_identifier = {_normalize_identifier(ref.doi_or_url): ref for ref in references}
    numbered: list[ExportReference] = []
    numbers: dict[str, int] = {}

    def number_for(identifier: str) -> int:
        if identifier not in numbers:
            numbered.append(by_identifier[identifier])
            numbers[identifier] = len(numbered)
        return numbers[identifier]

    def replace(match: re.Match[str]) -> str:
        parts = [_normalize_identifier(part) for part in re.split(r"\s*;\s*|,\s+", match.group(1).strip())]
        if not parts or any(part not in by_identifier for part in parts):
            return match.group(0)
        return ", ".join(f"[{number_for(part)}]" for part in parts)

    renumbered = [(key, _BRACKET_PATTERN.sub(replace, body)) for key, body in sections]
    for identifier in by_identifier:
        if identifier not in numbers:
            number_for(identifier)
    return renumbered, numbered


def _format_reference(number: int, reference: ExportReference) -> str:
    authors = ", ".join(html.unescape(author.strip()) for author in reference.authors if author.strip())
    segments = [
        authors,
        f"\u201c{html.unescape(reference.title)}\u201d" if reference.title else "",
        html.unescape(reference.venue.strip()),
        str(reference.year) if reference.year else "",
    ]
    text = ", ".join(segment for segment in segments if segment)
    return f"[{number}] {text}. {reference.doi_or_url}" if text else f"[{number}] {reference.doi_or_url}"


def _heading(section_key: str, index: int, venue: Venue | None) -> str:
    title = _SECTION_TITLES.get(section_key, section_key.replace("_", " ").title())
    if venue == Venue.IEEE and section_key != SectionType.ABSTRACT.value and index < len(_ROMAN):
        return f"{_ROMAN[index]}. {title}"
    return title


def _add_body(document, body: str, *, section_title: str) -> None:
    """Blank-line separated paragraphs; markdown headings become sub-headings (or are dropped if they
    just repeat the section title, which drafted text often does)."""
    for index, paragraph in enumerate(p.strip() for p in re.split(r"\n\s*\n", body.strip())):
        if not paragraph:
            continue
        heading = _MARKDOWN_HEADING_PATTERN.match(paragraph)
        if heading and "\n" not in paragraph:
            text = heading.group(1).strip().strip("*").strip()
            if not (index == 0 and text.lower() == section_title.lower()):
                document.add_heading(text, level=2)
            continue
        document.add_paragraph(paragraph)


def render_paper_docx(
    *,
    title: str,
    sections: list[tuple[str, str]],
    references: Iterable[ExportReference] = (),
    venue: Venue | None = None,
) -> bytes:
    """Render the full paper (title, ordered sections, numbered references) as a docx.

    Callers MUST run the confidentiality screen over the compiled text before calling this
    (see contracts/api-contracts.md "Export" — final screen before file generation).
    """
    sections, numbered_references = _number_references(sections, references)

    document = Document()
    document.core_properties.title = title
    document.add_heading(title, level=0)
    numbered_index = 0
    for section_key, body in sections:
        heading = _heading(section_key, numbered_index, venue)
        document.add_heading(heading, level=1)
        if section_key != SectionType.ABSTRACT.value:
            numbered_index += 1
        _add_body(document, body, section_title=_SECTION_TITLES.get(section_key, ""))

    if numbered_references:
        document.add_heading("References", level=1)
        for number, reference in enumerate(numbered_references, start=1):
            document.add_paragraph(_format_reference(number, reference))

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
