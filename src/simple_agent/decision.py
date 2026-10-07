"""Phase B: deterministic protocol-atom evaluation and question prioritisation.

Nothing here calls an LLM. Given a session's known facts, this module decides
which protocol atoms are satisfied/excluded/still-missing information, purely
by walking the corpus's ``requirements`` lists -- the same guarantee the
project has always made: the model cannot talk its way into an ESI level that
the stated facts don't support.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from .corpus import Corpus, cosine_scores
from .session import Session

ATOM_RETRIEVAL_LIMIT = 8
# Below this cosine score a retrieved atom is noise, not a candidate. Unlike
# concept search (short names/aliases), atom retrieval.text is long English
# clinical sentences, so its baseline similarity scale differs -- calibrated
# separately: measured real queries score ~0.42-0.48 against genuinely
# relevant atoms and ~0.08-0.17 against unrelated ones for this embedding
# model/corpus. Matters more now that atom_missing feeds directly into what
# the patient gets asked (see agent.py's askable computation), not just a
# supported/excluded count.
MIN_ATOM_RELEVANCE_SCORE = 0.25

# A stricter bar than MIN_ATOM_RELEVANCE_SCORE, applied only when deciding
# whether an atom-only-linked fact (one not already reachable via a concept's
# own REQUIRES_ASSESSMENT_OF relation, see agent.py's `direct_targets`) may be
# proactively ASKED of the patient. Real incident (2026-08-27): a single
# off-topic reply ("bạn đoán xem", zero clinical content) scored 0.2512
# against an ESI-2 syncope atom for a plain "fatigue" query -- comfortably
# above MIN_ATOM_RELEVANCE_SCORE but nowhere near the ~0.42-0.48 this corpus's
# genuinely relevant matches score (see that constant's own comment); a real,
# on-topic answer to the same query scored 0.245, i.e. didn't even retrieve.
# 0.32 sits above the observed noise crossing with real margin while staying
# well below genuine matches. Deliberately does NOT change
# MIN_ATOM_RELEVANCE_SCORE itself: that threshold still governs what gets
# retrieved into `session.seen_atom_ids` and evaluated for ESI matching
# (evaluate_atoms) -- full recall there is exactly what lets a later, better
# answer still land a real match. This constant only holds back which
# follow-up question gets volunteered when the only evidence for asking it is
# a borderline-scoring atom.
MIN_ATOM_RELEVANCE_SCORE_FOR_PROACTIVE_ASK = 0.32

# A hard, deterministic stop on how many distinct fact_targets one session
# will proactively ask about. Without it, a session that ends up asserting
# several overlapping concepts (each pulling in its own REQUIRES_ASSESSMENT_OF
# fact list) can keep the interview open indefinitely -- there is no ESI
# judgment involved in reaching this cap, it's a pure resource budget in the
# same spirit as the corpus's own fact_target:resource_count.
MAX_ASKED_FACTS_PER_SESSION = 17

# How many consecutive turns the same fact_target_id may be re-selected as
# the question to ask without ever resolving (see agent.py's stale-question
# bail-out). Also a pure resource-budget rule, not an ESI judgment: Phase A
# can record a related concept from the patient's answer while forgetting to
# close out the pending fact_target itself, which would otherwise make the
# same question repeat indefinitely.
STALE_QUESTION_LIMIT = 2

# The corpus's atoms are authored against the real ESI v4 algorithm's four
# sequential decision points (decision_point ids all start with one of these
# letters): A asks whether an immediate life-saving intervention is needed
# (-> ESI 1), B whether the situation is otherwise high-risk (-> ESI 2), C
# whether vitals sit in a danger zone (-> ESI 2/3), and D predicts resource
# count to split ESI 3/4/5. The real algorithm is short-circuiting -- you
# only reach D if A/B/C all came back negative -- so a fact that could settle
# an A/B/C atom is worth asking before one that only feeds a D atom, even if
# both are equally "decisive" (see decisiveness below).
_DECISION_POINT_PRIORITY = {"A": 0, "B": 1, "C": 2, "D": 3}


def _decision_point_priority(decision_point: str | None) -> int:
    if not decision_point:
        return 99
    return _DECISION_POINT_PRIORITY.get(decision_point[0], 99)


def retrieve_atoms_scored(
    corpus: Corpus, embed: Callable[[str], np.ndarray], query: str
) -> list[tuple[dict[str, Any], float]]:
    """Same retrieval as ``retrieve_atoms``, but also returns each atom's raw
    cosine score -- needed by agent.py to gate *proactive asking* against
    MIN_ATOM_RELEVANCE_SCORE_FOR_PROACTIVE_ASK without weakening
    MIN_ATOM_RELEVANCE_SCORE's own recall guarantee for ESI matching.
    """
    scores = cosine_scores(embed(query), corpus.protocol_embeddings)
    order = np.argsort(scores)[::-1][:ATOM_RETRIEVAL_LIMIT]
    return [
        (corpus.atom_by_id[corpus.protocol_metadata[row]["atom_id"]], float(scores[row]))
        for row in order
        if scores[row] >= MIN_ATOM_RELEVANCE_SCORE
    ]


def retrieve_atoms(corpus: Corpus, embed: Callable[[str], np.ndarray], query: str) -> list[dict[str, Any]]:
    return [atom for atom, _score in retrieve_atoms_scored(corpus, embed, query)]


# How many fact_targets retrieve_fact_targets_scored returns at most.
FACT_TARGET_RETRIEVAL_LIMIT = 10

# Below this cosine score a retrieved fact_target is noise, not a candidate.
# Calibrated the same way as MIN_ATOM_RELEVANCE_SCORE above, against this
# corpus's own fact_target_patient_embeddings.npy (name + lay_terms,
# text-embedding-3-small): off-topic filler ("hôm nay trời đẹp quá", "bạn
# đoán xem") tops out around 0.40-0.42 against its best-matching
# fact_target, while a clean single-symptom query lands 0.54-0.56 against
# the right one. Set just above the measured noise ceiling rather than
# closer to the clean-query end, because a *compound* real sentence (several
# findings in one message, e.g. "phồng rộp da nông, đau rát nhẹ 1/10") splits
# its embedding mass across several fact_targets at once and can land as low
# as ~0.44 against the single best match -- recall matters more here than it
# would for a sharper signal, since search_fact_targets_for_text only ever
# *suggests* candidates; record_fact's own schema validation is the actual
# gate on what gets written.
MIN_FACT_TARGET_TEXT_SCORE = 0.42


def retrieve_fact_targets_scored(
    corpus: Corpus, embed: Callable[[str], np.ndarray], query: str, *, limit: int = FACT_TARGET_RETRIEVAL_LIMIT
) -> list[tuple[dict[str, Any], float]]:
    """Find fact_targets by embedding raw text directly -- e.g. a phrase from
    the patient's own message -- independent of which concepts got recorded
    this turn. Backs tools.py's search_fact_targets_for_text: the concept-
    mediated path (search_fact_targets_for_concepts) can only surface a
    fact_target whose owning concept the model already identified, so a
    detail the model failed to tie to any concept was previously
    undiscoverable even though the patient had already stated it.

    ``limit`` defaults to the module constant but is overridable: agent.py's
    extraction-backfill pass (see extraction_backfill.py) deliberately asks
    for a much wider net than tools.py's own proactive surfacing does, since
    it's a single dedicated classification call rather than context injected
    into Phase A's own tool-calling loop -- the recall/noise tradeoff that
    keeps tools.py's own limit narrow doesn't apply the same way there.
    """
    scores = cosine_scores(embed(query), corpus.fact_target_embeddings)
    order = np.argsort(scores)[::-1][:limit]
    return [
        (corpus.fact_by_id[corpus.fact_target_metadata[row]["fact_target_id"]], float(scores[row]))
        for row in order
        if scores[row] >= MIN_FACT_TARGET_TEXT_SCORE
    ]


def matches(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "EQ":
        return actual == expected
    if operator == "NEQ":
        return actual != expected
    try:
        if operator == "GT":
            return actual > expected
        if operator == "GTE":
            return actual >= expected
        if operator == "LT":
            return actual < expected
        if operator == "LTE":
            return actual <= expected
    except TypeError:
        return False
    return False


def _branch_status(branch: list[dict[str, Any]], facts: dict[str, Any]) -> tuple[bool, list[str]]:
    """(contradicted, unmet_required_fact_ids) for one AND-group of requirements."""
    unmet: list[str] = []
    for requirement in branch:
        fact_id = requirement["fact_target_id"]
        if fact_id not in facts:
            if requirement.get("required", True):
                unmet.append(fact_id)
            continue
        if not matches(facts[fact_id], requirement.get("operator", "EQ"), requirement.get("expected_value")):
            return True, []
    return False, unmet


def atom_status(atom: dict[str, Any], facts: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return (contradicted, unmet_required_fact_ids) for one atom against ``facts``.

    ``requirements`` is normally a flat list of condition objects, all AND'd
    together -- unchanged from every atom authored before this function
    existed. If any element of the list is itself a list, the array switches
    to disjunctive-normal-form: each top-level element is one OR-branch (a
    bare condition object is a singleton branch, a nested list is an
    AND-group), and the atom as a whole is satisfied the moment any single
    branch is. This lets one atom express "(A and B) or C" -- a headache
    concept with a new focal deficit is high-risk whether it arrived via
    sudden onset (A and B) or is severe enough alone (C) -- without forking
    into several near-duplicate atoms that all share one decision_effect.
    """
    requirements = atom.get("requirements", [])
    if any(isinstance(item, list) for item in requirements):
        branches = [item if isinstance(item, list) else [item] for item in requirements]
    else:
        branches = [requirements]

    results = [_branch_status(branch, facts) for branch in branches]
    alive = [(contradicted, unmet) for contradicted, unmet in results if not contradicted]
    if not alive:
        # Every branch is individually contradicted -- no fact still to be
        # learned could ever make this atom true.
        return True, []
    for _contradicted, unmet in alive:
        if not unmet:
            return False, []
    # Report the closest-to-complete alive branch, not the union of all of
    # them -- resolving that one branch is sufficient to satisfy the atom,
    # and this is what rank_question_targets's decisiveness tier reads.
    return False, min((unmet for _contradicted, unmet in alive), key=len)


