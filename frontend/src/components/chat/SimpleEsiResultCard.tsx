"use client";

import React from "react";
import { motion } from "framer-motion";
import { BadgeCheck, PhoneCall, Siren } from "lucide-react";

import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { DURATION, EASE_OUT, dropVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { EsiLevel } from "@/types/clinical-history";

/**
 * Prominent, standalone callout for the single most severe matched ESI
 * level, shown right after the AI's last chat message on `/triage-pilot`.
 *
 * Real feedback (2026-08-29): the ESI result used to only ever appear as a
 * sentence buried inside the "chưa qua thẩm định" disclaimer paragraph
 * ("Mức ESI gợi ý: 2.") -- easy to miss, no visual weight. This makes the
 * number itself the headline plus one short, plain sentence on what that
 * level actually means for the patient, in the same ESI colours the nurse
 * screens use (`esiTheme`), so patient and nurse never see one level in two
 * colours.
 *
 * `esiLevel` must already be the single narrowed top level (see
 * triage-pilot/page.tsx's call site), never the full matched_esi_levels
 * array -- this component has no opinion on which level to show, only how
 * to present one. `source` says whose level it is: the AI's proposal, or the
 * level a nurse has already confirmed or adjusted.
 *
 * ESI 1/2 is announced (`role="alert"`) and carries its own `tel:115`: the
 * right action at those levels is to call, and the call button must not sit
 * below the fold behind facility lists. ESI 3-5 get no siren -- an alarm on a
 * result the system itself judged non-urgent teaches people to ignore it.
 */

export function isUrgentEsi(esiLevel: EsiLevel): boolean {
  return esiLevel <= 2;
}

const ESI_MEANING: Record<EsiLevel, string> = {
  1: "Đe dọa tính mạng — cần cấp cứu ngay lập tức, không chờ đợi.",
  2: "Nguy cơ cao — cần được nhân viên y tế đánh giá càng sớm càng tốt.",
  3: "Cần nhiều xét nghiệm/xử trí hơn nhưng tình trạng còn ổn định — nên đến cơ sở y tế sớm.",
  4: "Vấn đề ở mức nhẹ — có thể khám theo lịch thông thường.",
  5: "Không khẩn cấp — có thể tự theo dõi hoặc khám định kỳ.",
};

interface SimpleEsiResultCardProps {
  esiLevel: EsiLevel;
  source?: "AI" | "NURSE";
}

export function SimpleEsiResultCard({ esiLevel, source = "AI" }: SimpleEsiResultCardProps) {
  const theme = esiTheme(esiLevel);
  const urgent = isUrgentEsi(esiLevel);
  const confirmed = source === "NURSE";

  return (
    <motion.section
      variants={dropVariants}
      initial="hidden"
      animate="visible"
      role={urgent ? "alert" : undefined}
      aria-live={urgent ? "assertive" : undefined}
      aria-label={`Kết quả sàng lọc: ESI ${esiLevel}, ${theme.label}`}
      className={cn(
        "overflow-hidden rounded-3xl border-2 bg-card shadow-sm",
        urgent ? "border-rose-600 dark:border-rose-500" : "border-border",
      )}
    >
      <div
        className={cn(
          "flex items-center justify-between gap-4 px-4 py-2 sm:px-6",
          urgent
            ? "bg-rose-700 text-white"
            : confirmed
              ? "bg-emerald-50 text-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-100"
              : "bg-muted text-foreground",
        )}
      >
        <p className="flex min-h-10 items-center gap-2 text-sm font-bold">
          {urgent ? (
            <Siren className="size-5 shrink-0" aria-hidden="true" />
          ) : confirmed ? (
            <BadgeCheck className="size-5 shrink-0" aria-hidden="true" />
          ) : null}
          {confirmed ? "Điều dưỡng đã xác nhận mức này" : "Mức đề xuất của AI, chờ nhân viên y tế xem lại"}
        </p>
      </div>

      <div className="p-4 sm:p-6">
        <div className="flex items-center gap-4">
          {/* Thẻ lên trước, mức ESI bật vào sau -- mắt đi theo đúng thứ tự đọc. */}
          <motion.span
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: DURATION.base, ease: EASE_OUT, delay: 0.15 }}
            aria-hidden="true"
            className={cn(
              "flex size-16 shrink-0 flex-col items-center justify-center rounded-2xl border leading-none",
              theme.chip,
            )}
          >
            <span className="text-xs font-bold">ESI</span>
            <span className="text-3xl font-extrabold">{esiLevel}</span>
          </motion.span>
          <div className="min-w-0">
            <h2 className="text-xl font-extrabold tracking-tight text-foreground">
              ESI {esiLevel} · {theme.label}
            </h2>
            <p className="mt-2 text-base leading-7 text-foreground">{ESI_MEANING[esiLevel]}</p>
          </div>
        </div>

        {!confirmed && (
          <p className="mt-4 text-sm leading-6 text-muted-foreground">
            Đây không phải chẩn đoán. Kết quả đã được chuyển tới nhân viên y tế để xem lại.
          </p>
        )}

        {urgent && (
          <motion.a
            href="tel:115"
            whileTap={{ scale: 0.97 }}
            aria-label="Gọi Tổng đài Cấp cứu Quốc gia 115"
            className="ring-pulse mt-4 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-rose-700 px-4 text-lg font-extrabold text-white transition-colors hover:bg-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
          >
            <PhoneCall className="size-5 shrink-0" aria-hidden="true" />
            {esiLevel === 1 ? "Gọi 115 ngay" : "Gọi 115"}
          </motion.a>
        )}
      </div>
    </motion.section>
  );
}
