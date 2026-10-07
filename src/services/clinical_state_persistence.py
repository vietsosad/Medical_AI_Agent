"""Persist canonical patient state and the red-flag lifecycle onto a case.

Two things previously survived only in process memory and were lost on restart:

* the canonical facts, their provenance and their history;
* the red-flag lifecycle, of which only the final boolean was stored, so
  "confirmed emergency" and "precaution taken because the validator was down"
  looked identical afterwards.

Both are written here on **every** turn, not only on turns that escalate, so an
alert stays answerable later: when it was raised, why, what it resolved to, and
what resolved it.
"""

from __future__ import annotations

from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from src.models.db_models import AuditLog, TriageCase, get_utc_now

# Lifecycle transitions worth an immutable ledger entry.
_AUDITED_RED_FLAG_STATUSES: frozenset[str] = frozenset(
    {
        "CANDIDATE",
        "CONFIRMED",
        "NOT_CONFIRMED",
        "UNCERTAIN",
        "SAFETY_FALLBACK",
        # A watch is a clinical decision too: a reviewer needs to see that the
        # system noticed something and chose to keep listening rather than
        # escalate, and when that choice was made.
        "MONITORING",
    }
)

# Resolutions that close a candidate, one way or another.
_RESOLVED_STATUSES: frozenset[str] = frozenset(
    {"CONFIRMED", "NOT_CONFIRMED", "SAFETY_FALLBACK"}
)


def persist_canonical_state(case: TriageCase, agent_state: dict[str, Any]) -> None:
    """Store the canonical state so facts survive a restart with provenance."""
    canonical = agent_state.get("canonical_state")
    if isinstance(canonical, dict) and canonical:
        case.canonical_state = canonical
        case.canonical_state_version = int(
            agent_state.get("canonical_state_version") or canonical.get("version") or 0
        )


def persist_red_flag_lifecycle(
    session: AsyncSession,
    case: TriageCase,
    agent_state: dict[str, Any],
) -> AuditLog | None:
    """Record the lifecycle and emit an audit entry when the status changes.

    ``is_red_flag_triggered`` stays derived and confirmed-only, so existing
    queues and the frontend keep working unchanged.
    """
    status = agent_state.get("red_flag_status")
    if not status:
        return None

    previous_status = case.red_flag_status
    # Offset-naive UTC, matching every other timestamp column in this schema.
    # The red-flag columns are TIMESTAMP WITHOUT TIME ZONE, and asyncpg refuses
    # an aware datetime for one outright -- which failed the whole transaction
    # mid-turn, so the patient saw a network error at the exact moment the
    # system had decided their case was an emergency.
    now = get_utc_now()

    case.red_flag_status = str(status)
    case.red_flag_detection_source = agent_state.get("emergency_detection_source")
    case.red_flag_resolution_reason = agent_state.get("red_flag_resolution_reason")
    if agent_state.get("red_flag_candidate_esi") is not None:
        case.red_flag_candidate_esi = int(agent_state["red_flag_candidate_esi"])
    if agent_state.get("red_flag_candidate_reason"):
        case.red_flag_trigger_keyword = str(agent_state["red_flag_candidate_reason"])
    if agent_state.get("red_flag_latency_ms") is not None:
        case.red_flag_latency_ms = agent_state["red_flag_latency_ms"]

    # Stamped on the first turn the lifecycle is active at all, not only on a
    # turn whose status happens to be CANDIDATE. A candidate raised and
    # confirmed inside one turn is the most urgent case there is, and it was
    # exactly the case that ended up with no raised-at time -- leaving an
    # emergency in the ledger that resolved before it began.
    if status != "NO_CANDIDATE" and case.red_flag_raised_at is None:
        case.red_flag_raised_at = now
    if status in _RESOLVED_STATUSES:
        case.red_flag_resolved_at = now

    # Confirmed-only. A CANDIDATE must never reach the emergency flag.
    case.is_red_flag_triggered = bool(agent_state.get("is_red_flag"))

    if previous_status == status or status not in _AUDITED_RED_FLAG_STATUSES:
        return None

    entry = AuditLog(
        event_type=f"RED_FLAG_{status}",
        triage_case_id=case.id,
        actor_role="SYSTEM_AI",
        before_state={"red_flag_status": previous_status},
        after_state={
            "red_flag_status": status,
            "detection_source": case.red_flag_detection_source,
            "candidate_reason": case.red_flag_trigger_keyword,
            "candidate_esi": case.red_flag_candidate_esi,
            "applied_esi": agent_state.get("current_esi_level"),
            "resolution_reason": case.red_flag_resolution_reason,
        },
        clinical_justification=case.red_flag_resolution_reason,
        latency_ms=agent_state.get("red_flag_latency_ms"),
    )
    session.add(entry)
    return entry


