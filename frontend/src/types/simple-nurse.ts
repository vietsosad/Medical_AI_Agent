/**
 * DTOs for the `simple_agent` nurse-review pilot (`/api/v1/nurse-simple/*`,
 * `src/api/routes_nurse_simple.py`).
 *
 * Deliberately separate from `@/types/clinical-hitl` (the real
 * `NurseQueueItemDTO`/`NurseCaseDetailDTO` contract): this pilot has no
 * red-flag, specialist-review, PII-access, or EHR risk_context concept, and
 * "citations" here are every protocol atom referenced during the session
 * (`seen_atom_ids`), not a proven-matched subset -- see
 * `.claude/plans/sunny-launching-mitten.md`.
 */

export type SimpleReviewStatus = "WAITING_REVIEW" | "ASSIGNED" | "TRIAGE_DECIDED" | "HANDED_OFF" | "PARKED";

export type SimpleDecisionType = "CONFIRM_ESI" | "ADJUST_ESI";

export type SimpleReasonCode =
  | "MATCHES_PROTOCOL"
  | "ADDITIONAL_CLINICAL_JUDGMENT"
  | "INSUFFICIENT_PATIENT_DATA"
  | "OTHER";

export type SimpleNurseQueueBucket = "QUEUE" | "PARKED" | "DECIDED";

/**
 * `GET /nurse-simple/dashboard` -- số liệu tổng quan của trạm điều phối.
 *
 * Mọi trường ở đây là phép ĐẾM trực tiếp trên dữ liệu ca, không phải chỉ số
 * ước lượng; xem đầu `src/services/simple_nurse_dashboard.py`. Giao diện có
 * nghĩa vụ giữ nguyên cách gọi tên: `agreement` là "điều dưỡng đã làm gì với
 * đề xuất của AI", KHÔNG phải độ chính xác của AI.
 */
export interface SimpleEsiBucketDTO {
  /** null = agent kết luận chưa đủ dữ liệu để đề xuất mức nào. */
  level: 1 | 2 | 3 | 4 | 5 | null;
  count: number;
}

export type SimpleWaitBucketKey = "UNDER_WARNING" | "WARNING" | "CRITICAL";

export interface SimpleWaitBucketDTO {
  key: SimpleWaitBucketKey;
  count: number;
}

export interface SimpleAgreementDTO {
  decided_total: number;
  confirmed: number;
  /** Điều dưỡng chốt ở mức KHẨN HƠN mức AI đề xuất. */
  escalated: number;
  /** Điều dưỡng chốt ở mức ÍT KHẨN HƠN mức AI đề xuất. */
  de_escalated: number;
  adjusted_without_proposal: number;
}

export interface SimpleReasonCountDTO {
  code: string;
  count: number;
}

export interface SimpleDailyPointDTO {
  date: string;
  completed: number;
  decided: number;
}

export interface SimpleNurseDashboardDTO {
  generated_at: string;
  waiting: number;
  assigned_total: number;
  assigned_to_me: number;
  parked: number;
  decided: number;
  insufficient_live: number;
  longest_wait_minutes: number | null;
  esi_distribution: SimpleEsiBucketDTO[];
  wait_buckets: SimpleWaitBucketDTO[];
  agreement: SimpleAgreementDTO;
  reason_codes: SimpleReasonCountDTO[];
  daily_volume: SimpleDailyPointDTO[];
}

/** `GET /nurse-simple/queue` query params -- see routes_nurse_simple.py's
 * `get_simple_nurse_queue` for the exact filter/sort/pagination semantics. */
export interface SimpleNurseQueueParams {
  bucket?: SimpleNurseQueueBucket;
  mineOnly?: boolean;
  q?: string;
  patientEmail?: string;
  esiLevels?: number[];
  page?: number;
  pageSize?: number;
}

/** `routes_nurse_simple.py`'s `describe_satisfied_branch` output shape --
 * shared by `SimpleAgentCitationDTO` here and `matched_atoms` in
 * `@/types/simple-triage` (both come from the same backend function). */
export interface SimpleSatisfiedRequirementDTO {
  fact_target_id: string;
  name: string;
  operator: "EQ" | "NEQ" | "GT" | "GTE" | "LT" | "LTE";
  expected_value: string | number | boolean | null;
  actual_value: string | number | boolean | null;
}

export type SimpleSessionStatus = "ACTIVE" | "COMPLETED" | "ABANDONED";

