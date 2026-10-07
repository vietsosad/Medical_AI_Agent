import { z } from "zod";

// FastAPI/Pydantic serializes optional DTO fields with `null` by default.
// Normalize those values to `undefined` so the parsed SSE event still matches
// the existing optional TypeScript properties used by the UI.
const optionalFromNullable = <TSchema extends z.ZodTypeAny>(schema: TSchema) =>
  schema.nullish().transform((value): z.output<TSchema> | undefined => value ?? undefined);

export const intentSchema = z.enum([
  "TRIAGE_NEW_SYMPTOM",
  "TRIAGE_FOLLOW_UP",
  "GREETING_HELP",
  "OUT_OF_SCOPE",
  "UNCLEAR",
  "EMERGENCY_SIGNAL",
  "SAFETY_CRISIS_SUPPORT",
]);

export const phaseSchema = z.enum([
  "SAFETY_CHECK",
  "INTENT_CLASSIFICATION",
  "INTAKE_EXTRACTION",
  "CLARIFICATION",
  "PATIENT_CONFIRMATION",
  "RETRIEVAL",
  "REASONING",
  "REASSESSMENT",
  "HANDOFF",
  "COMPLETE",
]);

export const decisionStatusSchema = z.enum([
  "NOT_APPLICABLE",
  "COLLECTING",
  "NEEDS_CLARIFICATION",
  "READY_FOR_EVIDENCE",
  "READY_FOR_REASONING",
  "AWAITING_PATIENT_CONFIRMATION",
  "INSUFFICIENT_EVIDENCE",
  "RETRIEVAL_FAILURE",
  "PROPOSED",
  "EMERGENCY_ESCALATED",
]);

export const responseTypeSchema = z.enum([
  "TEXT",
  "STRUCTURED_QUESTION",
  "INTAKE_REVIEW",
  "EMERGENCY",
  "TRIAGE_PROPOSAL",
  "SAFETY_GUIDANCE",
]);

export const evidenceStatusSchema = z.enum([
  "NOT_REQUESTED",
  "RETRIEVED",
  "INSUFFICIENT_EVIDENCE",
  "RETRIEVAL_FAILURE",
  "CASE_EXAMPLE_SUPPORT",
  "SUFFICIENT",
]);

export const optionSchema = z.object({
  id: z.string(),
  label: z.string(),
  value: z.union([z.string(), z.number()]),
  description: optionalFromNullable(z.string()),
  isRisk: z.boolean().optional(),
  isExclusive: z.boolean().optional(),
});

const vitalFormFieldSchema = z.object({
  id: z.enum([
    "heart_rate",
    "blood_pressure",
    "respiratory_rate",
    "spo2",
    "temperature_c",
    "gcs",
  ]),
  label: z.string().min(1),
  unit: z.string().min(1),
  placeholder: z.string().min(1),
  inputMode: z.enum(["numeric", "decimal", "text"]),
  min: optionalFromNullable(z.number()),
  max: optionalFromNullable(z.number()),
  step: optionalFromNullable(z.number().positive()),
});

const ehrConfirmationSnapshotSchema = z.object({
  age: z.number().int().min(0).max(130).nullable(),
  gender: z.string().nullable(),
  height_cm: z.number().positive().nullable(),
  weight_kg: z.number().positive().nullable(),
  bmi: z.number().positive().nullable(),
  blood_type: z.string().nullable(),
  chronic_conditions: z.array(z.string()),
  allergies: z.array(z.string()),
  daily_medications: z.array(z.string()),
});

export const structuredPayloadSchema = z.object({
  optionsType: z.enum(["single", "multiple", "scale", "text_only", "vitals_form"]),
  options: optionalFromNullable(z.array(optionSchema)),
  fields: optionalFromNullable(z.array(vitalFormFieldSchema)),
  ehrSnapshot: optionalFromNullable(ehrConfirmationSnapshotSchema),
  minScale: optionalFromNullable(z.number().int()),
  maxScale: optionalFromNullable(z.number().int()),
  submitted: z.boolean().optional(),
  selectedAnswer: optionalFromNullable(z.union([
    z.string(),
    z.array(z.string()),
    z.number(),
  ])),
});

const retrievalChannelSchema = z.object({
  channel: z.enum(["vi_dense", "en_dense", "sparse", "demo_dense", "hybrid"]),
  rank: z.number().int().positive(),
  score: z.number().nullable().optional(),
});

