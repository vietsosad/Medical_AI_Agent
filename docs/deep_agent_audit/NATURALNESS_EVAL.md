# NATURALNESS EVALUATION — how the conversation reads

*Deterministic metrics decide whether the agent is **correct**. This decides
whether it is **bearable to talk to**, which is a different question and is
scored separately (§26).*

---

## Method

* **Judge:** `gpt-4o`, temperature 0, one call per conversation.
* **Blind in the ways that matter.** The judge is given only the
  patient-visible transcript — the patient's utterances, the agent's replies,
  and a marker where the confirmation review was displayed. It is not told
  which run it is reading (before or after a fix), and it never sees a planner
  target, a canonical fact, a stop reason, a question count or an ESI.
* **Explicitly not a clinical authority.** The prompt states that it is not
  evaluating medicine, priority level or diagnosis. Its score is a UX signal
  and appears alongside the deterministic metrics, never instead of them.
* **Raw transcripts preserved.** Every conversation the judge scored is kept
  verbatim in `eval/conversations/`, so any score can be re-examined against
  what actually happened.
* **Structured output.** The judge returns one JSON object: ten 1–5 criterion
  scores, an overall mean, and one sentence naming the worst problem in that
  conversation. Unparseable output is recorded as an error, never silently
  dropped.

Implementation: `eval/live_audit/judge.py`, run via
`eval/live_audit/run_evaluation.py --judge`.

## Rubric

| Criterion | What a 5 looks like |
|---|---|
| `relevance` | every question follows from what the patient just said |
| `context_retention` | the agent uses what it was already told |
| `no_unnecessary_repetition` | nothing already answered is asked again |
| `question_coherence` | the sequence has a thread; it does not jump |
| `appropriate_acknowledgement` | new information is acknowledged naturally, not robotically |
| `adaptive_symptom_handling` | a symptom raised mid-conversation is folded in without restarting |
| `conciseness` | short, human, no boilerplate |
| `natural_progression` | the conversation visibly moves toward a conclusion |
| `premature_form_avoidance` | the review appears when there is something to review, once |
| `premature_handoff_avoidance` | a clinician is not invoked to escape a hard turn |

## Results

See `LIVE_E2E_RESULTS.md` § *Naturalness* for the scored table, the per-criterion
means before and after, and the judge's own worst-problem sentence for each
conversation — including the ones that scored badly.

## Limits of this signal

* One judge, one model, one temperature. It is not a panel and it is not a
  human evaluation.
* An LLM judge rewards fluent text. A conversation can read well and still be
  clinically wrong, which is exactly why the deterministic metrics are primary.
* Scores are comparable within this audit (same prompt, same judge, same rubric)
  and should not be compared against numbers produced any other way.
