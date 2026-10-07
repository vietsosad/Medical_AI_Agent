"""Phase A tool implementations: the model's only way to read or change session
state. Every mutation is validated against the corpus here, in code -- the
model can request a concept/fact by ID but this module decides whether that ID
is real, whether a value satisfies its schema, and whether a concept candidate
is confident enough to record without asking the patient to disambiguate.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import numpy as np

from .corpus import Corpus, cosine_scores, tokenize, validate_fact
from .decision import atom_status, gate_satisfied, retrieve_atoms, retrieve_fact_targets_scored
from .session import Session

logger = logging.getLogger(__name__)

# Below this cosine score an embedding "match" is treated as noise, not a
# candidate. Calibrated against measured baselines in data/siu: random
# unrelated concept pairs already sit at a median cosine of ~0.38 (p5 ~0.26)
# with this embedding model, and even a non-clinical sentence like "hôm nay
# trời đẹp quá" scores ~0.40 against its best-matching concept -- 0.20 let
# essentially everything through.
MIN_RELEVANT_SCORE = 0.40
# How many candidates survive rerank and get returned to the model.
EMBEDDING_CANDIDATES = 5
# How many raw-cosine hits are pulled before reranking -- wider than the
# final candidate count so a correct concept whose alias wording doesn't
# closely match the query's phrasing (pure semantic score) still has a
# chance to be pulled back up by the lexical-overlap bonus below.
EMBEDDING_POOL_SIZE = 30
# Rerank score = semantic cosine + this weight * token-overlap ratio against
# a concept's aliases/canonical_name. A cheap, deterministic hybrid signal:
# semantic alone missed concept:chest_pain entirely (ranked #15) for "tôi
# thấy nhói ở bên trái ngực" even though "nhói ngực"/"ngực" literally appear
# in its aliases, just not as a contiguous substring lexical_concepts can catch.
LEXICAL_OVERLAP_WEIGHT = 0.20
# Ambiguity is judged against the #1 candidate only (not chained adjacent
# pairs, which let a middling match drag in everything near it transitively),
# as a *relative* fraction of the top score -- fixed absolute gaps like the
# old 0.03 don't account for how compressed scores are for a given query.
AMBIGUITY_RELATIVE_MARGIN = 0.04

# How many concepts/fact_targets prime_proactive_candidates surfaces
# unconditionally in get_session_state, every turn -- tighter than the
# on-demand tools' own limits (EMBEDDING_CANDIDATES=5,
# FACT_TARGET_RETRIEVAL_LIMIT=10) since this is unconditional payload on
# every turn, not something the model explicitly asked for.
PROACTIVE_CONCEPT_LIMIT = 4
PROACTIVE_FACT_TARGET_LIMIT = 6
# How many recent session.history turns feed the query -- see
# prime_proactive_candidates. A lone current-turn message loses whatever
# topic an earlier turn established (measured live: "rát lắm nó làm tôi đau
# và lan rộng 1mm" alone scores burn_extent_estimate at 0.41, *below*
# threshold, competing with unrelated fields like chest_pain_radiation;
# prefixed with the turn that established "tôi bị bỏng", it scores 0.47).
PROACTIVE_HISTORY_WINDOW = 4


def _looks_like_a_question(text: str) -> bool:
    """True if ``text`` reads like a question addressed to the patient, not a fact they stated.

    Cheap deterministic guard for a real failure mode: Phase A occasionally
    composes the question it was about to ask and passes that same text into
    record_fact/record_qualitative_observation, which happily accepts any
    non-empty string -- silently recording a fabricated "observation" that
    is actually the assistant's own words, not anything the patient said.
    """
    stripped = text.strip().rstrip("\"'”’")
    return stripped.endswith(("?", "？"))


_TOOL_METHODS = {
    "get_session_state",
    "search_clinical_concepts",
    "search_fact_targets_for_concepts",
    "search_fact_targets_for_text",
    "search_protocol_atoms",
    "record_concept",
    "record_fact",
    "record_facts",
    "record_qualitative_observation",
    "mark_fact_unknown",
    "finish_turn",
}


class AgentToolbox:
    """Binds one turn's ``Corpus`` + ``Session`` to the tool functions."""

    def __init__(self, corpus: Corpus, session: Session, embed: Callable[[str], np.ndarray]) -> None:
        self.corpus = corpus
        self.session = session
        self.embed = embed
        # IDs actually surfaced by a search_* call this turn (or already part
        # of the session) -- record_concept refuses anything else, so the model
        # cannot invent a concept id it merely guessed at.
        self.seen_concept_ids: set[str] = set(session.concepts)
        self.outcome: dict[str, Any] | None = None
        self.finished = False
        # Populated once per turn by prime_proactive_candidates (see that
        # method) and read by get_session_state -- concepts/fact_targets
        # relevant to the conversation so far, surfaced unconditionally
        # instead of waiting for the model to remember to search for them.
        self.proactive_concepts: list[dict[str, Any]] = []
        self.proactive_fact_targets: list[dict[str, Any]] = []
        # Real (non-finish_turn) tool dispatches so far this turn -- see
        # deepagent_understanding.py's _run() for why this lives here as a
        # plain instance attribute rather than a ContextVar. LangGraph runs
        # each tool call in its own task/context copy, so a ContextVar
        # mutated inside one dispatch is never visible to the next one
        # (confirmed live: a traced ContextVar-based counter stayed at 1 for
        # all 12 real dispatches of one real turn -- the budget was never
        # actually enforced). This object, though, is the same instance
        # retrieved via _toolbox_ctx.get() on every call this turn, so
        # mutating its own attribute works correctly.
        self.real_dispatch_count = 0

    def dispatch(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in _TOOL_METHODS:
            result = {"ok": False, "error": f"Unknown tool {name!r}."}
            logger.debug("TOOL %s(%s) -> %s", name, arguments, result)
            return result
        method = getattr(self, name)
        try:
            result = method(**arguments)
        except TypeError as exc:
            result = {"ok": False, "error": f"Bad arguments for {name}: {exc}"}
        self.session.tool_log.append({"tool": name, "arguments": arguments, "result": result})
        self.session.turn_tool_log.append({"tool": name, "arguments": arguments, "result": result})
        logger.debug(
            "TOOL %s(%s) -> %s",
            name, json.dumps(arguments, ensure_ascii=False), json.dumps(result, ensure_ascii=False),
        )
        return result

    # -- observation -----------------------------------------------------

    def get_session_state(self) -> dict[str, Any]:
        concepts = [
            {"concept_id": cid, "canonical_name": self.corpus.concept_by_id[cid]["canonical_name"]}
            for cid in self.session.concept_order
        ]
        facts = [
            {
                "fact_target_id": fid,
                "name": self.corpus.fact_by_id[fid]["name"],
                "value": value,
                # True when the recorded value is the literal "UNKNOWN" token: nobody
                # has actually described this fact yet, it is not settled. Distinct
                # from unknown_facts (an explicit "I don't know") -- this can still be
                # overwritten the moment the patient describes it, even outside the
                # pending question (see prompts.py's "Revisiting a fact already left
                # as UNKNOWN"). Without this flag it looks identical to a genuinely
                # resolved fact, and a later clear description of it is never recorded.
                "unconfirmed_unknown": value == "UNKNOWN",
            }
            for fid, value in self.session.facts.items()
        ]
        observations = [
            {
                "fact_target_id": fid,
                "observation": text,
                "needs_precise_number": fid in self.session.needs_precision,
            }
            for fid, text in self.session.qualitative_observations.items()
        ]
        unknown = [
            {"fact_target_id": fid, "name": self.corpus.fact_by_id[fid]["name"]}
            for fid in self.session.unknown_facts
        ]
        pending_value_schema = None
        if self.session.last_question:
            pending_target = self.corpus.fact_by_id.get(self.session.last_question)
            if pending_target:
                pending_value_schema = pending_target.get("value_schema")

        # See corpus.py's gate_fact_ids: every fact_target_id some OTHER
        # fact's gated_by depends on (e.g. facial_swelling_present gates
        # oral_swelling_location), listed here unconditionally -- every
        # turn, regardless of which concepts are currently active -- so a
        # patient volunteering one of these unprompted ("tôi bị sưng", out
        # of nowhere) can be recorded immediately instead of only being
        # discoverable once the system's own question selection happens to
        # reach a fact_target that needs it. Same {name, lay_terms,
        # value_schema, state} shape as search_fact_targets_for_concepts so
        # record_fact's value can match allowed_values on the first try.
        gate_facts = []
        for fid in sorted(self.corpus.gate_fact_ids):
            target = self.corpus.fact_by_id.get(fid)
            if target is None:
                continue
            if fid in self.session.facts:
                state = "known"
            elif fid in self.session.unknown_facts:
                state = "unknown"
            elif fid in self.session.qualitative_observations:
                state = "described_needs_precise_number" if fid in self.session.needs_precision else "described"
            else:
                state = "not_asked"
            gate_facts.append(
                {
                    "fact_target_id": fid,
                    "name": target["name"],
                    "lay_terms": target.get("lay_terms", ""),
                    "value_schema": target.get("value_schema"),
                    "state": state,
                }
            )

        return {
            # Who "patient_concepts"/"known_facts"/etc. below currently
            # describe: the patient themself, or one specific other person
            # they're asking about (see record_concept's subject_label).
            "active_subject": {
                "type": self.session.subject_type,
                "label": self.session.subject_label or None,
            },
            "patient_concepts": concepts,
            "known_facts": facts,
            "qualitative_observations": observations,
            "unknown_facts": unknown,
            "pending_question_fact_target_id": self.session.last_question,
            # So the very turn that answers the pending question already has
            # the exact allowed_values/min/max in context, without needing a
            # separate search_fact_targets_for_concepts call first -- without
            # this, a clear direct answer (e.g. "tăng dần" for an enum whose
            # token is "GRADUAL") often only reaches
            # record_qualitative_observation, never record_fact, leaving the
            # fact permanently un-satisfiable for atom matching while also
            # permanently excluded from being asked again.
            "pending_question_value_schema": pending_value_schema,
            "gate_facts": gate_facts,
            # Computed once per turn by prime_proactive_candidates, from
            # recent conversation context -- see that method's docstring.
            # Concepts already recorded this session are excluded (nothing
            # to add); fact_targets are not (their "state" says whether
            # they're already known/unknown/described, same as
            # search_fact_targets_for_concepts's own results). record_concept
            # accepts any id listed here directly, no extra search call
            # needed first -- these have already been marked "seen".
            "proactive_concepts": self.proactive_concepts,
            "proactive_fact_targets": self.proactive_fact_targets,
            "awaiting_confirmation": self.session.confirmation_offered,
            "recent_conversation": [{"speaker": speaker, "text": text} for speaker, text in self.session.history],
        }

    def _rank_concepts(self, query: str) -> list[dict[str, Any]]:
        """Core of search_clinical_concepts, minus the seen_concept_ids side
        effect and the final [:12] cap -- shared with prime_proactive_candidates
        so both use identical ranking/ambiguity logic instead of two
        implementations drifting apart."""
        lexical_ids = self.corpus.lexical_concepts(query)
        scores = cosine_scores(self.embed(query), self.corpus.concept_embeddings)
        pool_order = np.argsort(scores)[::-1][:EMBEDDING_POOL_SIZE]

        query_tokens = tokenize(query)
        reranked: list[tuple[str, float, float]] = []  # (concept_id, semantic_score, combined_score)
        for i in pool_order:
            semantic_score = float(scores[i])
            if semantic_score < MIN_RELEVANT_SCORE:
                continue
            concept_id = self.corpus.concept_metadata[i]["concept_id"]
            concept_tokens = self.corpus.concept_tokens.get(concept_id) or set()
            # Normalised by the QUERY's token count (recall), not the
            # concept's: a concept with many aliases has a large token
            # vocabulary, and normalising by that would dilute the bonus for
            # exactly the richly-described concepts we want it to reward.
            overlap_ratio = len(query_tokens & concept_tokens) / len(query_tokens) if query_tokens else 0.0
            combined_score = semantic_score + LEXICAL_OVERLAP_WEIGHT * overlap_ratio
            reranked.append((concept_id, semantic_score, combined_score))
        reranked.sort(key=lambda item: item[2], reverse=True)
        embedding_hits = [(cid, semantic_score) for cid, semantic_score, _ in reranked[:EMBEDDING_CANDIDATES]]
        combined_by_id = {cid: combined for cid, _, combined in reranked[:EMBEDDING_CANDIDATES]}

        candidates: dict[str, dict[str, Any]] = {}
        for concept_id in lexical_ids:
            candidates[concept_id] = {
                "concept_id": concept_id,
                "canonical_name": self.corpus.concept_by_id[concept_id]["canonical_name"],
                "confidence": "EXACT_ALIAS",
            }

        semantic_order = [cid for cid, _ in embedding_hits if cid not in candidates]
        score_by_id = dict(embedding_hits)

        # Ambiguity: measured against the #1 combined-ranked candidate only
        # (not chained adjacent pairs, which let a middling match transitively
        # drag in everything near it), as a *relative* fraction of the top
        # score. A curated corpus.distinguishes_from pair overrides this and
        # is always ambiguous regardless of score, since that's an explicit
        # authoring signal that two concepts are commonly confused.
        ambiguous_ids: set[str] = set()
        if semantic_order:
            top_id = semantic_order[0]
            top_score = combined_by_id[top_id]
            for concept_id in semantic_order[1:]:
                if top_score and (top_score - combined_by_id[concept_id]) / top_score <= AMBIGUITY_RELATIVE_MARGIN:
                    ambiguous_ids.add(top_id)
                    ambiguous_ids.add(concept_id)
            for a in semantic_order:
                if any(b in self.corpus.distinguishes_from.get(a, ()) for b in semantic_order if b != a):
                    ambiguous_ids.add(a)

        for concept_id in semantic_order:
            candidates[concept_id] = {
                "concept_id": concept_id,
                "canonical_name": self.corpus.concept_by_id[concept_id]["canonical_name"],
                "confidence": "AMBIGUOUS" if concept_id in ambiguous_ids else "CONFIDENT",
                "score": round(score_by_id[concept_id], 3),
            }

        return [candidates[cid] for cid in lexical_ids] + [candidates[cid] for cid in semantic_order]

    def search_clinical_concepts(self, query: str) -> dict[str, Any]:
        ordered = self._rank_concepts(query)
        self.seen_concept_ids.update(item["concept_id"] for item in ordered)
        return {"candidates": ordered[:12]}

    def prime_proactive_candidates(self) -> None:
        """Run once per turn, before the model makes any tool call (see
        deepagent_understanding.py's run_deepagent_understanding_loop) --
        surfaces concepts/fact_targets relevant to the conversation so far
        directly in get_session_state, instead of relying on the model to
        remember to call search_clinical_concepts/search_fact_targets_for_text
        itself. Real incident this fixes: across repeated live runs, the
        model never once called search_fact_targets_for_text even when a
        record_fact call had just failed with an unknown id right before --
        it consistently fell back to search_clinical_concepts (a tool it
        already uses constantly for everything else) instead of reaching for
        a less-familiar one, no matter how the latter's tool description was
        worded. A pull-based tool the model has to decide to call is
        measurably less reliable than information already placed in its
        context -- the existing gate_facts field (always present regardless
        of which concepts are active) works for exactly this reason.

        Query = recent session.history (already includes this turn's own
        message -- see agent.py's process_turn, which calls
        session.remember_turn("patient", message) before Phase A ever runs),
        not the current message alone: an isolated later-turn reply that
        doesn't repeat an earlier-established topic retrieves badly on its
        own (measured live: "rát lắm nó làm tôi đau và lan rộng 1mm" alone
        scores the right fact_target *below* the relevance threshold and
        surfaces unrelated ones instead; prefixed with the turn that
        established "tôi bị bỏng", it clears the threshold with margin).
        """
        recent = self.session.history[-PROACTIVE_HISTORY_WINDOW:]
        if not recent:
            return
        query = "\n".join(f"{speaker}: {text}" for speaker, text in recent)

        concept_candidates = [
            item for item in self._rank_concepts(query) if item["concept_id"] not in self.session.concepts
        ][:PROACTIVE_CONCEPT_LIMIT]
        self.seen_concept_ids.update(item["concept_id"] for item in concept_candidates)
        self.proactive_concepts = concept_candidates

        fact_hits = retrieve_fact_targets_scored(self.corpus, self.embed, query)
        self.proactive_fact_targets = [
            {**self._fact_target_result(target["fact_target_id"]), "score": round(score, 3)}
            for target, score in fact_hits[:PROACTIVE_FACT_TARGET_LIMIT]
        ]

    def _fact_target_state(self, fid: str) -> str:
        if fid in self.session.facts:
            return "known"
        if fid in self.session.unknown_facts:
            return "unknown"
        if fid in self.session.qualitative_observations:
            return "described_needs_precise_number" if fid in self.session.needs_precision else "described"
        return "not_asked"

    def _fact_target_result(self, fid: str) -> dict[str, Any]:
        target = self.corpus.fact_by_id[fid]
        return {
            "fact_target_id": fid,
            "name": target["name"],
            "reporting_style": target.get("reporting_style", "CLINICIAN_ONLY"),
            "lay_terms": target.get("lay_terms", ""),
            "severity_anchors": target.get("severity_anchors"),
            # Exposed so record_fact's value can be the exact token on
            # the first try, e.g. an enum fact_target's allowed_values
            # like "AROUND_UMBILICUS" -- without this, the model can
            # only guess free text from lay_terms (e.g. "quanh rốn" or
            # "around umbilicus"), which fails schema validation and
            # burns tool-call budget on retries.
            "value_schema": target.get("value_schema"),
            "state": self._fact_target_state(fid),
        }

    def search_fact_targets_for_concepts(self, concept_ids: list[str]) -> dict[str, Any]:
        valid_ids = [cid for cid in concept_ids if cid in self.corpus.concept_by_id]
        fact_ids = list(dict.fromkeys(fid for cid in valid_ids for fid in self.corpus.facts_for_concept.get(cid, [])))
        return {"fact_targets": [self._fact_target_result(fid) for fid in fact_ids]}

    def search_fact_targets_for_text(self, text: str) -> dict[str, Any]:
        """Find fact_targets by embedding a phrase directly, bypassing the
        concept graph -- for a detail the patient stated that doesn't map to
        any concept already found this turn (see decision.py's
        retrieve_fact_targets_scored for why this exists and how the
        relevance threshold was calibrated). ``text`` should be the
        patient's own words (or close to them), not a made-up search term."""
        hits = retrieve_fact_targets_scored(self.corpus, self.embed, text)
        return {
            "fact_targets": [
                {**self._fact_target_result(target["fact_target_id"]), "score": round(score, 3)}
                for target, score in hits
            ]
        }

    def search_protocol_atoms(self, query: str) -> dict[str, Any]:
        atoms = retrieve_atoms(self.corpus, self.embed, query)
        results = []
        for atom in atoms:
            contradicted, unmet = atom_status(atom, self.session.facts)
            status = "CONTRADICTED" if contradicted else ("SATISFIED" if not unmet else "MISSING_INFO")
            results.append(
                {
                    "atom_id": atom["atom_id"],
                    "decision_point": atom.get("decision_point"),
                    "atom_type": atom.get("atom_type"),
                    "status": status,
                    "missing_fact_target_ids": unmet,
                }
            )
        return {"protocol_atoms": results}

    # -- mutation ----------------------------------------------------------

    def record_concept(
        self,
        concept_id: str,
        subject: str = "SELF",
        subject_label: str | None = None,
        status: str = "ASSERTED",
    ) -> dict[str, Any]:
        if concept_id not in self.corpus.concept_by_id:
            return {"ok": False, "error": f"Unknown concept_id {concept_id!r}."}
        if subject not in {"SELF", "OTHER_PERSON"}:
            return {"ok": False, "error": "subject must be SELF or OTHER_PERSON."}
        if status not in {"ASSERTED", "NEGATED"}:
            return {"ok": False, "error": "status must be ASSERTED or NEGATED."}

        label = (subject_label or "").strip()
        if subject == "OTHER_PERSON" and not label:
            # No label this call -- if we're already mid-triage for some
            # other person, assume this is still about them (the model need
            # not repeat subject_label on every follow-up call this turn).
            # Otherwise fall back to a generic phrase rather than rejecting
            # the call outright, which would burn tool-call budget.
            label = self.session.subject_label if self.session.subject_type == "OTHER_PERSON" else "người đó"

        switched = self.session.switch_subject(subject, label)
        if switched:
            # Union, not replace: keep every concept_id search_clinical_concepts
            # actually returned earlier this same turn (still legitimately
            # "seen" regardless of which subject it ends up recorded for), and
            # additionally treat a resumed subject's own already-recorded
            # concepts as seen too, so the model isn't forced to re-search
            # something it already established for that person earlier.
            self.seen_concept_ids |= set(self.session.concepts)

        if status == "NEGATED":
            changed = self.session.negate_concept(concept_id)
            if changed:
                self.session.turn_negated_concepts.append(concept_id)
            return {"ok": True, "negated": concept_id, "subject": self.session.subject_type}

        if concept_id not in self.seen_concept_ids:
            return {
                "ok": False,
                "error": "Call search_clinical_concepts first; concept_id was not a returned candidate.",
            }
        changed = self.session.assert_concept(concept_id)
        if changed:
            self.session.turn_asserted_concepts.append(concept_id)
        return {
            "ok": True,
            "asserted": concept_id,
            "subject": self.session.subject_type,
            "subject_label": self.session.subject_label,
        }

    def record_fact(self, fact_target_id: str, value: Any) -> dict[str, Any]:
        target = self.corpus.fact_by_id.get(fact_target_id)
        if target is None:
            return {"ok": False, "error": f"Unknown fact_target_id {fact_target_id!r}."}
        if isinstance(value, str) and _looks_like_a_question(value):
            return {
                "ok": False,
                "error": (
                    "value looks like a question, not something the patient said. Only record what the patient "
                    "themselves stated; do not record a question you were about to ask them."
                ),
            }
        converted = validate_fact(target, value)
        if converted is None:
            schema = target.get("value_schema") or {}
            return {
                "ok": False,
                "error": "Value does not satisfy this fact target's schema.",
                "value_schema": schema,
            }
        # gated_by must already be satisfied -- nothing recorded so far
        # establishes the precondition this fact target presupposes (see
        # decision.py's gate_satisfied for the full two-path rule and the
        # incident this specific guard closes, added 2026-08-29): live
        # trace, a burn case with only concept:recent_burn/burn_injury
        # asserted, Phase A wrote fact_target:limb_function_status=NORMAL_USE
        # (gated on joint_pain_present==YES, never established, not a direct
        # target of either asserted concept) from a reply that actually
        # answered the pending pain_severity question -- the wrong,
        # ungated fact_target silently absorbed the reply and the real
        # pending question was left unresolved, then re-asked next turn
        # with different wording (looked to the patient like the same
        # question twice). Rejecting the write here, with a pointer back to
        # pending_question_fact_target_id, nudges the model to resolve the
        # fact that was actually asked instead.
        if not gate_satisfied(fact_target_id, self.session, self.corpus):
            return {
                "ok": False,
                "error": (
                    "This fact target's gated_by precondition is not established anywhere in this session yet "
                    "(neither the required prior fact nor an already-asserted concept that directly covers it), "
                    "so it should not be set from an unrelated reply. If the patient's message actually answers "
                    "session_snapshot's pending_question_fact_target_id, call record_fact/"
                    "record_qualitative_observation for that fact_target_id instead."
                ),
            }
        # DESCRIPTIVE_SEVERITY (pain_severity) must not be set or overwritten as a
        # side effect of an answer to some other fact target -- observed failure:
        # answering the abdominal_pain_character question with "đau nhói" also
        # silently reset an already-correct pain_severity=3 to 7, purely because
        # the word sounded intense, immediately satisfying an ESI-2 atom the
        # patient never actually described. Require this turn's own
        # record_qualitative_observation call for the SAME fact_target_id first,
        # so the model must ground the number in wording actually about severity.
        if (
            target.get("reporting_style") == "DESCRIPTIVE_SEVERITY"
            and fact_target_id not in self.session.turn_observations
        ):
            return {
                "ok": False,
                "error": (
                    "Call record_qualitative_observation for this fact_target_id first, with the patient's own "
                    "wording about severity/intensity specifically -- record_fact for a DESCRIPTIVE_SEVERITY "
                    "target cannot be set or changed based on an answer about something else (e.g. pain "
                    "character/location), only on wording that actually describes how bad it feels."
                ),
            }
        self.session.facts[fact_target_id] = converted
        self.session.qualitative_observations.pop(fact_target_id, None)
        self.session.unknown_facts.discard(fact_target_id)
        self.session.needs_precision.discard(fact_target_id)
        if fact_target_id not in self.session.turn_accepted_facts:
            self.session.turn_accepted_facts.append(fact_target_id)
        return {"ok": True, "recorded": converted}

    def record_facts(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Same as calling record_fact once per item, in order, but in a
        single round trip -- exists purely to cut tool-call count when
        several facts are ready to record at once (a real information-dense
        message routinely resolves 3-4 facts in the same turn; that used to
        cost 3-4 separate round trips for no benefit, since each record_fact
        call is independent and stateless with respect to the others). One
        item's failure (bad id, schema mismatch, DESCRIPTIVE_SEVERITY
        ordering) does not block the rest -- each gets its own result,
        exactly as if called individually, so a failure can still be
        retried without redoing the ones that already succeeded."""
        results = []
        for item in items:
            try:
                result = self.record_fact(fact_target_id=item["fact_target_id"], value=item["value"])
            except (KeyError, TypeError) as exc:
                result = {"ok": False, "error": f"Bad item {item!r}: {exc}"}
            results.append({"fact_target_id": item.get("fact_target_id"), **result})
        return {"results": results}

    def record_qualitative_observation(self, fact_target_id: str, observation: str) -> dict[str, Any]:
        target = self.corpus.fact_by_id.get(fact_target_id)
        if target is None:
            return {"ok": False, "error": f"Unknown fact_target_id {fact_target_id!r}."}
        text = (observation or "").strip()
        if not text:
            return {"ok": False, "error": "observation must be non-empty text."}
        if _looks_like_a_question(text):
            return {
                "ok": False,
                "error": (
                    "observation looks like a question, not something the patient said. Only record what the "
                    "patient themselves stated; do not record a question you were about to ask them."
                ),
            }
        self.session.qualitative_observations[fact_target_id] = text
        self.session.unknown_facts.discard(fact_target_id)
        # EXACT_MEASUREMENT (vitals) always needs a raw number. DESCRIPTIVE_SEVERITY
        # (pain_severity) also needs one -- its severity_anchors exist so the model
        # can map words to a number, but a vague description recorded here without a
        # matching record_fact call must not be treated as resolved: without this,
        # the fact silently drops out of `askable` (agent.py) forever unresolved,
        # and any atom gating on its threshold can never be satisfied even when the
        # true severity would have crossed it.
        if (
            target.get("reporting_style") in ("EXACT_MEASUREMENT", "DESCRIPTIVE_SEVERITY")
            and fact_target_id not in self.session.facts
        ):
            self.session.needs_precision.add(fact_target_id)
        if fact_target_id not in self.session.turn_observations:
            self.session.turn_observations.append(fact_target_id)
        return {"ok": True, "recorded": text}

    def mark_fact_unknown(self, fact_target_id: str) -> dict[str, Any]:
        if fact_target_id not in self.corpus.fact_by_id:
            return {"ok": False, "error": f"Unknown fact_target_id {fact_target_id!r}."}
        self.session.unknown_facts.add(fact_target_id)
        self.session.needs_precision.discard(fact_target_id)
        return {"ok": True, "marked_unknown": fact_target_id}

    def finish_turn(
        self,
        intent: str = "TRIAGE",
        clarification: str | None = None,
        conversational_response: str | None = None,
        confirmed_ready: bool | None = None,
        patient_wants_to_stop: bool | None = None,
        retrieval_query: str | None = None,
    ) -> dict[str, Any]:
        self.outcome = {
            "intent": intent if intent in {"TRIAGE", "NON_CLINICAL"} else "TRIAGE",
            "clarification": clarification,
            "conversational_response": conversational_response,
            "confirmed_ready": confirmed_ready,
            "patient_wants_to_stop": bool(patient_wants_to_stop),
            # English clinical-register text for retrieve_atoms_scored's query
            # (see agent.py) -- replaces the old naive "concept labels + raw
            # Vietnamese message" join. None here just means Phase A didn't
            # provide one this turn; agent.py falls back to the last one
            # persisted on the session, and only to the old join as a last
            # resort (e.g. a test stub understanding_fn that never sets it).
            "retrieval_query": retrieval_query,
        }
        self.finished = True
        return {"ok": True}
