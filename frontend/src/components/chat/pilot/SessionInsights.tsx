"use client";

import { useId } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Check } from "lucide-react";

import { DURATION, EASE_OUT, popVariants, riseVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";

import { formatRecordedValue, TRIAGE_STEPS, type RecordedSnapshot, type TriageStep } from "./pilot-transcript";

/**
 * Cột thông tin của phiên: những gì trợ lý đã ghi lại (để người bệnh tự kiểm
 * tra), đang ở bước nào, và lời nhắc không chờ trợ lý khi nguy kịch.
 */

export function RecordedPanel({
  recorded,
  freshFactIds,
  freshSymptomIds,
}: {
  recorded: RecordedSnapshot;
  /** Dữ kiện vừa được ghi ở lượt cuối -- nháy sáng một lần để mắt bắt được. */
  freshFactIds: ReadonlySet<string>;
  freshSymptomIds: ReadonlySet<string>;
}) {
  const titleId = useId();
  const empty = recorded.symptoms.length === 0 && recorded.facts.length === 0;

  return (
    <section aria-labelledby={titleId} className="rounded-3xl border border-border bg-card p-6">
      <h2 id={titleId} className="text-lg font-bold text-foreground">
        Mình đã ghi nhận
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Thấy chỗ nào chưa đúng, hãy nói lại trong khung chat.
      </p>

      {empty ? (
        <p className="mt-4 rounded-2xl bg-muted px-4 py-4 text-sm leading-6 text-muted-foreground">
          Kể triệu chứng của bạn, mình sẽ ghi lại ở đây để bạn kiểm tra.
        </p>
      ) : (
        <>
          {recorded.symptoms.length > 0 && (
            <ul aria-label="Triệu chứng đã kể" className="mt-4 flex flex-wrap gap-2">
              <AnimatePresence initial={false}>
                {recorded.symptoms.map((symptom) => (
                  <motion.li
                    key={symptom.concept_id}
                    layout
                    variants={riseVariants}
                    initial="hidden"
                    animate="visible"
                    className={cn(
                      "rounded-full border border-brand-edge bg-brand-soft px-4 py-2 text-sm font-semibold text-brand-ink",
                      freshSymptomIds.has(symptom.concept_id) && "fact-flash",
                    )}
                  >
                    {symptom.label}
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
          )}
          {recorded.facts.length > 0 && (
            <dl className="mt-4 flex flex-col">
              <AnimatePresence initial={false}>
                {recorded.facts.map((fact) => (
                  <motion.div
                    key={fact.fact_target_id}
                    layout
                    variants={riseVariants}
                    initial="hidden"
                    animate="visible"
                    className={cn(
                      "flex items-baseline justify-between gap-4 rounded-xl border-b border-border px-2 py-2 last:border-b-0",
                      freshFactIds.has(fact.fact_target_id) && "fact-flash",
                    )}
                  >
                    <dt className="text-sm text-muted-foreground">{fact.name}</dt>
                    <dd className="text-right text-base font-semibold text-foreground">{formatRecordedValue(fact)}</dd>
                  </motion.div>
                ))}
              </AnimatePresence>
            </dl>
          )}
        </>
      )}
    </section>
  );
}

export function StepsPanel({ step }: { step: TriageStep }) {
  const titleId = useId();
  return (
    <section aria-labelledby={titleId} className="rounded-3xl border border-border bg-card p-6">
      <h2 id={titleId} className="text-lg font-bold text-foreground">
        Các bước
      </h2>
      <ol className="mt-4 flex flex-col gap-4">
        {TRIAGE_STEPS.map(({ step: n, label }) => {
          const done = n < step;
          const current = n === step;
          return (
            <li
              key={n}
              aria-current={current ? "step" : undefined}
              className={cn(
                "flex items-center gap-4 text-base transition-colors duration-200",
                current ? "font-bold text-foreground" : done ? "text-foreground" : "text-muted-foreground",
              )}
            >
              <span
                className={cn(
                  "relative flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-bold transition-colors duration-300",
                  done && "bg-brand text-brand-foreground",
                  current && "border-2 border-brand text-brand-ink",
                  !done && !current && "border border-border",
                )}
              >
                <AnimatePresence mode="wait" initial={false}>
                  {done ? (
                    <motion.span key="done" variants={popVariants} initial="hidden" animate="visible" className="flex">
                      <Check className="size-4" strokeWidth={3} aria-hidden="true" />
                    </motion.span>
                  ) : (
                    <motion.span
                      key="number"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: DURATION.quick, ease: EASE_OUT }}
                    >
                      {n}
                    </motion.span>
                  )}
                </AnimatePresence>
              </span>
              {label}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

/**
 * Chỉ là lời nhắc bằng chữ: nút gọi 115 chỉ được đẩy lên khi phiên có dấu hiệu
 * nguy kịch hoặc kết quả ESI 1/2 -- còi báo động ở mọi màn sẽ dạy người ta lờ
 * nó đi.
 */
export function DangerSignsReminder() {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="rounded-3xl border border-rose-200 bg-rose-50 p-6 text-rose-950 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-100"
    >
      <h2 id={titleId} className="flex items-center gap-2 text-lg font-bold">
        <AlertTriangle className="size-5 shrink-0 text-rose-700 dark:text-rose-300" aria-hidden="true" />
        Không chờ trợ lý nếu nguy kịch
      </h2>
      <p className="mt-2 text-sm leading-6">
        Khó thở dữ dội, ngất, co giật, nôn ra máu, đau ngực lan ra tay: gọi ngay 115 hoặc đến cơ sở cấp cứu gần
        nhất.
      </p>
    </section>
  );
}