def describe_satisfied_branch(
    atom: dict[str, Any], facts: dict[str, Any], corpus: Corpus
) -> list[dict[str, Any]]:
    """For an atom already known to be fully supported (``atom_status``
    returns ``(False, [])``), find the first OR-branch that is completely
    satisfied and describe each of its requirements with the patient's own
    reported value -- e.g. "Mức độ đau (>= 8): bạn báo cáo 9".

    Deliberately a separate, read-only function rather than a change to
    ``atom_status``/``_branch_status``: those two stay byte-for-byte the
    matching engine they always were (zero risk to RETURN_MATCH/
    RETURN_INCOMPLETE decisions), this only re-walks the same requirements a
    second time purely to keep what `_branch_status` throws away, for
    patient/nurse-facing display (`agent.py`'s ``matched_atoms``, `sbar.py`'s
    ``citations``). Returns `[]` if no branch is actually fully satisfied
    (e.g. called on an atom that's only MISSING_INFO/CONTRADICTED) -- callers
    should check status first.
    """
    requirements = atom.get("requirements", [])
    if any(isinstance(item, list) for item in requirements):
        branches = [item if isinstance(item, list) else [item] for item in requirements]
    else:
        branches = [requirements]

    for branch in branches:
        described: list[dict[str, Any]] = []
        branch_satisfied = True
        for requirement in branch:
            fact_id = requirement["fact_target_id"]
            if fact_id not in facts:
                if requirement.get("required", True):
                    branch_satisfied = False
                    break
                continue
            operator = requirement.get("operator", "EQ")
            expected_value = requirement.get("expected_value")
            if not matches(facts[fact_id], operator, expected_value):
                branch_satisfied = False
                break
            fact_def = corpus.fact_by_id.get(fact_id)
            described.append(
                {
                    "fact_target_id": fact_id,
                    "name": fact_def["name"] if fact_def else fact_id,
                    "operator": operator,
                    "expected_value": expected_value,
                    "actual_value": facts[fact_id],
                }
            )
        if branch_satisfied:
            return described
    return []


