import { z } from "zod";

export const esiLevelSchema = z.union([
  z.literal(1),
  z.literal(2),
  z.literal(3),
  z.literal(4),
  z.literal(5),
]);

export const reviewStatusSchema = z.enum([
  "WAITING_REVIEW",
  "ASSIGNED",
  "IN_REVIEW",
  "NEEDS_MORE_INFO",
  "SPECIALIST_REVIEW_REQUIRED",
  "TRIAGE_DECIDED",
  "HANDED_OFF",
]);

export const observationKindSchema = z.enum([
  "HEART_RATE",
  "BLOOD_PRESSURE",
  "RESPIRATORY_RATE",
  "SPO2",
  "TEMPERATURE",
  "CONSCIOUSNESS",
]);

export const observationAvailabilitySchema = z.enum([
  "MEASURED",
  "UNKNOWN",
  "NOT_MEASURED",
  "NOT_APPLICABLE",
]);

export const observationSourceSchema = z.enum([
  "PATIENT_REPORTED",
  "NURSE_MEASURED",
  "DEVICE",
  "UNKNOWN",
]);

const nurseIdentitySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
});

const dataCompletenessSchema = z.object({
  is_complete: z.boolean(),
  missing_fields: z.array(z.string()),
});

export const nurseQueueItemSchema = z.object({
  case_id: z.string().min(1),
  patient_name: z.string().min(1),
  masked_patient_label: z.string().min(1),
  age: z.number().int().min(0).max(130).nullable(),
  sex: z.string().nullable(),
  // A case with incomplete intake is still actionable in the Nurse queue.
  // The backend reports the missing field through data_completeness.
  chief_complaint: z.string(),
  ai_recommended_esi: esiLevelSchema.nullable(),
  red_flags: z.array(z.string()),
  is_red_flag: z.boolean(),
  waiting_since: z.string().min(1),
  wait_time_seconds: z.number().int().nonnegative(),
  review_status: reviewStatusSchema,
  assignee: nurseIdentitySchema.nullable(),
  data_completeness: dataCompletenessSchema,
  case_version: z.number().int().positive(),
  alert_acknowledged: z.boolean(),
  // Bộ đếm phục vụ hiển thị, không phải dữ liệu an toàn: đặt mặc định để hàng
  // đợi vẫn dùng được khi backend cũ chưa phát trường này trong lúc triển khai.
  unread_count: z.number().int().nonnegative().default(0),
  last_message_at: z.string().nullable().default(null),
});

export const nurseQueueResponseSchema = z.object({
  items: z.array(nurseQueueItemSchema),
  summary: z.object({
    total_waiting: z.number().int().nonnegative(),
    urgent_count: z.number().int().nonnegative(),
    mine_count: z.number().int().nonnegative(),
    // Non-safety UI counter: default keeps the queue usable during a rolling
    // frontend/backend deployment where the older API has not emitted it yet.
    specialist_count: z.number().int().nonnegative().default(0),
    longest_wait_seconds: z.number().int().nonnegative(),
  }),
  sla_target_minutes: z.number().int().positive().nullable(),
});

export const clinicalTranscriptMessageSchema = z.object({
  id: z.string().min(1),
  // NURSE là tin do một nhân viên lâm sàng thật gõ; giao diện bắt buộc phải
  // dán nhãn khác với tin do mô hình sinh ra.
  sender: z.enum(["PATIENT", "AI_AGENT", "SYSTEM_SHIELD", "NURSE"]),
  content: z.string(),
  created_at: z.string().min(1),
  sender_name: z.string().nullable().default(null),
  read_at: z.string().nullable().default(null),
});

export const inboxResponseSchema = z.object({
  items: z.array(
    z.object({
      case_id: z.string().min(1),
      patient_name: z.string().min(1),
      age: z.number().int().min(0).max(130).nullable(),
      sex: z.string().nullable(),
      chief_complaint: z.string(),
      ai_recommended_esi: esiLevelSchema.nullable(),
      is_red_flag: z.boolean(),
      priority: z.enum(["RED_FLAG", "URGENT", "NORMAL"]),
      preview: z.string(),
      unread_count: z.number().int().nonnegative(),
      last_message_at: z.string().nullable(),
      assignee: nurseIdentitySchema.nullable(),
      case_version: z.number().int().positive(),
    }),
  ),
  total_unread: z.number().int().nonnegative(),
  urgent_unread: z.number().int().nonnegative(),
});

export const caseMessagesResponseSchema = z.object({
  case_id: z.string().min(1),
  messages: z.array(clinicalTranscriptMessageSchema),
  unread_count: z.number().int().nonnegative(),
});

export const emergencyContactResponseSchema = z.object({
  case_id: z.string().min(1),
  contacts: z.array(
    z.object({
      label: z.string().min(1),
      full_name: z.string().nullable(),
      relationship: z.string().nullable(),
      // null nghĩa là chưa khai báo. Giao diện phải hiện "Chưa cập nhật";
      // tuyệt đối không thay bằng số của người khác.
      phone: z.string().nullable(),
    }),
  ),
  expires_at: z.string().min(1),
});

