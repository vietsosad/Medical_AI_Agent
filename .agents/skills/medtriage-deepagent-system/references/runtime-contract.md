# Runtime Contract

## Ownership

- FastAPI calls `get_deepagent_runtime()`.
- `MedTriageDeepAgentSupervisor` owns agent construction and hot session state.
- `chat_messages`, `triage_cases`, and nurse review records are durable.
- Hot state may be lost on restart and must be conservatively rebuilt from chat.

## Required turn order

1. `redflag_detector` before every LLM call.
2. `classify_request`.
3. `update_intake` for triage intents.
4. `retrieve_clinical_evidence` only after readiness and patient confirmation.
5. `reason_and_prepare_handoff` only after evidence authorization.
6. `verify_clinical_output` before returning a result.

Rejected, repeated, or out-of-order tools must not mutate clinical state.

## SSE compatibility

Emit `accepted`, mapped phase `progress`, `heartbeat`, optional `intent`, then
exactly one `result` or `error`. Keep historical phase names so frontend schemas
do not need a migration during the runtime switch.

## Degraded operation

If no tool-calling model exists, the package is unavailable, the agent errors,
or the final verification tool was skipped, execute the same gated tools
deterministically. Never use model prose as a fallback clinical answer.
