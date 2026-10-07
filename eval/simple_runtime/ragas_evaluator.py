"""RAGAS evaluation for database-grounded Simple Agent observations."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import types
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from .corpus_reader import CorpusSnapshot, load_postgres_corpus
from .schemas import RagasCaseInput, RagasResult


SCORE_FIELDS = (
    "faithfulness_score",
    "context_precision_score",
    "context_recall_score",
    "context_relevance_score",
    "answer_relevancy_score",
)


@dataclass(frozen=True)
class RagasConfig:
    provider: str
    model: str
    temperature: float
    max_tokens: int
    max_retries: int
    timeout_seconds: float
    case_delay_seconds: float
    embedding_provider: str
    embedding_model: str
    embedding_revision: str | None
    embedding_device: str
    embedding_batch_size: int

    @classmethod
    def from_env(cls) -> RagasConfig:
        embedding_model = os.getenv("RAGAS_EMBEDDING_MODEL") or os.getenv(
            "EMBEDDING_MODEL_NAME", "BAAI/bge-m3"
        )
        embedding_revision = os.getenv("RAGAS_EMBEDDING_REVISION") or os.getenv(
            "EMBEDDING_MODEL_REVISION"
        )
        return cls(
            provider=os.getenv("RAGAS_LLM_PROVIDER", "openai"),
            model=os.getenv("RAGAS_LLM_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("RAGAS_LLM_TEMPERATURE", "0")),
            max_tokens=int(os.getenv("RAGAS_LLM_MAX_TOKENS", "2000")),
            max_retries=int(os.getenv("RAGAS_MAX_RETRIES", "5")),
            timeout_seconds=float(os.getenv("RAGAS_TIMEOUT_SECONDS", "90")),
            case_delay_seconds=float(os.getenv("RAGAS_CASE_DELAY_SECONDS", "2")),
            embedding_provider=os.getenv("RAGAS_EMBEDDING_PROVIDER", "huggingface"),
            embedding_model=embedding_model,
            embedding_revision=embedding_revision,
            embedding_device=os.getenv("RAGAS_EMBEDDING_DEVICE", "cpu"),
            embedding_batch_size=int(os.getenv("RAGAS_EMBEDDING_BATCH_SIZE", "8")),
        )

    def validate(self) -> None:
        if self.provider.lower() != "openai":
            raise RuntimeError(
                f"Unsupported RAGAS_LLM_PROVIDER: {self.provider}. Only openai is supported."
            )
        if self.embedding_provider.lower() != "huggingface":
            raise RuntimeError(
                "Unsupported RAGAS_EMBEDDING_PROVIDER: "
                f"{self.embedding_provider}. Only huggingface is supported."
            )
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required for RAGAS evaluation.")


@dataclass
class RagasMetricBundle:
    faithfulness: Any
    context_precision: Any
    context_recall: Any
    context_relevance: Any
    answer_relevancy: Any
    client: Any | None = None


def ragas_version() -> str:
    """Phiên bản RAGAS đang cài, hoặc "not-installed" nếu chưa cài.

    Hàm này được gọi khi dựng metadata của MỌI lượt chạy, kể cả lượt chạy
    ``--skip-ragas`` vốn không đụng tới RAGAS. Trước đây nó ném
    ``PackageNotFoundError`` và làm chết cả tầng đánh giá tất định -- tức là
    không cài được một gói chỉ dùng cho tầng LLM-judge thì cũng mất luôn tầng
    đo không cần LLM. Trả về một chuỗi thay vì ném lỗi giữ cho hai tầng độc
    lập đúng như thiết kế, và metadata vẫn ghi lại sự thật là gói chưa có.
    """
    try:
        return version("ragas")
    except PackageNotFoundError:
        return "not-installed"


def _install_ragas_langchain_compatibility() -> None:
    """Bridge a RAGAS 0.4.3 optional Vertex import removed by LangChain 1.x.

    RAGAS imports the old classes only for type detection.  The evaluator uses
    OpenAI exclusively, so inert placeholders avoid downgrading the product's
    LangChain dependencies without changing RAGAS metric behaviour.
    """

    module_name = "langchain_community.chat_models.vertexai"
    try:
        vertex_spec = importlib.util.find_spec(module_name)
    except (ImportError, ModuleNotFoundError):
        vertex_spec = None
    if vertex_spec is None and module_name not in sys.modules:
        shim = types.ModuleType(module_name)
        shim.ChatVertexAI = type("ChatVertexAI", (), {})
        sys.modules[module_name] = shim

    import langchain_community.llms as community_llms

    if "VertexAI" not in vars(community_llms):
        community_llms.VertexAI = type("VertexAI", (), {})


def _create_metric_bundle(config: RagasConfig) -> RagasMetricBundle:
    config.validate()
    os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")
    _install_ragas_langchain_compatibility()

    from openai import AsyncOpenAI
    from ragas.embeddings import HuggingFaceEmbeddings
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        ContextRelevance,
        Faithfulness,
    )

    client = AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        timeout=config.timeout_seconds,
        max_retries=config.max_retries,
    )
    llm = llm_factory(
        config.model,
        provider=config.provider,
        client=client,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    embedding_kwargs: dict[str, Any] = {}
    if config.embedding_revision:
        embedding_kwargs["revision"] = config.embedding_revision
    embeddings = HuggingFaceEmbeddings(
        model=config.embedding_model,
        device=config.embedding_device,
        normalize_embeddings=True,
        batch_size=config.embedding_batch_size,
        **embedding_kwargs,
    )
    return RagasMetricBundle(
        faithfulness=Faithfulness(llm=llm),
        context_precision=ContextPrecision(llm=llm),
        context_recall=ContextRecall(llm=llm),
        context_relevance=ContextRelevance(llm=llm),
        answer_relevancy=AnswerRelevancy(llm=llm, embeddings=embeddings),
        client=client,
    )


def _atom_text(atom: dict[str, Any]) -> str:
    payload = {
        "atom_id": atom.get("atom_id"),
        "authority_scope": atom.get("authority_scope"),
        "decision_point": atom.get("decision_point"),
        "retrieval_text": atom.get("retrieval_text"),
        "requirements": atom.get("requirements") or [],
        "decision_effect": atom.get("decision_effect") or {},
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _final_decision_snapshot(observation: dict[str, Any]) -> dict[str, Any]:
    snapshots = [
        item
        for item in observation.get("decision_snapshots", [])
        if isinstance(item, dict)
    ]
    for snapshot in reversed(snapshots):
        if snapshot.get("action") == "RETURN_MATCH":
            return snapshot
    return snapshots[-1] if snapshots else {}


def _deduplicated_atom_ids(items: list[Any], *, limit: int | None = None) -> list[str]:
    atom_ids: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        atom_id = str(item.get("atom_id") or item.get("id") or "")
        if not atom_id or atom_id in seen:
            continue
        seen.add(atom_id)
        atom_ids.append(atom_id)
        if limit is not None and len(atom_ids) >= limit:
            break
    return atom_ids


def _incomplete(case_id: str, message: str, *, applicable: bool = True) -> RagasResult:
    return RagasResult(
        case_id=case_id,
        ragas_applicable=applicable,
        metric_errors={} if not applicable else {"input": message},
        metric_reasons={"not_applicable": message} if not applicable else {},
        verdict="incomplete" if applicable else "skipped",
    )


def prepare_ragas_input(
    observation: dict[str, Any], corpus: CorpusSnapshot
) -> tuple[RagasCaseInput | None, RagasResult | None]:
    """Build one RAGAS sample without using backend prediction as reference."""

    case_id = str(observation.get("case_id") or "")
    expected_esi = observation.get("expected_esi")
    if expected_esi is None:
        return None, _incomplete(
            case_id,
            "Case has no expected ESI and is evaluated by deterministic safety metrics only.",
            applicable=False,
        )
    if observation.get("predicted_esi") is None:
        return None, _incomplete(case_id, "Backend returned no final ESI prediction.")
    response_text = str(observation.get("final_response") or "").strip()
    if not response_text:
        return None, _incomplete(case_id, "Backend returned no final response.")

    final_snapshot = _final_decision_snapshot(observation)
    retrieved_ids = _deduplicated_atom_ids(
        final_snapshot.get("retrieved_atoms_this_turn") or [], limit=5
    )
    if not retrieved_ids:
        return None, _incomplete(case_id, "Final decision turn has no retrieved protocol atoms.")
    missing_retrieved = [atom_id for atom_id in retrieved_ids if atom_id not in corpus.atoms]
    if missing_retrieved:
        return None, _incomplete(
            case_id, f"Retrieved atom IDs are absent from PostgreSQL: {missing_retrieved}"
        )
    retrieved_contexts = [_atom_text(corpus.atoms[atom_id]) for atom_id in retrieved_ids]

    citation_ids = _deduplicated_atom_ids(observation.get("citations") or [])
    matched_ids = _deduplicated_atom_ids(observation.get("matched_atoms") or [])
    grounding_ids = citation_ids or matched_ids
    missing_grounding = [atom_id for atom_id in grounding_ids if atom_id not in corpus.atoms]
    if missing_grounding:
        return None, _incomplete(
            case_id, f"Cited or matched atom IDs are absent from PostgreSQL: {missing_grounding}"
        )
    grounding_ids = [
        atom_id
        for atom_id in grounding_ids
        if corpus.atoms[atom_id].get("authority_scope") == "CLINICAL_AUTHORITY"
    ]
    if not grounding_ids:
        return None, _incomplete(
            case_id, "No cited or matched CLINICAL_AUTHORITY atom is available for grounding."
        )
    grounding_contexts = [_atom_text(corpus.atoms[atom_id]) for atom_id in grounding_ids]

    expected_retrieval = observation.get("expected_retrieval") or {}
    primary_atom_id = str(expected_retrieval.get("primary_atom_id") or "")
    primary_atom = corpus.atoms.get(primary_atom_id)
    if not primary_atom:
        return None, _incomplete(
            case_id, f"Expected primary atom is absent from PostgreSQL: {primary_atom_id}"
        )
    if primary_atom.get("authority_scope") != "CLINICAL_AUTHORITY":
        return None, _incomplete(
            case_id, f"Expected primary atom is not CLINICAL_AUTHORITY: {primary_atom_id}"
        )

    presentation = observation.get("presentation") or {}
    profile = observation.get("profile") or {}
    persisted = observation.get("persisted_state") or {}
    user_input = "\n".join(
        (
            "Dựa trên dữ kiện bệnh nhân đã xác nhận, mức ESI nào được evidence/protocol hỗ trợ?",
            f"Tình huống bệnh nhân: {presentation.get('initial_message', '')}",
            "Hồ sơ tóm tắt: " + json.dumps(profile, ensure_ascii=False, sort_keys=True, default=str),
            "Facts đã xác nhận: "
            + json.dumps(persisted.get("facts") or {}, ensure_ascii=False, sort_keys=True, default=str),
        )
    )
    response_payload = {
        "predicted_esi": observation["predicted_esi"],
        "final_action": observation.get("final_action") or observation.get("terminal_action"),
        "matched_atoms": observation.get("matched_atoms") or [],
        "citations": observation.get("citations") or [],
        "resource_count": (persisted.get("facts") or {}).get("fact_target:resource_count"),
    }
    response = (
        "Structured decision evidence: "
        + json.dumps(response_payload, ensure_ascii=False, sort_keys=True, default=str)
    )
    expected_decision = observation.get("expected_decision") or {}
    expected_state = observation.get("expected_state") or {}
    reference = "\n".join(
        (
            f"Expected ESI: {expected_esi}",
            f"Expected primary atom: {primary_atom_id}",
            f"Expected decision points: {expected_retrieval.get('decision_points') or []}",
            f"Expected resource count: {expected_decision.get('resource_count')}",
            "Expected facts: "
            + json.dumps(expected_state.get("facts") or {}, ensure_ascii=False, sort_keys=True, default=str),
            "Authoritative protocol atom: " + _atom_text(primary_atom),
        )
    )
    return (
        RagasCaseInput(
            case_id=case_id,
            user_input=user_input,
            response=response,
            reference=reference,
            retrieved_contexts=retrieved_contexts,
            grounding_contexts=grounding_contexts,
        ),
        None,
    )


async def _score_case(sample: RagasCaseInput, metrics: RagasMetricBundle) -> RagasResult:
    calls = {
        "faithfulness_score": lambda: metrics.faithfulness.ascore(
            user_input=sample.user_input,
            response=sample.response,
            retrieved_contexts=sample.grounding_contexts,
        ),
        "context_precision_score": lambda: metrics.context_precision.ascore(
            user_input=sample.user_input,
            reference=sample.reference,
            retrieved_contexts=sample.retrieved_contexts,
        ),
        "context_recall_score": lambda: metrics.context_recall.ascore(
            user_input=sample.user_input,
            retrieved_contexts=sample.retrieved_contexts,
            reference=sample.reference,
        ),
        "context_relevance_score": lambda: metrics.context_relevance.ascore(
            user_input=sample.user_input,
            retrieved_contexts=sample.retrieved_contexts,
        ),
        "answer_relevancy_score": lambda: metrics.answer_relevancy.ascore(
            user_input=sample.user_input,
            response=sample.response,
        ),
    }
    scores: dict[str, float | None] = {field: None for field in SCORE_FIELDS}
    reasons: dict[str, str] = {}
    errors: dict[str, str] = {}
    for field, call in calls.items():
        try:
            metric_result = await call()
            score = float(metric_result.value)
            if not 0 <= score <= 1:
                raise ValueError(f"score outside [0, 1]: {score}")
            scores[field] = score
            if metric_result.reason:
                reasons[field] = str(metric_result.reason)
        except Exception as exc:
            errors[field] = str(exc)

    completed_scores = [value for value in scores.values() if value is not None]
    ragas_score = (
        round(sum(completed_scores) / len(completed_scores), 4)
        if len(completed_scores) == len(SCORE_FIELDS)
        else None
    )
    if errors or ragas_score is None:
        case_verdict = "incomplete"
    elif ragas_score >= 0.80:
        case_verdict = "pass"
    elif ragas_score >= 0.65:
        case_verdict = "warning"
    else:
        case_verdict = "fail"
    return RagasResult(
        case_id=sample.case_id,
        **scores,
        ragas_score=ragas_score,
        metric_reasons=reasons,
        metric_errors=errors,
        verdict=case_verdict,
    )


async def evaluate_observations(
    observations: list[dict[str, Any]],
    config: RagasConfig | None = None,
    *,
    corpus: CorpusSnapshot | None = None,
    metric_bundle: RagasMetricBundle | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    config = config or RagasConfig.from_env()
    corpus = corpus or load_postgres_corpus()
    samples: dict[str, RagasCaseInput] = {}
    results: dict[str, RagasResult] = {}
    for observation in observations:
        sample, preliminary = prepare_ragas_input(observation, corpus)
        case_id = str(observation.get("case_id") or "")
        if preliminary is not None:
            results[case_id] = preliminary
        elif sample is not None:
            samples[case_id] = sample

    created_bundle = metric_bundle is None
    if samples and metric_bundle is None:
        try:
            metric_bundle = _create_metric_bundle(config)
        except Exception as exc:
            for case_id in samples:
                results[case_id] = _incomplete(
                    case_id, f"RAGAS initialization failed: {exc}"
                )

    try:
        evaluated_count = 0
        if metric_bundle is not None:
            for observation in observations:
                case_id = str(observation.get("case_id") or "")
                sample = samples.get(case_id)
                if sample is None:
                    continue
                if evaluated_count and config.case_delay_seconds > 0:
                    await asyncio.sleep(config.case_delay_seconds)
                results[case_id] = await _score_case(sample, metric_bundle)
                evaluated_count += 1
    finally:
        if created_bundle and metric_bundle is not None and metric_bundle.client is not None:
            await metric_bundle.client.close()

    ordered = [results[str(item.get("case_id") or "")].model_dump() for item in observations]
    errors = [
        f"{row['case_id']}: "
        + "; ".join(f"{key}={value}" for key, value in row["metric_errors"].items())
        for row in ordered
        if row.get("ragas_applicable") and row.get("metric_errors")
    ]
    return ordered, errors


def run_ragas(
    observations: list[dict[str, Any]],
    config: RagasConfig | None = None,
    *,
    corpus: CorpusSnapshot | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    return asyncio.run(evaluate_observations(observations, config, corpus=corpus))