export interface SimpleNurseQueueItemDTO {
  session_id: string;
  initial_message: string;
  final_action: "RETURN_MATCH" | "RETURN_INCOMPLETE" | null;
  ai_proposed_esi: 1 | 2 | 3 | 4 | 5 | null;
  is_insufficient: boolean;
  // "Cần xem ngay" from the pre-LLM emergency screen -- a reason, not an ESI.
  // A flagged case can be ACTIVE: the patient may still be talking.
  session_status?: SimpleSessionStatus;
  attention_required?: boolean;
  attention_reason?: string | null;
  attention_raised_at?: string | null;
  turn_count: number;
  waiting_since: string;
  review_status: SimpleReviewStatus;
  assigned_nurse_id: string | null;
  case_version: number;
  unread_count: number;
  patient_email: string | null;
  patient_name: string | null;
  // DECIDED-bucket display.
  final_esi: number | null;
  decision_type: SimpleDecisionType | null;
  decision_note: string | null;
  decided_at: string | null;
  // PARKED-bucket display.
  parked_at: string | null;
  parked_by_nurse_id: string | null;
  parked_reason: string | null;
}

export interface SimpleNurseQueueSummaryDTO {
  total_waiting: number;
  mine_count: number;
  insufficient_count: number;
}

export interface SimpleNurseQueuePaginationDTO {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface SimpleNurseQueueResponseDTO {
  items: SimpleNurseQueueItemDTO[];
  summary: SimpleNurseQueueSummaryDTO;
  pagination: SimpleNurseQueuePaginationDTO;
}

/** One protocol atom referenced during the session (`sbar.py`'s
 * `_citation_entries`) -- not only the ones that ended up fully satisfied,
 * see that function's docstring. `status` says whether it actually was;
 * `satisfied_requirements` is only non-empty when `status === "SATISFIED"`. */
export interface SimpleAgentCitationDTO {
  atom_id: string;
  decision_point: string | null;
  criteria_text: string | null;
  status: "SATISFIED" | "CONTRADICTED" | "MISSING_INFO";
  satisfied_requirements: SimpleSatisfiedRequirementDTO[];
}

export interface SimpleAgentSbarDTO {
  situation: string;
  background: string;
  assessment: string;
  recommendation: string;
  citations: SimpleAgentCitationDTO[];
}

export interface SimpleNurseTranscriptRowDTO {
  turn_index: number;
  sender: "PATIENT" | "AGENT";
  content: string;
  created_at: string;
}

/** Đường liên lạc của người bệnh trong một ca -- xem simpleNursePatientContactSchema. */
export interface SimpleNursePatientContactDTO {
  account: {
    full_name: string | null;
    email: string | null;
    phone: string | null;
  };
  /** Thẻ hồ sơ EHR đã chọn lúc bắt đầu phiên; null nghĩa là phiên ẩn danh. */
  profile: {
    full_name: string;
    relationship_type: string;
    is_primary: boolean;
    age: number | null;
    gender: string | null;
    phone_number: string | null;
    blood_type: string | null;
    chronic_conditions: string[];
    allergies: string[];
    emergency_contact_name: string | null;
    emergency_contact_phone: string | null;
  } | null;
}

export interface SimpleNurseCaseDetailDTO {
  session_id: string;
  patient: SimpleNursePatientContactDTO;
  initial_message: string;
  final_action: "RETURN_MATCH" | "RETURN_INCOMPLETE" | null;
  final_message: string | null;
  ai_proposed_esi: 1 | 2 | 3 | 4 | 5 | null;
  matched_esi_levels: number[];
  final_concepts: string[];
  session_status?: SimpleSessionStatus;
  attention_required?: boolean;
  attention_reason?: string | null;
  attention_raised_at?: string | null;
  review_status: SimpleReviewStatus;
  assigned_nurse_id: string | null;
  case_version: number;
  final_esi: number | null;
  decision_type: SimpleDecisionType | null;
  decision_reason_code: SimpleReasonCode | null;
  decision_note: string | null;
  sbar: SimpleAgentSbarDTO | null;
  messages: SimpleNurseTranscriptRowDTO[];
}

export interface SimpleClaimPayload {
  version: number;
  action: "CLAIM" | "RELEASE" | "PARK" | "RESTORE";
  // Required (>= 10 ký tự) only for PARK -- see routes_nurse_simple.py's
  // _MIN_PARK_REASON_LENGTH.
  reason?: string | null;
}

export interface SimpleDecisionPayload {
  version: number;
  decision_type: SimpleDecisionType;
  final_esi: number;
  reason_code: SimpleReasonCode;
  note: string | null;
}

export interface SimpleNurseActionResponseDTO {
  session_id: string;
  review_status: SimpleReviewStatus;
  case_version: number;
  final_esi?: number | null;
}
