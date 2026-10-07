"use client";

import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  CircleHelp,
  ClipboardCheck,
  HeartPulse,
  Pill,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useEhrLite } from "@/hooks/queries/use-clinical-profile";
import { cn } from "@/lib/utils";
import type { EhrConfirmationSnapshot, OptionItem } from "@/types/triage-chat";

interface EhrConfirmationCardProps {
  snapshot?: EhrConfirmationSnapshot | null;
  options: OptionItem[];
  disabled: boolean;
  onSubmitAnswer: (answer: string | number, optionId?: string) => void;
}

interface OptionPresentation {
  Icon: LucideIcon;
  description: string;
  className: string;
  iconClassName: string;
}

function formatGender(value: string | null): string {
  const normalized = value?.trim().toUpperCase();
  if (normalized === "MALE") return "Nam";
  if (normalized === "FEMALE") return "Nữ";
  if (normalized === "OTHER") return "Khác";
  return "Chưa có";
}

function formatBloodType(value: string | null): string {
  const normalized = value?.trim().toUpperCase();
  if (!normalized || ["UNKNOWN", "UNSPECIFIED", "CHUA_RO"].includes(normalized)) {
    return "Chưa rõ";
  }
  return value?.trim() || "Chưa rõ";
}

function formatMeasure(value: number | null, unit: string): string {
  return value === null ? "Chưa có" : `${value} ${unit}`;
}

function calculateBmi(
  heightCm: number | null | undefined,
  weightKg: number | null | undefined,
): number | null {
  if (!heightCm || !weightKg) return null;
  return Number((weightKg / ((heightCm / 100) ** 2)).toFixed(1));
}

function formatList(items: string[]): string {
  const availableItems = items.map((item) => item.trim()).filter(Boolean);
  return availableItems.length > 0 ? availableItems.join(", ") : "Chưa ghi nhận";
}

function getOptionPresentation(optionId: string): OptionPresentation {
  if (optionId === "ehr_confirmed") {
    return {
      Icon: CheckCircle2,
      description: "Tiếp tục dùng dữ liệu này trong lượt phân loại.",
      className: "border-emerald-300 bg-emerald-50 text-emerald-950 hover:bg-emerald-100",
      iconClassName: "text-emerald-700",
    };
  }
  if (optionId === "ehr_changed") {
    return {
      Icon: RefreshCw,
      description: "Cho AI biết phần cần cập nhật cho ca hiện tại.",
      className: "border-amber-300 bg-amber-50 text-amber-950 hover:bg-amber-100",
      iconClassName: "text-amber-700",
    };
  }
  return {
    Icon: CircleHelp,
    description: "Đánh dấu để nhân viên y tế kiểm tra lại.",
    className: "border-slate-300 bg-white text-slate-900 hover:bg-slate-100 dark:border-slate-700",
    iconClassName: "text-slate-600 dark:text-slate-300",
  };
}

