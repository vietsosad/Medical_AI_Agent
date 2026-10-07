"use client";

import React, { useState, useCallback, useMemo } from "react";
import { useWatch, type UseFormReturn } from "react-hook-form";
import { motion, AnimatePresence } from "framer-motion";
import {
  HeartPulse,
  Activity,
  Droplet,
  Wind,
  ShieldAlert,
  HeartCrack,
  TrendingUp,
  Stethoscope,
  CheckCircle2,
  Plus,
  X,
  Sparkles,
  BookmarkPlus,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { EhrLiteFormValues } from "@/schemas/clinical-profile.schema";

// ============================================================================
// 1. CONSTANTS: COMMON CLINICAL CHRONIC CONDITIONS WITH VECTOR ICONS
// ============================================================================
// Tuân thủ tuyệt đối quy chuẩn: 100% Vector Icons từ lucide-react (Không dùng emoji)

export interface ConditionCardDefinition {
  id: string;
  label: string;
  enLabel: string;
  description: string;
  icon: React.ElementType;
  themeColor: {
    border: string;
    bg: string;
    text: string;
    shadow: string;
  };
}

const COMMON_CHRONIC_CONDITIONS: ConditionCardDefinition[] = [
  {
    id: "Coronary Stented (Stent mạch vành LAD)",
    label: "Đặt Stent Mạch Vành",
    enLabel: "Coronary Stented",
    description: "Đã từng đặt stent hoặc can thiệp mạch vành.",
    icon: HeartPulse,
    themeColor: {
      border: "border-rose-200",
      bg: "bg-rose-50/80",
      text: "text-rose-600",
      shadow: "shadow-2xs",
    },
  },
  {
    id: "Hypertension Stage 2 (Tăng huyết áp)",
    label: "Huyết Áp Cao (Độ II)",
    enLabel: "Hypertension Stage 2",
    description: "Đã được chẩn đoán huyết áp cao.",
    icon: Activity,
    themeColor: {
      border: "border-amber-200",
      bg: "bg-amber-50/80",
      text: "text-amber-600",
      shadow: "shadow-2xs",
    },
  },
  {
    id: "Diabetes Type 2 (Đái tháo đường Tuýp 2)",
    label: "Đái Tháo Đường",
    enLabel: "Diabetes Type 2",
    description: "Đã được chẩn đoán đái tháo đường.",
    icon: Droplet,
    themeColor: {
      border: "border-red-200",
      bg: "bg-red-50/80",
      text: "text-red-600",
      shadow: "shadow-2xs",
    },
  },
  {
    id: "Chronic Asthma / COPD (Hen suyễn phế quản)",
    label: "Hen Suyễn / COPD",
    enLabel: "Chronic Asthma / COPD",
    description: "Hen suyễn, COPD hoặc bệnh phổi mạn đã biết.",
    icon: Wind,
    themeColor: {
      border: "border-sky-200",
      bg: "bg-sky-50/80",
      text: "text-sky-600",
      shadow: "shadow-2xs",
    },
  },
  {
    id: "Chronic Kidney Disease (Bệnh Thận Mạn)",
    label: "Bệnh Thận Mạn Tính",
    enLabel: "Chronic Kidney Disease",
    description: "Đã được chẩn đoán bệnh thận mạn.",
    icon: ShieldAlert,
    themeColor: {
      border: "border-purple-200",
      bg: "bg-purple-50/80",
      text: "text-purple-600",
      shadow: "shadow-2xs",
    },
  },
  {
    id: "Cardiovascular Disease (Bệnh Lý Tim Mạch)",
    label: "Bệnh Lý Tim Mạch",
    enLabel: "Cardiovascular Disease",
    description: "Có tiền sử bệnh tim mạch.",
    icon: HeartCrack,
    themeColor: {
      border: "border-rose-300",
      bg: "bg-rose-100/70",
      text: "text-rose-700",
      shadow: "shadow-2xs",
    },
  },
  {
    id: "Dyslipidemia (Rối loạn Lipid máu)",
    label: "Rối Loạn Mỡ Máu",
    enLabel: "Dyslipidemia",
    description: "Đã được chẩn đoán rối loạn mỡ máu.",
    icon: TrendingUp,
    themeColor: {
      border: "border-yellow-300",
      bg: "bg-yellow-50/80",
      text: "text-amber-700",
      shadow: "shadow-2xs",
    },
  },
  {
    id: "Gastric Ulcer (Viêm loét dạ dày)",
    label: "Viêm Loét Dạ Dày",
    enLabel: "Gastric Ulcer & Bleeding Risk",
    description: "Đã từng viêm loét dạ dày.",
    icon: Stethoscope,
    themeColor: {
      border: "border-orange-200",
      bg: "bg-orange-50/80",
      text: "text-orange-600",
      shadow: "shadow-2xs",
    },
  },
];

// ============================================================================
// 2. COMPONENT INTERFACE
// ============================================================================
export interface ChronicConditionsSelectorProps {
  form: UseFormReturn<EhrLiteFormValues>;
  className?: string;
}

/**
 * Người dùng chọn các tình trạng sức khỏe đã biết để lưu vào hồ sơ.
 */
export const ChronicConditionsSelector: React.FC<ChronicConditionsSelectorProps> = ({
  form,
  className,
}) => {
  const { control, setValue } = form;
  const [customInput, setCustomInput] = useState<string>("");
  const [inputError, setInputError] = useState<string>("");

  // Lắng nghe real-time mảng chronic_conditions từ React Hook Form
  const selectedConditions = useWatch({
    control,
    name: "chronic_conditions",
    defaultValue: [],
  });

  // Tách biệt các bệnh nền tuỳ chỉnh (nằm ngoài danh sách 8 bệnh chuẩn)
  const customConditions = useMemo(() => {
    const commonIds = new Set(COMMON_CHRONIC_CONDITIONS.map((c) => c.id));
    return (selectedConditions || []).filter((cond) => !commonIds.has(cond));
  }, [selectedConditions]);

  // Chọn hoặc bỏ chọn tình trạng sức khỏe trong danh sách
  const handleToggleCondition = useCallback(
    (conditionId: string) => {
      const currentList = selectedConditions || [];
      const isSelected = currentList.includes(conditionId);
      let nextList: string[];

      if (isSelected) {
        nextList = currentList.filter((item) => item !== conditionId);
      } else {
        nextList = [...currentList, conditionId];
      }

      setValue("chronic_conditions", nextList, {
        shouldValidate: true,
        shouldDirty: true,
      });
    },
    [selectedConditions, setValue]
  );

  // Hàm thêm bệnh nền tuỳ chỉnh qua Input
  const handleAddCustomCondition = useCallback(
    (e: React.FormEvent | React.MouseEvent) => {
      e.preventDefault();
      const cleanText = customInput.trim();

      if (!cleanText) {
        setInputError("Vui lòng gõ tên bệnh nền trước khi thêm.");
        return;
      }

      if (cleanText.length < 3) {
        setInputError("Tên bệnh nền cần có ít nhất 3 ký tự.");
        return;
      }

      const currentList = selectedConditions || [];
      if (currentList.some((item) => item.toLowerCase() === cleanText.toLowerCase())) {
        setInputError("Bệnh nền này đã tồn tại trong danh sách.");
        return;
      }

      setValue("chronic_conditions", [...currentList, cleanText], {
        shouldValidate: true,
        shouldDirty: true,
      });
      setCustomInput("");
      setInputError("");
    },
    [customInput, selectedConditions, setValue]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleAddCustomCondition(e);
      }
    },
    [handleAddCustomCondition]
  );

  return (
    <div
      className={cn(
        "bg-card border border-border shadow-[0_10px_35px_rgba(0,0,0,0.04)] hover:shadow-[0_15px_45px_rgba(14,165,233,0.08)] rounded-3xl p-6 md:p-8 relative overflow-hidden transition-all duration-300 hover:border-sky-300/80",
        className
      )}
    >
      {/* Ambient Depth Lighting */}
      <div className="absolute top-0 right-10 h-64 w-64 rounded-full bg-emerald-500/5 blur-[90px] pointer-events-none" />
      <div className="absolute bottom-0 left-10 h-64 w-64 rounded-full bg-sky-500/5 blur-[90px] pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border relative z-10">
        <div className="flex items-center gap-3.5">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 border border-emerald-200 shadow-sm">
            <HeartPulse className="h-6 w-6 text-emerald-600 animate-pulse" />
          </div>
          <div>
            <h2 className="text-xl font-black text-foreground tracking-tight flex items-center gap-2">
              <span>Tình trạng sức khỏe đã biết</span>
            </h2>
            <p className="text-xs text-slate-600 font-normal mt-0.5 dark:text-slate-300">
              Chỉ chọn những tình trạng bạn đã được chẩn đoán hoặc biết chắc. Bạn có thể bỏ qua mục này nếu chưa rõ.
            </p>
          </div>
        </div>

        {/* Counter badge */}
        <div className="flex items-center gap-2 bg-background border border-border px-3.5 py-2 rounded-2xl self-start sm:self-center shrink-0 shadow-inner">
          <Sparkles className="w-4 h-4 text-emerald-600 animate-pulse shrink-0" />
          <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">Đã chọn:</span>
          <span className="text-base font-semibold text-emerald-700">
            {selectedConditions?.length || 0}
          </span>
          <span className="text-sm text-muted-foreground">mục</span>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* 1. LƯỚI THẺ CHỌN CẤU TRÚC (STRUCTURED CHOICE CARDS MATRIX)           */}
      {/* ===================================================================== */}
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 relative z-10">
        {COMMON_CHRONIC_CONDITIONS.map((cond) => {
          const isSelected = (selectedConditions || []).includes(cond.id);
          const IconComponent = cond.icon;

          return (
            <motion.button
              key={cond.id}
              type="button"
              tabIndex={0}
              whileHover={{ scale: 1.015, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => handleToggleCondition(cond.id)}
              className={cn(
                "p-4 rounded-2xl border text-left flex flex-col justify-between relative transition-all duration-300 group overflow-hidden outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 select-none cursor-pointer min-h-[140px]",
                isSelected
                  ? "border-2 border-emerald-600 bg-emerald-50/90 shadow-[0_4px_20px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/20"
                  : "border-border/90 bg-background/80 hover:border-sky-300 hover:bg-card hover:shadow-md"
              )}
            >
              {/* Background gradient lighting on selected state */}
              {isSelected && (
                <div className="absolute -right-6 -bottom-6 h-28 w-28 rounded-full bg-emerald-200/50 blur-2xl pointer-events-none" />
              )}

              {/* Top Row: Icon & Status Checkbox Badge */}
              <div className="flex items-center justify-between w-full relative z-10">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-xl border transition-transform duration-300 group-hover:scale-105 shadow-2xs",
                    isSelected ? "bg-emerald-600 text-white border-emerald-700 shadow-md" : cn(cond.themeColor.bg, cond.themeColor.border, cond.themeColor.text)
                  )}
                >
                  <IconComponent className="h-5 w-5" />
                </div>

                {/* Animated Check Icon */}
                <div className="h-6 w-6 flex items-center justify-center">
                  <AnimatePresence mode="wait">
                    {isSelected ? (
                      <motion.div
                        key="checked"
                        initial={{ scale: 0, rotate: -45 }}
                        animate={{ scale: 1, rotate: 0 }}
                        exit={{ scale: 0, rotate: 45 }}
                        transition={{ type: "spring", stiffness: 450, damping: 15 }}
                        className="h-6 w-6 rounded-full bg-emerald-600 text-white flex items-center justify-center shadow-md shadow-emerald-600/35 font-bold"
                      >
                        <CheckCircle2 className="h-4 w-4 text-white stroke-[2.5]" />
                      </motion.div>
                    ) : (
                      <div className="h-5 w-5 rounded-full border-2 border-slate-300 group-hover:border-slate-400 transition-colors dark:border-slate-700" />
                    )}
                  </AnimatePresence>
                </div>
              </div>

              {/* Bottom Text Content */}
              <div className="mt-4 relative z-10">
                <h3
                  className={cn(
                    "text-sm font-extrabold tracking-tight transition-colors duration-200 line-clamp-1",
                    isSelected ? "text-emerald-950 font-black" : "text-slate-800 group-hover:text-slate-950 dark:text-slate-100"
                  )}
                >
                  {cond.label}
                </h3>
                <p className="mt-2 text-sm leading-5 text-slate-600 line-clamp-2 dark:text-slate-300">
                  {cond.description}
                </p>
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* ===================================================================== */}
      {/* 2. TAG INPUT FIELD (THÊM BỆNH NỀN KHÔNG NẰM TRONG DANH SÁCH)          */}
      {/* ===================================================================== */}
      <div className="mt-8 pt-6 border-t border-border relative z-10">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div className="flex-1 space-y-2">
            <label htmlFor="custom-condition-input" className="text-sm font-extrabold text-slate-800 flex items-center gap-2 dark:text-slate-100">
              <BookmarkPlus className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Thông tin sức khỏe khác</span>
            </label>
            <p className="text-xs text-slate-600 dark:text-slate-300">
              Gõ tên bệnh lý, phẫu thuật hoặc tình trạng khác mà bạn muốn lưu, rồi nhấn Enter.
            </p>

            <div className="relative flex items-center gap-2.5 pt-1">
              <div className="relative flex-1">
                <input
                  id="custom-condition-input"
                  type="text"
                  value={customInput}
                  onChange={(e) => {
                    setCustomInput(e.target.value);
                    if (inputError) setInputError("");
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="Vd: Lupus ban đỏ hệ thống, Viêm gan B mãn tính, Tiền sử u nang..."
                  className={cn(
                    "w-full h-11 pl-4 pr-10 bg-background border border-border/90 rounded-2xl text-foreground font-sans text-sm font-semibold focus:outline-none focus:bg-card focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 transition-all placeholder:text-slate-400 shadow-inner",
                    inputError ? "border-rose-500 focus:ring-rose-500 text-rose-900 bg-rose-50/50" : ""
                  )}
                />
                {customInput && (
                  <button
                    type="button"
                    onClick={() => setCustomInput("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1 dark:hover:text-slate-300"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              <button
                type="button"
                onClick={handleAddCustomCondition}
                className="h-11 px-5 rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold text-xs flex items-center gap-2 transition-all duration-200 shrink-0 shadow-md shadow-emerald-600/25 active:scale-95"
              >
                <Plus className="w-4 h-4 stroke-[2.5]" />
                <span>Thêm</span>
              </button>
            </div>
            {/* Input error banner */}
            <AnimatePresence>
              {inputError && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="flex items-center gap-1.5 text-xs font-bold text-rose-600 pt-1"
                >
                  <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0 animate-bounce" />
                  <span>{inputError}</span>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Hiển thị danh sách Thẻ Tag Bệnh Nền Tùy Chỉnh (Custom Tags Pool) */}
        {customConditions.length > 0 && (
          <div className="mt-5 p-4.5 bg-background/90 border border-border rounded-2xl shadow-inner">
            <div className="text-xs font-extrabold text-slate-700 uppercase tracking-wider mb-3 flex items-center gap-2 dark:text-slate-200">
              <span>Danh sách bệnh nền đặc thù đã ghi nhận ({customConditions.length}):</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <AnimatePresence>
                {customConditions.map((cond) => (
                  <motion.div
                    key={cond}
                    layout
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8, y: -10 }}
                    transition={{ duration: 0.2 }}
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-card border border-emerald-300 text-emerald-900 text-xs font-extrabold shadow-xs group/tag hover:border-emerald-500 transition-all"
                  >
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                    <span>{cond}</span>
                    <button
                      type="button"
                      onClick={() => handleToggleCondition(cond)}
                      className="text-slate-400 hover:text-rose-600 hover:bg-rose-50 p-0.5 rounded-md transition-colors ml-1"
                      title="Xóa bệnh nền này"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
