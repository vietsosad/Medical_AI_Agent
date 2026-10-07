# Safety Contract

## Emergency path

The deterministic reflex must run before network/model work. Preserve rule ID,
trigger reason, latency, ESI level, emergency guidance, and nurse queue handoff.
Normal RAG must not delay or override this path.

After a negative reflex result, `assess_contextual_emergency` is mandatory before
intent classification. Its structured DeepAgent model assessment may escalate a
combination of severe contextual signs, but it may never clear, lower, or delay a
deterministic red flag. The model does not select ESI or author patient guidance;
policy applies a conservative ESI 2 escalation pending clinician confirmation.
Timeout, invalid output, or provider failure must be audited as `UNAVAILABLE` and
must never fabricate a reassuring semantic result.

## Non-emergency proposal path

A persistable proposal requires:

- `patient_confirmed_intake=true`
- `decision_status=PROPOSED`
- ESI from 1 through 5
- non-empty SBAR
- non-empty citations
- production `SUFFICIENT/AUTHORIZED`, or explicit demo
  `CASE_EXAMPLE_SUPPORT/DEMO_ONLY`

## Output firewall

Do not expose chain-of-thought. Patient text may describe observed risk and
recommend professional assessment, but must not assert a diagnosis or prescribe
medication. The final verifier must operate on tool-produced text, never on free
model prose.

## HITL

Persist AI output as a proposal awaiting nurse review. Preserve approve,
override, escalation, handoff, optimistic versioning, and audit behavior in the
existing nurse APIs.

Confirmed cases that fail the evidence gate must also enter nurse review without
an AI ESI, SBAR, or citation. The patient must be told that validated information
is insufficient and that the case is waiting for nurse confirmation.
