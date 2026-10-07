#!/usr/bin/env python3
"""Audit `data/siu/fact_targets.jsonl` for semantically duplicate fields.

Root-cause tool for the "asked twice under two different fact_target ids"
class of bug (see the burn/skin incident this was built for): rather than
waiting for a live conversation to expose one collision at a time, this
embeds every fact_target's CLINICAL definition and its PATIENT-facing
question *separately* and combines them into one weighted score, over the
full corpus in one pass.

Two vectors per fact_target, not one blended string, per explicit
instruction:

- ``clinical_text`` = name + description -- what is actually being
  measured, worded the way a clinician would.
- ``patient_text``  = name + lay_terms -- how it is actually asked, which
  is what lets two differently-authored fields that ask the same question
  in different words surface as similar.

``lay_terms`` tends to be long and full of enumerated answer options, so it
is not weighted equally with ``description``:

    semantic_score = 0.70 * cosine(clinical_a, clinical_b)
                    + 0.30 * cosine(patient_a, patient_b)

Uses the exact same embedding call simple_agent's own runtime retrieval uses
(`text-embedding-3-small`, see `SimpleTriageAgent._embed` in
`src/simple_agent/agent.py`) -- not the newer, differently-dimensioned
`src/services/embeddings.py` service -- so the two `.npy` indexes this
script writes are directly reusable as a *runtime* retrieval index later
(e.g. a `search_fact_targets_for_text` tool), not just a one-off audit
artifact.

Usage:
    python3 scripts/audit_fact_target_duplicates.py [--threshold 0.55] [--top 150]

Writes (filenames match `Corpus._read_index_files(prefix)`'s `{prefix}_embeddings.npy` /
`{prefix}_metadata.json` convention, so `fact_target_patient` is a drop-in third index
alongside `concept`/`protocol` -- see `Corpus.__init__`):
    data/indexes_siu/fact_target_clinical_embeddings.npy
    data/indexes_siu/fact_target_clinical_metadata.json
    data/indexes_siu/fact_target_patient_embeddings.npy
    data/indexes_siu/fact_target_patient_metadata.json
    data/siu/FACT_TARGET_DUPLICATE_AUDIT.md
    data/siu/FACT_TARGET_DUPLICATE_AUDIT.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "data" / "siu"
INDEX_DIR = REPO_ROOT / "data" / "indexes_siu"
EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100
CLINICAL_WEIGHT = 0.70
PATIENT_WEIGHT = 0.30


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def clinical_text(fact: dict[str, Any]) -> str:
    return f"Tên thuộc tính: {fact['name']}\nĐịnh nghĩa: {fact['description']}"


def patient_text(fact: dict[str, Any]) -> str:
    return f"Tên thuộc tính: {fact['name']}\nCách hỏi bệnh nhân: {fact['lay_terms']}"


def embed_all(client: Any, texts: list[str]) -> np.ndarray:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        vectors.extend(item.embedding for item in response.data)
        print(f"  embedded {min(start + BATCH_SIZE, len(texts))}/{len(texts)}", file=sys.stderr)
    return np.asarray(vectors, dtype=np.float32)


def cosine_matrix(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = matrix / norms
    return normalized @ normalized.T


def schema_summary(fact: dict[str, Any]) -> str:
    schema = fact.get("value_schema") or {}
    kind = schema.get("type")
    if kind == "enum":
        values = schema.get("allowed_values") or []
        return f"enum[{len(values)}]: {', '.join(values)}"
    if kind in ("integer", "number"):
        lo, hi = schema.get("minimum"), schema.get("maximum")
        return f"{kind} [{lo}, {hi}]"
    return json.dumps(schema, ensure_ascii=False)


def allowed_values_summary(fact: dict[str, Any]) -> str:
    """Plain '|'-joined list of allowed values for a CSV cell -- the enum
    values themselves, not schema_summary's prose ('enum[n]: ...'), so a
    reviewer can compare two fields' actual value sets side by side without
    parsing text.
    """
    schema = fact.get("value_schema") or {}
    kind = schema.get("type")
    if kind == "enum":
        return "|".join(schema.get("allowed_values") or [])
    if kind in ("integer", "number"):
        lo, hi = schema.get("minimum"), schema.get("maximum")
        return f"{kind}[{lo}..{hi}]"
    return ""


def gate_summary(fact: dict[str, Any]) -> str:
    gated_by = fact.get("gated_by")
    if not gated_by:
        return "(không gate)"
    if "any_of" in gated_by:
        return " HOẶC ".join(
            f"{g['fact_target_id']}=={g['expected_value']}" for g in gated_by["any_of"]
        )
    return f"{gated_by['fact_target_id']}=={gated_by['expected_value']}"


def build_usage_index(
    relations: list[dict[str, Any]], atoms: list[dict[str, Any]]
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    concepts_by_fact: dict[str, list[str]] = defaultdict(list)
    for rel in relations:
        if rel.get("relation_type") == "REQUIRES_ASSESSMENT_OF":
            concepts_by_fact[rel["target_id"]].append(rel["source_concept_id"])

    atoms_by_fact: dict[str, list[str]] = defaultdict(list)
    for atom in atoms:
        fact_ids: set[str] = set()
        for branch in atom.get("requirements", []):
            items = branch if isinstance(branch, list) else [branch]
            fact_ids.update(item["fact_target_id"] for item in items)
        for fid in fact_ids:
            atoms_by_fact[fid].append(atom["atom_id"])

    return concepts_by_fact, atoms_by_fact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--top", type=int, default=150)
    parser.add_argument(
        "--skip-embedding",
        action="store_true",
        help="Reuse the .npy/.json index files already on disk instead of calling the API again.",
    )
    args = parser.parse_args()

    fact_targets = read_jsonl(CORPUS_DIR / "fact_targets.jsonl")
    relations = read_jsonl(CORPUS_DIR / "concept_relations.jsonl")
    atoms = read_jsonl(CORPUS_DIR / "protocol_atoms.jsonl")
    fact_by_id = {f["fact_target_id"]: f for f in fact_targets}
    ids = [f["fact_target_id"] for f in fact_targets]
    print(f"Loaded {len(fact_targets)} fact_targets", file=sys.stderr)

    clinical_path = INDEX_DIR / "fact_target_clinical_embeddings.npy"
    clinical_metadata_path = INDEX_DIR / "fact_target_clinical_metadata.json"
    patient_path = INDEX_DIR / "fact_target_patient_embeddings.npy"
    patient_metadata_path = INDEX_DIR / "fact_target_patient_metadata.json"

    # Metadata is just `{"fact_target_id": ...}` per row -- matches the
    # minimal shape Corpus._validate_index checks (id present and known),
    # same convention pg_corpus.py uses for concept/protocol metadata.
    row_metadata = [{"fact_target_id": fid} for fid in ids]

    if args.skip_embedding and clinical_path.exists() and patient_path.exists():
        print("Reusing existing embedding index files.", file=sys.stderr)
        clinical_matrix = np.load(clinical_path)
        patient_matrix = np.load(patient_path)
    else:
        from openai import OpenAI

        client = OpenAI()
        print("Embedding clinical_text (name + description)...", file=sys.stderr)
        clinical_matrix = embed_all(client, [clinical_text(f) for f in fact_targets])
        print("Embedding patient_text (name + lay_terms)...", file=sys.stderr)
        patient_matrix = embed_all(client, [patient_text(f) for f in fact_targets])
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        np.save(clinical_path, clinical_matrix)
        np.save(patient_path, patient_matrix)

    clinical_metadata_path.write_text(json.dumps(row_metadata, ensure_ascii=False, indent=1), encoding="utf-8")
    patient_metadata_path.write_text(json.dumps(row_metadata, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"Wrote {clinical_path}, {clinical_metadata_path}, {patient_path}, {patient_metadata_path}",
        file=sys.stderr,
    )

    clinical_sim = cosine_matrix(clinical_matrix)
    patient_sim = cosine_matrix(patient_matrix)
    combined = CLINICAL_WEIGHT * clinical_sim + PATIENT_WEIGHT * patient_sim

    concepts_by_fact, atoms_by_fact = build_usage_index(relations, atoms)

    n = len(ids)
    pairs: list[tuple[float, float, float, str, str]] = []
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((combined[i, j], clinical_sim[i, j], patient_sim[i, j], ids[i], ids[j]))
    pairs.sort(key=lambda row: row[0], reverse=True)

    # Histogram over the whole corpus so the threshold isn't a guess.
    buckets = [0.9, 0.8, 0.7, 0.6, 0.55, 0.5, 0.4]
    print("\n=== Toàn cảnh phân bố semantic_score trên", len(pairs), "cặp ===")
    for b in buckets:
        count = sum(1 for row in pairs if row[0] >= b)
        print(f"  >= {b:.2f}: {count} cặp")

    shortlisted = [row for row in pairs if row[0] >= args.threshold][: args.top]
    print(f"\n=== {len(shortlisted)} cặp >= {args.threshold} (giới hạn top {args.top}) ===\n")

    report_lines = [
        "# Fact-target duplicate audit (embedding-based)",
        "",
        f"Sinh tự động bởi `scripts/audit_fact_target_duplicates.py`. Model `{EMBEDDING_MODEL}`, ",
        f"`semantic_score = {CLINICAL_WEIGHT}*cosine(clinical) + {PATIENT_WEIGHT}*cosine(patient)`, ",
        "`clinical` = tên+description, `patient` = tên+lay_terms. Ngưỡng hiển thị: "
        f"`{args.threshold}` (top {args.top}).",
        "",
        "Đây là danh sách ỨNG VIÊN để rà tay, không phải kết luận: score cao chỉ nói hai field "
        "*hỏi giống nhau*, không nói được liệu gộp có làm mất độ phân giải mà atom nào đó cần "
        "hay không (xem ví dụ burn_extent_estimate/skin_finding_distribution đã gặp).",
        "",
        "## Phân bố điểm",
        "",
    ]
    for b in buckets:
        count = sum(1 for row in pairs if row[0] >= b)
        report_lines.append(f"- >= {b:.2f}: {count} cặp / {len(pairs)} tổng")
    report_lines += ["", "## Danh sách ứng viên", ""]

    for rank, (score, csim, psim, a_id, b_id) in enumerate(shortlisted, start=1):
        fa, fb = fact_by_id[a_id], fact_by_id[b_id]
        report_lines += [
            f"### {rank}. `{a_id}` <-> `{b_id}` — score {score:.3f} (clinical {csim:.3f} / patient {psim:.3f})",
            "",
            f"- **{a_id}** — {fa['name']}",
            f"  - schema: {schema_summary(fa)}",
            f"  - gate: {gate_summary(fa)}",
            f"  - concept nào yêu cầu: {', '.join(concepts_by_fact.get(a_id, [])) or '(không, chỉ qua atom)'}",
            f"  - atom nào dùng ({len(atoms_by_fact.get(a_id, []))}): "
            f"{', '.join(atoms_by_fact.get(a_id, [])[:6])}"
            + (" ..." if len(atoms_by_fact.get(a_id, [])) > 6 else ""),
            f"- **{b_id}** — {fb['name']}",
            f"  - schema: {schema_summary(fb)}",
            f"  - gate: {gate_summary(fb)}",
            f"  - concept nào yêu cầu: {', '.join(concepts_by_fact.get(b_id, [])) or '(không, chỉ qua atom)'}",
            f"  - atom nào dùng ({len(atoms_by_fact.get(b_id, []))}): "
            f"{', '.join(atoms_by_fact.get(b_id, [])[:6])}"
            + (" ..." if len(atoms_by_fact.get(b_id, [])) > 6 else ""),
            "",
        ]
        print(f"{rank:3d}. {score:.3f}  {a_id}  <->  {b_id}")

    report_path = CORPUS_DIR / "FACT_TARGET_DUPLICATE_AUDIT.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nĐã ghi báo cáo đầy đủ vào {report_path}", file=sys.stderr)

    # One row per candidate pair, flat columns -- easier to sort/filter in a
    # spreadsheet than the Markdown report above, per explicit request: id,
    # description, and allowed values for both sides of each pair, plus the
    # 3 scores that produced the ranking.
    csv_path = CORPUS_DIR / "FACT_TARGET_DUPLICATE_AUDIT.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "rank", "semantic_score", "clinical_score", "patient_score",
            "fact_id_a", "name_a", "description_a", "lay_terms_a", "allowed_values_a", "gate_a",
            "fact_id_b", "name_b", "description_b", "lay_terms_b", "allowed_values_b", "gate_b",
        ])
        for rank, (score, csim, psim, a_id, b_id) in enumerate(shortlisted, start=1):
            fa, fb = fact_by_id[a_id], fact_by_id[b_id]
            writer.writerow([
                rank, f"{score:.4f}", f"{csim:.4f}", f"{psim:.4f}",
                a_id, fa["name"], fa["description"], fa["lay_terms"], allowed_values_summary(fa), gate_summary(fa),
                b_id, fb["name"], fb["description"], fb["lay_terms"], allowed_values_summary(fb), gate_summary(fb),
            ])
    print(f"Đã ghi CSV vào {csv_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