export function EhrConfirmationCard({
  snapshot,
  options,
  disabled,
  onSubmitAnswer,
}: EhrConfirmationCardProps) {
  const { data: currentEhr, isLoading } = useEhrLite(snapshot ? null : undefined);
  const resolvedSnapshot: EhrConfirmationSnapshot | null =
    snapshot ??
    (currentEhr
      ? {
          age: currentEhr.age ?? null,
          gender: currentEhr.gender ?? null,
          height_cm: currentEhr.height_cm ?? null,
          weight_kg: currentEhr.weight_kg ?? null,
          bmi: calculateBmi(currentEhr.height_cm, currentEhr.weight_kg),
          blood_type: currentEhr.blood_type ?? null,
          chronic_conditions: currentEhr.chronic_conditions,
          allergies: currentEhr.allergies.map((item) => item.name),
          daily_medications: currentEhr.current_medications.map((item) => item.name),
        }
      : null);

  return (
    <section
      aria-label="Xác nhận thông tin hồ sơ EHR"
      className="@container mt-4 space-y-4 border-y border-slate-200 bg-slate-50 px-4 py-4 text-slate-950 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
    >
      <header className="flex flex-col gap-4 @xl:flex-row @xl:items-start @xl:justify-between">
        <div className="flex min-w-0 items-start gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300">
            <ClipboardCheck className="size-6" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h3 className="text-base font-bold leading-6">
              Thông tin từ hồ sơ EHR
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              Đây là dữ liệu đang được dùng làm ngữ cảnh cho lượt khám này.
            </p>
          </div>
        </div>
        <span className="w-fit shrink-0 rounded-lg border border-amber-300 bg-amber-50 px-2 py-2 text-sm font-semibold text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200">
          Chờ bạn xác nhận
        </span>
      </header>

      {resolvedSnapshot ? (
        <dl className="grid grid-cols-1 gap-4 border-t border-slate-200 pt-4 dark:border-slate-700 @2xl:grid-cols-2">
          <div className="flex min-w-0 items-start gap-4">
            <Activity
              className="mt-2 size-5 shrink-0 text-sky-700 dark:text-sky-300"
              aria-hidden="true"
            />
            <div className="min-w-0">
              <dt className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                Thông tin cơ thể
              </dt>
              <dd className="mt-2 break-words text-base font-semibold leading-6">
                {resolvedSnapshot.age ?? "Chưa có"} tuổi · {formatGender(resolvedSnapshot.gender)}
              </dd>
              <dd className="mt-2 break-words text-sm leading-6 text-slate-700 dark:text-slate-300">
                {formatMeasure(resolvedSnapshot.height_cm, "cm")} ·{" "}
                {formatMeasure(resolvedSnapshot.weight_kg, "kg")} · BMI{" "}
                {resolvedSnapshot.bmi ?? "Chưa có"}
              </dd>
              <dd className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-300">
                Nhóm máu: {formatBloodType(resolvedSnapshot.blood_type)}
              </dd>
            </div>
          </div>

          <div className="flex min-w-0 items-start gap-4">
            <HeartPulse
              className="mt-2 size-5 shrink-0 text-amber-700 dark:text-amber-300"
              aria-hidden="true"
            />
            <div className="min-w-0">
              <dt className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                Bệnh nền
              </dt>
              <dd className="mt-2 break-words text-base font-semibold leading-6">
                {formatList(resolvedSnapshot.chronic_conditions)}
              </dd>
            </div>
          </div>

          <div className="flex min-w-0 items-start gap-4">
            <ShieldAlert
              className="mt-2 size-5 shrink-0 text-rose-700 dark:text-rose-300"
              aria-hidden="true"
            />
            <div className="min-w-0">
              <dt className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                Dị ứng
              </dt>
              <dd className="mt-2 break-words text-base font-semibold leading-6">
                {formatList(resolvedSnapshot.allergies)}
              </dd>
            </div>
          </div>

          <div className="flex min-w-0 items-start gap-4">
            <Pill
              className="mt-2 size-5 shrink-0 text-sky-700 dark:text-sky-300"
              aria-hidden="true"
            />
            <div className="min-w-0">
              <dt className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                Thuốc hằng ngày
              </dt>
              <dd className="mt-2 break-words text-base font-semibold leading-6">
                {formatList(resolvedSnapshot.daily_medications)}
              </dd>
            </div>
          </div>
        </dl>
      ) : (
        <div
          role="status"
          className="border-t border-slate-200 pt-4 text-sm leading-6 text-slate-600 dark:border-slate-700 dark:text-slate-300"
        >
          {isLoading
            ? "Đang tải thông tin EHR của người được khám..."
            : "Chưa tải được thông tin EHR. Nếu bạn không chắc, hãy chọn phương án cần nhân viên y tế kiểm tra lại."}
        </div>
      )}

      <div className="space-y-4 border-t border-slate-200 pt-4 dark:border-slate-700">
        <div className="flex items-start gap-4">
          <AlertCircle className="mt-2 size-5 shrink-0 text-sky-700 dark:text-sky-300" aria-hidden="true" />
          <p className="text-base font-semibold leading-6">
            Những thông tin này còn đúng với hiện tại không?
          </p>
        </div>

        <div className="grid grid-cols-1 gap-2" role="group" aria-label="Xác nhận hồ sơ EHR">
          {options.map((option) => {
            const presentation = getOptionPresentation(option.id);
            const Icon = presentation.Icon;
            return (
              <Button
                key={option.id}
                type="button"
                variant="outline"
                disabled={disabled}
                onClick={() => onSubmitAnswer(option.value, option.id)}
                className={cn(
                  "h-auto min-h-14 w-full justify-start gap-4 whitespace-normal rounded-xl p-4 text-left focus-visible:ring-2 focus-visible:ring-sky-600",
                  presentation.className,
                )}
              >
                <Icon
                  className={cn("size-6 shrink-0", presentation.iconClassName)}
                  aria-hidden="true"
                />
                <span className="min-w-0">
                  <span className="block text-base font-bold leading-6">{option.label}</span>
                  <span className="mt-2 block text-sm font-medium leading-6 opacity-80">
                    {presentation.description}
                  </span>
                </span>
              </Button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
