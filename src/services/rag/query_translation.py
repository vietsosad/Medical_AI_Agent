"""Vietnamese clinical query -> English concept terms, from the curated ontology.

The knowledge corpora are entirely English while patients speak Vietnamese, and
text-embedding-3-large is markedly weaker cross-lingually than the multilingual
encoder it replaces: on a chest-pain query, the English phrasing scores 0.53
against the same corpus where the Vietnamese phrasing scores 0.29. An English
channel is therefore not an optimisation, it is what makes retrieval work.

The mapping is not invented here. `data/guard_rules/ontology_vi_en.json` already
carries 31 reviewed clinical concepts with English terms, Vietnamese terms and
real patient slang; only its red-flag keywords were being used and the English
half was discarded. This module reads the same file, so the vocabulary a
clinician reviews is the vocabulary retrieval uses.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ONTOLOGY_PATH = Path("data/guard_rules/ontology_vi_en.json")


def fold(text: str) -> str:
    """Diacritic-insensitive form, so 'kho tho' still matches 'khó thở'."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    stripped = stripped.replace("đ", "d")
    return re.sub(r"\s+", " ", stripped).strip()


@dataclass(frozen=True)
class ConceptMatch:
    concept_key: str
    clinical_name: str
    english_terms: tuple[str, ...]
    matched_surface: str
    matched_via: str


@dataclass(frozen=True)
class TranslatedQuery:
    query_vi: str
    query_en: str
    concepts: tuple[ConceptMatch, ...]
    sparse_terms: tuple[str, ...]
    degraded_modes: tuple[str, ...]


@lru_cache(maxsize=1)
def _load_index() -> tuple[tuple[str, str, str, tuple[str, ...], str], ...]:
    """Flatten the ontology into (folded_surface, concept, name, en_terms, via).

    Longest surface first so 'đau ngực dữ dội' is not shadowed by 'đau ngực'.
    """
    if not ONTOLOGY_PATH.exists():
        return ()
    data = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    entries: list[tuple[str, str, str, tuple[str, ...], str]] = []
    for key, entry in data.items():
        english = tuple(entry.get("standard_en_terms", []))
        if not english:
            continue
        name = str(entry.get("clinical_name", key))
        for field, via in (
            ("standard_vi_terms", "clinical_term"),
            ("patient_slang_dialect", "patient_slang"),
        ):
            for surface in entry.get(field, []):
                folded = fold(str(surface))
                if folded:
                    entries.append((folded, key, name, english, via))
        # The English terms themselves are surfaces too: patients and nurses mix
        # languages, and an English word in the message should still route.
        for surface in english:
            entries.append((fold(str(surface)), key, name, english, "english_term"))
    entries.sort(key=lambda item: len(item[0]), reverse=True)
    return tuple(entries)


def _tokens(text: str) -> set[str]:
    return {t for t in fold(text).split() if len(t) > 2}


MAX_CONCEPTS = 3


def match_concepts(text: str, *, max_concepts: int = MAX_CONCEPTS) -> list[ConceptMatch]:
    """Exact surface matches first; only if none, a scored token-overlap fallback.

    Both paths are capped. An uncapped fallback matched eleven concepts for one
    abdominal-pain sentence, and pouring eleven concepts' worth of English into
    one query buries the two terms that actually describe the patient.
    """
    haystack = fold(text)
    tokens = _tokens(text)
    seen: set[str] = set()
    matches: list[ConceptMatch] = []

    for surface, key, name, english, via in _load_index():
        if key in seen:
            continue
        if surface and surface in haystack:
            seen.add(key)
            matches.append(ConceptMatch(key, name, english, surface, via))
    if matches:
        return matches[:max_concepts]

    # Fallback: rank by how much of the concept's surface the message shares,
    # requiring two content tokens so a bare "đau" cannot match every painful
    # presentation in the ontology.
    scored: dict[str, tuple[int, ConceptMatch]] = {}
    for surface, key, name, english, via in _load_index():
        overlap = len(_tokens(surface) & tokens)
        if overlap < 2:
            continue
        candidate = ConceptMatch(key, name, english, surface, f"{via}_partial")
        if key not in scored or overlap > scored[key][0]:
            scored[key] = (overlap, candidate)
    ranked = sorted(scored.values(), key=lambda item: item[0], reverse=True)
    return [match for _, match in ranked[:max_concepts]]


def translate_query(query_vi: str, *, max_terms_per_concept: int = 4) -> TranslatedQuery:
    """Build an English retrieval query from a Vietnamese clinical message."""
    matches = match_concepts(query_vi)
    english_terms: list[str] = []
    sparse: list[str] = []
    for match in matches:
        for term in match.english_terms[:max_terms_per_concept]:
            if term not in english_terms:
                english_terms.append(term)
            # Unigrams, because the corpus keyword index is unigram English;
            # an underscored slug matches nothing there.
            for token in re.findall(r"[a-z0-9]+", term.lower()):
                if len(token) > 2 and token not in sparse:
                    sparse.append(token)

    degraded: list[str] = []
    if not english_terms:
        degraded.append("EN_CHANNEL_UNAVAILABLE")

    return TranslatedQuery(
        query_vi=query_vi,
        query_en=", ".join(english_terms),
        concepts=tuple(matches),
        sparse_terms=tuple(sparse),
        degraded_modes=tuple(degraded),
    )
