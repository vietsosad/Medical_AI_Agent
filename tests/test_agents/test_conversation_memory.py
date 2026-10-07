"""Memory is retrieval support, scoped to one patient, never a second truth.

The adversarial half of this file matters more than the functional half: a
memory system that works but leaks is worse than no memory system.
"""

from __future__ import annotations

import pytest

from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.context_assembly import assemble_context, estimate_tokens
from src.agents.conversation_memory import (
    ConversationMemory,
    MemoryScope,
    should_remember,
)
from src.agents.nodes.fact_extraction import apply_message_to_state

ALICE = MemoryScope(patient_id="alice", session_id="s-alice")
BOB = MemoryScope(patient_id="bob", session_id="s-bob")


def _memory_with(scope: MemoryScope, *messages: str) -> ConversationMemory:
    memory = ConversationMemory()
    for index, message in enumerate(messages):
        memory.remember(
            message,
            patient_id=scope.patient_id,
            session_id=scope.session_id,
            turn_id=f"t{index + 1}",
        )
    return memory


# --------------------------------------------------------------------------
# §19 / §33-L Patient isolation - adversarial
# --------------------------------------------------------------------------

def test_one_patient_never_retrieves_another_patients_memory() -> None:
    memory = ConversationMemory()
    memory.remember("Tôi bị đau ngực dữ dội", patient_id="alice", session_id="s-alice")
    memory.remember("Tôi bị đau ngực dữ dội", patient_id="bob", session_id="s-bob")

    hits = memory.search("đau ngực", ALICE)
    assert len(hits) == 1
    assert all(item.patient_id == "alice" for item, _ in hits)


def test_an_identical_message_from_another_patient_is_invisible_not_ranked_low() -> None:
    """Isolation is not a scoring penalty. It is a filter applied first."""
    memory = ConversationMemory()
    memory.remember(
        "Tôi dị ứng penicillin nặng", patient_id="bob", session_id="s-bob"
    )
    assert memory.search("dị ứng penicillin", ALICE) == []
    assert memory.recent(ALICE) == []
    assert memory.important_events(ALICE) == []


def test_same_patient_different_session_is_still_scoped_out() -> None:
    memory = ConversationMemory()
    memory.remember("Tôi đau đầu", patient_id="alice", session_id="other-session")
    assert memory.search("đau đầu", ALICE) == []


@pytest.mark.parametrize(
    "scope",
    [
        MemoryScope(patient_id="", session_id="s"),
        MemoryScope(patient_id="alice", session_id=""),
    ],
)
def test_an_incomplete_scope_can_read_nothing(scope: MemoryScope) -> None:
    memory = _memory_with(ALICE, "Tôi đau ngực")
    assert memory.search("đau ngực", scope) == []
    assert memory.recent(scope) == []


def test_an_unscoped_write_is_refused() -> None:
    """An item that cannot be scoped could later be read by the wrong person."""
    memory = ConversationMemory()
    assert memory.remember("Tôi đau ngực", patient_id="", session_id="s") is None
    assert memory.remember("Tôi đau ngực", patient_id="p", session_id="") is None


def test_the_rolling_summary_is_scoped_too() -> None:
    memory = ConversationMemory()
    for index in range(15):
        memory.remember(
            f"Tôi thấy mệt lần {index}",
            patient_id="bob",
            session_id="s-bob",
            turn_id=f"t{index}",
        )
    memory.build_rolling_summary(BOB)
    assert memory.rolling_summary(BOB) is not None
    assert memory.rolling_summary(ALICE) is None


# --------------------------------------------------------------------------
# §20 Write policy
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["vâng ạ", "ok", "cảm ơn", "ừ", ""])
def test_bare_acknowledgements_are_not_stored(text: str) -> None:
    assert should_remember(text) is False


@pytest.mark.parametrize(
    "text", ["Tôi bị đau ngực từ sáng", "Tôi đang uống thuốc huyết áp"]
)
def test_clinically_meaningful_statements_are_stored(text: str) -> None:
    assert should_remember(text) is True


def test_an_important_event_is_stored_even_if_terse() -> None:
    memory = ConversationMemory()
    item = memory.record_event(
        "RED_FLAG_CANDIDATE", "ok", patient_id="alice", session_id="s-alice"
    )
    assert item is not None
    assert item.memory_type == "IMPORTANT_EVENT"


