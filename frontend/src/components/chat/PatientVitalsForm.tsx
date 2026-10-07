"use client";

import { CheckCircle2, CircleSlash2, Clock3, Gauge, Send } from "lucide-react";
import { useId } from "react";
import { useForm, useWatch } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { VitalFormField, VitalFormFieldId } from "@/types/triage-chat";

type MeasurementSource = "" | "HOME_DEVICE" | "HEALTH_FACILITY" | "UNKNOWN";

interface PatientVitalsFormValues extends Record<VitalFormFieldId, string> {
  availability: "AVAILABLE" | "UNAVAILABLE" | null;
  source: MeasurementSource;
  measured_at: string;
}

const SOURCE_LABELS: Record<Exclude<MeasurementSource, "">, string> = {
  HOME_DEVICE: "Thiết bị tại nhà",
  HEALTH_FACILITY: "Cơ sở y tế",
  UNKNOWN: "Không nhớ rõ nguồn",
};

const EMPTY_MEASUREMENTS: Record<VitalFormFieldId, string> = {
  heart_rate: "",
  blood_pressure: "",
  respiratory_rate: "",
  spo2: "",
  temperature_c: "",
  gcs: "",
};

function validateVitalValue(field: VitalFormField, rawValue: string): true | string {
  const value = rawValue.trim();
  if (!value || field.inputMode === "text") return true;

  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return `${field.label} phải là một số hợp lệ.`;
  if (field.inputMode === "numeric" && !Number.isInteger(numericValue)) {
    return `${field.label} phải là số nguyên.`;
  }
  if (field.min !== undefined && numericValue < field.min) {
    return `${field.label} không được nhỏ hơn ${field.min}.`;
  }
  if (field.max !== undefined && numericValue > field.max) {
    return `${field.label} không được lớn hơn ${field.max}.`;
  }
  if (field.step !== undefined) {
    const stepBase = field.min ?? 0;
    const steps = (numericValue - stepBase) / field.step;
    if (Math.abs(steps - Math.round(steps)) > 1e-8) {
      return `${field.label} phải theo bước ${field.step}.`;
    }
  }
  return true;
}

interface PatientVitalsFormProps {
  fields: VitalFormField[];
  disabled: boolean;
  onSubmitAnswer: (answer: string) => void;
}

