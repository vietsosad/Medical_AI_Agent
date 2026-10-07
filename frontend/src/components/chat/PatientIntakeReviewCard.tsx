"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, CheckCircle2, ClipboardCheck, PencilLine, ShieldCheck } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import type { IntakeSummary } from "@/types/triage-chat";

const reviewSchema = z.object({
  correction: z.string().max(2000, "Nội dung bổ sung tối đa 2.000 ký tự."),
  acknowledged: z.boolean().refine((value) => value, {
    message: "Bạn cần xác nhận đã kiểm tra thông tin trước khi bắt đầu phân loại.",
  }),
});

type ReviewFormValues = z.infer<typeof reviewSchema>;

interface PatientIntakeReviewCardProps {
  summary: IntakeSummary;
  isSubmitting: boolean;
  onConfirm: () => Promise<void>;
  onRequestChanges: (correction: string) => Promise<void>;
}

function formatList(items: string[]): string {
  return items.length > 0 ? items.join(", ") : "Chưa ghi nhận";
}

const vitalLabels: Record<string, string> = {
  blood_pressure: "Huyết áp",
  heart_rate: "Mạch",
  spo2: "SpO₂",
  temperature_c: "Nhiệt độ",
  respiratory_rate: "Nhịp thở",
  gcs: "GCS",
};

function formatVitals(vitals: Record<string, string | number> | undefined): string {
  if (!vitals || Object.keys(vitals).length === 0) {
    return "Chưa có số đo";
  }
  return Object.entries(vitals)
    .filter(([key]) => !["systolic_bp", "diastolic_bp"].includes(key))
    .map(([key, value]) => `${vitalLabels[key] || key}: ${value}`)
    .join("; ");
}

