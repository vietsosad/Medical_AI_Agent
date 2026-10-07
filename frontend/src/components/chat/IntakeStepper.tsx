"use client";

import type { IntentType, WorkflowPhase } from "@/types/triage-chat";
import { Activity, CheckCircle2, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

interface IntakeStepperProps {
  phase?: WorkflowPhase | null;
  intent?: IntentType | null;
  isProcessing?: boolean;
}

const STEPS = [
  { title: "Kiểm tra an toàn", description: "Sàng lọc dấu hiệu khẩn cấp" },
  { title: "Thu thập thông tin", description: "Làm rõ lời khai của bạn" },
  { title: "Bạn xác nhận", description: "Kiểm tra, sửa hoặc bổ sung" },
  { title: "AI phân loại", description: "Đối chiếu phác đồ có nguồn" },
  { title: "Nhân viên y tế duyệt", description: "Xác nhận hướng xử trí" },
] as const;

const PHASE_STEP: Partial<Record<WorkflowPhase, number>> = {
  SAFETY_CHECK: 1,
  INTENT_CLASSIFICATION: 2,
  INTAKE_EXTRACTION: 2,
  CLARIFICATION: 2,
  REASSESSMENT: 2,
  PATIENT_CONFIRMATION: 3,
  RETRIEVAL: 4,
  REASONING: 4,
  HANDOFF: 5,
  COMPLETE: 5,
};

export function IntakeStepper({ phase, intent, isProcessing = false }: IntakeStepperProps) {
  const currentStep = phase ? PHASE_STEP[phase] ?? 1 : 1;
  const nonTriage = intent && ["GREETING_HELP", "OUT_OF_SCOPE", "UNCLEAR"].includes(intent);
  if (nonTriage) {
    return (
      <section
        className="w-full rounded-2xl border border-border bg-card p-6"
        aria-label="Trạng thái hỗ trợ"
      >
        <div className="flex items-center gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-sky-700">
            <ShieldCheck className="size-6" aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-base font-bold text-slate-950 dark:text-slate-50">Hỗ trợ đúng phạm vi</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              Hội thoại này không làm tăng bước khai thác triệu chứng và không tạo đề xuất ESI.
            </p>
          </div>
        </div>
      </section>
    );
  }

  const displayedStep = currentStep;
  const statusLabel = isProcessing
    ? "Đang xử lý"
    : phase === "REASSESSMENT"
      ? "Đang đánh giá lại"
    : phase === "PATIENT_CONFIRMATION"
      ? "Chờ bạn xác nhận"
      : phase === "HANDOFF"
        ? "Chờ thẩm định"
        : phase === "COMPLETE"
          ? "Đã hoàn tất"
        : "Sẵn sàng";

  return (
    <section className="w-full rounded-2xl border border-border bg-card p-6" aria-label="Tiến trình xử lý">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-slate-100">
          <ShieldCheck className="size-4 text-sky-700" aria-hidden="true" />
          {nonTriage ? "Hỗ trợ đúng phạm vi" : "Tiến trình từ thu thập đến thẩm định"}
        </span>
        <span className="rounded-lg bg-muted px-2 py-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
          {statusLabel}
        </span>
      </div>

      <div className="mb-4 grid grid-cols-5 gap-2" aria-hidden="true">
        {STEPS.map((step, index) => (
          <span
            key={step.title}
            className={cn(
              "h-2 rounded-full transition-colors",
              index + 1 <= displayedStep ? "bg-sky-600" : "bg-slate-200 dark:bg-slate-700",
            )}
          />
        ))}
      </div>

      <ol className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
        {STEPS.map((step, index) => {
          const number = index + 1;
          const isCurrent = currentStep === number;
          const isComplete = currentStep > number;
          return (
            <li
              key={step.title}
              aria-current={isCurrent ? "step" : undefined}
              className={cn(
                "flex min-h-20 items-start gap-2 rounded-xl border p-4",
                isCurrent ? "border-sky-600 bg-sky-50 text-sky-950" : "border-border bg-background text-slate-600 dark:text-slate-300",
              )}
            >
              {isComplete ? (
                <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-600" aria-hidden="true" />
              ) : isCurrent && isProcessing ? (
                <Activity className="mt-0.5 size-5 shrink-0 animate-pulse text-sky-700" aria-hidden="true" />
              ) : (
                <span className="flex size-5 shrink-0 items-center justify-center rounded-md bg-card text-sm font-bold">{number}</span>
              )}
              <span className="min-w-0">
                <span className="block text-sm font-bold leading-5">{step.title}</span>
                <span className="block text-sm leading-5 text-slate-600 dark:text-slate-300">{step.description}</span>
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
