"use client";

import React, { useMemo, useCallback } from "react";
import { useWatch, type UseFormReturn } from "react-hook-form";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  Calendar,
  ArrowUpDown,
  Weight,
  Droplet,
  AlertTriangle,
  HeartPulse,
  Info,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  UserCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { calculateBMI } from "@/lib/clinical-utils";
import type { EhrLiteFormValues } from "@/schemas/clinical-profile.schema";
import type { GenderType, BloodType, BmiCategory } from "@/types/clinical-profile";

// ============================================================================
// 1. CONSTANTS FOR CLINICAL SELECTION (ZERO EMOJI IN UI - 100% VECTOR ICON COMPLIANCE)
// ============================================================================

const GENDER_OPTIONS: Array<{ value: GenderType; label: string; enLabel: string }> = [
  { value: "MALE", label: "Nam", enLabel: "Male" },
  { value: "FEMALE", label: "Nữ", enLabel: "Female" },
  { value: "OTHER", label: "Khác", enLabel: "Other" },
];

const BLOOD_TYPE_OPTIONS: Array<{ value: BloodType; label: string; isCommon?: boolean }> = [
  { value: "O+", label: "O+", isCommon: true },
  { value: "O-", label: "O-" },
  { value: "A+", label: "A+", isCommon: true },
  { value: "A-", label: "A-" },
  { value: "B+", label: "B+", isCommon: true },
  { value: "B-", label: "B-" },
  { value: "AB+", label: "AB+" },
  { value: "AB-", label: "AB-" },
  { value: "UNKNOWN", label: "Chưa rõ" },
];

// ============================================================================
// 2. BMI REFERENCE LABELS
// ============================================================================
const getCategoryDetails = (category: BmiCategory) => {
  switch (category) {
    case "UNDERWEIGHT":
      return {
        label: "Dưới khoảng tham khảo",
        colorClass: "text-sky-900 bg-sky-100/90 border-sky-300",
        badgeGlow: "shadow-sm",
        pointerBg: "bg-sky-600 text-white border-sky-400 shadow-md",
        cardioStatus: "BMI là chỉ số tham khảo được tính từ chiều cao và cân nặng, không phải chẩn đoán.",
        Icon: TrendingDown,
      };
    case "NORMAL":
      return {
        label: "Trong khoảng tham khảo",
        colorClass: "text-emerald-900 bg-emerald-100/90 border-emerald-300",
        badgeGlow: "shadow-sm",
        pointerBg: "bg-emerald-600 text-white border-emerald-400 shadow-md",
        cardioStatus: "BMI là chỉ số tham khảo được tính từ chiều cao và cân nặng, không phải chẩn đoán.",
        Icon: CheckCircle2,
      };
    case "OVERWEIGHT":
      return {
        label: "Trên khoảng tham khảo",
        colorClass: "text-amber-900 bg-amber-100/90 border-amber-300",
        badgeGlow: "shadow-sm",
        pointerBg: "bg-amber-500 text-slate-950 border-amber-300 shadow-md dark:text-slate-50",
        cardioStatus: "BMI là chỉ số tham khảo được tính từ chiều cao và cân nặng, không phải chẩn đoán.",
        Icon: TrendingUp,
      };
    case "OBESE":
      return {
        label: "BMI cao so với khoảng tham khảo",
        colorClass: "text-rose-950 bg-rose-100/90 border-rose-300",
        badgeGlow: "shadow-sm",
        pointerBg: "bg-rose-600 text-white border-rose-400 shadow-md",
        cardioStatus: "BMI là chỉ số tham khảo được tính từ chiều cao và cân nặng, không phải chẩn đoán.",
        Icon: AlertTriangle,
      };
  }
};

// ============================================================================
// 3. COMPONENT INTERFACE
// ============================================================================
export interface VitalsBmiCardProps {
  form: UseFormReturn<EhrLiteFormValues>;
  className?: string;
}

/**
 * Biểu mẫu thông tin cơ thể và chỉ số BMI tham khảo.
 */
