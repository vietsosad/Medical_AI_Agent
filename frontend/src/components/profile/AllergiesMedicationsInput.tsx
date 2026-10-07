"use client";

import React, { useState, useCallback, useMemo } from "react";
import { useWatch, type UseFormReturn } from "react-hook-form";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldAlert,
  AlertTriangle,
  Plus,
  X,
  Pill,
  Clock,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { EhrLiteFormValues } from "@/schemas/clinical-profile.schema";
import type { AllergyDTO, MedicationDTO, AllergyType, AllergySeverity } from "@/types/clinical-profile";
import { toast } from "sonner";

const ALLERGY_TYPE_OPTIONS: Array<{ value: AllergyType; label: string }> = [
  { value: "MEDICATION", label: "Thuốc" },
  { value: "FOOD", label: "Thực phẩm" },
  { value: "ENVIRONMENT", label: "Môi trường" },
  { value: "OTHER", label: "Khác" },
];

const SEVERITY_OPTIONS: Array<{ value: AllergySeverity; label: string; badge: string }> = [
  { value: "HIGH", label: "Nặng", badge: "bg-rose-600 text-white border-rose-600 shadow-sm font-extrabold" },
  { value: "MEDIUM", label: "Vừa", badge: "bg-amber-500 text-slate-950 border-amber-500 shadow-sm font-extrabold dark:text-slate-50" },
  { value: "LOW", label: "Nhẹ", badge: "bg-sky-600 text-white border-sky-600 shadow-sm font-extrabold" },
];

const allergyTypeLabels: Record<AllergyType, string> = {
  MEDICATION: "Thuốc",
  FOOD: "Thực phẩm",
  ENVIRONMENT: "Môi trường",
  OTHER: "Khác",
};

const allergySeverityLabels: Record<AllergySeverity, string> = {
  HIGH: "Mức độ nặng",
  MEDIUM: "Mức độ vừa",
  LOW: "Mức độ nhẹ",
};

export interface AllergiesMedicationsInputProps {
  form: UseFormReturn<EhrLiteFormValues>;
  className?: string;
}

/**
 * Component Quản Trị Dị Ứng & Thuốc Đang Dùng (AllergiesMedicationsInput)
 * Lưu những thông tin về dị ứng và thuốc do người dùng tự khai báo.
 */
