# REFACTOR PLAN — what was done, in what order, and what remains

Executed in the order the audit brief specifies (§30). Every phase ended by
re-running the golden live conversation suite against the real stack.

---

## Phase A — State ownership and memory correctness ✅

| Change | File | Why |
|---|---|---|
| Confirmation is durable conversation state, not a request field | `src/api/routes_patient.py` | F-01: the payload cleared it on every turn |
| `confirmation_lifecycle` becomes the single authority on whether a confirmation still holds | `src/agents/confirmation_lifecycle.py` (new) | three writers, no precedence |
| `TriageCase.conversation_control` JSON column + `persist_conversation_control` | `src/models/db_models.py`, `src/services/db.py`, `src/services/clinical_state_persistence.py` | F-09: question history and confirmation were hot-state only |
| Durable control is the baseline on a cold start; hot state overlays it | `src/api/routes_patient.py` | message replay cannot reconstruct asked-targets |
| `active_question` persisted alongside the loop state | `src/services/clinical_state_persistence.py`, `src/api/routes_patient.py` | F-07: a free-text adaptive question could not be rebuilt by replay |

## Phase B — Semantic question identity and answer binding ✅

| Change | File | Why |
|---|---|---|
| Tone-sensitive symptom surfaces checked against the patient's own spelling | `src/agents/nodes/fact_extraction.py` | F-03: "hồ sơ" was recorded as a cough |
| `"hoi"` reclassified from hedge to mild-intensity; hedge matching word-bounded | same | F-05: a stated complaint could never be satisfied |
| The open question survives the router's intent label | `src/agents/nodes/intake_analyzer.py` | **F-20**: the largest single source of repeated questions |
| A question's semantic target is carried through rendering and is what the answer binds to | `src/agents/nodes/question_engine.py`, `src/agents/nodes/intake_analyzer.py` | **F-22**: a symptom probe rendered on a legacy slot lost its identity |
| An anaphor inside a direct answer is not an unresolved reference | `src/agents/nodes/action_planner.py` | F-21: the agent interrupted its own question to ask what the patient meant |
| Repeats are marked `question_type: CLARIFICATION` and reworded | `src/agents/nodes/question_engine.py` | F-06 |
| A denial answering the associated-symptom slot is no longer stored as a symptom | `src/agents/nodes/intake_analyzer.py` | F-17 |

## Phase C — Multi-problem fact attribution ✅ (verified, no change needed)

`problem_state._resolve_attribute` already attributes a global observation to
the **primary** problem only, and entity-scoped observations to their own
problem. The live suite confirms it: in `S03` a severity given about the
headache never satisfied the nausea, and the dizziness raised at turn 3 joined
the problem list without resetting anything. No change was required; the
invariant is now covered by the golden suite rather than only by unit tests.

## Phase D — Adaptive planning and semantic stopping ✅

| Change | File | Why |
|---|---|---|
| Workflow gates no longer count toward the question budget | `src/agents/nodes/action_planner.py` | F-02: two EHR turns declared the case sufficient |
| Gates ordered structural → clinical → workflow | `src/agents/nodes/readiness_evaluator.py` | F-04: the EHR form was always the first question |
| An exhausted `chief_complaint` with a hedged symptom stops blocking | same | F-05: premature handoff |
| `evidence_question_budget` bounds the reasoner's post-confirmation questions | `src/config.py`, `src/agents/nodes/triage_reasoner.py`, `src/agents/deepagent_runtime/tools.py` | **F-18**: the reasoner walked its 32-target menu and never concluded |

## Phase E — Confirmation lifecycle ✅

| Change | File | Why |
|---|---|---|
| Adding a fact after confirmation does not invalidate it; correcting one does | `src/agents/confirmation_lifecycle.py` | §17 |
| The reasoner no longer cancels a confirmation to ask a question | `src/agents/nodes/triage_reasoner.py` | **F-14** |
| The review records the fact snapshot it was built for | `src/agents/nodes/patient_confirmation.py` | §16: one review per state version |

## Phase F — Retrieval, fusion and reasoning integration ✅

| Change | File | Why |
|---|---|---|
| The deterministic completion path can reach reasoning after model-run retrieval | `src/agents/deepagent_runtime/tools.py` | **F-13**: turns ended with no answer at all |
| The proposal is written to the patient in Vietnamese, second person | `src/agents/nodes/triage_reasoner.py` | F-19: an English third-person clinical note was shown to the patient |
| `evidence_question_budget` stops the reasoner walking its 32-target menu | `src/config.py`, `src/agents/nodes/triage_reasoner.py` | F-18: the case never concluded |
| Provider retries and a separate supervisor timeout | `src/config.py`, `src/services/llm_provider.py` | F-11 |
| Dead fallback model names corrected | `src/services/llm_provider.py` | F-12 |

**Retrieval itself was not touched.** No rebuild, no re-embedding, no label
change, no rollback of English normalisation. `esi_knowledge_documents` and
`mietic_cases` are byte-identical to the approved baseline.

## Phase G — API / SSE / frontend contract ✅ (verified, no change needed)

* `CaseSupportDTO` already carries presentation, symptom concepts, validated
  ESI, candidate levels, `labelStatus` and a relevance band (§22).
* The frontend already refuses to render a cosine score as a confidence and
  shows a relevance band instead (§23) — `EvidenceSources.tsx`.
* `UNKNOWN` label status stays `UNKNOWN`; candidate levels are shown as
  competing answers, never resolved into one.

---

## Not done, and why

| Item | Reason |
|---|---|
| Retiring the legacy `plan_next_question` ladder (H-15) | It is still the fallback for every non-adaptive target, including the reasoner's `evidence_requested_fact`. Replacing it is a larger change than this audit should make in one pass; the wording defect it caused (unnamed "triệu chứng này") is fixed. |
| Retiring `clinical_requirements.PROFILES` on the degraded path (H-05) | It is the deterministic fallback when the model is unavailable. Removing it would leave the degraded path with no requirement policy at all. |
| Recalibrating the semantic emergency detector (F-08) | §34 forbids weakening a safety invariant. This is a clinical calibration decision, not an engineering one. |
| Invocation-time provider failover (F-12) | The `try/except` chain only validates a model at construction, so a dead model name still reaches the runtime. Fixing it means a health probe or a first-call failover, which changes startup behaviour. |

## Suggested next work, in priority order

1. **Cut supervisor cost and latency** (F-10). Five `gpt-4o` calls and ~15k
   input tokens per turn to emit tool names; the deterministic completion path
   already produces the same tool order. Consider a smaller orchestration model
   or skipping orchestration entirely for turns with only one legal next tool.
2. **Invocation-time provider failover** (F-12).
3. **Retire the legacy slot ladder** (H-15) once every reasoner target has an
   adaptive rendering.
