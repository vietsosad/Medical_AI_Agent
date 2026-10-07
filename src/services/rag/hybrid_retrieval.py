"""Multi-query hybrid retrieval: dense + lexical, fused, reranked, filtered.

The previous path embedded one long mixed-language string and took the top five
by cosine distance. Three things went wrong with that, and this module fixes
each separately so a benchmark can attribute an improvement to the layer that
produced it:

* **One vector for a whole case.** An average over "everything about this
  patient" is moderately close to a great many cases and specific to none.
  Several short, specific queries are issued instead and their results fused.
* **Dense only.** Cosine similarity has no way to insist on a word. A patient
  with diaphoresis and a patient without it read almost identically to an
  embedding; a keyword channel does not have that problem. PostgreSQL's own
  full-text search is used, so no new dependency and no change to the corpora.
* **Top-K is not relevance.** A retriever asked for five results returns five
  results whatever it found. Fused candidates are reranked and then filtered
  against a floor, so a case with nothing similar in the corpus shows no
  similar cases rather than five unrelated ones.

Nothing here writes to a corpus, changes an embedding, or assigns an ESI level.
Authority remains a property of the row, decided in SQL by ``retrieval_scope``.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text as sql_text
from sqlmodel.ext.asyncio.session import AsyncSession

from src.services.db import async_engine
from src.services.embeddings import EmbeddingError, get_embedding_service

logger = logging.getLogger(__name__)

# Reciprocal rank fusion damping. 60 is the value from the original RRF paper;
# it makes the top few ranks matter without letting rank 1 dominate.
DEFAULT_RRF_K = 60


@dataclass
class ChannelHit:
    """One channel's opinion about one document."""

    channel: str
    rank: int
    score: float


@dataclass
class FusedCandidate:
    """A document seen by one or more channels, with everything they said."""

    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    hits: list[ChannelHit] = field(default_factory=list)
    fusion_score: float = 0.0
    # Post-rerank relevance in [0, 1]. None until a reranker has run.
    relevance: float | None = None
    relevance_reason: str = ""

    @property
    def channels(self) -> list[str]:
        return sorted({hit.channel for hit in self.hits})

    @property
    def best_dense_score(self) -> float | None:
        dense = [hit.score for hit in self.hits if hit.channel.startswith("dense")]
        return max(dense) if dense else None

    @property
    def best_lexical_score(self) -> float | None:
        lexical = [hit.score for hit in self.hits if hit.channel.startswith("lexical")]
        return max(lexical) if lexical else None

    def audit(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "channels": self.channels,
            "fusion_score": round(self.fusion_score, 5),
            "dense": (
                round(self.best_dense_score, 4)
                if self.best_dense_score is not None
                else None
            ),
            "lexical": (
                round(self.best_lexical_score, 5)
                if self.best_lexical_score is not None
                else None
            ),
            "relevance": (
                round(self.relevance, 3) if self.relevance is not None else None
            ),
        }


@dataclass(frozen=True)
class CorpusSpec:
    """Where to search and which columns describe a row."""

    table: str
    id_column: str
    text_column: str
    extra_columns: str = ""
    where: str = "TRUE"
    params: dict[str, Any] = field(default_factory=dict)


async def _dense_search(
    spec: CorpusSpec,
    vector: list[float],
    limit: int,
) -> list[dict[str, Any]]:
    columns = f"{spec.id_column} AS doc_id, {spec.text_column} AS text"
    if spec.extra_columns:
        columns += f", {spec.extra_columns}"
    statement = sql_text(
        f"SELECT {columns}, 1 - (embedding <=> CAST(:qv AS vector)) AS score "
        f"FROM {spec.table} WHERE {spec.where} "
        f"ORDER BY embedding <=> CAST(:qv AS vector) LIMIT :k"
    )
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            statement, {"qv": str(vector), "k": limit, **spec.params}
        )
        return [dict(row) for row in result.mappings().all()]


