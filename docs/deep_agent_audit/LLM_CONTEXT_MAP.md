# LLM CONTEXT MAP — what each model actually receives

*§6 of the audit brief: trace every LLM invocation and state exactly what the
model is given. Nothing here is inferred from design intent; each row was read
off the code that builds the prompt and confirmed against live captures
(`eval/conversations/_llm_context_capture.json`, produced by
`eval/live_audit/capture_context.py`).*

**No chain of thought is logged anywhere.** Only prompt inputs, token counts and
structured outputs are recorded, and the only patient text involved in this
audit is synthetic.

---

## Legend

✅ present · ❌ absent · ➖ not applicable

| Context | supervisor | contextual&nbsp;emergency | intent&nbsp;router | query&nbsp;planner | reranker | reasoner |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| full conversation history | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| last N patient messages | ❌ | ✅ (last 3) | ❌ | ❌ | ❌ | ❌ |
| latest patient message | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| canonical patient state | ❌ | ❌ | ❌ | ✅ (grounded facts) | ❌ | ✅ (`to_reasoner_payload`) |
| ProblemState | ❌ | ❌ | ❌ | ✅ | ➖ | ❌ (via canonical view) |
| current question target | ❌ | ✅ (`active_question`) | ✅ | ❌ | ❌ | ❌ |
| questions already asked | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (`asked_targets` + counts) |
| resolved / closed targets | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (`resolved_targets`, "never re-ask") |
| negative findings | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ (`explicitly_denied_symptoms`) |
| confirmation state | ❌ | ❌ | ❌ | ❌ | ❌ | ➖ (gate runs before the call) |
| retrieval evidence | ❌ | ❌ | ❌ | ➖ | ✅ (case text only) | ✅ (with provenance) |
| EHR / verified profile | ❌ | ❌ | ❌ | ✅ (age band, sex) | ❌ | ✅ (only if confirmed) |
| vitals | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ + `vital_signs_status` |
| tool results this turn | ✅ | ➖ | ➖ | ➖ | ➖ | ➖ |

---

## 1. Supervisor — `deepagent_runtime/supervisor.py`

**Model:** `gpt-4o`, temperature 0. **Calls per turn:** 5 observed.
**Input:** ~3.0–3.3 k tokens per step. **Output:** 11–48 tokens (a tool call).

Receives: `SUPERVISOR_PROMPT`, one fixed user instruction
(*"Advance the active MedTriage turn using only the permitted clinical
tools"*), the six tool schemas, the four runtime skill files, and — growing with
each step — the results of the tools it has already called. Those results are
deliberately tiny:

```json
{"status": "OK", "decision_status": "...", "workflow_phase": "...",
 "next_step": "...", "allowed_next_tools": ["..."]}
```

> **The supervisor never sees a patient message, a symptom, a fact or an
> evidence document.** It is a routing model over a state machine, and the
> `allowed_next_tools` field usually leaves it exactly one legal move.

That is the right safety design — a model that cannot see clinical content
cannot invent it — and it is also why F-10 (five `gpt-4o` calls per turn to
choose a forced move) is pure overhead.

**It cannot be why the agent seems to forget a question**: it never knew one.

## 2. Contextual emergency detector — `nodes/contextual_emergency_detector.py`

**Model:** `gpt-4o` (`get_deepagent_llm`), structured output. **1 call/turn**,
~0.65 k input tokens.

```json
{"latest_patient_message": "...",          // truncated at 2000 chars
 "recent_patient_messages": ["...", ...],  // last 3 patient turns, ≤500 chars each
 "active_question": {...},
 "safety_screen_candidate": "..."}         // only when the fast screen matched
```

No canonical state, no problem list, no evidence. Its output can escalate but
cannot clear a deterministic reflex lock.

## 3. Intent router — `nodes/intent_classifier.py`

**Model:** `gpt-4o-mini`, structured. **Conditional** — only when the
deterministic pass returns `UNCLEAR` and `intent_llm_fallback_enabled`. 3 calls
across the entire 24-scenario baseline.

Receives **only the latest message**, JSON-encoded. No history, no state.

> This is where the "forgetting" actually began. The *deterministic* classifier
> does see `active_question`, and returns `TRIAGE_NEW_SYMPTOM` for any reply
> carrying a symptom word (`new_symptom_during_unrelated_follow_up`).
> `intake_analyzer` then discarded the open question on that label — see
> **F-20**. Fixed: the open question now survives the intent label.

## 4. Retrieval query planner — `services/rag/clinical_query_planner.py`

**Model:** `gpt-4o-mini`. System prompt + `grounded_facts` JSON only.

The model may only **rephrase** facts already extracted from canonical state;
`validate_grounding` rejects any query that mentions a concept outside the
allowed vocabulary, and the deterministic baseline is returned unchanged on any
failure, timeout or violation.

## 5. Case reranker — `services/rag/hybrid_retrieval.py`

**Model:** `gpt-4o-mini`. `{patient_presentation, cases:[{id, presentation}]}`.

Never shown an ESI level, and can only reorder or suppress candidates the
retrieval channels already returned.

## 6. Clinical reasoner — `nodes/triage_reasoner.py`

**Model:** `gpt-4o` (`get_resilient_llm("large")`), structured
`TriageEvaluation`. **1–2 calls** per reasoning turn (one bounded regrounding
retry). ~2.8 k input tokens.

The only call that receives the clinical picture:

* `ClinicalStateView.to_reasoner_payload()` — present, denied, historical and
  not-asked symptoms kept distinct, with an explicit instruction that
  *not asked ≠ absent*;
* the blueprint read-model;
* verified EHR facts **only when the patient confirmed the record**, plus a
  note saying so;
* patient-reported vitals and `vital_signs_status`, with
  *"missing vitals must not be read as normal"*;
* unresolved contradictions;
* **`asked_targets` with counts** and **`resolved_targets`** ("never ask these
  again");
* the retrieval evidence with citation ids, protocol codes, sections, criteria,
  decision points and facets;
* since this audit: the remaining evidence-question budget, and the
  instruction to answer the patient **in Vietnamese, second person** (F-19).

---

## Why the agent looked like it forgot

Three separate mechanisms, none of them "the model lost context":

1. **F-20** — the open question was thrown away before extraction whenever the
   router labelled the turn a new symptom, so a clear answer bound to nothing.
2. **F-01 / F-14** — the confirmation was cleared by the transport and by the
   reasoner, so the conversation restarted at the checkpoint it had passed.
3. **F-13** — a turn could end with no reasoning at all, and the previous
   message was re-sent verbatim.

The models were given consistent context throughout. What was inconsistent was
the state around them.