const clinicalObservationSchema = z.object({
  id: z.string().min(1),
  kind: observationKindSchema,
  value: z.string().nullable(),
  unit: z.string().nullable(),
  availability: observationAvailabilitySchema,
  source: observationSourceSchema,
  measured_at: z.string().nullable(),
  recorded_by: nurseIdentitySchema,
  recorded_at: z.string().min(1),
});

export const nurseCaseDetailSchema = nurseQueueItemSchema.extend({
  triage_status: z.string().min(1),
  final_esi: esiLevelSchema.nullable(),
  observations: z.array(clinicalObservationSchema),
  risk_context: z.object({
    age: z.number().int().min(0).max(130).nullable(),
    gender: z.string().nullable(),
    height_cm: z.number().positive().nullable(),
    weight_kg: z.number().positive().nullable(),
    bmi: z.number().positive().nullable(),
    blood_type: z.string().nullable(),
    chronic_conditions: z.array(z.string()),
    allergies: z.array(z.string()),
    active_medications: z.array(z.string()),
    pregnancy_status: z.string().nullable(),
    patient_reported_vitals: z.record(z.string(), z.union([z.string(), z.number()])),
    patient_reported_vitals_source: z.string().nullable(),
    patient_reported_vitals_measured_at: z.string().nullable(),
    vital_signs_status: z.string(),
    ehr_confirmation_status: z.string(),
    ehr_profile_updated_at: z.string().nullable(),
    patient_context_note: z.string().nullable(),
  }),
  sbar: z.object({
    situation: z.string().nullable(),
    background: z.string().nullable(),
    assessment: z.string().nullable(),
    recommendation: z.string().nullable(),
  }),
  citations: z.array(
    z.object({
      code: z.string().min(1),
      title: z.string().nullable().default(null),
      excerpt: z.string().nullable().default(null),
      source_uri: z.string().nullable().default(null),
      section: z.string().nullable().default(null),
      version: z.string().nullable().default(null),
      content_hash: z.string().nullable().default(null),
    }),
  ),
  ai_rationale: z.string().nullable(),
  transcript: z.array(clinicalTranscriptMessageSchema),
  specialist_review: z.object({
    required: z.boolean(),
    reason_code: z.string().nullable(),
    note: z.string().nullable(),
    requested_at: z.string().nullable(),
  }),
});

export const nurseActionResponseSchema = z.object({
  success: z.boolean(),
  case_id: z.string().min(1),
  review_status: reviewStatusSchema,
  case_version: z.number().int().positive(),
  message: z.string().min(1),
});

export const piiAccessResponseSchema = z.object({
  case_id: z.string().min(1),
  full_name: z.string().min(1),
  phone: z.string().nullable(),
  emergency_contact_name: z.string().nullable(),
  emergency_contact_phone: z.string().nullable(),
  expires_at: z.string().min(1),
});

export const observationsFormSchema = z
  .object({
    observations: z.array(
      z.object({
        kind: observationKindSchema,
        value: z.string(),
        unit: z.string(),
        availability: observationAvailabilitySchema,
        source: observationSourceSchema,
        measured_at: z.string(),
      }),
    ),
  })
  .superRefine(({ observations }, context) => {
    observations.forEach((observation, index) => {
      if (
        observation.availability === "MEASURED" &&
        (!observation.value.trim() || !observation.unit || !observation.measured_at)
      ) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Giá trị đã đo cần đủ số liệu, đơn vị và thời điểm đo.",
          path: ["observations", index, "value"],
        });
      }
    });
  });

export const triageDecisionFormSchema = z
  .object({
    action: z.enum(["CONFIRM_ESI", "ADJUST_ESI", "REQUEST_SPECIALIST_REVIEW"]),
    final_esi: z.coerce.number().int().min(1).max(5),
    reason_code: z.string().min(2, "Vui lòng chọn lý do."),
    note: z.string(),
  })
  .superRefine((value, context) => {
    if (value.action !== "CONFIRM_ESI" && value.note.trim().length < 10) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Cần ghi chú ít nhất 10 ký tự.",
        path: ["note"],
      });
    }
  });

export const handoffFormSchema = z.object({
  destination: z.enum([
    "IMMEDIATE_CARE",
    "PRIORITY_IN_PERSON",
    "ROUTINE_QUEUE",
  ]),
  note: z.string().min(5, "Ghi chú bàn giao cần ít nhất 5 ký tự.").max(800),
});

export const piiAccessFormSchema = z.object({
  reason: z.string().min(10, "Lý do truy cập cần ít nhất 10 ký tự.").max(300),
});

export type ObservationsFormValues = z.infer<typeof observationsFormSchema>;
export type TriageDecisionFormValues = z.infer<typeof triageDecisionFormSchema>;
export type HandoffFormValues = z.infer<typeof handoffFormSchema>;
export type PiiAccessFormValues = z.infer<typeof piiAccessFormSchema>;