async def _lexical_search(
    spec: CorpusSpec,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Rank by PostgreSQL full-text relevance over the same retrieval text.

    Uses the built-in ``english`` configuration, computed on the fly. It reads
    the identical column the dense channel embeds, so the two channels are
    opinions about the same text rather than about different data.
    """
    columns = f"{spec.id_column} AS doc_id, {spec.text_column} AS text"
    if spec.extra_columns:
        columns += f", {spec.extra_columns}"
    statement = sql_text(
        f"SELECT {columns}, "
        f"ts_rank_cd(to_tsvector('english', {spec.text_column}), "
        f"plainto_tsquery('english', :q)) AS score "
        f"FROM {spec.table} "
        f"WHERE {spec.where} "
        f"AND to_tsvector('english', {spec.text_column}) "
        f"@@ plainto_tsquery('english', :q) "
        f"ORDER BY score DESC LIMIT :k"
    )
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            statement, {"q": query, "k": limit, **spec.params}
        )
        return [dict(row) for row in result.mappings().all()]


# How much each query is worth in fusion. The overall presentation query
# describes the whole patient and is the most specific thing we can ask for; a
# bare "headache" query matches every headache in the corpus and is useful only
# for breaking ties. Unweighted fusion let the broad queries outvote the
# specific one, which is the same averaging problem the single-vector approach
# had, one level up.
DEFAULT_QUERY_WEIGHTS: dict[str, float] = {
    "overall": 1.0,
    "associated": 0.7,
    "primary": 0.45,
    "decision_point": 0.35,
    "combined": 1.0,
}

# The keyword channel is a check on the dense one, not a peer: it cannot see
# negation or paraphrase, so it is weighted to break ties and to rescue an
# exact term the embedding blurred, rather than to lead.
LEXICAL_CHANNEL_WEIGHT = 0.5


def channel_weight(channel: str, weights: dict[str, float] | None = None) -> float:
    kind, _, query_name = channel.partition(":")
    table = weights or DEFAULT_QUERY_WEIGHTS
    weight = table.get(query_name, 0.5)
    return weight * (LEXICAL_CHANNEL_WEIGHT if kind == "lexical" else 1.0)


def fuse(
    channel_results: dict[str, list[dict[str, Any]]],
    *,
    rrf_k: int = DEFAULT_RRF_K,
    weights: dict[str, float] | None = None,
) -> list[FusedCandidate]:
    """Reciprocal rank fusion over every channel that returned anything.

    Rank-based rather than score-based on purpose: a cosine similarity and a
    ``ts_rank_cd`` are not on the same scale and never will be, so combining
    the raw numbers would silently weight one channel by the accident of its
    units.
    """
    merged: dict[str, FusedCandidate] = {}
    for channel, rows in channel_results.items():
        for rank, row in enumerate(rows, start=1):
            doc_id = str(row["doc_id"])
            candidate = merged.get(doc_id)
            if candidate is None:
                candidate = FusedCandidate(
                    doc_id=doc_id,
                    text=str(row.get("text") or ""),
                    metadata={
                        key: value
                        for key, value in row.items()
                        if key not in {"doc_id", "text", "score"}
                    },
                )
                merged[doc_id] = candidate
            candidate.hits.append(
                ChannelHit(channel=channel, rank=rank, score=float(row.get("score") or 0.0))
            )
            candidate.fusion_score += channel_weight(channel, weights) / (rrf_k + rank)
    return sorted(merged.values(), key=lambda item: item.fusion_score, reverse=True)


async def multi_query_search(
    spec: CorpusSpec,
    queries: list[tuple[str, str]],
    *,
    per_query_limit: int = 10,
    pool_size: int = 30,
    rrf_k: int = DEFAULT_RRF_K,
    use_lexical: bool = True,
    vectors: dict[str, list[float]] | None = None,
    weights: dict[str, float] | None = None,
) -> tuple[list[FusedCandidate], dict[str, Any]]:
    """Run every query on every enabled channel and fuse the results.

    A channel that fails is recorded as degraded and dropped; it never turns
    into an empty result set that would read as "there is no evidence".
    """
    channel_results: dict[str, list[dict[str, Any]]] = {}
    degraded: list[str] = []

    embeddings = dict(vectors or {})
    missing = [name for name, _ in queries if name not in embeddings]
    if missing:
        service = get_embedding_service()
        try:
            computed = await asyncio.gather(
                *(
                    service.embed_query_async(
                        next(text for name, text in queries if name == key)
                    )
                    for key in missing
                )
            )
            embeddings.update(dict(zip(missing, computed, strict=True)))
        except EmbeddingError as exc:
            logger.error("Multi-query embedding failed: %s", exc)
            degraded.append("DENSE_CHANNEL_UNAVAILABLE")
        except Exception as exc:  # noqa: BLE001 - provider boundary
            logger.exception("Unexpected multi-query embedding failure")
            degraded.append(f"DENSE_CHANNEL_ERROR:{type(exc).__name__}")

    tasks: list[tuple[str, Any]] = []
    for name, query in queries:
        vector = embeddings.get(name)
        if vector is not None:
            tasks.append((f"dense:{name}", _dense_search(spec, vector, per_query_limit)))
        if use_lexical:
            tasks.append((f"lexical:{name}", _lexical_search(spec, query, per_query_limit)))

    if not tasks:
        return [], {"degraded_modes": degraded, "channels": {}}

    outcomes = await asyncio.gather(
        *(task for _, task in tasks), return_exceptions=True
    )
    for (channel, _), outcome in zip(tasks, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            logger.warning(
                "Retrieval channel %s failed: %s", channel, type(outcome).__name__
            )
            degraded.append(f"CHANNEL_FAILED:{channel}")
            continue
        if outcome:
            channel_results[channel] = outcome

    if not channel_results:
        return [], {"degraded_modes": degraded, "channels": {}}

    fused = fuse(channel_results, rrf_k=rrf_k, weights=weights)[:pool_size]
    audit = {
        "degraded_modes": degraded,
        "channels": {
            channel: {
                "result_count": len(rows),
                "top_score": max((float(r.get("score") or 0.0) for r in rows), default=None),
            }
            for channel, rows in channel_results.items()
        },
        "pool_size": len(fused),
        "queries": [{"name": name, "text": text} for name, text in queries],
    }
    return fused, audit


# ---------------------------------------------------------------------------
# Reranking
# ---------------------------------------------------------------------------

# Vital-sign keys a case may carry, and how close two readings must be before
# they count as describing a similar physiological state.
_VITAL_TOLERANCE: dict[str, float] = {
    "temp_c": 0.8,
    "hr": 20.0,
    "rr": 5.0,
    "spo2": 3.0,
    "sbp": 25.0,
}


def deterministic_relevance(
    candidate: FusedCandidate,
    *,
    grounded_concepts: tuple[str, ...] | list[str],
    lexical_terms: tuple[str, ...] | list[str] = (),
) -> tuple[float, str]:
    """Score how much this case actually resembles the patient's presentation.

    Cheap, explainable and offline. It compares the *concepts* the two
    presentations share rather than their embeddings, which is precisely the
    thing an averaged vector loses. The score is a similarity, never a clinical
    judgement: it says how useful this case is as context, and says nothing
    about what should happen to the patient.
    """
    wanted = {str(item) for item in grounded_concepts if str(item)}
    if not wanted:
        return 0.0, "no grounded concepts to compare"

    case_concepts = {
        str(item)
        for item in (candidate.metadata.get("symptom_concepts") or [])
        if str(item)
    }
    text = candidate.text.lower()
    # A corpus row without a concept list is not a row without concepts. Fall
    # back to reading them out of the presentation text, so 1,347 unlabelled
    # MIETIC rows are not scored as having nothing in common with anybody.
    matched = {
        concept
        for concept in wanted
        if concept in case_concepts or concept.replace("_", " ") in text
    }
    coverage = len(matched) / len(wanted)

    lexical_hits = sum(
        1 for term in {str(item).lower() for item in lexical_terms} if term in text
    )
    lexical_coverage = lexical_hits / max(1, len(set(lexical_terms)))

    # Agreement between the two retrieval channels is itself evidence: a case
    # both a vector and a keyword search liked is more likely to be relevant
    # than one only a vector liked.
    both_channels = (
        candidate.best_dense_score is not None
        and candidate.best_lexical_score is not None
    )

    score = 0.62 * coverage + 0.23 * lexical_coverage + (0.15 if both_channels else 0.0)
    reason = (
        f"{len(matched)}/{len(wanted)} concepts"
        f"{' + both channels' if both_channels else ''}"
    )
    return max(0.0, min(1.0, score)), reason


_RERANK_PROMPT = """You rate how similar a retrieved emergency-department case \
is to the patient being triaged.

Rate 0-3:
3 = same presentation: the leading complaint and the main associated findings match
2 = related: the leading complaint matches but the picture differs
1 = weak: only incidental overlap
0 = unrelated

You are NOT assigning an acuity, a triage level or a diagnosis. You are only \
judging similarity. Return JSON: {"scores": [{"id": "<case id>", "score": <0-3>}]}
"""


async def llm_rerank(
    presentation: str,
    candidates: list[FusedCandidate],
    *,
    limit: int = 12,
) -> bool:
    """Score the top candidates with a small model. True when it was applied.

    A failure leaves every ``relevance`` untouched so the deterministic score
    stands. The reranker can reorder and can suppress; it can never introduce a
    case the retrieval channels did not return, and it is never shown -- or
    asked for -- an ESI level.
    """
    if not candidates:
        return False
    try:
        from src.config import get_settings
        from src.services.llm_provider import get_resilient_llm

        head = candidates[:limit]
        payload = {
            "patient_presentation": presentation,
            "cases": [
                {"id": item.doc_id, "presentation": item.text[:600]} for item in head
            ],
        }
        import json

        model = get_resilient_llm("small")
        response = await asyncio.wait_for(
            model.ainvoke(
                [
                    {"role": "system", "content": _RERANK_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ]
            ),
            timeout=get_settings().llm_request_timeout_seconds,
        )
        content = getattr(response, "content", "") or ""
        if isinstance(content, list):
            content = " ".join(str(part) for part in content)
        import re

        match = re.search(r"\{.*\}", str(content), flags=re.S)
        if not match:
            return False
        scores = json.loads(match.group(0)).get("scores") or []
    except Exception as exc:  # noqa: BLE001 - optional reranker boundary
        logger.info("LLM reranker unavailable: %s", type(exc).__name__)
        return False

    by_id = {item.doc_id: item for item in candidates}
    applied = False
    for entry in scores:
        if not isinstance(entry, dict):
            continue
        candidate = by_id.get(str(entry.get("id")))
        if candidate is None:
            continue
        try:
            raw = float(entry.get("score"))
        except (TypeError, ValueError):
            continue
        normalized = max(0.0, min(1.0, raw / 3.0))
        # Combined with, not substituted for, the deterministic score. A model
        # that has misread one case cannot then promote it past a concept
        # comparison that says the two presentations share nothing.
        base = candidate.relevance if candidate.relevance is not None else normalized
        candidate.relevance = round(0.5 * base + 0.5 * normalized, 4)
        candidate.relevance_reason = f"{candidate.relevance_reason}; llm {raw:.0f}/3"
        applied = True
    return applied


def apply_relevance_floor(
    candidates: list[FusedCandidate],
    *,
    minimum: float,
    max_shown: int,
) -> list[FusedCandidate]:
    """Keep only candidates worth showing, and never more than the cap.

    Returning fewer -- or none -- is the point. A retriever asked for five
    always finds five, and presenting five unrelated cases as "similar" is
    worse for a clinician than presenting none, because it costs them the time
    to rule each one out.
    """
    kept = [
        item
        for item in candidates
        if item.relevance is not None and item.relevance >= minimum
    ]
    kept.sort(key=lambda item: (item.relevance or 0.0), reverse=True)
    return kept[:max_shown]