def persist_extraction_disagreements(
    session: AsyncSession,
    case: TriageCase,
    agent_state: dict[str, Any],
) -> int:
    """Log parser divergence to the ledger so drift is measurable.

    Written as its own event type, never as a clinical contradiction: no
    clarification is owed to the patient, and no clinical fact changes.
    """
    disagreements = agent_state.get("extraction_disagreements") or []
    if not isinstance(disagreements, list) or not disagreements:
        return 0
    logged = 0
    for item in disagreements:
        if not isinstance(item, dict):
            continue
        session.add(
            AuditLog(
                event_type="EXTRACTION_DISAGREEMENT",
                triage_case_id=case.id,
                actor_role="SYSTEM_AI",
                before_state={"legacy_value": item.get("legacy_value")},
                after_state={
                    "fact_key": item.get("fact_key"),
                    "canonical_value": item.get("canonical_value"),
                    "resolution": item.get("resolution"),
                },
                clinical_justification=(
                    "Extractor disagreement; canonical state is authoritative. "
                    "This is not a patient contradiction."
                ),
            )
        )
        logged += 1
    return logged


def persist_conversation_memory(
    case: TriageCase,
    agent_state: dict[str, Any],
) -> None:
    """Store conversation memory alongside the case that owns it.

    Scoping is structural: memory lives on the TriageCase, and every read path
    additionally filters by patient and session, so similarity can never reach
    across patients.
    """
    memory = agent_state.get("conversation_memory")
    if isinstance(memory, dict) and memory:
        case.conversation_memory = memory


# What the conversation has already done to this patient. Everything here is
# control state, never a clinical fact: which questions were put to them, which
# targets were accepted as unknown, and whether they confirmed the intake
# review. Facts live in ``canonical_state`` and nowhere else.
CONVERSATION_CONTROL_KEYS: tuple[str, ...] = (
    # The question currently open. Message replay can only rebuild a question
    # that carried a structured payload, so a free-text adaptive question was
    # lost across a restart and the patient's next reply bound to nothing.
    "active_question",
    "patient_confirmed_intake",
    "intake_confirmation_status",
    "intake_confirmation_prompt_count",
    "confirmed_fact_snapshot",
    "action_loop_state",
    "adaptive_questioning_complete",
    "adaptive_opening_sent",
    "vital_signs_status",
    "clinical_memory_confirmation_status",
    "confirmed_clinical_memory_updated_at",
    "clinical_memory_update_pending",
    "clinical_context_update_pending",
)


def persist_conversation_control(
    case: TriageCase,
    agent_state: dict[str, Any],
) -> None:
    """Store the conversation's control state so a restart does not repeat itself.

    Without this the question history and the confirmation lived only in process
    memory, so a restarted backend re-asked questions the patient had already
    answered and re-opened a review they had already confirmed. Both read to a
    patient as the system not having listened.
    """
    control = dict(case.conversation_control or {})
    for key in CONVERSATION_CONTROL_KEYS:
        if key in agent_state:
            control[key] = agent_state[key]
    case.conversation_control = control


def persist_action_decision(
    session: AsyncSession,
    case: TriageCase,
    agent_state: dict[str, Any],
) -> AuditLog | None:
    """Log which action was proposed, what the validator did, and why.

    Structured reason codes only - never chain of thought, never patient text.
    """
    validation = agent_state.get("action_validation")
    if not isinstance(validation, dict) or not validation:
        return None
    action = validation.get("action") or {}
    entry = AuditLog(
        event_type="NBA_ACTION_DECISION",
        triage_case_id=case.id,
        actor_role="SYSTEM_AI",
        before_state={
            "proposed_action": validation.get("proposed_action"),
            "proposed_target": validation.get("proposed_target"),
            "safety_state": validation.get("safety_state"),
            "readiness_outcome": validation.get("readiness_outcome"),
            "red_flag_status": validation.get("red_flag_status"),
        },
        after_state={
            "outcome": validation.get("outcome"),
            "executed_action": action.get("action_type"),
            "target": action.get("target"),
            "rationale_code": action.get("rationale_code"),
            "block_reason": validation.get("block_reason"),
            "replaced_from": validation.get("replaced_from"),
            "state_version": agent_state.get("canonical_state_version"),
        },
        clinical_justification=str(validation.get("detail") or "")[:500] or None,
    )
    session.add(entry)
    return entry


def persist_turn_state(
    session: AsyncSession,
    case: TriageCase,
    agent_state: dict[str, Any],
) -> None:
    """Single entry point used by every patient turn."""
    persist_canonical_state(case, agent_state)
    persist_red_flag_lifecycle(session, case, agent_state)
    persist_extraction_disagreements(session, case, agent_state)
    persist_conversation_memory(case, agent_state)
    persist_conversation_control(case, agent_state)
    persist_action_decision(session, case, agent_state)
    session.add(case)