export const ragCitationSchema = z.object({
  id: z.string(),
  title: z.string(),
  protocolId: z.string(),
  excerpt: z.string(),
  relevanceScore: optionalFromNullable(z.number()),
  issuingBody: optionalFromNullable(z.string()),
  sourceUri: optionalFromNullable(z.string().url()),
  version: optionalFromNullable(z.string()),
  section: optionalFromNullable(z.string()),
  effectiveDate: optionalFromNullable(z.string()),
  validationStatus: optionalFromNullable(z.literal("approved")),
  contentHash: optionalFromNullable(z.string()),
  reviewedBy: optionalFromNullable(z.string()),
  reviewedAt: optionalFromNullable(z.string()),
  calibrationId: optionalFromNullable(z.string()),
  sourceType: optionalFromNullable(z.enum(["validated_protocol", "case_example"])),
  retrievalChannels: z.array(retrievalChannelSchema).optional(),
});

export const caseSupportSchema = z.object({
  caseId: z.string(),
  excerpt: z.string(),
  /** Raw cosine similarity. Kept for audit; never rendered as a confidence. */
  similarityScore: optionalFromNullable(z.number()),
  /** Post-rerank retrieval relevance. Also not a probability. */
  retrievalRelevance: optionalFromNullable(z.number()),
  relevanceBand: z
    .enum(["HIGH", "MODERATE", "LOW", "UNKNOWN"])
    .nullish()
    .transform((value) => value ?? "UNKNOWN"),
  /** The retrieved case's own recorded level. Never this patient's ESI. */
  validatedEsiLevel: optionalFromNullable(z.number().int().min(1).max(5)),
  candidateEsiLevels: z.array(z.number().int().min(1).max(5)).nullish()
    .transform((value) => value ?? []),
  labelStatus: z
    .enum(["CONSISTENT", "CONFLICTING", "UNKNOWN"])
    .nullish()
    .transform((value) => value ?? "UNKNOWN"),
  ageBand: optionalFromNullable(z.string()),
  sex: optionalFromNullable(z.string()),
  symptomConcepts: z.array(z.string()).nullish().transform((value) => value ?? []),
  retrievalScope: z.literal("CASE_SUPPORT"),
  authorityStatus: z.literal("NOT_PROTOCOL"),
  sourceType: z.literal("case_example"),
});

const ehrSnapshotSchema = z.object({
  age: z.number().int().min(0).max(130).nullable().default(null),
  gender: z.string().nullable().default(null),
  height_cm: z.number().positive().nullable().default(null),
  weight_kg: z.number().positive().nullable().default(null),
  bmi: z.number().positive().nullable().default(null),
  blood_type: z.string().nullable().default(null),
  chronic_conditions: z.array(z.string()),
  allergies: z.array(z.string()),
  daily_medications: z.array(z.string()),
  updated_at: z.string().nullable(),
  confirmation_status: z.enum([
    "NOT_REVIEWED",
    "CONFIRMED",
    "UPDATED_BY_PATIENT",
    "UNCERTAIN",
  ]),
  patient_context_note: z.string().nullable(),
});

export const intakeSummarySchema = z.object({
  chief_complaint: z.array(z.string()),
  /** Mentioned but hedged. Shown so the patient can confirm or deny them. */
  uncertain_symptoms: z.array(z.string()).nullish().transform((v) => v ?? []),
  onset_time: z.string().nullable(),
  severity_score: z.number().int().min(0).max(10).nullable(),
  radiation: z.string().nullable(),
  associated_symptoms: z.array(z.string()),
  current_medication: z.array(z.string()),
  recent_procedure: z.string().nullable().optional(),
  vital_signs: z.record(z.union([z.string(), z.number()])).optional(),
  vital_signs_status: z.enum([
    "NOT_REVIEWED",
    "PATIENT_REPORTED",
    "UNAVAILABLE_CONFIRMED",
    "UNCERTAIN",
  ]).optional(),
  vital_signs_source: z.string().nullable().optional(),
  vital_signs_measured_at: z.string().nullable().optional(),
  ehr_snapshot: ehrSnapshotSchema.optional(),
});