def evaluate_atoms(
    atoms: list[dict[str, Any]], facts: dict[str, Any]
) -> tuple[list[dict[str, Any]], set[str], list[dict[str, Any]]]:
    """Split ``atoms`` into (supported ASSIGN_ESI atoms, missing fact ids, excluding atoms).

    An atom whose ``decision_effect.impact`` is ``EXCLUDE_ESI`` and is fully
    supported removes its ``candidate_esi`` from the assignable set instead of
    adding to it -- this is the one new decision axis protocol atoms can carry
    beyond a single "this matches" criterion.
    """
    assign_supported: list[dict[str, Any]] = []
    exclude_supported: list[dict[str, Any]] = []
    missing: set[str] = set()
    for atom in atoms:
        contradicted, unmet = atom_status(atom, facts)
        if contradicted:
            continue
        if unmet:
            missing.update(unmet)
            continue
        impact = atom.get("decision_effect", {}).get("impact")
        if impact == "EXCLUDE_ESI":
            exclude_supported.append(atom)
        else:
            assign_supported.append(atom)

    excluded_levels = {atom["decision_effect"].get("candidate_esi") for atom in exclude_supported}
    supported = [atom for atom in assign_supported if atom["decision_effect"].get("candidate_esi") not in excluded_levels]
    return supported, missing, exclude_supported


