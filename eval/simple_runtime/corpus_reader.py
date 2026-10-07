from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session, select

from src.models.db_models import (
    SimpleAgentClinicalConcept,
    SimpleAgentConceptRelation,
    SimpleAgentFactTarget,
    SimpleAgentFactTargetEmbedding,
    SimpleAgentProtocolAtom,
)
from src.services.db import sync_engine


def _hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CorpusSnapshot:
    concepts: dict[str, dict[str, Any]]
    relations: list[dict[str, str]]
    atoms: dict[str, dict[str, Any]]
    facts: dict[str, dict[str, Any]]
    fact_embedding_dimensions: dict[str, int]
    table_fingerprints: dict[str, str]
    table_counts: dict[str, int]


def load_postgres_corpus() -> CorpusSnapshot:
    """Read exactly the five tables hydrated by SimpleAgentRuntime."""
    with Session(sync_engine) as db:
        concept_rows = db.exec(select(SimpleAgentClinicalConcept)).all()
        relation_rows = db.exec(select(SimpleAgentConceptRelation)).all()
        atom_rows = db.exec(select(SimpleAgentProtocolAtom)).all()
        fact_rows = db.exec(select(SimpleAgentFactTarget)).all()
        embedding_rows = db.exec(select(SimpleAgentFactTargetEmbedding)).all()

    if not all((concept_rows, relation_rows, atom_rows, fact_rows, embedding_rows)):
        raise RuntimeError("One or more required simple_agent corpus tables are empty.")

    concepts = {
        row.concept_id: {
            "concept_id": row.concept_id, "canonical_name": row.canonical_name,
            "aliases": row.aliases or [], "semantic_type": row.semantic_type,
            "embedding": row.embedding,
        }
        for row in concept_rows
    }
    relations = [
        {"source_concept_id": row.source_concept_id, "relation_type": row.relation_type, "target_id": row.target_id}
        for row in relation_rows
    ]
    atoms = {
        row.atom_id: {
            "atom_id": row.atom_id, "authority_scope": row.authority_scope,
            "source_document_id": row.source_document_id, "atom_type": row.atom_type,
            "decision_point": row.decision_point, "requirements": row.requirements or [],
            "decision_effect": row.decision_effect or {}, "retrieval_text": row.retrieval_text,
            "retrieval_embedding_model": row.retrieval_embedding_model, "embedding": row.embedding,
        }
        for row in atom_rows
    }
    facts = {
        row.fact_target_id: {
            "fact_target_id": row.fact_target_id, "name": row.name, "description": row.description,
            "value_schema": row.value_schema or {}, "reporting_style": row.reporting_style,
            "lay_terms": row.lay_terms, "severity_anchors": row.severity_anchors,
            "gated_by": row.gated_by, "requires_sex": row.requires_sex,
        }
        for row in fact_rows
    }
    embedding_dimensions = {row.fact_target_id: len(row.embedding or []) for row in embedding_rows}
    missing = set(facts) - set(embedding_dimensions)
    if missing:
        raise RuntimeError(f"Fact targets without embeddings: {sorted(missing)[:5]}")

    normalized_tables = {
        "simple_agent_clinical_concepts": [{k: v for k, v in item.items() if k != "embedding"} | {"embedding_hash": _hash(item["embedding"])} for item in concepts.values()],
        "simple_agent_concept_relations": relations,
        "simple_agent_protocol_atoms": [{k: v for k, v in item.items() if k != "embedding"} | {"embedding_hash": _hash(item["embedding"])} for item in atoms.values()],
        "simple_agent_fact_targets": list(facts.values()),
        "simple_agent_fact_target_embeddings": [{"fact_target_id": key, "dimension": dimension} for key, dimension in embedding_dimensions.items()],
    }
    return CorpusSnapshot(
        concepts=concepts, relations=relations, atoms=atoms, facts=facts,
        fact_embedding_dimensions=embedding_dimensions,
        table_fingerprints={name: _hash(sorted(rows, key=lambda item: json.dumps(item, sort_keys=True, default=str))) for name, rows in normalized_tables.items()},
        table_counts={name: len(rows) for name, rows in normalized_tables.items()},
    )


def row_fingerprint(value: Any) -> str:
    return _hash(value)