export const VitalsBmiCard: React.FC<VitalsBmiCardProps> = ({ form, className }) => {
  const {
    register,
    control,
    setValue,
    formState: { errors },
  } = form;

  // Real-time reactive listening với useWatch không cần chờ Save button
  const watchedHeight = useWatch({ control, name: "height_cm", defaultValue: null });
  const watchedWeight = useWatch({ control, name: "weight_kg", defaultValue: null });
  const watchedGender = useWatch({ control, name: "gender", defaultValue: null });
  const watchedBloodType = useWatch({ control, name: "blood_type", defaultValue: null });

  // Tính toán chỉ số BMI theo chuẩn WHO WPRO Châu Á
  const bmiResult = useMemo(() => {
    const validHeight = typeof watchedHeight === "number" && !Number.isNaN(watchedHeight) ? watchedHeight : 0;
    const validWeight = typeof watchedWeight === "number" && !Number.isNaN(watchedWeight) ? watchedWeight : 0;
    return calculateBMI(validHeight, validWeight);
  }, [watchedHeight, watchedWeight]);

  const categoryDetails = useMemo(() => {
    return getCategoryDetails(bmiResult.category);
  }, [bmiResult.category]);
  const hasBmi = bmiResult.bmi > 0;

  // Quy định dải BMI hiển thị trên dải quang phổ từ 14.0 (0%) tới 34.0 (100%)
  const gaugePercent = useMemo(() => {
    if (!bmiResult || bmiResult.bmi <= 0) return 0;
    const clampedBmi = Math.min(Math.max(bmiResult.bmi, 14.0), 34.0);
    const rawPercentage = ((clampedBmi - 14.0) / (34.0 - 14.0)) * 100;
    return Math.min(Math.max(rawPercentage, 4), 96);
  }, [bmiResult]);

  // Hàm chọn Giới tính tối ưu cho phím Tab & nhấp chuột
  const handleGenderChange = useCallback(
    (val: GenderType) => {
      setValue("gender", val, { shouldValidate: true, shouldDirty: true });
    },
    [setValue]
  );

  // Hàm chọn Nhóm máu tối ưu
  const handleBloodTypeChange = useCallback(
    (val: BloodType) => {
      setValue("blood_type", val, { shouldValidate: true, shouldDirty: true });
    },
    [setValue]
  );

  return (
    <div
      className={cn(
        "bg-card border border-border shadow-[0_10px_35px_rgba(0,0,0,0.04)] hover:shadow-[0_15px_45px_rgba(14,165,233,0.08)] rounded-3xl p-6 md:p-8 relative overflow-hidden transition-all duration-300 hover:border-sky-300/80",
        className
      )}
    >
      {/* Subtle ambient lighting for medical clean aesthetics */}
      <div className="absolute -right-24 -top-24 h-56 w-56 rounded-full bg-emerald-500/5 blur-[80px] pointer-events-none" />
      <div className="absolute -left-24 -bottom-24 h-56 w-56 rounded-full bg-sky-500/5 blur-[80px] pointer-events-none" />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 relative z-10">
        {/* ===================================================================== */}
        {/* CỘT TRÁI: CLINICAL INPUTS & INTERACTIVE SELECTORS (7 COLUMNS)         */}
        {/* ===================================================================== */}
        <div className="lg:col-span-7 flex flex-col justify-between space-y-6">
          {/* Header section */}
          <div className="flex items-center gap-3.5 pb-4 border-b border-border">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-sky-50 border border-sky-200 shadow-sm">
              <Activity className="h-6 w-6 text-sky-600 animate-pulse" />
            </div>
            <div>
              <h2 className="text-xl font-black text-foreground tracking-tight flex items-center gap-2">
                <span>Thông tin cơ thể</span>
              </h2>
              <p className="text-xs text-slate-600 font-normal dark:text-slate-300">
                Chỉ nhập những thông tin bạn biết. BMI được tính từ chiều cao và cân nặng để tham khảo.
              </p>
            </div>
          </div>

          <div className="space-y-6">
            {/* Hàng 1: Tuổi & Giới tính */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
              {/* Tuổi */}
              <div className="md:col-span-5 flex flex-col space-y-2">
                <label
                  htmlFor="input-age"
                  className="text-sm font-extrabold text-slate-800 flex items-center gap-2 dark:text-slate-100"
                >
                  <Calendar className="w-4 h-4 text-sky-600 shrink-0" />
                  <span>Tuổi</span>
                </label>
                <div className="relative">
                  <input
                    id="input-age"
                    type="number"
                    tabIndex={1}
                    placeholder="Vd: 54"
                    className={cn(
                      "w-full h-11 px-4 bg-background border border-border/90 rounded-2xl text-foreground font-mono text-base font-bold focus:outline-none focus:bg-card focus:ring-2 focus:ring-sky-500/40 focus:border-sky-500 transition-all duration-200 placeholder:text-slate-400 shadow-inner",
                      errors.age && "border-rose-500/80 focus:ring-rose-500/30 text-rose-900 bg-rose-50/50"
                    )}
                    {...register("age", { valueAsNumber: true })}
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-mono font-bold text-muted-foreground pointer-events-none">
                    Tuổi
                  </span>
                </div>
                {/* Error Banner cho Tuổi */}
                <AnimatePresence>
                  {errors.age && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      role="alert"
                      aria-live="assertive"
                      className="flex items-center gap-1.5 text-xs font-bold text-rose-600 pt-0.5"
                    >
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0 animate-bounce" />
                      <span>{errors.age.message}</span>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Giới tính (Segmented Interactive Buttons) */}
              <div className="md:col-span-7 flex flex-col space-y-2">
                <label className="text-sm font-extrabold text-slate-800 flex items-center gap-2 dark:text-slate-100">
                  <UserCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Giới tính</span>
                </label>
                <div
                  role="radiogroup"
                  aria-label="Chọn giới tính"
                  className="grid grid-cols-3 gap-1.5 p-1.5 bg-muted border border-border/90 rounded-2xl h-11 relative shadow-inner"
                >
                  {GENDER_OPTIONS.map((opt, idx) => {
                    const isSelected = watchedGender === opt.value;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        role="radio"
                        aria-checked={isSelected}
                        tabIndex={idx === 0 ? 2 : 0}
                        onClick={() => handleGenderChange(opt.value)}
                        className={cn(
                          "relative z-10 h-full rounded-xl flex items-center justify-center gap-1 text-xs font-bold transition-all duration-200 select-none outline-none focus-visible:ring-2 focus-visible:ring-sky-500",
                          isSelected ? "text-white font-black" : "text-slate-600 hover:text-foreground hover:bg-card/60 dark:text-slate-300"
                        )}
                      >
                        {isSelected && (
                          <motion.div
                            layoutId="gender-active-pill"
                            className="absolute inset-0 bg-sky-600 rounded-xl shadow-md -z-10"
                            transition={{ type: "spring", stiffness: 350, damping: 25 }}
                          />
                        )}
                        <span>{opt.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Hàng 2: Chiều cao & Cân nặng (Cơ sở reactive cho BMI) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {/* Chiều cao */}
              <div className="flex flex-col space-y-2">
                <label
                  htmlFor="input-height"
                  className="text-sm font-extrabold text-slate-800 flex items-center justify-between dark:text-slate-100"
                >
                  <span className="flex items-center gap-2">
                    <ArrowUpDown className="w-4 h-4 text-amber-600 shrink-0" />
                    <span>Chiều cao</span>
                  </span>
                  <span className="text-[11px] font-mono font-semibold text-muted-foreground">50 - 250 cm</span>
                </label>
                <div className="relative">
                  <input
                    id="input-height"
                    type="number"
                    step="0.5"
                    tabIndex={3}
                    placeholder="Vd: 168"
                    className={cn(
                      "w-full h-11 px-4 bg-background border border-border/90 rounded-2xl text-foreground font-mono text-base font-bold focus:outline-none focus:bg-card focus:ring-2 focus:ring-amber-500/40 focus:border-amber-500 transition-all duration-200 placeholder:text-slate-400 shadow-inner",
                      errors.height_cm && "border-rose-500/80 focus:ring-rose-500/30 text-rose-900 bg-rose-50/50"
                    )}
                    {...register("height_cm", { valueAsNumber: true })}
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-mono font-extrabold text-amber-700 pointer-events-none">
                    cm
                  </span>
                </div>
                <AnimatePresence>
                  {errors.height_cm && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      role="alert"
                      aria-live="assertive"
                      className="flex items-center gap-1.5 text-xs font-bold text-rose-600 pt-0.5"
                    >
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                      <span>{errors.height_cm.message}</span>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Cân nặng */}
              <div className="flex flex-col space-y-2">
                <label
                  htmlFor="input-weight"
                  className="text-sm font-extrabold text-slate-800 flex items-center justify-between dark:text-slate-100"
                >
                  <span className="flex items-center gap-2">
                    <Weight className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>Cân nặng</span>
                  </span>
                  <span className="text-[11px] font-mono font-semibold text-muted-foreground">3.0 - 350 kg</span>
                </label>
                <div className="relative">
                  <input
                    id="input-weight"
                    type="number"
                    step="0.1"
                    tabIndex={4}
                    placeholder="Vd: 72.5"
                    className={cn(
                      "w-full h-11 px-4 bg-background border border-border/90 rounded-2xl text-foreground font-mono text-base font-bold focus:outline-none focus:bg-card focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 transition-all duration-200 placeholder:text-slate-400 shadow-inner",
                      errors.weight_kg && "border-rose-500/80 focus:ring-rose-500/30 text-rose-900 bg-rose-50/50"
                    )}
                    {...register("weight_kg", { valueAsNumber: true })}
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-mono font-extrabold text-emerald-700 pointer-events-none">
                    kg
                  </span>
                </div>
                <AnimatePresence>
                  {errors.weight_kg && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      role="alert"
                      aria-live="assertive"
                      className="flex items-center gap-1.5 text-xs font-bold text-rose-600 pt-0.5"
                    >
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                      <span>{errors.weight_kg.message}</span>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Hàng 3: Nhóm máu hệ ABO/Rh (Interactive Medical Choice Badges) */}
            <div className="flex flex-col space-y-3 pt-1">
              <label className="text-sm font-extrabold text-slate-800 flex items-center justify-between dark:text-slate-100">
                <span className="flex items-center gap-2">
                  <Droplet className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>Nhóm máu</span>
                </span>
                <span className="text-sm text-muted-foreground">Nếu bạn đã biết</span>
              </label>

              <div
                role="radiogroup"
                aria-label="Chọn nhóm máu ABO Rh"
                className="grid grid-cols-3 sm:grid-cols-5 gap-2.5"
              >
                {BLOOD_TYPE_OPTIONS.map((opt, idx) => {
                  const isSelected = watchedBloodType === opt.value;
                  const isUnknown = opt.value === "UNKNOWN";

                  return (
                    <button
                      key={opt.value}
                      type="button"
                      role="radio"
                      aria-checked={isSelected}
                      tabIndex={idx === 0 ? 5 : 0}
                      onClick={() => handleBloodTypeChange(opt.value)}
                      className={cn(
                        "h-10 px-3 rounded-xl border font-mono text-xs font-extrabold transition-all duration-200 flex items-center justify-center gap-1.5 select-none relative outline-none focus-visible:ring-2 focus-visible:ring-rose-500 shadow-2xs",
                        isUnknown ? "col-span-1 sm:col-span-2 text-[11px]" : "col-span-1",
                        isSelected
                          ? "bg-rose-600 border-rose-600 text-white shadow-[0_4px_15px_rgba(225,29,72,0.3)] scale-[1.02]"
                          : "bg-background/90 border-slate-200 text-slate-700 hover:bg-rose-50 hover:border-rose-300 hover:text-rose-900"
                      )}
                    >
                      <span>{opt.label}</span>
                      {opt.isCommon && !isSelected && (
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0" title="Nhóm máu phổ biến" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* ===================================================================== */}
        {/* CỘT PHẢI: REAL-TIME REACTIVE BMI GAUGE & CARDIOVASCULAR SHIELD        */}
        {/* ===================================================================== */}
        <div className="lg:col-span-5 flex flex-col justify-between">
          <div className="bg-background/90 border border-border/90 rounded-3xl p-6 flex flex-col justify-between h-full relative group hover:border-sky-300/80 transition-colors shadow-inner">
            {/* Header Gauge */}
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-border">
                <div className="flex items-center gap-2.5">
                  <HeartPulse className="w-5 h-5 text-rose-600 animate-pulse shrink-0" />
                  <span className="text-base font-bold text-foreground">
                    Chỉ số BMI
                  </span>
                </div>
                <span className="text-[11px] font-mono font-extrabold px-2.5 py-0.5 rounded-md bg-card border border-amber-300 text-amber-800 shadow-2xs">
                  Tham khảo
                </span>
              </div>

              {/* Number Readout & Status Badge */}
              <div className="mt-6 flex items-baseline justify-between gap-4">
                <div>
                  <div className="mb-1 text-sm font-medium text-muted-foreground">
                    Chỉ số khối cơ thể (BMI)
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono text-5xl font-black tracking-tight text-foreground drop-shadow-xs">
                      {bmiResult.bmi > 0 ? bmiResult.bmi : "--.-"}
                    </span>
                    <span className="text-xs font-mono font-bold text-muted-foreground">kg/m²</span>
                  </div>
                </div>

                <div
                  className={cn(
                    "px-3 py-1.5 rounded-xl border text-xs font-bold flex items-center gap-1.5 backdrop-blur-md shrink-0 transition-all duration-300",
                    hasBmi ? categoryDetails.colorClass : "border-border bg-card text-slate-600 dark:text-slate-300",
                    categoryDetails.badgeGlow
                  )}
                >
                  {hasBmi ? (
                    <categoryDetails.Icon className="w-4 h-4 shrink-0" />
                  ) : (
                    <Info className="w-4 h-4 shrink-0" />
                  )}
                  <span>{hasBmi ? categoryDetails.label : "Chưa có số liệu"}</span>
                </div>
              </div>
            </div>

            {/* COLOR SPECTRUM BAR WITH FRAMER MOTION MICRO-ANIMATIONS */}
            <div className="my-8 relative pt-4 pb-2">
              {/* Animated Pointer Badge (Lướt múa nhẹ nhàng theo thời gian thực) */}
              <div className="relative w-full h-0 z-20">
                <motion.div
                  className="absolute bottom-0 -mb-2 flex flex-col items-center pointer-events-none"
                  initial={false}
                  animate={{ left: `${gaugePercent}%` }}
                  transition={{ type: "spring", stiffness: 200, damping: 20 }}
                  style={{ transform: "translateX(-50%)" }}
                >
                  <div
                    className={cn(
                      "px-2.5 py-1 rounded-md text-[11px] font-mono font-black whitespace-nowrap shadow-md border flex items-center gap-1 transition-all duration-300 -mt-8",
                      categoryDetails.pointerBg
                    )}
                  >
                    <span className="opacity-90 font-bold">BMI</span>
                    <span>{bmiResult.bmi > 0 ? bmiResult.bmi : "--"}</span>
                  </div>
                  {/* Glowing needle lines */}
                  <div className="w-0.5 h-6 bg-slate-800 shadow-xs mt-0.5 rounded-full" />
                  <div className="w-2.5 h-2.5 rounded-full bg-card border-2 border-slate-900 shadow-sm -mt-1" />
                </motion.div>
              </div>

              {/* Color Spectrum Gauge Track */}
              <div className="h-3.5 w-full rounded-full bg-slate-200/90 border border-slate-300 p-0.5 flex overflow-hidden shadow-inner relative z-10 dark:bg-slate-700 dark:border-slate-700">
                {/* Dải Gầy (Underweight < 18.5) */}
                <div
                  className="w-[22%] bg-gradient-to-r from-sky-500 to-sky-400 h-full rounded-l-full relative group/seg transition-opacity duration-300 hover:opacity-90"
                  title="Underweight (< 18.5)"
                />
                {/* Dải Lý tưởng (Normal 18.5 - 22.9) */}
                <div
                  className="w-[24%] bg-gradient-to-r from-emerald-400 via-emerald-500 to-teal-500 h-full relative group/seg transition-opacity duration-300 hover:opacity-90"
                  title="Normal (18.5 - 22.9)"
                />
                {/* Dải Thừa cân (Overweight 23.0 - 24.9) */}
                <div
                  className="w-[18%] bg-gradient-to-r from-amber-400 via-amber-500 to-orange-500 h-full relative group/seg transition-opacity duration-300 hover:opacity-90"
                  title="Overweight (23.0 - 24.9)"
                />
                {/* Dải Béo phì (Obese ≥ 25.0) */}
                <div
                  className="w-[36%] bg-gradient-to-r from-rose-500 via-red-600 to-purple-600 h-full rounded-r-full relative group/seg transition-opacity duration-300 hover:opacity-90"
                  title="Obese (≥ 25.0)"
                />
              </div>

              {/* Gauge legend markers */}
              <div className="flex justify-between items-center mt-2 px-1 text-[10px] font-mono font-bold text-muted-foreground select-none">
                <span className="text-sky-700">14.0 (Gầy)</span>
                <span className="text-emerald-700">18.5 (Chuẩn)</span>
                <span className="text-amber-800">23.0 (Thừa cân)</span>
                <span className="text-rose-700">≥ 25.0 (Béo phì)</span>
              </div>
            </div>

            {/* Clinical Cardiovascular Analysis Box */}
            <div className="space-y-3 mt-auto">
              <div
                className={cn(
                  "rounded-2xl p-4 border transition-all duration-300 shadow-2xs",
                  hasBmi ? categoryDetails.colorClass : "border-border bg-card text-slate-700 dark:text-slate-200"
                )}
              >
                <div className="flex items-center gap-2 font-black text-xs uppercase tracking-wider mb-2">
                  <categoryDetails.Icon className="w-4 h-4 shrink-0" />
                  <span>Về chỉ số BMI</span>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed font-normal dark:text-slate-200">
                  {hasBmi
                    ? categoryDetails.cardioStatus
                    : "Nhập chiều cao và cân nặng để xem chỉ số BMI tham khảo."}
                </p>
              </div>

              {/* Footer Trust & Medical Standard Notice */}
              <div className="pt-3 border-t border-border flex items-start gap-2 text-[11px] text-slate-600 dark:text-slate-300">
                <Info className="w-3.5 h-3.5 text-sky-600 shrink-0 mt-0.5" />
                <div className="leading-tight font-medium">
                  BMI chỉ là một chỉ số sàng lọc dựa trên chiều cao và cân nặng; không thay thế chẩn đoán hoặc tư vấn của nhân viên y tế.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
