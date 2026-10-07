"""Regression coverage for adaptive, authority-gated evidence decisions.

These tests deliberately replace embeddings, retrieval, and structured LLM calls
with in-process fakes.  A retrieval outage must never be confused with a
clinical finding, and MIETIC case labels must never become ESI authority.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest
from pydantic import ValidationError

from src.agents.canonical_state import CanonicalPatientState
from src.agents.deepagent_runtime.tools import (
    TurnContext,
    reasoning_phase,
    retrieve_evidence_phase,
)
from src.agents.nodes.answer_validator import validate_answer_alignment
from src.agents.nodes.evidence_gate import (
    build_retrieval_failure_response,
    retrieve_evidence_node,
)
from src.agents.nodes.fact_extraction import extract_facts
from src.agents.nodes.intake_analyzer import analyze_patient_intake
from src.agents.nodes.triage_reasoner import (
    TriageEvaluation,
    _target_is_unresolved,
    run_triage_reasoner_node,
)
from src.models.patient_schemas import PatientChatMessageDTO, RagCitationDTO
from src.config import RAG_REFINEMENT_ATTEMPTS_HARD_MAX, Settings
from src.services.rag.outcomes import (
    RetrievalOutcome,
    RetrievalStatus,
    RetrievedItem,
)
from src.services.rag.knowledge_retriever import KnowledgeRetriever


class _FakeEmbeddingService:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.vector = [0.25, 0.5, 0.75]

    async def embed_query_async(self, query: str) -> list[float]:
        self.queries.append(query)
        return self.vector


class _FakeRetriever:
    def __init__(
        self,
        authority: RetrievalOutcome,
        case_support: RetrievalOutcome,
    ) -> None:
        self.authority = authority
        self.case_support = case_support
        self.authority_calls: list[dict[str, Any]] = []
        self.case_calls: list[dict[str, Any]] = []

    async def search_esi_authority(
        self,
        query: str,
        **kwargs: Any,
    ) -> RetrievalOutcome:
        self.authority_calls.append({"query": query, **kwargs})
        return self.authority

    async def search_mietic_cases(
        self,
        query: str,
        **kwargs: Any,
    ) -> RetrievalOutcome:
        self.case_calls.append({"query": query, **kwargs})
        return self.case_support

    # The multi-query hybrid surface. Implemented alongside the single-query
    # one so these tests exercise whichever the pipeline actually calls.
    async def search_esi_authority_hybrid(
        self,
        queries: list[tuple[str, str]],
        **kwargs: Any,
    ) -> tuple[RetrievalOutcome, dict[str, Any]]:
        self.authority_calls.append(
            {
                "query": "; ".join(text for _, text in queries),
                "queries": queries,
                **kwargs,
            }
        )
        return self.authority, {"channels": {}}

    async def search_mietic_cases_hybrid(
        self,
        queries: list[tuple[str, str]],
        **kwargs: Any,
    ) -> tuple[RetrievalOutcome, dict[str, Any]]:
        self.case_calls.append(
            {
                "query": "; ".join(text for _, text in queries),
                "queries": queries,
                **kwargs,
            }
        )
        return self.case_support, {"channels": {}}


class _ScriptedStructuredLLM:
    def __init__(self, results: Iterable[TriageEvaluation]) -> None:
        self._results = list(results)
        self.prompts: list[str] = []
        self.schemas: list[type[Any]] = []

    def with_structured_output(
        self,
        schema: type[Any],
    ) -> _ScriptedStructuredLLM:
        self.schemas.append(schema)
        return self

    async def ainvoke(self, prompt: str) -> TriageEvaluation:
        self.prompts.append(prompt)
        if not self._results:
            raise AssertionError("Structured reasoner was invoked too many times")
        return self._results.pop(0)


def _authority_outcome() -> RetrievalOutcome:
    return RetrievalOutcome(
        status=RetrievalStatus.SUCCESS,
        channels=("dense",),
        items=(
            RetrievedItem(
                doc_id="ESI-AUTH-001",
                text=(
                    "ESI criterion AUTH-CRIT-1 requires the current presentation "
                    "and decision-critical observations to be assessed together."
                ),
                score=0.92,
                source_table="esi_knowledge_documents",
                retrieval_scope="CLINICAL_AUTHORITY",
                authority_status="AUTHORITATIVE",
                retrieval_channel="dense",
                metadata={
                    "atom_type": "decision_rule",
                    "pass5_version": "pass5-v1",
                    "retrieval_text_sha256": "hash-authority-001",
                    "payload": {
                        "title": "Emergency Severity Index decision rule",
                        "heading_path": "Decision Point B",
                        "criterion_ids": ["AUTH-CRIT-1"],
                        "decision_points": ["B"],
                        "retrieval_facets": ["severe-pain"],
                        "issuing_body": "AHRQ",
                        "source_occurrences": [
                            {"source_uri": "https://example.test/esi"}
                        ],
                    },
                },
            ),
        ),
    )


def _mietic_outcome(*, conflicting: bool) -> RetrievalOutcome:
    if not conflicting:
        return RetrievalOutcome(status=RetrievalStatus.NO_RESULTS, channels=("dense",))
    return RetrievalOutcome(
        status=RetrievalStatus.SUCCESS,
        channels=("dense",),
        items=(
            RetrievedItem(
                doc_id="MIETIC-CONFLICT-SECRET",
                # Genuinely similar to the fixture patient, because a case that
                # resembles nobody is now withheld before it can reach anything
                # -- and the invariant under test is that a *usable* case with a
                # conflicting label still cannot leak its label to the reasoner.
                text=(
                    "Patient: 41 years, female. Presentation: abdominal pain "
                    "since this morning with nausea. MIETIC secret conflict "
                    "says a different ESI label."
                ),
                score=0.99,
                source_table="mietic_cases",
                retrieval_scope="CASE_SUPPORT",
                authority_status="NOT_PROTOCOL",
                retrieval_channel="dense",
                metadata={
                    "validated_esi_level": 1,
                    "label_status": "CONFLICTING",
                    "symptom_concepts": ["abdominal_pain", "nausea"],
                },
            ),
        ),
    )


def _canonical_for(message: str) -> dict[str, Any]:
    """Canonical state as the live pipeline would have built it.

    Retrieval queries are now derived from canonical facts, so a fixture
    without canonical state describes a patient the retriever knows nothing
    about -- and correctly declines to search for.
    """
    from src.agents.canonical_state import CanonicalPatientState
    from src.agents.nodes.fact_extraction import apply_message_to_state

    state = CanonicalPatientState()
    apply_message_to_state(state, message, turn_id="fixture-t1")
    return state.to_dict()


def _confirmed_retrieval_state() -> dict[str, Any]:
    return {
        "canonical_state": _canonical_for("Tôi đau bụng từ sáng nay"),
        "query": "Tôi đau bụng từ sáng nay",
        "intent": "TRIAGE_NEW_SYMPTOM",
        "patient_confirmed_intake": True,
        "retrieval_query_vi": "đau bụng khởi phát sáng nay",
        "retrieval_query_en": "abdominal pain since this morning",
        "retrieval_sparse_terms": ["đau bụng", "abdominal pain"],
        "retrieval_degraded_modes": [],
        "clinical_blueprint": {
            "chief_complaint": ["đau bụng"],
            "onset_time": "sáng nay",
            "severity_score": None,
            "associated_symptoms": [],
            "vital_signs": {},
        },
        "clinical_memory_confirmation_status": "CONFIRMED",
        "clinical_memory": {},
        "verified_profile_context": {},
        "unresolved_contradictions": [],
        "missing_critical_fields": [],
        "decision_relevant_unknowns": [],
        "relevant_uncertainties": [],
        "readiness_outcome": "READY",
        "next_step": "retrieve_evidence",
    }


def _grounded_evidence_state() -> dict[str, Any]:
    return {
        **_confirmed_retrieval_state(),
        "retrieved_evidence": [
            {
                "citation_id": "ESI-AUTH-001",
                "protocol_code": "ESI-AUTH-001",
                "section": "Decision Point B",
                "protocol_content": "Authority text for AUTH-CRIT-1.",
                "protocol_criteria": ["AUTH-CRIT-1"],
                "decision_points": ["B"],
                "retrieval_facets": ["severe-pain"],
            }
        ],
        "turn_rag_citations": [
            {
                "id": "ESI-AUTH-001",
                "title": "Emergency Severity Index decision rule",
                "protocolId": "ESI-AUTH-001",
                "excerpt": "Authority text for AUTH-CRIT-1.",
                "sourceType": "validated_protocol",
                "retrievalChannels": [
                    {"channel": "en_dense", "rank": 1, "score": 0.92}
                ],
            }
        ],
        "available_protocol_criteria": ["AUTH-CRIT-1"],
        "matched_protocol_criteria": [],
        "evidence_status": "RETRIEVED",
        "evidence_authority_status": "AUTHORIZED",
        "evidence_sufficiency_outcome": "PENDING_EVALUATION",
        "decision_status": "READY_FOR_REASONING",
        "workflow_phase": "RETRIEVAL",
        "next_step": "triage_reasoner",
    }


def _authority_artifacts(
    doc_id: str,
    criterion: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence = {
        "citation_id": doc_id,
        "protocol_code": doc_id,
        "section": "Decision Point B",
        "protocol_content": f"Authority text for {criterion}.",
        "protocol_criteria": [criterion],
        "decision_points": ["B"],
        "retrieval_facets": ["severe-pain"],
        "provenance": {"retrieval_text_sha256": f"hash-{doc_id}"},
    }
    citation = {
        "id": doc_id,
        "title": f"Authority {doc_id}",
        "protocolId": doc_id,
        "excerpt": f"Authority text for {criterion}.",
        "sourceType": "validated_protocol",
        "retrievalChannels": [
            {"channel": "en_dense", "rank": 1, "score": 0.91}
        ],
    }
    return evidence, citation


def _need_more_evidence(
    *,
    query: str,
    citation_id: str,
    criterion: str,
) -> TriageEvaluation:
    return TriageEvaluation(
        decision="NEED_MORE_EVIDENCE",
        reasoning=(
            "Bằng chứng hiện tại chưa phủ trực tiếp nhánh quyết định cần thiết "
            "cho tình huống đã khai."
        ),
        matched_criteria=[criterion],
        citation_ids=[citation_id],
        refined_query=query,
        decision_point="B",
        retrieval_facets=["severe-pain"],
    )


def _propose() -> TriageEvaluation:
    return TriageEvaluation(
        decision="PROPOSE",
        esi_level=3,
        reasoning=(
            "Các dấu hiệu đã khai cần được nhân viên y tế đánh giá theo mức ưu "
            "tiên đề xuất này."
        ),
        matched_criteria=["AUTH-CRIT-1"],
        citation_ids=["ESI-AUTH-001"],
    )


@pytest.mark.asyncio
async def test_retrieval_phase_preserves_technical_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_update(_state: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def query_update(_state: dict[str, Any]) -> dict[str, Any]:
        return {"retrieval_query_vi": "đau bụng"}

    async def failed_retrieval(_state: dict[str, Any]) -> dict[str, Any]:
        return build_retrieval_failure_response("database connection refused")

    async def must_not_rewrite(_state: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("technical failure was rewritten as insufficiency")

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.enrich_profile_context_node",
        no_update,
    )
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.build_bilingual_query_node",
        query_update,
    )
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.retrieve_evidence_node",
        failed_retrieval,
    )
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.respond_to_insufficient_evidence_node",
        must_not_rewrite,
    )

    context = TurnContext({"next_step": "retrieve_evidence", "current_esi_level": 4})
    result = await retrieve_evidence_phase(context)

    assert result["decision_status"] == "RETRIEVAL_FAILURE"
    assert context.state["evidence_status"] == "RETRIEVAL_FAILURE"
    assert context.state["workflow_phase"] == "RETRIEVAL"
    assert context.state["current_esi_level"] is None
    assert context.state["sbar_report"] is None
    assert context.state["turn_rag_citations"] == []
    assert "lỗi kỹ thuật" in context.state["response"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failing_node",
    ["enrich_profile_context_node", "build_bilingual_query_node"],
)
async def test_retrieval_setup_exception_fails_as_technical_outage(
    monkeypatch: pytest.MonkeyPatch,
    failing_node: str,
) -> None:
    async def no_update(_state: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def explode(_state: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("private provider detail")

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.enrich_profile_context_node",
        no_update,
    )
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.build_bilingual_query_node",
        no_update,
    )
    monkeypatch.setattr(
        f"src.agents.deepagent_runtime.tools.{failing_node}",
        explode,
    )
    context = TurnContext(
        {
            "next_step": "retrieve_evidence",
            "decision_status": "READY_FOR_REASONING",
            "current_esi_level": 2,
            "sbar_report": {"situation": "stale"},
        }
    )

    result = await retrieve_evidence_phase(context)

    assert result["decision_status"] == "RETRIEVAL_FAILURE"
    assert context.state["current_esi_level"] is None
    assert context.state["sbar_report"] is None
    assert context.state["turn_rag_citations"] == []
    assert "private provider detail" not in context.state["response"]


@pytest.mark.asyncio
async def test_authority_retrieved_with_no_mietic_match_reaches_structured_reasoner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embedding = _FakeEmbeddingService()
    retriever = _FakeRetriever(_authority_outcome(), _mietic_outcome(conflicting=False))
    monkeypatch.setattr(
        "src.services.rag.hybrid_retrieval.get_embedding_service",
        lambda: embedding,
    )
    monkeypatch.setattr(
        "src.agents.nodes.evidence_gate.get_knowledge_retriever",
        lambda: retriever,
    )
    monkeypatch.setattr(
        "src.agents.nodes.evidence_gate.translate_query",
        lambda _query: None,
    )

    state = _confirmed_retrieval_state()
    retrieval = await retrieve_evidence_node(state)

    assert retrieval["evidence_status"] == "RETRIEVED"
    assert retrieval["evidence_sufficiency_outcome"] == "PENDING_EVALUATION"
    assert retrieval["next_step"] == "triage_reasoner"
    assert retrieval["case_support_evidence"] == []
    # Embedding now happens inside the retrieval layer, so with a fake
    # retriever installed the observable fact is what it was asked to find.
    assert retriever.authority_calls
    assert retriever.authority_calls[-1]["queries"]
    # Both corpora were searched from the same canonical presentation. They no
    # longer share a single vector: each corpus gets the query set that suits
    # it, and the authority set deliberately keeps the narrow symptom query the
    # case-support set drops.
    assert retriever.authority_calls[0]["queries"]
    assert retriever.case_calls[0]["queries"]

    llm = _ScriptedStructuredLLM([_propose()])
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        lambda **_kwargs: llm,
    )
    reasoning = await run_triage_reasoner_node({**state, **retrieval})

    assert len(llm.prompts) == 1
    assert "ESI-AUTH-001" in llm.prompts[0]
    assert "AUTH-CRIT-1" in llm.prompts[0]
    assert "decision-critical observations" in llm.prompts[0]
    assert reasoning["decision_status"] == "PROPOSED"
    assert reasoning["current_esi_level"] == 3
    assert reasoning["evidence_status"] == "SUFFICIENT"
    assert reasoning["evidence_sufficiency_outcome"] == "READY_FOR_REASONING"
    assert [item["id"] for item in reasoning["turn_rag_citations"]] == [
        "ESI-AUTH-001"
    ]


@pytest.mark.asyncio
async def test_db_shaped_authority_row_flows_through_real_retriever_to_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the production row adapter, evidence gate, and reasoner prompt.

    Only the database I/O itself is replaced.  ``KnowledgeRetriever`` still
    converts the DB-shaped row into a typed outcome, and the active evidence
    node still performs its provenance/citation adaptation before reasoning.
    """
    embedding = _FakeEmbeddingService()
    retriever = KnowledgeRetriever(top_k=5, min_similarity=0.25)
    vector_searches: list[dict[str, Any]] = []

    async def db_shaped_rows(**kwargs: Any) -> list[dict[str, Any]]:
        vector_searches.append(kwargs)
        if kwargs["table"] == "mietic_cases":
            return []
        return [
            {
                "doc_id": "DB-ESI-AUTH-777",
                "text": (
                    "DB_AUTHORITY_PROMPT_MARKER: assess the current severe "
                    "presentation under criterion DB-CRIT-777."
                ),
                "score": 0.94,
                "atom_type": "decision_rule",
                "pass5_version": "pass5-db-fixture",
                "retrieval_text_sha256": "hash-db-authority-777",
                "payload": {
                    "title": "DB-shaped ESI authority",
                    "heading_path": "Decision Point B",
                    "criterion_ids": ["DB-CRIT-777"],
                    "decision_points": ["B"],
                    "retrieval_facets": ["severe-presentation"],
                    "issuing_body": "AHRQ",
                    "source_uri": "https://example.test/db-esi-777",
                },
            }
        ]

    async def hybrid_dense(spec: Any, vector: list[float], limit: int) -> list[dict[str, Any]]:
        return await db_shaped_rows(table=spec.table, top_k=limit, vector=vector)

    async def hybrid_lexical(spec: Any, query: str, limit: int) -> list[dict[str, Any]]:
        return await db_shaped_rows(table=spec.table, top_k=limit, query=query)

    monkeypatch.setattr(retriever, "_vector_search", db_shaped_rows)
    monkeypatch.setattr(
        "src.services.rag.hybrid_retrieval._dense_search", hybrid_dense
    )
    monkeypatch.setattr(
        "src.services.rag.hybrid_retrieval._lexical_search", hybrid_lexical
    )
    monkeypatch.setattr(
        "src.services.rag.hybrid_retrieval.get_embedding_service",
        lambda: embedding,
    )
    monkeypatch.setattr(
        "src.agents.nodes.evidence_gate.get_knowledge_retriever",
        lambda: retriever,
    )
    monkeypatch.setattr(
        "src.agents.nodes.evidence_gate.translate_query",
        lambda _query: None,
    )

    state = _confirmed_retrieval_state()
    retrieval = await retrieve_evidence_node(state)
    llm = _ScriptedStructuredLLM(
        [
            TriageEvaluation(
                decision="PROPOSE",
                esi_level=3,
                reasoning=(
                    "Các dữ kiện hiện tại cần được nhân viên y tế đánh giá theo "
                    "mức ưu tiên được phác đồ hỗ trợ."
                ),
                matched_criteria=["DB-CRIT-777"],
                citation_ids=["DB-ESI-AUTH-777"],
            )
        ]
    )
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        lambda **_kwargs: llm,
    )

    reasoning = await run_triage_reasoner_node({**state, **retrieval})

    # Several queries now run against each corpus, so what matters is that both
    # were searched -- not that exactly one call reached each.
    searched = {call["table"] for call in vector_searches}
    assert searched == {"esi_knowledge_documents", "mietic_cases"}
    # Every dense search used a vector from the one embedding service, and the
    # keyword channel searched the same corpora with the same queries.
    dense_calls = [call for call in vector_searches if "vector" in call]
    assert dense_calls
    assert all(call["vector"] is embedding.vector for call in dense_calls)
    assert retrieval["retrieved_evidence"][0]["citation_id"] == "DB-ESI-AUTH-777"
    assert retrieval["turn_rag_citations"][0]["protocolId"] == "DB-ESI-AUTH-777"
    assert "DB_AUTHORITY_PROMPT_MARKER" in llm.prompts[0]
    assert "DB-CRIT-777" in llm.prompts[0]
    assert reasoning["decision_status"] == "PROPOSED"
    assert reasoning["turn_rag_citations"][0]["id"] == "DB-ESI-AUTH-777"


