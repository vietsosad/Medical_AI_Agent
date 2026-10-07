# STATE OWNERSHIP — where each fact really lives

*Question this answers: for every piece of conversational state, which layer is
the source of truth, and is there more than one?*

---

## 1. Ownership table (as audited)

| State | Source of truth | Durable? | Competing writers found |
|---|---|---|---|
| Patient facts (symptoms, onset, severity, vitals, negations) | `CanonicalPatientState` (`canonical_state`) | ✅ `TriageCase.canonical_state` | none — `clinical_blueprint` is a derived read-model |
| Negative findings | same (`status=NEGATED` observation) | ✅ | none |
| Problem list | derived: `build_problem_state(ClinicalStateView)` | ❌ derived per turn | none |
| Question plan / open targets | derived: `plan_from_agent_state` | ❌ derived per turn | none |
| Question history (`asked_targets`) | `action_loop_state` in hot runtime state | ❌ **hot only** | none, but lost on restart |
| Resolved / accepted-unknown targets | `action_loop_state.accepted_unknown_targets` | ❌ **hot only** | none, but lost on restart |
| Current question (`active_question`) | hot state, **plus** request-time re-injection, **plus** message replay | ❌ | ⚠️ **three writers** |
| Confirmation (`patient_confirmed_intake`) | request payload → hot state | ❌ | 🔴 **three competing writers** |
| Red-flag lifecycle | `red_flag_status` in state, mirrored to `TriageCase` | ✅ | none (mirror is derived) |
| Conversation memory | `ConversationMemory` → `TriageCase.conversation_memory` | ✅ | none |
| Retrieval attempts / refinement | turn-local `TurnContext` state | ❌ turn-scoped by design | none |
| EHR confirmation status | hot state + `EHRProfile.updated_at` freshness check | ❌ | acceptable (freshness re-derives) |

## 2. 🔴 The confirmation conflict (root cause of F-01)

`patient_confirmed_intake` had **three** writers with no precedence rule:

1. **Request payload** — `routes_patient.submit_chat_turn` wrote
   `"patient_confirmed_intake": payload.confirm_intake` into `ai_state` on
   *every* turn. Because `DeepAgentSessionStore.prepare_turn` deep-merges the
   incoming dict over stored state, any ordinary message **cleared** a
   confirmation the patient had already given.
2. **Runtime hot state** — the value the previous turn actually concluded.
3. **Message replay** — `recover_triage_state(...).awaiting_confirmation`, used
   on the first interaction after a cold start.

Observed consequence (live, every non-emergency scenario in the baseline):

```
patient presses confirm            → confirmed=True  → retrieval + reasoning run
reasoner asks one more question    → agent asks it
patient answers the question       → confirmed=False (payload overwrite)
readiness: ready & not confirmed   → confirmation review shown again
patient presses confirm            → ... loop
```

Terminal outcome `STUCK_ON_CONFIRMATION` in **10 of 24** baseline scenarios and
`normal_case_finalized_rate = 0.0`.

**Fix applied (Phase A):** the request payload may only *raise* confirmation,
never clear it. Invalidation became an explicit, reasoned decision owned by the
confirmation lifecycle (Phase E), and the flag is now persisted on the case so
it survives a restart.

## 3. `active_question` — three writers, one legitimate

`active_question` is written by the question engine (owner), re-injected by the
API from hot state, and reconstructed from `ChatMessage.structured_options` by
`recover_triage_state`. The last two are *recovery* paths, not independent
opinions, and the API prefers hot state. This is acceptable, but the recovery
path can only rebuild questions that carried a structured payload — a free-text
adaptive question (`headache.course`) is **not** recoverable after a restart.
Recorded as F-07.

## 4. Hot-only state and what a restart loses

`action_loop_state` (asked targets, repeat counts, accepted-unknown targets,
consecutive-question budget) exists only in process memory. After a restart the
agent can legitimately re-ask a question it had already put to the patient,
because the evidence that it asked is gone. Canonical facts survive, so a
question whose *answer* was recorded is still suppressed; a question the patient
declined or dodged is not.

Live evidence: `S23_session_reload` (`eval/conversations/`).
