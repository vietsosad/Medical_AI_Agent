# Routing Contract

## Turn terminal states

- Scope response: `decision_status=NOT_APPLICABLE`, `next_step=complete`.
- Clarification: `decision_status=NEEDS_CLARIFICATION`,
  `next_step=wait_for_patient`.
- Intake review: `decision_status=AWAITING_PATIENT_CONFIRMATION` and wait.
- Ready: `patient_confirmed_intake=true`, `next_step=retrieve_evidence`.
- Emergency: short-circuit to handoff without normal intake.

## Fact policy

- Do not convert missing values to normal/negative findings.
- Keep patient-reported vitals labelled with source and measurement time.
- Do not silently overwrite a conflicting confirmed fact.
- Do not use stale EHR facts until confirmed in the current session.
- A patient correction is case context and must not silently overwrite EHR.

## Question policy

Ask one question per turn. Use choices for bounded values such as onset, scale,
vitals availability, and EHR confirmation. Use free text for chief complaint,
procedure details, corrections, and contradiction resolution.
