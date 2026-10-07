# Evidence Contract

## Production authority

Production ESI requires all of the following:

- `document_type=validated_protocol`
- `validation_status=approved`
- `authority_status=AUTHORIZED`
- complete provenance metadata and stable citation ID
- clinical scope match
- at least one matched decision criterion
- approved calibration profile and enough passing retrieval channels

`triageknowledgebase` contains legacy MIETIC case examples. It may support an
explicit demo mode only as `document_type=case_example`,
`authority_status=DEMO_ONLY`, and `evidence_status=CASE_EXAMPLE_SUPPORT`.
Never relabel it as a validated protocol.

## Current database limitation

The restored database has `triageknowledgebase` but not
`triage_protocol_documents` or `triage_case_examples`. Keep production evidence
fail-closed until validated protocols are ingested, calibrated, and approved.

## Citation policy

Reasoner citation IDs and matched criteria must be subsets of the artifacts
accepted by the evidence gate. The final verifier must clear ESI and SBAR when
that linkage is absent.

## Insufficient evidence handoff

After the patient has confirmed intake, insufficient or unauthorized evidence
must clear ESI, SBAR, and citations, set `decision_status=INSUFFICIENT_EVIDENCE`,
and move the case to the nurse HITL queue. Patient output must state that there
is not enough validated information for safe AI triage and that the case is
waiting for nurse confirmation. Use `workflow_phase=HANDOFF`; never present the
handoff as a completed AI decision.