function formatEhrTimestamp(value: string | null | undefined): string {
  if (!value) return "Không có thời điểm cập nhật";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

export function PatientIntakeReviewCard({
  summary,
  isSubmitting,
  onConfirm,
  onRequestChanges,
}: PatientIntakeReviewCardProps) {
  const ehr = summary.ehr_snapshot;
  const ehrStatus =
    ehr?.confirmation_status === "CONFIRMED"
      ? "Đã được người bệnh xác nhận lại trong phiên"
      : ehr?.confirmation_status === "UPDATED_BY_PATIENT"
        ? "Người bệnh đã báo thay đổi; không tự ghi đè hồ sơ EHR"
        : ehr?.confirmation_status === "UNCERTAIN"
          ? "Người bệnh chưa chắc thông tin còn đúng"
          : "Chưa được xác nhận lại";
  const vitalStatus =
    summary.vital_signs_status === "PATIENT_REPORTED"
      ? "Do người bệnh cung cấp, cần nhân viên y tế đo lại"
      : summary.vital_signs_status === "UNAVAILABLE_CONFIRMED"
        ? "Người bệnh xác nhận chưa có số đo"
        : "Chưa xác minh";
  const {
    control,
    register,
    getValues,
    handleSubmit,
    resetField,
    setError,
    formState: { errors },
  } = useForm<ReviewFormValues>({
    resolver: zodResolver(reviewSchema),
    defaultValues: {
      correction: "",
      acknowledged: false,
    },
  });

  const summaryRows = [
    { label: "Triệu chứng chính", value: formatList(summary.chief_complaint) },
    { label: "Thời điểm bắt đầu", value: summary.onset_time || "Chưa ghi nhận" },
    {
      label: "Mức độ hiện tại",
      value: summary.severity_score == null ? "Chưa ghi nhận" : `${summary.severity_score}/10`,
    },
    { label: "Vị trí hoặc hướng lan", value: summary.radiation || "Chưa ghi nhận" },
    { label: "Dấu hiệu đi kèm", value: formatList(summary.associated_symptoms) },
    // A hedged symptom is not recorded as a finding, but the patient still
    // said it. This row is where they can confirm or deny it.
    {
      label: "Bạn có nhắc tới nhưng chưa chắc chắn",
      value: formatList(summary.uncertain_symptoms),
    },
    { label: "Phẫu thuật hoặc thủ thuật gần đây", value: summary.recent_procedure || "Chưa ghi nhận" },
    { label: "Sinh hiệu hiện có", value: formatVitals(summary.vital_signs) },
    { label: "Nguồn sinh hiệu", value: vitalStatus },
    { label: "Thiết bị / nơi đo", value: summary.vital_signs_source || "Chưa ghi nhận" },
    { label: "Thời điểm đo", value: summary.vital_signs_measured_at || "Chưa ghi nhận" },
    { label: "Thuốc đang dùng đã khai báo", value: formatList(summary.current_medication) },
    {
      label: "Tuổi / giới tính từ EHR",
      value: ehr
        ? `${ehr.age ?? "Chưa có"} tuổi · ${ehr.gender ?? "Chưa có"}`
        : "Chưa ghi nhận",
    },
    {
      label: "Thể chất từ EHR",
      value: ehr
        ? `${ehr.height_cm ?? "Chưa có"} cm · ${ehr.weight_kg ?? "Chưa có"} kg · BMI ${ehr.bmi ?? "Chưa có"}`
        : "Chưa ghi nhận",
    },
    { label: "Nhóm máu từ EHR", value: ehr?.blood_type || "Chưa ghi nhận" },
    { label: "Bệnh nền trong EHR", value: formatList(ehr?.chronic_conditions || []) },
    { label: "Dị ứng trong EHR", value: formatList(ehr?.allergies || []) },
    { label: "Thuốc hằng ngày trong EHR", value: formatList(ehr?.daily_medications || []) },
    { label: "Trạng thái xác nhận EHR", value: ehrStatus },
    { label: "EHR cập nhật lúc", value: formatEhrTimestamp(ehr?.updated_at) },
    ...(ehr?.patient_context_note
      ? [{ label: "Đính chính của người bệnh", value: ehr.patient_context_note }]
      : []),
  ] as const;

  const handleCorrection = async () => {
    const correction = getValues("correction").trim();
    if (correction.length < 3) {
      setError("correction", {
        type: "manual",
        message: "Hãy mô tả nội dung cần sửa hoặc bổ sung ít nhất 3 ký tự.",
      });
      return;
    }
    await onRequestChanges(correction);
    resetField("correction");
  };

  const handleConfirmation = handleSubmit(async () => {
    await onConfirm();
  });

  return (
    <section
      aria-labelledby="patient-intake-review-title"
      className="mx-auto w-full max-w-3xl overflow-hidden rounded-2xl border border-sky-200 bg-card shadow-sm"
    >
      <header className="flex items-start gap-4 bg-sky-50 p-6">
        <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-sky-600 text-white">
          <ClipboardCheck className="size-6" aria-hidden="true" />
        </span>
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 id="patient-intake-review-title" className="text-lg font-bold text-slate-950 dark:text-slate-50">
              Kiểm tra thông tin trước khi AI phân loại
            </h2>
            <span className="rounded-lg border border-amber-300 bg-amber-50 px-2 py-2 text-sm font-semibold text-amber-900">
              Chưa xác nhận
            </span>
          </div>
          <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">
            AI mới chỉ tổng hợp lời khai của bạn và chưa đưa ra mức ưu tiên. Hãy kiểm tra từng mục,
            sửa hoặc bổ sung nếu cần.
          </p>
        </div>
      </header>

      <div className="space-y-6 p-6">
        <dl className="divide-y divide-slate-200 border-y border-border">
          {summaryRows.map((row) => {
            const isMissing = row.value === "Chưa ghi nhận";
            return (
              <div key={row.label} className="grid gap-2 py-4 sm:grid-cols-[minmax(0,12rem)_1fr] sm:gap-4">
                <dt className="text-sm font-semibold text-slate-600 dark:text-slate-300">{row.label}</dt>
                <dd
                  className={cn(
                    "text-base font-medium leading-6 text-slate-950 dark:text-slate-50",
                    isMissing && "text-muted-foreground",
                  )}
                >
                  {row.value}
                </dd>
              </div>
            );
          })}
        </dl>

        <div className="space-y-2">
          <label htmlFor="intake-correction" className="flex items-center gap-2 text-base font-semibold text-foreground">
            <PencilLine className="size-5 text-sky-700" aria-hidden="true" />
            Có thông tin nào cần sửa hoặc bổ sung?
          </label>
          <textarea
            id="intake-correction"
            rows={3}
            disabled={isSubmitting}
            placeholder="Ví dụ: Mức đau hiện tại là 7/10, cơn đau lan ra vai trái và tôi đang dùng thuốc huyết áp..."
            aria-invalid={Boolean(errors.correction)}
            aria-describedby={errors.correction ? "intake-correction-error" : "intake-correction-help"}
            className="min-h-24 w-full resize-y rounded-xl border border-slate-300 bg-card p-4 text-base leading-6 text-slate-950 outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-sky-600 focus-visible:ring-2 focus-visible:ring-sky-600/20 disabled:cursor-not-allowed disabled:bg-muted dark:border-slate-700 dark:text-slate-50"
            {...register("correction")}
          />
          {errors.correction ? (
            <p id="intake-correction-error" role="alert" className="text-sm font-medium text-rose-700">
              {errors.correction.message}
            </p>
          ) : (
            <p id="intake-correction-help" className="text-sm text-slate-600 dark:text-slate-300">
              Nội dung bổ sung sẽ được AI ghi nhận lại và gửi cho bạn kiểm tra lần nữa.
            </p>
          )}
          <Button
            type="button"
            variant="outline"
            disabled={isSubmitting}
            onClick={handleCorrection}
            className="min-h-12 w-full border-slate-300 px-4 text-base font-semibold text-slate-800 focus-visible:ring-2 focus-visible:ring-sky-600 sm:w-auto dark:text-slate-100 dark:border-slate-700"
          >
            <PencilLine className="size-5" aria-hidden="true" />
            Gửi phần sửa hoặc bổ sung
          </Button>
        </div>

        <form onSubmit={handleConfirmation} className="space-y-4 border-t border-border pt-6">
          <Controller
            name="acknowledged"
            control={control}
            render={({ field }) => (
              <label
                htmlFor="intake-acknowledged"
                className="flex min-h-12 cursor-pointer items-start gap-4 rounded-xl bg-background p-4 text-sm leading-6 text-slate-800 focus-within:ring-2 focus-within:ring-sky-600 dark:text-slate-100"
              >
                <Checkbox
                  id="intake-acknowledged"
                  checked={field.value}
                  onCheckedChange={(checked) => field.onChange(checked === true)}
                  disabled={isSubmitting}
                  className="mt-0.5 size-6 border-slate-400 bg-card data-[state=checked]:border-sky-600 data-[state=checked]:bg-sky-600 data-[state=checked]:bg-none focus-visible:ring-sky-600 focus-visible:ring-offset-white"
                />
                <span>
                  Tôi đã kiểm tra và xác nhận thông tin trên đúng với tình trạng hiện tại của người
                  được khám.
                </span>
              </label>
            )}
          />
          {errors.acknowledged && (
            <p role="alert" className="text-sm font-medium text-rose-700">
              {errors.acknowledged.message}
            </p>
          )}

          <div className="flex items-start gap-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            <ShieldCheck className="mt-0.5 size-5 shrink-0 text-sky-700" aria-hidden="true" />
            <p>
              Sau xác nhận, AI mới đối chiếu phác đồ để đề xuất mức ưu tiên. Kết quả vẫn cần nhân
              viên y tế thẩm định và không thay thế chẩn đoán.
            </p>
          </div>

          <Button
            type="submit"
            disabled={isSubmitting}
            className="min-h-12 w-full bg-sky-600 px-6 text-base font-bold text-white hover:bg-sky-700 focus-visible:ring-2 focus-visible:ring-sky-600"
          >
            {isSubmitting ? (
              <>
                <span className="size-5 animate-spin rounded-full border-2 border-white/40 border-t-white" aria-hidden="true" />
                Đang bắt đầu phân loại
              </>
            ) : (
              <>
                <CheckCircle2 className="size-5" aria-hidden="true" />
                Xác nhận và bắt đầu phân loại
                <ArrowRight className="size-5" aria-hidden="true" />
              </>
            )}
          </Button>
        </form>
      </div>
    </section>
  );
}
