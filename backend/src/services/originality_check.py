"""Originality/similarity checking (research.md decision: internal embedding-similarity check).

v1 uses a dependency-free TF-IDF + cosine similarity implementation (pure Python — no
numpy/scikit-learn, which lack prebuilt wheels on some newer Python versions) as a stand-in for a
full embedding index; the interface is kept narrow so a commercial provider or a real embedding
model can be substituted later without changing callers (research.md FR-022 decision).
"""
import math
import re
from collections import Counter
from dataclasses import dataclass

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass
class OriginalitySource:
    identifier: str  # e.g., a DOI/URL or "prior-paper:<id>"
    text: str
    is_self_plagiarism: bool = False


@dataclass
class SimilarityMatch:
    matching_source: str
    similarity_score: float
    is_self_plagiarism: bool


def _tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


def _term_frequencies(tokens: list[str]) -> Counter:
    return Counter(tokens)


def _cosine_similarity(a: Counter, b: Counter) -> float:
    shared_terms = set(a) & set(b)
    dot_product = sum(a[term] * b[term] for term in shared_terms)
    norm_a = math.sqrt(sum(count * count for count in a.values()))
    norm_b = math.sqrt(sum(count * count for count in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def find_similar_passages(
    passage: str, corpus: list[OriginalitySource], *, threshold: float = 0.8
) -> list[SimilarityMatch]:
    """Return corpus entries whose similarity to `passage` meets/exceeds `threshold`."""
    if not corpus or not passage.strip():
        return []

    passage_vector = _term_frequencies(_tokenize(passage))
    matches = []
    for item in corpus:
        item_vector = _term_frequencies(_tokenize(item.text))
        score = _cosine_similarity(passage_vector, item_vector)
        if score >= threshold:
            matches.append(
                SimilarityMatch(
                    matching_source=item.identifier,
                    similarity_score=score,
                    is_self_plagiarism=item.is_self_plagiarism,
                )
            )

    return sorted(matches, key=lambda m: m.similarity_score, reverse=True)

