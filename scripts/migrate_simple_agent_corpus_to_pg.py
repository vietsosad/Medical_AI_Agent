"""One-time migration: load data/siu + data/indexes_siu into Postgres.

Pure data transfer, no OpenAI calls -- the embeddings already exist in
data/indexes_siu/*.npy, this script only moves them (plus the four JSONL
files) into simple_agent_clinical_concepts / simple_agent_concept_relations /
simple_agent_protocol_atoms / simple_agent_fact_targets. Local files are left
untouched: they remain the input to this script and to
tests/test_simple_agent.py (which runs offline, without Postgres).

Idempotent: re-running upserts by natural key (concept_id/atom_id/
fact_target_id, or the (source_concept_id, relation_type, target_id) triple
for relations) rather than duplicating rows, so this is safe to re-run after
data/siu content changes and data/indexes_siu is rebuilt.

Usage:
    python scripts/migrate_simple_agent_corpus_to_pg.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from src.models.db_models import (  # noqa: E402
    SimpleAgentClinicalConcept,
    SimpleAgentConceptRelation,
    SimpleAgentFactTarget,
    SimpleAgentFactTargetEmbedding,
    SimpleAgentProtocolAtom,
)
from src.services.db import sync_engine  # noqa: E402
from src.simple_agent.corpus import CORPUS_FILES, CorpusError, read_jsonl  # noqa: E402

CORPUS_DIR = REPO_ROOT / "data/siu"
INDEX_DIR = REPO_ROOT / "data/indexes_siu"


def _load_index(prefix: str) -> tuple[np.ndarray, list[dict]]:
    matrix = np.load(INDEX_DIR / f"{prefix}_embeddings.npy")
    metadata = json.loads((INDEX_DIR / f"{prefix}_metadata.json").read_text(encoding="utf-8"))
    if matrix.ndim != 2 or len(matrix) != len(metadata):
        raise CorpusError(f"{prefix} index rows do not match its metadata")
    return matrix.astype(np.float32), metadata


def migrate(*, dry_run: bool = False) -> None:
    missing = [name for name in CORPUS_FILES if not (CORPUS_DIR / name).is_file()]
    if missing:
        raise CorpusError(f"Missing primary corpus file(s): {', '.join(missing)}")

    concepts = read_jsonl(CORPUS_DIR / "clinical_concepts.jsonl")
    relations = read_jsonl(CORPUS_DIR / "concept_relations.jsonl")
    protocol_atoms = read_jsonl(CORPUS_DIR / "protocol_atoms.jsonl")
    fact_targets = read_jsonl(CORPUS_DIR / "fact_targets.jsonl")
    concept_matrix, concept_metadata = _load_index("concept")
    protocol_matrix, protocol_metadata = _load_index("protocol")
    # See SimpleAgentFactTargetEmbedding's docstring for why fact_targets get
    # their own table instead of a column on simple_agent_fact_targets --
    # "patient" (name + lay_terms), not "clinical" (name + description, the
    # other vector scripts/audit_fact_target_duplicates.py produces, used
    # only for the offline duplicate audit): this is what a raw patient
    # utterance gets embedded against at runtime, see decision.py's
    # retrieve_fact_targets_scored.
    fact_target_matrix, fact_target_metadata = _load_index("fact_target_patient")

    concept_embedding_by_id = {m["concept_id"]: concept_matrix[i] for i, m in enumerate(concept_metadata)}
    atom_embedding_by_id = {m["atom_id"]: protocol_matrix[i] for i, m in enumerate(protocol_metadata)}
    fact_target_embedding_by_id = {
        m["fact_target_id"]: fact_target_matrix[i] for i, m in enumerate(fact_target_metadata)
    }

    missing_concept_embeddings = [c["concept_id"] for c in concepts if c["concept_id"] not in concept_embedding_by_id]
    missing_atom_embeddings = [a["atom_id"] for a in protocol_atoms if a["atom_id"] not in atom_embedding_by_id]
    missing_fact_embeddings = [
        f["fact_target_id"] for f in fact_targets if f["fact_target_id"] not in fact_target_embedding_by_id
    ]
    if missing_concept_embeddings or missing_atom_embeddings or missing_fact_embeddings:
        raise CorpusError(
            "Corpus/index mismatch -- rebuild data/indexes_siu before migrating (fact_target index is built by "
            "scripts/audit_fact_target_duplicates.py, not this script). "
            f"concepts missing embeddings: {missing_concept_embeddings[:3]}, "
            f"atoms missing embeddings: {missing_atom_embeddings[:3]}, "
            f"fact_targets missing embeddings: {missing_fact_embeddings[:3]}"
        )

    print(
        f"Loaded {len(concepts)} concepts, {len(relations)} relations, "
        f"{len(protocol_atoms)} protocol atoms, {len(fact_targets)} fact targets "
        f"from {CORPUS_DIR}, embeddings from {INDEX_DIR}."
    )
    if dry_run:
        print("--dry-run: not writing anything.")
        return

    with Session(sync_engine) as db:
        existing_concepts = {
            row.concept_id: row for row in db.exec(select(SimpleAgentClinicalConcept)).all()
        }
        for concept in concepts:
            row = existing_concepts.get(concept["concept_id"]) or SimpleAgentClinicalConcept(
                concept_id=concept["concept_id"]
            )
            row.canonical_name = concept["canonical_name"]
            row.aliases = concept.get("aliases", [])
            row.semantic_type = concept.get("semantic_type", "")
            row.embedding = concept_embedding_by_id[concept["concept_id"]].tolist()
            db.add(row)
        db.commit()
        print(f"Upserted {len(concepts)} rows into simple_agent_clinical_concepts.")

        existing_atoms = {row.atom_id: row for row in db.exec(select(SimpleAgentProtocolAtom)).all()}
        for atom in protocol_atoms:
            row = existing_atoms.get(atom["atom_id"]) or SimpleAgentProtocolAtom(atom_id=atom["atom_id"])
            row.authority_scope = atom.get("authority_scope", "")
            row.source_document_id = atom.get("source_document_id", "")
            row.atom_type = atom.get("atom_type", "")
            row.decision_point = atom.get("decision_point")
            row.requirements = atom.get("requirements", [])
            row.decision_effect = atom.get("decision_effect", {})
            retrieval = atom.get("retrieval") or {}
            row.retrieval_text = retrieval.get("text", "")
            row.retrieval_embedding_model = retrieval.get("embedding_model", "text-embedding-3-small")
            row.embedding = atom_embedding_by_id[atom["atom_id"]].tolist()
            db.add(row)
        db.commit()
        print(f"Upserted {len(protocol_atoms)} rows into simple_agent_protocol_atoms.")

        existing_facts = {row.fact_target_id: row for row in db.exec(select(SimpleAgentFactTarget)).all()}
        for fact in fact_targets:
            row = existing_facts.get(fact["fact_target_id"]) or SimpleAgentFactTarget(
                fact_target_id=fact["fact_target_id"]
            )
            row.name = fact.get("name", "")
            row.description = fact.get("description", "")
            row.value_schema = fact.get("value_schema", {})
            row.reporting_style = fact.get("reporting_style", "")
            row.lay_terms = fact.get("lay_terms", "")
            row.severity_anchors = fact.get("severity_anchors")
            row.gated_by = fact.get("gated_by")
            row.requires_sex = fact.get("requires_sex")
            db.add(row)
        db.commit()
        print(f"Upserted {len(fact_targets)} rows into simple_agent_fact_targets.")

        existing_fact_embeddings = {
            row.fact_target_id: row for row in db.exec(select(SimpleAgentFactTargetEmbedding)).all()
        }
        for fact in fact_targets:
            fid = fact["fact_target_id"]
            row = existing_fact_embeddings.get(fid) or SimpleAgentFactTargetEmbedding(fact_target_id=fid)
            row.embedding = fact_target_embedding_by_id[fid].tolist()
            db.add(row)
        db.commit()
        print(f"Upserted {len(fact_targets)} rows into simple_agent_fact_target_embeddings.")

        existing_relations = {
            (row.source_concept_id, row.relation_type, row.target_id): row
            for row in db.exec(select(SimpleAgentConceptRelation)).all()
        }
        new_relation_count = 0
        for relation in relations:
            key = (relation.get("source_concept_id"), relation.get("relation_type"), relation.get("target_id"))
            if key in existing_relations:
                continue
            db.add(
                SimpleAgentConceptRelation(
                    source_concept_id=key[0], relation_type=key[1], target_id=key[2],
                )
            )
            new_relation_count += 1
        db.commit()
        print(
            f"Inserted {new_relation_count} new rows into simple_agent_concept_relations "
            f"({len(relations) - new_relation_count} already present)."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Load and validate only, write nothing.")
    args = parser.parse_args()
    try:
        migrate(dry_run=args.dry_run)
    except CorpusError as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
