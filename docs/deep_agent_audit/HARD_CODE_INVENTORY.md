# HARD-CODE INVENTORY

Every hard-coded table, ordering, budget and template that influences the
conversation, classified so that a safety invariant is never mistaken for a
questionnaire and vice versa.

Classes used:

| Class | Meaning | May it decide the conversation path? |
|---|---|---|
| `SAFETY_INVARIANT` | Prevents a time-critical miss or an ungrounded claim | **must not be removed** |
| `STATE_INVARIANT` | Keeps state consistent/attributable | must not be removed |
| `ONTOLOGY_HINT` | Vocabulary: what *could* be worth knowing | hint only |
| `QUESTION_RENDERING` | Wording of a question already selected | rendering only |
| `ORCHESTRATION_HARD_CODE` | Fixed ordering/budget in the runtime | bounded control only |

---

## 1. Inventory

| # | Item | Location | Class | Verdict |
|---|---|---|---|---|
| H-01 | `PROBLEM_PROFILES` (19 concepts × relevant facts + importance) | `src/agents/problem_state.py` | `ONTOLOGY_HINT` | ✅ correct role. It supplies *candidate* attributes and their importance; ranking, stopping and selection live in `question_planning`. It does **not** enforce "complaint X → always ask A,B,C,D". |
| H-02 | `_PAIN_CHARACTERISATION` / `_GENERIC_CHARACTERISATION` bases | same | `ONTOLOGY_HINT` | ✅ shared vocabulary, not an order |
| H-03 | `_GLOBAL_ATTRIBUTE_KEYS` | same | `STATE_INVARIANT` | ✅ this is the multi-problem attribution rule (§12) |
| H-04 | `VITAL_ATTRIBUTE_KEYS` | same | `ONTOLOGY_HINT` | ✅ |
| H-05 | `REQUIREMENT PROFILES` (`PROFILES`, chest_pain/dyspnea/fever/standard) | `src/agents/clinical_requirements.py` | `ONTOLOGY_HINT` (declared `PENDING_CLINICAL_REVIEW`) | ⚠️ **still a questionnaire on the degraded path.** `evaluate_readiness` (full profile evaluator) is non-blocking on the DeepAgent path but is the deterministic fallback, where it *does* impose a fixed required-field list. |
| H-06 | `evaluate_pre_retrieval_readiness` structural gates (complaint, contradictions, EHR workflow) | `readiness_evaluator.py` | `STATE_INVARIANT` | ✅ genuinely structural: retrieval cannot build a query without a complaint |
| H-07 | `_IMPORTANCE_GAIN`, `_PRIMARY_BONUS`, `_NEW_PROBLEM_BONUS`, `_UNCHARACTERISED_SAFETY_PENALTY` | `question_planning.py` | `ORCHESTRATION_HARD_CODE` | ✅ tie-breaking weights, explicitly not clinical ranking |
| H-08 | `DEFAULT_MAX_CONSECUTIVE_QUESTIONS = 8` / `adaptive_max_consecutive_questions` | `question_planning.py`, `config.py` | `ORCHESTRATION_HARD_CODE` | ✅ circuit breaker; records `QUESTION_BUDGET_EXHAUSTED` when it fires |
| H-09 | `NO_INFORMATION_GAIN` breaker (2 consecutive no-gain turns) | `question_planning.plan_questions` | `ORCHESTRATION_HARD_CODE` | 🔴 **fired on workflow turns and caused premature confirmation in 100% of baseline scenarios** (F-02). Fixed. |
| H-10 | `MAX_REPEATS_PER_TARGET = 2`, `MAX_ACTIONS_PER_TURN = 8` | `next_best_action.py` | `ORCHESTRATION_HARD_CODE` | ✅ bounded, but see F-05: exhausting `chief_complaint` produced a handoff |
| H-11 | `_INFORMATION_GAIN` static six-slot table | `next_best_action.py` | `ORCHESTRATION_HARD_CODE` | ✅ only used when the adaptive planner supplied no gain |
| H-12 | `SAFETY_PRECEDENCE` ordering | `next_best_action.py` | `SAFETY_INVARIANT` | ✅ keep |
| H-13 | `_HANDLERS` closed dispatch table | `action_execution.py` | `SAFETY_INVARIANT` | ✅ keep |
| H-14 | `_ATTRIBUTE_QUESTIONS`, `_VITAL_QUESTIONS` templates | `adaptive_questions.py` | `QUESTION_RENDERING` | ✅ |
| H-15 | Legacy fixed question ladder in `plan_next_question` (complaint → onset → severity → associated → vitals → EHR) | `question_engine.py` | `ORCHESTRATION_HARD_CODE` | 🔴 **still acts as a questionnaire engine** whenever the selected target is a legacy slot — which is exactly what the post-confirmation reasoner path produces (F-04). |
| H-16 | `SYMPTOM_LEXICON` + `_DISQUALIFYING_FOLLOWERS` + `_HEDGE_MARKERS` | `fact_extraction.py` | `ONTOLOGY_HINT` | 🔴 two live defects: accent-folding collisions (F-03) and `"hoi"` treated as epistemic hedging (F-05). Fixed. |
| H-17 | Deterministic red-flag rules | `redflag_detector.py` / config | `SAFETY_INVARIANT` | ✅ keep, unchanged (0.04 ms observed) |
| H-18 | Output firewall in `verify_clinical_output` (citation subset, confirmation, criterion linkage) | `deepagent_runtime/tools.py` | `SAFETY_INVARIANT` | ✅ keep, unchanged |
| H-19 | Bounded retrieval refinement (`RAG_REFINEMENT_ATTEMPTS_HARD_MAX = 3`, signature/fingerprint progress checks) | `config.py`, `tools.py` | `ORCHESTRATION_HARD_CODE` | ✅ keep |
| H-20 | `case_support_min_relevance = 0.30`, `case_support_max_shown = 3` | `config.py` | `ORCHESTRATION_HARD_CODE` | ✅ calibrated against `eval/retrieval_ledger.json` |
| H-21 | EHR confirmation gate (`clinical_memory_confirmation`) blocking readiness | `readiness_evaluator.py` | `ORCHESTRATION_HARD_CODE` (workflow) | 🔴 consumed the first two turns of every conversation and poisoned the information-gain breaker (F-02). Reclassified as non-blocking-for-questioning. |

## 2. What was NOT touched

Per §20 and §34, none of the following was modified by this audit:

* the two active RAG tables (`esi_knowledge_documents`, `mietic_cases`) — no
  rebuild, no re-embed, no label change;
* the embedding model or retrieval foundation;
* deterministic red-flag rules and their monotonicity;
* the clinical authority boundary and citation firewall;
* SBAR commit/publication ordering;
* the final verifier.

## 3. Verdict on §10/§11

`PROBLEM_PROFILES` is already a hint layer, not a questionnaire engine: the live
transcripts show question selection driven by `question_planning` over problem
state, with per-target information gain, not by a per-complaint fixed list.

The **residual questionnaire** in the system is not `PROBLEM_PROFILES` — it is
H-15, the legacy `plan_next_question` ladder, which the post-confirmation
reasoner path re-enters (F-04), plus H-05 on the degraded path.
