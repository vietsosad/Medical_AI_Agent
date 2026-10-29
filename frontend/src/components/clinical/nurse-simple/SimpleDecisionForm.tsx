"use client";

import { useId, useMemo } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import { CheckCircle2, Loader2, SlidersHorizontal } from "lucide-react";
import { useController, useForm, useWatch } from "react-hook-form";

import {
  ESI_LEVELS,
  MIN_ADJUST_NOTE_LENGTH,
  REASON_OPTIONS,
  buildDecisionSchema,
  decisionTypeFor,
  esiRelation,
  type DecisionFormValues,
  type EsiLevel,
} from "@/components/clinical/nurse-simple/case/decision-schema";
import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { DURATION, EASE_OUT, enterTransition, layoutTransition, staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useSubmitSimpleDecision } from "@/queries/useSimpleNurseQueries";
import type { SimpleDecisionType } from "@/types/simple-nurse";

/**
 * Bàn chốt ESI của điều dưỡng: chỉ CONFIRM_ESI / ADJUST_ESI (simple_agent
 * không có luồng chuyên khoa). Lưu là đóng ca luôn (`review_status ->
 * HANDED_OFF`), không có bước bàn giao riêng.
 *
 * Không còn hai nút "xác nhận" / "điều chỉnh" tách rời: điều dưỡng chọn thẳng
 * mức ESI. Chọn đúng mức AI đề xuất là xác nhận, chọn mức khác là điều chỉnh,
 * và nút chính đọc lên đúng việc sắp làm ("Xác nhận ESI 2" / "Điều chỉnh
 * thành ESI 3"). Ca AI chưa đủ dữ liệu không được chọn sẵn mức nào: một con số
 * điền sẵn ở ca thiếu dữ liệu là lời gợi ý mà không ai đứng tên.
 */

export interface DecidedSummary {
  finalEsi: number;
  decisionType: SimpleDecisionType;
}

function submitLabel(aiEsi: EsiLevel | null, finalEsi: number | null): string {
  if (finalEsi === null) return "Chốt mức ESI";
  if (decisionTypeFor(aiEsi, finalEsi) === "CONFIRM_ESI") return `Xác nhận ESI ${finalEsi}`;
  return aiEsi === null ? `Chốt ESI ${finalEsi}` : `Điều chỉnh thành ESI ${finalEsi}`;
}

const fieldError = "mt-2 text-sm font-semibold text-rose-700 dark:text-rose-400";

/** Đổi xác nhận <-> điều chỉnh thì danh sách lý do mới nổi lên lần lượt. */
const reasonVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: { ...enterTransition, delay: staggerDelay(index) },
  }),
};

