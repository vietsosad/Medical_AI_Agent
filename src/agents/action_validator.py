"""Deterministic validation of a proposed action, before anything executes.

The planner proposes; this decides. Every check here is ordinary Python against
canonical state and the safety lifecycle — no model is consulted, and there is
no path by which a model can waive a rule. An unsafe proposal is blocked or
replaced with a safe one; it is never sent back for the planner to reconsider,
because "ask the model again" is not a safety control.

Four families of check, in the order a failure would matter:

* **Safety** — a confirmed emergency permits escalation and nothing else.
* **Clinical** — a question must target a genuinely unresolved requirement, and
  must not contradict what canonical state already knows.
* **State** — no re-asking a fact already answered, including one the patient
  explicitly denied.
* **Security** — the action must stay inside the authorised patient and session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from src.agents.clinical_state_view import ClinicalStateView
from src.agents.next_best_action import (
    MAX_ACTIONS_PER_TURN,
    ActionContext,
    NextBestAction,
)

ValidationOutcome = Literal["APPROVED", "REPLACED", "BLOCKED"]

BlockReason = Literal[
    "EMERGENCY_PERMITS_ONLY_ESCALATION",
    "UNTARGETED_QUESTION",
    "TARGET_ALREADY_ANSWERED",
    "TARGET_NOT_A_LIVE_REQUIREMENT",
    "TARGET_ALREADY_EXHAUSTED",
    "ESI_NOT_PLANNER_AUTHORITY",
    "RED_FLAG_NOT_PLANNER_AUTHORITY",
    "EVIDENCE_GATE_NOT_SATISFIED",
    "CROSS_PATIENT_ACCESS",
    "SESSION_MISMATCH",
    "TURN_ACTION_LIMIT_REACHED",
]

# Actions permitted once a red flag is confirmed or a precaution is in force.
#
# ESCALATE only. END used to be here, on the reasoning that a handed-off case
# is finished -- but that conflates two different things. Ending a conversation
# is a claim that nothing further is required, and under an emergency that
# claim is exactly what must not be made by a planner. The deterministic
# escalation path owns concluding an emergency turn; until it does, an END
# proposal is replaced with the escalation the state mandates rather than being
# allowed through. Nothing selects END under an emergency today, which is
# precisely why this had to be closed before something did.
_EMERGENCY_PERMITTED: frozenset[str] = frozenset({"ESCALATE"})

# Actions the planner may never produce, because they are policy decisions
# owned by the evidence gate, the ESI policy and the red-flag lifecycle.
_FORBIDDEN_TARGETS: frozenset[str] = frozenset(
    {"esi_level", "current_esi_level", "final_clinical_esi", "is_red_flag"}
)

_PRIMARY_BRIDGED_ATTRIBUTES: frozenset[str] = frozenset(
    {"onset_time", "severity_score", "radiation"}
)


@dataclass(frozen=True)
class ValidatedAction:
    """The verdict, plus whatever action is actually allowed to run."""

    outcome: ValidationOutcome
    action: NextBestAction | None
    block_reason: BlockReason | None = None
    detail: str = ""
    replaced_from: str | None = None
    audit: dict[str, Any] = field(default_factory=dict)

    @property
    def may_execute(self) -> bool:
        return self.outcome in {"APPROVED", "REPLACED"} and self.action is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "block_reason": self.block_reason,
            "detail": self.detail,
            "replaced_from": self.replaced_from,
            "action": self.action.to_dict() if self.action else None,
            **self.audit,
        }


def _escalation_action(reason: str) -> NextBestAction:
    return NextBestAction(
        action_type="ESCALATE",
        rationale_code="CONFIRMED_RED_FLAG",
        priority=100,
        safety_constraints=("no_further_questioning",),
        audit_metadata={"replaced_because": reason},
    )


def _target_answered_via_primary_problem(
    target: str,
    view: ClinicalStateView,
    *,
    declined_counts: bool = True,
) -> bool:
    """Treat generic and primary-problem scoped answers as the same fact.

    Runtime state can briefly contain a stale missing-target list while
    canonical state already has the answer under the sibling namespace.  The
    projection bridges this for later nodes, but the final validator must also
    block the actual question so a patient is not asked "when did it start?"
    twice.
    """
    from src.agents.problem_state import build_problem_state

    problem_state = build_problem_state(view)
    primary = problem_state.primary
    if primary is None:
        return False

    if "." in target and not target.startswith(("symptom.", "vital.")):
        concept, attribute = target.split(".", 1)
        if concept != primary.concept or attribute not in _PRIMARY_BRIDGED_ATTRIBUTES:
            return False
        fact = primary.facts.get(attribute)
        return bool(
            fact
            and fact.is_answered
            and (declined_counts or not fact.declined)
        )

    if target not in _PRIMARY_BRIDGED_ATTRIBUTES:
        return False
    fact = primary.facts.get(target)
    return bool(
        fact
        and fact.is_answered
        and (declined_counts or not fact.declined)
    )


def validate_action(
    action: NextBestAction,
    context: ActionContext,
    view: ClinicalStateView,
    *,
    authorized_patient_id: str | None = None,
    action_patient_id: str | None = None,
    authorized_session_id: str | None = None,
    action_session_id: str | None = None,
) -> ValidatedAction:
    """Approve, replace or block a proposed action. Never consults a model."""

    # -- Security first: an action touching the wrong patient never runs, --
    # -- whatever it was going to do. --------------------------------------
    if (
        authorized_patient_id is not None
        and action_patient_id is not None
        and authorized_patient_id != action_patient_id
    ):
        return ValidatedAction(
            outcome="BLOCKED",
            action=None,
            block_reason="CROSS_PATIENT_ACCESS",
            detail="Action referenced a patient other than the authorised one",
        )
    if (
        authorized_session_id is not None
        and action_session_id is not None
        and authorized_session_id != action_session_id
    ):
        return ValidatedAction(
            outcome="BLOCKED",
            action=None,
            block_reason="SESSION_MISMATCH",
            detail="Action referenced a different session",
        )

    # -- Safety: an emergency in force permits escalation and nothing else. --
    if context.safety_state in {"CONFIRMED_RED_FLAG", "SAFETY_FALLBACK"}:
        if action.action_type not in _EMERGENCY_PERMITTED:
            return ValidatedAction(
                outcome="REPLACED",
                action=_escalation_action(context.safety_state),
                block_reason="EMERGENCY_PERMITS_ONLY_ESCALATION",
                detail=(
                    f"{action.action_type} is not permitted while "
                    f"{context.safety_state} is in force"
                ),
                replaced_from=action.action_type,
            )

    # -- The planner may not decide clinical policy outcomes. ---------------
    if action.target in _FORBIDDEN_TARGETS:
        return ValidatedAction(
            outcome="BLOCKED",
            action=None,
            block_reason=(
                "RED_FLAG_NOT_PLANNER_AUTHORITY"
                if action.target == "is_red_flag"
                else "ESI_NOT_PLANNER_AUTHORITY"
            ),
            detail=f"{action.target} is decided by clinical policy, not the planner",
        )

    # -- Loop control: a bounded turn cannot spin. --------------------------
    # A loop budget is an engineering safeguard against wasted work. It must
    # never be the reason a patient in an emergency is not escalated: running
    # out of internal actions is our problem, not a clinical finding. So the
    # limit applies to everything except the escalation an emergency mandates.
    is_mandated_escalation = (
        context.safety_state in {"CONFIRMED_RED_FLAG", "SAFETY_FALLBACK", "REQUIRES_ESCALATION"}
        and action.action_type in _EMERGENCY_PERMITTED
    )
    if context.turn_action_count >= MAX_ACTIONS_PER_TURN and not is_mandated_escalation:
        return ValidatedAction(
            outcome="BLOCKED",
            action=None,
            block_reason="TURN_ACTION_LIMIT_REACHED",
            detail="Maximum internal actions for one turn reached",
        )

    # -- Clinical + state checks for anything that asks the patient. --------
    if action.action_type in {"ASK", "CLARIFY"}:
        if not action.target:
            return ValidatedAction(
                outcome="BLOCKED",
                action=None,
                block_reason="UNTARGETED_QUESTION",
                detail="Every question must name the requirement it resolves",
            )

        if context.asked_targets.get(action.target, 0) >= 2:
            return ValidatedAction(
                outcome="BLOCKED",
                action=None,
                block_reason="TARGET_ALREADY_EXHAUSTED",
                detail=(
                    f"{action.target} has been asked twice without progress; "
                    "record UNKNOWN and move on rather than asking again"
                ),
            )

        # Safety clarification and contradiction resolution are lifecycle
        # targets rather than canonical fact keys, so they bypass the fact
        # checks below but still had to pass loop control.
        is_lifecycle_target = action.target == "red_flag_context" or (
            action.target.startswith("contradiction_")
        )
        if not is_lifecycle_target:
            live_requirements = set(context.missing_critical_fields) | set(
                context.relevant_uncertainties
            )
            if action.target not in live_requirements:
                return ValidatedAction(
                    outcome="BLOCKED",
                    action=None,
                    block_reason="TARGET_NOT_A_LIVE_REQUIREMENT",
                    detail=(
                        f"{action.target} is not an open requirement for this "
                        "presentation"
                    ),
                )

            reading = view.read(action.target)
            # A patient saying "I don't know" closes ordinary intake
            # questioning, but authorized evidence may identify that exact
            # fact as decision-critical after confirmation.  Permit that one
            # bounded evidence-driven re-ask; KNOWN and NEGATED facts remain
            # immutable, and the evidence-question/repeat budgets still cap it.
            evidence_driven_question = (
                action.rationale_code == "DECISION_RELEVANT_UNKNOWN"
                and action.audit_metadata.get("selected_by")
                == "structured_evidence_reasoner"
            )
            # A denial is an answer. Asking again ignores what the patient said.
            if (
                reading.is_present
                or reading.is_negated
                or _target_answered_via_primary_problem(
                    action.target,
                    view,
                    declined_counts=not evidence_driven_question,
                )
            ):
                if action.action_type == "ASK":
                    return ValidatedAction(
                        outcome="BLOCKED",
                        action=None,
                        block_reason="TARGET_ALREADY_ANSWERED",
                        detail=(
                            f"{action.target} is already {reading.status} in "
                            "canonical state"
                        ),
                    )

    # -- Retrieval must go through the existing gate, never around it. ------
    if action.action_type == "RETRIEVE_RAG" and context.next_step != "retrieve_evidence":
        return ValidatedAction(
            outcome="BLOCKED",
            action=None,
            block_reason="EVIDENCE_GATE_NOT_SATISFIED",
            detail="Intake is not confirmed and ready for evidence retrieval",
        )

    return ValidatedAction(outcome="APPROVED", action=action)


def plan_and_validate(
    context: ActionContext,
    view: ClinicalStateView,
    *,
    planner_available: bool = True,
    authorized_patient_id: str | None = None,
    action_patient_id: str | None = None,
    authorized_session_id: str | None = None,
    action_session_id: str | None = None,
) -> ValidatedAction:
    """Select an action and validate it. The only entry point callers need."""
    from src.agents.next_best_action import (
        deterministic_fallback_action,
        select_next_best_action,
    )

    proposed = (
        select_next_best_action(context)
        if planner_available
        else deterministic_fallback_action(context)
    )
    validated = validate_action(
        proposed,
        context,
        view,
        authorized_patient_id=authorized_patient_id,
        action_patient_id=action_patient_id,
        authorized_session_id=authorized_session_id,
        action_session_id=action_session_id,
    )
    return ValidatedAction(
        outcome=validated.outcome,
        action=validated.action,
        block_reason=validated.block_reason,
        detail=validated.detail,
        replaced_from=validated.replaced_from,
        audit={
            "proposed_action": proposed.action_type,
            "proposed_target": proposed.target,
            "rationale_code": proposed.rationale_code,
            "safety_state": context.safety_state,
            "readiness_outcome": context.readiness_outcome,
            "red_flag_status": context.red_flag_status,
            "planner_available": planner_available,
        },
    )
