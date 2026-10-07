"""Adaptive question planning: what is worth asking next, and when to stop.

The old conversation walked a fixed slot order -- complaint, onset, severity,
associated symptoms, vitals, EHR -- and then handed the patient a form and let
*them* decide whether enough had been collected. Two things were wrong with
that. The order was the same for a sprained ankle and a thunderclap headache,
and the stopping decision belonged to the person least able to make it.

This module replaces both. Every turn it reads the problem state, works out
what is still unknown *for these problems*, ranks the open questions by what
answering them would be worth, and returns a structured judgement of whether
the case is ready for the confirmation checkpoint.

Two properties matter more than the ranking itself:

1. **Sufficient is not complete.** A case reaches
   ``SUFFICIENT_FOR_CONFIRMATION`` while optional detail is still unknown. An
   attribute that cannot change the triage decision never blocks progress.
2. **Stopping is semantic first, bounded second.** Questioning ends because
   nothing valuable is left to ask, not because a counter ran out. The counters
   exist so a planning bug cannot produce a twenty-question interrogation, and
   they are recorded separately in the audit when they fire.

This module selects; it does not execute, and it does not decide what is
*allowed*. The action validator and the deterministic clinical gates keep that
authority, exactly as before.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from src.agents.problem_state import (
    VITAL_ATTRIBUTE_KEYS,
    Problem,
    ProblemState,
)

SufficiencyLevel = Literal[
    # A safety-relevant unknown is open. Ask before anything else.
    "SAFETY_CRITICAL_MISSING",
    # Something that could move the ESI decision is unknown.
    "DECISION_CRITICAL_MISSING",
    # Only detail that would be nice to have remains. Does not block.
    "USEFUL_BUT_OPTIONAL",
    # Enough to put the summary to the patient for confirmation.
    "SUFFICIENT_FOR_CONFIRMATION",
]

# Why questioning stopped, when it stopped for a reason other than sufficiency.
StopReason = Literal[
    "SEMANTIC_SUFFICIENT",
    "QUESTION_BUDGET_EXHAUSTED",
    "NO_INFORMATION_GAIN",
    "ALL_TARGETS_EXHAUSTED",
]

# Ordering weight per importance class. Not a clinical ranking: it only orders
# competing open questions so the most consequential one is asked first.
_IMPORTANCE_GAIN: dict[str, float] = {
    "SAFETY": 1.0,
    "DECISION": 0.7,
    "USEFUL": 0.3,
}

# The primary problem's gaps are worth marginally more than a secondary
# problem's, so a two-symptom case characterises the leading complaint first
# instead of interleaving.
_PRIMARY_BONUS = 0.08
# A problem the patient has just raised is worth folding in promptly, so it is
# not left uncharacterised while the conversation finishes older business.
_NEW_PROBLEM_BONUS = 0.05

# A red-flag probe about a problem nobody has described yet is a question the
# answer to which cannot be interpreted. "Is this the worst headache of your
# life?" asked before "when did it start?" reads as an interrogation and buys
# less than the basic characterisation it jumped ahead of. Safety questions are
# not skipped -- they are asked once the problem has been opened, which in
# practice is the very next question.
_UNCHARACTERISED_SAFETY_PENALTY = 0.45

# How many questions may be asked in a row before the runtime stops regardless
# of what is still unknown. Deliberately generous: it is a circuit breaker, not
# a question count. Configurable via Settings.
DEFAULT_MAX_CONSECUTIVE_QUESTIONS = 8


@dataclass(frozen=True)
class QuestionCandidate:
    """One thing worth asking, with the problem it belongs to."""

    # Planner target: "<concept>.<attribute>", "symptom.<x>" or "vital.<x>".
    target: str
    problem_concept: str
    problem_label: str
    attribute: str
    importance: str
    reason_vi: str
    expected_information_gain: float
    # The canonical key an answer will be recorded under.
    canonical_key: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "problem": self.problem_concept,
            "attribute": self.attribute,
            "importance": self.importance,
            "expected_information_gain": round(self.expected_information_gain, 3),
            "canonical_key": self.canonical_key,
        }


@dataclass
class QuestionPlan:
    """This turn's judgement: what to ask, and whether to stop asking."""

    sufficiency: SufficiencyLevel
    candidates: list[QuestionCandidate] = field(default_factory=list)
    # Targets that were worth asking but have been put to the patient as often
    # as policy allows. Recorded as accepted-unknown rather than re-asked.
    exhausted_targets: list[str] = field(default_factory=list)
    stop_reason: StopReason | None = None
    consecutive_questions: int = 0

    @property
    def next_question(self) -> QuestionCandidate | None:
        return self.candidates[0] if self.candidates else None

    @property
    def should_ask(self) -> bool:
        """Ask only while something blocking is open and a candidate exists."""
        return bool(self.candidates) and self.sufficiency in {
            "SAFETY_CRITICAL_MISSING",
            "DECISION_CRITICAL_MISSING",
        }

    @property
    def is_sufficient(self) -> bool:
        return self.sufficiency in {
            "SUFFICIENT_FOR_CONFIRMATION",
            "USEFUL_BUT_OPTIONAL",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "sufficiency": self.sufficiency,
            "stop_reason": self.stop_reason,
            "consecutive_questions": self.consecutive_questions,
            "candidates": [item.to_dict() for item in self.candidates[:6]],
            "exhausted_targets": list(self.exhausted_targets),
        }


