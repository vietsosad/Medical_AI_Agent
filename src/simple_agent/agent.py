"""A deliberately small runtime built only around the four mock-corpus files.

There is no release manager, graph, phase orchestration, or hidden clinical
rules. Concepts, concept-to-fact links, protocol requirements and the two
vector indexes are loaded directly from ``data/``. The model may select only
IDs supplied by this module; it cannot invent a clinical concept or patient
fact, and ESI/protocol matching is always plain deterministic Python
(``decision.py``), never LLM judgment.

One turn now runs three phases:

  Phase A (``understanding.py``): a bounded OpenAI tool-calling loop reads the
  message and calls tools on ``AgentToolbox`` to update session state --
  concepts (with who they apply to and whether asserted/negated), facts,
  qualitative observations, unknowns.

  Phase B (``decision.py``): deterministic protocol-atom evaluation against
  the now-updated session facts, and priority ranking of what to ask next.

  Phase C (``phrasing.py``): a small LLM call turns the chosen fact target (or
  final outcome) into a plain-language Vietnamese message.
"""

from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from openai import OpenAI

from . import skills
from .confirmation_intent import classify_confirmation_reply
from .corpus import REPO_ROOT, Corpus, CorpusError, fold, validate_fact
from .deepagent_understanding import run_deepagent_understanding_loop
from .decision import (
    MAX_ASKED_FACTS_PER_SESSION,
    MIN_ATOM_RELEVANCE_SCORE_FOR_PROACTIVE_ASK,
    STALE_QUESTION_LIMIT,
    atom_status,
    describe_satisfied_branch,
    evaluate_atoms,
    gate_satisfied,
    rank_question_targets,
    retrieve_atoms_scored,
)
from .phrasing import phrase_confirmation, phrase_outcome, phrase_question
from .preask_check import check_already_answered, content_words
from .resource_estimate import estimate_resource_count
from .session import Session
from .tools import AgentToolbox
from .tracing import (
    finish_trace_span,
    trace_span,
    wrap_simple_agent_openai,
)

logger = logging.getLogger(__name__)

__all__ = ["SimpleTriageAgent", "CorpusError", "REPO_ROOT"]


def _is_unknown_answer(message: str) -> bool:
    """Recognise a standalone inability-to-answer reply, not clinical content.

    This is conversation plumbing, analogous to recognising ``quit`` in the
    CLI: it is deliberately independent of symptoms, ESI levels, and the
    corpus, and is checked before Phase A so a short "không rõ" can't be
    mistaken for a new clinical assertion.
    """
    cleaned = re.sub(r"[^\w\s]", " ", fold(message))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned in {
        "khong ro", "toi khong ro", "minh khong ro", "em khong ro",
        "khong biet", "toi khong biet", "minh khong biet", "em khong biet",
        "ko ro", "ko biet", "khong chac", "toi khong chac", "khong co",
    }


# A deterministic keyword whitelist used to live here
# (_is_confirmation_affirmation), checking a "nothing else, go ahead" reply
# once a confirmation offer is pending, because Phase A's own
# ``finish_turn(confirmed_ready=...)`` flag was observed live to sometimes
# not follow its own correct understanding (2026-08-27). That whitelist
# needed three separate real-miss patches (2026-08-27, then twice more on
# 2026-08-28) for phrasings it didn't happen to enumerate yet -- "tôi không
# muốn bổ sung", "bạn hãy đánh giá luôn", "tôi đồng ý để bạn đánh giá" -- and
# still missed a plain "tôi không có bổ sung gì cả" the next time round: no
# finite exact-match list generalises to open-ended natural language.
# Replaced 2026-08-29 with a dedicated small classification call
# (``classify_confirmation_reply``, see confirmation_intent.py's module
# docstring for the full rationale) that judges the reply's plain meaning
# instead of matching it against enumerated phrases.


# Matches a denied-finding clause from a comma/semicolon/period boundary
# through to the next one, e.g. ", no neck stiffness" or ". Denies swelling".
_NEGATED_CLAUSE_RE = re.compile(
    r"(?:^|[,;.]\s*)(?:no|not|without|denies?|absent(?:\s+of)?|negative\s+for)\b[^,.;]*",
    re.IGNORECASE,
)


def _strip_negated_clauses(retrieval_query: str) -> str:
    """Best-effort removal of denied-finding clauses from a retrieval_query.

    Real incident (2026-08-27): embedding models handle negation poorly --
    "no neck stiffness" still surfaces neck-stiffness atoms because the
    words "neck"/"stiffness" dominate the embedded meaning regardless of the
    "no" in front. Measured live: scores for the exact atoms a patient had
    just denied went UP (0.58-0.66) each turn retrieval_query accumulated
    another "no X" clause, not down. prompts.py's system prompt now tells
    Phase A to describe only what IS present and never list denials, but
    that isn't reliably followed every turn (same class of gap as
    confirmed_ready elsewhere in this file) -- this is a deterministic
    backstop, not a replacement for that instruction.
    """
    cleaned = _NEGATED_CLAUSE_RE.sub("", retrieval_query)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,.;")
    # Never return an empty string (e.g. a query that was nothing but a
    # denial) -- an empty embed() call is worse than a slightly noisy one.
    return cleaned or retrieval_query


def _recover_dropped_concepts(toolbox: AgentToolbox) -> None:
    """Backstop for a real Phase A failure mode (2026-08-27): the model calls
    record_concept for a real symptom before ever calling
    search_clinical_concepts (valid content, just called out of order), gets
    back "Call search_clinical_concepts first", then -- even after a
    following search confirms that exact id as a real EXACT_ALIAS/CONFIDENT
    candidate -- never retries record_concept at all. The turn then falls
    through to process_turn's "not session.concepts" fallback, which hands
    the patient whatever leftover conversational_response text the model
    wrote (observed live: a fabricated, unrelated question, e.g. asking about
    fever after the patient said "đau bụng") instead of recording the
    concept they actually described and asking a real follow-up about it.

    Deliberately narrow, same spirit as _strip_negated_clauses: only
    recovers a call that failed *solely* because of ordering. The id must
    reappear in a *later* search result as
    EXACT_ALIAS or CONFIDENT (never AMBIGUOUS -- withholding those is
    correct), and must never have been successfully recorded afterwards --
    the model may have deliberately recorded a different, more specific id
    instead after further thought, and that decision must not be overridden.
    """
    log = toolbox.session.turn_tool_log
    already_recorded = {
        entry["arguments"].get("concept_id")
        for entry in log
        if entry["tool"] == "record_concept" and entry["result"].get("ok")
    }
    for i, entry in enumerate(log):
        if entry["tool"] != "record_concept" or entry["result"].get("ok"):
            continue
        if "search_clinical_concepts first" not in entry["result"].get("error", ""):
            continue
        args = entry["arguments"]
        concept_id = args.get("concept_id")
        if not concept_id or concept_id in already_recorded:
            continue
        confirmed = any(
            later["tool"] == "search_clinical_concepts"
            and any(
                candidate.get("concept_id") == concept_id
                and candidate.get("confidence") in {"EXACT_ALIAS", "CONFIDENT"}
                for candidate in later["result"].get("candidates", [])
            )
            for later in log[i + 1 :]
        )
        if confirmed:
            toolbox.record_concept(**args)