export const AllergiesMedicationsInput: React.FC<AllergiesMedicationsInputProps> = ({
  form,
  className,
}) => {
  const { control, setValue } = form;

  // Lắng nghe real-time mảng allergies & current_medications
  const allergyValues = useWatch({ control, name: "allergies", defaultValue: [] });
  const medicationValues = useWatch({ control, name: "current_medications", defaultValue: [] });
  const watchedAllergies = useMemo(() => allergyValues ?? [], [allergyValues]);
  const watchedMedications = useMemo(() => medicationValues ?? [], [medicationValues]);

  // --------------------------------------------------------------------------
  // STATE CHO INLINE FORM DỊ ỨNG
  // --------------------------------------------------------------------------
  const [allergyName, setAllergyName] = useState("");
  const [allergyType, setAllergyType] = useState<AllergyType>("MEDICATION");
  const [allergySeverity, setAllergySeverity] = useState<AllergySeverity>("HIGH");
  const [allergyError, setAllergyError] = useState("");

  // --------------------------------------------------------------------------
  // STATE CHO INLINE FORM THUỐC ĐANG DÙNG
  // --------------------------------------------------------------------------
  const [medName, setMedName] = useState("");
  const [medDosage, setMedDosage] = useState("");
  const [medFreq, setMedFreq] = useState("");
  const [medError, setMedError] = useState("");

  // Hàm xử lý Thêm Dị Ứng mới
  const handleAddAllergy = useCallback(
    (e: React.FormEvent | React.MouseEvent) => {
      e.preventDefault();
      const cleanName = allergyName.trim();
      if (!cleanName) {
        setAllergyError("Vui lòng nhập tên thuốc hoặc tác nhân gây dị ứng.");
        return;
      }
      if (watchedAllergies.some((a) => a.name.toLowerCase() === cleanName.toLowerCase())) {
        setAllergyError("Tác nhân dị ứng này đã có trong hồ sơ.");
        return;
      }

      const newAllergy: AllergyDTO = {
        id: `alg-${crypto.randomUUID()}`,
        name: cleanName,
        type: allergyType,
        severity: allergySeverity,
      };

      setValue("allergies", [...watchedAllergies, newAllergy], {
        shouldValidate: true,
        shouldDirty: true,
      });

      toast.success("Đã thêm thông tin dị ứng vào hồ sơ.", {
        description: "Hãy báo lại nhân viên y tế nếu bạn từng có phản ứng dị ứng.",
      });

      setAllergyName("");
      setAllergyError("");
    },
    [allergyName, allergyType, allergySeverity, watchedAllergies, setValue]
  );

  // Hàm xóa Dị Ứng
  const handleRemoveAllergy = useCallback(
    (id: string) => {
      const filtered = watchedAllergies.filter((a) => a.id !== id);
      setValue("allergies", filtered, { shouldValidate: true, shouldDirty: true });
      toast.info("Đã xóa thông tin dị ứng khỏi hồ sơ.");
    },
    [watchedAllergies, setValue]
  );

  // Hàm xử lý Thêm Thuốc Hằng Ngày
  const handleAddMedication = useCallback(
    (e: React.FormEvent | React.MouseEvent) => {
      e.preventDefault();
      const cleanMed = medName.trim();
      const cleanDosage = medDosage.trim();
      const cleanFreq = medFreq.trim();

      if (!cleanMed || !cleanDosage || !cleanFreq) {
        setMedError("Vui lòng nhập đầy đủ: Tên thuốc, liều lượng và tần suất sử dụng.");
        return;
      }

      const newMed: MedicationDTO = {
        id: `med-${crypto.randomUUID()}`,
        name: cleanMed,
        dosage: cleanDosage,
        frequency: cleanFreq,
      };

      setValue("current_medications", [...watchedMedications, newMed], {
        shouldValidate: true,
        shouldDirty: true,
      });

      toast.success("Đã bổ sung thuốc vào danh mục điều trị hằng ngày.");
      setMedName("");
      setMedDosage("");
      setMedFreq("");
      setMedError("");
    },
    [medName, medDosage, medFreq, watchedMedications, setValue]
  );

  // Hàm xóa Thuốc Hằng Ngày
  const handleRemoveMedication = useCallback(
    (id: string) => {
      const filtered = watchedMedications.filter((m) => m.id !== id);
      setValue("current_medications", filtered, { shouldValidate: true, shouldDirty: true });
      toast.info("Đã ngừng ghi nhận thuốc trong danh mục điều trị.");
    },
    [watchedMedications, setValue]
  );

  return (
    <div className={cn("grid grid-cols-1 lg:grid-cols-12 gap-8", className)}>
      {/* ===================================================================== */}
      {/* CỘT TRÁI (6 CỘT): THÔNG TIN DỊ ỨNG */}
      {/* ===================================================================== */}
      <div className="lg:col-span-6 bg-card border border-border shadow-[0_10px_35px_rgba(0,0,0,0.04)] rounded-3xl p-6 md:p-7 flex flex-col justify-between relative overflow-hidden hover:border-sky-300/80 transition-colors duration-300">
        <div className="absolute -top-20 -left-20 h-48 w-48 rounded-full bg-rose-500/5 blur-[80px] pointer-events-none" />

        <div>
          {/* Header Dị ứng */}
          <div className="flex items-center justify-between pb-5 border-b border-border">
            <div className="flex items-center gap-3.5">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-rose-50 border border-rose-200 shadow-sm">
                <ShieldAlert className="w-6 h-6 text-rose-600 animate-pulse" />
              </div>
              <div>
                <h3 className="text-lg font-black text-foreground tracking-tight flex items-center gap-2">
                  <span>Dị Ứng Y Khoa &amp; Tác Nhân</span>
                  <span className="text-xs font-mono px-2.5 py-0.5 rounded-md bg-rose-50 border border-rose-200 text-rose-800 font-extrabold shadow-2xs">
                    {watchedAllergies.length}
                  </span>
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  Lưu lại những tác nhân bạn biết hoặc đã từng gây phản ứng.
                </p>
              </div>
            </div>
          </div>

          {/* INLINE FORM THÊM DỊ ỨNG */}
          <div className="mt-6 p-4.5 bg-background/90 border border-border/90 rounded-2xl space-y-4 shadow-inner">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
              <Plus className="w-4 h-4 text-rose-600 stroke-[3]" />
              <span>Ghi nhận tác nhân dị ứng mới</span>
            </div>

            <div className="space-y-3.5">
              <div>
                <input
                  type="text"
                  value={allergyName}
                  onChange={(e) => {
                    setAllergyName(e.target.value);
                    if (allergyError) setAllergyError("");
                  }}
                  onKeyDown={(e) => e.key === "Enter" && handleAddAllergy(e)}
                  placeholder="Vd: Penicillin, Aspirin, Đậu phộng, Phấn hoa..."
                  className="h-11 w-full rounded-xl border border-slate-300 bg-card px-4 text-sm font-medium text-foreground shadow-2xs transition-all placeholder:text-slate-400 focus:border-rose-500 focus:outline-none focus:ring-2 focus:ring-rose-500/40 dark:border-slate-700"
                />
              </div>

              {/* Bộ chọn Type & Severity */}
              <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                {/* Loại dị ứng */}
                <div className="sm:col-span-7 flex flex-col space-y-1.5">
                  <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Loại</span>
                  <div className="grid grid-cols-2 gap-2">
                    {ALLERGY_TYPE_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setAllergyType(opt.value)}
                        className={cn(
                          "min-h-11 rounded-xl border px-2 text-sm font-semibold transition-colors",
                          allergyType === opt.value
                            ? "bg-slate-900 text-white border-slate-900 font-black shadow-sm"
                            : "bg-card text-slate-700 border-slate-300 hover:bg-muted/80 dark:text-slate-200 dark:border-slate-700"
                        )}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Mức độ do người dùng tự khai báo */}
                <div className="sm:col-span-5 flex flex-col space-y-1.5">
                  <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Mức độ bạn từng gặp</span>
                  <div className="flex flex-col gap-2">
                    {SEVERITY_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setAllergySeverity(opt.value)}
                        className={cn(
                          "min-h-11 rounded-xl border px-3 text-sm transition-colors",
                          allergySeverity === opt.value
                            ? opt.badge
                            : "bg-card text-slate-700 border-slate-300 hover:bg-muted/80 font-bold dark:text-slate-200 dark:border-slate-700"
                        )}
                      >
                        <span>{opt.label}</span>
                        <span className="w-1.5 h-1.5 rounded-full bg-current shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Error banner cho form dị ứng */}
              {allergyError && (
                <div className="flex items-center gap-2 text-sm font-semibold text-rose-600">
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0 animate-bounce" />
                  <span>{allergyError}</span>
                </div>
              )}

              <button
                type="button"
                onClick={handleAddAllergy}
                className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-rose-600 text-sm font-bold text-white shadow-sm transition-colors hover:bg-rose-700"
              >
                <Plus className="w-4 h-4 stroke-[3]" />
                <span>Thêm Dị Ứng Vào Hồ Sơ</span>
              </button>
            </div>
          </div>

          {/* DANH SÁCH TAG DỊ ỨNG ĐÃ GHI NHẬN */}
          <div className="mt-6 space-y-3">
            <div className="flex items-center justify-between gap-4 text-sm font-semibold text-slate-700 dark:text-slate-200">
              <span>Danh mục dị ứng hiện có ({watchedAllergies.length}):</span>
              <span className="text-sm font-normal text-muted-foreground">Chọn X để xóa</span>
            </div>

            {watchedAllergies.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-background/70 p-6 text-center text-sm leading-6 text-slate-600 dark:text-slate-300 dark:border-slate-700">
                Chưa có thông tin dị ứng được khai báo. Điều này không khẳng định bạn không có dị ứng.
              </div>
            ) : (
              <div className="flex flex-wrap gap-2.5">
                <AnimatePresence>
                  {watchedAllergies.map((alg) => (
                      <motion.div
                        key={alg.id}
                        layout
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.8, y: -10 }}
                        transition={{ duration: 0.2 }}
                        className="group/alg relative inline-flex items-center gap-2 rounded-2xl border border-border bg-background px-4 py-2 text-sm font-semibold text-foreground transition-colors hover:border-sky-300 hover:bg-card"
                      >
                        <div className="flex flex-col">
                          <span className="text-sm font-semibold leading-tight">{alg.name}</span>
                          <span className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                            {allergyTypeLabels[alg.type]} · {allergySeverityLabels[alg.severity]}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveAllergy(alg.id)}
                          className="ml-1 min-h-11 min-w-11 shrink-0 rounded-xl p-2 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-600"
                          title="Xóa dị ứng này"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 flex items-start gap-2 border-t border-border pt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
          <Info className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <p>Thông tin này do bạn tự khai báo. Ứng dụng không xác minh dị ứng hoặc dự báo phản ứng với thuốc.</p>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* CỘT PHẢI (6 CỘT): QUẢN TRỊ THUỐC SỬ DỤNG HẰNG NGÀY                  */}
      {/* ===================================================================== */}
      <div className="lg:col-span-6 bg-card border border-border shadow-[0_10px_35px_rgba(0,0,0,0.04)] rounded-3xl p-6 md:p-7 flex flex-col justify-between relative overflow-hidden hover:border-sky-300/80 transition-colors duration-300">
        <div className="absolute -top-20 -right-20 h-48 w-48 rounded-full bg-emerald-500/5 blur-[80px] pointer-events-none" />

        <div>
          {/* Header Thuốc hằng ngày */}
          <div className="flex items-center justify-between pb-5 border-b border-border">
            <div className="flex items-center gap-3.5">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 border border-emerald-200 shadow-sm">
                <Pill className="w-6 h-6 text-emerald-600" />
              </div>
              <div>
                <h3 className="text-lg font-black text-foreground tracking-tight flex items-center gap-2">
                  <span>Thuốc Sử Dụng Hằng Ngày</span>
                  <span className="text-xs font-mono px-2.5 py-0.5 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-800 font-extrabold shadow-2xs">
                    {watchedMedications.length}
                  </span>
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  Ghi lại thuốc bạn đang dùng để tiện cung cấp khi được hỏi.
                </p>
              </div>
            </div>
          </div>

          {/* INLINE FORM THÊM THUỐC ĐANG DÙNG */}
          <div className="mt-6 p-4.5 bg-background/90 border border-border/90 rounded-2xl space-y-4 shadow-inner">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
              <Plus className="w-4 h-4 text-emerald-600 stroke-[3]" />
              <span>Thêm thuốc đang dùng</span>
            </div>

            <div className="space-y-3.5">
              <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                {/* Tên thuốc */}
                <div className="sm:col-span-7">
                  <input
                    type="text"
                    value={medName}
                    onChange={(e) => {
                      setMedName(e.target.value);
                      if (medError) setMedError("");
                    }}
                    placeholder="Tên thuốc (Vd: Plavix, Concor...)"
                    className="h-11 w-full rounded-xl border border-slate-300 bg-card px-4 text-sm font-medium text-foreground shadow-2xs transition-all placeholder:text-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 dark:border-slate-700"
                  />
                </div>
                {/* Liều lượng */}
                <div className="sm:col-span-5">
                  <input
                    type="text"
                    value={medDosage}
                    onChange={(e) => {
                      setMedDosage(e.target.value);
                      if (medError) setMedError("");
                    }}
                    placeholder="Liều dùng (Vd: 75mg, 2.5mg...)"
                    className="h-11 w-full rounded-xl border border-slate-300 bg-card px-4 text-sm font-medium text-foreground shadow-2xs transition-all placeholder:text-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 dark:border-slate-700"
                  />
                </div>
              </div>

              <div>
                <input
                  type="text"
                  value={medFreq}
                  onChange={(e) => {
                    setMedFreq(e.target.value);
                    if (medError) setMedError("");
                  }}
                  onKeyDown={(e) => e.key === "Enter" && handleAddMedication(e)}
                  placeholder="Tần suất sử dụng (Vd: 1 viên/ngày - Sáng sau ăn)"
                  className="h-11 w-full rounded-xl border border-slate-300 bg-card px-4 text-sm font-medium text-foreground shadow-2xs transition-all placeholder:text-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 dark:border-slate-700"
                />
              </div>

              {/* Error banner cho form thuốc */}
              {medError && (
                <div className="flex items-center gap-2 text-sm font-semibold text-rose-600">
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0 animate-bounce" />
                  <span>{medError}</span>
                </div>
              )}

              <button
                type="button"
                onClick={handleAddMedication}
                className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 text-sm font-bold text-white shadow-sm transition-colors hover:bg-emerald-700"
              >
                <Plus className="w-4 h-4 stroke-[3]" />
                <span>Thêm Thuốc Đang Dùng</span>
              </button>
            </div>
          </div>

          {/* DANH SÁCH MINI CARDS THUỐC ĐANG DÙNG */}
          <div className="mt-6 space-y-3">
            <div className="flex items-center justify-between gap-4 text-sm font-semibold text-slate-700 dark:text-slate-200">
              <span>Danh mục thuốc điều trị ({watchedMedications.length}):</span>
              <span className="text-sm font-normal text-muted-foreground">Chọn X để xóa</span>
            </div>

            {watchedMedications.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-background/70 p-6 text-center text-sm leading-6 text-slate-600 dark:text-slate-300 dark:border-slate-700">
                Chưa có thuốc đang dùng được khai báo. Hãy cập nhật khi bạn có thông tin chính xác.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[320px] overflow-y-auto pr-1 custom-scrollbar">
                <AnimatePresence>
                  {watchedMedications.map((med) => (
                    <motion.div
                      key={med.id}
                      layout
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, scale: 0.9, x: -20 }}
                      transition={{ duration: 0.2 }}
                      className="bg-card border border-border rounded-2xl p-4 flex items-center justify-between transition-all duration-200 hover:border-emerald-400 hover:shadow-md group/card shadow-xs"
                    >
                      <div className="flex items-center gap-3.5 min-w-0">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-200 shadow-2xs">
                          <Pill className="w-5 h-5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-black text-foreground tracking-tight truncate">
                              {med.name}
                            </span>
                            <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-sm font-semibold text-emerald-800">
                              {med.dosage}
                            </span>
                          </div>
                          <div className="mt-1 flex items-center gap-2 truncate text-sm text-slate-600 dark:text-slate-300">
                            <Clock className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                            <span>{med.frequency}</span>
                          </div>
                        </div>
                      </div>

                      {/* Nút xóa hover trượt ra */}
                      <button
                        type="button"
                        onClick={() => handleRemoveMedication(med.id)}
                        className="ml-2 min-h-11 min-w-11 shrink-0 rounded-xl p-2 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-600"
                        title="Xóa thuốc khỏi toa điều trị"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 flex items-start gap-2 border-t border-border pt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
          <Info className="mt-0.5 size-4 shrink-0 text-emerald-600" />
          <p>Danh sách này không thay thế hướng dẫn của bác sĩ hoặc dược sĩ. Không tự thay đổi thuốc dựa trên thông tin trong ứng dụng.</p>
        </div>
      </div>
    </div>
  );
};
