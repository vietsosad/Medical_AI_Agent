"""Problem-oriented view of canonical state: what is wrong, and what we still
do not know about each of those things.

``ClinicalStateView`` answers "is this fact true?". That is the right question
for a gate and the wrong question for a conversation, because it forces the
planner to reason over a flat namespace of keys. A patient who says "tôi bị đau
đầu và buồn nôn" has two *problems*, each with its own unanswered
characterisation, and a planner that cannot see that structure can only walk a
global checklist -- which is exactly the fixed-form behaviour this module
exists to remove.

Nothing here is a second source of truth. Every problem and every fact is a
projection of :class:`CanonicalPatientState`; this module performs no I/O,
records nothing, and cannot assert a fact the canonical layer does not already
hold.

Attribute attribution is deliberately conservative:

* An entity-scoped observation (``headache.severity_score``, written by the
  extractor when the patient referred back to a symptom) belongs to that
  problem and to no other.
* A global observation (``severity_score``) is attributed to the *primary*
  problem only. Copying it onto every active problem would invent a fact:
  "6/10" said about a headache is not a claim about the nausea.
* Everything else stays UNKNOWN, which is not ``False`` and not NEGATED.

.. warning::
   The relevance catalogue below (:data:`PROBLEM_PROFILES`) is
   ``PENDING_CLINICAL_REVIEW`` internal configuration, exactly like
   :mod:`src.agents.clinical_requirements`. It decides *what is worth asking
   about*, never what is clinically true and never what ESI applies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_requirements import (
    POLICY_REVIEW_STATUS,
    POLICY_VERSION,
)
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.nodes.fact_extraction import SYMPTOM_DISPLAY_VI, describe_fact_key

ProblemStatus = Literal["ACTIVE", "UNCERTAIN", "DENIED", "HISTORICAL"]

# How much a missing answer matters. Deliberately not a fixed question order:
# the same attribute is safety-critical for one presentation and optional for
# another, so priority is a property of (problem, attribute), not of a slot.
FactImportance = Literal["SAFETY", "DECISION", "USEFUL"]


@dataclass(frozen=True)
class RelevantFact:
    """One thing worth knowing about one problem, and how much it matters."""

    # Attribute name as the planner and question engine know it.
    attribute: str
    importance: FactImportance
    # Why this is worth asking, in the patient's language, for audit and for
    # the question engine's fallback wording.
    reason_vi: str
    # A canonical symptom key to probe rather than a scalar attribute. When
    # set, the answer lands on ``symptom.<key>`` instead of ``<problem>.<attr>``.
    probe_symptom: str | None = None


@dataclass(frozen=True)
class ProblemProfile:
    """The characterisation worth collecting for one kind of problem."""

    concept: str
    relevant_facts: tuple[RelevantFact, ...]


# Attributes shared by most symptomatic presentations. Kept separate so a
# profile declares only what is special about it.
_PAIN_CHARACTERISATION: tuple[RelevantFact, ...] = (
    RelevantFact("onset_time", "DECISION", "thời điểm bắt đầu"),
    RelevantFact("course", "DECISION", "diễn tiến tăng dần hay đột ngột"),
    RelevantFact("severity_score", "DECISION", "mức độ đau 0-10"),
    # Location, character and radiation describe the pain richly but rarely
    # move an acuity decision on their own, so they are collected when the
    # patient offers them and are never a reason to keep asking. A profile that
    # needs one of them as a decision point overrides it (see chest_pain).
    RelevantFact("location", "USEFUL", "vị trí khó chịu"),
    RelevantFact("character", "USEFUL", "tính chất cơn đau"),
    RelevantFact("radiation", "USEFUL", "hướng lan"),
)

_GENERIC_CHARACTERISATION: tuple[RelevantFact, ...] = (
    RelevantFact("onset_time", "DECISION", "thời điểm bắt đầu"),
    RelevantFact("course", "USEFUL", "diễn tiến"),
    RelevantFact("severity_score", "USEFUL", "mức độ khó chịu"),
)


def _profile(concept: str, *extra: RelevantFact, base: tuple[RelevantFact, ...]) -> ProblemProfile:
    return ProblemProfile(concept=concept, relevant_facts=(*base, *extra))


# PENDING_CLINICAL_REVIEW. Written by engineers to replace a global checklist.
PROBLEM_PROFILES: dict[str, ProblemProfile] = {
    profile.concept: profile
    for profile in (
        _profile(
            "headache",
            RelevantFact(
                "worst_ever",
                "SAFETY",
                "cơn đau đầu dữ dội nhất từng có",
            ),
            RelevantFact(
                "associated_neuro",
                "SAFETY",
                "yếu liệt, nói khó hoặc nhìn mờ kèm theo",
            ),
            RelevantFact("fever", "DECISION", "sốt kèm theo", probe_symptom="fever"),
            base=_PAIN_CHARACTERISATION,
        ),
        _profile(
            "chest_pain",
            RelevantFact(
                "associated_dyspnea",
                "SAFETY",
                "khó thở kèm theo",
                probe_symptom="dyspnea",
            ),
            RelevantFact(
                "associated_diaphoresis",
                "SAFETY",
                "vã mồ hôi kèm theo",
                probe_symptom="diaphoresis",
            ),
            RelevantFact("exertion", "DECISION", "đau tăng khi gắng sức"),
            # Radiation is a decision point for chest pain specifically, so it
            # is promoted back above the shared default.
            RelevantFact("radiation", "DECISION", "hướng lan"),
            base=_PAIN_CHARACTERISATION,
        ),
        _profile(
            "abdominal_pain",
            RelevantFact("fever", "DECISION", "sốt kèm theo", probe_symptom="fever"),
            RelevantFact(
                "associated_vomiting",
                "DECISION",
                "nôn kèm theo",
                probe_symptom="vomiting",
            ),
            RelevantFact("bowel_change", "USEFUL", "thay đổi đại tiện"),
            base=_PAIN_CHARACTERISATION,
        ),
        _profile(
            "dyspnea",
            RelevantFact("spo2", "SAFETY", "SpO2 nếu đo được"),
            RelevantFact("rest_or_exertion", "DECISION", "khó thở khi nghỉ hay gắng sức"),
            base=_GENERIC_CHARACTERISATION,
        ),
        _profile(
            "nausea",
            RelevantFact(
                "vomiting",
                "DECISION",
                "có nôn hay không",
                probe_symptom="vomiting",
            ),
            RelevantFact("frequency", "USEFUL", "số lần"),
            RelevantFact("relation_to_primary", "USEFUL", "liên quan tới triệu chứng chính"),
            base=_GENERIC_CHARACTERISATION,
        ),
        _profile(
            "vomiting",
            RelevantFact("frequency", "DECISION", "số lần nôn"),
            RelevantFact("blood", "SAFETY", "nôn ra máu"),
            base=_GENERIC_CHARACTERISATION,
        ),
        _profile(
            "dizziness",
            RelevantFact("syncope", "SAFETY", "có ngất hay không", probe_symptom="syncope"),
            RelevantFact("relation_to_primary", "USEFUL", "liên quan tới triệu chứng chính"),
            base=_GENERIC_CHARACTERISATION,
        ),
        _profile(
            "fever",
            RelevantFact("temperature", "DECISION", "nhiệt độ đo được"),
            base=_GENERIC_CHARACTERISATION,
        ),
        _profile("back_pain", base=_PAIN_CHARACTERISATION),
        _profile("sore_throat", base=_GENERIC_CHARACTERISATION),
        _profile("diarrhea", RelevantFact("frequency", "DECISION", "số lần đi ngoài"), base=_GENERIC_CHARACTERISATION),
        _profile("cough", base=_GENERIC_CHARACTERISATION),
        _profile("rash", base=_GENERIC_CHARACTERISATION),
        _profile("bleeding", RelevantFact("volume", "SAFETY", "lượng máu"), base=_GENERIC_CHARACTERISATION),
        _profile("palpitations", base=_GENERIC_CHARACTERISATION),
        _profile("lightheadedness", base=_GENERIC_CHARACTERISATION),
        _profile("syncope", base=_GENERIC_CHARACTERISATION),
        _profile("seizure", base=_GENERIC_CHARACTERISATION),
        _profile("diaphoresis", base=_GENERIC_CHARACTERISATION),
    )
}

# Used for a complaint the lexicon could not map to a known concept. It still
# gets characterised rather than being dropped from the conversation.
DEFAULT_PROFILE = ProblemProfile(
    concept="unspecified",
    relevant_facts=_GENERIC_CHARACTERISATION,
)

# Attributes whose value lives on a shared canonical key rather than under the
# problem. ``severity_score`` recorded globally means "the severity the patient
# gave", which is about the primary problem and about nothing else.
_GLOBAL_ATTRIBUTE_KEYS: dict[str, str] = {
    "onset_time": "onset_time",
    "severity_score": "severity_score",
    "radiation": "radiation",
    "course": "course",
    "character": "character",
    "location": "location",
    "worst_ever": "worst_ever",
    "frequency": "frequency",
}

# Objective measurements the agent may ask for, mapped to their canonical key.
VITAL_ATTRIBUTE_KEYS: dict[str, str] = {
    "temperature": "vital.temperature_c",
    "spo2": "vital.spo2",
    "heart_rate": "vital.heart_rate",
    "blood_pressure": "vital.systolic_bp",
    "respiratory_rate": "vital.respiratory_rate",
}


def profile_for_concept(concept: str) -> ProblemProfile:
    return PROBLEM_PROFILES.get(concept, DEFAULT_PROFILE)


@dataclass(frozen=True)
class ProblemFactState:
    """What we know about one attribute of one problem."""

    attribute: str
    # The canonical key the answer is (or would be) recorded under.
    canonical_key: str
    status: str
    value: Any
    importance: FactImportance
    reason_vi: str
    # The patient was asked and said they could not tell us. Clinically this is
    # still UNCERTAIN and is never a finding; conversationally it is settled.
    declined: bool = False

    @property
    def is_answered(self) -> bool:
        """KNOWN, NEGATED and an explicit "I don't know" are all answers.

        UNKNOWN -- nobody has said anything -- is not, and a hedged report is
        not either: it is worth one clarification, which the repeat limit
        bounds.
        """
        return self.status in {"KNOWN", "NEGATED"} or self.declined

    @property
    def is_uncertain(self) -> bool:
        return self.status == "UNCERTAIN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "attribute": self.attribute,
            "canonical_key": self.canonical_key,
            "status": self.status,
            "value": self.value,
            "importance": self.importance,
            "declined": self.declined,
        }


@dataclass
class Problem:
    """One thing the patient is complaining of, and its characterisation."""

    concept: str
    label_vi: str
    status: ProblemStatus
    is_primary: bool
    facts: dict[str, ProblemFactState] = field(default_factory=dict)
    first_turn_id: str = ""
    last_turn_id: str = ""
    mention_count: int = 1

    @property
    def known_facts(self) -> dict[str, Any]:
        return {
            name: state.value
            for name, state in self.facts.items()
            if state.status == "KNOWN"
        }

    @property
    def unknown_relevant_facts(self) -> list[str]:
        return [
            name for name, state in self.facts.items() if not state.is_answered
        ]

    def missing_by_importance(self, importance: FactImportance) -> list[str]:
        return [
            name
            for name, state in self.facts.items()
            if not state.is_answered and state.importance == importance
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "label": self.label_vi,
            "status": self.status,
            "is_primary": self.is_primary,
            "mention_count": self.mention_count,
            "facts": {
                name: state.to_dict()
                for name, state in self.facts.items()
                if state.is_answered or state.is_uncertain
            },
            "unknown_relevant_facts": self.unknown_relevant_facts,
        }


@dataclass
class ProblemState:
    """The whole picture: active problems plus patient-level context."""

    problems: list[Problem] = field(default_factory=list)
    denied_concepts: list[str] = field(default_factory=list)
    historical_concepts: list[str] = field(default_factory=list)
    vitals: dict[str, Any] = field(default_factory=dict)
    demographics: dict[str, Any] = field(default_factory=dict)
    medications: list[Any] = field(default_factory=list)
    # Concepts whose first mention is the most recent turn. The planner uses
    # this to fold a mid-conversation symptom into planning without restarting
    # intake.
    newly_mentioned: list[str] = field(default_factory=list)
    policy_version: str = POLICY_VERSION
    review_status: str = POLICY_REVIEW_STATUS

    @property
    def active_problems(self) -> list[Problem]:
        return [item for item in self.problems if item.status in {"ACTIVE", "UNCERTAIN"}]

    def problem(self, concept: str) -> Problem | None:
        return next((item for item in self.problems if item.concept == concept), None)

    @property
    def primary(self) -> Problem | None:
        return next((item for item in self.active_problems if item.is_primary), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "review_status": self.review_status,
            "problems": [item.to_dict() for item in self.active_problems],
            "denied_concepts": list(self.denied_concepts),
            "historical_concepts": list(self.historical_concepts),
            "newly_mentioned": list(self.newly_mentioned),
            "global": {
                "vitals": dict(self.vitals),
                "demographics": dict(self.demographics),
                "medications": list(self.medications),
            },
        }

    def render_tree(self) -> str:
        """A compact human-readable outline, for transcripts and audit logs."""
        lines: list[str] = ["Active problems"]
        active = self.active_problems
        for index, problem in enumerate(active):
            branch = "└─" if index == len(active) - 1 else "├─"
            spacer = "   " if index == len(active) - 1 else "│  "
            marker = " (primary)" if problem.is_primary else ""
            lines.append(f"{branch} {problem.concept}{marker}")
            names = list(problem.facts)
            for position, name in enumerate(names):
                state = problem.facts[name]
                leaf = "└─" if position == len(names) - 1 else "├─"
                shown = state.value if state.is_answered else "?"
                if state.status == "NEGATED":
                    shown = f"không ({shown})" if shown not in (None, "") else "không"
                lines.append(f"{spacer}{leaf} {name}: {shown}")
        if self.newly_mentioned:
            lines.append("")
            lines.append("Newly mentioned")
            for index, concept in enumerate(self.newly_mentioned):
                branch = "└─" if index == len(self.newly_mentioned) - 1 else "├─"
                lines.append(f"{branch} {concept}")
        return "\n".join(lines)


def _label(concept: str, view: ClinicalStateView | None = None) -> str:
    known = SYMPTOM_DISPLAY_VI.get(concept)
    if known:
        return known
    if view is not None:
        # An unmapped complaint is shown in the patient's own wording. A slug
        # ("dau_o_vung_tran") is an internal identifier and must never reach a
        # question, and the neutral fallback below says nothing useful when the
        # patient's own phrase is available and is exactly what they said.
        phrase = view.current_value(f"complaint.{concept}")
        if phrase:
            return str(phrase)[:80]
    return describe_fact_key(f"symptom.{concept}")


def _problem_status(view: ClinicalStateView, key: str) -> ProblemStatus | None:
    reading = view.read(key)
    if reading.is_present:
        return "ACTIVE"
    if reading.is_uncertain:
        return "UNCERTAIN"
    if reading.is_negated:
        return "DENIED"
    if view.historical_values(key):
        return "HISTORICAL"
    return None


DECLINED_NOTE = "declined_unknown"


def _declined(view: ClinicalStateView, key: str) -> bool:
    observation = view.canonical.observation_of(key)
    return bool(observation and observation.note == DECLINED_NOTE)


def _recorded_at(view: ClinicalStateView, key: str) -> str:
    observation = view.canonical.observation_of(key)
    return observation.recorded_at if observation else ""


def _resolve_attribute(
    view: ClinicalStateView,
    concept: str,
    relevant: RelevantFact,
    *,
    is_primary: bool,
) -> ProblemFactState:
    """Find the canonical observation that answers this attribute, if any."""
    # A symptom probe is answered by the shared symptom key: "do you also have
    # a fever" is the same fact whichever problem prompted the question.
    if relevant.probe_symptom:
        key = f"symptom.{relevant.probe_symptom}"
        reading = view.read(key)
        return ProblemFactState(
            attribute=relevant.attribute,
            canonical_key=key,
            status=reading.status,
            value=reading.value,
            importance=relevant.importance,
            reason_vi=relevant.reason_vi,
            declined=_declined(view, key),
        )

    if relevant.attribute in VITAL_ATTRIBUTE_KEYS:
        key = VITAL_ATTRIBUTE_KEYS[relevant.attribute]
        reading = view.read(key)
        return ProblemFactState(
            attribute=relevant.attribute,
            canonical_key=key,
            status=reading.status,
            value=reading.value,
            importance=relevant.importance,
            reason_vi=relevant.reason_vi,
            declined=_declined(view, key),
        )

    # Entity-scoped first: the extractor writes "<concept>.<attr>" when the
    # patient attached the detail to a symptom they had already named.
    scoped_key = f"{concept}.{relevant.attribute}"
    scoped = view.read(scoped_key)
    global_key = _GLOBAL_ATTRIBUTE_KEYS.get(relevant.attribute)

    def _state(key: str, reading: Any) -> ProblemFactState:
        return ProblemFactState(
            attribute=relevant.attribute,
            canonical_key=key,
            status=reading.status,
            value=reading.value,
            importance=relevant.importance,
            reason_vi=relevant.reason_vi,
            declined=_declined(view, key),
        )

    # Only the primary problem may claim an unattributed value. Attaching
    # "6/10" to every active problem would assert something the patient never
    # said about the others.
    if not (global_key and is_primary):
        if not scoped.is_unknown:
            return _state(scoped_key, scoped)
        return ProblemFactState(
            attribute=relevant.attribute,
            canonical_key=global_key or scoped_key,
            status="UNKNOWN",
            value=None,
            importance=relevant.importance,
            reason_vi=relevant.reason_vi,
        )

    # For the primary problem both keys describe the same thing, so the answer
    # is whichever the patient gave *last*. Preferring the scoped key
    # unconditionally meant a "tôi không rõ" recorded against the question we
    # asked permanently shadowed the number the patient volunteered two turns
    # later -- the severity reached the summary and never reached the query.
    global_reading = view.read(global_key)
    if scoped.is_unknown:
        return _state(global_key, global_reading)
    if global_reading.is_unknown:
        return _state(scoped_key, scoped)
    scoped_at = _recorded_at(view, scoped_key)
    global_at = _recorded_at(view, global_key)
    if global_at > scoped_at:
        return _state(global_key, global_reading)
    return _state(scoped_key, scoped)


def build_problem_state(
    view: ClinicalStateView,
    *,
    current_turn_id: str = "",
) -> ProblemState:
    """Project canonical state into problems, their facts and their gaps."""
    canonical = view.canonical
    concepts: list[tuple[str, ProblemStatus]] = []
    for key in sorted(canonical.facts):
        if not key.startswith("symptom."):
            continue
        concept = key.removeprefix("symptom.")
        status = _problem_status(view, key)
        if status is not None:
            concepts.append((concept, status))

    # A complaint the patient phrased themselves is still a problem worth
    # characterising -- but only when nothing in it was recognised. The legacy
    # slot-filling extractor emits a complaint phrase for every pain-word span
    # it sees ("đau", "đau tăng dần lên", "đau ở vùng trán"), so admitting all
    # of them would turn one headache into five problems and ask the patient to
    # characterise each of the four that do not exist.
    known = {concept for concept, _ in concepts}
    if not concepts:
        for key in sorted(canonical.facts):
            if not key.startswith("complaint."):
                continue
            slug = key.removeprefix("complaint.")
            if slug in known or not view.read(key).is_present:
                continue
            concepts.append((slug, "ACTIVE"))
            known.add(slug)
            break

    # Ordering decides which problem is primary, and mention order is what a
    # patient means by "triệu chứng chính": the thing they led with.
    #
    # The timestamp alone cannot carry that meaning. ``recorded_at`` comes from
    # ``datetime.now()``, whose resolution on Windows is about 15ms -- far
    # coarser than the gap between two symptoms pulled out of the *same*
    # sentence. Those two observations therefore land on an identical timestamp
    # string most of the time, the sort becomes a tie, and a stable sort falls
    # back to the order of ``concepts`` -- which is alphabetical, because it was
    # built by walking ``sorted(canonical.facts)``.
    #
    # The result was that "nhức đầu quá, chóng mặt" made *dizziness* the primary
    # problem, purely because d sorts before h, and it did so only on the runs
    # where the clock happened not to tick mid-extraction. Which symptom drives
    # protocol retrieval is not something that may depend on a clock tick.
    #
    # ``canonical.entities`` is a plain dict, so its keys stay in the order the
    # symptoms were first seen. That insertion order *is* mention order, and it
    # is what breaks the tie now.
    entity_order = {
        entity.normalized: index
        for index, entity in enumerate(canonical.entities.values())
    }
    unseen_rank = len(entity_order)

    def _first_seen(concept: str) -> tuple[str, int]:
        observations = [
            item
            for fact_key, fact in canonical.facts.items()
            if fact_key in {f"symptom.{concept}", f"complaint.{concept}"}
            for item in fact.observations
        ]
        earliest = min(
            (item.recorded_at for item in observations),
            default="",
        )
        return (earliest, entity_order.get(concept, unseen_rank))

    ordered = sorted(concepts, key=lambda item: _first_seen(item[0]))

    problems: list[Problem] = []
    denied: list[str] = []
    historical: list[str] = []
    newly: list[str] = []
    primary_assigned = False
    for concept, status in ordered:
        if status == "DENIED":
            denied.append(concept)
            continue
        if status == "HISTORICAL":
            historical.append(concept)
            continue
        entity = canonical.find_entity(concept)
        is_primary = not primary_assigned
        primary_assigned = True
        profile = profile_for_concept(concept)
        problem = Problem(
            concept=concept,
            label_vi=_label(concept, view),
            status=status,
            is_primary=is_primary,
            first_turn_id=entity.first_turn_id if entity else "",
            last_turn_id=entity.last_turn_id if entity else "",
            mention_count=entity.mention_count if entity else 1,
        )
        for relevant in profile.relevant_facts:
            problem.facts[relevant.attribute] = _resolve_attribute(
                view,
                concept,
                relevant,
                is_primary=is_primary,
            )
        problems.append(problem)
        if current_turn_id and problem.first_turn_id == current_turn_id:
            newly.append(concept)

    vitals = {
        key.removeprefix("vital."): view.current_value(key)
        for key in sorted(canonical.facts)
        if key.startswith("vital.") and view.current_value(key) is not None
    }
    demographics = {
        key: view.current_value(key)
        for key in ("age", "sex")
        if view.current_value(key) is not None
    }
    medications = [
        item.value
        for item in canonical.history_of("medication")
        if item.is_active and item.status == "KNOWN"
    ]

    return ProblemState(
        problems=problems,
        denied_concepts=denied,
        historical_concepts=historical,
        vitals=vitals,
        demographics=demographics,
        medications=medications,
        newly_mentioned=newly,
    )


def build_problem_state_from_agent_state(state: dict[str, Any]) -> ProblemState:
    """Convenience for nodes, which hold a serialized turn state."""
    view = ClinicalStateView(
        CanonicalPatientState.from_dict(state.get("canonical_state"))
    )
    return build_problem_state(
        view,
        current_turn_id=str(state.get("current_turn_id") or ""),
    )
