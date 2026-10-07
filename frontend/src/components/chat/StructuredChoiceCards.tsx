"use client";

import React, { useId, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Check, ChevronRight } from "lucide-react";

import { EhrConfirmationCard } from "@/components/chat/EhrConfirmationCard";
import { PatientVitalsForm } from "@/components/chat/PatientVitalsForm";
import { cn } from "@/lib/utils";
import type { OptionItem, StructuredPayload } from "@/types/triage-chat";

interface StructuredChoiceCardsProps {
  payload: StructuredPayload;
  onSubmitAnswer: (
    answer: string | string[] | number,
    optionId?: string,
  ) => void;
  disabled?: boolean;
}

export function StructuredChoiceCards({
  payload,
  onSubmitAnswer,
  disabled = false,
}: StructuredChoiceCardsProps) {
  const [selectedChips, setSelectedChips] = useState<string[]>([]);
  const [selectedScale, setSelectedScale] = useState<number | null>(null);
  const scaleLabelId = useId();
  const shouldReduceMotion = useReducedMotion();

  const rawScaleMin = payload.minScale ?? 0;
  const rawScaleMax = payload.maxScale ?? 10;
  const scaleMin = Math.min(rawScaleMin, rawScaleMax);
  const scaleMax = Math.max(rawScaleMin, rawScaleMax);
  const scalePosition = selectedScale ?? scaleMin;

  if (payload.submitted) return null;

  if (payload.optionsType === "vitals_form" && payload.fields) {
    return (
      <PatientVitalsForm
        fields={payload.fields}
        disabled={disabled}
        onSubmitAnswer={onSubmitAnswer}
      />
    );
  }

  const isEhrConfirmation = payload.options?.some((option) =>
    ["ehr_confirmed", "ehr_changed", "ehr_unsure"].includes(option.id),
  );

  if (isEhrConfirmation && payload.options) {
    return (
      <EhrConfirmationCard
        snapshot={payload.ehrSnapshot}
        options={payload.options}
        disabled={disabled}
        onSubmitAnswer={onSubmitAnswer}
      />
    );
  }

  if (payload.optionsType === "single" && payload.options) {
    return (
      <div className="mt-4 w-full space-y-3 font-sans">
        {payload.options.map((option, index) => (
          <motion.button
            key={option.id}
            type="button"
            disabled={disabled}
            onClick={() => onSubmitAnswer(option.value, option.id)}
            initial={shouldReduceMotion ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: shouldReduceMotion ? 0 : 0.2,
              delay: shouldReduceMotion ? 0 : index * 0.05,
            }}
            className="group flex min-h-14 min-w-11 w-full cursor-pointer select-none items-center justify-between rounded-xl border-2 border-slate-200 bg-white p-4 text-left text-slate-900 transition-colors hover:border-sky-500 hover:bg-sky-50/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-800 dark:bg-zinc-950 dark:text-slate-100 dark:hover:border-sky-400 dark:hover:bg-sky-950/50 sm:p-5"
          >
            <span className="flex min-w-0 flex-1 flex-col pr-4">
              <span className="text-base font-bold leading-snug transition-colors group-hover:text-sky-900 dark:group-hover:text-sky-200 sm:text-lg">
                {option.label}
              </span>
              {option.description && (
                <span className="mt-1 block text-sm font-medium leading-relaxed text-slate-600 dark:text-slate-400">
                  {option.description}
                </span>
              )}
            </span>
            <span className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-100 text-slate-600 transition-colors group-hover:border-sky-500 group-hover:bg-sky-600 group-hover:text-white dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:group-hover:bg-sky-500">
              <ChevronRight className="size-5" aria-hidden="true" />
            </span>
          </motion.button>
        ))}
      </div>
    );
  }

  if (payload.optionsType === "multiple" && payload.options) {
    const options = payload.options;

    const toggleChip = (option: OptionItem) => {
      const value = String(option.value);
      const exclusiveValues = new Set(
        options
          .filter((candidate) => candidate.isExclusive)
          .map((candidate) => String(candidate.value)),
      );

      setSelectedChips((currentSelection) => {
        if (currentSelection.includes(value)) {
          return currentSelection.filter((item) => item !== value);
        }
        if (option.isExclusive) return [value];

        return [
          ...currentSelection.filter((item) => !exclusiveValues.has(item)),
          value,
        ];
      });
    };

    return (
      <div className="mt-4 w-full space-y-5 font-sans">
        <div className="flex flex-wrap gap-3">
          {options.map((option, index) => {
            const isSelected = selectedChips.includes(String(option.value));

            return (
              <motion.button
                key={option.id}
                type="button"
                disabled={disabled}
                aria-pressed={isSelected}
                onClick={() => toggleChip(option)}
                initial={shouldReduceMotion ? false : { opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{
                  duration: shouldReduceMotion ? 0 : 0.2,
                  delay: shouldReduceMotion ? 0 : index * 0.04,
                }}
                className={cn(
                  "flex min-h-12 min-w-11 cursor-pointer select-none items-center gap-3 rounded-xl border-2 px-5 py-3 text-base font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 disabled:cursor-not-allowed disabled:opacity-60",
                  isSelected
                    ? "border-sky-600 bg-sky-600 text-white"
                    : "border-slate-200 bg-white text-slate-800 hover:border-sky-500 hover:bg-sky-50/80 dark:border-slate-800 dark:bg-zinc-950 dark:text-slate-200 dark:hover:bg-zinc-900",
                )}
              >
                <span
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-lg border-2",
                    isSelected
                      ? "border-white bg-white text-sky-700"
                      : "border-slate-300 bg-slate-100 dark:border-slate-700 dark:bg-slate-900",
                  )}
                  aria-hidden="true"
                >
                  {isSelected && <Check className="size-4" />}
                </span>
                <span>{option.label}</span>
              </motion.button>
            );
          })}
        </div>

        <button
          type="button"
          disabled={disabled || selectedChips.length === 0}
          onClick={() => onSubmitAnswer(selectedChips)}
          className="flex min-h-[52px] min-w-11 w-full cursor-pointer items-center justify-center gap-2.5 rounded-xl bg-sky-600 px-6 py-4 text-base font-bold text-white transition-colors hover:bg-sky-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500 dark:disabled:bg-slate-800 dark:disabled:text-slate-400 sm:text-lg"
        >
          <span>Xác nhận lựa chọn ({selectedChips.length} mục)</span>
          <ArrowRight className="size-5" aria-hidden="true" />
        </button>
      </div>
    );
  }

  if (payload.optionsType === "scale") {
    return (
      <div className="mt-5 w-full space-y-6 rounded-2xl border border-slate-200 bg-slate-50 p-6 font-sans dark:border-slate-800 dark:bg-zinc-950">
        <div className="rounded-xl border border-slate-200 bg-white p-5 text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100">
          <p id={scaleLabelId} className="text-sm font-semibold text-slate-600 dark:text-slate-300">
            Giá trị đã chọn
          </p>
          <p className="mt-2 font-mono text-3xl font-bold tracking-tight">
            {selectedScale === null ? "Chưa chọn" : selectedScale}
          </p>
        </div>

        <div className="space-y-3 px-2 py-2">
          <input
            type="range"
            min={scaleMin}
            max={scaleMax}
            step={1}
            value={scalePosition}
            onChange={(event) => setSelectedScale(Number(event.target.value))}
            onPointerUp={(event) => setSelectedScale(Number(event.currentTarget.value))}
            onKeyUp={(event) => {
              if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) {
                setSelectedScale(Number(event.currentTarget.value));
              }
            }}
            disabled={disabled}
            aria-labelledby={scaleLabelId}
            className="h-11 w-full cursor-pointer accent-sky-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
          />
          <div className="flex items-center justify-between border-t border-slate-200/80 px-1 pt-3 text-sm font-semibold text-slate-600 dark:border-slate-800 dark:text-slate-300">
            <span>Tối thiểu: {scaleMin}</span>
            <span>Tối đa: {scaleMax}</span>
          </div>
        </div>

        <button
          type="button"
          disabled={disabled || selectedScale === null}
          onClick={() => {
            if (selectedScale !== null) onSubmitAnswer(selectedScale);
          }}
          className="flex min-h-[52px] min-w-11 w-full cursor-pointer items-center justify-center gap-2.5 rounded-xl bg-sky-600 px-6 py-4 text-base font-bold text-white transition-colors hover:bg-sky-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500 dark:disabled:bg-slate-800 dark:disabled:text-slate-400 sm:text-lg"
        >
          <span>
            {selectedScale === null ? "Chọn một mức trước khi gửi" : `Gửi mức đã chọn: ${selectedScale}`}
          </span>
          <ArrowRight className="size-5" aria-hidden="true" />
        </button>
      </div>
    );
  }

  return null;
}
