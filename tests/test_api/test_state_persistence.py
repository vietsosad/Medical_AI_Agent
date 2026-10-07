"""Persistence of canonical state and the red-flag lifecycle.

Runs against a real SQLite database created from the live models, so a schema
mistake or an unsafe default fails here rather than in production.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.agents.canonical_state import CanonicalPatientState
from src.models.db_models import AuditLog, TriageCase, User
from src.services.clinical_state_persistence import persist_turn_state

from src.services.db import POSTGRES_ONLY_TABLES as POSTGRES_ONLY


@pytest_asyncio.fixture
async def db_session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'state.db'}")
    tables = [
        table
        for table in SQLModel.metadata.sorted_tables
        if table.name not in POSTGRES_ONLY
    ]
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables)
        )
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


async def _case(session: AsyncSession, patient_id: str = "user-1") -> TriageCase:
    session.add(User(id=patient_id, email=f"{patient_id}@x.test", full_name="P"))
    case = TriageCase(patient_id=patient_id)
    session.add(case)
    await session.commit()
    return case


def _agent_state(**overrides: Any) -> dict[str, Any]:
    state: dict[str, Any] = {
        "red_flag_status": "CANDIDATE",
        "red_flag_candidate_reason": "đau thắt ngực",
        "red_flag_candidate_esi": 2,
        "red_flag_latency_ms": 0.04,
        "is_red_flag": False,
    }
    state.update(overrides)
    return state


# --------------------------------------------------------------------------
# Red-flag lifecycle
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_candidate_is_persisted_without_setting_the_emergency_flag(
    db_session: AsyncSession,
) -> None:
    case = await _case(db_session)
    persist_turn_state(db_session, case, _agent_state())
    await db_session.commit()

    assert case.red_flag_status == "CANDIDATE"
    assert case.red_flag_candidate_esi == 2
    assert case.red_flag_raised_at is not None
    assert case.red_flag_resolved_at is None
    # A candidate must never reach the derived emergency flag.
    assert case.is_red_flag_triggered is False


@pytest.mark.asyncio
async def test_confirmed_and_fallback_are_distinguishable_after_the_conversation(
    db_session: AsyncSession,
) -> None:
    confirmed = await _case(db_session, "user-a")
    persist_turn_state(
        db_session,
        confirmed,
        _agent_state(
            red_flag_status="CONFIRMED",
            is_red_flag=True,
            emergency_detection_source="CONTEXTUAL_VALIDATION",
            red_flag_resolution_reason="Ngữ cảnh xác nhận hiện tại",
            current_esi_level=2,
        ),
    )
    fallback = await _case(db_session, "user-b")
    persist_turn_state(
        db_session,
        fallback,
        _agent_state(
            red_flag_status="SAFETY_FALLBACK",
            is_red_flag=True,
            emergency_detection_source="SAFETY_FALLBACK",
            red_flag_resolution_reason="Bộ kiểm chứng không khả dụng",
            current_esi_level=2,
        ),
    )
    await db_session.commit()

    # Both locked the case, but the reason is still answerable.
    assert confirmed.is_red_flag_triggered == fallback.is_red_flag_triggered is True
    assert confirmed.red_flag_status != fallback.red_flag_status
    assert confirmed.red_flag_detection_source == "CONTEXTUAL_VALIDATION"
    assert fallback.red_flag_detection_source == "SAFETY_FALLBACK"
    assert fallback.red_flag_resolved_at is not None


@pytest.mark.asyncio
async def test_lifecycle_is_queryable_by_status(db_session: AsyncSession) -> None:
    """A nurse must be able to filter precautions from validated emergencies."""
    for index, status in enumerate(
        ["CONFIRMED", "SAFETY_FALLBACK", "NOT_CONFIRMED", "SAFETY_FALLBACK"]
    ):
        case = await _case(db_session, f"user-{index}")
        persist_turn_state(
            db_session,
            case,
            _agent_state(
                red_flag_status=status,
                is_red_flag=status in {"CONFIRMED", "SAFETY_FALLBACK"},
            ),
        )
    await db_session.commit()

    rows = await db_session.execute(
        select(TriageCase).where(TriageCase.red_flag_status == "SAFETY_FALLBACK")
    )
    assert len(rows.scalars().all()) == 2


@pytest.mark.asyncio
async def test_each_transition_writes_one_audit_entry(
    db_session: AsyncSession,
) -> None:
    case = await _case(db_session)
    persist_turn_state(db_session, case, _agent_state())
    persist_turn_state(
        db_session,
        case,
        _agent_state(
            red_flag_status="CONFIRMED",
            is_red_flag=True,
            emergency_detection_source="CONTEXTUAL_VALIDATION",
            red_flag_resolution_reason="Xác nhận hiện tại",
        ),
    )
    await db_session.commit()

    logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.triage_case_id == case.id)
        )
    ).scalars().all()
    events = {log.event_type for log in logs}
    assert events == {"RED_FLAG_CANDIDATE", "RED_FLAG_CONFIRMED"}
    confirmed = next(log for log in logs if log.event_type == "RED_FLAG_CONFIRMED")
    # The ledger answers when, why, and on what basis.
    assert confirmed.before_state["red_flag_status"] == "CANDIDATE"
    assert confirmed.after_state["detection_source"] == "CONTEXTUAL_VALIDATION"
    assert confirmed.after_state["candidate_reason"] == "đau thắt ngực"
    assert confirmed.clinical_justification == "Xác nhận hiện tại"


@pytest.mark.asyncio
async def test_an_unchanged_status_does_not_spam_the_ledger(
    db_session: AsyncSession,
) -> None:
    case = await _case(db_session)
    persist_turn_state(db_session, case, _agent_state())
    persist_turn_state(db_session, case, _agent_state())
    await db_session.commit()
    logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.triage_case_id == case.id)
        )
    ).scalars().all()
    assert len(logs) == 1


# --------------------------------------------------------------------------
# Canonical state
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_canonical_state_survives_a_database_round_trip(
    db_session: AsyncSession,
) -> None:
    from src.agents.nodes.fact_extraction import apply_message_to_state

    state = CanonicalPatientState()
    apply_message_to_state(
        state,
        "Tôi 67 tuổi, sáng nay sốt 39 độ, giờ nhiệt độ còn 37.8",
        turn_id="t1",
    )
    case = await _case(db_session)
    persist_turn_state(
        db_session,
        case,
        {
            "canonical_state": state.to_dict(),
            "canonical_state_version": state.version,
        },
    )
    await db_session.commit()
    db_session.expunge_all()

    reloaded = (
        await db_session.execute(select(TriageCase).where(TriageCase.id == case.id))
    ).scalars().first()
    restored = CanonicalPatientState.from_dict(reloaded.canonical_state)

    assert restored.value_of("age") == 67
    assert restored.value_of("vital.temperature_c") == 37.8
    assert [o.value for o in restored.historical_values("vital.temperature_c")] == [39.0]
    assert restored.observation_of("age").source == "PATIENT_REPORTED"
    assert reloaded.canonical_state_version == state.version


@pytest.mark.asyncio
async def test_a_legacy_case_without_canonical_state_reads_as_unknown(
    db_session: AsyncSession,
) -> None:
    """Rows written before this feature must not crash or imply negatives."""
    case = await _case(db_session)
    await db_session.commit()

    assert case.canonical_state is None
    assert case.red_flag_status is None
    restored = CanonicalPatientState.from_dict(case.canonical_state)
    assert restored.status_of("symptom.chest_pain") == "UNKNOWN"
    assert restored.value_of("severity_score") is None


@pytest.mark.asyncio
async def test_migration_statements_are_idempotent(tmp_path) -> None:
    """init_db's additive ALTERs must be safe to run against an existing DB."""
    from src.services.db import _ADDITIVE_TRIAGE_CASE_COLUMNS

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'mig.db'}")
    tables = [
        table
        for table in SQLModel.metadata.sorted_tables
        if table.name not in POSTGRES_ONLY
    ]
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables)
        )
        for _ in range(2):
            result = await conn.execute(text("PRAGMA table_info(triage_cases)"))
            existing = {str(row[1]) for row in result.fetchall()}
            for column, ddl_type in _ADDITIVE_TRIAGE_CASE_COLUMNS:
                if column not in existing:
                    await conn.execute(
                        text(
                            f"ALTER TABLE triage_cases ADD COLUMN {column} {ddl_type}"
                        )
                    )
        result = await conn.execute(text("PRAGMA table_info(triage_cases)"))
        columns = {str(row[1]) for row in result.fetchall()}
    await engine.dispose()

    for column, _ in _ADDITIVE_TRIAGE_CASE_COLUMNS:
        assert column in columns