# Generic suffix tokens that recur across many unrelated fact_target ids
# (e.g. "fever_present", "gas_passage_status", "symptom_duration_bucket") --
# excluded from _fact_id_tokens below so two otherwise-unrelated fact
# targets don't look related purely because both ids happen to end the same
# way (see _recover_dropped_measurement's own comment for why this matters).
_GENERIC_FACT_ID_TOKENS = frozenset({
    "present", "status", "level", "bucket", "count", "value", "estimate", "type", "pattern",
})


def _fact_id_tokens(fact_target_id: str) -> set[str]:
    return set(fact_target_id.removeprefix("fact_target:").split("_")) - _GENERIC_FACT_ID_TOKENS


def _recover_dropped_measurement(toolbox: AgentToolbox) -> None:
    """Backstop for a real Phase A failure mode (2026-08-28): the patient
    volunteers a precise vital-sign figure together with the concept it
    belongs to (e.g. "sốt 38 độ"), the model records the symptom-present
    concept/fact correctly, but then guesses a plausible-sounding
    fact_target_id for the number that does not exist in this corpus at all
    (observed live: ``record_fact("fact_target:body_temperature_celsius",
    38)`` -> "Unknown fact_target_id") instead of the corpus's actual
    EXACT_MEASUREMENT fact target for that vital (``fact_target:
    temperature``, correctly linked to ``concept:fever`` in
    concept_relations.jsonl and required by 143 protocol atoms). It then
    proceeds straight to finish_turn -- unlike a schema-mismatch failure
    (e.g. reusing an already-known ENUM id like ``fact_target:fever_present``
    for the same number), which the model's own next tool call already
    tends to soften into a record_qualitative_observation fallback, a
    fabricated id leaves the number completely unrecorded, while
    conversational_response still narrates it back as if it had been
    captured.

    Deliberately narrower than a plain "any schema-valid candidate" match:
    ``concept:fever`` alone links to *four* EXACT_MEASUREMENT vitals
    (temperature, heart_rate, respiratory_rate, systolic_bp) whose ranges
    are wide enough that a single figure like 38 validly satisfies all of
    them, so schema-validity alone can't disambiguate. Requiring the
    fabricated id to share a real (non-generic) token with the correct
    candidate's own id grounds the recovery in what the model itself
    named -- "body_TEMPERATURE_celsius" unambiguously points at
    ``fact_target:temperature`` this way, without hardcoding any
    concept-to-vital clinical knowledge outside the corpus. Never guesses
    when more than one candidate both validates the value and shares a
    token (genuinely ambiguous) or when a candidate already has a recorded
    value (a deliberate later call, or an earlier turn's answer, must not
    be overridden).
    """
    log = toolbox.session.turn_tool_log
    already_recorded = {
        entry["arguments"].get("fact_target_id")
        for entry in log
        if entry["tool"] == "record_fact" and entry["result"].get("ok")
    }
    candidate_ids = list(dict.fromkeys(
        fact_id
        for concept_id in toolbox.session.concepts
        for fact_id in toolbox.corpus.facts_for_concept.get(concept_id, [])
    ))
    for entry in log:
        if entry["tool"] != "record_fact" or entry["result"].get("ok"):
            continue
        value = entry["arguments"].get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        failed_tokens = _fact_id_tokens(entry["arguments"].get("fact_target_id") or "")
        if not failed_tokens:
            continue
        matches = [
            fact_id
            for fact_id in candidate_ids
            if fact_id not in already_recorded
            and fact_id not in toolbox.session.facts
            and (target := toolbox.corpus.fact_by_id.get(fact_id))
            and target.get("reporting_style") == "EXACT_MEASUREMENT"
            and validate_fact(target, value) is not None
            and _fact_id_tokens(fact_id) & failed_tokens
        ]
        if len(matches) == 1:
            toolbox.record_fact(fact_target_id=matches[0], value=value)
            already_recorded.add(matches[0])


# Deterministic keyword sets (folded via corpus.fold, word-bounded), each
# matched against an OTHER_PERSON subject_label to recognise when the patient
# is describing the *same* person as the session's selected EHR profile card,
# just in the third person -- e.g. the card is the patient's spouse and they
# say "vợ tôi bị..." instead of "tôi bị...". Mirrors the exact canonical
# subject_label translations prompts.py already teaches the LLM to produce
# ("con của bạn", "vợ của bạn"/"chồng của bạn", "mẹ của bạn"/"bố của bạn",
# "anh/chị/em của bạn"), so a label built by that instruction always contains
# its relationship's keyword somewhere in it. "OTHER" has no reliable
# keyword (covers everything from "bạn tôi" to "cô tôi") and is deliberately
# absent -- an OTHER-relationship card never auto-applies its sex to an
# OTHER_PERSON subject; SELF is handled directly in _effective_sex below, not
# through this table.
_RELATIONSHIP_LABEL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "CHILD": ("con",),
    "SPOUSE": ("vo", "chong"),
    "PARENT": ("me", "bo", "ba", "cha"),
    "SIBLING": ("anh", "chi", "em"),
}


def _card_matches_label(card_relationship: str | None, subject_label: str) -> bool:
    if not card_relationship:
        return False
    keywords = _RELATIONSHIP_LABEL_KEYWORDS.get(card_relationship, ())
    folded = f" {fold(subject_label)} "
    return any(f" {keyword} " in folded for keyword in keywords)


def _effective_sex(session: Session) -> str | None:
    """The sex that should govern requires_sex gating for whoever the
    conversation is *currently* about, or None when that's genuinely unknown.

    SELF always resolves to the session's own card (see Session.card_gender
    -- set once at /start from the EHR profile the patient picked, None for
    an anonymous session): whichever person that card represents *is* "SELF"
    for this conversation, regardless of whether the card itself is tagged
    SELF or a relative under the account holder's own profile list (e.g. a
    spouse using a shared account and picking her own card still says "tôi").

    OTHER_PERSON only inherits the card's sex when the label the patient's
    wording produced plausibly names the *same* person the card already
    represents (see _card_matches_label) -- e.g. the card is the patient's
    spouse and they narrate in the third person ("vợ tôi bị...") instead of
    switching to first person. A mismatch (mentioning a different, uncarded
    relative) deliberately falls through to None -- unknown sex never blocks
    a question, it just means this shortcut doesn't apply, same as an
    anonymous session today.
    """
    if session.subject_type != "OTHER_PERSON":
        return session.card_gender
    if _card_matches_label(session.card_relationship, session.subject_label):
        return session.card_gender
    return None


def _references_fact(atom: dict[str, Any], fact_target_id: str) -> bool:
    """Whether any OR/AND branch of ``atom``'s requirements names ``fact_target_id``.

    Used only to decide whether the resource_count estimate (see
    resource_estimate.py) is worth attempting -- not an ESI decision itself.
    ``evaluate_atoms``'s ``atom_missing`` can't answer this: it only tracks
    facts still missing *and* still required, and protocol_atoms.jsonl marks
    resource_count non-required precisely so an unresolved value stops
    blocking a match outright -- which means it never appears in atom_missing
    at all, required or not.
    """
    for item in atom.get("requirements", []):
        branch = item if isinstance(item, list) else [item]
        if any(requirement.get("fact_target_id") == fact_target_id for requirement in branch):
            return True
    return False


