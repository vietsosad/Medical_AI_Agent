"use client";

import { AlertCircle, Dna, HeartPulse, Pill, ShieldAlert, User } from "lucide-react";

import { useEhrLite } from "@/hooks/queries/use-clinical-profile";

function formatGender(gender: "MALE" | "FEMALE" | "OTHER" | null | undefined): string {
  if (gender === "MALE") return "Nam";
  if (gender === "FEMALE") return "Nữ";
  if (gender === "OTHER") return "Khác";
  return "Chưa có";
}

function calculateBmi(heightCm: number | null | undefined, weightKg: number | null | undefined): string {
  if (!heightCm || !weightKg) return "Chưa có";
  return (weightKg / ((heightCm / 100) ** 2)).toFixed(1);
}

function formatBloodType(value: string | null | undefined): string {
  const normalized = value?.trim().toUpperCase();
  if (!normalized || ["UNKNOWN", "UNSPECIFIED", "CHUA_RO"].includes(normalized)) {
    return "Chưa rõ";
  }
  return value?.trim() || "Chưa rõ";
}

export function VerifiedClinicalContextHeader({ profileId }: { profileId?: string | null }) {
  const { data: ehr, isLoading, isError } = useEhrLite(profileId);

  if (isLoading) {
    return (
      <div className="flex w-full animate-pulse flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-zinc-900 p-5">
        <div className="h-6 w-56 rounded-lg bg-slate-300 dark:bg-slate-800" />
        <div className="h-10 w-full rounded-lg bg-slate-200 dark:bg-slate-800 md:w-96" />
      </div>
    );
  }

  if (isError || !ehr) {
    return (
      <div className="flex w-full items-start gap-3.5 rounded-2xl border-2 border-amber-300/80 bg-amber-50/80 dark:bg-amber-950/70 dark:border-amber-700/80 p-4.5 text-sm font-medium leading-6 text-amber-950 dark:text-amber-200 shadow-sm">
        <ShieldAlert className="mt-0.5 size-5 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
        <span>
          Chưa đồng bộ được hồ sơ EHR của đúng người đang khám. AI sẽ không dùng dữ liệu hồ sơ
          khác để suy luận.
        </span>
      </div>
    );
  }

  const bmi = calculateBmi(ehr.height_cm, ehr.weight_kg);
  const conditions = ehr.chronic_conditions.length > 0
    ? ehr.chronic_conditions.join(", ")
    : "Chưa ghi nhận";
  const allergies = ehr.allergies.length > 0
    ? ehr.allergies.map((item) => item.name).join(", ")
    : "Chưa ghi nhận";
  const medications = ehr.current_medications.length > 0
    ? ehr.current_medications.map((item) => item.name).join(", ")
    : "Chưa ghi nhận";

  return (
    <section
      aria-labelledby="ehr-memory-title"
      className="@container w-full overflow-hidden rounded-2xl border-2 border-sky-100 dark:border-slate-800 bg-white dark:bg-zinc-900 p-5 text-slate-900 dark:text-slate-100 shadow-md transition-all duration-300"
    >
      <div className="space-y-4">
        <div className="flex min-w-0 items-start gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-sky-50 dark:bg-sky-950/80 text-sky-600 dark:text-sky-400 border border-sky-200 dark:border-sky-800 shadow-2xs">
            <Dna className="size-6 stroke-[2.5]" aria-hidden="true" />
          </span>
          <div className="min-w-0 space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 id="ehr-memory-title" className="text-base sm:text-lg font-black tracking-tight text-slate-950 dark:text-white">
                Hồ sơ đang được AI dùng làm ngữ cảnh
              </h2>
              <span className="rounded-xl border border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950/90 px-3 py-1 text-xs font-mono font-black text-emerald-800 dark:text-emerald-200 uppercase tracking-wide">
                Cần xác nhận lại trong phiên
              </span>
            </div>
            <p className="text-sm font-medium leading-relaxed text-slate-600 dark:text-slate-400">
              Dữ liệu này hỗ trợ đặt câu hỏi và đối chiếu nguy cơ; không tự tạo chẩn đoán hay tự
              thay thế số đo hiện tại.
            </p>
          </div>
        </div>

        <dl className="grid grid-cols-1 gap-4 border-t border-slate-200/80 dark:border-slate-800 pt-4 text-sm @2xl:grid-cols-2">
          <div className="flex min-w-0 items-start gap-3.5 rounded-xl bg-slate-50/80 dark:bg-zinc-800/50 p-3.5 border border-slate-200/60 dark:border-slate-800">
            <User className="mt-1 size-5 shrink-0 text-sky-600 dark:text-sky-400 stroke-[2.5]" aria-hidden="true" />
            <div className="min-w-0">
              <dt className="text-xs font-mono font-bold tracking-wider text-slate-500 dark:text-slate-400 uppercase">Nhân khẩu học</dt>
              <dd className="mt-1 break-words text-base font-extrabold leading-6 text-slate-950 dark:text-white">
                {ehr.age ?? "Chưa có"} tuổi · {formatGender(ehr.gender)}
              </dd>
            </div>
          </div>
          <div className="flex min-w-0 items-start gap-3.5 rounded-xl bg-slate-50/80 dark:bg-zinc-800/50 p-3.5 border border-slate-200/60 dark:border-slate-800">
            <HeartPulse className="mt-1 size-5 shrink-0 text-sky-600 dark:text-sky-400 stroke-[2.5]" aria-hidden="true" />
            <div className="min-w-0">
              <dt className="text-xs font-mono font-bold tracking-wider text-slate-500 dark:text-slate-400 uppercase">Thể chất / nhóm máu</dt>
              <dd className="mt-1 break-words text-base font-extrabold leading-6 text-slate-950 dark:text-white">
                {ehr.height_cm ?? "Chưa có"} cm · {ehr.weight_kg ?? "Chưa có"} kg · BMI {bmi}
              </dd>
              <dd className="mt-1 text-sm font-semibold text-slate-600 dark:text-slate-300">
                Nhóm máu: <span className="font-mono text-sky-700 dark:text-sky-300">{formatBloodType(ehr.blood_type)}</span>
              </dd>
            </div>
          </div>
          <div className="flex min-w-0 items-start gap-3.5 rounded-xl bg-amber-50/60 dark:bg-amber-950/40 p-3.5 border border-amber-200/80 dark:border-amber-800/60">
            <AlertCircle className="mt-1 size-5 shrink-0 text-amber-600 dark:text-amber-400 stroke-[2.5]" aria-hidden="true" />
            <div className="min-w-0">
              <dt className="text-xs font-mono font-bold tracking-wider text-amber-800 dark:text-amber-300 uppercase">Bệnh nền</dt>
              <dd className="mt-1 break-words text-base font-extrabold leading-6 text-slate-950 dark:text-white">{conditions}</dd>
            </div>
          </div>
          <div className="flex min-w-0 items-start gap-3.5 rounded-xl bg-rose-50/60 dark:bg-rose-950/40 p-3.5 border border-rose-200/80 dark:border-rose-800/60">
            <ShieldAlert className="mt-1 size-5 shrink-0 text-rose-600 dark:text-rose-400 stroke-[2.5]" aria-hidden="true" />
            <div className="min-w-0">
              <dt className="text-xs font-mono font-bold tracking-wider text-rose-800 dark:text-rose-300 uppercase">Dị ứng</dt>
              <dd className="mt-1 break-words text-base font-extrabold leading-6 text-slate-950 dark:text-white">{allergies}</dd>
            </div>
          </div>
          <div className="flex min-w-0 items-start gap-3.5 rounded-xl bg-slate-50/80 dark:bg-zinc-800/50 p-3.5 border border-slate-200/60 dark:border-slate-800 @2xl:col-span-2">
            <Pill className="mt-1 size-5 shrink-0 text-sky-600 dark:text-sky-400 stroke-[2.5]" aria-hidden="true" />
            <div className="min-w-0">
              <dt className="text-xs font-mono font-bold tracking-wider text-slate-500 dark:text-slate-400 uppercase">Thuốc hằng ngày</dt>
              <dd className="mt-1 break-words text-base font-extrabold leading-6 text-slate-950 dark:text-white">{medications}</dd>
            </div>
          </div>
        </dl>
      </div>
    </section>
  );
}