# --------------------------------------------------------------------------
# §18 Patient isolation
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_canonical_state_does_not_leak_between_patients(
    db_session: AsyncSession,
) -> None:
    alice = await _case(db_session, "alice")
    bob = await _case(db_session, "bob")

    alice_state = CanonicalPatientState()
    alice_state.record("symptom.chest_pain", True, turn_id="t1")
    persist_turn_state(
        db_session, alice, {"canonical_state": alice_state.to_dict()}
    )
    bob_state = CanonicalPatientState()
    bob_state.record("symptom.headache", True, turn_id="t1")
    persist_turn_state(db_session, bob, {"canonical_state": bob_state.to_dict()})
    await db_session.commit()

    # The ownership predicate the patient API uses must scope state too.
    scoped = (
        await db_session.execute(
            select(TriageCase).where(
                TriageCase.id == alice.id, TriageCase.patient_id == "bob"
            )
        )
    ).scalars().first()
    assert scoped is None

    alice_restored = CanonicalPatientState.from_dict(alice.canonical_state)
    assert alice_restored.status_of("symptom.chest_pain") == "KNOWN"
    assert alice_restored.status_of("symptom.headache") == "UNKNOWN"


@pytest.mark.asyncio
async def test_audit_entries_stay_bound_to_their_own_case(
    db_session: AsyncSession,
) -> None:
    alice = await _case(db_session, "alice")
    bob = await _case(db_session, "bob")
    persist_turn_state(db_session, alice, _agent_state(red_flag_status="CONFIRMED"))
    persist_turn_state(db_session, bob, _agent_state(red_flag_status="NOT_CONFIRMED"))
    await db_session.commit()

    alice_logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.triage_case_id == alice.id)
        )
    ).scalars().all()
    assert {log.event_type for log in alice_logs} == {"RED_FLAG_CONFIRMED"}
    assert all(log.triage_case_id == alice.id for log in alice_logs)


