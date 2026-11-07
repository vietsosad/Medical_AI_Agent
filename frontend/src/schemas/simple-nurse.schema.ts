import { z } from "zod";

/** Zod schemas validating `/api/v1/nurse-simple/*` responses at the network boundary. */

export const simpleReviewStatusSchema = z.enum([
  "WAITING_REVIEW",
  "ASSIGNED",
  "TRIAGE_DECIDED",
  "HANDED_OFF",
  "PARKED",
]);

export const simpleNurseQueueBucketSchema = z.enum(["QUEUE", "PARKED", "DECIDED"]);

const esiLevelSchema = z.union([
  z.literal(1),
  z.literal(2),
  z.literal(3),
  z.literal(4),
  z.literal(5),
]);

export const simpleSatisfiedRequirementSchema = z.object({
  fact_target_id: z.string(),
  name: z.string(),
  operator: z.enum(["EQ", "NEQ", "GT", "GTE", "LT", "LTE"]),
  expected_value: z.union([z.string(), z.number(), z.boolean()]).nullable(),
  actual_value: z.union([z.string(), z.number(), z.boolean()]).nullable(),
});

const simpleWaitBucketSchema = z.object({
  key: z.enum(["UNDER_WARNING", "WARNING", "CRITICAL"]),
  count: z.number(),
});

const simpleMatrixRowKeySchema = z.enum(["1", "2", "3", "4", "5", "INSUFFICIENT", "IN_PROGRESS"]);
const countSchema = z.number().int().nonnegative();

const simpleDecisionMatrixSchema = z.object({
  decided_total: countSchema,
  kept: countSchema,
  more_urgent: countSchema,
  less_urgent: countSchema,
  without_proposal: countSchema,
  without_final_esi: countSchema,
  rows: z.array(
    z.object({
      key: simpleMatrixRowKeySchema,
      counts: z.array(z.object({ final_esi: esiLevelSchema, count: countSchema })),
    }),
  ),
});

const simpleFlaggedClaimSchema = z.object({
  min_cases: countSchema,
  flagged_total: countSchema,
  claimed: countSchema,
  unclaimed: countSchema,
  untimed: countSchema,
  claimed_under_warning: countSchema,
  bins: z.array(
    z.object({ min_minutes: countSchema, max_minutes: countSchema.nullable(), count: countSchema }),
  ),
});

const simpleDecisionWaitSchema = z.object({
  min_cases: countSchema,
  decided_total: countSchema,
  rows: z.array(
    z.object({ key: simpleMatrixRowKeySchema, count: countSchema, median_minutes: countSchema.nullable() }),
  ),
});

const simpleWeekdayHourSchema = z.object({
  utc_offset_hours: z.number().int(),
  first_day: z.string(),
  last_day: z.string(),
  total: countSchema,
  rows: z.array(
    z.object({
      weekday: z.union([z.literal(1), z.literal(2), z.literal(3), z.literal(4), z.literal(5), z.literal(6), z.literal(7)]),
      days: countSchema,
      // Đúng 24 giờ: thiếu một giờ là cả hàng lệch cột, xếp phiên vào sai giờ.
      hours: z.array(countSchema).length(24),
    }),
  ),
});

export const simpleNurseDashboardSchema = z.object({
  generated_at: z.string(),
  window_days: z.number().int().positive(),
  waiting: z.number(),
  assigned_total: z.number(),
  assigned_to_me: z.number(),
  parked: z.number(),
  decided: z.number(),
  insufficient_live: z.number(),
  attention_live: z.number(),
  in_progress_live: z.number(),
  longest_wait_minutes: z.number().nullable(),
  esi_distribution: z.array(
    z.object({ level: esiLevelSchema.nullable(), count: z.number() }),
  ),
  wait_buckets: z.array(simpleWaitBucketSchema),
  esi_wait_matrix: z.array(
    z.object({
      key: z.enum(["1", "2", "3", "4", "5", "INSUFFICIENT", "IN_PROGRESS"]),
      counts: z.array(simpleWaitBucketSchema),
    }),
  ),
  completed_in_window: z.number(),
  decided_in_window: z.number(),
  hour_of_day: z.array(z.object({ hour_utc: z.number().int().min(0).max(23), completed: z.number() })),
  recent_hours: z.array(z.object({ hour_start: z.string(), completed: z.number(), decided: z.number() })),
  agreement: z.object({
    decided_total: z.number(),
    confirmed: z.number(),
    escalated: z.number(),
    de_escalated: z.number(),
    adjusted_without_proposal: z.number(),
  }),
  reason_codes: z.array(z.object({ code: z.string(), count: z.number() })),
  daily_volume: z.array(
    z.object({ date: z.string(), completed: z.number(), decided: z.number() }),
  ),
  // Chỉ cộng thêm: máy chủ chưa có các khối này vẫn qua được kiểm tra.
  decision_matrix: simpleDecisionMatrixSchema.optional(),
  flagged_claim: simpleFlaggedClaimSchema.optional(),
  decision_wait: simpleDecisionWaitSchema.optional(),
  weekday_hour: simpleWeekdayHourSchema.optional(),
});