def test_an_unknown_event_kind_is_refused() -> None:
    memory = ConversationMemory()
    assert (
        memory.record_event("MADE_UP", "x", patient_id="alice", session_id="s-alice")
        is None
    )


# --------------------------------------------------------------------------
# §21 / §22 Retrieval and entity linking
# --------------------------------------------------------------------------

def test_an_old_symptom_reference_is_retrievable_after_many_turns() -> None:
    memory = _memory_with(
        ALICE,
        "Tôi bị đau đầu dữ dội từ tối qua",
        *[f"Tôi vẫn thấy mệt lần {index}" for index in range(20)],
    )
    hits = memory.search("cơn đau đầu tôi nói lúc nãy", ALICE)
    assert hits
    assert "đau đầu" in hits[0][0].content


def test_an_old_medication_reference_is_retrievable() -> None:
    memory = _memory_with(
        ALICE,
        "Tôi đang uống thuốc huyết áp amlodipine",
        *[f"Tôi thấy hơi mệt {index}" for index in range(10)],
    )
    hits = memory.search("thuốc tôi nói hôm trước", ALICE)
    assert hits
    assert "amlodipine" in hits[0][0].content


def test_an_unrelated_query_retrieves_nothing() -> None:
    memory = _memory_with(ALICE, "Tôi bị đau đầu")
    assert memory.search("thời tiết hôm nay thế nào", ALICE) == []


# --------------------------------------------------------------------------
# §25 Corrections
# --------------------------------------------------------------------------

def test_a_superseded_memory_stops_surfacing() -> None:
    memory = ConversationMemory()
    item = memory.remember(
        "Tôi đau từ 8 giờ", patient_id="alice", session_id="s-alice", turn_id="t1"
    )
    assert memory.search("đau từ mấy giờ", ALICE)
    assert memory.supersede(item.id, "t2") is True
    assert memory.search("đau từ mấy giờ", ALICE) == []


def test_superseding_an_unknown_item_is_a_no_op() -> None:
    memory = _memory_with(ALICE, "Tôi đau ngực")
    assert memory.supersede("does-not-exist", "t2") is False


# --------------------------------------------------------------------------
# §26 Temporal context is carried, not stripped
# --------------------------------------------------------------------------

def test_memory_preserves_the_temporal_context_it_was_given() -> None:
    memory = ConversationMemory()
    memory.remember(
        "Tuần trước tôi sốt 39",
        patient_id="alice",
        session_id="s-alice",
        temporal_context="HISTORICAL",
    )
    hits = memory.search("sốt", ALICE)
    assert hits[0][0].temporal_context == "HISTORICAL"


def test_memory_never_writes_to_canonical_state() -> None:
    """§24: canonical state is not modified by anything memory does."""
    canonical = CanonicalPatientState()
    apply_message_to_state(canonical, "Tôi không đau ngực", turn_id="t1")
    memory = _memory_with(ALICE, "Tôi đau ngực dữ dội")

    memory.search("đau ngực", ALICE)
    view = ClinicalStateView(canonical)
    # Memory says one thing; canonical still says what the patient actually said.
    assert view.is_negated("symptom.chest_pain") is True
    assert view.is_present("symptom.chest_pain") is False


# --------------------------------------------------------------------------
# §17 Summarisation must not lose clinically important events
# --------------------------------------------------------------------------

def test_summarisation_never_compacts_an_important_event() -> None:
    memory = ConversationMemory()
    memory.record_event(
        "RED_FLAG_CANDIDATE", "đau thắt ngực",
        patient_id="alice", session_id="s-alice",
    )
    for index in range(20):
        memory.remember(
            f"Tôi thấy hơi mệt {index}",
            patient_id="alice",
            session_id="s-alice",
            turn_id=f"t{index}",
        )
    memory.build_rolling_summary(ALICE)

    events = memory.important_events(ALICE)
    assert any(item.event_kind == "RED_FLAG_CANDIDATE" for item in events)
    assert "đau thắt ngực" not in (memory.rolling_summary(ALICE).content or "")


def test_summary_is_only_built_once_there_is_something_to_compact() -> None:
    memory = _memory_with(ALICE, "Tôi đau ngực")
    assert memory.build_rolling_summary(ALICE) is None


# --------------------------------------------------------------------------
# Serialization
# --------------------------------------------------------------------------