@pytest.mark.asyncio
async def test_missing_lifecycle_in_agent_state_leaves_the_case_untouched(
    db_session: AsyncSession,
) -> None:
    """A turn that reports no status must not clear an existing one."""
    case = await _case(db_session)
    persist_turn_state(db_session, case, _agent_state(red_flag_status="CONFIRMED",
                                                      is_red_flag=True))
    await db_session.commit()
    before = case.red_flag_status

    persist_turn_state(db_session, case, {"canonical_state": {"version": 1}})
    await db_session.commit()
    assert case.red_flag_status == before == "CONFIRMED"


@pytest.mark.asyncio
async def test_raised_at_is_recorded_once_not_reset_by_later_turns(
    db_session: AsyncSession,
) -> None:
    case = await _case(db_session)
    persist_turn_state(db_session, case, _agent_state())
    await db_session.commit()
    raised = case.red_flag_raised_at
    assert raised is not None

    persist_turn_state(
        db_session, case, _agent_state(red_flag_status="CONFIRMED", is_red_flag=True)
    )
    await db_session.commit()
    assert case.red_flag_raised_at == raised
    assert case.red_flag_resolved_at is not None
    # Resolution never precedes the moment the candidate was raised.
    resolved = case.red_flag_resolved_at
    if resolved.tzinfo is None:
        resolved = resolved.replace(tzinfo=UTC)
    if raised.tzinfo is None:
        raised = raised.replace(tzinfo=UTC)
    assert resolved >= raised


# --------------------------------------------------------------------------
# Extraction disagreement is auditable and distinct from contradiction
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extraction_disagreement_is_written_to_the_ledger(
    db_session: AsyncSession,
) -> None:
    case = await _case(db_session)
    persist_turn_state(
        db_session,
        case,
        {
            "canonical_state": {"version": 1},
            "extraction_disagreements": [
                {
                    "fact_key": "onset_time",
                    "legacy_value": "8 giờ",
                    "canonical_value": "5 giờ",
                    "resolution": "CANONICAL_AUTHORITATIVE",
                }
            ],
        },
    )
    await db_session.commit()

    logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.triage_case_id == case.id)
        )
    ).scalars().all()
    assert [log.event_type for log in logs] == ["EXTRACTION_DISAGREEMENT"]
    entry = logs[0]
    assert entry.before_state["legacy_value"] == "8 giờ"
    assert entry.after_state["canonical_value"] == "5 giờ"
    # It must be legible as a parser problem, not a patient one.
    assert "not a patient contradiction" in entry.clinical_justification


@pytest.mark.asyncio
async def test_a_turn_without_disagreement_writes_no_such_event(
    db_session: AsyncSession,
) -> None:
    case = await _case(db_session)
    persist_turn_state(db_session, case, {"canonical_state": {"version": 1}})
    await db_session.commit()
    logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.triage_case_id == case.id)
        )
    ).scalars().all()
    assert logs == []