# Characterisation attributes whose importance is judged relative to the
# problem's place in the presentation. A safety probe is never downgraded, and
# neither is the question of how a secondary problem relates to the main one --
# that relationship is often what the acuity turns on.
_ALWAYS_BLOCKING_ATTRIBUTES = frozenset({"relation_to_primary"})


def _effective_importance(problem: Problem, attribute: str, declared: str) -> str:
    """How much this gap blocks *here*, as opposed to how relevant it is.

    The profile table states clinical relevance and is reviewed as such. This
    applies the one judgement the table cannot express: characterising a
    secondary complaint in the same depth as the leading one buys little for a
    triage decision and costs the patient several more questions. Safety probes
    are unaffected, so nothing time-critical is downgraded by being mentioned
    second.
    """
    if declared == "SAFETY" or problem.is_primary:
        return declared
    if attribute in _ALWAYS_BLOCKING_ATTRIBUTES:
        return declared
    return "USEFUL" if declared == "DECISION" else declared


def _target_for(problem: Problem, attribute: str, canonical_key: str) -> str:
    """The planner target for one problem attribute.

    A shared canonical key (a probed symptom, a vital sign) uses that key
    directly, because the answer is the same fact whichever problem prompted
    the question. Anything else is scoped to the problem, so an answer about
    the headache cannot be read as an answer about the nausea.
    """
    if canonical_key.startswith(("symptom.", "vital.")):
        return canonical_key
    return f"{problem.concept}.{attribute}"


def collect_candidates(
    problem_state: ProblemState,
    *,
    asked_targets: dict[str, int] | None = None,
    accepted_unknown_targets: set[str] | frozenset[str] | None = None,
    max_repeats_per_target: int = 2,
    vitals_available: bool = True,
) -> tuple[list[QuestionCandidate], list[str]]:
    """Every open question worth asking, best first, plus the exhausted ones."""
    asked = dict(asked_targets or {})
    accepted = set(accepted_unknown_targets or ())
    candidates: list[QuestionCandidate] = []
    exhausted: list[str] = []

    for problem in problem_state.active_problems:
        for attribute, state in problem.facts.items():
            if state.is_answered:
                # A denial is an answer. Asking again would be asking a
                # question the patient already answered.
                continue
            target = _target_for(problem, attribute, state.canonical_key)
            if target in accepted or asked.get(target, 0) >= max_repeats_per_target:
                exhausted.append(target)
                continue
            if (
                attribute in VITAL_ATTRIBUTE_KEYS
                or state.canonical_key.startswith("vital.")
            ) and not vitals_available:
                # The patient has already said they have no way to measure.
                # That is an answer about the whole class, not a gap.
                continue
            importance = _effective_importance(problem, attribute, state.importance)
            gain = _IMPORTANCE_GAIN.get(importance, 0.3)
            if importance == "SAFETY" and not problem.known_facts:
                gain -= _UNCHARACTERISED_SAFETY_PENALTY
            if problem.is_primary:
                gain += _PRIMARY_BONUS
            if problem.concept in problem_state.newly_mentioned:
                gain += _NEW_PROBLEM_BONUS
            if state.is_uncertain:
                # A hedged answer is worth resolving slightly more than a
                # silence of the same importance: we know it matters here.
                gain += 0.04
            candidates.append(
                QuestionCandidate(
                    target=target,
                    problem_concept=problem.concept,
                    problem_label=problem.label_vi,
                    attribute=attribute,
                    importance=importance,
                    reason_vi=state.reason_vi,
                    expected_information_gain=gain,
                    canonical_key=state.canonical_key,
                )
            )

    # One question per canonical key: two problems may both want to know about
    # vomiting, and asking twice is asking the same question twice.
    seen: set[str] = set()
    unique: list[QuestionCandidate] = []
    for candidate in sorted(
        candidates,
        key=lambda item: item.expected_information_gain,
        reverse=True,
    ):
        if candidate.canonical_key in seen:
            continue
        seen.add(candidate.canonical_key)
        unique.append(candidate)
    return unique, sorted(set(exhausted))


