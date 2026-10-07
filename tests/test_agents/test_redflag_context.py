"""Deterministic red-flag rules own the emergency safety lock.

These tests pin the monotonic architecture the fast screen must obey:

    configured rule match -> CONFIRMED lock -> contextual enrichment

The raw matcher remains recall-oriented. Once the detector accepts one of its
configured matches, however, a contextual model may enrich or escalate the
result but cannot clear it, lower its acuity, or resume ordinary intake.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.guardrails import screen_red_flag_candidate
from src.agents.nodes.contextual_emergency_detector import (
    ContextualEmergencyAssessment,
    assess_contextual_emergency_node,
)
from src.agents.nodes.redflag_detector import detect_redflag_node


class FakeValidator:
    """A contextual validator with a scripted verdict."""

    def __init__(self, result: ContextualEmergencyAssessment | Exception) -> None:
        self.result = result
        self.invoked = False

    def with_structured_output(self, _schema: Any) -> FakeValidator:
        return self

    async def ainvoke(self, _prompt: str) -> ContextualEmergencyAssessment:
        self.invoked = True
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class UnavailableValidator:
    """A model object that cannot do structured output at all."""


def _verdict(
    context_type: str,
    *,
    current: bool,
    confidence: float = 0.95,
    category: str = "CARDIAC",
) -> ContextualEmergencyAssessment:
    return ContextualEmergencyAssessment(
        context_type=context_type,
        is_current_personal_event=current,
        is_time_critical_emergency=current,
        confidence=confidence,
        risk_category=category,
        observed_signals=["đau thắt ngực"],
        evidence_summary="Kết luận ngữ cảnh của bộ kiểm chứng.",
    )


def _use(monkeypatch: pytest.MonkeyPatch, validator: Any) -> None:
    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: validator,
    )


async def _screen_then_validate(
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    validator: Any,
) -> dict[str, Any]:
    """Run the real two-stage path: fast screen, then contextual resolution."""
    state: dict[str, Any] = {"query": query}
    state.update(await detect_redflag_node(state))
    _use(monkeypatch, validator)
    state.update(await assess_contextual_emergency_node(state))
    return state


# --------------------------------------------------------------------------
# A configured positive rule creates the lock before model work.
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "query",
    [
        "Tôi đang đau thắt ngực dữ dội",
        "Tuần trước tôi từng bị đau thắt ngực",
        "Bố tôi từng bị đau thắt ngực",
        "Nếu bị đau thắt ngực thì có nguy hiểm không?",
        "Tôi hoàn toàn không hề bị đau thắt ngực",
    ],
)
@pytest.mark.asyncio
async def test_positive_screen_match_creates_a_deterministic_lock(query: str) -> None:
    update = await detect_redflag_node({"query": query})
    assert update["red_flag_status"] == "CONFIRMED"
    assert update["is_red_flag"] is True
    assert update["current_esi_level"] == 2
    assert update["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
    assert update["next_step"] == "emergency_escalated"


@pytest.mark.asyncio
async def test_screen_stays_quiet_on_unrelated_text() -> None:
    update = await detect_redflag_node({"query": "Hôm nay trời đẹp quá"})
    assert update["red_flag_status"] == "NO_CANDIDATE"
    assert update["is_red_flag"] is False


# --------------------------------------------------------------------------
# Part C battery: same keyword, different meaning, different resolution.
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_current_actual_event_is_confirmed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = await _screen_then_validate(
        monkeypatch,
        "Tôi đang đau thắt ngực dữ dội",
        FakeValidator(_verdict("CURRENT_PERSONAL_EVENT", current=True)),
    )
    assert state["red_flag_status"] == "CONFIRMED"
    assert state["is_red_flag"] is True
    assert state["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
    assert state["semantic_emergency_status"] == "ESCALATED"
    assert state["current_esi_level"] == 2
    assert "115" in state["response"]


@pytest.mark.parametrize(
    ("query", "context_type"),
    [
        ("Tuần trước tôi từng bị đau thắt ngực", "HISTORICAL_OR_QUOTED"),
        ("Hôm qua tôi đau thắt ngực nhưng giờ hết rồi", "HISTORICAL_OR_QUOTED"),
        ("Bố tôi từng bị đau thắt ngực", "HISTORICAL_OR_QUOTED"),
        ("Nếu bị đau thắt ngực thì có nguy hiểm không?", "EDUCATIONAL_OR_HYPOTHETICAL"),
        ("Tôi hoàn toàn không hề bị đau thắt ngực", "HISTORICAL_OR_QUOTED"),
    ],
)
@pytest.mark.asyncio
async def test_non_current_context_cannot_clear_the_deterministic_lock(
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    context_type: str,
) -> None:
    """A negative semantic reading is recorded without lowering rule authority."""
    state = await _screen_then_validate(
        monkeypatch,
        query,
        FakeValidator(_verdict(context_type, current=False)),
    )
    assert state["red_flag_status"] == "CONFIRMED"
    assert state["is_red_flag"] is True
    assert state["current_esi_level"] == 2
    assert state["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
    assert state["semantic_emergency_status"] == "CLEAR"
    assert state["next_step"] == "emergency_escalated"


@pytest.mark.asyncio
async def test_the_same_rule_match_stays_locked_across_semantic_verdicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Semantic context remains observable but cannot reverse rule authority."""
    now = await _screen_then_validate(
        monkeypatch,
        "Tôi đang đau thắt ngực dữ dội",
        FakeValidator(_verdict("CURRENT_PERSONAL_EVENT", current=True)),
    )
    past = await _screen_then_validate(
        monkeypatch,
        "Tuần trước tôi từng bị đau thắt ngực",
        FakeValidator(_verdict("HISTORICAL_OR_QUOTED", current=False)),
    )
    assert now["red_flag_candidate_reason"] == past["red_flag_candidate_reason"]
    assert now["is_red_flag"] is True
    assert past["is_red_flag"] is True
    assert now["semantic_emergency_status"] == "ESCALATED"
    assert past["semantic_emergency_status"] == "CLEAR"


