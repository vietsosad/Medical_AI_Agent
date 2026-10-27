import { z } from "zod";

import { simpleAgentSbarSchema, simpleReviewStatusSchema, simpleSatisfiedRequirementSchema } from "./simple-nurse.schema";

// Mức ESI luôn là số nguyên 1-5; 2.5 hay 0 là dữ liệu hỏng, không phải một mức.
const esiNumberSchema = z.number().int().min(1).max(5);

/**
 * Zod schemas validating `/api/v1/simple-triage/*` responses at the network
 * boundary -- same purpose as `triage-stream.schema.ts`, but for the much
 * smaller, un-nested `simple_agent` pilot contract (see
 * `@/types/simple-triage`). No SSE here: both pilot endpoints are plain JSON.
 */

export const simpleTriageDecisionSchema = z.object({
  route: z.enum(["TRIAGE", "CLARIFY", "NON_CLINICAL", "GUARDRAIL"]),
  action: z.enum([
    "ASK_NEXT",
    "ASK_CONFIRMATION",
    "ASK_CLARIFICATION",
    "RESPOND",
    "REFUSE",
    "RETURN_MATCH",
    "RETURN_INCOMPLETE",
  ]),
  reason: z.string(),
  subject_type: z.enum(["SELF", "OTHER_PERSON"]),
  subject_label: z.string().nullable(),
  concepts: z.array(z.string()),
  retrieved_protocol_atoms: z.number(),
  accepted_fact_ids: z.array(z.string()),
  qualitative_observation_ids: z.array(z.string()),
  asserted_concept_ids: z.array(z.string()),
  negated_concept_ids: z.array(z.string()),
  supported_protocol_atoms: z.number(),
  unresolved_protocol_requirements: z.number(),
  question_target_id: z.string().nullable(),
  matched_esi_levels: z.array(esiNumberSchema),
  matched_atoms: z
    .array(z.object({
      atom_id: z.string(),
      decision_point: z.string().nullable(),
      criteria_text: z.string().nullable(),
      satisfied_requirements: z.array(simpleSatisfiedRequirementSchema).optional(),
    }))
    .optional(),
  // Dữ liệu chẩn đoán nội bộ, không hiển thị -- optional vì PATIENT
  // rows' decision_snapshot is `{}` and older AGENT rows predate these two
  // fields; both parse via .partial() on the message-row schema regardless,
  // this only matters for the turn-response schema below.
  tool_calls: z
    .array(z.object({ tool: z.string(), arguments: z.record(z.string(), z.unknown()), result: z.record(z.string(), z.unknown()) }))
    .optional(),
  retrieved_atoms_this_turn: z
    .array(z.object({ atom_id: z.string(), score: z.number(), confident_enough_to_ask: z.boolean() }))
    .optional(),
  retrieval_query: z.string().nullable().optional(),
  // Backend pre-LLM emergency screen hit -- see SimpleSafetyAlertDTO.
  safety_alert: z
    .object({
      rule_id: z.string(),
      kind: z.enum(["EMERGENCY", "SELF_HARM"]),
      label: z.string(),
      trigger: z.string(),
    })
    .optional(),
});

export const simpleTriageTurnResponseSchema = z.object({
  session_id: z.string(),
  message: z.string(),
  decision: simpleTriageDecisionSchema,
});

export const simpleTriageSessionSummarySchema = z.object({
  session_id: z.string(),
  status: z.enum(["ACTIVE", "COMPLETED", "ABANDONED"]),
  profile_id: z.string().nullable(),
  initial_message: z.string(),
  turn_count: z.number(),
  started_at: z.string(),
  last_activity_at: z.string(),
  completed_at: z.string().nullable(),
  final_route: z.string().nullable(),
  final_action: z.string().nullable(),
  matched_esi_levels: z.array(esiNumberSchema),
  final_message: z.string().nullable(),
  final_concepts: z.array(z.string()),
  review_status: simpleReviewStatusSchema.nullable(),
  is_overridden: z.boolean(),
  final_esi: esiNumberSchema.nullable(),
  decision_type: z.enum(["CONFIRM_ESI", "ADJUST_ESI"]).nullable().default(null),
  decision_reason_code: z.string().nullable().default(null),
  decision_note: z.string().nullable().default(null),
  reviewer_name: z.string().nullable().default(null),
  reviewed_at: z.string().nullable().default(null),
  review_display_status: z.enum(["APPROVED", "OVERRIDDEN", "PENDING_REVIEW"]),
  unread_from_staff: z.number(),
});

export const simpleTriageMessageRowSchema = z.object({
  turn_index: z.number(),
  sender: z.enum(["PATIENT", "AGENT"]),
  content: z.string(),
  route: z.string().nullable(),
  action: z.string().nullable(),
  question_target_id: z.string().nullable(),
  // `.partial()`: `{}` on PATIENT rows, a (possibly not-yet-extended-with-
  // every-future-field) decision dict on AGENT rows -- see
  // giữ nguyên theo hợp đồng backend. Dữ liệu chẩn đoán nội bộ, không phải
  // contract this app's behavior depends on.
  decision_snapshot: simpleTriageDecisionSchema.partial(),
  created_at: z.string(),
});

export const simpleTriageSessionDetailSchema = simpleTriageSessionSummarySchema.extend({
  messages: z.array(simpleTriageMessageRowSchema),
  sbar: simpleAgentSbarSchema.nullable(),
});
