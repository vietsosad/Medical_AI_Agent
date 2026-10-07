/**
 * DTOs for the `simple_agent` pilot surface (`/api/v1/simple-triage/*`,
 * `src/api/routes_simple_triage.py`).
 *
 * Deliberately NOT the `ChatMessage`/`StructuredPayload` contract used by the
 * production `/triage` flow (see `@/types/triage-chat`) -- that contract has
 * required fields (`step`, `WorkflowPhase`, `DecisionStatus`, ...) that model
 * DeepAgent-runtime concepts (SBAR, HITL, red-flag, RAG citations) which
 * `simple_agent` does not produce. These types mirror the pilot route's
 * actual response shape one-to-one instead of forcing it into a bigger
 * contract it doesn't fill in honestly.
 */

import type { SimpleAgentSbarDTO, SimpleReviewStatus, SimpleSatisfiedRequirementDTO } from "./simple-nurse";

/** `src/simple_agent/agent.py`'s `_result()` "decision" dict, verbatim. */
export interface SimpleTriageDecisionDTO {
  route: "TRIAGE" | "CLARIFY" | "NON_CLINICAL" | "GUARDRAIL";
  action:
    | "ASK_NEXT"
    | "ASK_CONFIRMATION"
    | "ASK_CLARIFICATION"
    | "RESPOND"
    | "REFUSE"
    | "RETURN_MATCH"
    | "RETURN_INCOMPLETE";
  reason: string;
  subject_type: "SELF" | "OTHER_PERSON";
  subject_label: string | null;
  concepts: string[];
  retrieved_protocol_atoms: number;
  accepted_fact_ids: string[];
  qualitative_observation_ids: string[];
  asserted_concept_ids: string[];
  negated_concept_ids: string[];
  // Counts, not arrays -- src/simple_agent/agent.py's _result() sends
  // len(supported)/len(atom_missing), never the atom lists themselves.
  supported_protocol_atoms: number;
  unresolved_protocol_requirements: number;
  question_target_id: string | null;
  matched_esi_levels: number[];
  // Patient-facing (NOT debug-only): the specific protocol atom(s) that
  // fully supported a RETURN_MATCH outcome, so the UI can show which
  // criteria were matched instead of a bare ESI number. `criteria_text` is
  // the English clinical-register sentence protocol_atoms.jsonl's
  // `retrieval.text` already carries -- shown as-is, no translation (mock
  // corpus, same honesty standard as SBAR's citations). Empty on every
  // non-RETURN_MATCH turn, and absent on rows persisted before this field
  // existed.
  matched_atoms?: Array<{
    atom_id: string;
    decision_point: string | null;
    criteria_text: string | null;
    // Which specific requirement(s) the patient's own reported facts
    // satisfied, e.g. "Mức độ đau (>= 8): 9" -- see decision.py's
    // describe_satisfied_branch. Absent on rows persisted before this field
    // existed.
    satisfied_requirements?: SimpleSatisfiedRequirementDTO[];
  }>;
  // Debug-only, never used to drive any UI behavior -- see
  // chẩn đoán nội bộ. `tool_calls`: this turn's Phase A tool-call
  // trace (search_clinical_concepts/record_concept/record_fact/...), mirrors
  // `scripts/run_agent.py --debug`'s "TOOL x(...) -> {...}" lines.
  // `retrieved_atoms_this_turn`: this turn's Phase B semantic-retrieval
  // results with their raw cosine scores, so a borderline/noisy match is
  // visible without a one-off probe script against the corpus.
  tool_calls?: Array<{ tool: string; arguments: Record<string, unknown>; result: Record<string, unknown> }>;
  retrieved_atoms_this_turn?: Array<{ atom_id: string; score: number; confident_enough_to_ask: boolean }>;
  // The English clinical-register text Phase A produced (via finish_turn's
  // retrieval_query) and used as this turn's atom-retrieval search query --
  // replaces the old "concept labels + raw Vietnamese message" join. Null
  // before any concept is recorded, or on a stub understanding_fn (tests).
  retrieval_query?: string | null;
}

