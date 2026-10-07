"""Next Best Action: choosing what is useful to do next.

The agent decides what is *useful*; deterministic clinical policy decides what
is *allowed*; canonical patient state decides what is *actually known*. This
module is the first of those three and only the first.

Two properties matter more than the selection logic itself:

1. **Selection is not execution.** Nothing here runs a tool. A selector returns
   a proposal, which ``action_validator`` may approve, replace or block before
   anything happens. A model may later propose actions; it still cannot execute
   one, because the type system does not give it a tool name to call.

2. **Safety is applied before selection, not after.** The action context is
   built from an already-evaluated red-flag status and readiness outcome, so a
   confirmed emergency cannot be "planned around". Precedence is a fixed
   ordering, not a model judgement.

Rationale is recorded as a short structured code, never free-text reasoning:
enough to audit why an action was chosen, without persisting a chain of thought.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ActionType = Literal[
    # Ask for a decision-relevant fact the patient has not given.
    "ASK",
    # Resolve an ambiguity that could change triage.
    "CLARIFY",
    # Fetch protocol evidence through the existing evidence gate.
    "RETRIEVE_RAG",
    # Look back at earlier conversation to resolve a reference.
    "RETRIEVE_MEMORY",
    # A clinically relevant change invalidated an earlier conclusion.
    "REASSESS",
    # Tell the patient something without asking for anything.
    "EXPLAIN",
    # Hand off to emergency care or a clinician.
    "ESCALATE",
    # Stop asking; the case is ready or complete.
    "END",
]

# Short, enumerable reasons. Auditable, and safe to persist.
RationaleCode = Literal[
    "CONFIRMED_RED_FLAG",
    "SAFETY_FALLBACK_PENDING_REVIEW",
    "SAFETY_CONTEXT_UNRESOLVED",
    "PATIENT_CONTRADICTION_OPEN",
    "DECISION_RELEVANT_UNKNOWN",
    "CLINICALLY_RELEVANT_UNCERTAINTY",
    "UNRESOLVED_REFERENCE",
    "STALE_ASSESSMENT_AFTER_CHANGE",
    "READY_FOR_EVIDENCE",
    "SUFFICIENT_TO_CONCLUDE",
    "NO_TRIAGE_INTENT",
    "REPEATED_WITHOUT_PROGRESS",
    "PLANNER_UNAVAILABLE_FALLBACK",
]

# Fixed precedence. A later entry can never pre-empt an earlier one, and this
# ordering is not something the planner or a model may reorder.
SAFETY_PRECEDENCE: tuple[str, ...] = (
    "CONFIRMED_RED_FLAG",
    "SAFETY_FALLBACK",
    "REQUIRES_ESCALATION",
    "NEEDS_CLARIFICATION",
    "NOT_READY",
    "READY",
)


@dataclass(frozen=True)
class NextBestAction:
    """A proposed conversational action. Not yet permitted, not yet executed."""

    action_type: ActionType
    rationale_code: RationaleCode
    # The fact key or requirement this action is about. ASK and CLARIFY must
    # always name one; the validator rejects an untargeted question.
    target: str | None = None
    priority: int = 50
    # Rough value of the answer, used only to order competing questions.
    expected_information_gain: float = 0.0
    required_context: tuple[str, ...] = ()
    policy_dependencies: tuple[str, ...] = ()
    safety_constraints: tuple[str, ...] = ()
    audit_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "rationale_code": self.rationale_code,
            "target": self.target,
            "priority": self.priority,
            "expected_information_gain": self.expected_information_gain,
            "required_context": list(self.required_context),
            "policy_dependencies": list(self.policy_dependencies),
            "safety_constraints": list(self.safety_constraints),
            "audit_metadata": dict(self.audit_metadata),
        }


@dataclass(frozen=True)
class ActionContext:
    """Everything the selector is allowed to see.

    Deliberately narrow. The selector cannot reach into raw state, so it cannot
    invent a clinical fact or re-derive readiness with its own rules.
    """

    red_flag_status: str = "NO_CANDIDATE"
    is_red_flag: bool = False
    readiness_outcome: str = "NOT_READY"
    intent: str = "UNCLEAR"
    decision_relevant_unknowns: tuple[str, ...] = ()
    relevant_uncertainties: tuple[str, ...] = ()
    missing_critical_fields: tuple[str, ...] = ()
    unresolved_contradictions: tuple[str, ...] = ()
    requires_reassessment: bool = False
    has_unresolved_reference: bool = False
    has_conclusion: bool = False
    next_step: str = ""
    # Loop control: how many times each target has already been asked.
    asked_targets: dict[str, int] = field(default_factory=dict)
    accepted_unknown_targets: tuple[str, ...] = ()
    turn_action_count: int = 0
    # Per-target expected information gain, supplied by the adaptive question
    # planner. Empty means "no plan this turn", and the static table below is
    # used instead -- so an outage in planning degrades the *ordering* of
    # questions and never the safety precedence above it.
    target_information_gain: dict[str, float] = field(default_factory=dict)

    @property
    def safety_state(self) -> str:
        """Where this turn sits in the fixed precedence ordering."""
        # Order matters for the audit trail as much as for behaviour: a
        # precaution taken because the validator was down must not be recorded
        # as a confirmed emergency, even though both escalate.
        if self.red_flag_status == "SAFETY_FALLBACK":
            return "SAFETY_FALLBACK"
        if self.red_flag_status == "CONFIRMED" or self.is_red_flag:
            return "CONFIRMED_RED_FLAG"
        if self.red_flag_status == "UNCERTAIN":
            return "REQUIRES_ESCALATION"
        if self.unresolved_contradictions or self.relevant_uncertainties:
            return "NEEDS_CLARIFICATION"
        if self.readiness_outcome == "READY":
            return "READY"
        return "NOT_READY"

    @classmethod
    def from_agent_state(cls, state: dict[str, Any]) -> ActionContext:
        loop_state = state.get("action_loop_state") or {}
        return cls(
            red_flag_status=str(state.get("red_flag_status") or "NO_CANDIDATE"),
            is_red_flag=bool(state.get("is_red_flag")),
            readiness_outcome=str(state.get("readiness_outcome") or "NOT_READY"),
            intent=str(state.get("intent") or "UNCLEAR"),
            decision_relevant_unknowns=tuple(
                state.get("decision_relevant_unknowns") or ()
            ),
            relevant_uncertainties=tuple(state.get("relevant_uncertainties") or ()),
            missing_critical_fields=tuple(state.get("missing_critical_fields") or ()),
            unresolved_contradictions=tuple(
                str(item.get("field") or item.get("key") or "unknown")
                for item in (state.get("unresolved_contradictions") or [])
                if isinstance(item, dict)
            ),
            requires_reassessment=bool(state.get("requires_triage_reassessment")),
            has_unresolved_reference=bool(state.get("has_unresolved_reference")),
            has_conclusion=bool(
                state.get("current_esi_level")
                or state.get("sbar_report")
                # A pending reassessment is itself proof that a conclusion
                # existed: the flag is only ever raised when a clinically
                # relevant change invalidated one. Upstream nodes may have
                # already cleared the ESI by the time the planner runs, and
                # without this the planner would conclude there was nothing to
                # reassess and quietly skip the reassessment it was asked for.
                or state.get("requires_triage_reassessment")
            ),
            next_step=str(state.get("next_step") or ""),
            asked_targets=dict(loop_state.get("asked_targets") or {}),
            accepted_unknown_targets=tuple(
                loop_state.get("accepted_unknown_targets") or ()
            ),
            turn_action_count=int(loop_state.get("turn_action_count") or 0),
            target_information_gain={
                str(key): float(value)
                for key, value in (state.get("target_information_gain") or {}).items()
            },
        )


# How many times one target may be asked before the planner must move on. Asking
# a third time after two non-answers is not persistence, it is a loop.
MAX_REPEATS_PER_TARGET = 2
# Hard ceiling on internal actions per turn, so a planning bug cannot spin.
MAX_ACTIONS_PER_TURN = 8

# Rough ordering of what is worth asking first within a presentation. Not a
# clinical ranking - it only breaks ties between equally-required facts.
_INFORMATION_GAIN: dict[str, float] = {
    "chief_complaint": 1.0,
    "severity_score": 0.8,
    "associated_symptoms": 0.75,
    "onset_time": 0.7,
    "vital_signs": 0.5,
    "clinical_memory_confirmation": 0.3,
}


def _gain(target: str, context: ActionContext | None = None) -> float:
    """How much answering this is worth, planner first, static table second.

    The static table only knows the six workflow slots that existed when the
    conversation walked a fixed order. An adaptive target such as
    ``headache.course`` is not in it and would otherwise fall to the same
    default as everything else, silently flattening the planner's ranking back
    into an arbitrary one.
    """
    if context is not None and target in context.target_information_gain:
        return context.target_information_gain[target]
    return _INFORMATION_GAIN.get(target, 0.6)


def _exhausted(context: ActionContext, target: str) -> bool:
    """Whether this target has been asked enough times already."""
    return (
        context.asked_targets.get(target, 0) >= MAX_REPEATS_PER_TARGET
        or target in context.accepted_unknown_targets
    )


def select_next_best_action(context: ActionContext) -> NextBestAction:
    """Choose one action. Deterministic, ordered by fixed safety precedence.

    This is not a language model. Safety states resolve to a single permitted
    action, and only once the case is clinically quiet does the choice open up
    to questioning, retrieval or stopping. A model may later propose an
    alternative for the questioning band, but it enters through the validator
    and can never reach the bands above.
    """
    safety_state = context.safety_state

    if safety_state == "CONFIRMED_RED_FLAG":
        return NextBestAction(
            action_type="ESCALATE",
            rationale_code="CONFIRMED_RED_FLAG",
            priority=100,
            policy_dependencies=("red_flag_lifecycle",),
            safety_constraints=("no_further_questioning", "no_esi_from_planner"),
            audit_metadata={"safety_state": safety_state},
        )

    if safety_state == "SAFETY_FALLBACK":
        return NextBestAction(
            action_type="ESCALATE",
            rationale_code="SAFETY_FALLBACK_PENDING_REVIEW",
            priority=95,
            policy_dependencies=("red_flag_lifecycle",),
            safety_constraints=("precaution_not_a_finding",),
            audit_metadata={"safety_state": safety_state},
        )

    if safety_state == "REQUIRES_ESCALATION":
        # The contextual validator could not decide. We ask rather than guess.
        return NextBestAction(
            action_type="CLARIFY",
            rationale_code="SAFETY_CONTEXT_UNRESOLVED",
            target="red_flag_context",
            priority=90,
            policy_dependencies=("contextual_emergency_validation",),
            safety_constraints=("must_not_resolve_by_assumption",),
            audit_metadata={"safety_state": safety_state},
        )

    if context.intent not in {"TRIAGE_NEW_SYMPTOM", "TRIAGE_FOLLOW_UP"}:
        return NextBestAction(
            action_type="EXPLAIN",
            rationale_code="NO_TRIAGE_INTENT",
            priority=20,
            audit_metadata={"intent": context.intent},
        )

    # A patient contradiction must be settled before anything is concluded.
    for field_name in context.unresolved_contradictions:
        target = f"contradiction_{field_name}"
        if not _exhausted(context, target):
            return NextBestAction(
                action_type="CLARIFY",
                rationale_code="PATIENT_CONTRADICTION_OPEN",
                target=target,
                priority=85,
                expected_information_gain=1.0,
                policy_dependencies=("contradiction_resolution",),
                audit_metadata={"field": field_name},
            )

    # An unresolved back-reference blocks correct attribution of later facts.
    if context.has_unresolved_reference and not _exhausted(context, "entity_reference"):
        return NextBestAction(
            action_type="RETRIEVE_MEMORY",
            rationale_code="UNRESOLVED_REFERENCE",
            target="entity_reference",
            priority=80,
            required_context=("conversation_memory",),
            audit_metadata={},
        )

    # Ambiguity that could move triage is clarified, never assumed away.
    for target in context.relevant_uncertainties:
        if not _exhausted(context, target):
            return NextBestAction(
                action_type="CLARIFY",
                rationale_code="CLINICALLY_RELEVANT_UNCERTAINTY",
                target=target,
                priority=70,
                expected_information_gain=_gain(target, context),
                policy_dependencies=("risk_aware_readiness",),
                audit_metadata={},
            )

    # A relevant change invalidated an earlier conclusion.
    if context.requires_reassessment and context.has_conclusion:
        return NextBestAction(
            action_type="REASSESS",
            rationale_code="STALE_ASSESSMENT_AFTER_CHANGE",
            priority=75,
            policy_dependencies=("evidence_gate", "esi_policy"),
            safety_constraints=("no_esi_from_planner",),
            audit_metadata={},
        )

    # Ask only for what could change this presentation's triage, best first.
    askable = [
        target
        for target in context.missing_critical_fields
        if not _exhausted(context, target)
    ]
    if askable:
        target = max(askable, key=lambda item: _gain(item, context))
        return NextBestAction(
            action_type="ASK",
            rationale_code="DECISION_RELEVANT_UNKNOWN",
            target=target,
            priority=60,
            expected_information_gain=_gain(target, context),
            policy_dependencies=("risk_aware_readiness",),
            audit_metadata={
                "decision_relevant": target in context.decision_relevant_unknowns,
            },
        )

    # Everything askable has been asked as often as policy allows. Move on with
    # the answer recorded as UNKNOWN rather than asking again or inventing one.
    if context.missing_critical_fields and not askable:
        return NextBestAction(
            action_type="EXPLAIN",
            rationale_code="REPEATED_WITHOUT_PROGRESS",
            priority=40,
            safety_constraints=("must_not_fabricate_missing_value",),
            audit_metadata={
                "unanswered": list(context.missing_critical_fields),
            },
        )

    if context.next_step == "retrieve_evidence":
        return NextBestAction(
            action_type="RETRIEVE_RAG",
            rationale_code="READY_FOR_EVIDENCE",
            priority=55,
            policy_dependencies=("evidence_gate", "protocol_whitelist"),
            safety_constraints=("citations_must_be_subset",),
            audit_metadata={},
        )

    if context.readiness_outcome == "READY":
        return NextBestAction(
            action_type="END",
            rationale_code="SUFFICIENT_TO_CONCLUDE",
            priority=10,
            audit_metadata={"readiness": context.readiness_outcome},
        )

    # Reaching here means nothing is askable yet readiness still says the case
    # is not ready. The readiness evaluator does not produce that combination
    # today -- it reports NOT_READY only when something is missing -- so this
    # is a guard against a future change quietly turning "we do not know
    # enough" into a conclusion. Stopping is a claim; we decline to make it.
    return NextBestAction(
        action_type="EXPLAIN",
        rationale_code="REPEATED_WITHOUT_PROGRESS",
        priority=15,
        safety_constraints=("must_not_conclude_while_not_ready",),
        audit_metadata={
            "readiness": context.readiness_outcome,
            "nothing_askable": True,
        },
    )


def deterministic_fallback_action(context: ActionContext) -> NextBestAction:
    """What to do when a planner is unavailable.

    Never fabricates. Falls back to the same deterministic selector, which is
    what the system uses normally anyway; the distinction is recorded so an
    outage is visible in the audit trail rather than looking like a choice.
    """
    action = select_next_best_action(context)
    return NextBestAction(
        action_type=action.action_type,
        rationale_code="PLANNER_UNAVAILABLE_FALLBACK",
        target=action.target,
        priority=action.priority,
        expected_information_gain=action.expected_information_gain,
        required_context=action.required_context,
        policy_dependencies=action.policy_dependencies,
        safety_constraints=action.safety_constraints,
        audit_metadata={**action.audit_metadata, "planner": "unavailable"},
    )
