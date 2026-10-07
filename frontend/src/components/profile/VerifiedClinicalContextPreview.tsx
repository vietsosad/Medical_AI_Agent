"use client";

import React from "react";
import { useWatch, type UseFormReturn } from "react-hook-form";
import { HeartPulse, Info, Pill, Stethoscope } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EhrLiteFormValues } from "@/schemas/clinical-profile.schema";

export interface VerifiedClinicalContextPreviewProps {
  form: UseFormReturn<EhrLiteFormValues>;
  className?: string;
}

const genderLabels = {
  MALE: "Nam",
  FEMALE: "Nữ",
  OTHER: "Khác",
} as const;

const allergyTypeLabels = {
  MEDICATION: "Thuốc",
  FOOD: "Thực phẩm",
  ENVIRONMENT: "Môi trường",
  OTHER: "Khác",
} as const;

const allergySeverityLabels = {
  HIGH: "Mức độ nặng",
  MEDIUM: "Mức độ vừa",
  LOW: "Mức độ nhẹ",
} as const;

/**
 * A patient-readable summary of the values currently entered in the profile.
 * This intentionally does not expose internal prompts, raw JSON, or automated
 * clinical conclusions.
 */
export const VerifiedClinicalContextPreview: React.FC<VerifiedClinicalContextPreviewProps> = ({
  form,
  className,
}) => {
  const values = useWatch({ control: form.control });
  const allergies = values?.allergies ?? [];
  const medications = values?.current_medications ?? [];
  const conditions = values?.chronic_conditions ?? [];

  const details = [
    { label: "Tuổi", value: values?.age ? `${values.age} tuổi` : "Chưa khai báo" },
    { label: "Giới tính", value: values?.gender ? genderLabels[values.gender] : "Chưa khai báo" },
    { label: "Chiều cao", value: values?.height_cm ? `${values.height_cm} cm` : "Chưa khai báo" },
    { label: "Cân nặng", value: values?.weight_kg ? `${values.weight_kg} kg` : "Chưa khai báo" },
    { label: "Nhóm máu", value: values?.blood_type && values.blood_type !== "UNKNOWN" ? values.blood_type : "Chưa rõ" },
  ];

  return (
    <section
      className={cn("rounded-3xl border border-sky-100 bg-card p-6 shadow-sm md:p-8", className)}
      aria-labelledby="profile-summary-title"
    >
      <header className="flex items-start gap-4 border-b border-slate-100 pb-6">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-sky-50 text-sky-700">
          <Stethoscope className="size-5" aria-hidden="true" />
        </span>
        <div>
          <h2 id="profile-summary-title" className="text-lg font-bold text-foreground">
            Tóm tắt thông tin đã khai báo
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
            Kiểm tra lại các thông tin dưới đây trước khi lưu hồ sơ.
          </p>
        </div>
      </header>

      <dl className="grid grid-cols-1 gap-4 py-6 sm:grid-cols-2 lg:grid-cols-5">
        {details.map((detail) => (
          <div key={detail.label}>
            <dt className="text-sm font-medium text-muted-foreground">{detail.label}</dt>
            <dd className="mt-1 text-base font-semibold text-foreground">{detail.value}</dd>
          </div>
        ))}
      </dl>

      <div className="grid grid-cols-1 gap-6 border-t border-slate-100 pt-6 lg:grid-cols-2">
        <section aria-labelledby="profile-conditions-title">
          <div className="flex items-center gap-2">
            <HeartPulse className="size-5 text-teal-600" aria-hidden="true" />
            <h3 id="profile-conditions-title" className="text-base font-bold text-foreground">
              Tình trạng sức khỏe đã biết
            </h3>
          </div>
          {conditions.length > 0 ? (
            <ul className="mt-4 space-y-2">
              {conditions.map((condition) => (
                <li key={condition} className="text-sm leading-6 text-slate-700 dark:text-slate-200">
                  {condition}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">Chưa có thông tin được khai báo.</p>
          )}
        </section>

        <section aria-labelledby="profile-medications-title">
          <div className="flex items-center gap-2">
            <Pill className="size-5 text-teal-600" aria-hidden="true" />
            <h3 id="profile-medications-title" className="text-base font-bold text-foreground">
              Dị ứng và thuốc đang dùng
            </h3>
          </div>
          <div className="mt-4 space-y-4 text-sm leading-6 text-slate-700 dark:text-slate-200">
            <div>
              <p className="font-medium text-foreground">Dị ứng</p>
              {allergies.length > 0 ? (
                <ul className="mt-1 space-y-1">
                  {allergies.map((allergy) => {
                    const type = allergy.type ?? "OTHER";
                    const severity = allergy.severity ?? "MEDIUM";

                    return (
                      <li key={allergy.id}>
                        {allergy.name} ({allergyTypeLabels[type]}, {allergySeverityLabels[severity]})
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="mt-1 text-slate-600 dark:text-slate-300">Chưa có thông tin được khai báo.</p>
              )}
            </div>
            <div>
              <p className="font-medium text-foreground">Thuốc đang dùng</p>
              {medications.length > 0 ? (
                <ul className="mt-1 space-y-1">
                  {medications.map((medication) => (
                    <li key={medication.id}>
                      {medication.name} — {medication.dosage}, {medication.frequency}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-slate-600 dark:text-slate-300">Chưa có thông tin được khai báo.</p>
              )}
            </div>
          </div>
        </section>
      </div>

      <p className="mt-6 flex gap-2 border-t border-slate-100 pt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
        <Info className="mt-0.5 size-4 shrink-0 text-sky-600" aria-hidden="true" />
        Hồ sơ này giúp bạn chuẩn bị thông tin khi trao đổi. Ứng dụng không xác minh dị ứng, chẩn đoán bệnh hoặc tư vấn dùng thuốc.
      </p>
    </section>
  );
};