# Upper bound on how many askable fact_targets get a pre-ask check in one
# turn (agent.py's process_turn walks the already-ranked askable list,
# checking-and-skipping each already-answered one before settling on what
# to actually ask -- see _run_preask_checks). Caps the cost/latency of a
# single very information-dense message without limiting *which* fact can
# ever be caught (unlike the retired extraction_backfill.py, this walks the
# corpus's own deterministic priority ranking, not an embedding-scored
# candidate list, so nothing is excluded by construction -- only how many
# get checked in one turn is bounded).
PREASK_CHECK_LIMIT = 6
# DESCRIPTIVE_SEVERITY fields (pain_severity) require record_qualitative_observation
# for the *same* fact_target_id in the *same* turn first (tools.py's
# record_fact guard, added after a real misattributed-severity incident) --
# a pre-ask check has no observation step of its own and runs before this
# turn's message is even processed that way, so it could never satisfy that
# guard regardless of what it finds. Skipped up front rather than spending
# a call that record_fact would just reject.
_PREASK_EXCLUDED_REPORTING_STYLES = frozenset({"DESCRIPTIVE_SEVERITY"})


class SimpleTriageAgent:
    """One-turn-at-a-time triage helper with a small, inspectable decision log.

    ``understanding_fn`` and ``phraser`` and ``embedder`` are dependency-
    injection seams for offline tests. Production uses OpenAI for all three.
    """

    def __init__(
        self,
        corpus_dir: Path | str = REPO_ROOT / "data/siu",
        index_dir: Path | str = REPO_ROOT / "data/indexes_siu",
        *,
        corpus: Corpus | None = None,
        embedder: Callable[[str], np.ndarray] | None = None,
        understanding_fn: Callable[[AgentToolbox, str], None] | None = None,
        phraser: Callable[[str, dict[str, Any]], str] | None = None,
        resource_estimator: Callable[[list[str], list[dict[str, Any]], list[dict[str, str]]], int | None]
        | None = None,
        confirmation_classifier: Callable[[str], bool] | None = None,
        preask_checker: Callable[[dict[str, Any], list[dict[str, str]]], Any | None] | None = None,
        enable_preask_check: bool = False,
    ) -> None:
        # ``corpus``, when given, skips file loading entirely -- used by
        # src/agents/simple_agent_runtime/runtime.py to hand in a Corpus
        # hydrated from Postgres (see src/simple_agent/pg_corpus.py) instead
        # of data/siu/data/indexes_siu. corpus_dir/index_dir are then unused.
        self.corpus = corpus if corpus is not None else Corpus(Path(corpus_dir), Path(index_dir))
        self._embedder = embedder
        self._understanding_fn = understanding_fn
        self._phraser = phraser
        self._resource_estimator = resource_estimator
        self._confirmation_classifier = confirmation_classifier
        # Defaults to disabled, unlike every other LLM-call seam above --
        # deliberately not gated by the same "embed a zero vector to make it
        # inert" trick every other retrieval-backed test relies on, because
        # the pre-ask check's candidate source (the already-ranked askable
        # list, see _run_preask_checks) needs no embedding call at all. Same
        # regression class caught live in this package before (see
        # preask_check.py's module docstring for the retired
        # extraction_backfill.py's own version of this): with no such gate,
        # ~30 existing offline tests in test_simple_agent.py that assert a
        # concept via a stub understanding_fn would start making real OpenAI
        # calls on every process_turn. Explicit opt-in here keeps every
        # existing (and future) offline test exactly as offline as the class
        # docstring above promises; production (runtime.py) and the manual
        # CLI (scripts/run_agent.py) turn this on explicitly. Passing an
        # explicit `preask_checker` stub always runs the check regardless of
        # this flag -- that's an explicit request to exercise it, not an
        # accident.
        self._enable_preask_check = enable_preask_check
        self._preask_checker = preask_checker
        self._preask_word_frequency: dict[str, int] | None = None
        self._client: OpenAI | None = None
        self.sessions: dict[str, Session] = defaultdict(Session)

    def _client_or_raise(self) -> OpenAI:
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or export it in this shell.")
            self._client = wrap_simple_agent_openai(OpenAI(api_key=api_key))
        return self._client

    def _embed(self, text: str) -> np.ndarray:
        if self._embedder:
            return np.asarray(self._embedder(text), dtype=np.float32)
        logger.debug("EMBED call | text=%r", text)
        model_name = "text-embedding-3-small"
        with trace_span(
            "simple_agent.embedding",
            run_type="embedding",
            inputs={"text_length": len(text), "model": model_name},
            metadata={"ls_provider": "openai", "ls_model_name": model_name},
        ) as embedding_span:
            response = self._client_or_raise().embeddings.create(
                input=[text],
                model=model_name,
            )
            vector = np.asarray(response.data[0].embedding, dtype=np.float32)
            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)
            usage_metadata = {
                key: value
                for key, value in {
                    "input_tokens": prompt_tokens,
                    "total_tokens": total_tokens,
                }.items()
                if isinstance(value, int)
            }
            finish_trace_span(
                embedding_span,
                {"dimensions": int(vector.size)},
                usage_metadata=usage_metadata,
            )
            return vector

    def _run_understanding(self, session: Session, message: str) -> dict[str, Any]:
        with trace_span(
            "simple_agent.phase_a_understanding",
            inputs={
                "message_length": len(message),
                "known_concept_count": len(session.concepts),
                "known_fact_count": len(session.facts),
            },
        ) as phase_span:
            toolbox = AgentToolbox(self.corpus, session, embed=self._embed)
            if self._understanding_fn:
                self._understanding_fn(toolbox, message)
                outcome = toolbox.outcome or {"intent": "TRIAGE"}
            else:
                outcome = run_deepagent_understanding_loop(toolbox, message)
            _recover_dropped_concepts(toolbox)
            _recover_dropped_measurement(toolbox)
            finish_trace_span(
                phase_span,
                {
                    "intent": outcome.get("intent"),
                    "finished": toolbox.finished,
                    "tool_call_count": len(session.turn_tool_log),
                    "accepted_fact_count": len(session.turn_accepted_facts),
                    "asserted_concept_count": len(session.turn_asserted_concepts),
                },
            )
            return outcome

    def _confirmation_intent(self, message: str) -> bool:
        with trace_span(
            "simple_agent.confirmation_intent",
            inputs={"message_length": len(message)},
        ) as confirmation_span:
            if self._confirmation_classifier:
                ready = self._confirmation_classifier(message)
            else:
                ready = classify_confirmation_reply(self._client_or_raise(), message)
            finish_trace_span(confirmation_span, {"ready_to_finalize": ready})
            return ready

    def _preask_word_frequency_table(self) -> dict[str, int]:
        """How many fact_targets in the WHOLE corpus mention each content
        word in their own name/lay_terms -- computed once, cached for the
        life of this agent (the corpus doesn't change mid-process). Feeds
        preask_check.py's _quote_supports_candidate: see that function's
        own docstring for the real incident (a generic word like "đau",
        pain, shared by ~20% of this corpus's fact_targets) this exists to
        weigh against.
        """
        if self._preask_word_frequency is None:
            counter: dict[str, int] = {}
            for target in self.corpus.fact_by_id.values():
                for word in content_words(f"{target.get('name', '')} {target.get('lay_terms', '')}"):
                    counter[word] = counter.get(word, 0) + 1
            self._preask_word_frequency = counter
        return self._preask_word_frequency

    def _run_preask_checks(self, session: Session, ranked: list[str]) -> set[str]:
        """Walks ``ranked`` (already priority-ordered by rank_question_targets)
        from the top, asking a small dedicated LLM call for each: has the
        patient, somewhere in this conversation, already explicitly
        answered this specific fact? Records any that come back answered
        and returns their ids, so the caller can drop them from both
        ``askable``/``ranked`` and settle on a real question to ask from
        whatever remains.

        Checks up to PREASK_CHECK_LIMIT *eligible* candidates (skipping any
        DESCRIPTIVE_SEVERITY one for free, without spending a call -- see
        _PREASK_EXCLUDED_REPORTING_STYLES) and does NOT stop at the first
        miss. Real corpus behaviour found live while testing this (2026-08-29):
        pain_severity (DESCRIPTIVE_SEVERITY, can never be confirmed this way
        regardless of what's found -- see that constant's own comment) ranks
        first for many concepts, including concept:burn_injury itself -- an
        earlier version of this method that broke out of the loop on the
        first excluded or unanswered candidate effectively never got past
        rank 1 for exactly the conversations this feature exists to help.
        A real dense message states several facts out of rank order, not
        necessarily contiguously from the top, so a genuine "not answered"
        partway down the list must not stop the rest of the walk either --
        only the checked-count cap does. Whatever remains unresolved after
        this runs, `ranked[0]` still correctly becomes this turn's question
        exactly as before, since only what's actually confirmed answered
        gets removed from `ranked` (see the call site in process_turn).

        See preask_check.py's module docstring for why this replaced
        extraction_backfill.py (a wide, once-per-turn scan) -- checking one
        fact at a time against the corpus's own deterministic ranking,
        right before it would be asked, measurably reduced the
        wrong-topic-bridging hallucination that scanning many candidates at
        once produced.
        """
        if not self._enable_preask_check and self._preask_checker is None:
            return set()
        if not session.history:
            return set()
        with trace_span(
            "simple_agent.preask_checks",
            inputs={
                "ranked_candidate_count": len(ranked),
                "conversation_turn_count": len(session.history),
            },
        ) as preask_span:
            conversation = [{"speaker": speaker, "text": text} for speaker, text in session.history]
            toolbox = AgentToolbox(self.corpus, session, embed=self._embed)
            answered: set[str] = set()
            checked = 0
            for fact_id in ranked:
                if checked >= PREASK_CHECK_LIMIT:
                    break
                target = self.corpus.fact_by_id[fact_id]
                if target.get("reporting_style") in _PREASK_EXCLUDED_REPORTING_STYLES:
                    continue
                checked += 1
                # Flat shape (not the raw corpus record, which nests
                # allowed_values under value_schema) -- built once here so an
                # injected preask_checker stub sees exactly what a real call
                # would send, not the raw corpus record's own nesting.
                fact_target_payload = {
                    "fact_target_id": fact_id,
                    "name": target["name"],
                    "lay_terms": target.get("lay_terms", ""),
                    "allowed_values": (target.get("value_schema") or {}).get("allowed_values"),
                }
                if self._preask_checker:
                    value = self._preask_checker(fact_target_payload, conversation)
                else:
                    value = check_already_answered(
                        self._client_or_raise(), fact_target=fact_target_payload, conversation=conversation,
                        word_frequency=self._preask_word_frequency_table(),
                    )
                if value is None:
                    continue
                result = toolbox.record_fact(fact_target_id=fact_id, value=value)
                if result.get("ok"):
                    answered.add(fact_id)
            finish_trace_span(
                preask_span,
                {"checked_count": checked, "answered_count": len(answered)},
            )
            return answered

    def _phrase(self, kind: str, context: dict[str, Any]) -> str:
        with trace_span(
            f"simple_agent.phase_c_{kind}",
            inputs={"kind": kind, "context_field_count": len(context)},
        ) as phrasing_span:
            if self._phraser:
                message = self._phraser(kind, context)
            else:
                client = self._client_or_raise()
                if kind == "question":
                    message = phrase_question(client, **context)
                elif kind == "confirmation":
                    message = phrase_confirmation(client, **context)
                else:
                    message = phrase_outcome(client, **context)
            finish_trace_span(
                phrasing_span,
                {"kind": kind, "response_length": len(message)},
            )
            return message

    @staticmethod
    def _subject_context(session: Session) -> dict[str, Any]:
        if session.subject_type != "OTHER_PERSON":
            return {"type": "SELF"}
        return {"type": "OTHER_PERSON", "label": session.subject_label}

    def _gate_satisfied(self, fact_id: str, session: Session) -> bool:
        """Whether ``fact_id`` may be proactively asked, per its optional
        ``gated_by``. Thin wrapper: the actual logic moved to decision.py's
        ``gate_satisfied`` (2026-08-29) so tools.py's ``record_fact`` can
        enforce the exact same rule when *accepting a value*, not just when
        deciding what to proactively ask -- see that function's own
        docstring for the full rationale and the real incident
        (fact_target:limb_function_status written from a reply that
        actually answered a pending, unrelated question) that motivated
        sharing it.
        """
        return gate_satisfied(fact_id, session, self.corpus)

    def _sex_compatible(self, fact_id: str, session: Session) -> bool:
        """Whether ``fact_id`` may be asked of whoever the conversation is
        currently about, per its optional ``requires_sex`` (see
        ``fact_targets.jsonl``): a handful of fact targets (pregnancy status,
        vaginal bleeding, uterine contractions...) only make sense for one
        sex, but reach ``askable`` as an ordinary differential fact for
        concepts like fever/abdominal pain that have nothing to do with what
        the patient actually said about themselves -- real risk (2026-08-28):
        the demo patient account is male, so an unrelated fever/abdominal
        complaint could proactively ask him about being pregnant.

        Permissive by default, same spirit as _gate_satisfied: only excludes
        when the *effective* sex for the current subject (see
        _effective_sex) is actually known and contradicts requires_sex.
        Unknown sex (anonymous session, or an OTHER_PERSON not matching the
        session's card) always lets the question through -- silently missing
        a real case is worse than an occasional harmless ask.
        """
        requires_sex = self.corpus.fact_by_id[fact_id].get("requires_sex")
        if not requires_sex:
            return True
        effective_sex = (_effective_sex(session) or "").strip().upper()
        # Only ever *excludes* on an unambiguous MALE/FEMALE mismatch -- an
        # EHR profile's "Other" (a real, deliberate value) is treated the
        # same as genuinely unknown, since it says nothing about which of
        # these two the gate cares about either way.
        if effective_sex not in {"MALE", "FEMALE"}:
            return True
        return effective_sex == requires_sex.strip().upper()

    def _confirmation_context(self, session: Session) -> dict[str, Any]:
        return {
            "recorded_concepts": [self.corpus.concept_by_id[c]["canonical_name"] for c in sorted(session.concepts)],
            "recorded_facts": [
                {"name": self.corpus.fact_by_id[fid]["name"], "value": value}
                for fid, value in session.facts.items()
            ],
            "subject": self._subject_context(session),
        }

    def _estimate_resource_count(self, session: Session) -> int | None:
        concepts = [self.corpus.concept_by_id[c]["canonical_name"] for c in sorted(session.concepts)]
        recorded_facts = [
            {"name": self.corpus.fact_by_id[fid]["name"], "value": value}
            for fid, value in session.facts.items()
        ]
        qualitative_observations = [
            {"name": self.corpus.fact_by_id[fid]["name"], "observation": text}
            for fid, text in session.qualitative_observations.items()
        ]
        with trace_span(
            "simple_agent.resource_count_estimation",
            inputs={
                "concept_count": len(concepts),
                "recorded_fact_count": len(recorded_facts),
                "qualitative_observation_count": len(qualitative_observations),
            },
        ) as resource_span:
            if self._resource_estimator:
                estimate = self._resource_estimator(
                    concepts,
                    recorded_facts,
                    qualitative_observations,
                )
            else:
                estimate = estimate_resource_count(
                    self._client_or_raise(),
                    concepts=concepts,
                    recorded_facts=recorded_facts,
                    qualitative_observations=qualitative_observations,
                )
            finish_trace_span(
                resource_span,
                {"estimate_available": estimate is not None},
            )
            return estimate

    def process_turn(self, session_id: str, message: str) -> dict[str, Any]:
        logger.debug("=== TURN START | session=%s | message=%r ===", session_id, message)
        session = self.sessions[session_id]
        session.start_turn()
        session.remember_turn("patient", message)
        # Captured before anything below can mutate last_question, so the
        # stale-question bail-out can tell "same fact re-selected again" from
        # "a fresh question, first time asked".
        previous_question = session.last_question

        # Deterministic guardrail, checked before any LLM call: a clear attempt
        # to extract the system prompt/instructions gets a fixed refusal and
        # never reaches Phase A, so it can't be talked around. Session state
        # (concepts/facts already recorded) is left untouched.
        with trace_span(
            "simple_agent.guardrail_check",
            inputs={"message_length": len(message)},
        ) as guardrail_span:
            prompt_probe = skills.is_prompt_probe(message)
            finish_trace_span(guardrail_span, {"prompt_probe_blocked": prompt_probe})
        if prompt_probe:
            session.remember_turn("agent", skills.PROBE_REFUSAL_MESSAGE)
            return self._result(
                skills.PROBE_REFUSAL_MESSAGE, route="GUARDRAIL", action="REFUSE",
                reason="Message matched the deterministic system-prompt-probe pattern; no LLM call was made.",
                session=session, retrieved=0,
            )

        # Do this before Phase A. Otherwise a short reply such as "không rõ"
        # can be mistaken for a new clinical assertion and advance to a
        # different, equally unanswerable fact target.
        declined_fact = None
        if session.last_question and _is_unknown_answer(message):
            declined_fact = session.last_question
            session.unknown_facts.add(declined_fact)
            session.needs_precision.discard(declined_fact)
            session.last_question = None

        # Same spirit as the block above: computed before Phase A so a plain
        # "go ahead" reply doesn't depend on Phase A reliably setting
        # finish_turn's confirmed_ready flag on this same call (see
        # confirmation_intent.py's module docstring for the observed
        # failure that motivated a separate, dedicated classification call).
        # Only matters below if session.confirmation_offered is still true by
        # then; harmless to compute unconditionally here. Short-circuits on
        # ``and`` exactly as before, so this LLM call only ever fires on the
        # turn right after a confirmation was actually offered, not every turn.
        confirmation_intent = session.confirmation_offered and self._confirmation_intent(message)

        outcome = self._run_understanding(session, message)

        # The model may recognise a natural unknown reply that is not in the
        # small deterministic set above.
        if session.last_question and session.last_question in session.unknown_facts:
            declined_fact = declined_fact or session.last_question
            session.last_question = None

        intent = outcome.get("intent")
        if intent != "TRIAGE" and not session.concepts:
            reply = outcome.get("conversational_response") or "Chào bạn! Bạn đang gặp vấn đề sức khỏe gì?"
            session.remember_turn("agent", reply)
            return self._result(
                reply, route="NON_CLINICAL", action="RESPOND",
                reason="The message did not state a health concern for the patient or anyone they're asking about.",
                session=session, retrieved=0,
            )

        clarification = outcome.get("clarification")
        if clarification or not session.concepts:
            # Prefer the model's own conversational_response over the generic
            # fallback when there is one.
            reply = (
                clarification
                or outcome.get("conversational_response")
                or "Bạn có thể mô tả triệu chứng, vị trí và thời điểm bắt đầu không?"
            )
            session.remember_turn("agent", reply)
            return self._result(
                reply, route="CLARIFY", action="ASK_CLARIFICATION",
                reason="Ambiguous or missing concept selection required a clarifying question.",
                session=session, retrieved=0,
            )

        # Prefer Phase A's own retrieval_query (an English clinical-register
        # summary of the whole picture, see prompts.py/tools.py's finish_turn)
        # over the old naive join -- fixes the exact failure class from the
        # syncope incident, where a single noisy raw-Vietnamese turn (e.g.
        # "bạn đoán xem") could swing the embedded query's meaning on its own.
        # Two fallbacks, in order: the last retrieval_query persisted on the
        # session (Phase A said nothing new this turn -- same query as
        # before, not an empty one), then the old join (Phase A never
        # produced one at all, e.g. a test's stub understanding_fn).
        retrieval_query = outcome.get("retrieval_query") or session.retrieval_query
        if not retrieval_query:
            concept_labels = [self.corpus.concept_by_id[c]["canonical_name"] for c in session.concepts]
            retrieval_query = "; ".join(concept_labels + [message])
        # Deterministic backstop (see _strip_negated_clauses) for when Phase A
        # doesn't follow the system prompt's "describe only what IS present"
        # instruction -- stripped before persisting, not just before this
        # call, so a later quiet turn's fallback-to-last-query also benefits.
        retrieval_query = _strip_negated_clauses(retrieval_query)
        session.retrieval_query = retrieval_query
        with trace_span(
            "simple_agent.phase_b_retrieval",
            inputs={
                "query_length": len(retrieval_query),
                "known_concept_count": len(session.concepts),
                "known_fact_count": len(session.facts),
            },
        ) as retrieval_span:
            retrieved_scored = retrieve_atoms_scored(
                self.corpus,
                self._embed,
                retrieval_query,
            )
            scores = [float(score) for _atom, score in retrieved_scored]
            finish_trace_span(
                retrieval_span,
                {
                    "candidate_count": len(retrieved_scored),
                    "top_score": round(max(scores), 4) if scores else None,
                },
            )
        session.seen_atom_ids = list(
            dict.fromkeys(session.seen_atom_ids + [atom["atom_id"] for atom, _score in retrieved_scored])
        )
        # Track the best score ever seen for each atom_id -- used below to
        # decide which atom-only-linked facts may be proactively asked
        # (MIN_ATOM_RELEVANCE_SCORE_FOR_PROACTIVE_ASK). Deliberately max, not
        # this turn's score: an atom retrieved confidently once stays trusted
        # even if a later turn's weaker query also happens to re-surface it.
        for atom, score in retrieved_scored:
            atom_id = atom["atom_id"]
            if score > session.atom_relevance_score.get(atom_id, 0.0):
                session.atom_relevance_score[atom_id] = score
        # Debug-only (see SimpleDecisionDebugPanel): this turn's retrieval
        # results with their raw scores, so a borderline/noisy match (like
        # the syncope-atom incident) is visible from the browser instead of
        # needing a one-off probe script against the corpus.
        session.turn_retrieved_atoms = [
            {
                "atom_id": atom["atom_id"],
                "score": round(float(score), 4),
                "confident_enough_to_ask": score >= MIN_ATOM_RELEVANCE_SCORE_FOR_PROACTIVE_ASK,
            }
            for atom, score in retrieved_scored
        ]
        # retrieved_atom_ids keeps its original, narrower meaning ("atoms
        # embedding search actually surfaced this session") for everything
        # below that gates *proactive asking* on retrieval confidence
        # (confidently_missing) or reports "retrieved=" in the debug panel.
        retrieved_atom_ids = session.seen_atom_ids

        # Generic fallback atoms (see corpus.py's GENERIC_FALLBACK_FACT_TARGET_IDS)
        # are always in play for *evaluation*, independent of whether this
        # turn's retrieval query happens to resemble the topic they were
        # authored under -- real incident (2026-08-28): "tôi bị đau tay" ("my
        # arm/hand hurts") never retrieved atom:esi_4_one_resource (fully
        # generic requirements, topic-abstract wording), so a
        # fully-supported ESI4 match sat unused. Deliberately excluded from
        # `retrieved_atom_ids`/confidently_missing below though: letting
        # these atoms' own unmet fields (pain_severity, symptom_onset...)
        # proactively trigger `askable` would ask about pain severity on
        # every session from turn one, even one where the patient never
        # mentioned pain at all -- these atoms exist to *recognise* a match
        # once its generic facts are already known some other way (concept
        # links, patient's own wording), never to drive what gets asked.
        atom_ids_in_play = list(
            dict.fromkeys(retrieved_atom_ids + list(self.corpus.generic_fallback_atom_ids))
        )
        atoms = [self.corpus.atom_by_id[atom_id] for atom_id in atom_ids_in_play]
        with trace_span(
            "simple_agent.phase_b_evaluate_protocol_atoms",
            inputs={
                "atom_count": len(atoms),
                "known_fact_count": len(session.facts),
            },
        ) as evaluation_span:
            supported, atom_missing, _excluded = evaluate_atoms(
                atoms,
                session.facts,
            )
            finish_trace_span(
                evaluation_span,
                {
                    "supported_atom_count": len(supported),
                    "incomplete_atom_count": len(atom_missing),
                    "excluded_atom_count": len(_excluded),
                },
            )

        # Deterministic early-stop, mirroring the real ESI algorithm's own
        # short-circuit: decision points A (immediate life-saving) and B/C
        # (high-risk / danger-zone vitals) assign ESI 1/2 and, in the real
        # algorithm, are never followed by further questioning -- only a
        # decision point D (resource-count) match needs more than the atom
        # already in hand, since ESI 3/4/5 is settled by how many distinct
        # resources are predicted, not a single criterion. Once such a
        # decisive atom is already fully supported, asking about other,
        # lower-priority atoms/concepts only delays a result that won't
        # change what gets returned.
        decisive_match = any(
            atom.get("decision_effect", {}).get("candidate_esi") in (1, 2) for atom in supported
        )

        # Deterministic resource budget, not an ESI judgment: once this many
        # distinct fact_targets have been engaged with (answered, declined or
        # observed) in the session, stop opening new questions even if some
        # asserted concept still has unresolved direct_targets left. Without
        # this, a session that asserts several overlapping concepts (each
        # pulling in its own REQUIRES_ASSESSMENT_OF list) can keep growing the
        # askable set faster than it shrinks and never reach confirmation.
        asked_so_far = len(session.facts) + len(session.unknown_facts) + len(session.qualitative_observations)
        # Phase A sets this when the patient signals general reluctance to
        # keep answering ("kệ đi", "hỏi gì nhiều vậy") -- distinct from
        # mark_fact_unknown's per-fact "I don't know". Without checking it
        # here, that signal (which Phase A's own conversational_response often
        # already reflects) never reaches question selection: askable stays
        # non-empty and the interview just keeps going.
        patient_wants_to_stop = bool(outcome.get("patient_wants_to_stop"))
        if decisive_match or patient_wants_to_stop or asked_so_far >= MAX_ASKED_FACTS_PER_SESSION:
            askable: list[str] = []
            direct_targets: list[str] = []
        else:
            # Union of two sources, not concept-links alone: a concept's own
            # REQUIRES_ASSESSMENT_OF relations are frequently thinner than
            # what the atoms actually retrieved for it require (e.g.
            # concept:arm_pain links only symptom_onset/pain_severity, while
            # its retrieved atoms also need upper_extremity_movement_ability,
            # resource_count, etc.) -- without atom_missing here, the
            # interview runs out of things to ask and returns INCOMPLETE
            # despite there being more relevant, patient-answerable questions
            # the retrieved atoms are explicitly waiting on.
            direct_targets = list(dict.fromkeys(
                fact_id for concept_id in session.concepts for fact_id in self.corpus.facts_for_concept.get(concept_id, [])
            ))
            # A fact that reaches `askable` only via atom_missing (no direct
            # concept link) must have at least one owning atom whose
            # retrieval score cleared MIN_ATOM_RELEVANCE_SCORE_FOR_PROACTIVE_ASK
            # -- a stricter bar than the MIN_ATOM_RELEVANCE_SCORE that got it
            # into `atoms`/atom_missing in the first place. Real incident
            # (2026-08-27): a single off-topic reply scored just over the
            # lower bar against an ESI-2 syncope atom for a "fatigue" query,
            # so the interview proactively asked about fainting with zero
            # supporting evidence. This only filters what gets ASKED --
            # `atoms`/`supported`/`atom_missing`/matched_esi_levels above are
            # untouched, so a low-confidence atom still counts fully if the
            # patient volunteers the fact some other way.
            confidently_missing: set[str] = set()
            for atom_id in retrieved_atom_ids:
                atom = self.corpus.atom_by_id[atom_id]
                contradicted, unmet = atom_status(atom, session.facts)
                if contradicted or not unmet:
                    continue
                score = session.atom_relevance_score.get(atom["atom_id"])
                if score is None or score >= MIN_ATOM_RELEVANCE_SCORE_FOR_PROACTIVE_ASK:
                    confidently_missing.update(unmet)
            candidate_targets = list(dict.fromkeys(direct_targets + list(confidently_missing)))
            askable = [
                fact_id for fact_id in candidate_targets
                if self.corpus.fact_by_id[fact_id].get("reporting_style") != "CLINICIAN_ONLY"
                and fact_id not in session.facts
                and fact_id not in session.unknown_facts
                and (fact_id not in session.qualitative_observations or fact_id in session.needs_precision)
                and self._gate_satisfied(fact_id, session)
                and self._sex_compatible(fact_id, session)
            ]
        with trace_span(
            "simple_agent.phase_b_rank_questions",
            inputs={
                "askable_count": len(askable),
                "atom_count": len(atoms),
            },
        ) as ranking_span:
            ranked = rank_question_targets(session, self.corpus, atoms, askable)
            finish_trace_span(
                ranking_span,
                {
                    "ranked_count": len(ranked),
                    "question_selected": bool(ranked),
                },
            )

        # Before settling on what to ask, walk down the ranked list checking
        # whether the conversation already answers each one -- see
        # _run_preask_checks' own docstring. Whatever comes back answered is
        # dropped from *both* askable and ranked here (not just ranked) so
        # the quiet_turn/stale-question logic just below, which re-reads
        # askable, can't re-select something pre-ask just resolved.
        preask_answered = self._run_preask_checks(session, ranked)
        if preask_answered:
            askable = [fid for fid in askable if fid not in preask_answered]
            ranked = [fid for fid in ranked if fid not in preask_answered]
        question_target = ranked[0] if ranked else None

        # Real failure observed live: a reply that Phase A extracted nothing
        # from (a dodge like "bạn đoán xem", not a real answer and not one of
        # the fixed "không rõ" phrases either) still feeds into this turn's
        # retrieve_atoms() query (see the `message` in the "; ".join(...)
        # above). A freshly-retrieved atom's single-requirement fact can then
        # outrank the still-unanswered `previous_question` on both
        # decisiveness and decision-point urgency (rank_question_targets has
        # no notion of "already pending"), so the interview silently drops a
        # question the patient never actually answered and jumps to an
        # unrelated, possibly more sensitive one (e.g. fatigue -> syncope)
        # with zero evidence behind it. Deliberately narrow: this only
        # re-points *which* question gets asked next turn -- it never touches
        # retrieval, atom evaluation, or ESI matching (`atoms`/`supported`/
        # `atom_missing`/`matched_esi_levels` above are all unaffected), and
        # it only overrides when nothing at all was learned this turn. If
        # `previous_question` keeps coming up empty, the stale-question
        # bail-out just below still kicks in after STALE_QUESTION_LIMIT turns
        # exactly as it already does for any other repeated question.
        quiet_turn = not (
            session.turn_asserted_concepts
            or session.turn_accepted_facts
            or session.turn_negated_concepts
            or session.turn_observations
        )
        if (
            quiet_turn
            and previous_question
            and previous_question != declined_fact
            and previous_question in askable
            and question_target != previous_question
        ):
            question_target = previous_question

        if question_target and question_target == previous_question:
            session.stale_question_streak += 1
            if session.stale_question_streak >= STALE_QUESTION_LIMIT:
                # Deterministic bail-out: this exact fact_target_id has been
                # re-selected repeatedly without ever resolving -- Phase A
                # recorded related concepts from the patient's answers but
                # never closed the pending fact_target itself. Don't ask a
                # 3rd time; treat it like the patient couldn't give a
                # schema-valid answer and move on with whatever else is
                # still askable, the same way an explicit "không rõ" would.
                session.unknown_facts.add(question_target)
                session.needs_precision.discard(question_target)
                session.stale_question_streak = 0
                askable = [fid for fid in askable if fid != question_target]
                with trace_span(
                    "simple_agent.phase_b_rerank_after_stale_question",
                    inputs={"askable_count": len(askable)},
                ) as rerank_span:
                    ranked = rank_question_targets(
                        session,
                        self.corpus,
                        atoms,
                        askable,
                    )
                    finish_trace_span(
                        rerank_span,
                        {
                            "ranked_count": len(ranked),
                            "question_selected": bool(ranked),
                        },
                    )
                question_target = ranked[0] if ranked else None
        else:
            session.stale_question_streak = 0

        if question_target:
            # New askable info superseded any pending confirmation offer.
            session.confirmation_offered = False

            # 2a: tell Phase C when this question is a pivot into (or across)
            # a red-flag/differential screen unrelated to what was just asked,
            # so it can frame the switch instead of sounding like a
            # non-sequitur (real incident: fever -> neck stiffness -> oral
            # swelling -> joint count -> joint redness, each with zero
            # acknowledgment of the jump). Deliberately phrasing-only: this
            # never changes *which* fact gets asked (that's 2b, not done
            # yet) -- only whether Phase C is told to add a short transition.
            # "Screening" = reached only via some atom's own requirement, not
            # one of the concept's own direct follow-ups (direct_targets) --
            # comparing *owning atoms* (not just fact ids) means continuing to
            # ask a requirement of the *same* atom correctly does not count
            # as a pivot.
            #
            # _owning_atoms used to be defined via atom_status's *unmet* list
            # (a fact "owns" an atom only while that atom still needs it).
            # Real incident (2026-08-29, leg-pain session): by the time this
            # runs, the message that just answered ``previous_question`` has
            # already been recorded into session.facts, so it can never be
            # "unmet" for anything any more -- old_owners was always empty in
            # the ordinary one-fact-per-turn flow, so topic_shift came out
            # True for nearly every atom-derived question, including a
            # completely mundane one (symptom_trend, "liên tục hay từng cơn")
            # right after symptom_onset -- Phase C, told this was "an
            # unrelated safety check", then invented its own red-flag
            # question (dizziness/fainting) instead of asking about
            # symptom_trend at all (see phrasing.py's QUESTION_PHRASING
            # prompt for the matching fix). Fixed by using _references_fact
            # (plain membership in an atom's requirements, regardless of
            # whether it's currently resolved) instead -- verified live
            # against this exact session: symptom_onset and symptom_trend
            # share two real owning atoms already retrieved that turn
            # (atom:esi_4_stable_gradual_joint_pain,
            # atom:esi_5_gradual_stable_mild_joint_pain), so this now
            # correctly comes out topic_shift=False.
            def _owning_atoms(fact_id: str | None) -> set[str]:
                if not fact_id:
                    return set()
                return {atom["atom_id"] for atom in atoms if _references_fact(atom, fact_id)}

            topic_shift = False
            if question_target not in direct_targets and question_target != previous_question:
                new_owners = _owning_atoms(question_target)
                old_owners = _owning_atoms(previous_question)
                topic_shift = not (new_owners & old_owners)

            session.last_question = question_target
            fact_target = self.corpus.fact_by_id[question_target]
            question = self._phrase(
                "question",
                {
                    "fact_target": fact_target,
                    "needs_precision": question_target in session.needs_precision,
                    "history": session.history,
                    "subject": self._subject_context(session),
                    "topic_shift": topic_shift,
                },
            )
            session.remember_turn("agent", question)
            return self._result(
                question, route="TRIAGE", action="ASK_NEXT",
                reason=(
                    f"Skipped unavailable fact {declined_fact}; selected patient-reportable {question_target}."
                    if declined_fact
                    else (
                        f"Re-asking still-unresolved {question_target}: the last reply gave no new "
                        "information, so a newly retrieved fact was not allowed to pre-empt it."
                        if quiet_turn and question_target == previous_question
                        else f"Selected patient-reportable fact {question_target} linked to the concept."
                    )
                ),
                session=session, retrieved=len(retrieved_atom_ids), supported=len(supported),
                missing=len(atom_missing), question_target=question_target,
            )

        session.last_question = None

        # Every askable fact is resolved. Confirm with the patient before
        # finalising -- they may still want to add or correct something.
        confirmed_ready = outcome.get("confirmed_ready") is True or confirmation_intent
        if not session.confirmation_offered or not confirmed_ready:
            first_offer = not session.confirmation_offered
            session.confirmation_offered = True
            summary = self._phrase("confirmation", self._confirmation_context(session))
            session.remember_turn("agent", summary)
            return self._result(
                summary, route="TRIAGE", action="ASK_CONFIRMATION",
                reason=(
                    "All askable patient-reportable facts are resolved; confirming before finalising."
                    if first_offer else "Patient has not yet confirmed readiness to finalise; re-offering."
                ),
                session=session, retrieved=len(retrieved_atom_ids), supported=len(supported),
                missing=len(atom_missing), question_target=None,
            )

        session.confirmation_offered = False

        # Nearly every ESI 3/4/5 (D_RESOURCE_PREDICTION) atom needs
        # fact_target:resource_count, but it is CLINICIAN_ONLY -- never asked
        # of the patient -- and protocol_atoms.jsonl now marks it non-required
        # there so an unresolved value no longer blocks a match outright (see
        # data/siu/MULTI_TURN_PROBE_FINDINGS.md). That alone can still leave
        # several adjacent ESI levels simultaneously "supported" with none
        # ruled out. Only attempt to narrow that down when some retrieved atom
        # actually names this fact at all (_references_fact -- atom_missing
        # can't tell us this any more, precisely because required=false stops
        # it from ever being "missing") -- never for a purely ESI 1/2 decisive
        # match, whose atoms don't reference it -- and only once per session
        # (resource_count_estimated guard), right here where every
        # patient-answerable question is already resolved and confirmed, i.e.
        # exactly when there is enough recorded context for the estimate to
        # be worth trusting.
        if (
            "fact_target:resource_count" not in session.facts
            and not session.resource_count_estimated
            and any(_references_fact(atom, "fact_target:resource_count") for atom in atoms)
        ):
            session.resource_count_estimated = True
            estimated = self._estimate_resource_count(session)
            if estimated is not None:
                session.facts["fact_target:resource_count"] = estimated
                with trace_span(
                    "simple_agent.phase_b_reevaluate_after_resource_estimate",
                    inputs={"atom_count": len(atoms)},
                ) as reevaluation_span:
                    supported, atom_missing, _excluded = evaluate_atoms(
                        atoms,
                        session.facts,
                    )
                    finish_trace_span(
                        reevaluation_span,
                        {
                            "supported_atom_count": len(supported),
                            "incomplete_atom_count": len(atom_missing),
                            "excluded_atom_count": len(_excluded),
                        },
                    )

        subject_context = self._subject_context(session)
        matched_esi_levels: list[int] = []
        matched_atoms: list[dict[str, Any]] = []
        if supported:
            # Persist here, not where atom_ids_in_play was built above: a
            # generic fallback atom's resource_count condition is marked
            # non-required (see the comment just above), so it can look
            # vacuously "supported" *before* the estimate above ever runs --
            # persisting that early would flood every session's SBAR
            # citations/debug panel with ~47 generic atoms from turn one,
            # most never actually earning their match. This point runs after
            # the estimate (or once resource_count was never needed at all),
            # so `supported` here already reflects the real, final facts --
            # only atoms that genuinely decided this outcome get remembered.
            session.seen_atom_ids = list(
                dict.fromkeys(session.seen_atom_ids + [atom["atom_id"] for atom in supported])
            )
            matched_esi_levels = sorted(
                {
                    int(level)
                    for atom in supported
                    if (level := atom.get("decision_effect", {}).get("candidate_esi")) is not None
                }
            )
            # Patient-facing (not debug-only, see _result's docstring below):
            # which specific atom(s) actually produced this match, so the UI
            # can show "matched protocol criteria" instead of a bare ESI
            # number. criteria_text is the same English clinical-register
            # sentence protocol_atoms.jsonl's retrieval.text already carries
            # for embedding -- shown as-is (mock corpus, no official
            # translation), same honesty standard as SBAR's citations.
            #
            # Narrowed to the single most severe (lowest-numbered) matched
            # level (2026-08-29, real feedback): `supported` can legitimately
            # contain atoms for several different matched ESI levels at once
            # (e.g. a benign ESI 3 "stable, 2+ resources" atom alongside a
            # genuine ESI 2 finding) -- showing all of them read as if the
            # case were several severities simultaneously, when only the
            # most severe one is the actual, actionable result. Same
            # narrowing applied to SBAR's citations, see sbar.py's
            # _citation_entries docstring for the fuller rationale.
            top_level = matched_esi_levels[0] if matched_esi_levels else None
            matched_atoms = [
                {
                    "atom_id": atom["atom_id"],
                    "decision_point": atom.get("decision_point"),
                    "criteria_text": atom.get("retrieval", {}).get("text"),
                    # Which specific requirement(s) the patient's own reported
                    # facts satisfied, e.g. "Mức độ đau (>= 8): 9" -- not just
                    # the atom's static English sentence above. See
                    # decision.py's describe_satisfied_branch docstring.
                    "satisfied_requirements": describe_satisfied_branch(atom, session.facts, self.corpus),
                }
                for atom in supported
                if top_level is None or atom.get("decision_effect", {}).get("candidate_esi") == top_level
            ]
            # Same top-severity-only narrowing as matched_atoms/citations
            # just above -- real feedback (2026-08-29): the outcome message
            # itself still said "cấp 2 hoặc 3" after matched_atoms/citations
            # were already narrowed to just ESI 2, an inconsistency the
            # patient noticed directly. matched_esi_levels itself is left
            # untouched (still the full set, e.g. for the sidebar/history
            # list badges) -- only what gets phrased into this message narrows.
            levels = [str(top_level)] if top_level is not None else []
            message_out = self._phrase("outcome", {"matched": True, "esi_levels": levels, "subject": subject_context})
            action, reason = "RETURN_MATCH", "At least one retrieved protocol atom is fully supported by stated facts."
        else:
            message_out = self._phrase("outcome", {"matched": False, "esi_levels": [], "subject": subject_context})
            action, reason = "RETURN_INCOMPLETE", "No retrieved protocol atom is fully supported and no patient-reportable linked fact remains."
        session.remember_turn("agent", message_out)
        return self._result(
            message_out, route="TRIAGE", action=action, reason=reason,
            session=session, retrieved=len(atoms), supported=len(supported),
            missing=len(atom_missing), question_target=None, matched_esi_levels=matched_esi_levels,
            matched_atoms=matched_atoms,
        )

    @staticmethod
    def _result(
        message: str, *, route: str, action: str, reason: str, session: Session, retrieved: int,
        supported: int = 0, missing: int = 0, question_target: str | None = None,
        matched_esi_levels: list[int] | None = None, matched_atoms: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        logger.debug(
            "=== TURN END | route=%s action=%s question_target=%s reason=%s | reply=%r ===",
            route, action, question_target, reason, message,
        )
        return {
            "message": message,
            "decision": {
                "route": route,
                "action": action,
                "reason": reason,
                "subject_type": session.subject_type,
                "subject_label": session.subject_label or None,
                "concepts": sorted(session.concepts),
                "retrieved_protocol_atoms": retrieved,
                "accepted_fact_ids": list(session.turn_accepted_facts),
                "qualitative_observation_ids": list(session.turn_observations),
                "asserted_concept_ids": list(session.turn_asserted_concepts),
                "negated_concept_ids": list(session.turn_negated_concepts),
                "supported_protocol_atoms": supported,
                "unresolved_protocol_requirements": missing,
                "question_target_id": question_target,
                "matched_esi_levels": matched_esi_levels or [],
                "matched_atoms": matched_atoms or [],
                # Debug-only fields below -- never read by decision.py/agent.py
                # itself, purely for SimpleDecisionDebugPanel. See session.py's
                # turn_tool_log/turn_retrieved_atoms for what populates them.
                "tool_calls": list(session.turn_tool_log),
                "retrieved_atoms_this_turn": list(session.turn_retrieved_atoms),
                "retrieval_query": session.retrieval_query,
            },
        }