def test_memory_survives_a_round_trip_with_scope_intact() -> None:
    memory = _memory_with(ALICE, "Tôi bị đau đầu từ tối qua")
    memory.record_event(
        "NEW_SYMPTOM", "headache", patient_id="alice", session_id="s-alice"
    )
    restored = ConversationMemory.from_dict(memory.to_dict())

    assert restored.search("đau đầu", ALICE)
    assert restored.important_events(ALICE)
    # Isolation survives serialization.
    assert restored.search("đau đầu", BOB) == []


@pytest.mark.parametrize("payload", [None, {}, {"items": None}, {"junk": 1}])
def test_a_corrupt_memory_payload_degrades_to_empty(payload: object) -> None:
    memory = ConversationMemory.from_dict(payload)  # type: ignore[arg-type]
    assert memory.recent(ALICE) == []
    assert memory.search("bất kỳ", ALICE) == []


# --------------------------------------------------------------------------
# §23 Long-context assembly
# --------------------------------------------------------------------------

def test_context_includes_sections_in_priority_order() -> None:
    memory = _memory_with(ALICE, "Tôi đau ngực từ sáng")
    context = assemble_context(
        safety_constraints="Không chẩn đoán.",
        current_message="Tôi thấy khó thở",
        canonical_summary="chest_pain=KNOWN",
        memory=memory,
        scope=ALICE,
    )
    assert context.included[0] == "safety_constraints"
    assert "current_message" in context.included
    assert "canonical_state" in context.included


def test_a_tight_budget_drops_low_priority_sections_not_clinical_ones() -> None:
    memory = _memory_with(ALICE, *[f"Câu chuyện dài số {i}" * 20 for i in range(10)])
    memory.record_event(
        "RED_FLAG_CANDIDATE", "đau thắt ngực",
        patient_id="alice", session_id="s-alice",
    )
    context = assemble_context(
        safety_constraints="Không chẩn đoán.",
        current_message="Tôi thấy khó thở",
        canonical_summary="chest_pain=KNOWN",
        memory=memory,
        scope=ALICE,
        budget=60,
    )
    # The non-negotiable clinical sections survive.
    assert {"safety_constraints", "current_message", "canonical_state"} <= set(
        context.included
    )
    # Conversation filler is what gets dropped.
    assert "recent_conversation" in context.dropped


def test_important_events_outrank_ordinary_conversation_under_pressure() -> None:
    memory = ConversationMemory()
    memory.record_event(
        "RED_FLAG_CANDIDATE", "đau thắt ngực",
        patient_id="alice", session_id="s-alice",
    )
    for index in range(10):
        memory.remember(
            "Chuyện phiếm rất dài " * 15,
            patient_id="alice", session_id="s-alice", turn_id=f"t{index}",
        )
    context = assemble_context(
        safety_constraints="S",
        current_message="M",
        canonical_summary="C",
        memory=memory,
        scope=ALICE,
        budget=120,
    )
    assert "important_events" in context.included
    assert "recent_conversation" in context.dropped


def test_semantic_memory_is_opt_in_not_every_turn() -> None:
    memory = _memory_with(
        ALICE, "Tôi bị đau đầu từ tối qua", *[f"filler {i}" for i in range(10)]
    )
    without = assemble_context(
        safety_constraints="S", current_message="cơn đau đầu đó",
        canonical_summary="C", memory=memory, scope=ALICE,
    )
    with_memory = assemble_context(
        safety_constraints="S", current_message="cơn đau đầu đó",
        canonical_summary="C", memory=memory, scope=ALICE, retrieve_memory=True,
    )
    assert "semantic_memory" not in without.included
    assert "semantic_memory" in with_memory.included


def test_context_audit_records_what_was_used_without_patient_text() -> None:
    memory = _memory_with(ALICE, "Tôi đau ngực")
    audit = assemble_context(
        safety_constraints="S", current_message="M", canonical_summary="C",
        memory=memory, scope=ALICE,
    ).audit()
    assert set(audit) == {
        "sections_included", "sections_dropped", "estimated_tokens",
        "budget", "over_budget", "memory_ids",
    }
    assert "Tôi đau ngực" not in str(audit)


def test_token_estimation_is_monotonic() -> None:
    assert estimate_tokens("a" * 300) > estimate_tokens("a" * 30)


def test_assembly_works_with_no_memory_at_all() -> None:
    """§36: memory unavailable must not break the turn."""
    context = assemble_context(
        safety_constraints="S", current_message="M", canonical_summary="C",
    )
    assert "current_message" in context.included
    assert context.memory_ids_used == []
