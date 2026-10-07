"""Three bands, not two: escalate, watch, or ask.

The system used to have only "this is an emergency" and "this is nothing", so
every worrying word fell into the first. Typing "khó thở" locked the session;
after the first fix it instead triggered an emergency questionnaire -- which
still fired on "khó thở nhẹ thôi" and "mấy hôm nay tôi hay khó thở", where the
patient had *already answered* the acute question.

The missing band is what a clinician actually does with an unqualified symptom:
note it, keep taking the history, and act the moment severity, onset or a second
sign makes it real. That is MONITORING. It is not terminal, it carries across
turns, and it is re-tested after extraction against the canonical state -- which
is where the deciding fact ("đau 9 trên 10") actually lands.

What must not change, and is asserted here: anything the deterministic screen
matches still escalates, and accumulated evidence still escalates. A calmer
system that misses an emergency is not an improvement.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.canonical_state import CanonicalPatientState
from src.agents.guardrails import screen_red_flag_candidate
from src.agents.nodes.contextual_emergency_detector import (
    SEVERE_PAIN_THRESHOLD,
    accumulated_evidence_is_sufficient,
    emergency_evidence_is_sufficient,
    reassess_monitored_concern,
)
from src.agents.nodes.redflag_detector import detect_redflag_node
from src.agents.state import RedFlagStatus


def _state_with(**facts: Any) -> dict[str, Any]:
    """A turn state whose canonical facts are already extracted."""
    canonical = CanonicalPatientState()
    for key, value in facts.items():
        canonical.record(
            key.replace("__", "."),
            value,
            temporal="CURRENT",
            turn_id="t1",
        )
    return {"canonical_state": canonical.to_dict()}


# --------------------------------------------------------------------------
# The band exists and is not terminal
# --------------------------------------------------------------------------

def test_monitoring_is_a_declared_lifecycle_state() -> None:
    from typing import get_args

    assert "MONITORING" in get_args(RedFlagStatus)


def test_monitoring_does_not_stop_the_turn() -> None:
    """The whole point: the consultation continues."""
    from src.agents.deepagent_runtime.tools import turn_is_terminal

    assert turn_is_terminal({"red_flag_status": "MONITORING"}) is False
    # While the states that must stop it still do.
    assert turn_is_terminal({"red_flag_status": "UNCERTAIN"}) is True
    assert turn_is_terminal({"is_red_flag": True}) is True


def test_monitoring_never_carries_an_esi_or_the_red_flag() -> None:
    """A watch note is not a clinical finding."""
    from src.agents.nodes.contextual_emergency_detector import _monitoring_update

    update = _monitoring_update(
        {},
        reason="theo dõi",
        confidence=0.8,
        context_type="CURRENT_PERSONAL_EVENT",
        signals=["khó thở"],
        candidate_reason="khó thở",
    )

    assert update["red_flag_status"] == "MONITORING"
    assert update["is_red_flag"] is False
    assert update["current_esi_level"] is None
    assert update["next_step"] == "intent_classifier"


# --------------------------------------------------------------------------
# A watch survives between turns
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_watch_is_carried_to_the_next_turn() -> None:
    """The escalating answer arrives with no keyword in it at all."""
    carried = await detect_redflag_node({
        "query": "đau khoảng 9 trên 10",
        "red_flag_status": "MONITORING",
        "red_flag_candidate_reason": "khó thở",
        "red_flag_candidate_esi": 2,
    })

    assert carried["red_flag_status"] == "MONITORING"
    assert carried["red_flag_candidate_reason"] == "khó thở"
    assert carried["is_red_flag"] is False


@pytest.mark.asyncio
async def test_a_watch_is_not_promoted_to_a_screen_candidate() -> None:
    """CANDIDATE goes to the branch that confirms on currency alone.

    Promoting a watch there would escalate "khó thở" then "đau 3 trên 10" on
    the strength of the symptom merely still being present.
    """
    carried = await detect_redflag_node({
        "query": "đau khoảng 3 trên 10",
        "red_flag_status": "MONITORING",
        "red_flag_candidate_reason": "khó thở",
    })

    assert carried["red_flag_status"] != "CANDIDATE"


@pytest.mark.asyncio
async def test_an_uncertain_concern_is_still_carried_as_a_candidate() -> None:
    """The pre-existing behaviour is untouched."""
    carried = await detect_redflag_node({
        "query": "Đang xảy ra với tôi ngay bây giờ",
        "red_flag_status": "UNCERTAIN",
        "red_flag_candidate_reason": "đau ngực dữ dội",
    })

    assert carried["red_flag_status"] == "CANDIDATE"


# --------------------------------------------------------------------------
# Accumulated evidence escalates
# --------------------------------------------------------------------------

def test_severe_pain_on_an_open_watch_is_sufficient() -> None:
    """AHRQ ESI Decision Point B: severe pain is a high-risk situation."""
    state = {
        **_state_with(severity_score=SEVERE_PAIN_THRESHOLD),
        "red_flag_status": "MONITORING",
    }

    assert accumulated_evidence_is_sufficient(state) is True


def test_mild_pain_on_an_open_watch_is_not_sufficient() -> None:
    state = {
        **_state_with(severity_score=3),
        "red_flag_status": "MONITORING",
    }

    assert accumulated_evidence_is_sufficient(state) is False


def test_two_symptoms_accumulated_over_turns_are_sufficient() -> None:
    """Saying it in one breath or two changes nothing clinically."""
    state = {
        **_state_with(symptom__chest_pain=True, symptom__dyspnea=True),
        "red_flag_status": "MONITORING",
    }

    assert accumulated_evidence_is_sufficient(state) is True


def test_accumulated_evidence_is_ignored_without_an_open_concern() -> None:
    """Severity alone is not an emergency; it needs something to be severe about."""
    state = {
        **_state_with(severity_score=9),
        "red_flag_status": "NO_CANDIDATE",
    }

    assert accumulated_evidence_is_sufficient(state) is False


def test_the_post_intake_recheck_escalates_a_watch() -> None:
    state = {
        **_state_with(severity_score=9),
        "red_flag_status": "MONITORING",
        "red_flag_candidate_reason": "khó thở",
        "red_flag_candidate_esi": 2,
    }

    escalation = reassess_monitored_concern(state)

    assert escalation is not None
    assert escalation["red_flag_status"] == "CONFIRMED"
    assert escalation["is_red_flag"] is True
    assert escalation["current_esi_level"] == 2


def test_the_post_intake_recheck_is_silent_when_nothing_changed() -> None:
    state = {
        **_state_with(severity_score=2),
        "red_flag_status": "MONITORING",
    }

    assert reassess_monitored_concern(state) is None


@pytest.mark.parametrize(
    "status", ["NO_CANDIDATE", "CANDIDATE", "CONFIRMED", "NOT_CONFIRMED"],
)
def test_the_recheck_only_acts_on_a_watch(status: str) -> None:
    """It must not re-decide states other layers already own."""
    state = {
        **_state_with(severity_score=9),
        "red_flag_status": status,
    }

    assert reassess_monitored_concern(state) is None


def test_the_recheck_needs_no_model() -> None:
    """Deterministic policy on canonical facts, so it cannot be talked past."""
    import inspect

    source = inspect.getsource(reassess_monitored_concern)
    for forbidden in ("llm", "ainvoke", "get_deepagent_llm", "prompt"):
        assert forbidden not in source.lower()


# --------------------------------------------------------------------------
# The deterministic screen is untouched
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "message",
    [
        "khó thở dữ dội",
        "không thở nổi",
        "bất tỉnh",
        "co giật liên hồi",
        "chảy máu không cầm",
        "đau thắt ngực",
        "tôi sắp chết",
        "máu phun thành tia",
    ],
)
def test_high_specificity_phrases_still_raise_a_candidate(message: str) -> None:
    candidate = screen_red_flag_candidate(message)

    assert candidate is not None, message
    assert candidate["status"] == "CANDIDATE"


@pytest.mark.parametrize(
    "message",
    [
        "tôi bị gãy chân chảy nhiều máu xương lòi ra",
        "tôi bị gãy chân, máu chảy rất nhiều, xương trắng lòi ra",
    ],
)
def test_open_fracture_with_heavy_bleeding_is_esi_1(message: str) -> None:
    candidate = screen_red_flag_candidate(message)

    assert candidate is not None, message
    assert candidate["candidate_esi"] == 1
    assert candidate["safety_rule_id"] == "REFLEX_OPEN_FRACTURE_HEMORRHAGE_V1"
    assert candidate["candidate_source"] == "DETERMINISTIC_REFLEX"


def test_open_fracture_without_heavy_bleeding_is_esi_2() -> None:
    candidate = screen_red_flag_candidate("tôi bị gãy xương hở lòi đầu xương")

    assert candidate is not None
    assert candidate["candidate_esi"] == 2
    assert candidate["safety_rule_id"] == "REFLEX_OPEN_FRACTURE_V1"


@pytest.mark.parametrize(
    ("message", "rule_id"),
    [
        ("tôi ngừng thở rồi", "REFLEX_CARDIORESPIRATORY_ARREST_V1"),
        ("bệnh nhân không còn thở", "REFLEX_CARDIORESPIRATORY_ARREST_V1"),
        ("không bắt được mạch", "REFLEX_CARDIORESPIRATORY_ARREST_V1"),
        ("tim ngừng đập", "REFLEX_CARDIORESPIRATORY_ARREST_V1"),
        ("đang phải ép tim", "REFLEX_CARDIORESPIRATORY_ARREST_V1"),
        ("bệnh nhân phải đặt nội khí quản", "REFLEX_LIFESAVING_INTERVENTION_V1"),
        ("đang phải bóp bóng", "REFLEX_LIFESAVING_INTERVENTION_V1"),
        ("tôi tím tái không thở được", "REFLEX_RESPIRATORY_FAILURE_V1"),
        ("bệnh nhân thở ngáp cá", "REFLEX_RESPIRATORY_FAILURE_V1"),
        ("gọi không tỉnh lay không dậy", "REFLEX_UNRESPONSIVE_AVPU_V1"),
        ("AVPU U", "REFLEX_UNRESPONSIVE_AVPU_V1"),
        ("tay chân lạnh toát lơ mơ tụt huyết áp", "REFLEX_HEMODYNAMIC_SHOCK_V1"),
        ("co giật hơn 5 phút không dừng", "REFLEX_STATUS_SEIZURE_V1"),
        ("co giật liên tục không tỉnh lại", "REFLEX_STATUS_SEIZURE_V1"),
        ("máu vọt phun phọt thành vòi", "REFLEX_MAJOR_EXTERNAL_HEMORRHAGE_V1"),
        ("phải garo cầm máu", "REFLEX_MAJOR_EXTERNAL_HEMORRHAGE_V1"),
        ("bỏng mặt cổ sau cháy, khàn tiếng thở khò khè", "REFLEX_AIRWAY_BURN_INHALATION_V1"),
        ("bỏng độ 3 diện rộng trên 20% cơ thể", "REFLEX_AIRWAY_BURN_INHALATION_V1"),
        ("ăn tôm xong môi lưỡi sưng nghẹt cổ thở không ra", "REFLEX_ANAPHYLAXIS_AIRWAY_SHOCK_V1"),
        ("bị ong đốt xong ngất lịm tụt huyết áp", "REFLEX_ANAPHYLAXIS_AIRWAY_SHOCK_V1"),
        ("chích ma túy quá liều thở chậm tím tái đồng tử co nhỏ", "REFLEX_TOXIC_OVERDOSE_RESPIRATORY_FAILURE_V1"),
        ("uống thuốc trừ sâu sùi bọt mép thở yếu", "REFLEX_TOXIC_OVERDOSE_RESPIRATORY_FAILURE_V1"),
        ("sau sinh băng huyết máu chảy ồ ạt", "REFLEX_OBSTETRIC_HEMORRHAGE_SHOCK_V1"),
    ],
)
def test_immediate_lifesaving_patterns_are_esi_1(message: str, rule_id: str) -> None:
    candidate = screen_red_flag_candidate(message)

    assert candidate is not None, message
    assert candidate["candidate_esi"] == 1
    assert candidate["safety_rule_id"] == rule_id


def test_severe_hypoglycemia_vital_is_esi_1() -> None:
    candidate = screen_red_flag_candidate("đường huyết 45 mg/dL vã mồ hôi lịm đi")

    assert candidate is not None
    assert candidate["candidate_esi"] == 1
    assert candidate["safety_rule_id"] == "REFLEX_PATIENT_REPORTED_VITALS_V1"


@pytest.mark.parametrize(
    "message",
    [
        "không đau thắt ngực",
        "không có chảy máu không cầm",
        "tôi không bị bất tỉnh",
        "không co giật liên hồi",
        "Không thở nổi nghĩa là gì?",
    ],
)
def test_negated_or_educational_red_flag_mentions_do_not_trigger(message: str) -> None:
    assert screen_red_flag_candidate(message) is None


@pytest.mark.parametrize(
    "message",
    ["khó thở dữ dội", "không thở được", "tôi tím tái", "tôi sắp chết"],
)
def test_qualified_wording_is_sufficient_on_its_own(message: str) -> None:
    assert emergency_evidence_is_sufficient(message, []) is True


# --------------------------------------------------------------------------
# Already-answered context does not get interrogated
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "message",
    [
        "khó thở nhẹ thôi",
        "tôi hơi khó thở",
        "mấy hôm nay tôi hay khó thở",
        "khó thở vài ngày rồi",
        "thỉnh thoảng tôi bị khó thở",
        "tôi bị khó thở khi leo cầu thang",
        "khó thở khi gắng sức",
        "hay bị đau đầu mãn tính",
    ],
)
def test_deescalating_context_is_recognised(message: str) -> None:
    from src.agents.nodes.contextual_emergency_detector import (
        _has_deescalating_context,
    )

    assert _has_deescalating_context(message) is True


@pytest.mark.parametrize(
    "message",
    ["khó thở", "đau ngực", "tôi bị đau bụng", "khó thở dữ dội"],
)
def test_unqualified_or_severe_wording_is_not_deescalating(message: str) -> None:
    from src.agents.nodes.contextual_emergency_detector import (
        _has_deescalating_context,
    )

    assert _has_deescalating_context(message) is False


def test_deescalation_is_accent_insensitive() -> None:
    from src.agents.nodes.contextual_emergency_detector import (
        _has_deescalating_context,
    )

    assert _has_deescalating_context("may hom nay hay bi kho tho") is True