@pytest.mark.asyncio
async def test_legacy_recovered_provenance_survives_persistence(
    db_session: AsyncSession,
) -> None:
    """A replayed case must still be identifiable as replayed after reload."""
    from src.agents.clinical_state_view import ClinicalStateView
    from src.services.triage_session_recovery import build_legacy_canonical_state

    state = build_legacy_canonical_state(
        {"chief_complaint": ["đau ngực"], "onset_time": "5 giờ"}
    )
    case = await _case(db_session)
    persist_turn_state(db_session, case, {"canonical_state": state.to_dict()})
    await db_session.commit()
    db_session.expunge_all()

    reloaded = (
        await db_session.execute(select(TriageCase).where(TriageCase.id == case.id))
    ).scalars().first()
    view = ClinicalStateView(
        CanonicalPatientState.from_dict(reloaded.canonical_state)
    )
    assert view.has_degraded_provenance() is True
    assert view.read("onset_time").source == "LEGACY_RECOVERED"
    assert view.is_patient_asserted("onset_time") is False


# --------------------------------------------------------------------------
# NBA decisions and conversation memory are persisted and isolated
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_action_decision_is_written_to_the_ledger(
    db_session: AsyncSession,
) -> None:
    case = await _case(db_session)
    persist_turn_state(
        db_session,
        case,
        {
            "canonical_state": {"version": 1},
            "action_validation": {
                "outcome": "REPLACED",
                "proposed_action": "ASK",
                "proposed_target": "onset_time",
                "safety_state": "CONFIRMED_RED_FLAG",
                "readiness_outcome": "NOT_READY",
                "red_flag_status": "CONFIRMED",
                "block_reason": "EMERGENCY_PERMITS_ONLY_ESCALATION",
                "replaced_from": "ASK",
                "detail": "ASK is not permitted while CONFIRMED_RED_FLAG is in force",
                "action": {
                    "action_type": "ESCALATE",
                    "target": None,
                    "rationale_code": "CONFIRMED_RED_FLAG",
                },
            },
        },
    )
    await db_session.commit()

    logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.triage_case_id == case.id)
        )
    ).scalars().all()
    entry = next(log for log in logs if log.event_type == "NBA_ACTION_DECISION")
    assert entry.before_state["proposed_action"] == "ASK"
    assert entry.after_state["executed_action"] == "ESCALATE"
    assert entry.after_state["block_reason"] == "EMERGENCY_PERMITS_ONLY_ESCALATION"
    assert entry.after_state["rationale_code"] == "CONFIRMED_RED_FLAG"


@pytest.mark.asyncio
async def test_conversation_memory_survives_a_database_round_trip(
    db_session: AsyncSession,
) -> None:
    from src.agents.conversation_memory import ConversationMemory, MemoryScope

    memory = ConversationMemory()
    memory.remember(
        "Tôi bị đau đầu từ tối qua",
        patient_id="alice",
        session_id="s-alice",
        turn_id="t1",
    )
    case = await _case(db_session, "alice")
    persist_turn_state(
        db_session, case, {"conversation_memory": memory.to_dict()}
    )
    await db_session.commit()
    db_session.expunge_all()

    reloaded = (
        await db_session.execute(select(TriageCase).where(TriageCase.id == case.id))
    ).scalars().first()
    restored = ConversationMemory.from_dict(reloaded.conversation_memory)
    scope = MemoryScope(patient_id="alice", session_id="s-alice")
    assert restored.search("đau đầu", scope)


@pytest.mark.asyncio
async def test_persisted_memory_cannot_be_read_by_another_patients_scope(
    db_session: AsyncSession,
) -> None:
    """Isolation must survive persistence, not just live in process memory."""
    from src.agents.conversation_memory import ConversationMemory, MemoryScope

    memory = ConversationMemory()
    memory.remember(
        "Tôi dị ứng penicillin", patient_id="alice", session_id="s-alice"
    )
    case = await _case(db_session, "alice")
    persist_turn_state(db_session, case, {"conversation_memory": memory.to_dict()})
    await db_session.commit()
    db_session.expunge_all()

    reloaded = (
        await db_session.execute(select(TriageCase).where(TriageCase.id == case.id))
    ).scalars().first()
    restored = ConversationMemory.from_dict(reloaded.conversation_memory)
    intruder = MemoryScope(patient_id="bob", session_id="s-bob")
    assert restored.search("penicillin", intruder) == []
    assert restored.recent(intruder) == []
