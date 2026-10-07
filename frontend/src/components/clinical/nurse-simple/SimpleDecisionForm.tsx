"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useSubmitSimpleDecision } from "@/queries/useSimpleNurseQueries";
import type { SimpleDecisionType, SimpleReasonCode } from "@/types/simple-nurse";

/**
 * Trimmed version of `@/components/clinical/nurse/DecisionForm.tsx`: only
 * CONFIRM_ESI / ADJUST_ESI (no REQUEST_SPECIALIST_REVIEW -- simple_agent has
 * no specialist workflow). Submitting closes the case directly
 * (`review_status -> HANDED_OFF`) instead of a separate handoff step -- see
 * the plan's "Đơn giản hóa có chủ đích" section.
 */

const REASON_OPTIONS: Record<SimpleDecisionType, { value: SimpleReasonCode; label: string }[]> = {
  CONFIRM_ESI: [{ value: "MATCHES_PROTOCOL", label: "Dữ liệu phù hợp với phác đồ đã tham chiếu" }],
  ADJUST_ESI: [
    { value: "ADDITIONAL_CLINICAL_JUDGMENT", label: "Nhận định lâm sàng bổ sung" },
    { value: "INSUFFICIENT_PATIENT_DATA", label: "Dữ liệu bệnh nhân cung cấp chưa đủ" },
    { value: "OTHER", label: "Lý do khác (ghi rõ trong ghi chú)" },
  ],
};

