"""Hydrate a ``Corpus`` from the versioned SQL migration bundle, offline.

``database/migrations/20260901_simple_agent_corpus_data.sql`` is the pg_dump
that seeds the five ``simple_agent_*`` corpus tables in every environment, so
it is the corpus production actually runs on. Reading it directly gives the
test suite and offline scripts that same corpus without a live Postgres and
without the non-versioned ``data/siu``/``data/indexes_siu`` files -- whose
absence used to skip every test of ``decision.py`` on any machine but one.

Rows are parsed from the dump's ``COPY ... FROM stdin`` blocks and handed to
``pg_corpus.corpus_from_rows``, the same mapping and validation the
Postgres path uses. No network, no LLM, no embedding calls.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from src.simple_agent.corpus import REPO_ROOT, Corpus, CorpusError
from src.simple_agent.pg_corpus import corpus_from_rows

DEFAULT_SQL_BUNDLE = REPO_ROOT / "database/migrations/20260901_simple_agent_corpus_data.sql"

_COPY_HEADER = re.compile(r"^COPY public\.(\w+) \(([^)]*)\) FROM stdin;$")
_COPY_ESCAPE = re.compile(r"\\(x[0-9a-fA-F]{1,2}|[0-7]{1,3}|.)")
_COPY_ESCAPE_CHARS = {"b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}


def _json(value: str | None) -> Any:
    return None if value is None else json.loads(value)


def _vector(value: str | None) -> np.ndarray:
    if not value:
        raise CorpusError("corpus bundle row has no embedding")
    return np.array(value.strip("[]").split(","), dtype=np.float32)


# Per table: the column decoders that are not plain text. Every column the
# dump carries is kept, so a row has the same attributes as its SQLModel.
_DECODERS: dict[str, dict[str, Callable[[str | None], Any]]] = {
    "simple_agent_clinical_concepts": {"aliases": _json, "embedding": _vector},
    "simple_agent_concept_relations": {},
    "simple_agent_protocol_atoms": {
        "requirements": _json,
        "decision_effect": _json,
        "embedding": _vector,
    },
    "simple_agent_fact_targets": {
        "value_schema": _json,
        "severity_anchors": _json,
        "gated_by": _json,
    },
    "simple_agent_fact_target_embeddings": {"embedding": _vector},
}


def _unescape(field: str) -> str | None:
    """Decode one field of PostgreSQL's COPY text format."""
    if field == r"\N":
        return None

    def replace(match: re.Match[str]) -> str:
        code = match.group(1)
        if code[0] == "x" and len(code) > 1:
            return chr(int(code[1:], 16))
        if code[0] in "01234567":
            return chr(int(code, 8))
        return _COPY_ESCAPE_CHARS.get(code, code)

    return _COPY_ESCAPE.sub(replace, field)


def read_copy_blocks(path: Path) -> dict[str, list[dict[str, str | None]]]:
    """Return every ``COPY public.<table>`` block in a pg_dump file as raw rows."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CorpusError(f"Cannot read corpus bundle {path}: {exc}") from exc

    tables: dict[str, list[dict[str, str | None]]] = {}
    table: str | None = None
    columns: list[str] = []
    for number, line in enumerate(lines, start=1):
        if table is None:
            header = _COPY_HEADER.match(line)
            if header:
                table = header.group(1)
                columns = [name.strip() for name in header.group(2).split(",")]
                tables[table] = []
            continue
        if line == r"\.":
            table = None
            continue
        fields = line.split("\t")
        if len(fields) != len(columns):
            raise CorpusError(
                f"{path.name}:{number}: {table} row has {len(fields)} fields, expected {len(columns)}"
            )
        tables[table].append({name: _unescape(value) for name, value in zip(columns, fields)})
    if table is not None:
        raise CorpusError(f"{path.name}: COPY block for {table} is not terminated")
    return tables


def _rows(tables: dict[str, list[dict[str, str | None]]], table: str) -> list[SimpleNamespace]:
    if table not in tables:
        raise CorpusError(f"corpus bundle has no COPY block for {table}")
    decoders = _DECODERS[table]
    return [
        SimpleNamespace(**{
            name: decoders[name](value) if name in decoders else value
            for name, value in raw.items()
        })
        for raw in tables[table]
    ]


_TABLE_ORDER = (
    "simple_agent_clinical_concepts",
    "simple_agent_concept_relations",
    "simple_agent_protocol_atoms",
    "simple_agent_fact_targets",
    "simple_agent_fact_target_embeddings",
)


@lru_cache(maxsize=2)
def _bundle_rows(path: Path) -> tuple[list[SimpleNamespace], ...]:
    tables = read_copy_blocks(path)
    return tuple(_rows(tables, table) for table in _TABLE_ORDER)


def _private_copy(row: SimpleNamespace) -> SimpleNamespace:
    # corpus_from_rows already copies every embedding into a fresh matrix, so
    # only the JSON columns need a deep copy to keep corpora independent.
    return SimpleNamespace(**{
        name: value if name == "embedding" else copy.deepcopy(value)
        for name, value in vars(row).items()
    })


def load_corpus_from_sql_bundle(path: Path = DEFAULT_SQL_BUNDLE) -> Corpus:
    """Build the production corpus from the SQL bundle.

    The dump is parsed once per path; every call still returns an independent
    ``Corpus``, so a caller that mutates one (tests do) cannot leak into the next.
    """
    return corpus_from_rows(*(
        [_private_copy(row) for row in rows] for rows in _bundle_rows(Path(path).resolve())
    ))
