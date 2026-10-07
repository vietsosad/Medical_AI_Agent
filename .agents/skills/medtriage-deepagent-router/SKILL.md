---
name: medtriage-deepagent-router
description: Implement or audit MedTriage intent classification, answer alignment, intake extraction, contradiction handling, readiness evaluation, clarification questions, patient confirmation, and allowed-next-tool routing. Use when changing adaptive triage conversation behavior or router specialist instructions.
---

# MedTriage DeepAgent Router

Advance one patient turn with explicit prerequisites and one highest-value next
question. Keep common routing deterministic; use the agent to choose among
authorized capabilities, not to invent clinical facts.

## Procedure

1. Classify greeting, scope, new symptom, or follow-up after safety preflight.
2. Validate whether the utterance answers the active structured question.
3. Extract only explicit facts and preserve provenance.
4. Surface contradictions before readiness or retrieval.
5. Ask one clarification when required fields remain.
6. Require the patient to confirm the reviewable intake summary.
7. Permit retrieval only when readiness is complete and confirmation is true.

Read [references/routing-contract.md](references/routing-contract.md) before
changing tool prerequisites or conversation terminal states.
