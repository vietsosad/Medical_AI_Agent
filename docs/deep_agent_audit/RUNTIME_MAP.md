# RUNTIME MAP — what actually runs on one patient turn

*Derived from the live audit, not from design documents. Every claim here was
observed in a real turn against the local PostgreSQL database, the real
retrieval corpus and the real OpenAI provider.*

Sources: `src/api/routes_patient.py`, `src/agents/deepagent_runtime/*`,
`src/agents/nodes/*`. Live evidence: `eval/conversations/`.

---

## 1. Entry points

| Route | Handler | Shape |
|---|---|---|
| `POST /api/v1/triage/start` | `start_triage_session` | blocking, returns first agent message |
| `POST /api/v1/triage/chat/{session_id}` | `submit_chat_turn` | **SSE stream**, `accepted` → `progress`* → `intent` → `result`/`error` |
| `GET /api/v1/triage/chat/{session_id}/messages` | `get_session_messages` | replay + reconstructed question payload |

Both mutating routes require `PatientUserDep` (JWT bearer → `get_current_user`
→ `get_current_patient`). The audit overrides those two dependencies **inside
the harness process only** — see `AUTH.md` section of `LIVE_E2E_RESULTS.md`.

## 2. Turn pipeline (observed)

```
submit_chat_turn
 ├─ ownership check (TriageCase.patient_id == current_user.id)
 ├─ status gates (RED_FLAG_LOCKED / COMPLETED reject with 400)
 ├─ persist PATIENT ChatMessage  (durable, before the agent runs)
 ├─ build `ai_state` from: request payload + hot runtime state + EHRProfile
 │                          + (first interaction only) message-replay recovery
 └─ MedTriageDeepAgentSupervisor.stream_turn(ai_state, session_id)
     └─ DeepAgentSessionStore.serialize_turn(session_id)   # per-session lock
        ├─ prepare_turn: deep-merge incoming over stored hot state
        └─ _execute_context(TurnContext(state))
            ├─ run_reflex_screen        → redflag_detector           [deterministic, no LLM]
            ├─ if reflex locked/candidate → run_remaining_required_tools (bounded)
            └─ else DEEPAGENT mode:
               agent.ainvoke(...)       → supervisor LLM picks tools
               then run_remaining_required_tools(...) completes anything skipped
```

### Tool-gated phases

| Tool | Nodes it runs | LLM? |
|---|---|---|
| `assess_contextual_emergency` | `contextual_emergency_detector` (+`summary_creator` on escalate) | **yes** (`get_deepagent_llm`, structured) |
| `classify_request` | `intent_classifier` (+`scope_responder`) | **conditional** (`get_resilient_llm("small")`, only when the deterministic pass fails) |
| `update_intake` | `answer_validator` → `intake_analyzer` → *monitored-concern re-test* → `contradiction_detector` → `readiness_evaluator` → `action_planner` → `action_execution` | **no** (fully deterministic) |
| `retrieve_clinical_evidence` | `profile_context_enricher` → `bilingual_query_builder` → `retrieve_evidence` | **yes** (query planner, reranker) |
| `reason_and_prepare_handoff` | `triage_reasoner` (+ bounded `refine_evidence` loop, + `summary_creator`) | **yes** (`get_resilient_llm("large")`) |
| `verify_clinical_output` | output firewall + `conversation_memory` | **no** |

`run_remaining_required_tools` guarantees every turn completes the mandatory
phases even when the supervisor model skips, repeats or misorders tools. In the
audit the supervisor **did** drive its own turns (`execution_mode: DEEPAGENT`,
`model_selected_tools` populated) — the deterministic completion path was a
backstop, not the norm.

## 3. Observed cost and latency per turn

Measured over the baseline suite (`gpt-4o` supervisor, `gpt-4o` contextual
emergency detector):

| Item | Observed |
|---|---|
| Supervisor LLM calls per turn | **5** (one per tool step; ~3.0–3.3k input tokens each, 11–48 output tokens) |
| Contextual emergency LLM calls per turn | 1 (~0.65k input) |
| Typical wall-clock per turn | 6–8 s |
| Typical cost per non-retrieval turn | ~$0.04–0.05 |

The supervisor re-sends the whole system prompt plus the accumulated tool
transcript on every step, so orchestration dominates spend while producing only
a tool name. This is an efficiency finding, not a correctness one — see
`FAILURE_MATRIX.md` F-10.

## 4. Concurrency and state isolation

* `DeepAgentSessionStore` holds **hot state in process memory only**, keyed by
  `session_id`, with a per-session `asyncio.Lock`.
* Durable state lives on `TriageCase` (`canonical_state`,
  `canonical_state_version`, `conversation_memory`, red-flag lifecycle) and in
  `ChatMessage` rows.
* A cold process rebuilds a session from `TriageCase.canonical_state` when
  present, otherwise by replaying `ChatMessage` through
  `recover_triage_state`.

The audit ran 4 conversations concurrently against one process with no
cross-session leakage observed.

## 5. Retrieval path (live)

```
canonical_state → problem_state → clinical_query_planner (deterministic + LLM)
  → bilingual_query_builder (vi / en / sparse terms)
  → knowledge_retriever.search_esi_authority_hybrid   [esi_knowledge_documents, pgvector]
  → hybrid_retrieval.fuse (RRF) → llm_rerank → apply_relevance_floor
  → evidence_gate (authority status, scope, calibration)
  → triage_reasoner (criterion linkage) → verify_clinical_output (citation firewall)
```

`mietic_cases` is queried only as **case support** and is quarantined from
authority: it can never satisfy the evidence gate or supply an ESI.