export function SimpleDecisionForm({
  sessionId,
  caseVersion,
  aiEsi,
  onDecided,
  onError,
}: {
  sessionId: string;
  caseVersion: number;
  aiEsi: EsiLevel | null;
  /** Gọi sau khi backend đã lưu quyết định -- nơi gọi lo phần xác nhận và chuyển trang. */
  onDecided?: (summary: DecidedSummary) => void;
  onError?: (error: Error) => void;
}) {
  const decision = useSubmitSimpleDecision(sessionId);
  const schema = useMemo(() => buildDecisionSchema(aiEsi), [aiEsi]);
  const ids = useId();
  const relationId = `${ids}-relation`;
  const esiErrorId = `${ids}-esi-error`;
  const reasonErrorId = `${ids}-reason-error`;
  const noteId = `${ids}-note`;
  const noteHintId = `${ids}-note-hint`;

  const {
    control,
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitted },
  } = useForm<DecisionFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      final_esi: aiEsi,
      reason_code: aiEsi ? "MATCHES_PROTOCOL" : "ADDITIONAL_CLINICAL_JUDGMENT",
      note: "",
    },
  });

  const { field: esiField } = useController({ control, name: "final_esi" });
  const { field: reasonField } = useController({ control, name: "reason_code" });
  const note = useWatch({ control, name: "note" }) ?? "";

  const finalEsi = esiField.value;
  const decisionType = decisionTypeFor(aiEsi, finalEsi);
  const reasons = REASON_OPTIONS[decisionType];
  const noteRequired = decisionType === "ADJUST_ESI";
  const relation = esiRelation(aiEsi, finalEsi);
  const label = submitLabel(aiEsi, finalEsi);
  const pending = decision.isPending;

  const chooseEsi = (level: EsiLevel) => {
    const nextType = decisionTypeFor(aiEsi, level);
    esiField.onChange(level);
    // Đổi giữa xác nhận và điều chỉnh thì danh sách lý do đổi theo; lý do cũ
    // không còn hợp lệ nên chọn sẵn lý do đầu tiên của loại mới.
    if (nextType !== decisionType) {
      setValue("reason_code", REASON_OPTIONS[nextType][0].value, { shouldValidate: isSubmitted });
    }
  };

  const submit = handleSubmit((values) => {
    if (values.final_esi === null) return;
    const type = decisionTypeFor(aiEsi, values.final_esi);
    const chosen = values.final_esi;
    decision.mutate(
      {
        version: caseVersion,
        decision_type: type,
        final_esi: chosen,
        reason_code: values.reason_code,
        note: values.note.trim() || null,
      },
      {
        onSuccess: (result) => onDecided?.({ finalEsi: result.final_esi ?? chosen, decisionType: type }),
        onError: (error) => onError?.(error),
      },
    );
  });

  // Gắn ref của RHF vào ô đang chọn (hoặc ô đầu tiên) để lỗi "chưa chọn mức"
  // đưa tiêu điểm bàn phím về đúng nhóm nút.
  const focusTarget = finalEsi ?? ESI_LEVELS[0];

  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-6">
      {/* ------------------------------------------------------- MỨC BẠN CHỐT */}
      <fieldset aria-describedby={errors.final_esi ? `${relationId} ${esiErrorId}` : relationId}>
        <legend className="text-sm font-bold text-foreground">Mức bạn chốt</legend>
        <div className="mt-4 grid grid-cols-5 gap-2">
          {ESI_LEVELS.map((level) => {
            const theme = esiTheme(level);
            const selected = finalEsi === level;
            const proposedByAi = aiEsi === level;
            return (
              <motion.label
                key={level}
                whileTap={{ scale: 0.97 }}
                className={cn(
                  "relative flex min-h-16 cursor-pointer flex-col items-center justify-center rounded-xl border leading-none",
                  "transition-[translate,background-color,box-shadow] duration-200",
                  "has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand has-[:focus-visible]:ring-offset-2 has-[:focus-visible]:ring-offset-card",
                  theme.chip,
                  selected
                    ? "shadow-md"
                    : "bg-card hover:-translate-y-0.5 dark:text-foreground motion-reduce:hover:translate-y-0",
                )}
              >
                <input
                  ref={level === focusTarget ? esiField.ref : undefined}
                  type="radio"
                  name={esiField.name}
                  value={level}
                  checked={selected}
                  onChange={() => chooseEsi(level)}
                  onBlur={esiField.onBlur}
                  className="sr-only"
                />
                {/* Một vòng duy nhất trượt từ mức cũ sang mức mới: mắt thấy
                    ngay mình vừa đổi từ đâu sang đâu. */}
                {selected && (
                  <motion.span
                    layoutId={`esi-choice-${sessionId}`}
                    transition={layoutTransition}
                    className="pointer-events-none absolute -inset-px rounded-xl border-2 border-current"
                    aria-hidden="true"
                  />
                )}
                {/* Mức AI đề xuất luôn mang nhãn "AI", kể cả khi điều dưỡng đã
                    chọn mức khác -- để thấy mình đang điều chỉnh từ đâu. */}
                {proposedByAi && (
                  <span
                    aria-hidden="true"
                    className="absolute -top-2 left-1/2 z-10 -translate-x-1/2 rounded-full bg-slate-900 px-2 text-xs font-bold leading-4 text-white dark:bg-slate-100 dark:text-slate-900"
                  >
                    AI
                  </span>
                )}
                <span aria-hidden="true" className="text-xs font-bold">
                  ESI
                </span>
                <span aria-hidden="true" className="text-xl font-black leading-tight tabular-nums">
                  {level}
                </span>
                <span className="sr-only">
                  ESI {level} · {theme.label}
                  {proposedByAi ? " · AI đề xuất" : ""}
                </span>
              </motion.label>
            );
          })}
        </div>

        <p id={relationId} aria-live="polite" className="mt-2 min-h-6 text-sm leading-6 text-foreground">
          {finalEsi !== null && (
            <span className="font-bold">
              ESI {finalEsi} · {esiTheme(finalEsi).label}
            </span>
          )}
          {finalEsi !== null && relation && <span className="text-muted-foreground"> — </span>}
          {relation && <span className="text-muted-foreground">{relation}</span>}
        </p>
        {errors.final_esi?.message && (
          <p id={esiErrorId} role="alert" className={fieldError}>
            {errors.final_esi.message}
          </p>
        )}
      </fieldset>

      {/* --------------------------------------------------------------- LÝ DO */}
      <fieldset aria-describedby={errors.reason_code ? reasonErrorId : undefined}>
        <legend className="text-sm font-bold text-foreground">Lý do</legend>
        <div className="mt-2 flex flex-col gap-2">
          <AnimatePresence initial={false}>
            {reasons.map((reason, index) => {
              const checked = reasonField.value === reason.value;
              return (
                <motion.label
                  key={reason.value}
                  custom={index}
                  variants={reasonVariants}
                  initial="hidden"
                  animate="visible"
                  className={cn(
                    "flex min-h-11 cursor-pointer items-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold leading-6 transition-colors",
                    "has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand has-[:focus-visible]:ring-offset-2 has-[:focus-visible]:ring-offset-card",
                    checked
                      ? "border-brand bg-brand-soft text-brand-ink"
                      : "border-border text-foreground hover:bg-muted",
                  )}
                >
                  <input
                    type="radio"
                    name={reasonField.name}
                    value={reason.value}
                    checked={checked}
                    onChange={() => reasonField.onChange(reason.value)}
                    onBlur={reasonField.onBlur}
                    className="size-4 shrink-0 accent-brand"
                  />
                  {reason.label}
                </motion.label>
              );
            })}
          </AnimatePresence>
        </div>
        {errors.reason_code?.message && (
          <p id={reasonErrorId} role="alert" className={fieldError}>
            {errors.reason_code.message}
          </p>
        )}
      </fieldset>

      {/* ------------------------------------------------------------ GHI CHÚ */}
      <div>
        <label htmlFor={noteId} className="text-sm font-bold text-foreground">
          Ghi chú cho người bệnh{" "}
          <span className="font-medium text-muted-foreground">
            {noteRequired ? `(bắt buộc, tối thiểu ${MIN_ADJUST_NOTE_LENGTH} ký tự)` : "(không bắt buộc)"}
          </span>
        </label>
        <textarea
          id={noteId}
          rows={3}
          {...register("note")}
          aria-invalid={Boolean(errors.note)}
          aria-describedby={noteHintId}
          placeholder="Ghi nhận ngắn, khách quan; không chẩn đoán hoặc kê đơn."
          className="mt-2 w-full resize-none rounded-xl border border-border bg-background px-4 py-2 text-base leading-6 text-foreground placeholder:text-muted-foreground focus-visible:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 aria-[invalid=true]:border-rose-400"
        />
        {errors.note?.message ? (
          <p id={noteHintId} role="alert" className={fieldError}>
            {errors.note.message}
          </p>
        ) : (
          <p id={noteHintId} className="mt-2 text-sm text-muted-foreground">
            {noteRequired
              ? `Người bệnh đọc được ghi chú này. Đã nhập ${note.trim().length}/${MIN_ADJUST_NOTE_LENGTH} ký tự tối thiểu.`
              : "Người bệnh đọc được ghi chú này."}
          </p>
        )}
      </div>

      {/* --------------------------------------------------------- NÚT CHỐT */}
      <div>
        <motion.button
          type="submit"
          disabled={pending}
          whileTap={{ scale: 0.97 }}
          aria-label={pending ? "Đang lưu quyết định" : label}
          className="flex min-h-12 w-full items-center justify-center overflow-hidden rounded-2xl bg-brand px-4 text-base font-extrabold text-brand-foreground shadow-lg shadow-brand/25 transition-colors hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:opacity-70"
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={pending ? "pending" : label}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: DURATION.quick, ease: EASE_OUT }}
              className="flex items-center gap-2"
            >
              {pending ? (
                <Loader2 className="size-5 animate-spin motion-reduce:animate-none" aria-hidden="true" />
              ) : decisionType === "CONFIRM_ESI" ? (
                <CheckCircle2 className="size-5" aria-hidden="true" />
              ) : (
                <SlidersHorizontal className="size-5" aria-hidden="true" />
              )}
              {pending ? "Đang lưu..." : label}
            </motion.span>
          </AnimatePresence>
        </motion.button>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          {aiEsi !== null ? "Chọn mức khác để điều chỉnh, nút sẽ đổi thành “Điều chỉnh”. " : ""}
          Lưu quyết định sẽ đóng ca.
        </p>
        {decision.error && (
          <p role="alert" className={cn(fieldError, "text-center")}>
            {decision.error.message}
          </p>
        )}
      </div>
    </form>
  );
}