def assess_sufficiency(
    candidates: list[QuestionCandidate],
    *,
    has_complaint: bool,
) -> SufficiencyLevel:
    """Classify what is still missing, in the terms the stopping policy uses."""
    if not has_complaint:
        # Without an attributable complaint there is nothing to characterise
        # and nothing to retrieve against. This is a structural gap, not a
        # clinical judgement.
        return "DECISION_CRITICAL_MISSING"
    importances = {candidate.importance for candidate in candidates}
    if "SAFETY" in importances:
        return "SAFETY_CRITICAL_MISSING"
    if "DECISION" in importances:
        return "DECISION_CRITICAL_MISSING"
    if "USEFUL" in importances:
        # Open, but not a reason to keep the patient answering questions.
        return "USEFUL_BUT_OPTIONAL"
    return "SUFFICIENT_FOR_CONFIRMATION"


def plan_questions(
    problem_state: ProblemState,
    *,
    asked_targets: dict[str, int] | None = None,
    accepted_unknown_targets: set[str] | frozenset[str] | None = None,
    consecutive_questions: int = 0,
    max_consecutive_questions: int = DEFAULT_MAX_CONSECUTIVE_QUESTIONS,
    max_repeats_per_target: int = 2,
    vitals_available: bool = True,
    information_gained_last_turn: bool = True,
) -> QuestionPlan:
    """Decide what to ask next, or that the case is ready for confirmation.

    Termination is semantic first: when nothing safety- or decision-relevant is
    open, the plan is sufficient and questioning stops even though optional
    detail remains unknown. The bounded checks below can only stop it *earlier*,
    never keep it going, and each records why.
    """
    candidates, exhausted = collect_candidates(
        problem_state,
        asked_targets=asked_targets,
        accepted_unknown_targets=accepted_unknown_targets,
        max_repeats_per_target=max_repeats_per_target,
        vitals_available=vitals_available,
    )
    has_complaint = bool(problem_state.active_problems)
    sufficiency = assess_sufficiency(candidates, has_complaint=has_complaint)

    plan = QuestionPlan(
        sufficiency=sufficiency,
        candidates=candidates,
        exhausted_targets=exhausted,
        consecutive_questions=consecutive_questions,
    )

    if not plan.should_ask:
        plan.stop_reason = "SEMANTIC_SUFFICIENT" if has_complaint else None
        return plan

    # -- bounded safeguards. Each may stop questioning early; none may extend it.
    if consecutive_questions >= max_consecutive_questions:
        plan.candidates = []
        plan.sufficiency = "SUFFICIENT_FOR_CONFIRMATION"
        plan.stop_reason = "QUESTION_BUDGET_EXHAUSTED"
        return plan

    if not information_gained_last_turn and consecutive_questions >= 2:
        # Two questions in a row have produced no new canonical fact. Asking a
        # third is not persistence; it is a loop the patient cannot get out of.
        plan.candidates = []
        plan.sufficiency = "SUFFICIENT_FOR_CONFIRMATION"
        plan.stop_reason = "NO_INFORMATION_GAIN"
        return plan

    return plan


def plan_from_agent_state(state: dict[str, Any]) -> QuestionPlan:
    """Build this turn's plan from a serialized agent state."""
    from src.agents.problem_state import build_problem_state_from_agent_state

    loop = dict(state.get("action_loop_state") or {})
    problem_state = build_problem_state_from_agent_state(state)
    return plan_questions(
        problem_state,
        asked_targets=dict(loop.get("asked_targets") or {}),
        accepted_unknown_targets=set(loop.get("accepted_unknown_targets") or ()),
        consecutive_questions=int(loop.get("consecutive_questions") or 0),
        max_consecutive_questions=_max_consecutive_questions(),
        vitals_available=state.get("vital_signs_status") != "UNAVAILABLE_CONFIRMED",
        information_gained_last_turn=bool(state.get("information_gained_last_turn", True)),
    )


def _max_consecutive_questions() -> int:
    try:
        from src.config import get_settings

        return int(get_settings().adaptive_max_consecutive_questions)
    except Exception:  # noqa: BLE001 - configuration must never break planning
        return DEFAULT_MAX_CONSECUTIVE_QUESTIONS