def gate_satisfied(fact_id: str, session: Session, corpus: Corpus) -> bool:
    """Whether ``fact_id`` may be recorded/asked at all, per its optional
    ``gated_by`` (see ``fact_targets.jsonl``): a detail fact (e.g.
    "circumstances of fainting") that presupposes some event/finding actually
    occurred (e.g. "did you faint at all") should not be asked -- or
    accepted -- before that's established. Real incident (2026-08-27):
    retrieval noise surfaced ``fact_target:syncope_context`` for a plain
    fatigue complaint with zero evidence the patient had ever fainted.

    Two independent ways to satisfy a gate, both meaning "we already have
    real evidence this happened": (1) the gate fact itself is recorded with
    the expected value, or (2) some already-asserted concept directly
    requires this *same* detail fact via REQUIRES_ASSESSMENT_OF (e.g. the
    patient plainly said "tôi bị ngất" -> concept:syncope asserted ->
    syncope_context is one of its direct targets) -- that assertion is
    itself sufficient evidence, and without this second path a patient who
    already told us the gated event happened would get stuck: nothing would
    prompt the separate yes/no gate fact either, since it usually isn't a
    direct target of that same concept.

    Real incident (2026-08-28): the patient explicitly answered "không" to
    "Gần đây bạn có bị ngã hoặc va đập vào đầu không?" (recent_head_trauma),
    recorded as NO -- yet post_trauma_vomiting_count (gated on
    recent_head_trauma == YES) got asked right after anyway, because
    concept:vomiting (already asserted, unrelated to any head trauma) also
    lists it as a direct target and path (2) doesn't check whether the gate
    fact was ever actually answered, only whether it matches. Path (2)
    exists to cover an *unknown* gate (never separately asked), not to
    overrule an *explicit denial* -- no already-asserted concept's broad
    differential list should ever get to relitigate a gate the patient just
    answered. Checked before path (2), not folded into it: an explicit
    non-matching answer must block the detail regardless of which concepts
    are asserted, while a still-unknown gate keeps falling through to (2)
    exactly as before.

    ``gated_by`` may also be an ``any_of`` list of gates (OR, not a single
    precondition) -- added 2026-08-29 for ``fact_target:skin_sensation``
    (asked when EITHER a burn OR a non-burn thermal exposure is present,
    merged from the old burn-only-gated ``fact_target:burn_sensation``).
    Generalises both paths above: satisfied if *any* gate matches; blocked
    by an explicit denial only once *every* gate has been explicitly
    answered and none matched (one gate denied while another is still
    unknown must not block -- the still-unknown one could yet turn out
    true); falls through to path (2) otherwise, unaffected by which
    specific gate concept-membership is checked against. A plain
    (non-``any_of``) ``gated_by`` is just the one-gate case of the same
    logic.

    Shared by two call sites (moved here 2026-08-29 so both can use the
    exact same logic instead of drifting apart): agent.py's askability
    check (whether to *proactively ask* about a fact target -- permissive,
    since silently missing a real case is worse than an occasional
    harmless ask) and tools.py's ``record_fact`` (whether to *accept a
    value Phase A is trying to write* for a fact target -- rejecting an
    ungated write closes a real hole found live 2026-08-29: given a burn
    case with only concept:recent_burn/concept:burn_injury asserted, Phase A
    wrote fact_target:limb_function_status=NORMAL_USE from a reply
    ("làm bình thường") that actually answered the pending pain_severity
    question -- limb_function_status is gated on joint_pain_present==YES
    and is not a direct target of either asserted concept, so this gate was
    never satisfied at all; nothing had ever established the patient even
    had joint pain. The wrong fact_target absorbed the reply and the
    genuinely-pending question was left unresolved, silently re-asked next
    turn with different phrasing).
    """
    gated_by = corpus.fact_by_id[fact_id].get("gated_by")
    if not gated_by:
        return True
    gates = gated_by["any_of"] if "any_of" in gated_by else [gated_by]
    gate_values = [session.facts.get(gate["fact_target_id"]) for gate in gates]
    if any(value == gate["expected_value"] for value, gate in zip(gate_values, gates)):
        return True
    if all(value is not None for value in gate_values):
        return False
    return any(fact_id in corpus.facts_for_concept.get(concept_id, []) for concept_id in session.concepts)