/**
 * "Cần xem ngay" from the backend's pre-LLM emergency screen: a reason for a
 * human to look now, never an ESI. A flagged case can still be ACTIVE.
 */
const attentionFields = {
  session_status: z.enum(["ACTIVE", "COMPLETED", "ABANDONED"]).default("COMPLETED"),
  attention_required: z.boolean().default(false),
  attention_reason: z.string().nullable().default(null),
  attention_raised_at: z.string().nullable().default(null),
};

export const simpleNurseQueueItemSchema = z.object({
  session_id: z.string(),
  initial_message: z.string(),
  final_action: z.enum(["RETURN_MATCH", "RETURN_INCOMPLETE"]).nullable(),
  ai_proposed_esi: esiLevelSchema.nullable(),
  is_insufficient: z.boolean(),
  ...attentionFields,
  turn_count: z.number(),
  waiting_since: z.string(),
  review_status: simpleReviewStatusSchema,
  assigned_nurse_id: z.string().nullable(),
  case_version: z.number(),
  unread_count: z.number(),
  patient_email: z.string().nullable(),
  patient_name: z.string().nullable(),
  final_esi: z.number().int().min(1).max(5).nullable(),
  decision_type: z.enum(["CONFIRM_ESI", "ADJUST_ESI"]).nullable(),
  decision_note: z.string().nullable(),
  decided_at: z.string().nullable(),
  parked_at: z.string().nullable(),
  parked_by_nurse_id: z.string().nullable(),
  parked_reason: z.string().nullable(),
});

export const simpleNurseQueueResponseSchema = z.object({
  items: z.array(simpleNurseQueueItemSchema),
  summary: z.object({
    total_waiting: z.number(),
    mine_count: z.number(),
    insufficient_count: z.number(),
  }),
  pagination: z.object({
    page: z.number(),
    page_size: z.number(),
    total_items: z.number(),
    total_pages: z.number(),
  }),
});

export const simpleAgentCitationSchema = z.object({
  atom_id: z.string(),
  decision_point: z.string().nullable(),
  criteria_text: z.string().nullable(),
  status: z.enum(["SATISFIED", "CONTRADICTED", "MISSING_INFO"]),
  satisfied_requirements: z.array(simpleSatisfiedRequirementSchema),
});

export const simpleAgentSbarSchema = z.object({
  situation: z.string(),
  background: z.string(),
  assessment: z.string(),
  recommendation: z.string(),
  citations: z.array(simpleAgentCitationSchema),
});

export const simpleNurseTranscriptRowSchema = z.object({
  turn_index: z.number(),
  sender: z.enum(["PATIENT", "AGENT"]),
  content: z.string(),
  created_at: z.string(),
});

/**
 * Danh tính & đường liên lạc của người bệnh, chỉ trả qua endpoint đã đứng sau
 * quyền nhân viên lâm sàng (xem `_patient_contact_block` trong
 * src/api/routes_nurse_simple.py). `profile` là null với phiên ẩn danh.
 */
export const simpleNursePatientContactSchema = z.object({
  account: z.object({
    full_name: z.string().nullable(),
    email: z.string().nullable(),
    phone: z.string().nullable(),
  }),
  profile: z
    .object({
      full_name: z.string(),
      relationship_type: z.string(),
      is_primary: z.boolean(),
      age: z.number().nullable(),
      gender: z.string().nullable(),
      phone_number: z.string().nullable(),
      blood_type: z.string().nullable(),
      chronic_conditions: z.array(z.string()),
      allergies: z.array(z.string()),
      emergency_contact_name: z.string().nullable(),
      emergency_contact_phone: z.string().nullable(),
    })
    .nullable(),
});

export const simpleNurseCaseDetailSchema = z.object({
  session_id: z.string(),
  patient: simpleNursePatientContactSchema,
  initial_message: z.string(),
  final_action: z.enum(["RETURN_MATCH", "RETURN_INCOMPLETE"]).nullable(),
  final_message: z.string().nullable(),
  ai_proposed_esi: esiLevelSchema.nullable(),
  matched_esi_levels: z.array(z.number().int().min(1).max(5)),
  final_concepts: z.array(z.string()),
  ...attentionFields,
  review_status: simpleReviewStatusSchema,
  assigned_nurse_id: z.string().nullable(),
  case_version: z.number(),
  final_esi: z.number().int().min(1).max(5).nullable(),
  decision_type: z.enum(["CONFIRM_ESI", "ADJUST_ESI"]).nullable(),
  decision_reason_code: z
    .enum(["MATCHES_PROTOCOL", "ADDITIONAL_CLINICAL_JUDGMENT", "INSUFFICIENT_PATIENT_DATA", "OTHER"])
    .nullable(),
  decision_note: z.string().nullable(),
  sbar: simpleAgentSbarSchema.nullable(),
  messages: z.array(simpleNurseTranscriptRowSchema),
});

export const simpleNurseActionResponseSchema = z.object({
  session_id: z.string(),
  review_status: simpleReviewStatusSchema,
  case_version: z.number(),
  final_esi: z.number().int().min(1).max(5).nullable().optional(),
});
