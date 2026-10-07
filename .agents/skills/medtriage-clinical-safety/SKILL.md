---
name: medtriage-clinical-safety
description: Implement or audit MedTriage emergency reflex interception, diagnosis and prescribing suppression, ESI/SBAR authorization, patient confirmation, nurse HITL handoff, and safe degraded behavior. Use for any patient-facing clinical output or safety-critical agent/tool change.
---

# MedTriage Clinical Safety

Keep safety controls outside model discretion and verify every clinical output
before persistence or display.

## Mandatory controls

1. Run deterministic red-flag screening before DeepAgent or any other LLM.
2. Short-circuit emergencies to ESI 1/2 guidance and nurse handoff.
3. Require explicit patient confirmation before non-emergency reasoning.
4. Require authorized evidence or explicit demo-only support before ESI/SBAR.
5. Suppress diagnostic assertions and prescribing language.
6. Send proposals to nurse HITL; AI output is never the final clinical decision.
7. Fail closed on model timeout, invalid structure, missing citation, or gate skip.

Read [references/safety-contract.md](references/safety-contract.md) before
changing guardrails, reasoner output, SBAR generation, or proposal persistence.
