"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Save } from "lucide-react";
import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { useUpdateObservations } from "@/hooks/mutations/use-hitl-mutations";
import {
  observationsFormSchema,
  type ObservationsFormValues,
} from "@/lib/validations/clinical-hitl.schema";
import type {
  ClinicalObservationDTO,
  ClinicalObservationInputDTO,
  ObservationKind,
} from "@/types/clinical-hitl";

const observationDefinitions: Array<{ kind: ObservationKind; label: string; unit: string }> = [
  { kind: "HEART_RATE", label: "Mạch", unit: "lần/phút" },
  { kind: "BLOOD_PRESSURE", label: "Huyết áp", unit: "mmHg" },
  { kind: "RESPIRATORY_RATE", label: "Nhịp thở", unit: "lần/phút" },
  { kind: "SPO2", label: "SpO₂", unit: "%" },
  { kind: "TEMPERATURE", label: "Nhiệt độ", unit: "°C" },
  { kind: "CONSCIOUSNESS", label: "Tri giác", unit: "GCS" },
];

function toLocalDateTime(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function buildDefaults(observations: ClinicalObservationDTO[]): ObservationsFormValues {
  const byKind = new Map(observations.map((item) => [item.kind, item]));
  return {
    observations: observationDefinitions.map((definition) => {
      const existing = byKind.get(definition.kind);
      return {
        kind: definition.kind,
        value: existing?.value ?? "",
        unit: existing?.unit ?? definition.unit,
        availability: existing?.availability ?? "NOT_MEASURED",
        source: existing?.source ?? "NURSE_MEASURED",
        measured_at: toLocalDateTime(existing?.measured_at ?? null),
      };
    }),
  };
}

export function ObservationForm({
  caseId,
  caseVersion,
  observations,
}: {
  caseId: string;
  caseVersion: number;
  observations: ClinicalObservationDTO[];
}) {
  const mutation = useUpdateObservations(caseId);
  const {
    control,
    register,
    reset,
    handleSubmit,
    formState: { errors, isDirty },
  } = useForm<ObservationsFormValues>({
    resolver: zodResolver(observationsFormSchema),
    defaultValues: buildDefaults(observations),
  });
  const values = useWatch({ control, name: "observations" });

  useEffect(() => {
    reset(buildDefaults(observations));
  }, [observations, reset]);

  const submit = handleSubmit((formValues) => {
    const payload: ClinicalObservationInputDTO[] = formValues.observations.map((item) => {
      if (item.availability !== "MEASURED") {
        return {
          kind: item.kind,
          value: null,
          unit: null,
          availability: item.availability,
          source: item.source,
          measured_at: null,
        };
      }
      return {
        kind: item.kind,
        value: item.value.trim(),
        unit: item.unit,
        availability: item.availability,
        source: item.source,
        measured_at: new Date(item.measured_at).toISOString(),
      };
    });
    mutation.mutate({ case_version: caseVersion, observations: payload });
  });

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-border text-slate-600 dark:text-slate-300">
              <th className="p-4 font-medium">Sinh hiệu</th>
              <th className="p-4 font-medium">Tình trạng</th>
              <th className="p-4 font-medium">Giá trị</th>
              <th className="p-4 font-medium">Nguồn</th>
              <th className="p-4 font-medium">Thời điểm đo</th>
            </tr>
          </thead>
          <tbody>
            {observationDefinitions.map((definition, index) => {
              const measured = values?.[index]?.availability === "MEASURED";
              return (
                <tr key={definition.kind} className="border-b border-slate-100 last:border-b-0">
                  <td className="p-4 text-base font-semibold text-slate-950 dark:text-slate-50">
                    {definition.label}
                    <input type="hidden" {...register(`observations.${index}.kind`)} />
                    <input type="hidden" {...register(`observations.${index}.unit`)} />
                  </td>
                  <td className="p-4">
                    <select
                      {...register(`observations.${index}.availability`)}
                      className="min-h-11 w-full rounded-lg border border-slate-300 bg-card px-2 text-sm text-foreground focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700"
                      aria-label={`Tình trạng dữ liệu ${definition.label}`}
                    >
                      <option value="MEASURED">Đã có số đo</option>
                      <option value="NOT_MEASURED">Chưa có số đo</option>
                      <option value="UNKNOWN">Không biết</option>
                      <option value="NOT_APPLICABLE">Không áp dụng</option>
                    </select>
                  </td>
                  <td className="p-4">
                    <div className="flex min-h-11 items-center gap-2">
                      <input
                        {...register(`observations.${index}.value`)}
                        disabled={!measured}
                        inputMode={definition.kind === "BLOOD_PRESSURE" ? "text" : "decimal"}
                        placeholder={measured ? "Nhập giá trị" : "Chưa có dữ liệu"}
                        className="min-h-11 min-w-28 rounded-lg border border-slate-300 px-2 text-sm text-slate-950 disabled:bg-muted dark:border-slate-700 dark:text-slate-50"
                        aria-label={`Giá trị ${definition.label}`}
                      />
                      <span className="whitespace-nowrap text-sm text-slate-600 dark:text-slate-300">{definition.unit}</span>
                    </div>
                    {errors.observations?.[index]?.value?.message && (
                      <p className="mt-2 text-sm text-rose-700" role="alert">
                        {errors.observations[index]?.value?.message}
                      </p>
                    )}
                  </td>
                  <td className="p-4">
                    <select
                      {...register(`observations.${index}.source`)}
                      className="min-h-11 w-full rounded-lg border border-slate-300 bg-card px-2 text-sm text-foreground focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700"
                      aria-label={`Nguồn ${definition.label}`}
                    >
                      <option value="NURSE_MEASURED">Điều dưỡng đo</option>
                      <option value="PATIENT_REPORTED">Bệnh nhân cung cấp</option>
                      <option value="DEVICE">Thiết bị</option>
                      <option value="UNKNOWN">Không rõ nguồn</option>
                    </select>
                  </td>
                  <td className="p-4">
                    <input
                      type="datetime-local"
                      {...register(`observations.${index}.measured_at`)}
                      disabled={!measured}
                      className="min-h-11 w-full rounded-lg border border-slate-300 px-2 text-sm text-slate-950 disabled:bg-muted dark:border-slate-700 dark:text-slate-50"
                      aria-label={`Thời điểm đo ${definition.label}`}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-slate-600 dark:text-slate-300">Không có giá trị nào được tự suy ra từ ESI.</p>
        <Button
          type="submit"
          disabled={!isDirty || mutation.isPending}
          variant="outline"
          className="min-h-11 border-sky-300 bg-card text-sky-800 hover:bg-sky-50"
        >
          <Save className="size-4" aria-hidden="true" />
          {mutation.isPending ? "Đang lưu..." : "Lưu dữ liệu đo"}
        </Button>
      </div>
      {mutation.isError && (
        <p className="text-sm text-rose-700" role="alert">
          {mutation.error.message}
        </p>
      )}
      {mutation.isSuccess && (
        <p className="text-sm text-emerald-700" role="status">
          {mutation.data.message}
        </p>
      )}
    </form>
  );
}