# --------------------------------------------------------------------------
# Ambiguity from the model cannot weaken a deterministic positive.
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unclear_context_preserves_the_deterministic_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = await _screen_then_validate(
        monkeypatch,
        "đau thắt ngực",
        FakeValidator(_verdict("UNCLEAR", current=False, confidence=0.4)),
    )
    assert state["red_flag_status"] == "CONFIRMED"
    assert state["is_red_flag"] is True
    assert state["current_esi_level"] == 2
    assert state["semantic_emergency_status"] == "INCONCLUSIVE"
    assert state["response_type"] == "EMERGENCY"
    assert state["next_step"] == "emergency_escalated"
    assert "115" in state["response"]


@pytest.mark.asyncio
async def test_low_confidence_verdict_cannot_downgrade_rule_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = await _screen_then_validate(
        monkeypatch,
        "đau thắt ngực",
        FakeValidator(
            _verdict("CURRENT_PERSONAL_EVENT", current=True, confidence=0.10)
        ),
    )
    assert state["red_flag_status"] == "CONFIRMED"
    assert state["is_red_flag"] is True
    assert state["semantic_emergency_status"] == "INCONCLUSIVE"


# --------------------------------------------------------------------------
# Fail-safe: model failure cannot alter an existing deterministic lock.
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "validator",
    [
        FakeValidator(TimeoutError()),
        FakeValidator(RuntimeError("provider down")),
        UnavailableValidator(),
    ],
)
@pytest.mark.asyncio
async def test_validator_failure_preserves_the_deterministic_lock(
    monkeypatch: pytest.MonkeyPatch,
    validator: Any,
) -> None:
    state = await _screen_then_validate(
        monkeypatch,
        "Tôi đang đau thắt ngực dữ dội",
        validator,
    )
    assert state["red_flag_status"] == "CONFIRMED"
    assert state["is_red_flag"] is True
    assert state["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
    assert state["semantic_emergency_status"] == "UNAVAILABLE"
    assert state["red_flag_resolution_reason"]
    assert "115" in state["response"]


@pytest.mark.asyncio
async def test_validator_failure_without_a_candidate_is_not_an_emergency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only an open candidate justifies precautionary escalation."""
    state = await _screen_then_validate(
        monkeypatch,
        "Tôi hơi mệt trong người",
        FakeValidator(TimeoutError()),
    )
    assert state["red_flag_status"] == "NO_CANDIDATE"
    assert state.get("is_red_flag") is False
    assert state["next_step"] == "intent_classifier"


@pytest.mark.asyncio
async def test_model_outage_preserves_the_rule_acuity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = await _screen_then_validate(
        monkeypatch,
        "Tôi không thở nổi",
        FakeValidator(TimeoutError()),
    )
    assert state["red_flag_status"] == "CONFIRMED"
    assert state["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
    assert state["current_esi_level"] == state["red_flag_candidate_esi"] == 1


# --------------------------------------------------------------------------
# Part G: normalization must not lose a candidate.
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "query",
    [
        "toi dau nguc du doi va kho tho",
        "tôi đau ngựcj dữ dội quá",
        "toi bi dau that nguc",
        "TÔI ĐAU THẮT NGỰC",
    ],
)
def test_unaccented_and_mistyped_input_still_raises_a_candidate(query: str) -> None:
    assert screen_red_flag_candidate(query) is not None


def test_normalization_does_not_invent_certainty() -> None:
    """Folding raises a candidate; it never sets an ESI or confirms anything."""
    candidate = screen_red_flag_candidate("toi dau nguc du doi")
    assert candidate is not None
    assert candidate["status"] == "CANDIDATE"
    assert "action_guidance" not in candidate


# --------------------------------------------------------------------------
# The model may resolve context, never downgrade acuity.
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_model_cannot_downgrade_a_current_event_it_deems_mild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Acuity belongs to clinical policy, not to the model's severity opinion."""
    mild_but_current = ContextualEmergencyAssessment(
        context_type="CURRENT_PERSONAL_EVENT",
        is_current_personal_event=True,
        is_time_critical_emergency=False,  # model thinks it is not serious
        confidence=0.97,
        risk_category="NONE",
        observed_signals=["đau ngực"],
        evidence_summary="Model judged this mild.",
    )
    state = await _screen_then_validate(
        monkeypatch,
        "Tôi đang đau thắt ngực dữ dội",
        FakeValidator(mild_but_current),
    )
    assert state["red_flag_status"] == "CONFIRMED"
    assert state["is_red_flag"] is True
    assert state["current_esi_level"] == 2


# --------------------------------------------------------------------------
# An open candidate survives across turns until it is actually resolved.
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unresolved_candidate_is_not_dropped_on_the_next_turn() -> None:
    """The safety answer carries no keyword, so re-screening alone would lose it."""
    pending = {
        "query": "Đang xảy ra với tôi ngay bây giờ",
        "red_flag_status": "UNCERTAIN",
        "red_flag_candidate_reason": "đau thắt ngực",
        "red_flag_candidate_esi": 2,
        "safety_rule_id": "REFLEX_CARDIAC_CHEST_PAIN_V1",
    }
    update = await detect_redflag_node(pending)

    assert update["red_flag_status"] == "CANDIDATE"
    assert update["red_flag_candidate_reason"] == "đau thắt ngực"
    assert update["red_flag_candidate_esi"] == 2
    assert update["is_red_flag"] is False


@pytest.mark.asyncio
async def test_answering_the_safety_question_can_confirm_the_carried_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A legacy open candidate remains resolvable when the patient confirms it."""
    turn_one = {
        "red_flag_status": "UNCERTAIN",
        "red_flag_candidate_reason": "đau thắt ngực",
        "red_flag_candidate_esi": 2,
        "safety_rule_id": "REFLEX_CARDIAC_CHEST_PAIN_V1",
    }

    turn_two = dict(turn_one)
    turn_two["query"] = "Đang xảy ra với tôi ngay bây giờ"
    turn_two.update(await detect_redflag_node(turn_two))
    _use(monkeypatch, FakeValidator(_verdict("CURRENT_PERSONAL_EVENT", current=True)))
    turn_two.update(await assess_contextual_emergency_node(turn_two))

    assert turn_two["red_flag_status"] == "CONFIRMED"
    assert turn_two["is_red_flag"] is True
    assert turn_two["current_esi_level"] == 2


@pytest.mark.asyncio
async def test_answering_the_safety_question_can_also_clear_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    turn_one = {
        "red_flag_status": "UNCERTAIN",
        "red_flag_candidate_reason": "đau thắt ngực",
        "red_flag_candidate_esi": 2,
        "safety_rule_id": "REFLEX_CARDIAC_CHEST_PAIN_V1",
    }
    turn_two = dict(turn_one)
    turn_two["query"] = "Tôi hỏi giúp người khác"
    turn_two.update(await detect_redflag_node(turn_two))
    _use(monkeypatch, FakeValidator(_verdict("HISTORICAL_OR_QUOTED", current=False)))
    turn_two.update(await assess_contextual_emergency_node(turn_two))

    assert turn_two["red_flag_status"] == "NOT_CONFIRMED"
    assert turn_two["is_red_flag"] is False
    # The safety question must not linger as a clinical intake question.
    assert turn_two["active_question"] is None
    assert turn_two["structured_question"] is None


@pytest.mark.asyncio
async def test_carried_candidate_still_fails_safe_if_the_validator_dies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    turn_one = {
        "red_flag_status": "UNCERTAIN",
        "red_flag_candidate_reason": "đau thắt ngực",
        "red_flag_candidate_esi": 2,
        "safety_rule_id": "REFLEX_CARDIAC_CHEST_PAIN_V1",
    }
    turn_two = dict(turn_one)
    turn_two["query"] = "Đang xảy ra với tôi ngay bây giờ"
    turn_two.update(await detect_redflag_node(turn_two))
    _use(monkeypatch, FakeValidator(TimeoutError()))
    turn_two.update(await assess_contextual_emergency_node(turn_two))

    assert turn_two["red_flag_status"] == "SAFETY_FALLBACK"
    assert turn_two["is_red_flag"] is True
