#!/usr/bin/env python3
"""Draft an ingestion manifest from the AHRQ ESI source files in this repo.

The protocol table is empty, and the reason it is empty matters: the ingestion
script refuses anything without a named clinical reviewer and an approved
retrieval calibration, and nobody has supplied either. This builder does the
half of the job that *can* be done honestly -- parsing the real source
documents, chunking them by decision point, and deriving every field that is
actually derivable from the text -- and stops at the boundary where a human
clinical judgement is required.

It deliberately does **not** fill in:

* ``validation_status`` -- only a clinician may mark a section approved;
* ``reviewed_by`` / ``reviewed_at`` -- a review that did not happen has no
  reviewer and no date;
* ``calibration_profile`` -- retrieval thresholds are an empirical claim about
  precision and recall on this corpus, and nobody has measured them;
* ``source_uri`` beyond the value recorded in the source header.

Writing plausible values into those fields would produce a manifest that passes
ingestion and a corpus that lies about its own provenance, which is a worse
outcome than an empty table. So the draft this produces is *expected to fail*
validation, and the failure names precisely what a clinical owner must supply.

Usage::

    python scripts/build_protocol_manifest.py            # write the draft
    python scripts/build_protocol_manifest.py --check    # report gaps only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE = REPO_ROOT / "data" / "extracted_tables" / "ahrq_esi_v5_cleaned.md"
OUTPUT_FILE = REPO_ROOT / "data" / "protocols" / "ahrq_esi_v5.draft-manifest.json"

PARSER_VERSION = "ahrq-esi-md-parser-1.0.0"
MANIFEST_VERSION = "validated-protocol-manifest-v1"

# Recorded from the source document header, not inferred.
PROTOCOL_CODE = "AHRQ-ESI-V5"
ISSUING_BODY = "Agency for Healthcare Research and Quality"
SOURCE_KEY = "ahrq_esi_v5"
VERSION = "5"

# The placeholder marker. Every occurrence is a field a human must supply.
REQUIRES_HUMAN = "REQUIRES_CLINICAL_OWNER"

# Terms the ingestion script accepts: lowercase, underscore-separated.
_CONTROLLED = re.compile(r"^[a-z0-9]+(?:[_:.\-/][a-z0-9]+)*$")

# Keyword vocabulary. Only terms that literally appear in the source text are
# emitted, so a keyword is always evidence of what the section says.
_KEYWORD_PATTERNS: dict[str, tuple[str, ...]] = {
    "lifesaving_intervention": ("lifesaving intervention", "intubat", "defibrillat"),
    "airway": ("airway", "ventilation", "apneic"),
    "high_risk": ("high-risk", "high risk"),
    "altered_mental_status": ("altered mental status", "lethargic", "disoriented",
                              "unresponsive", "confused"),
    "severe_pain": ("severe pain", "distress"),
    "resource_prediction": ("resource",),
    "vital_signs": ("vital sign",),
    "esi_1": ("esi 1", "esi level 1"),
    "esi_2": ("esi 2", "esi level 2"),
    "esi_3": ("esi 3", "esi level 3"),
    "esi_4": ("esi 4", "esi level 4"),
    "esi_5": ("esi 5", "esi level 5"),
    "triage_algorithm": ("decision point", "algorithm"),
    "pediatric": ("pediatric", "child", "infant"),
}


@dataclass
class ParsedSection:
    """One decision section lifted from the source document."""

    section: str
    title: str
    body: str
    decision_criteria: list[str] = field(default_factory=list)

    @property
    def content_hash(self) -> str:
        normalized = "\n".join(
            line.rstrip() for line in self.body.strip().splitlines()
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _slugify(text: str) -> str:
    folded = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return folded[:60] or "section"


def parse_sections(markdown: str) -> list[ParsedSection]:
    """Split on headings, keeping each decision section whole.

    Chunking follows the document's own structure rather than a token window.
    A decision point that is split in half is not a decision point any more,
    and a retrieval hit on half a rule is worse than no hit at all.
    """
    sections: list[ParsedSection] = []
    current_title = ""
    buffer: list[str] = []

    def flush() -> None:
        if not current_title:
            return
        body = "\n".join(buffer).strip()
        if len(body) < 80:
            # Below the ingestion minimum; a fragment this short carries no
            # usable clinical rule.
            return
        sections.append(
            ParsedSection(
                section=_slugify(current_title),
                title=current_title,
                body=body,
                decision_criteria=_extract_criteria(body),
            )
        )

    for line in markdown.splitlines():
        heading = re.match(r"^(#{2,3})\s+(.*)$", line)
        if heading:
            flush()
            current_title = heading.group(2).strip().strip("*")
            buffer = []
            continue
        if current_title:
            buffer.append(line)
    flush()
    return sections


def _extract_criteria(body: str) -> list[str]:
    """Pull the explicit decision statements out of a section.

    Only lines that already read as a rule are taken. Nothing is paraphrased,
    because a paraphrased clinical criterion is a new clinical claim.
    """
    criteria: list[str] = []
    for raw in body.splitlines():
        line = raw.strip().lstrip("*-• ").strip()
        if not line or line.startswith("|"):
            continue
        if re.search(r"ESI\s*[1-5]|Decision Point|➔|requires|Yes\b|No\b", line):
            cleaned = re.sub(r"\*\*?", "", line).strip()
            if 10 <= len(cleaned) <= 400:
                criteria.append(cleaned)
    # Table rows carry the criteria for the tabular sections.
    if not criteria:
        for raw in body.splitlines():
            if raw.strip().startswith("|") and "---" not in raw:
                cleaned = re.sub(r"\*\*?", "", raw.strip().strip("|")).strip()
                if 10 <= len(cleaned) <= 400:
                    criteria.append(cleaned)
    return criteria[:50]


def derive_keywords(body: str) -> list[str]:
    lowered = body.lower()
    found = [
        term
        for term, needles in _KEYWORD_PATTERNS.items()
        if any(needle in lowered for needle in needles)
    ]
    return [term for term in found if _CONTROLLED.fullmatch(term)] or ["triage_algorithm"]


def derive_scope(body: str) -> list[str]:
    """Scope for the ESI algorithm itself.

    The ESI algorithm is applied to every undifferentiated ED presentation, so
    ``general`` is a statement about the document rather than a guess about a
    symptom cluster. The population scope is likewise taken from the source:
    the handbook covers adult and paediatric triage.
    """
    scope = ["general", "all_populations"]
    if any(term in body.lower() for term in ("pediatric", "child", "infant")):
        scope.append("pediatric")
    return scope


def build_chunk(section: ParsedSection, index: int) -> dict[str, Any]:
    """Assemble one chunk: derived fields filled, human fields left open."""
    return {
        "citation_id": f"{PROTOCOL_CODE}:{section.section}",
        "chunk_id": f"{SOURCE_KEY}-{index:03d}",
        "protocol_code": PROTOCOL_CODE,
        "title": section.title[:500],
        "issuing_body": ISSUING_BODY,
        "source": SOURCE_KEY,
        "version": VERSION,
        "section": section.section,
        "document_type": "validated_protocol",
        "clinical_scope": derive_scope(section.body),
        "keywords": derive_keywords(section.body),
        "page_content": section.body,
        "decision_criteria": section.decision_criteria,
        "parser_version": PARSER_VERSION,
        "content_hash": section.content_hash,
        # --- Everything below requires a human clinical owner. --------------
        "source_uri": REQUIRES_HUMAN,
        "license_reference": REQUIRES_HUMAN,
        "effective_date": REQUIRES_HUMAN,
        "expires_at": None,
        "validation_status": REQUIRES_HUMAN,
        "reviewed_by": REQUIRES_HUMAN,
        "reviewed_at": REQUIRES_HUMAN,
        "calibration_id": REQUIRES_HUMAN,
        "calibration_profile": REQUIRES_HUMAN,
    }


def gap_report(chunks: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Which fields block ingestion, and why each needs a person."""
    reasons = {
        "source_uri": "The canonical URL of the AHRQ ESI v5 handbook edition "
                      "these sections were extracted from. Must be the exact "
                      "edition, not the AHRQ landing page.",
        "license_reference": "The licence or public-domain statement covering "
                             "redistribution of this text.",
        "effective_date": "The publication date of that edition.",
        "validation_status": "Only a clinician may mark a section approved for "
                             "clinical use.",
        "reviewed_by": "The name of the clinician who verified that each chunk "
                       "faithfully reproduces the source rule.",
        "reviewed_at": "The date that review took place.",
        "calibration_id": "Identifier for the retrieval calibration study.",
        "calibration_profile": "Per-channel similarity thresholds, measured on "
                               "a labelled query set, with the name and date of "
                               "whoever approved them. Cannot be guessed: a "
                               "threshold is a claim about precision and recall.",
    }
    blocking: dict[str, list[str]] = {}
    for field_name, reason in reasons.items():
        affected = [
            chunk["citation_id"]
            for chunk in chunks
            if chunk.get(field_name) == REQUIRES_HUMAN
        ]
        if affected:
            blocking[field_name] = affected
    return blocking


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="Report gaps without writing the draft.")
    args = parser.parse_args()

    if not SOURCE_FILE.exists():
        print(f"SOURCE MISSING: {SOURCE_FILE}")
        return 2

    sections = parse_sections(SOURCE_FILE.read_text(encoding="utf-8"))
    chunks = [build_chunk(section, i) for i, section in enumerate(sections, start=1)]

    hashes = [chunk["content_hash"] for chunk in chunks]
    duplicates = {h for h in hashes if hashes.count(h) > 1}

    print("=" * 74)
    print("AHRQ ESI V5 -- DRAFT PROTOCOL MANIFEST")
    print("=" * 74)
    print(f"source file        : {SOURCE_FILE.relative_to(REPO_ROOT)}")
    print(f"sections parsed    : {len(sections)}")
    print(f"duplicate chunks   : {len(duplicates)}")
    print(f"chunks w/ criteria : {sum(1 for c in chunks if c['decision_criteria'])}")
    print(f"chunks w/ keywords : {sum(1 for c in chunks if c['keywords'])}")
    print()

    blocking = gap_report(chunks)
    print("BLOCKING METADATA (must be supplied by a clinical owner):")
    for field_name, affected in blocking.items():
        print(f"  - {field_name:20s} missing on {len(affected)}/{len(chunks)} chunks")
    print()
    print("STATUS: NOT_READY_FOR_INGESTION")
    print("Reason: required clinical-approval and calibration metadata does not")
    print("        exist. It is deliberately not invented here.")

    if args.check:
        return 1

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "clinical_owner": REQUIRES_HUMAN,
        "export_approved_at": REQUIRES_HUMAN,
        "_draft_status": "NOT_READY_FOR_INGESTION",
        "_blocking_fields": {k: len(v) for k, v in blocking.items()},
        "_generated_by": PARSER_VERSION,
        "chunks": chunks,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print()
    print(f"draft written to   : {OUTPUT_FILE.relative_to(REPO_ROOT)}")
    print("This draft is expected to FAIL ingestion validation until the fields")
    print("above are supplied. That failure is the point.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
