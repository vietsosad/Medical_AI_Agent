"""Per-conversation state. No LLM calls and no corpus knowledge here.

Three-state fact model, kept explicit rather than inferred:

- absent from both ``facts`` and ``unknown_facts`` -> not asked yet (null)
- present in ``unknown_facts`` -> asked, patient could not/would not answer
- present in ``facts`` -> a schema-validated value is known

``qualitative_observations`` is a separate fourth channel: descriptive wording
that hasn't (or can't) become an exact value. It can coexist with an unresolved
entry in ``needs_precision`` when the fact target requires an exact measurement
but the patient only gave a vague description (see ``reporting_style`` in
fact_targets.jsonl).

One conversation can triage more than one person, but only one at a time (see
``switch_subject``): the fields below (``concepts`` through
``resource_count_estimated``) always describe whichever person -- the patient
themself (SELF) or one specific other person they named (OTHER_PERSON) -- is
currently active. Every other module in this package (tools.py, decision.py,
agent.py) reads/writes these fields exactly as before switching existed; they
are simply "whoever we're asking about right now", not necessarily the
patient. Switching parks the outgoing subject's state and restores (or starts
fresh for) the incoming one, so going back to a person already discussed
resumes their progress instead of losing it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    # Whoever `concepts`..`resource_count_estimated` below currently describe:
    # "SELF" (the patient) or "OTHER_PERSON" (someone they're asking about).
    subject_type: str = "SELF"
    # For OTHER_PERSON only: a short Vietnamese phrase identifying who, already
    # in the form the assistant should use when addressing the patient about
    # them (e.g. "con của bạn", "bạn của bạn") -- see prompts.py. Empty for SELF.
    subject_label: str = ""
    # Snapshots of every subject other than the currently active one, keyed by
    # subject_key ("SELF" or f"OTHER:{label}") -- see switch_subject. Lets the
    # patient go back to a person already discussed without losing what was
    # already recorded for them.
    parked_subjects: dict[str, dict[str, Any]] = field(default_factory=dict)

    concepts: set[str] = field(default_factory=set)
    # Order concepts were first asserted in, most-recent last. Used to prioritise
    # questions toward whatever the patient just brought up.
    concept_order: list[str] = field(default_factory=list)

    facts: dict[str, Any] = field(default_factory=dict)
    qualitative_observations: dict[str, str] = field(default_factory=dict)
    unknown_facts: set[str] = field(default_factory=set)
    needs_precision: set[str] = field(default_factory=set)

    # Union of every protocol atom's id ever retrieved this session, in
    # first-seen order. Each turn's retrieve_atoms() call is keyed on that
    # turn's raw message text alone -- a late confirmation reply like "đánh
    # giá đi" carries no clinical signal and can knock a genuinely-matching
    # atom out of that turn's top-k window even though every fact it needs is
    # already known. Accumulating across turns means a match found earlier in
    # the conversation is never lost to a later turn's weak retrieval query,
    # while each turn's fresh retrieve_atoms() call still runs so atoms
    # relevant only to newly-mentioned symptoms keep getting discovered.
    seen_atom_ids: list[str] = field(default_factory=list)
    # Best (max) cosine relevance score ever observed for each atom_id in
    # seen_atom_ids, across every turn it was retrieved on -- keyed like
    # seen_atom_ids, but only populated for atoms that came through
    # retrieve_atoms_scored (decision.py). Lets agent.py require a stricter
    # confidence bar (MIN_ATOM_RELEVANCE_SCORE_FOR_PROACTIVE_ASK) before an
    # atom-only-linked fact gets proactively asked, without weakening
    # MIN_ATOM_RELEVANCE_SCORE's own recall for seen_atom_ids/ESI matching.
    atom_relevance_score: dict[str, float] = field(default_factory=dict)

    # Last non-null retrieval_query Phase A produced via finish_turn (see
    # tools.py/prompts.py) -- an English clinical-register sentence used as
    # decision.py's retrieve_atoms_scored query, replacing the old naive
    # "concept labels + raw Vietnamese message" join. Persisted (not a
    # turn_* field) so a turn where Phase A leaves it null (nothing new to
    # report) still retrieves against the last real picture instead of an
    # empty/degenerate query.
    retrieval_query: str | None = None

    last_question: str | None = None
    # How many consecutive turns the same fact_target_id has been selected
    # as the question to ask without ever getting resolved (Phase A can
    # record a related concept from the patient's answer while forgetting to
    # close out the pending fact_target itself -- see agent.py's stale-question
    # bail-out). Reset to 0 whenever a different fact_target_id is asked.
    stale_question_streak: int = 0
    # Set once all askable facts are resolved and the "anything else, or
    # should I go ahead?" prompt has been shown; cleared either by a
    # confirmed_ready reply or by new askable facts reopening ASK_NEXT.
    confirmation_offered: bool = False
    # Set the first time agent.py attempts to estimate fact_target:resource_count
    # (CLINICIAN_ONLY, so never asked directly -- see resource_estimate.py) at
    # finalisation. Guards that one-shot LLM call from firing again on every
    # later turn of an already-finalised session.
    resource_count_estimated: bool = False

    # Shared across every subject in this conversation, never parked/reset:
    # the transcript is one continuous conversation regardless of who is
    # currently being asked about.
    history: list[tuple[str, str]] = field(default_factory=list)

    # Set once, at session creation, from the EHR profile card the patient
    # picked to open this conversation (see routes_simple_triage.py's /start
    # -- None for an anonymous/unlinked session). Deliberately NOT part of
    # _snapshot_active_subject/switch_subject: this describes the *card*
    # chosen for the whole conversation, not whichever person is currently
    # being discussed, so it must survive every subject switch unchanged.
    # card_relationship is the card's own EHRProfile.relationship_type
    # ("SELF" | "CHILD" | "SPOUSE" | "PARENT" | "SIBLING" | "OTHER"). Used by
    # agent.py's _effective_sex to decide which fact_targets carrying
    # requires_sex are safe to ask: real incident (2026-08-27) -- a fever/
    # abdominal-pain workup proactively asks pregnancy_status of *any*
    # patient regardless of sex (a legitimate protocol differential fact,
    # not tied to what the patient said), which is well-intentioned for an
    # adult woman but a demo-breaking non-sequitur for a male patient (or a
    # male relative asked about on his behalf).
    card_gender: str | None = None
    card_relationship: str | None = None

    # Reset at the start of every process_turn call; lets the orchestrator
    # report what changed *this* turn without the toolbox returning a parallel
    # extraction payload the way the old single-shot extractor did.
    turn_accepted_facts: list[str] = field(default_factory=list)
    turn_observations: list[str] = field(default_factory=list)
    turn_asserted_concepts: list[str] = field(default_factory=list)
    turn_negated_concepts: list[str] = field(default_factory=list)
    tool_log: list[dict[str, Any]] = field(default_factory=list)
    # Debug-only, this turn's slice of tool_log/retrieval -- lets a caller
    # (SimpleDecisionDebugPanel, via decision_snapshot) show exactly which
    # Phase A tool calls and Phase B retrieval scores produced this turn's
    # question, without re-running the turn or reading server logs. Reset
    # every turn just like the turn_* fields above; never persisted (not
    # meaningful across a reload -- the decision_snapshot on the message row
    # already captured it permanently when the turn happened).
    turn_tool_log: list[dict[str, Any]] = field(default_factory=list)
    turn_retrieved_atoms: list[dict[str, Any]] = field(default_factory=list)

    def remember_turn(self, speaker: str, text: str, *, max_turns: int = 10) -> None:
        self.history.append((speaker, text))
        if len(self.history) > max_turns:
            del self.history[: len(self.history) - max_turns]

    def start_turn(self) -> None:
        self.turn_accepted_facts = []
        self.turn_observations = []
        self.turn_asserted_concepts = []
        self.turn_negated_concepts = []
        self.turn_tool_log = []
        self.turn_retrieved_atoms = []

    def assert_concept(self, concept_id: str) -> bool:
        if concept_id in self.concepts:
            return False
        self.concepts.add(concept_id)
        self.concept_order.append(concept_id)
        return True

    def negate_concept(self, concept_id: str) -> bool:
        if concept_id not in self.concepts:
            return False
        self.concepts.discard(concept_id)
        self.concept_order = [c for c in self.concept_order if c != concept_id]
        return True

    @property
    def subject_key(self) -> str:
        if self.subject_type != "OTHER_PERSON":
            return "SELF"
        return f"OTHER:{self.subject_label.strip().lower()}"

    def _snapshot_active_subject(self) -> dict[str, Any]:
        return {
            "subject_type": self.subject_type,
            "subject_label": self.subject_label,
            "concepts": set(self.concepts),
            "concept_order": list(self.concept_order),
            "facts": dict(self.facts),
            "qualitative_observations": dict(self.qualitative_observations),
            "unknown_facts": set(self.unknown_facts),
            "needs_precision": set(self.needs_precision),
            "seen_atom_ids": list(self.seen_atom_ids),
            "atom_relevance_score": dict(self.atom_relevance_score),
            "retrieval_query": self.retrieval_query,
            "last_question": self.last_question,
            "stale_question_streak": self.stale_question_streak,
            "confirmation_offered": self.confirmation_offered,
            "resource_count_estimated": self.resource_count_estimated,
        }

    def _load_subject_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.subject_type = snapshot["subject_type"]
        self.subject_label = snapshot["subject_label"]
        self.concepts = snapshot["concepts"]
        self.concept_order = snapshot["concept_order"]
        self.facts = snapshot["facts"]
        self.qualitative_observations = snapshot["qualitative_observations"]
        self.unknown_facts = snapshot["unknown_facts"]
        self.needs_precision = snapshot["needs_precision"]
        self.seen_atom_ids = snapshot["seen_atom_ids"]
        # .get(): snapshots parked before this field existed (already-persisted
        # pilot sessions) won't have it -- treat as "no confidence data yet",
        # same as a never-retrieved atom.
        self.atom_relevance_score = snapshot.get("atom_relevance_score") or {}
        self.retrieval_query = snapshot.get("retrieval_query")
        self.last_question = snapshot["last_question"]
        self.stale_question_streak = snapshot["stale_question_streak"]
        self.confirmation_offered = snapshot["confirmation_offered"]
        self.resource_count_estimated = snapshot["resource_count_estimated"]

    def switch_subject(self, subject_type: str, subject_label: str = "") -> bool:
        """Make ``subject_type``/``subject_label`` the active subject.

        Parks the outgoing subject's concepts/facts/questions/etc. (keyed by
        its subject_key) and restores the incoming one's snapshot if it was
        parked earlier, or starts it fresh otherwise. A no-op (returns False)
        when the requested subject is already the active one -- e.g. the
        patient keeps describing the same third person turn after turn.
        """
        label = subject_label.strip() if subject_type == "OTHER_PERSON" else ""
        new_key = "SELF" if subject_type != "OTHER_PERSON" else f"OTHER:{label.lower()}"
        if new_key == self.subject_key:
            return False

        self.parked_subjects[self.subject_key] = self._snapshot_active_subject()
        resumed = self.parked_subjects.pop(new_key, None)
        if resumed is not None:
            self._load_subject_snapshot(resumed)
        else:
            self.subject_type = subject_type if subject_type == "OTHER_PERSON" else "SELF"
            self.subject_label = label
            self.concepts = set()
            self.concept_order = []
            self.facts = {}
            self.qualitative_observations = {}
            self.unknown_facts = set()
            self.needs_precision = set()
            self.seen_atom_ids = []
            self.atom_relevance_score = {}
            self.retrieval_query = None
            self.last_question = None
            self.stale_question_streak = 0
            self.confirmation_offered = False
            self.resource_count_estimated = False
        return True
