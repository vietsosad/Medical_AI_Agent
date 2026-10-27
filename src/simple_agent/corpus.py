"""Loads the four mock-corpus JSONL files and their embedding indexes.

Pure data access: no LLM calls, no session/conversation state. ``Corpus`` is
the single source of truth for concept/fact/atom lookups, alias matching, and
embedding retrieval. The model may only ever reference IDs this module knows
about; it cannot invent a clinical concept, fact target, or protocol atom.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_FILES = (
    "clinical_concepts.jsonl",
    "concept_relations.jsonl",
    "protocol_atoms.jsonl",
    "fact_targets.jsonl",
)


# Fact targets that characterise a presentation regardless of which body
# region or specialty it belongs to -- pain, timing, systemic screening, and
# the expected resource count -- as opposed to a detail fact scoped to one
# specific complaint (e.g. abdominal_pain_location, headache_character).
# Used by Corpus._build below to find atoms that are the corpus's equivalent
# of the real ESI algorithm's own decision-point-D "else" branches: "a
# stable patient not meeting level 1/2/3 criteria, expected to need N
# resources, is ESI 3/4/5" -- true for ANY presenting complaint, not just
# the one whose wording the atom happened to be authored under.
#
# Real incident (2026-08-28): data/siu/protocol_atoms.jsonl was authored
# across ~23 independent topic-by-topic passes (see
# data/siu/OR_BRANCH_GAP_AUDIT.md), so this same "else" rule got re-authored
# once per topic instead of once -- 47 atoms across ESI 3/4/5 whose entire
# requirement set is drawn only from these generic fields, each with its own
# topic-narrow retrieval.text ("Mild ABDOMINAL pain requiring only one ED
# resource...", "...UPPER-EXTREMITY pain requiring two or more...",
# "...gradual HEADACHE...", "...ENT symptoms...", 15 topics total). Atom
# retrieval is a semantic-similarity search against that same narrow
# wording, so a real, fully-supported match for an *out-of-topic* complaint
# (confirmed live: "tôi bị đau tay" ["my arm/hand hurts"] -- pain_present,
# pain_severity, resource_count all correctly recorded, `atom_status`
# against the full corpus confirms 0 unmet requirements) was never even
# retrieved into session.seen_atom_ids, because none of these atoms'
# wording resembles "đau tay" closely enough to clear
# MIN_ATOM_RELEVANCE_SCORE. See Corpus.generic_fallback_atom_ids below for
# the fix: these atoms are exempted from the retrieval gate entirely.
GENERIC_FALLBACK_FACT_TARGET_IDS = frozenset({
    "fact_target:pain_present",
    "fact_target:pain_severity",
    "fact_target:resource_count",
    "fact_target:symptom_duration_bucket",
    "fact_target:symptom_trend",
    "fact_target:symptom_onset",
    "fact_target:associated_systemic_symptoms",
    "fact_target:high_risk_situation",
})


# Measured vital signs, plus cyanosis (the one observable sign the ESI 1
# danger-zone criteria use). An ESI 1/2 atom built only from these says
# nothing about the presenting complaint, so whether it is evaluated must not
# depend on its wording resembling the complaint. Real incident (2026-09-16):
# a respiratory-failure case (SpO2 78, RR 42) satisfied three ESI 1 atoms but
# returned ESI 2, because semantic ranking left all three outside the top
# ATOM_RETRIEVAL_LIMIT. See Corpus.vital_sign_decisive_atom_ids below.
VITAL_SIGN_FACT_TARGET_IDS = frozenset({
    "fact_target:heart_rate",
    "fact_target:respiratory_rate",
    "fact_target:spo2",
    "fact_target:temperature",
    "fact_target:systolic_bp",
    "fact_target:cyanosis_present",
})


class CorpusError(RuntimeError):
    """The four source files or their indexes cannot be used together."""


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read one JSON object per non-blank line. Public: also used by scripts/ tooling."""
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise CorpusError(f"Cannot read {path}: {exc}") from exc


def fold(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower())
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", value.replace("đ", "d")).strip()


