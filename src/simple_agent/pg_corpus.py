"""Hydrate a ``Corpus`` from Postgres instead of local data/siu files.

The only consumer of this module today is
``src/agents/simple_agent_runtime/runtime.py`` -- the pilot HTTP routes'
runtime now sources its corpus entirely from the
``simple_agent_clinical_concepts``/``simple_agent_concept_relations``/
``simple_agent_protocol_atoms``/``simple_agent_fact_targets`` tables
(populated by ``scripts/migrate_simple_agent_corpus_to_pg.py``), not from
``data/siu``/``data/indexes_siu`` at all.

The test suite reads the same rows offline from the versioned SQL bundle via
``sql_bundle_corpus.py``, which shares ``corpus_from_rows`` below; only
``scripts/run_agent.py`` still uses the file-based ``Corpus(corpus_dir,
index_dir)`` constructor. ``corpus.py`` itself has no idea Postgres exists
(see ``Corpus.from_records``).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from sqlmodel import Session, select

from src.models.db_models import (
    SimpleAgentClinicalConcept,
    SimpleAgentConceptRelation,
    SimpleAgentFactTarget,
    SimpleAgentFactTargetEmbedding,
    SimpleAgentProtocolAtom,
)
from src.simple_agent.corpus import Corpus, CorpusError


def _concept_record(row: SimpleAgentClinicalConcept) -> dict[str, Any]:
    return {
        "concept_id": row.concept_id,
        "canonical_name": row.canonical_name,
        "aliases": row.aliases,
        "semantic_type": row.semantic_type,
    }


def _relation_record(row: SimpleAgentConceptRelation) -> dict[str, Any]:
    return {
        "source_concept_id": row.source_concept_id,
        "relation_type": row.relation_type,
        "target_id": row.target_id,
    }


def _atom_record(row: SimpleAgentProtocolAtom) -> dict[str, Any]:
    return {
        "atom_id": row.atom_id,
        "authority_scope": row.authority_scope,
        "source_document_id": row.source_document_id,
        "atom_type": row.atom_type,
        "decision_point": row.decision_point,
        "requirements": row.requirements,
        "decision_effect": row.decision_effect,
        "retrieval": {"text": row.retrieval_text, "embedding_model": row.retrieval_embedding_model},
    }


def _fact_target_record(row: SimpleAgentFactTarget) -> dict[str, Any]:
    return {
        "fact_target_id": row.fact_target_id,
        "name": row.name,
        "description": row.description,
        "value_schema": row.value_schema,
        "reporting_style": row.reporting_style,
        "lay_terms": row.lay_terms,
        "severity_anchors": row.severity_anchors,
        "gated_by": row.gated_by,
        "requires_sex": row.requires_sex,
    }


def load_corpus_from_postgres(engine: Any) -> Corpus:
    """Build a ``Corpus`` by querying the four simple_agent_* corpus tables.

    ``engine`` is a synchronous SQLAlchemy engine (``src.services.db.sync_engine``
    in production) -- this runs inside ``SimpleAgentRuntime``, which is itself
    always called through ``asyncio.to_thread`` (see runtime.py), so a
    blocking query here never touches the event loop.
    """
    with Session(engine) as db:
        concept_rows = db.exec(select(SimpleAgentClinicalConcept)).all()
        relation_rows = db.exec(select(SimpleAgentConceptRelation)).all()
        atom_rows = db.exec(select(SimpleAgentProtocolAtom)).all()
        fact_rows = db.exec(select(SimpleAgentFactTarget)).all()
        fact_embedding_rows = db.exec(select(SimpleAgentFactTargetEmbedding)).all()

    return corpus_from_rows(concept_rows, relation_rows, atom_rows, fact_rows, fact_embedding_rows)


def corpus_from_rows(
    concept_rows: Sequence[Any],
    relation_rows: Sequence[Any],
    atom_rows: Sequence[Any],
    fact_rows: Sequence[Any],
    fact_embedding_rows: Sequence[Any],
) -> Corpus:
    """Validate and map rows of the five corpus tables into a ``Corpus``.

    Rows only need the table's columns as attributes, so the SQL-bundle loader
    (``sql_bundle_corpus.py``) goes through this exact mapping and the same
    emptiness/embedding checks as production instead of a parallel copy.
    """
    if not concept_rows or not atom_rows or not fact_rows:
        raise CorpusError(
            "simple_agent corpus tables are empty -- run "
            "scripts/migrate_simple_agent_corpus_to_pg.py before enabling SIMPLE_AGENT_ENABLED."
        )

    concept_embeddings = np.array([row.embedding for row in concept_rows], dtype=np.float32)
    concept_metadata = [{"concept_id": row.concept_id} for row in concept_rows]
    protocol_embeddings = np.array([row.embedding for row in atom_rows], dtype=np.float32)
    protocol_metadata = [{"atom_id": row.atom_id} for row in atom_rows]

    # A separate table (see SimpleAgentFactTargetEmbedding's own docstring),
    # so its query result isn't guaranteed to come back in fact_rows' order --
    # look each one up by fact_target_id instead of zipping positionally.
    embedding_by_fact_id = {row.fact_target_id: row.embedding for row in fact_embedding_rows}
    missing_embeddings = [row.fact_target_id for row in fact_rows if row.fact_target_id not in embedding_by_fact_id]
    if missing_embeddings:
        raise CorpusError(
            "simple_agent_fact_target_embeddings is missing rows for "
            f"{missing_embeddings[:3]} (and possibly more) -- run "
            "scripts/migrate_simple_agent_corpus_to_pg.py after scripts/audit_fact_target_duplicates.py."
        )
    fact_target_embeddings = np.array(
        [embedding_by_fact_id[row.fact_target_id] for row in fact_rows], dtype=np.float32
    )
    fact_target_metadata = [{"fact_target_id": row.fact_target_id} for row in fact_rows]

    return Corpus.from_records(
        concepts=[_concept_record(row) for row in concept_rows],
        relations=[_relation_record(row) for row in relation_rows],
        protocol_atoms=[_atom_record(row) for row in atom_rows],
        fact_targets=[_fact_target_record(row) for row in fact_rows],
        concept_embeddings=concept_embeddings,
        concept_metadata=concept_metadata,
        protocol_embeddings=protocol_embeddings,
        protocol_metadata=protocol_metadata,
        fact_target_embeddings=fact_target_embeddings,
        fact_target_metadata=fact_target_metadata,
    )
