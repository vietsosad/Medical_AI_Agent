"""What the patient reads, and what counts as them contradicting themselves.

Three defects reported from a live session, all from one message -- "đau bụng
và buồn ỉa":

1. The reply asked the patient to reconcile a conflict about
   "complaint.abdominal pain": an internal key, in English, in a Vietnamese
   clinical question.
2. There was no conflict. Two extractions of the *same* complaint in the *same
   turn* were recorded as the patient contradicting themselves.
3. "buồn ỉa" extracted nothing at all, so a reported symptom simply vanished.

The first is a trust problem: a patient who sees a leaked identifier stops
believing the rest of the sentence. The second is worse -- being asked to
resolve a disagreement you never had is disorienting, and it spends the
credibility that a *real* clarification later depends on.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.canonical_state import CanonicalPatientState, is_descriptive_key
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.deepagent_runtime.tools import TurnContext, update_intake_phase
from src.agents.nodes.fact_extraction import (
    SYMPTOM_DISPLAY_VI,
    describe_fact_key,
    extract_symptom_facts,
    symptom_key_for_phrase,
)
from src.agents.nodes.question_engine import plan_next_question

BASE: dict[str, Any] = {
    "intent": "TRIAGE_NEW_SYMPTOM",
    "clinical_memory_confirmation_status": "CONFIRMED",
    "vital_signs_status": "REVIEWED",
    "patient_id": "patient-lang",
    "session_id": "session-lang",
}

# Anything that would betray an internal identifier to a patient.
_LEAK_MARKERS = ("complaint.", "symptom.", "associated.", "vital.", "_")


async def _turn(state: dict[str, Any], query: str, turn_id: str = "t1") -> dict[str, Any]:
    context = TurnContext({**BASE, **state, "query": query, "current_turn_id": turn_id})
    context.called_tools.update({"assess_contextual_emergency", "classify_request"})
    await update_intake_phase(context)
    return context.state


# --------------------------------------------------------------------------
# No internal identifier ever reaches the patient
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "key",
    [
        "complaint.abdominal_pain",
        "symptom.chest_pain",
        "symptom.diarrhea",
        "associated.nausea",
        "onset_time",
        "severity_score",
        "vital.temperature_c",
        # Unrecognised keys must degrade to a phrase, never to the raw key.
        "complaint.dau_khoang_7_tren_10",
        "weird.internal.key",
        "",
    ],
)
def test_a_fact_key_never_renders_as_itself(key: str) -> None:
    label = describe_fact_key(key)

    assert label
    assert key not in label or not key
    for marker in _LEAK_MARKERS:
        assert marker not in label, f"{key} leaked {marker!r} via {label!r}"


def test_every_canonical_symptom_has_vietnamese_wording() -> None:
    """A symptom the extractor can name must be a symptom we can say."""
    from src.agents.nodes.fact_extraction import SYMPTOM_LEXICON

    canonical = {key for _term, key in SYMPTOM_LEXICON}
    missing = canonical - set(SYMPTOM_DISPLAY_VI)

    assert not missing, f"no Vietnamese wording for: {sorted(missing)}"


@pytest.mark.parametrize(
    "key",
    ["complaint.abdominal_pain", "onset_time", "severity_score", "complaint.junk_slug"],
)
def test_the_clarification_question_is_readable_vietnamese(key: str) -> None:
    question = plan_next_question({}, [f"contradiction:{key}"], {})

    for marker in _LEAK_MARKERS:
        assert marker not in question.text, f"leaked {marker!r}: {question.text}"
    # The field routed back to the engine may carry the key; the text may not.
    assert "abdominal" not in question.text
    assert "complaint" not in question.text


def test_the_specific_reported_sentence_is_clean() -> None:
    """The exact string a patient was shown must not be producible again."""
    question = plan_next_question(
        {}, ["contradiction:complaint.abdominal_pain"], {}
    )

    assert "complaint.abdominal pain" not in question.text
    assert "đau bụng" in question.text


# --------------------------------------------------------------------------
# One turn cannot contradict itself
# --------------------------------------------------------------------------

def test_two_readings_of_one_utterance_are_a_disagreement_not_a_contradiction() -> None:
    state = CanonicalPatientState()
    state.record("severity_score", 7, temporal="CURRENT", turn_id="t1")
    state.record("severity_score", 8, temporal="CURRENT", turn_id="t1")

    assert state.unresolved_contradictions() == []
    assert len(state.extraction_disagreements) == 1
    assert state.extraction_disagreements[0].fact_key == "severity_score"


def test_two_turns_still_contradict_when_the_value_really_changes() -> None:
    """The relaxation must not disarm real contradiction detection."""
    state = CanonicalPatientState()
    state.record("severity_score", 7, temporal="CURRENT", turn_id="t1")
    state.record("severity_score", 3, temporal="CURRENT", turn_id="t2")

    unresolved = state.unresolved_contradictions()
    assert len(unresolved) == 1
    assert unresolved[0].key == "severity_score"


def test_a_complaint_wording_never_contradicts_another_wording() -> None:
    """"đau bụng" and "đau bụng buồn ỉa" describe one complaint, not two claims."""
    state = CanonicalPatientState()
    state.record("complaint.abdominal_pain", "đau bụng",
                 temporal="UNKNOWN_TIME", turn_id="t1")
    state.record("complaint.abdominal_pain", "đau bụng buồn ỉa",
                 temporal="UNKNOWN_TIME", turn_id="t2")

    assert state.unresolved_contradictions() == []


def test_descriptive_keys_are_identified_by_prefix() -> None:
    assert is_descriptive_key("complaint.abdominal_pain")
    assert not is_descriptive_key("symptom.abdominal_pain")
    assert not is_descriptive_key("severity_score")


@pytest.mark.asyncio
async def test_the_reported_message_asks_a_normal_question() -> None:
    """End to end: the message that broke, through the real runtime."""
    state = await _turn({}, "đau bụng và buồn ỉa")

    assert not (state.get("unresolved_contradictions") or []), \
        "a single message cannot be a patient contradiction"

    response = str(state.get("response") or "")
    assert response
    for marker in _LEAK_MARKERS:
        assert marker not in response, f"leaked {marker!r}: {response}"


# --------------------------------------------------------------------------
# Everyday wording is actually understood
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("buồn ỉa", "diarrhea"),
        ("mót ỉa", "diarrhea"),
        ("đi ngoài lỏng", "diarrhea"),
        ("đi cầu lỏng", "diarrhea"),
        ("đau bao tử", "abdominal_pain"),
        ("đau dạ dày", "abdominal_pain"),
        ("đau quặn bụng", "abdominal_pain"),
        ("nhức đầu", "headache"),
        ("xây xẩm", "lightheadedness"),
        ("rát họng", "sore_throat"),
        ("ngứa họng", "sore_throat"),
        ("hụt hơi", "dyspnea"),
        ("thở dốc", "dyspnea"),
        ("buồn ói", "nausea"),
        ("ngất xỉu", "syncope"),
    ],
)
def test_everyday_wording_maps_to_a_canonical_symptom(
    phrase: str, expected: str
) -> None:
    assert symptom_key_for_phrase(phrase) == expected


@pytest.mark.parametrize(
    "sentence",
    [
        "Tôi đi ngoài đường bị ngã",
        "Trời ơi bác sĩ ơi",
        "Cảm ơn bác sĩ nhiều",
        "Tôi muốn hỏi về lịch khám",
        "Hôm nay trời mưa quá",
    ],
)
def test_ordinary_sentences_do_not_manufacture_symptoms(sentence: str) -> None:
    """Recall must not be bought with invented patient-reported facts."""
    assert extract_symptom_facts(sentence) == []


def test_walking_down_the_street_is_not_diarrhoea() -> None:
    """The collocation guard, stated as the thing it actually prevents."""
    assert symptom_key_for_phrase("đi ngoài đường") is None
    assert symptom_key_for_phrase("đi ngoài lỏng") == "diarrhea"


@pytest.mark.asyncio
async def test_buon_ia_is_recorded_as_a_symptom() -> None:
    state = await _turn({}, "đau bụng và buồn ỉa")
    view = ClinicalStateView(
        CanonicalPatientState.from_dict(state.get("canonical_state") or {})
    )

    assert view.is_present("symptom.abdominal_pain")
    assert view.is_present("symptom.diarrhea")


# --------------------------------------------------------------------------
# A long message is read, not given up on
# --------------------------------------------------------------------------

LONG_MESSAGE = (
    "Chào bác sĩ, tôi năm nay 45 tuổi. Từ sáng nay khoảng 7 giờ tôi bắt đầu thấy "
    "đau bụng quặn từng cơn ở vùng quanh rốn, đau khoảng 7 trên 10, kèm theo "
    "buồn ỉa và đi ngoài lỏng khoảng 4 lần. Tôi cũng thấy buồn nôn nhưng không "
    "nôn. Tôi có tiền sử đau dạ dày nhiều năm và đang uống thuốc huyết áp hàng "
    "ngày. Tôi không sốt, không khó thở, không đau ngực. Tôi hơi mệt và xây xẩm "
    "mặt mày khi đứng dậy. Mong bác sĩ tư vấn giúp tôi ạ."
)


@pytest.mark.asyncio
async def test_a_long_message_yields_its_facts_without_false_conflict() -> None:
    state = await _turn({}, LONG_MESSAGE)
    view = ClinicalStateView(
        CanonicalPatientState.from_dict(state.get("canonical_state") or {})
    )

    # Affirmed
    assert view.is_present("symptom.abdominal_pain")
    assert view.is_present("symptom.diarrhea")
    assert view.is_present("symptom.nausea")
    assert view.read("severity_score").value == 7
    assert view.read("age").value == 45
    assert view.read("onset_time").value

    # Denied -- and a denial is an answer, not a gap
    for denied in ("symptom.fever", "symptom.dyspnea", "symptom.chest_pain",
                   "symptom.vomiting"):
        assert view.is_negated(denied), denied

    # The presentation is recognised, and nothing is disputed
    assert state.get("symptom_cluster") == "abdominal_pain"
    assert not (state.get("unresolved_contradictions") or [])


@pytest.mark.asyncio
async def test_a_long_message_reply_is_clean_vietnamese() -> None:
    state = await _turn({}, LONG_MESSAGE)
    response = str(state.get("response") or "")

    assert response
    for marker in _LEAK_MARKERS:
        assert marker not in response, f"leaked {marker!r}: {response}"