export function PatientVitalsForm({
  fields,
  disabled,
  onSubmitAnswer,
}: PatientVitalsFormProps) {
  const formId = useId();
  const {
    control,
    register,
    setValue,
    setError,
    clearErrors,
    handleSubmit,
    formState: { errors },
  } = useForm<PatientVitalsFormValues>({
    defaultValues: {
      availability: null,
      ...EMPTY_MEASUREMENTS,
      source: "",
      measured_at: "",
    },
  });
  const availability = useWatch({ control, name: "availability" });

  const selectAvailability = (value: "AVAILABLE" | "UNAVAILABLE") => {
    clearErrors("root.measurements");
    setValue("availability", value);
  };

  const submit = handleSubmit((values) => {
    if (values.availability === "UNAVAILABLE") {
      onSubmitAnswer("Chưa đo, không có số đo");
      return;
    }
    if (values.availability !== "AVAILABLE") return;

    const measurements = fields.flatMap((field) => {
      const value = values[field.id].trim();
      return value ? [`${field.label}: ${value} ${field.unit}`] : [];
    });
    if (measurements.length === 0) {
      setError("root.measurements", {
        type: "manual",
        message: "Hãy nhập ít nhất một chỉ số bạn đang có.",
      });
      return;
    }

    const supplementalDetails = [
      values.source ? `Nguồn đo: ${SOURCE_LABELS[values.source]}` : null,
      values.measured_at ? `Thời điểm đo: ${values.measured_at}` : null,
    ].filter((item): item is string => Boolean(item));

    onSubmitAnswer([
      "Đã có số đo sinh hiệu",
      ...supplementalDetails,
      ...measurements,
    ].join("; "));
  });

  return (
    <form
      onSubmit={submit}
      noValidate
      className="mt-4 space-y-6"
      aria-label="Biểu mẫu sinh hiệu người bệnh"
    >
      <fieldset className="grid gap-4 sm:grid-cols-2">
        <legend className="sr-only">Bạn có số đo sinh hiệu hay chưa?</legend>
        <button
          type="button"
          disabled={disabled}
          aria-pressed={availability === "AVAILABLE"}
          onClick={() => selectAvailability("AVAILABLE")}
          className={cn(
            "flex min-h-12 items-center gap-4 rounded-xl border-2 p-4 text-left text-base font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 disabled:cursor-not-allowed disabled:opacity-60",
            availability === "AVAILABLE"
              ? "border-sky-600 bg-sky-50 text-sky-950"
              : "border-border bg-card text-slate-800 hover:border-sky-400 dark:text-slate-100",
          )}
        >
          <CheckCircle2 className="size-6 shrink-0 text-sky-700" aria-hidden="true" />
          Đã có số đo
        </button>
        <button
          type="button"
          disabled={disabled}
          aria-pressed={availability === "UNAVAILABLE"}
          onClick={() => selectAvailability("UNAVAILABLE")}
          className={cn(
            "flex min-h-12 items-center gap-4 rounded-xl border-2 p-4 text-left text-base font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 disabled:cursor-not-allowed disabled:opacity-60",
            availability === "UNAVAILABLE"
              ? "border-slate-700 bg-muted text-slate-950 dark:text-slate-50"
              : "border-border bg-card text-slate-800 hover:border-slate-400 dark:text-slate-100",
          )}
        >
          <CircleSlash2 className="size-6 shrink-0 text-slate-700 dark:text-slate-200" aria-hidden="true" />
          Chưa có số đo
        </button>
      </fieldset>

      {availability === "AVAILABLE" && (
        <div className="space-y-6 border-t border-border pt-6">
          <div className="flex items-start gap-4 text-sm leading-6 text-slate-700 dark:text-slate-200">
            <Gauge className="mt-0.5 size-5 shrink-0 text-sky-700" aria-hidden="true" />
            <p>
              Chỉ nhập số bạn thực sự nhìn thấy trên máy hoặc phiếu đo. Nhân viên y tế cần xác
              minh lại các số đo này.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {fields.map((field) => {
              const inputId = `${formId}-${field.id}`;
              const errorId = `${inputId}-error`;
              const fieldError = errors[field.id]?.message;
              return (
                <label
                  key={field.id}
                  htmlFor={inputId}
                  className="space-y-2 text-sm font-semibold text-slate-800 dark:text-slate-100"
                >
                  <span>{field.label}</span>
                  <span className="flex min-h-12 items-center rounded-xl border border-slate-300 bg-card px-4 focus-within:border-sky-600 focus-within:ring-2 focus-within:ring-sky-600/20 dark:border-slate-700">
                    <input
                      id={inputId}
                      type={field.inputMode === "text" ? "text" : "number"}
                      inputMode={field.inputMode}
                      min={field.min}
                      max={field.max}
                      step={field.step ?? (field.inputMode === "decimal" ? "any" : undefined)}
                      disabled={disabled}
                      placeholder={field.placeholder}
                      aria-invalid={Boolean(fieldError)}
                      aria-describedby={fieldError ? errorId : undefined}
                      className="min-w-0 flex-1 bg-transparent py-2 text-base font-medium text-slate-950 outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:text-muted-foreground dark:text-slate-50"
                      {...register(field.id, {
                        validate: (value) => validateVitalValue(field, value),
                      })}
                      onInput={() => clearErrors("root.measurements")}
                    />
                    <span className="ml-2 shrink-0 text-sm font-medium text-slate-600 dark:text-slate-300">
                      {field.unit}
                    </span>
                  </span>
                  {fieldError && (
                    <span id={errorId} role="alert" className="block text-sm font-medium text-rose-700">
                      {fieldError}
                    </span>
                  )}
                </label>
              );
            })}
          </div>

          {errors.root?.measurements?.message && (
            <p role="alert" className="text-sm font-medium text-rose-700">
              {errors.root.measurements.message}
            </p>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
              <span>Nguồn số đo (không bắt buộc)</span>
              <select
                disabled={disabled}
                className="min-h-12 w-full rounded-xl border border-slate-300 bg-card px-4 text-base text-slate-950 outline-none focus-visible:border-sky-600 focus-visible:ring-2 focus-visible:ring-sky-600/20 disabled:cursor-not-allowed disabled:text-muted-foreground dark:border-slate-700 dark:text-slate-50"
                {...register("source")}
              >
                <option value="">Không cung cấp</option>
                <option value="HOME_DEVICE">Thiết bị tại nhà</option>
                <option value="HEALTH_FACILITY">Cơ sở y tế</option>
                <option value="UNKNOWN">Không nhớ rõ nguồn</option>
              </select>
            </label>
            <label className="space-y-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
              <span>Thời điểm đo (không bắt buộc)</span>
              <span className="relative block">
                <Clock3
                  className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted-foreground"
                  aria-hidden="true"
                />
                <input
                  type="datetime-local"
                  disabled={disabled}
                  className="min-h-12 w-full rounded-xl border border-slate-300 bg-card pl-12 pr-4 text-base text-slate-950 outline-none focus-visible:border-sky-600 focus-visible:ring-2 focus-visible:ring-sky-600/20 disabled:cursor-not-allowed disabled:text-muted-foreground dark:border-slate-700 dark:text-slate-50"
                  {...register("measured_at")}
                />
              </span>
            </label>
          </div>
        </div>
      )}

      {availability && (
        <Button
          type="submit"
          disabled={disabled}
          className="min-h-12 w-full bg-sky-600 px-6 text-base font-bold text-white hover:bg-sky-700 focus-visible:ring-2 focus-visible:ring-sky-600"
        >
          <Send className="size-5" aria-hidden="true" />
          {availability === "AVAILABLE" ? "Gửi số đo" : "Xác nhận chưa có số đo"}
        </Button>
      )}
    </form>
  );
}