# Vietnamese function words stripped before token-overlap scoring -- they
# carry no clinical signal and would otherwise inflate overlap between any
# two unrelated phrases (e.g. "tôi bị" appears in nearly every patient turn).
_STOPWORDS = {
    "toi", "ban", "minh", "em", "con", "be", "chau",
    "bi", "co", "la", "va", "voi", "cho", "cua", "dang", "da", "se", "van",
    "o", "tai", "ben", "trong", "ngoai", "the", "nay", "do", "kia",
    "rat", "hoi", "khong", "chua", "moi", "tu", "den", "khi", "luc", "lai",
    "thi", "nhu", "ma", "roi", "duoc", "bang", "vay", "qua", "ra", "vao",
    "thay",
}


def tokenize(value: str) -> set[str]:
    """Fold + split into content words, dropping short/stopword tokens.

    Used for lexical-overlap reranking: a deterministic, cheap signal that a
    query and a candidate concept share real words, independent of whether
    the exact alias phrase appears as a contiguous substring.
    """
    words = fold(value).split(" ")
    return {w for w in words if len(w) >= 2 and w not in _STOPWORDS}


def cosine_scores(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    query_norm = np.linalg.norm(query)
    row_norms = np.linalg.norm(matrix, axis=1)
    if not query_norm or not len(matrix):
        return np.zeros(len(matrix), dtype=np.float32)
    return (matrix @ query) / np.maximum(row_norms * query_norm, 1e-12)


def cosine_top_k(query: np.ndarray, matrix: np.ndarray, limit: int) -> list[int]:
    scores = cosine_scores(query, matrix)
    if not len(scores):
        return []
    return np.argsort(scores)[::-1][:limit].tolist()


def validate_fact(fact_target: dict[str, Any], value: Any) -> Any | None:
    """Coerce ``value`` against a fact target's schema, or return ``None`` if invalid."""
    schema = fact_target["value_schema"]
    value_type = schema.get("type")
    if value_type == "integer":
        try:
            converted: Any = int(value)
        except (ValueError, TypeError):
            return None
    elif value_type == "float":
        try:
            converted = float(value)
        except (ValueError, TypeError):
            return None
    elif value_type == "enum":
        allowed = schema.get("allowed_values") or []
        lookup = {str(item).casefold(): item for item in allowed}
        converted = lookup.get(str(value).casefold())
        if converted is None:
            return None
    else:
        return None
    minimum, maximum = schema.get("minimum"), schema.get("maximum")
    if minimum is not None and converted < minimum or maximum is not None and converted > maximum:
        return None
    return converted


class Corpus:
    """Loads and indexes the four corpus files under ``corpus_dir``/``index_dir``.

    ``from_records`` is the alternate entry point that builds the exact same
    in-memory structures from already-loaded data instead of local files --
    see ``src/simple_agent/pg_corpus.py``, which hydrates from the
    ``simple_agent_clinical_concepts``/``simple_agent_protocol_atoms``/etc.
    Postgres tables. Every lookup/search method below (and every caller in
    ``tools.py``/``decision.py``) is unaffected either way.
    """

    def __init__(self, corpus_dir: Path, index_dir: Path) -> None:
        self.corpus_dir = corpus_dir
        self.index_dir = index_dir
        missing = [name for name in CORPUS_FILES if not (corpus_dir / name).is_file()]
        if missing:
            raise CorpusError(f"Missing primary corpus file(s): {', '.join(missing)}")

        concepts = read_jsonl(corpus_dir / "clinical_concepts.jsonl")
        relations = read_jsonl(corpus_dir / "concept_relations.jsonl")
        protocol_atoms = read_jsonl(corpus_dir / "protocol_atoms.jsonl")
        fact_targets = read_jsonl(corpus_dir / "fact_targets.jsonl")
        concept_embeddings, concept_metadata = self._read_index_files("concept")
        protocol_embeddings, protocol_metadata = self._read_index_files("protocol")
        fact_target_embeddings, fact_target_metadata = self._read_index_files("fact_target_patient")
        self._build(
            concepts, relations, protocol_atoms, fact_targets,
            concept_embeddings, concept_metadata, protocol_embeddings, protocol_metadata,
            fact_target_embeddings, fact_target_metadata,
        )

    @classmethod
    def from_records(
        cls,
        *,
        concepts: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        protocol_atoms: list[dict[str, Any]],
        fact_targets: list[dict[str, Any]],
        concept_embeddings: np.ndarray,
        concept_metadata: list[dict[str, Any]],
        protocol_embeddings: np.ndarray,
        protocol_metadata: list[dict[str, Any]],
        fact_target_embeddings: np.ndarray,
        fact_target_metadata: list[dict[str, Any]],
    ) -> Corpus:
        """Build a Corpus from already-loaded records instead of local files.

        The record shapes must match what ``read_jsonl`` on each of the four
        ``data/siu`` files would produce, and the three embedding pairs must
        match what ``np.load``/``json.loads`` on the three ``indexes_siu``
        index files would produce -- this is a drop-in alternate source, not
        a different corpus shape.
        """
        self = cls.__new__(cls)
        self.corpus_dir = None
        self.index_dir = None
        self._build(
            concepts, relations, protocol_atoms, fact_targets,
            concept_embeddings, concept_metadata, protocol_embeddings, protocol_metadata,
            fact_target_embeddings, fact_target_metadata,
        )
        return self

    def _build(
        self,
        concepts: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        protocol_atoms: list[dict[str, Any]],
        fact_targets: list[dict[str, Any]],
        concept_embeddings: np.ndarray,
        concept_metadata: list[dict[str, Any]],
        protocol_embeddings: np.ndarray,
        protocol_metadata: list[dict[str, Any]],
        fact_target_embeddings: np.ndarray,
        fact_target_metadata: list[dict[str, Any]],
    ) -> None:
        self.concepts = concepts
        self.relations = relations
        self.protocol_atoms = protocol_atoms
        self.fact_targets = fact_targets
        self.concept_by_id = {item["concept_id"]: item for item in self.concepts}
        self.fact_by_id = {item["fact_target_id"]: item for item in self.fact_targets}
        self.atom_by_id = {item["atom_id"]: item for item in self.protocol_atoms}

        # Every fact_target_id referenced as *someone else's* gated_by --
        # derived purely from fact_targets.jsonl itself, no concept_relations
        # curation needed (see agent.py's SimpleTriageAgent._gate_satisfied
        # and tools.py's get_session_state "gate_facts"). Real incident:
        # adding gated_by to a detail fact whose gate has no
        # REQUIRES_ASSESSMENT_OF link to any concept left Phase A with no
        # legitimate way to ever discover the gate's own fact_target_id --
        # a patient volunteering "tôi bị sưng" unprompted couldn't be
        # recorded, so the gate got asked (again) once the system reached
        # the detail fact anyway. Exposing every such id directly, every
        # turn, regardless of which concepts are active, closes that gap
        # without writing a single concept_relations row.
        self.gate_fact_ids: set[str] = set()
        for item in self.fact_targets:
            gated_by = item.get("gated_by")
            if not gated_by:
                continue
            if "any_of" in gated_by:
                self.gate_fact_ids.update(g["fact_target_id"] for g in gated_by["any_of"])
            else:
                self.gate_fact_ids.add(gated_by["fact_target_id"])

        # See GENERIC_FALLBACK_FACT_TARGET_IDS's own comment: atoms whose
        # *entire* requirement set (every branch, every AND-condition) is
        # drawn only from those body-region-agnostic fields are the corpus's
        # generic ESI 3/4/5 "else" rules -- decision.py's rank_question_targets/
        # evaluate_atoms should always get to consider them, independent of
        # whether this turn's retrieval query happens to resemble whichever
        # topic they were originally authored under.
        self.generic_fallback_atom_ids: frozenset[str] = frozenset(
            atom["atom_id"]
            for atom in self.protocol_atoms
            if (fact_ids := {
                requirement["fact_target_id"]
                for branch in atom.get("requirements", [])
                for requirement in (branch if isinstance(branch, list) else [branch])
            })
            and fact_ids <= GENERIC_FALLBACK_FACT_TARGET_IDS
        )
        # Same retrieval-independence for ESI 1/2 danger-zone vital-sign
        # atoms (see VITAL_SIGN_FACT_TARGET_IDS): always evaluated, never
        # allowed to drive what gets asked.
        self.vital_sign_decisive_atom_ids: frozenset[str] = frozenset(
            atom["atom_id"]
            for atom in self.protocol_atoms
            if atom.get("decision_effect", {}).get("impact") == "ASSIGN_ESI"
            and atom.get("decision_effect", {}).get("candidate_esi") in (1, 2)
            and (fact_ids := {
                requirement["fact_target_id"]
                for branch in atom.get("requirements", [])
                for requirement in (branch if isinstance(branch, list) else [branch])
            })
            and fact_ids <= VITAL_SIGN_FACT_TARGET_IDS
        )

        # facts_for_concept and distinguishes_from are both derived from the same
        # relation file so an unrecognised relation_type is simply ignored here,
        # not rejected -- new relation types can be introduced by data alone.
        self.facts_for_concept: dict[str, list[str]] = defaultdict(list)
        self.distinguishes_from: dict[str, set[str]] = defaultdict(set)
        for relation in self.relations:
            rel_type = relation.get("relation_type")
            source = relation.get("source_concept_id")
            target = relation.get("target_id")
            if rel_type == "REQUIRES_ASSESSMENT_OF" and target in self.fact_by_id:
                self.facts_for_concept[source].append(target)
            elif rel_type == "DISTINGUISHES_FROM" and source in self.concept_by_id and target in self.concept_by_id:
                self.distinguishes_from[source].add(target)
                self.distinguishes_from[target].add(source)

        self.aliases = self._build_aliases()
        self.concept_tokens: dict[str, set[str]] = {
            concept["concept_id"]: set().union(
                *(tokenize(label) for label in [concept["canonical_name"], *concept.get("aliases", [])])
            )
            for concept in self.concepts
        }
        self.concept_embeddings, self.concept_metadata = self._validate_index(
            "concept", concept_embeddings, concept_metadata
        )
        self.protocol_embeddings, self.protocol_metadata = self._validate_index(
            "protocol", protocol_embeddings, protocol_metadata
        )
        # Embeds each fact_target's *patient-facing* question (name +
        # lay_terms) via `scripts/audit_fact_target_duplicates.py` -- lets
        # search_fact_targets_for_text (tools.py) find a fact_target
        # directly from raw patient wording, independent of which concepts
        # got recorded this turn. See that script's docstring for why
        # patient-phrased text (not the clinical name+description vector
        # the same script also produces, for the duplicate audit) is the
        # right space to match a patient's own words against.
        self.fact_target_embeddings, self.fact_target_metadata = self._validate_index(
            "fact_target_patient", fact_target_embeddings, fact_target_metadata
        )

    def _build_aliases(self) -> list[tuple[str, str]]:
        aliases: list[tuple[str, str]] = []
        for concept in self.concepts:
            for label in [concept["canonical_name"], *concept.get("aliases", [])]:
                folded = fold(label)
                if folded:
                    aliases.append((folded, concept["concept_id"]))
        return sorted(set(aliases), key=lambda item: len(item[0]), reverse=True)

    def _read_index_files(self, prefix: str) -> tuple[np.ndarray, list[dict[str, Any]]]:
        array_path = self.index_dir / f"{prefix}_embeddings.npy"
        metadata_path = self.index_dir / f"{prefix}_metadata.json"
        try:
            matrix = np.load(array_path)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise CorpusError(f"Cannot load {prefix} index: {exc}") from exc
        return matrix, metadata

    def _validate_index(
        self, prefix: str, matrix: np.ndarray, metadata: list[dict[str, Any]]
    ) -> tuple[np.ndarray, list[dict[str, Any]]]:
        if matrix.ndim != 2 or len(matrix) != len(metadata):
            raise CorpusError(f"{prefix} index rows do not match its metadata")
        id_key, known = {
            "concept": ("concept_id", self.concept_by_id),
            "protocol": ("atom_id", self.atom_by_id),
            "fact_target_patient": ("fact_target_id", self.fact_by_id),
        }[prefix]
        dangling = [item.get(id_key) for item in metadata if item.get(id_key) not in known]
        if dangling:
            raise CorpusError(f"{prefix} index has IDs absent from the primary corpus: {dangling[:3]}")
        return matrix.astype(np.float32), metadata

    def lexical_concepts(self, message: str) -> list[str]:
        folded = f" {fold(message)} "
        found: list[str] = []
        for alias, concept_id in self.aliases:
            if f" {alias} " in folded and concept_id not in found:
                found.append(concept_id)
        return found
