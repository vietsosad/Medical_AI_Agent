"use client";

import React from "react";
import { Siren } from "lucide-react";
import { getEsiBadgeConfig } from "@/lib/history-utils";
import type { EsiLevel } from "@/types/clinical-history";

/**
 * Prominent, standalone callout for the single most severe matched ESI
 * level, shown right after the AI's last chat message on `/triage-pilot`.
 *
 * Real feedback (2026-08-29): the ESI result used to only ever appear as a
 * sentence buried inside the "chưa qua thẩm định" disclaimer paragraph
 * ("Mức ESI gợi ý: 2.") -- easy to miss, no visual weight. This makes the
 * number itself the headline (large colored badge) plus one short, plain
 * sentence on what that level actually means for the patient, using
 * production's own `getEsiBadgeConfig` (`lib/history-utils.ts`) for the
 * exact same color language `/history` already uses -- not reinvented here.
 *
 * `esiLevel` must already be the single narrowed top level (see
 * triage-pilot/page.tsx's call site), never the full matched_esi_levels
 * array -- this component has no opinion on which level to show, only how
 * to present one.
 */

const ESI_MEANING: Record<EsiLevel, string> = {
  1: "Đe dọa tính mạng — cần cấp cứu ngay lập tức, không chờ đợi.",
  2: "Nguy cơ cao — cần được nhân viên y tế đánh giá càng sớm càng tốt.",
  3: "Cần nhiều xét nghiệm/xử trí hơn nhưng tình trạng còn ổn định — nên đến cơ sở y tế sớm.",
  4: "Vấn đề ở mức nhẹ — có thể khám theo lịch thông thường.",
  5: "Không khẩn cấp — có thể tự theo dõi hoặc khám định kỳ.",
};

export function SimpleEsiResultCard({ esiLevel }: { esiLevel: EsiLevel }) {
  const config = getEsiBadgeConfig(esiLevel);

  return (
    <div className="flex items-center gap-4 rounded-2xl border-2 border-border bg-card p-4 shadow-sm sm:p-5">
      <span
        className={`flex size-14 shrink-0 items-center justify-center rounded-full border-2 text-lg font-black ${config.colorClass}`}
        aria-hidden="true"
      >
        {esiLevel}
      </span>
      <div className="min-w-0">
        <p className="flex items-center gap-1.5 text-base font-black tracking-tight text-slate-950 dark:text-slate-50">
          <Siren className="size-4 shrink-0 text-rose-600" aria-hidden="true" />
          {config.label}
        </p>
        <p className="mt-0.5 text-sm leading-6 text-slate-700 dark:text-slate-200">{ESI_MEANING[esiLevel]}</p>
      </div>
    </div>
  );
}