export const chatMessageSchema = z.object({
  id: z.string(),
  // 'nurse' là tin do một nhân viên lâm sàng thật gõ. Thiếu nhãn này thì cả
  // danh sách tin nhắn hỏng ngay lần đầu nhân viên nhắn cho người bệnh.
  sender: z.enum(["user", "bot", "system_shield", "nurse"]),
  senderName: z.string().nullish(),
  timestamp: z.string(),
  content: z.string(),
  step: z.number().int().positive(),
  structured: structuredPayloadSchema.nullish(),
  ragCitations: z.array(ragCitationSchema).nullish(),
  caseSupport: z.array(caseSupportSchema).nullish(),
  intent: intentSchema.nullish(),
  responseType: responseTypeSchema.nullish(),
  decisionStatus: decisionStatusSchema.nullish(),
  workflowPhase: phaseSchema.nullish(),
  esiLevel: z.union([
    z.literal(1),
    z.literal(2),
    z.literal(3),
    z.literal(4),
    z.literal(5),
  ]).nullable().optional(),
  evidenceStatus: evidenceStatusSchema.nullish(),
  retrievalDegradedModes: z.array(z.string()).default([]),
  intakeSummary: intakeSummarySchema.nullish(),
  requiresPatientConfirmation: z.boolean().default(false),
  sbarFinalized: z.boolean().default(false),
});

export const sessionStatusSchema = z.object({
  session_id: z.string(),
  status: z.enum([
    "IN_PROGRESS",
    "HITL_REVIEWING",
    "COMPLETED",
    "RED_FLAG_LOCKED",
    "CANCELLED",
  ]),
  profile_id: z.string().nullable().optional(),
  ai_proposed_esi: z.number().int().min(1).max(5).nullable().optional(),
  final_esi: z.number().int().min(1).max(5).nullable().optional(),
  hitl_status: z.enum([
    "APPROVED",
    "OVERRIDDEN",
    "PENDING_REVIEW",
    "EMERGENCY_REJECTED",
  ]),
  reviewer_name: z.string().nullable().default(null),
  reviewed_at: z.string().nullable().default(null),
  decision_type: z.enum(["CONFIRM_ESI", "ADJUST_ESI"]).nullable().default(null),
  decision_note: z.string().nullable().default(null),
  is_red_flag_triggered: z.boolean(),
  created_at: z.string(),
  updated_at: z.string().nullable().optional(),
  sbar_summary: z.record(z.unknown()).nullable().optional(),
  sbar_finalized: z.boolean().default(false),
  intake_confirmation_status: z.enum([
    "NOT_READY",
    "AWAITING_CONFIRMATION",
    "CONFIRMED",
  ]),
  intake_summary: intakeSummarySchema.nullable().optional(),
  workflow_phase: phaseSchema.nullable().optional(),
  decision_status: decisionStatusSchema.nullable().optional(),
  evidence_status: evidenceStatusSchema.nullable().optional(),
  retrieval_degraded_modes: z.array(z.string()).default([]),
  // Người bệnh có quyền biết ai đang xem hồ sơ của mình. Mặc định giữ nguyên
  // hành vi cũ để bản backend chưa cập nhật vẫn dùng được.
  care_team_name: z.string().nullable().default(null),
  care_team_status: z
    .enum([
      "AI_SCREENING",
      "WAITING_REVIEW",
      "STAFF_REVIEWING",
      "SPECIALIST_REVIEW",
      "COMPLETED",
    ])
    .default("AI_SCREENING"),
  unread_from_staff: z.number().int().nonnegative().default(0),
});

export const sessionMessagesResponseSchema = z.object({
  session_status: sessionStatusSchema,
  messages: z.array(chatMessageSchema),
});

export const startTriageResponseSchema = z.object({
  session_id: z.string(),
  status: z.enum([
    "IN_PROGRESS",
    "HITL_REVIEWING",
    "COMPLETED",
    "RED_FLAG_LOCKED",
    "CANCELLED",
  ]),
  message: z.string(),
  is_red_flag: z.boolean(),
});

const eventBase = {
  message: z.string(),
  sequence: z.number().int().nonnegative(),
  elapsedMs: z.number().int().nonnegative(),
  phase: phaseSchema.nullish(),
  intent: intentSchema.nullish(),
  label: z.string().nullish(),
  detail: z.string().nullish(),
  progress: z.number().int().min(0).max(100).nullish(),
  timestamp: z.string(),
};

export const agentStreamEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("accepted"), ...eventBase }),
  z.object({ type: z.literal("progress"), ...eventBase }),
  z.object({ type: z.literal("intent"), ...eventBase }),
  z.object({ type: z.literal("heartbeat"), ...eventBase }),
  z.object({
    type: z.literal("result"),
    ...eventBase,
    result: chatMessageSchema,
  }),
  z.object({
    type: z.literal("error"),
    ...eventBase,
    retryable: z.boolean(),
    errorCode: z.string(),
  }),
]);
