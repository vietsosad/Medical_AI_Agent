"""Measure whether a Vietnamese query reaches the same evidence as its English twin.

The corpora are English; patients write Vietnamese. Using each ontology concept's
own English terms as the reference query, we can ask a concrete question without
hand-labelling anything: does the Vietnamese phrasing retrieve the same documents
the English phrasing does?

Three query channels are compared per concept:
    vi_only     the Vietnamese clinical terms, embedded as-is (today's behaviour)
    vi_slang    real patient wording from the ontology
    vi_plus_en  Vietnamese plus the ontology-translated English (the proposal)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import psycopg2  # noqa: E402

from src.services.embeddings import get_embedding_service  # noqa: E402
from src.services.rag.query_translation import translate_query  # noqa: E402

ONTOLOGY = Path("data/guard_rules/ontology_vi_en.json")


def top_ids(cur, table: str, id_col: str, vector: list[float], k: int, where: str) -> list[str]:
    cur.execute(
        f"SELECT {id_col} FROM {table} WHERE {where} "
        f"ORDER BY embedding <=> %s::vector LIMIT %s",
        (vector, k),
    )
    return [row[0] for row in cur.fetchall()]


def overlap(a: list[str], b: list[str]) -> float:
    return len(set(a) & set(b)) / len(a) if a else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--table", default="esi_knowledge_documents")
    parser.add_argument("--id-col", default="document_id")
    parser.add_argument("--where", default="retrieval_scope='CLINICAL_AUTHORITY'")
    args = parser.parse_args()

    data = json.loads(ONTOLOGY.read_text(encoding="utf-8"))
    service = get_embedding_service()
    conn = psycopg2.connect(
        host="localhost", port=5433, dbname="triage_db",
        user="triage_user", password="triage_password",
    )
    conn.set_session(readonly=True)

    totals = {"vi_only": 0.0, "vi_slang": 0.0, "vi_plus_en": 0.0, "slang_plus_en": 0.0}
    covered = 0
    rows = []

    with conn.cursor() as cur:
        for key, entry in data.items():
            en_terms = entry.get("standard_en_terms", [])
            vi_terms = entry.get("standard_vi_terms", [])
            slang = entry.get("patient_slang_dialect", [])
            if not (en_terms and vi_terms):
                continue
            covered += 1

            reference = top_ids(cur, args.table, args.id_col,
                                service.embed_query(", ".join(en_terms[:5])), args.k, args.where)

            vi_query = ", ".join(vi_terms[:5])
            slang_query = ", ".join(slang[:3])
            vi_en = translate_query(vi_query)
            slang_en = translate_query(slang_query)

            channels = {
                "vi_only": vi_query,
                "vi_slang": slang_query or vi_query,
                "vi_plus_en": f"{vi_query}. {vi_en.query_en}" if vi_en.query_en else vi_query,
                "slang_plus_en": (
                    f"{slang_query}. {slang_en.query_en}" if slang_en.query_en else slang_query or vi_query
                ),
            }
            scores = {}
            for name, query in channels.items():
                ids = top_ids(cur, args.table, args.id_col,
                              service.embed_query(query), args.k, args.where)
                scores[name] = overlap(reference, ids)
                totals[name] += scores[name]
            rows.append((key, scores))

    conn.close()
    print(f"concepts evaluated: {covered}   overlap@{args.k} vs English reference\n")
    print(f"{'channel':<16}{'mean overlap':>14}")
    for name in ("vi_only", "vi_slang", "vi_plus_en", "slang_plus_en"):
        print(f"{name:<16}{totals[name]/covered:>13.1%}")

    print("\nworst concepts on vi_only:")
    for key, scores in sorted(rows, key=lambda r: r[1]["vi_only"])[:6]:
        print(f"  {key:<44} vi={scores['vi_only']:.0%} -> vi+en={scores['vi_plus_en']:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
