/**
 * ZOD VALIDATION SCHEMAS FOR CLINICAL HISTORY & SBAR MODULE
 * Đảm bảo an toàn runtime tuyệt đối khi phân tích cú pháp dữ liệu từ API hoặc Fallback Seed.
 * Zero `any` tolerance - Đồng bộ 100% với DTO contracts.
 */
import * as z from "zod";
import { chatMessageSchema } from "@/schemas/triage-stream.schema";

// Replay uses the same public message contract as live SSE. Keeping a second,
// smaller schema here previously stripped evidence and rejected newer controls.
export const ChatMessageSchema = chatMessageSchema;

// ============================================================================
// 2. ZOD SCHEMAS CHO LỊCH SỬ LÂM SÀNG & KÝ ỨC SBAR (NHÓM 4)
// ============================================================================
export const EsiLevelSchema = z.union([
  z.literal(1),
  z.literal(2),
  z.literal(3),
  z.literal(4),
  z.literal(5),
]);

export const HitlReviewStatusSchema = z.enum([
  "APPROVED",
  "OVERRIDDEN",
  "PENDING_REVIEW",
  "EMERGENCY_REJECTED",
]);

export const TriageSessionStatusSchema = z.enum([
  "IN_PROGRESS",
  "HITL_REVIEWING",
  "COMPLETED",
  "RED_FLAG_LOCKED",
  "CANCELLED",
]);

export const HitlSignatureSchema = z.object({
  reviewer_name: z.string().min(1, "Tên chuyên gia thẩm định không được để trống"),
  review_timestamp: z.string(),
  status: HitlReviewStatusSchema,
  original_esi: EsiLevelSchema,
  final_esi: EsiLevelSchema,
  justification_note: z.string().optional(),
});

export const SbarReportSchema = z.object({
  situation: z.string().min(1, "Khối Situation không được thiếu trong phiếu SBAR"),
  background: z.string(),
  assessment: z.string(),
  recommendation: z.string(),
  citations: z.array(z.string()),
});

export const TriageHistoryListItemObjectSchema = z.object({
  session_id: z.string().min(1, "ID phiên khám không hợp lệ"),
  profile_name: z.string().nullable().optional(),
  relationship_type: z.string().nullable().optional(),
  // A newly-created case is persisted before its first complaint is collected.
  chief_complaint: z.string(),
  created_at: z.string(),
  status: TriageSessionStatusSchema,
  final_esi: EsiLevelSchema.nullable(),
  hitl_status: HitlReviewStatusSchema,
  sbar_snippet: z.string(),
  sbar_finalized: z.boolean(),
  unread_from_staff: z.number().optional(),
});

export const TriageHistoryListItemSchema = TriageHistoryListItemObjectSchema;

export const TriageSessionDetailSchema = TriageHistoryListItemObjectSchema.extend({
  messages: z.array(ChatMessageSchema),
  sbar_report: SbarReportSchema.nullable(),
  hitl_signature: HitlSignatureSchema.nullable().optional(),
});

export const TriageHistoryListResponseSchema = z.object({
  items: z.array(TriageHistoryListItemSchema),
});