export function SimpleDecisionForm({
  sessionId,
  caseVersion,
  aiEsi,
}: {
  sessionId: string;
  caseVersion: number;
  aiEsi: 1 | 2 | 3 | 4 | 5 | null;
}) {
  const router = useRouter();
  const decision = useSubmitSimpleDecision(sessionId);
  const [decisionType, setDecisionType] = useState<SimpleDecisionType>(aiEsi ? "CONFIRM_ESI" : "ADJUST_ESI");
  const [finalEsi, setFinalEsi] = useState<number>(aiEsi ?? 3);
  const [reasonCode, setReasonCode] = useState<SimpleReasonCode>(
    aiEsi ? "MATCHES_PROTOCOL" : "ADDITIONAL_CLINICAL_JUDGMENT",
  );
  const [note, setNote] = useState("");

  const selectDecisionType = (next: SimpleDecisionType) => {
    setDecisionType(next);
    setReasonCode(REASON_OPTIONS[next][0].value);
    if (next === "CONFIRM_ESI" && aiEsi) setFinalEsi(aiEsi);
  };

  const noteRequired = decisionType === "ADJUST_ESI";
  const noteValid = !noteRequired || note.trim().length >= 10;

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!noteValid) return;
    decision.mutate(
      {
        version: caseVersion,
        decision_type: decisionType,
        final_esi: decisionType === "CONFIRM_ESI" && aiEsi ? aiEsi : finalEsi,
        reason_code: reasonCode,
        note: note.trim() || null,
      },
      { onSuccess: () => router.push("/clinical/queue-pilot") },
    );
  };

  return (
    <form onSubmit={submit} className="space-y-6">
      <fieldset className="grid gap-4 sm:grid-cols-2">
        <legend className="sr-only">Chọn quyết định phân luồng</legend>
        <label
          className={cn(
            "glow-soft glow-sky flex min-h-24 cursor-pointer gap-3 rounded-xl border p-4",
            decisionType === "CONFIRM_ESI"
              ? "border-sky-600 bg-sky-50 shadow-[0_0_0_1px_rgb(2_132_199/0.5)]"
              : "border-border bg-card hover:border-sky-300",
            aiEsi === null && "cursor-not-allowed opacity-50",
          )}
        >
          <input
            type="radio"
            checked={decisionType === "CONFIRM_ESI"}
            disabled={aiEsi === null}
            onChange={() => selectDecisionType("CONFIRM_ESI")}
            className="mt-1 size-4 accent-sky-700"
          />
          <span>
            <span className="flex items-center gap-2 text-base font-semibold text-slate-950 dark:text-slate-50">
              <CheckCircle2
                className={cn(
                  "size-5 transition-transform duration-300 ease-out",
                  decisionType === "CONFIRM_ESI" && "scale-110 text-sky-700 motion-reduce:scale-100",
                )}
                aria-hidden="true"
              />
              Xác nhận ESI đề xuất
            </span>
            <span className="mt-1 block text-sm leading-6 text-slate-600 dark:text-slate-300">
              {aiEsi ? `Giữ nguyên mức AI đề xuất: ESI ${aiEsi}.` : "AI chưa đề xuất mức ESI nào để xác nhận."}
            </span>
          </span>
        </label>

        <label
          className={cn(
            "glow-soft glow-sky flex min-h-24 cursor-pointer gap-3 rounded-xl border p-4",
            decisionType === "ADJUST_ESI"
              ? "border-sky-600 bg-sky-50 shadow-[0_0_0_1px_rgb(2_132_199/0.5)]"
              : "border-border bg-card hover:border-sky-300",
          )}
        >
          <input
            type="radio"
            checked={decisionType === "ADJUST_ESI"}
            onChange={() => selectDecisionType("ADJUST_ESI")}
            className="mt-1 size-4 accent-sky-700"
          />
          <span>
            <span className="flex items-center gap-2 text-base font-semibold text-slate-950 dark:text-slate-50">
              <SlidersHorizontal
                className={cn(
                  "size-5 transition-transform duration-300 ease-out",
                  decisionType === "ADJUST_ESI" && "scale-110 text-sky-700 motion-reduce:scale-100",
                )}
                aria-hidden="true"
              />
              Điều chỉnh ESI
            </span>
            <span className="mt-1 block text-sm leading-6 text-slate-600 dark:text-slate-300">Chọn mức mới và ghi rõ lý do lâm sàng.</span>
          </span>
        </label>
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2">
        {decisionType === "ADJUST_ESI" && (
          <label className="rise-in text-sm font-medium text-slate-800 dark:text-slate-100">
            ESI sau điều chỉnh
            <select
              value={finalEsi}
              onChange={(e) => setFinalEsi(Number(e.target.value))}
              className="glow-soft glow-sky mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-card px-4 text-base text-slate-950 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700 dark:text-slate-50"
            >
              {[1, 2, 3, 4, 5].map((esi) => (
                <option key={esi} value={esi}>
                  ESI {esi}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="text-sm font-medium text-slate-800 dark:text-slate-100">
          Lý do
          <select
            value={reasonCode}
            onChange={(e) => setReasonCode(e.target.value as SimpleReasonCode)}
            className="glow-soft glow-sky mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-card px-4 text-sm text-slate-950 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700 dark:text-slate-50"
          >
            {REASON_OPTIONS[decisionType].map((reason) => (
              <option key={reason.value} value={reason.value}>
                {reason.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="block text-sm font-medium text-slate-800 dark:text-slate-100">
        Ghi chú {noteRequired ? "(bắt buộc, tối thiểu 10 ký tự)" : "(không bắt buộc)"}
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={4}
          className="glow-soft glow-sky mt-2 w-full rounded-xl border border-slate-300 bg-card p-4 text-base leading-6 text-slate-950 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700 dark:text-slate-50"
          placeholder="Ghi nhận ngắn, khách quan; không chẩn đoán hoặc kê đơn."
        />
        {noteRequired && !noteValid && note.length > 0 && (
          <span className="mt-2 block text-sm text-rose-700" role="alert">
            Cần ít nhất 10 ký tự.
          </span>
        )}
      </label>

      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={decision.isPending || !noteValid}
          className="glow-soft glow-sky min-h-11 border border-sky-700 bg-sky-700 px-6 text-white hover:bg-sky-800"
        >
          {decision.isPending ? "Đang lưu..." : "Lưu quyết định và đóng ca"}
        </Button>
      </div>
      {decision.error && (
        <p className="text-sm text-rose-700" role="alert">
          {decision.error.message}
        </p>
      )}
    </form>
  );
}