@pytest.mark.asyncio
async def test_open_contradiction_short_circuits_before_structured_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def must_not_create_llm(**_kwargs: Any) -> Any:
        raise AssertionError("contradictory canonical state reached the LLM")

    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        must_not_create_llm,
    )
    state = {
        **_grounded_evidence_state(),
        "unresolved_contradictions": [{"field": "onset_time"}],
    }
    context = TurnContext(state)
    context.called_tools.add("retrieve_clinical_evidence")

    result = await reasoning_phase(context)

    assert result["decision_status"] == "NEEDS_CLARIFICATION"
    assert context.state["evidence_sufficiency_outcome"] == "CONTRADICTORY_DATA"
    assert context.state["selected_action"]["target"] == "contradiction_onset_time"
    assert context.state["active_question"]["field"] == "contradiction_onset_time"
    assert context.state["current_esi_level"] is None
    assert context.state["sbar_report"] is None


@pytest.mark.asyncio
async def test_resolved_proposal_does_not_execute_an_unnecessary_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A grounded PROPOSE goes to SBAR, never back into question routing."""
    llm = _ScriptedStructuredLLM([_propose()])
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        lambda **_kwargs: llm,
    )

    async def question_must_not_run(_state: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("resolved evidence decision triggered a question")

    summary_calls: list[dict[str, Any]] = []

    async def safe_summary(state: dict[str, Any]) -> dict[str, Any]:
        summary_calls.append(dict(state))
        return {
            "sbar_report": {
                "situation": "Grounded proposal ready for nurse review",
                "citations": ["ESI-AUTH-001"],
            },
            "workflow_phase": "HANDOFF",
            "next_step": "complete",
        }

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.execute_selected_action_node",
        question_must_not_run,
    )
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.create_sbar_summary_node",
        safe_summary,
    )
    context = TurnContext(_grounded_evidence_state())
    context.called_tools.add("retrieve_clinical_evidence")

    result = await reasoning_phase(context)

    assert len(llm.prompts) == 1
    assert len(summary_calls) == 1
    assert summary_calls[0]["decision_status"] == "PROPOSED"
    assert result["decision_status"] == "PROPOSED"
    assert context.state["evidence_sufficiency_outcome"] == "READY_FOR_REASONING"
    assert context.state["current_esi_level"] == 3
    assert context.state.get("active_question") is None
    assert context.state.get("selected_action") is None
    assert all(
        item.tool_name != "evidence_question_execution" for item in context.audit
    )


@pytest.mark.asyncio
async def test_reasoner_need_more_patient_info_executes_only_targeted_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = _ScriptedStructuredLLM(
        [
            TriageEvaluation(
                decision="NEED_MORE_PATIENT_INFO",
                esi_level=None,
                reasoning=(
                    "Mức độ hiện tại là dữ kiện còn thiếu có thể thay đổi nhánh "
                    "quyết định của phác đồ."
                ),
                matched_criteria=["AUTH-CRIT-1"],
                citation_ids=["ESI-AUTH-001"],
                requested_fact="severity_score",
            )
        ]
    )
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        lambda **_kwargs: llm,
    )
    state = {
        **_grounded_evidence_state(),
        "missing_critical_fields": ["onset_time", "severity_score"],
        "decision_relevant_unknowns": ["severity_score"],
        "readiness_outcome": "NOT_READY",
    }
    # Onset is known, but leaving it first in the legacy list makes this a
    # regression check that the structured target wins over fixed ordering.
    state["clinical_blueprint"] = {
        **state["clinical_blueprint"],
        "onset_time": "sáng nay",
        "severity_score": None,
    }
    context = TurnContext(state)
    context.called_tools.add("retrieve_clinical_evidence")

    result = await reasoning_phase(context)

    assert result["decision_status"] == "NEEDS_CLARIFICATION"
    assert context.state["evidence_sufficiency_outcome"] == "NEED_MORE_PATIENT_INFO"
    assert context.state["selected_action"]["target"] == "severity_score"
    assert context.state["active_question"]["field"] == "severity_score"
    assert "0 đến 10" in context.state["response"]
    assert "bắt đầu từ" not in context.state["response"]
    assert context.state["current_esi_level"] is None
    assert context.state["turn_rag_citations"] == []


@pytest.mark.asyncio
async def test_reasoner_can_request_one_specific_protocol_fact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = _ScriptedStructuredLLM(
        [
            TriageEvaluation(
                decision="NEED_MORE_PATIENT_INFO",
                reasoning=(
                    "Khó thở hiện tại là dữ kiện còn thiếu có thể thay đổi nhánh "
                    "quyết định của phác đồ đang được viện dẫn."
                ),
                matched_criteria=["AUTH-CRIT-1"],
                citation_ids=["ESI-AUTH-001"],
                requested_fact="symptom.dyspnea",
            )
        ]
    )
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        lambda **_kwargs: llm,
    )
    context = TurnContext(_grounded_evidence_state())
    context.called_tools.add("retrieve_clinical_evidence")

    result = await reasoning_phase(context)

    assert result["decision_status"] == "NEEDS_CLARIFICATION"
    assert context.state["selected_action"]["target"] == "symptom.dyspnea"
    assert context.state["active_question"]["field"] == "associated_symptoms"
    assert "khó thở" in context.state["response"]
    options = context.state["structured_question"]["options"]
    assert [item["value"] for item in options] == [
        "Có khó thở",
        "Không có khó thở",
        "Tôi không chắc có khó thở",
    ]


@pytest.mark.asyncio
async def test_reasoner_rejects_criterion_from_a_different_citation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _grounded_evidence_state()
    state["retrieved_evidence"].append(
        {
            "citation_id": "ESI-AUTH-002",
            "protocol_code": "ESI-AUTH-002",
            "section": "Decision Point C",
            "protocol_content": "Authority text for AUTH-CRIT-2.",
            "protocol_criteria": ["AUTH-CRIT-2"],
            "decision_points": ["C"],
            "retrieval_facets": ["resources"],
        }
    )
    state["turn_rag_citations"].append(
        {
            "id": "ESI-AUTH-002",
            "title": "Another ESI decision rule",
            "protocolId": "ESI-AUTH-002",
            "excerpt": "Authority text for AUTH-CRIT-2.",
            "sourceType": "validated_protocol",
            "retrievalChannels": [
                {"channel": "en_dense", "rank": 2, "score": 0.88}
            ],
        }
    )
    # Recreate the old, unsafe turn-wide union to prove it cannot authorize a
    # criterion that belongs to a document the model did not cite.
    state["matched_protocol_criteria"] = ["AUTH-CRIT-1", "AUTH-CRIT-2"]
    llm = _ScriptedStructuredLLM(
        [
            TriageEvaluation(
                decision="PROPOSE",
                esi_level=3,
                reasoning=(
                    "Các dữ kiện đã khai cần được đánh giá theo tiêu chí từ "
                    "một tài liệu khác với tài liệu đang được viện dẫn."
                ),
                citation_ids=["ESI-AUTH-001"],
                matched_criteria=["AUTH-CRIT-2"],
            )
        ]
    )
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        lambda **_kwargs: llm,
    )

    result = await run_triage_reasoner_node(state)

    assert result["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert result["current_esi_level"] is None
    assert result["turn_rag_citations"] == []


@pytest.mark.asyncio
async def test_unexpected_reasoner_exception_cannot_return_stale_ready_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def explode(_state: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("unexpected model adapter failure")

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.run_triage_reasoner_node",
        explode,
    )
    state = {
        **_grounded_evidence_state(),
        "response": "stale successful-looking response",
        "current_esi_level": 2,
        "sbar_report": {"situation": "stale"},
    }
    context = TurnContext(state)
    context.called_tools.add("retrieve_clinical_evidence")

    result = await reasoning_phase(context)

    assert result["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert context.state["evidence_sufficiency_outcome"] == "ABSTAIN"
    assert context.state["current_esi_level"] is None
    assert context.state["sbar_report"] is None
    assert context.state["turn_rag_citations"] == []
    assert context.state["response"] != "stale successful-looking response"


@pytest.mark.asyncio
async def test_negative_radiation_answer_round_trip_is_not_reasked() -> None:
    validation = validate_answer_alignment(
        "Không lan",
        {"field": "radiation"},
    )
    facts = extract_facts("Không lan")
    radiation = next(item for item in facts if item.key == "radiation")
    result = await analyze_patient_intake(
        {
            "intent": "TRIAGE_FOLLOW_UP",
            "query": "Không lan",
            "answer_alignment": validation.alignment,
            "active_question": {"field": "radiation"},
            "clinical_blueprint": {"radiation": None},
            "current_turn_id": "radiation-turn",
        }
    )
    canonical = CanonicalPatientState.from_dict(result["canonical_state"])

    assert validation.alignment == "DIRECT_ANSWER"
    assert radiation.value == "không lan"
    assert radiation.status == "KNOWN"
    assert radiation.raw_span == "Không lan"
    assert canonical.value_of("radiation") == "không lan"
    assert result["clinical_blueprint"]["radiation"] == "không lan"


@pytest.mark.asyncio
async def test_scoped_adaptive_severity_answer_is_recorded_before_confirmation() -> None:
    canonical = CanonicalPatientState()
    canonical.record("symptom.headache", True, turn_id="t1")
    result = await analyze_patient_intake(
        {
            "intent": "TRIAGE_FOLLOW_UP",
            "query": "4",
            "answer_alignment": "DIRECT_ANSWER",
            "active_question": {
                "field": "headache.severity_score",
                "semantic_target": "headache.severity_score",
            },
            "canonical_state": canonical.to_dict(),
            "clinical_blueprint": {"chief_complaint": ["đau đầu"]},
            "current_turn_id": "severity-turn",
        }
    )
    updated = CanonicalPatientState.from_dict(result["canonical_state"])

    assert updated.value_of("headache.severity_score") == 4
    assert result["clinical_blueprint"]["severity_score"] == 4


def test_reasoner_does_not_reask_generic_targets_answered_on_primary_problem() -> None:
    canonical = CanonicalPatientState()
    canonical.record("symptom.headache", True, turn_id="t1")
    canonical.record("headache.onset_time", "vừa mới bị đau", turn_id="t2")
    canonical.record("headache.severity_score", 4, turn_id="t3")
    state = {
        "canonical_state": canonical.to_dict(),
        # Simulate a stale caller that has not yet received the fixed
        # projection.  The reasoner guard must still read canonical truth.
        "clinical_blueprint": {"chief_complaint": ["đau đầu"]},
        "action_loop_state": {"asked_targets": {}},
    }

    assert _target_is_unresolved("onset_time", state) is False
    assert _target_is_unresolved("severity_score", state) is False


@pytest.mark.asyncio
async def test_refinement_stops_when_retrieval_returns_no_new_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _need_more_evidence(
        query="severe abdominal pain ESI resource threshold",
        citation_id="ESI-AUTH-001",
        criterion="AUTH-CRIT-1",
    )
    llm = _ScriptedStructuredLLM([first])
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        lambda **_kwargs: llm,
    )

    refinement_calls: list[dict[str, Any]] = []

    async def refined_retrieval(state: dict[str, Any]) -> dict[str, Any]:
        refinement_calls.append(dict(state))
        return {
            "evidence_status": "RETRIEVED",
            "evidence_authority_status": "AUTHORIZED",
            "evidence_sufficiency_outcome": "PENDING_EVALUATION",
            "decision_status": "READY_FOR_REASONING",
            "next_step": "triage_reasoner",
        }

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.retrieve_evidence_node",
        refined_retrieval,
    )
    context = TurnContext(_grounded_evidence_state())
    context.called_tools.add("retrieve_clinical_evidence")

    result = await reasoning_phase(context)

    assert len(refinement_calls) == 1
    assert len(llm.prompts) == 1
    assert context.state["retrieval_refinement_count"] == 1
    assert refinement_calls[0]["retrieval_refined_query"].startswith(
        "severe abdominal pain"
    )
    assert refinement_calls[0]["retrieval_decision_point"] == "B"
    assert refinement_calls[0]["retrieval_facets"] == ["severe-pain"]
    assert context.state["retrieval_refinement_stop_reason"] == "NO_NEW_EVIDENCE"
    assert result["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert context.state["current_esi_level"] is None
    assert context.state["next_step"] == "complete"


@pytest.mark.asyncio
async def test_default_policy_allows_two_progressive_refinements_then_proposes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second_evidence, second_citation = _authority_artifacts(
        "ESI-AUTH-002",
        "AUTH-CRIT-2",
    )
    third_evidence, third_citation = _authority_artifacts(
        "ESI-AUTH-003",
        "AUTH-CRIT-3",
    )
    llm = _ScriptedStructuredLLM(
        [
            _need_more_evidence(
                query="abdominal pain decision point B severe pain",
                citation_id="ESI-AUTH-001",
                criterion="AUTH-CRIT-1",
            ),
            _need_more_evidence(
                query="abdominal pain decision point C resource count",
                citation_id="ESI-AUTH-002",
                criterion="AUTH-CRIT-2",
            ),
            TriageEvaluation(
                decision="PROPOSE",
                esi_level=3,
                reasoning=(
                    "Hai bước làm rõ bằng chứng đã cung cấp tiêu chí cần thiết "
                    "để nhân viên y tế xem xét mức ưu tiên đề xuất."
                ),
                matched_criteria=["AUTH-CRIT-3"],
                citation_ids=["ESI-AUTH-003"],
            ),
        ]
    )
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        lambda **_kwargs: llm,
    )
    snapshots = [
        (second_evidence, second_citation),
        (third_evidence, third_citation),
    ]
    refinement_calls: list[dict[str, Any]] = []

    async def progressive_retrieval(state: dict[str, Any]) -> dict[str, Any]:
        refinement_calls.append(dict(state))
        evidence, citation = snapshots[len(refinement_calls) - 1]
        retrieved = [*state["retrieved_evidence"], evidence]
        citations = [*state["turn_rag_citations"], citation]
        return {
            "retrieved_evidence": retrieved,
            "turn_rag_citations": citations,
            "matched_protocol_criteria": [
                criterion
                for item in retrieved
                for criterion in item["protocol_criteria"]
            ],
            "evidence_status": "RETRIEVED",
            "evidence_authority_status": "AUTHORIZED",
            "evidence_sufficiency_outcome": "PENDING_EVALUATION",
            "decision_status": "READY_FOR_REASONING",
            "next_step": "triage_reasoner",
        }

    async def safe_summary(_state: dict[str, Any]) -> dict[str, Any]:
        return {
            "sbar_report": {"citations": ["ESI-AUTH-003"]},
            "workflow_phase": "HANDOFF",
            "next_step": "complete",
        }

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.retrieve_evidence_node",
        progressive_retrieval,
    )
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.create_sbar_summary_node",
        safe_summary,
    )
    context = TurnContext(_grounded_evidence_state())
    context.called_tools.add("retrieve_clinical_evidence")

    result = await reasoning_phase(context)

    assert len(refinement_calls) == 2
    assert len(llm.prompts) == 3
    assert context.state["retrieval_refinement_count"] == 2
    assert len(context.state["retrieval_refinement_signatures"]) == 2
    assert len(context.state["retrieval_candidate_fingerprints"]) == 3
    assert context.state["retrieval_refinement_stop_reason"] is None
    assert result["decision_status"] == "PROPOSED"
    assert context.state["current_esi_level"] == 3
    assert context.state["next_step"] == "complete"


@pytest.mark.asyncio
async def test_cosmetic_query_repeat_stops_before_another_retrieval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second_evidence, second_citation = _authority_artifacts(
        "ESI-AUTH-002",
        "AUTH-CRIT-2",
    )
    llm = _ScriptedStructuredLLM(
        [
            _need_more_evidence(
                query="Severe abdominal pain resource threshold",
                citation_id="ESI-AUTH-001",
                criterion="AUTH-CRIT-1",
            ),
            _need_more_evidence(
                query="  severe   ABDOMINAL pain resource threshold  ",
                citation_id="ESI-AUTH-002",
                criterion="AUTH-CRIT-2",
            ),
        ]
    )
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        lambda **_kwargs: llm,
    )
    retrieval_calls = 0

    async def one_progressive_retrieval(
        state: dict[str, Any],
    ) -> dict[str, Any]:
        nonlocal retrieval_calls
        retrieval_calls += 1
        return {
            "retrieved_evidence": [*state["retrieved_evidence"], second_evidence],
            "turn_rag_citations": [
                *state["turn_rag_citations"],
                second_citation,
            ],
            "matched_protocol_criteria": ["AUTH-CRIT-1", "AUTH-CRIT-2"],
            "evidence_status": "RETRIEVED",
            "evidence_authority_status": "AUTHORIZED",
            "evidence_sufficiency_outcome": "PENDING_EVALUATION",
            "decision_status": "READY_FOR_REASONING",
            "next_step": "triage_reasoner",
        }

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.retrieve_evidence_node",
        one_progressive_retrieval,
    )
    context = TurnContext(_grounded_evidence_state())
    context.called_tools.add("retrieve_clinical_evidence")

    result = await reasoning_phase(context)

    assert retrieval_calls == 1
    assert len(llm.prompts) == 2
    assert context.state["retrieval_refinement_count"] == 1
    assert context.state["retrieval_refinement_stop_reason"] == (
        "NO_MEANINGFUL_QUERY_CHANGE"
    )
    assert result["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert context.state["current_esi_level"] is None


@pytest.mark.asyncio
async def test_progressive_refinement_stops_at_configured_default_maximum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second_evidence, second_citation = _authority_artifacts(
        "ESI-AUTH-002",
        "AUTH-CRIT-2",
    )
    third_evidence, third_citation = _authority_artifacts(
        "ESI-AUTH-003",
        "AUTH-CRIT-3",
    )
    llm = _ScriptedStructuredLLM(
        [
            _need_more_evidence(
                query="first bounded refinement",
                citation_id="ESI-AUTH-001",
                criterion="AUTH-CRIT-1",
            ),
            _need_more_evidence(
                query="second bounded refinement",
                citation_id="ESI-AUTH-002",
                criterion="AUTH-CRIT-2",
            ),
            _need_more_evidence(
                query="third refinement must not run",
                citation_id="ESI-AUTH-003",
                criterion="AUTH-CRIT-3",
            ),
        ]
    )
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        lambda **_kwargs: llm,
    )
    snapshots = [
        (second_evidence, second_citation),
        (third_evidence, third_citation),
    ]
    retrieval_calls = 0

    async def progressive_retrieval(state: dict[str, Any]) -> dict[str, Any]:
        nonlocal retrieval_calls
        evidence, citation = snapshots[retrieval_calls]
        retrieval_calls += 1
        retrieved = [*state["retrieved_evidence"], evidence]
        return {
            "retrieved_evidence": retrieved,
            "turn_rag_citations": [*state["turn_rag_citations"], citation],
            "matched_protocol_criteria": [
                criterion
                for item in retrieved
                for criterion in item["protocol_criteria"]
            ],
            "evidence_status": "RETRIEVED",
            "evidence_authority_status": "AUTHORIZED",
            "evidence_sufficiency_outcome": "PENDING_EVALUATION",
            "decision_status": "READY_FOR_REASONING",
            "next_step": "triage_reasoner",
        }

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.retrieve_evidence_node",
        progressive_retrieval,
    )
    context = TurnContext(_grounded_evidence_state())
    context.called_tools.add("retrieve_clinical_evidence")

    result = await reasoning_phase(context)

    assert retrieval_calls == 2
    assert len(llm.prompts) == 3
    assert context.state["retrieval_refinement_count"] == 2
    assert context.state["retrieval_refinement_stop_reason"] == "MAX_ATTEMPTS"
    assert result["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert context.state["next_step"] == "complete"


def test_refinement_budget_has_default_and_code_owned_hard_cap() -> None:
    assert Settings(_env_file=None).rag_max_refinement_attempts == 2
    assert RAG_REFINEMENT_ATTEMPTS_HARD_MAX == 3
    assert Settings(
        _env_file=None,
        rag_max_refinement_attempts=0,
    ).rag_max_refinement_attempts == 0
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            rag_max_refinement_attempts=RAG_REFINEMENT_ATTEMPTS_HARD_MAX + 1,
        )


@pytest.mark.asyncio
async def test_configured_zero_budget_disables_refinement_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = _ScriptedStructuredLLM(
        [
            _need_more_evidence(
                query="this refinement must not execute",
                citation_id="ESI-AUTH-001",
                criterion="AUTH-CRIT-1",
            )
        ]
    )
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        lambda **_kwargs: llm,
    )
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_rag_refinement_attempt_limit",
        lambda: 0,
    )
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.get_rag_refinement_attempt_limit",
        lambda: 0,
    )

    async def retrieval_must_not_run(_state: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("zero refinement budget executed retrieval")

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.retrieve_evidence_node",
        retrieval_must_not_run,
    )
    context = TurnContext(_grounded_evidence_state())
    context.called_tools.add("retrieve_clinical_evidence")

    result = await reasoning_phase(context)

    assert len(llm.prompts) == 1
    assert context.state.get("retrieval_refinement_count", 0) == 0
    assert context.state["retrieval_refinement_stop_reason"] == "MAX_ATTEMPTS"
    assert result["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert context.state["current_esi_level"] is None


@pytest.mark.asyncio
async def test_conflicting_mietic_label_never_enters_reasoner_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embedding = _FakeEmbeddingService()
    retriever = _FakeRetriever(_authority_outcome(), _mietic_outcome(conflicting=True))
    monkeypatch.setattr(
        "src.services.rag.hybrid_retrieval.get_embedding_service",
        lambda: embedding,
    )
    monkeypatch.setattr(
        "src.agents.nodes.evidence_gate.get_knowledge_retriever",
        lambda: retriever,
    )
    monkeypatch.setattr(
        "src.agents.nodes.evidence_gate.translate_query",
        lambda _query: None,
    )
    state = _confirmed_retrieval_state()
    retrieval = await retrieve_evidence_node(state)
    assert retrieval["case_support_evidence"][0]["label_status"] == "CONFLICTING"
    assert retrieval["case_support_evidence"][0]["validated_esi_level"] == 1

    llm = _ScriptedStructuredLLM([_propose()])
    monkeypatch.setattr(
        "src.agents.nodes.triage_reasoner.get_resilient_llm",
        lambda **_kwargs: llm,
    )
    result = await run_triage_reasoner_node({**state, **retrieval})

    prompt = llm.prompts[0]
    assert "MIETIC-CONFLICT-SECRET" not in prompt
    assert "MIETIC secret conflict" not in prompt
    assert "CONFLICTING" not in prompt
    assert result["decision_status"] == "PROPOSED"
    assert result["current_esi_level"] == 3
    assert result["turn_rag_citations"][0]["id"] == "ESI-AUTH-001"


def test_public_dtos_accept_structured_channels_and_retrieval_failure() -> None:
    citation = RagCitationDTO.model_validate(
        {
            "id": "ESI-AUTH-001",
            "title": "ESI decision rule",
            "protocolId": "ESI-AUTH-001",
            "excerpt": "Validated authority excerpt",
            "sourceType": "validated_protocol",
            "retrievalChannels": [
                {"channel": "en_dense", "rank": 1, "score": 0.92}
            ],
        }
    )
    message = PatientChatMessageDTO.model_validate(
        {
            "id": "message-1",
            "sender": "bot",
            "timestamp": "2026-08-20T00:00:00+00:00",
            "content": "Tra cứu tạm thời gián đoạn do lỗi kỹ thuật.",
            "step": 3,
            "ragCitations": [citation.model_dump()],
            "decisionStatus": "RETRIEVAL_FAILURE",
            "workflowPhase": "RETRIEVAL",
            "evidenceStatus": "RETRIEVAL_FAILURE",
        }
    )

    assert citation.retrievalChannels == [
        {"channel": "en_dense", "rank": 1, "score": 0.92}
    ]
    assert message.decisionStatus == "RETRIEVAL_FAILURE"
    assert message.evidenceStatus == "RETRIEVAL_FAILURE"
    assert message.ragCitations is not None
    assert message.ragCitations[0].retrievalChannels[0]["channel"] == "en_dense"
