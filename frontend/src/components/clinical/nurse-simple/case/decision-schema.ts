import { z } from "zod";

import type { SimpleDecisionType, SimpleReasonCode } from "@/types/simple-nurse";

/**
 * Luật của bàn quyết định, bám đúng `submit_simple_decision` trong
 * src/api/routes_nurse_simple.py:
 * - Xác nhận (CONFIRM_ESI) chỉ khi AI có đề xuất và mức chốt giữ nguyên mức đó.
 * - Mọi trường hợp khác là điều chỉnh (ADJUST_ESI) và cần ghi chú lâm sàng
 *   tối thiểu 10 ký tự -- kể cả ca AI chưa đủ dữ liệu để đề xuất.
 */

export type EsiLevel = 1 | 2 | 3 | 4 | 5;

export const ESI_LEVELS: readonly EsiLevel[] = [1, 2, 3, 4, 5];

export const MIN_ADJUST_NOTE_LENGTH = 10;
export const MIN_PARK_REASON_LENGTH = 10;

/**
 * Chữ của từng lý do được bảng số liệu tổng quan dùng lại nguyên văn
 * (SimpleNurseDashboard.tsx), nên đổi ở đây là phải đổi cả bên đó.
 */
export const REASON_OPTIONS: Record<SimpleDecisionType, { value: SimpleReasonCode; label: string }[]> = {
  CONFIRM_ESI: [{ value: "MATCHES_PROTOCOL", label: "Dữ liệu phù hợp với phác đồ đã tham chiếu" }],
  ADJUST_ESI: [
    { value: "ADDITIONAL_CLINICAL_JUDGMENT", label: "Nhận định lâm sàng bổ sung" },
    { value: "INSUFFICIENT_PATIENT_DATA", label: "Dữ liệu bệnh nhân cung cấp chưa đủ" },
    { value: "OTHER", label: "Lý do khác (ghi rõ trong ghi chú)" },
  ],
};

export function reasonLabel(code: SimpleReasonCode | null): string | null {
  if (!code) return null;
  for (const options of Object.values(REASON_OPTIONS)) {
    const match = options.find((option) => option.value === code);
    if (match) return match.label;
  }
  return code;
}

export function decisionTypeFor(aiEsi: EsiLevel | null, finalEsi: number | null): SimpleDecisionType {
  return aiEsi !== null && finalEsi === aiEsi ? "CONFIRM_ESI" : "ADJUST_ESI";
}

/**
 * Chiều của quyết định so với đề xuất của AI. Thang ESI ngược chiều con số
 * (1 là khẩn nhất), nên câu chữ nói thẳng chiều thay vì để người đọc tự suy.
 * Cùng cách gọi với bảng số liệu tổng quan.
 */
export function esiRelation(aiEsi: EsiLevel | null, finalEsi: number | null): string | null {
  if (aiEsi === null) {
    return finalEsi === null ? "AI chưa đề xuất mức nào, bạn chọn mức theo đánh giá của mình" : "AI chưa đề xuất mức nào";
  }
  if (finalEsi === null) return null;
  if (finalEsi === aiEsi) return "Giữ nguyên mức AI";
  return finalEsi < aiEsi ? "Chốt khẩn hơn AI" : "Chốt ít khẩn hơn AI";
}

const reasonCodeSchema = z.enum([
  "MATCHES_PROTOCOL",
  "ADDITIONAL_CLINICAL_JUDGMENT",
  "INSUFFICIENT_PATIENT_DATA",
  "OTHER",
]);

export function buildDecisionSchema(aiEsi: EsiLevel | null) {
  return z
    .object({
      final_esi: z.number().int().min(1).max(5).nullable(),
      reason_code: reasonCodeSchema,
      note: z.string().max(2000, "Ghi chú tối đa 2000 ký tự."),
    })
    .superRefine((values, ctx) => {
      if (values.final_esi === null) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["final_esi"],
          message: "Chọn một mức ESI trước khi chốt.",
        });
        return;
      }
      const decisionType = decisionTypeFor(aiEsi, values.final_esi);
      if (!REASON_OPTIONS[decisionType].some((option) => option.value === values.reason_code)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["reason_code"],
          message: "Chọn một lý do phù hợp với quyết định.",
        });
      }
      if (decisionType === "ADJUST_ESI" && values.note.trim().length < MIN_ADJUST_NOTE_LENGTH) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["note"],
          message: `Điều chỉnh ESI cần ghi chú lâm sàng ít nhất ${MIN_ADJUST_NOTE_LENGTH} ký tự.`,
        });
      }
    });
}

export type DecisionFormValues = z.infer<ReturnType<typeof buildDecisionSchema>>;

export const parkReasonSchema = z.object({
  reason: z
    .string()
    .trim()
    .min(MIN_PARK_REASON_LENGTH, `Lý do tạm gác cần ít nhất ${MIN_PARK_REASON_LENGTH} ký tự.`)
    .max(500, "Lý do tạm gác tối đa 500 ký tự."),
});

export type ParkReasonValues = z.infer<typeof parkReasonSchema>;