def rank_question_targets(
    session: Session, corpus: Corpus, atoms: list[dict[str, Any]], candidates: list[str]
) -> list[str]:
    """Order unresolved fact targets by how decisive, then how recent, they are.

    Decisiveness: a fact that would resolve an atom which is otherwise fully
    satisfied outranks one that only chips away at an atom still missing
    several other requirements. Recency: among equally decisive facts, prefer
    ones linked to a concept the patient raised most recently, so a new
    complaint doesn't get stuck behind an older, still-unanswered question.
    """
    atom_unmet: dict[str, list[str]] = {}
    atom_priority: dict[str, int] = {}
    for atom in atoms:
        contradicted, unmet = atom_status(atom, session.facts)
        if not contradicted and unmet:
            atom_unmet[atom["atom_id"]] = unmet
            atom_priority[atom["atom_id"]] = _decision_point_priority(atom.get("decision_point"))

    def urgency_rank(fact_id: str) -> int:
        priorities = [atom_priority[aid] for aid, unmet in atom_unmet.items() if fact_id in unmet]
        return min(priorities) if priorities else 99

    def decisiveness(fact_id: str) -> int:
        counts = [len(unmet) for unmet in atom_unmet.values() if fact_id in unmet]
        return min(counts) if counts else 999

    def recency_rank(fact_id: str) -> int:
        owning_concepts = [c for c in session.concepts if fact_id in corpus.facts_for_concept.get(c, [])]
        indices = [session.concept_order.index(c) for c in owning_concepts if c in session.concept_order]
        return -max(indices) if indices else 0

    # needs_precision facts (vague vitals answer) jump the queue for their
    # first re-ask: the patient already engaged with the question, just not
    # precisely enough yet. But only once -- if it was re-selected last turn
    # (stale_question_streak > 0) and is still imprecise, stop demanding it
    # and let an equally-decisive alternative the patient CAN answer surface
    # (e.g. pain quality/radiation instead of an unmeasurable blood pressure),
    # rather than looping for STALE_QUESTION_LIMIT more turns on a number the
    # patient plainly has no way to give.
    def precision_rank(fact_id: str) -> int:
        if fact_id not in session.needs_precision:
            return 1
        if fact_id == session.last_question and session.stale_question_streak >= 1:
            return 1
        return 0

    return sorted(
        candidates,
        key=lambda fid: (precision_rank(fid), urgency_rank(fid), decisiveness(fid), recency_rank(fid)),
    )