/** The `{"session_id", "message", "decision"}` shape returned by both
 * `POST /simple-triage/start` and `POST /simple-triage/chat/{id}`. */
export interface SimpleTriageTurnResponseDTO {
  session_id: string;
  message: string;
  decision: SimpleTriageDecisionDTO;
}

/** One row of `GET /simple-triage/sessions` / the summary half of
 * `GET /simple-triage/sessions/{id}`. */
export interface SimpleTriageSessionSummaryDTO {
  session_id: string;
  status: "ACTIVE" | "COMPLETED" | "ABANDONED";
  // The EHR profile card chosen at /start ("chọn thẻ của tôi"/"chọn thẻ
  // người thân"), or null for "ẩn danh/người mới". Carried through so the
  // UI can keep showing "đang khám cho ai" throughout the conversation --
  // see SimplePilotProfileSelector.tsx.
  profile_id: string | null;
  initial_message: string;
  turn_count: number;
  started_at: string;
  last_activity_at: string;
  completed_at: string | null;
  final_route: string | null;
  final_action: string | null;
  matched_esi_levels: number[];
  final_message: string | null;
  final_concepts: string[];
  // Nurse-review info, read-only join against SimpleAgentNurseReview (see
  // routes_simple_triage.py's `_review_info_by_session` -- this router never
  // writes to that table, only routes_nurse_simple.py does). `review_status`
  // is the raw WAITING_REVIEW/ASSIGNED/HANDED_OFF value; `is_overridden`/
  // `final_esi` and the decision fields are only meaningful once HANDED_OFF.
  // `review_display_status`
  // is the pre-collapsed 3-value form (mirrors production's `HitlReviewStatus`
  // minus the EMERGENCY_REJECTED case the pilot has no equivalent of) --
  // use this one for filtering/badges, not the raw `review_status`.
  review_status: SimpleReviewStatus | null;
  is_overridden: boolean;
  final_esi: number | null;
  decision_type: "CONFIRM_ESI" | "ADJUST_ESI" | null;
  decision_reason_code: string | null;
  decision_note: string | null;
  reviewer_name: string | null;
  reviewed_at: string | null;
  review_display_status: "APPROVED" | "OVERRIDDEN" | "PENDING_REVIEW";
  // Unread NURSE care-team replies -- lets the session list/sidebar show
  // "có tin mới" without the patient needing this exact session open (see
  // SimpleCareTeamDock, which only shows this while mounted on that page).
  unread_from_staff: number;
}

/** One row inside `GET /simple-triage/sessions/{id}`'s `messages` array. */
export interface SimpleTriageMessageRowDTO {
  turn_index: number;
  sender: "PATIENT" | "AGENT";
  content: string;
  route: string | null;
  action: string | null;
  question_target_id: string | null;
  // `{}` on PATIENT rows (nothing snapshotted there); the full Phase B
  // decision dict on AGENT rows -- dữ liệu chẩn đoán nội bộ, hiện không
  // the only consumer. Partial, not the full DTO: this is a raw debug dump
  // of whatever `decision.py` happened to produce, not a contract this app
  // depends on for behavior.
  decision_snapshot: Partial<SimpleTriageDecisionDTO>;
  created_at: string;
}

export interface SimpleTriageSessionDetailDTO extends SimpleTriageSessionSummaryDTO {
  messages: SimpleTriageMessageRowDTO[];
  // Patient-facing SBAR (see src/simple_agent/sbar.py's build_simple_agent_sbar),
  // computed at read-time only once the session is COMPLETED -- null before
  // that. Same 5-key shape as the nurse-side SBAR, reused directly rather
  // than duplicating the type.
  sbar: SimpleAgentSbarDTO | null;
}

/** The two terminal actions that close a simple-triage session -- mirrors
 * `_TERMINAL_ACTIONS` in `src/api/routes_simple_triage.py`. */
export const SIMPLE_TRIAGE_TERMINAL_ACTIONS = new Set([
  "RETURN_MATCH",
  "RETURN_INCOMPLETE",
]);
