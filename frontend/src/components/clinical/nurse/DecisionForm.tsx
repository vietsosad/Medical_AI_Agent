"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowUpRight, CheckCircle2, SlidersHorizontal } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm, useWatch } from "react-hook-form";

import { Button } from "@/components/ui/button";
import {
  useRequestSpecialistReview,
  useSubmitTriageDecision,
} from "@/hooks/mutations/use-hitl-mutations";
import {
  triageDecisionFormSchema,
  type TriageDecisionFormValues,
} from "@/lib/validations/clinical-hitl.schema";
import { cn } from "@/lib/utils";
import type { EsiLevel } from "@/types/clinical-hitl";

const actionOptions = [
  {
    value: "CONFIRM_ESI" as const,
    label: "Xác nhận ESI đề xuất",
    description: "Dữ liệu và căn cứ phù hợp với mức AI đề xuất.",
    icon: CheckCircle2,
  },
  {
    value: "ADJUST_ESI" as const,
    label: "Điều chỉnh ESI",
    description: "Chọn mức mới và ghi rõ lý do lâm sàng.",
    icon: SlidersHorizontal,
  },
  {
    value: "REQUEST_SPECIALIST_REVIEW" as const,
    label: "Yêu cầu đánh giá chuyên sâu",
    description: "Đưa ca về hàng đợi để một nhân viên lâm sàng khác rà soát độc lập.",
    icon: ArrowUpRight,
  },
];

const reasonOptions = {
  CONFIRM_ESI: [{ value: "AI_EVIDENCE_MATCH", label: "Dữ liệu phù hợp căn cứ ESI" }],
  ADJUST_ESI: [
    { value: "CLINICAL_FINDING_CHANGED", label: "Ghi nhận lâm sàng mới" },
    { value: "RISK_FACTOR", label: "Yếu tố nguy cơ liên quan" },
    { value: "DATA_CORRECTION", label: "Điều chỉnh dữ liệu đầu vào" },
  ],
  REQUEST_SPECIALIST_REVIEW: [
    { value: "OUTSIDE_PROTOCOL", label: "Ngoài phạm vi giao thức" },
    { value: "CONFLICTING_DATA", label: "Dữ liệu mâu thuẫn" },
    { value: "SCOPE_LIMIT", label: "Cần năng lực chuyên môn khác" },
    { value: "NEEDS_MEDICAL_ASSESSMENT", label: "Cần đánh giá lâm sàng chuyên sâu" },
  ],
};

export function DecisionForm({
  caseId,
  caseVersion,
  aiEsi,
  canDecide,
  missingFields,
}: {
  caseId: string;
  caseVersion: number;
  aiEsi: EsiLevel | null;
  canDecide: boolean;
  missingFields: string[];
}) {
  const router = useRouter();
  const decision = useSubmitTriageDecision(caseId);
  const specialistReview = useRequestSpecialistReview(caseId);
  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors },
  } = useForm<TriageDecisionFormValues>({
    resolver: zodResolver(triageDecisionFormSchema),
    defaultValues: {
      action: canDecide ? "CONFIRM_ESI" : "REQUEST_SPECIALIST_REVIEW",
      final_esi: aiEsi ?? 1,
      reason_code: canDecide ? "AI_EVIDENCE_MATCH" : "NEEDS_MEDICAL_ASSESSMENT",
      note: "",
    },
  });
  const action = useWatch({ control, name: "action" });
  const pending = decision.isPending || specialistReview.isPending;
  const requestError = decision.error ?? specialistReview.error;

  const selectAction = (nextAction: TriageDecisionFormValues["action"]) => {
    setValue("action", nextAction, { shouldValidate: true });
    setValue("reason_code", reasonOptions[nextAction][0].value, { shouldValidate: true });
    if (nextAction === "CONFIRM_ESI" && aiEsi) setValue("final_esi", aiEsi);
  };

  const submit = handleSubmit((values) => {
    if (values.action === "REQUEST_SPECIALIST_REVIEW") {
      specialistReview.mutate(
        {
          case_version: caseVersion,
          reason_code: values.reason_code,
          note: values.note.trim(),
        },
        { onSuccess: () => router.push("/clinical/queue") },
      );
      return;
    }
    decision.mutate({
      case_version: caseVersion,
      decision_type: values.action,
      final_esi: values.action === "CONFIRM_ESI" && aiEsi ? aiEsi : (values.final_esi as EsiLevel),
      reason_code: values.reason_code,
      note: values.note.trim() || null,
    });
  });

  return (
    <form onSubmit={submit} className="space-y-6">
      {!canDecide && (
        <div className="border-l-4 border-amber-500 bg-amber-50 p-4 text-sm text-amber-950" role="alert">
          Chưa thể chốt ESI vì thiếu: {missingFields.join(", ")}. Bạn vẫn có thể yêu cầu đánh giá chuyên sâu.
        </div>
      )}

      <fieldset className="grid gap-4 lg:grid-cols-3">
        <legend className="sr-only">Chọn quyết định phân luồng</legend>
        {actionOptions.map((option) => {
          const Icon = option.icon;
          const disabled = !canDecide && option.value !== "REQUEST_SPECIALIST_REVIEW";
          return (
            <label
              key={option.value}
              className={cn(
                "flex min-h-32 cursor-pointer gap-4 rounded-lg border p-4",
                action === option.value ? "border-sky-600 bg-sky-50" : "border-border bg-card",
                disabled && "cursor-not-allowed opacity-50",
              )}
            >
              <input
                type="radio"
                value={option.value}
                disabled={disabled}
                checked={action === option.value}
                onChange={() => selectAction(option.value)}
                className="mt-2 size-4 accent-sky-700"
              />
              <span>
                <span className="flex items-center gap-2 text-base font-semibold text-slate-950 dark:text-slate-50">
                  <Icon className="size-5" aria-hidden="true" />
                  {option.label}
                </span>
                <span className="mt-2 block text-sm leading-6 text-slate-600 dark:text-slate-300">{option.description}</span>
              </span>
            </label>
          );
        })}
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2">
        {action === "ADJUST_ESI" && (
          <label className="text-sm font-medium text-slate-800 dark:text-slate-100">
            ESI sau điều chỉnh
            <select
              {...register("final_esi")}
              className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 bg-card px-4 text-base text-slate-950 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700 dark:text-slate-50"
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
            {...register("reason_code")}
            className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 bg-card px-4 text-sm text-slate-950 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700 dark:text-slate-50"
          >
            {reasonOptions[action].map((reason) => (
              <option key={reason.value} value={reason.value}>
                {reason.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="block text-sm font-medium text-slate-800 dark:text-slate-100">
        Ghi chú {action === "CONFIRM_ESI" ? "(không bắt buộc)" : "(bắt buộc)"}
        <textarea
          {...register("note")}
          rows={4}
          className="mt-2 w-full rounded-lg border border-slate-300 p-4 text-base leading-6 text-slate-950 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700 dark:text-slate-50"
          placeholder="Ghi nhận ngắn, khách quan; không chẩn đoán hoặc kê đơn."
        />
        {errors.note?.message && (
          <span className="mt-2 block text-sm text-rose-700" role="alert">
            {errors.note.message}
          </span>
        )}
      </label>

      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={pending}
          className="min-h-11 bg-sky-700 px-6 text-white hover:bg-sky-800"
        >
          {pending ? "Đang lưu..." : "Lưu quyết định phân luồng"}
        </Button>
      </div>
      {requestError && (
        <p className="text-sm text-rose-700" role="alert">
          {requestError.message}
        </p>
      )}
    </form>
  );
}
