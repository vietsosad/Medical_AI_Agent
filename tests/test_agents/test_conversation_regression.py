"""Whole conversations, driven turn by turn through the real runtime.

These are transcripts, not unit tests. Each one was first observed failing
against the running system, and each asserts on what the patient would see and
on the structured state that produced it -- never on which functions were
called.

Between them they pin down the behaviours that separate an adaptive agent from
a fixed questionnaire:

* clinical input is recognised as clinical, whatever words the patient used;
* a patient confirming their summary is not the same as having enough
  information to triage;
* a missing patient fact produces a targeted question, not a nurse handoff;
* missing authority evidence produces bounded refinement, not a nurse handoff;
* a technical outage stays a technical outage;
* facts survive between turns;
* and at least one ordinary, non-emergency conversation actually reaches a
  cited ESI level.

Everything external is replaced with an in-process fake so the transcripts are
deterministic and offline. The pipeline itself, its gates and its state
transitions are the real ones.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from copy import deepcopy
from typing import Any

import pytest

from src.agents.deepagent_runtime.tools import (
    TurnContext,
    run_reflex_screen,
    run_remaining_required_tools,
)
from src.agents.nodes.contextual_emergency_detector import (
    ContextualEmergencyAssessment,
)
from src.agents.nodes.evidence_gate import INSUFFICIENT_EVIDENCE_HANDOFF_MESSAGE
from src.agents.nodes.intent_classifier import CRISIS_SUPPORT_MESSAGE
from src.agents.nodes.triage_reasoner import TriageEvaluation
from src.services.rag.outcomes import (
    RetrievalOutcome,
    RetrievalStatus,
    RetrievedItem,
)

AUTHORITY_ID = "ESI-AUTH-DP-B"
AUTHORITY_CRITERION = "ESI-AUTH-DP-B:decision_point:B"
SECOND_AUTHORITY_ID = "ESI-AUTH-ABDO"
SECOND_CRITERION = "ESI-AUTH-ABDO:facet:HIGH_RISK"

GENERIC_INTAKE_PROMPT = "hãy mô tả triệu chứng đang gặp"

# ---------------------------------------------------------------------------
# Fakes. Only the outside world is replaced.
# ---------------------------------------------------------------------------


class _FakeEmbeddings:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.vector = [0.1, 0.2, 0.3]

    async def embed_query_async(self, query: str) -> list[float]:
        self.queries.append(query)
        return self.vector


def _authority_item(doc_id: str, decision_points: list[str], facets: list[str]):
    return RetrievedItem(
        doc_id=doc_id,
        text=(
            f"{doc_id}: Decision Point B asks whether the patient is in severe "
            "pain or distress, judged from the presentation as a whole."
        ),
        score=0.9,
        source_table="esi_knowledge_documents",
        retrieval_scope="CLINICAL_AUTHORITY",
        authority_status="AUTHORITATIVE",
        retrieval_channel="dense",
        metadata={
            "atom_type": "DECISION_RULE",
            "pass5_version": "pass5-test",
            "retrieval_text_sha256": f"hash-{doc_id}",
            "payload": {
                "title": f"Authority {doc_id}",
                "heading_path": "Decision Point B",
                "decision_points": decision_points,
                "retrieval_facets": facets,
                "issuing_body": "AHRQ",
                "source_occurrences": [{"source_uri": "https://example.test/esi"}],
            },
        },
    )


def _authority_success() -> RetrievalOutcome:
    return RetrievalOutcome(
        status=RetrievalStatus.SUCCESS,
        channels=("dense",),
        items=(
            _authority_item(AUTHORITY_ID, ["B"], ["SEVERE_PAIN"]),
            _authority_item(SECOND_AUTHORITY_ID, [], ["HIGH_RISK"]),
        ),
    )


def _authority_empty() -> RetrievalOutcome:
    return RetrievalOutcome(status=RetrievalStatus.NO_RESULTS, channels=("dense",))


def _authority_outage() -> RetrievalOutcome:
    return RetrievalOutcome(
        status=RetrievalStatus.RETRIEVAL_FAILURE,
        channels=("dense",),
        error="connection refused to vector store",
    )


def _no_cases() -> RetrievalOutcome:
    return RetrievalOutcome(status=RetrievalStatus.NO_RESULTS, channels=("dense",))


class _FakeRetriever:
    """Serves one authority outcome per call, repeating the last one.

    Implements both the single-query and the multi-query hybrid surfaces, so a
    transcript exercises whichever the pipeline actually calls rather than
    silently passing because the method it expected was never invoked.
    """

    def __init__(
        self,
        authority: Sequence[RetrievalOutcome],
        case_support: RetrievalOutcome | None = None,
    ) -> None:
        self._authority = list(authority)
        self._case_support = case_support or _no_cases()
        self.authority_calls: list[dict[str, Any]] = []

    def _next_authority(self) -> RetrievalOutcome:
        if len(self._authority) > 1:
            return self._authority.pop(0)
        return self._authority[0]

    async def search_esi_authority(self, query: str, **kwargs: Any) -> RetrievalOutcome:
        self.authority_calls.append({"query": query, **kwargs})
        return self._next_authority()

    async def search_mietic_cases(self, query: str, **kwargs: Any) -> RetrievalOutcome:
        return self._case_support

    async def search_esi_authority_hybrid(
        self,
        queries: list[tuple[str, str]],
        **kwargs: Any,
    ) -> tuple[RetrievalOutcome, dict[str, Any]]:
        self.authority_calls.append(
            {"query": "; ".join(text for _, text in queries), "queries": queries, **kwargs}
        )
        return self._next_authority(), {"channels": {}}

    async def search_mietic_cases_hybrid(
        self,
        queries: list[tuple[str, str]],
        **kwargs: Any,
    ) -> tuple[RetrievalOutcome, dict[str, Any]]:
        return self._case_support, {"channels": {}}


class _ScriptedReasoner:
    """A structured reasoner with a fixed sequence of decisions."""

    def __init__(self, results: Iterable[TriageEvaluation]) -> None:
        self._results = list(results)
        self.prompts: list[str] = []

    def with_structured_output(self, _schema: type[Any]) -> _ScriptedReasoner:
        return self

    async def ainvoke(self, prompt: str) -> TriageEvaluation:
        self.prompts.append(prompt)
        if not self._results:
            raise AssertionError("The reasoner was consulted more often than scripted")
        return self._results.pop(0)


class _ClearContext:
    """Contextual safety validator that finds no current emergency."""

    def with_structured_output(self, _schema: type[Any]) -> _ClearContext:
        return self

    async def ainvoke(self, _prompt: str) -> ContextualEmergencyAssessment:
        return ContextualEmergencyAssessment(
            context_type="CURRENT_PERSONAL_EVENT",
            is_current_personal_event=True,
            is_time_critical_emergency=False,
            confidence=0.9,
            risk_category="NONE",
            observed_signals=[],
            evidence_summary="Không thấy dấu hiệu cần cấp cứu ngay.",
        )


class _OfflineRouter:
    """Intent router fallback that is simply unavailable.

    Every transcript below must pass on the deterministic path alone, so the
    bounded model router is switched off here rather than scripted. A test that
    only passes because a language model rescued it would tell us nothing about
    the routing we actually ship.
    """

    def with_structured_output(self, _schema: type[Any]) -> _OfflineRouter:
        return self

    async def ainvoke(self, _prompt: str) -> Any:
        raise RuntimeError("intent router intentionally offline in transcripts")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


class Conversation:
    """Drive whole patient turns and keep the session state between them."""

    def __init__(self, *, clinical_memory: dict[str, Any] | None = None) -> None:
        self.state: dict[str, Any] = {
            "session_id": "session-regression",
            "patient_id": "patient-regression",
            "profile_id": "patient-regression",
            "clinical_memory": clinical_memory or {},
            "clinical_memory_updated_at": "2026-01-01T00:00:00+00:00",
            "clinical_memory_confirmation_status": "NOT_REVIEWED",
            "confirmed_clinical_memory_updated_at": None,
            "clinical_context_update_pending": False,
            "clinical_memory_update_pending": False,
            "vital_signs_status": "NOT_REVIEWED",
            "patient_confirmed_intake": False,
        }
        self._turn = 0

    async def say(self, query: str, **overrides: Any) -> dict[str, Any]:
        """One patient message, advanced exactly as the runtime advances it."""
        self._turn += 1
        self.state.update(
            {
                "query": query,
                "current_turn_id": f"turn-{self._turn}",
                "step": self._turn,
                "messages": [{"role": "user", "content": query}],
                "patient_confirmed_intake": overrides.pop("confirm_intake", False),
                "metadata": {"deepagent_tool_gated": False},
            }
        )
        self.state.update(overrides)
        context = TurnContext(self.state)
        await run_reflex_screen(context)
        await run_remaining_required_tools(context)
        self.state = context.state
        # A snapshot, so a transcript can compare what the patient saw on one
        # turn against what they saw on the next.
        return deepcopy(self.state)

    async def confirm_ehr(self) -> dict[str, Any]:
        """Click the 'my record is still correct' option on the EHR form."""
        return await self.say(
            "Thông tin EHR hiện tại vẫn đúng",
            selected_option_id="ehr_confirmed",
            clinical_memory_confirmation_status="CONFIRMED",
            confirmed_clinical_memory_updated_at="2026-01-01T00:00:00+00:00",
        )

    async def answer_until_review(
        self,
        *answers: str,
        max_turns: int = 14,
    ) -> dict[str, Any]:
        """Reply to the agent's questions until it offers the summary.

        The agent now decides when it has characterised the presentation well
        enough to be worth confirming, so a transcript cannot jump straight to
        the review the way it could when a bare complaint was enough. Supplied
        answers are used in order; anything beyond them is answered "tôi không
        rõ", which is a real answer -- it settles the question without
        asserting a clinical value -- so a transcript about retrieval does not
        have to script a full intake to get there.
        """
        remaining = list(answers)
        result = deepcopy(self.state)
        for _ in range(max_turns):
            if self.state.get("response_type") == "INTAKE_REVIEW":
                return result
            if self.state.get("next_step") not in {
                "wait_for_patient",
                "question_engine",
            }:
                return result
            reply = remaining.pop(0) if remaining else "Tôi không rõ"
            result = await self.say(reply)
        return result

    async def confirm_intake(self, *answers: str) -> dict[str, Any]:
        """Answer any open questions, then confirm the intake review."""
        await self.answer_until_review(*answers)
        return await self.say(
            "Tôi xác nhận thông tin trên là chính xác",
            confirm_intake=True,
        )


def _need_more_patient_info(target: str, *, citation: str = AUTHORITY_ID):
    """The reasoner wants one more fact. It has no matched criterion yet -- by
    definition, because that is what it is asking about."""
    return TriageEvaluation(
        decision="NEED_MORE_PATIENT_INFO",
        reasoning=(
            "Chưa đủ dữ kiện người bệnh để xác định nhánh quyết định phù hợp "
            "cho tình trạng hiện tại."
        ),
        matched_criteria=[],
        citation_ids=[citation],
        requested_fact=target,
        uncertainty_reasons=[f"Chưa biết {target}"],
    )


def _need_more_evidence():
    return TriageEvaluation(
        decision="NEED_MORE_EVIDENCE",
        reasoning=(
            "Dữ kiện người bệnh đã đủ nhưng bằng chứng hiện có chưa phủ nhánh "
            "quyết định cần thiết."
        ),
        matched_criteria=[],
        citation_ids=[AUTHORITY_ID],
        refined_query="severe abdominal pain decision point B",
        decision_point="B",
        retrieval_facets=["SEVERE_PAIN"],
    )


def _propose(level: int = 3):
    return TriageEvaluation(
        decision="PROPOSE",
        esi_level=level,
        reasoning=(
            "Mức độ đau và bối cảnh hiện tại phù hợp với tiêu chí đã trích dẫn "
            "và cần được nhân viên y tế đánh giá theo mức ưu tiên này."
        ),
        matched_criteria=[AUTHORITY_CRITERION],
        citation_ids=[AUTHORITY_ID],
    )


async def _offline_query_plan(problem_state, **_kwargs):
    from src.services.rag.clinical_query_planner import build_deterministic_queries

    return build_deterministic_queries(problem_state)


async def _no_llm_rerank(*_args: Any, **_kwargs: Any) -> bool:
    return False


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: _ClearContext(),
    )
    monkeypatch.setattr(
        "src.agents.nodes.intent_classifier.get_resilient_llm",
        lambda **_kwargs: _OfflineRouter(),
    )
    # Embedding now happens inside the hybrid search layer, which is where a
    # transcript has to intercept it.
    monkeypatch.setattr(
        "src.services.rag.hybrid_retrieval.get_embedding_service",
        lambda: _FakeEmbeddings(),
    )
    monkeypatch.setattr(
        "src.agents.nodes.evidence_gate.translate_query",
        lambda _query: None,
    )
    # The query planner's optional model refinement is an outside service. The
    # deterministic baseline it falls back to is the grounded path under test.
    monkeypatch.setattr(
        "src.agents.nodes.evidence_gate.plan_clinical_queries",
        _offline_query_plan,
    )
    monkeypatch.setattr(
        "src.agents.nodes.evidence_gate.llm_rerank",
        _no_llm_rerank,
    )


@pytest.fixture
def retrieval(monkeypatch: pytest.MonkeyPatch):
    """Install an authority retriever for the transcript that asks for one."""

    def install(
        outcomes: Sequence[RetrievalOutcome] | None = None,
        *,
        case_support: RetrievalOutcome | None = None,
    ) -> _FakeRetriever:
        retriever = _FakeRetriever(
            list(outcomes or [_authority_success()]),
            case_support,
        )
        monkeypatch.setattr(
            "src.agents.nodes.evidence_gate.get_knowledge_retriever",
            lambda: retriever,
        )
        return retriever

    return install


@pytest.fixture
def reasoner(monkeypatch: pytest.MonkeyPatch):
    def install(results: Iterable[TriageEvaluation]) -> _ScriptedReasoner:
        scripted = _ScriptedReasoner(results)
        monkeypatch.setattr(
            "src.agents.nodes.triage_reasoner.get_resilient_llm",
            lambda **_kwargs: scripted,
        )
        return scripted

    return install


# ---------------------------------------------------------------------------
# Case A -- an irrelevant opener does not deafen the agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_case_a_symptom_after_irrelevant_opener_is_recognised() -> None:
    chat = Conversation()

    opener = await chat.say("em yêu anh")
    assert opener["intent"] in {"UNCLEAR", "OUT_OF_SCOPE"}

    symptom = await chat.say("tôi khó thở")

    assert symptom["intent"] == "TRIAGE_NEW_SYMPTOM"
    assert "dyspnea" in "".join(symptom["canonical_state"]["facts"])
    # The one thing that must never happen: asking for a symptom description
    # from someone who has just given one.
    assert GENERIC_INTAKE_PROMPT not in symptom["response"]


@pytest.mark.asyncio
async def test_case_a_variants_are_not_answered_with_the_generic_prompt() -> None:
    """The wordings that were observed falling through to "I did not understand"."""
    for utterance in (
        "tôi bị sốt",
        "Tôi đau bụng từ sáng.",
        "đi ngoài phân đen",
        "tôi hay bị hụt hơi khi leo cầu thang",
        "tôi bị choáng",
    ):
        chat = Conversation()
        turn = await chat.say(utterance)
        assert turn["intent"] == "TRIAGE_NEW_SYMPTOM", utterance
        assert GENERIC_INTAKE_PROMPT not in turn["response"], utterance


# ---------------------------------------------------------------------------
# Case B -- a bare complaint asks, it does not hand off
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_case_b_fever_is_canonicalised_and_does_not_hand_off() -> None:
    chat = Conversation()

    turn = await chat.say("tôi bị sốt")

    assert turn["intent"] == "TRIAGE_NEW_SYMPTOM"
    assert turn["clinical_blueprint"]["chief_complaint"] == ["sốt"]
    assert turn["decision_status"] != "INSUFFICIENT_EVIDENCE"
    assert turn["workflow_phase"] != "HANDOFF"
    assert INSUFFICIENT_EVIDENCE_HANDOFF_MESSAGE not in turn["response"]
    # Something is still being asked for, and it is a named target.
    assert turn["selected_action"]["action_type"] in {"ASK", "CLARIFY"}
    assert turn["selected_action"]["target"]


# ---------------------------------------------------------------------------
# Case C -- complaint and onset in one sentence are not asked for again
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_case_c_complaint_and_onset_in_one_sentence_are_kept() -> None:
    chat = Conversation()

    turn = await chat.say("Tôi đau bụng từ sáng.")

    blueprint = turn["clinical_blueprint"]
    assert blueprint["chief_complaint"] == ["đau bụng"]
    assert blueprint["onset_time"] == "sáng"
    assert turn["selected_action"]["target"] not in {"chief_complaint", "onset_time"}

    after_ehr = await chat.confirm_ehr()
    assert after_ehr["clinical_blueprint"]["onset_time"] == "sáng"
    assert after_ehr["clinical_blueprint"]["chief_complaint"] == ["đau bụng"]


# ---------------------------------------------------------------------------
# Case D -- confirmation is not sufficiency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_case_d_confirmed_intake_still_asks_for_a_decision_critical_fact(
    retrieval,
    reasoner,
) -> None:
    retrieval()
    reasoner([_need_more_patient_info("severity_score")])

    chat = Conversation()
    await chat.say("Tôi đau bụng từ sáng.")
    await chat.confirm_ehr()
    confirmed = await chat.confirm_intake()

    # The patient did confirm. That is recorded, and it is not the same claim
    # as "we now know enough".
    assert confirmed["evidence_sufficiency_outcome"] == "NEED_MORE_PATIENT_INFO"
    assert confirmed["evidence_requested_fact"] == "severity_score"
    assert confirmed["decision_status"] == "NEEDS_CLARIFICATION"
    assert confirmed["workflow_phase"] == "CLARIFICATION"
    assert confirmed["response_type"] == "STRUCTURED_QUESTION"
    assert "0 đến 10" in confirmed["response"]
    assert confirmed["current_esi_level"] is None
    assert INSUFFICIENT_EVIDENCE_HANDOFF_MESSAGE not in confirmed["response"]


@pytest.mark.asyncio
async def test_case_d_question_survives_without_a_matched_criterion(
    retrieval,
    reasoner,
) -> None:
    """The regression that made every ordinary conversation end at the nurse.

    A gap outcome has no matched criterion, because a criterion nobody has the
    facts to match is exactly what the question is about. Requiring one turned
    the reasoner's question into an abstention.
    """
    retrieval()
    scripted = reasoner([_need_more_patient_info("severity_score")])

    chat = Conversation()
    await chat.say("Tôi đau bụng từ sáng.")
    await chat.confirm_ehr()
    result = await chat.confirm_intake()

    assert scripted.prompts, "the reasoner was never consulted"
    assert result["evidence_sufficiency_outcome"] == "NEED_MORE_PATIENT_INFO"
    assert result.get("handoff_reason") is None
    assert result["selected_action"]["action_type"] == "ASK"
    assert result["selected_action"]["target"] == "severity_score"


@pytest.mark.asyncio
async def test_case_d_ungrounded_citation_is_retried_before_handing_off(
    retrieval,
    reasoner,
) -> None:
    """A wrong citation id is a formatting slip, not a clinical finding.

    Observed live: the reasoner asked a perfectly sensible question but
    attached a citation id that was not in the evidence it had been given, and
    the patient's conversation ended at the nurse queue over it. It gets one
    reminder, under the same gates.
    """
    retrieval()
    scripted = reasoner(
        [
            _need_more_patient_info("severity_score", citation="NOT-IN-EVIDENCE"),
            _need_more_patient_info("severity_score"),
        ]
    )

    chat = Conversation()
    await chat.say("Tôi đau bụng từ sáng.")
    await chat.confirm_ehr()
    result = await chat.confirm_intake()

    assert len(scripted.prompts) == 2
    assert "citation_ids" in scripted.prompts[1]
    assert result["evidence_sufficiency_outcome"] == "NEED_MORE_PATIENT_INFO"
    assert result["evidence_requested_fact"] == "severity_score"
    assert result.get("handoff_reason") is None


@pytest.mark.asyncio
async def test_a_second_ungrounded_answer_still_fails_closed(
    retrieval,
    reasoner,
) -> None:
    """The retry is one reminder, not a waiver."""
    retrieval()
    reasoner(
        [
            _need_more_patient_info("severity_score", citation="NOT-IN-EVIDENCE"),
            _need_more_patient_info("severity_score", citation="ALSO-NOT-IN-EVIDENCE"),
        ]
    )

    chat = Conversation()
    await chat.say("Tôi đau bụng từ sáng.")
    await chat.confirm_ehr()
    result = await chat.confirm_intake()

    assert result["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert result["handoff_reason"] == "QUESTION_NOT_GROUNDED_IN_AUTHORITY"
    assert result["current_esi_level"] is None


@pytest.mark.asyncio
async def test_a_handoff_reason_does_not_survive_into_a_later_turn(
    retrieval,
    reasoner,
) -> None:
    """An audit must not read a concluded turn as one that ended at the nurse."""
    retrieval()
    reasoner(
        [
            _need_more_patient_info("severity_score", citation="NOT-IN-EVIDENCE"),
            _need_more_patient_info("severity_score", citation="STILL-WRONG"),
            _propose(level=3),
        ]
    )

    chat = Conversation()
    await chat.say("Tôi đau bụng từ sáng.")
    await chat.confirm_ehr()
    stalled = await chat.confirm_intake()
    assert stalled["handoff_reason"] == "QUESTION_NOT_GROUNDED_IN_AUTHORITY"

    recovered = await chat.confirm_intake()
    assert recovered["decision_status"] == "PROPOSED"
    assert recovered["handoff_reason"] is None


# ---------------------------------------------------------------------------
# Case E -- no repeated confirmation message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_case_e_confirmation_prompt_does_not_repeat_verbatim() -> None:
    chat = Conversation()
    await chat.say("tôi bị sốt")
    await chat.confirm_ehr()
    # The agent characterises the fever before it offers anything to confirm,
    # so the review is reached by answering rather than by arriving.
    first = await chat.answer_until_review()
    assert first["decision_status"] == "AWAITING_PATIENT_CONFIRMATION"

    second = await chat.say("38.5 độ")
    assert second["decision_status"] == "AWAITING_PATIENT_CONFIRMATION"
    assert second["response"] != first["response"]
    assert "xác nhận" in second["response"]
    # The reprompt names what that turn actually took in, so the patient can
    # see they were heard rather than reading the same sentence again.
    assert "nhiệt độ" in second["response"]

    third = await chat.say("từ hôm qua")
    assert third["decision_status"] == "AWAITING_PATIENT_CONFIRMATION"
    assert "thời điểm bắt đầu" in third["response"]

    # And the answers were actually taken in, which is what the reprompt
    # wording promises the patient.
    blueprint = third["clinical_blueprint"]
    assert blueprint["onset_time"] == "hôm qua"
    assert blueprint["vital_signs"].get("temperature_c") == 38.5


@pytest.mark.asyncio
async def test_case_e_confirming_advances_the_conversation(
    retrieval,
    reasoner,
) -> None:
    retrieval()
    reasoner([_propose(level=3)])

    chat = Conversation()
    await chat.say("tôi bị sốt")
    await chat.confirm_ehr()
    advanced = await chat.confirm_intake()

    assert advanced["decision_status"] == "PROPOSED"
    assert advanced["workflow_phase"] != "PATIENT_CONFIRMATION"


# ---------------------------------------------------------------------------
# Case F -- deterministic safety stays monotonic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_case_f_configured_red_flag_locks_and_cannot_be_downgraded() -> None:
    chat = Conversation()

    emergency = await chat.say("méo miệng")

    assert emergency["is_red_flag"] is True
    assert emergency["red_flag_status"] == "CONFIRMED"
    assert emergency["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
    assert emergency["current_esi_level"] == 1

    # The contextual model said "no emergency" on every turn of this file. It
    # still cannot clear a configured rule.
    follow_up = await chat.say("chắc tôi ổn rồi, không sao đâu")
    assert follow_up["is_red_flag"] is True
    assert follow_up["red_flag_status"] == "CONFIRMED"
    assert follow_up["current_esi_level"] == 1


# ---------------------------------------------------------------------------
# Case G -- the acceptance case: an ordinary conversation reaches an ESI level
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_case_g_incomplete_conversation_reaches_a_cited_esi(
    retrieval,
    reasoner,
) -> None:
    """Start incomplete, ask, merge, retrieve, reason, conclude.

    This is the transcript the phase exists for. No red flag, no emergency
    shortcut: the agent works out what it is missing, asks for it, and only
    then commits to a level with citations behind it.
    """
    retriever = retrieval()
    scripted = reasoner(
        [
            _need_more_patient_info("severity_score"),
            _propose(level=3),
        ]
    )

    chat = Conversation(
        clinical_memory={
            "age": 34,
            "gender": "FEMALE",
            "chronic_conditions": [],
            "allergies": [],
            "daily_medications": [],
        }
    )

    opening = await chat.say("Tôi đau bụng từ sáng.")
    assert opening["clinical_blueprint"]["chief_complaint"] == ["đau bụng"]
    assert opening["current_esi_level"] is None

    await chat.confirm_ehr()

    asked = await chat.confirm_intake()
    assert asked["evidence_sufficiency_outcome"] == "NEED_MORE_PATIENT_INFO"
    assert asked["evidence_requested_fact"] == "severity_score"
    assert asked["current_esi_level"] is None

    answered = await chat.say("đau khoảng 7 trên 10")
    assert answered["clinical_blueprint"]["severity_score"] == 7

    concluded = await chat.confirm_intake()

    assert concluded["decision_status"] == "PROPOSED"
    assert concluded["current_esi_level"] == 3
    assert concluded["evidence_status"] == "SUFFICIENT"
    assert concluded["evidence_authority_status"] == "AUTHORIZED"
    assert concluded["evidence_sufficiency_outcome"] == "READY_FOR_REASONING"
    assert [item["id"] for item in concluded["turn_rag_citations"]] == [AUTHORITY_ID]
    assert concluded["matched_protocol_criteria"] == [AUTHORITY_CRITERION]
    assert concluded["sbar_report"]
    assert concluded["is_red_flag"] is not True
    assert INSUFFICIENT_EVIDENCE_HANDOFF_MESSAGE not in concluded["response"]

    # The severity the patient gave reached the retrieval query, so the second
    # search was not a repeat of the first. It arrives as the clinical word the
    # English corpus is written in rather than as the digit the patient typed:
    # the corpus says "severe abdominal pain", never "abdominal pain 7".
    assert len(retriever.authority_calls) == 2
    first_query = retriever.authority_calls[0]["query"]
    second_query = retriever.authority_calls[-1]["query"]
    assert "severe" in second_query
    assert "severe" not in first_query
    assert second_query != first_query
    # And the reasoner was told what had already been asked.
    assert "severity_score" in scripted.prompts[-1]


# ---------------------------------------------------------------------------
# Case H -- MIETIC absence does not block a conclusion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_case_h_no_case_support_still_concludes(retrieval, reasoner) -> None:
    retrieval(case_support=_no_cases())
    reasoner([_propose(level=4)])

    chat = Conversation()
    await chat.say("Tôi đau bụng từ sáng.")
    await chat.confirm_ehr()
    concluded = await chat.confirm_intake()

    assert concluded["case_support_evidence"] == []
    assert concluded["decision_status"] == "PROPOSED"
    assert concluded["current_esi_level"] == 4
    assert concluded["turn_rag_citations"]


# ---------------------------------------------------------------------------
# Case I -- an outage is an outage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_case_i_retrieval_outage_is_not_an_evidence_finding(
    retrieval,
    reasoner,
) -> None:
    retrieval([_authority_outage()])
    reasoner([])  # must never be consulted

    chat = Conversation()
    await chat.say("Tôi đau bụng từ sáng.")
    await chat.confirm_ehr()
    outage = await chat.confirm_intake()

    assert outage["decision_status"] == "RETRIEVAL_FAILURE"
    assert outage["evidence_status"] == "RETRIEVAL_FAILURE"
    assert outage["evidence_sufficiency_outcome"] == "RETRIEVAL_FAILURE"
    assert outage["current_esi_level"] is None
    assert "lỗi kỹ thuật" in outage["response"]
    assert INSUFFICIENT_EVIDENCE_HANDOFF_MESSAGE not in outage["response"]
    # The provider's own words never reach the patient.
    assert "connection refused" not in outage["response"]


# ---------------------------------------------------------------------------
# Missing evidence is refined, not handed off
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_authority_evidence_triggers_bounded_refinement(
    retrieval,
    reasoner,
) -> None:
    """A gap in the evidence is a reason to search again, once, within budget."""
    retriever = retrieval(
        [
            _authority_success(),
            # A narrowed search that surfaces something new while keeping the
            # document the reasoner will end up citing.
            RetrievalOutcome(
                status=RetrievalStatus.SUCCESS,
                channels=("dense",),
                items=(
                    _authority_item(AUTHORITY_ID, ["B"], ["SEVERE_PAIN"]),
                    _authority_item("ESI-AUTH-REFINED", ["B"], ["SEVERE_PAIN"]),
                ),
            ),
        ]
    )
    reasoner([_need_more_evidence(), _propose(level=3)])

    chat = Conversation()
    await chat.say("Tôi đau bụng từ sáng.")
    await chat.confirm_ehr()
    result = await chat.confirm_intake()

    assert len(retriever.authority_calls) == 2
    assert retriever.authority_calls[-1]["decision_point"] == "B"
    assert result["retrieval_refinement_count"] == 1
    assert result["decision_status"] == "PROPOSED"
    assert result["current_esi_level"] == 3


@pytest.mark.asyncio
async def test_exhausted_refinement_records_why_it_handed_off(
    retrieval,
    reasoner,
) -> None:
    """When refinement genuinely runs out, that is recorded as its own reason."""
    retrieval([_authority_success()])
    reasoner([_need_more_evidence()])

    chat = Conversation()
    await chat.say("Tôi đau bụng từ sáng.")
    await chat.confirm_ehr()
    result = await chat.confirm_intake()

    assert result["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert result["current_esi_level"] is None
    assert result["retrieval_refinement_stop_reason"] == "NO_NEW_EVIDENCE"
    assert result["handoff_reason"] == "REFINEMENT_NO_NEW_EVIDENCE"


@pytest.mark.asyncio
async def test_no_authority_candidates_is_reported_as_such(
    retrieval,
    reasoner,
) -> None:
    retrieval([_authority_empty()])
    reasoner([])

    chat = Conversation()
    await chat.say("Tôi đau bụng từ sáng.")
    await chat.confirm_ehr()
    result = await chat.confirm_intake()

    assert result["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert result["handoff_reason"] == "NO_AUTHORITY_EVIDENCE_RETRIEVED"
    assert result["current_esi_level"] is None


# ---------------------------------------------------------------------------
# State persistence between turns
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_facts_accepted_in_one_turn_are_still_there_several_turns_later(
    retrieval,
    reasoner,
) -> None:
    retrieval()
    reasoner([_propose(level=3)])

    chat = Conversation()
    await chat.say("Tôi đau bụng từ sáng.")
    await chat.say("đau khoảng 6 trên 10")
    await chat.say("có buồn nôn")
    await chat.confirm_ehr()
    final = await chat.confirm_intake()

    blueprint = final["clinical_blueprint"]
    assert "đau bụng" in blueprint["chief_complaint"]
    assert blueprint["onset_time"] == "sáng"
    assert blueprint["severity_score"] == 6
    assert "buồn nôn" in blueprint["associated_symptoms"]
    facts = final["canonical_state"]["facts"]
    assert "symptom.abdominal_pain" in facts
    assert "symptom.nausea" in facts


@pytest.mark.asyncio
async def test_free_text_vitals_reach_the_summary_the_patient_reviews() -> None:
    """A number the extractor understood must not disappear before the summary."""
    chat = Conversation()
    await chat.say("tôi bị sốt")
    await chat.confirm_ehr()
    turn = await chat.say("nhiệt độ 38.5")

    assert turn["clinical_blueprint"]["vital_signs"]["temperature_c"] == 38.5
    assert turn["vital_signs_status"] == "PATIENT_REPORTED"

    reviewed = await chat.answer_until_review()
    assert reviewed["intake_summary"]["vital_signs"]["temperature_c"] == 38.5


# ---------------------------------------------------------------------------
# Case J -- the whole thing, end to end
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_case_j_multi_symptom_conversation_reaches_a_cited_esi(
    retrieval,
    reasoner,
) -> None:
    """One ordinary conversation, first complaint to finalized SBAR.

    Two symptoms in the opening sentence, a third raised halfway through, no
    red flag and no emergency shortcut. The agent decides what to ask, decides
    when it has enough, puts the summary up itself, and only then retrieves and
    commits to a level with citations behind it.

    This is the acceptance test for the phase: every earlier assertion in this
    file covers one property, and this covers them holding together in a single
    conversation.
    """
    retriever = retrieval()
    reasoner([_propose(level=3)])

    chat = Conversation(
        clinical_memory={
            "age": 41,
            "gender": "FEMALE",
            "chronic_conditions": [],
            "allergies": [],
            "daily_medications": [],
        }
    )

    opening = await chat.say("Tôi bị đau đầu và buồn nôn")
    # Both complaints were understood, and the agent asked rather than
    # presenting a form to fill in.
    facts = set(opening["canonical_state"]["facts"])
    assert {"symptom.headache", "symptom.nausea"} <= facts
    assert opening["response_type"] != "INTAKE_REVIEW"

    await chat.confirm_ehr()

    asked_targets: list[str] = []
    seen_questions: list[str] = []

    async def answer(reply: str) -> dict[str, Any]:
        result = await chat.say(reply)
        target = (result.get("selected_action") or {}).get("target")
        if target:
            asked_targets.append(target)
        if result.get("response_type") in {"TEXT", "STRUCTURED_QUESTION"}:
            seen_questions.append(result["response"])
        return result

    await answer("Đau từ sáng nay, khoảng 6/10")
    # A third symptom arrives mid-conversation. It must join the picture, not
    # restart intake and not be dropped.
    mid = await answer("Tôi còn hơi chóng mặt nữa")
    assert "symptom.dizziness" in mid["canonical_state"]["facts"]
    assert mid["clinical_blueprint"]["severity_score"] == 6

    reviewed = await chat.answer_until_review(
        "Không, chưa bao giờ đau như vậy",
        "Không yếu tay chân, không nói khó",
        "Không sốt",
    )

    # The agent reached the checkpoint on its own; the patient was never asked
    # to judge whether the clinical information was sufficient.
    assert reviewed["response_type"] == "INTAKE_REVIEW"
    assert reviewed["decision_status"] == "AWAITING_PATIENT_CONFIRMATION"
    summary = reviewed["intake_summary"]
    assert "đau đầu" in " ".join(summary["chief_complaint"])
    assert summary["severity_score"] == 6

    # It got there by asking about the patient's own problems, each once.
    assert asked_targets
    assert all(
        target.startswith(("headache.", "nausea.", "dizziness.", "symptom.", "vital."))
        for target in asked_targets
    )
    assert len(seen_questions) == len(set(seen_questions))

    concluded = await chat.confirm_intake()

    assert concluded["decision_status"] == "PROPOSED"
    assert concluded["current_esi_level"] == 3
    assert concluded["evidence_authority_status"] == "AUTHORIZED"
    assert [item["id"] for item in concluded["turn_rag_citations"]] == [AUTHORITY_ID]
    assert concluded["sbar_report"]
    assert concluded["is_red_flag"] is not True

    # Retrieval was asked in clinical English built from canonical facts, not
    # handed the Vietnamese transcript.
    query = retriever.authority_calls[-1]["query"]
    assert "headache" in query
    assert "nausea" in query or "dizziness" in query
    assert "đau đầu" not in query


@pytest.mark.asyncio
async def test_clinical_answer_to_the_ehr_form_is_not_read_as_a_record_review() -> None:
    """"38.5 độ" is a temperature, not "my medical record is fine"."""
    chat = Conversation()
    await chat.say("tôi bị sốt")
    turn = await chat.say("38.5 độ")

    assert turn["clinical_memory_confirmation_status"] == "NOT_REVIEWED"
    assert turn["clinical_blueprint"]["vital_signs"]["temperature_c"] == 38.5


# ---------------------------------------------------------------------------
# Safety-sensitive input that is not an ESI presentation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crisis_expression_gets_safety_guidance_not_a_questionnaire() -> None:
    chat = Conversation()

    turn = await chat.say("tôi muốn tự tử")

    assert turn["intent"] == "SAFETY_CRISIS_SUPPORT"
    assert turn["response"] == CRISIS_SUPPORT_MESSAGE
    assert turn["response_type"] == "SAFETY_GUIDANCE"
    # Not a triage conclusion, and not an acuity claim.
    assert turn["current_esi_level"] is None
    assert turn["structured_question"] is None
    assert GENERIC_INTAKE_PROMPT not in turn["response"]
    assert INSUFFICIENT_EVIDENCE_HANDOFF_MESSAGE not in turn["response"]


@pytest.mark.asyncio
async def test_crisis_expression_does_not_loop_on_the_generic_message() -> None:
    chat = Conversation()
    first = await chat.say("tôi không muốn sống nữa")
    second = await chat.say("tôi không muốn sống nữa")

    for turn in (first, second):
        assert turn["intent"] == "SAFETY_CRISIS_SUPPORT"
        assert GENERIC_INTAKE_PROMPT not in turn["response"]
