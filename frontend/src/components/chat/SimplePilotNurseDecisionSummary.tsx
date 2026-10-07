"use client";

import { ArrowRight, CheckCircle2, FileText, UserCheck } from "lucide-react";

import { cn } from "@/lib/utils";
import type { SimpleTriageSessionSummaryDTO } from "@/types/simple-triage";

type PilotReviewStatus = SimpleTriageSessionSummaryDTO["review_display_status"];

function formatDecisionTime(value: string | null): string {
  if (!value) return "Chưa ghi nhận thời điểm";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

export function pilotAiProposedEsi(levels: number[]): number | null {
  const validLevels = levels.filter((level) => [1, 2, 3, 4, 5].includes(level));
  return validLevels.length > 0 ? Math.min(...validLevels) : null;
}

export function SimplePilotEsiBadge({
  aiProposedEsi,
  finalEsi,
  reviewStatus,
}: {
  aiProposedEsi: number | null;
  finalEsi: number | null;
  reviewStatus: PilotReviewStatus;
}) {
  const isReviewed = reviewStatus === "APPROVED" || reviewStatus === "OVERRIDDEN";
  const isAdjusted = reviewStatus === "OVERRIDDEN" && aiProposedEsi != null && finalEsi != null;
  const displayedEsi = isReviewed && finalEsi != null ? finalEsi : aiProposedEsi;
  if (displayedEsi == null) return null;

  const tone = displayedEsi <= 2
    ? "border-rose-200 bg-rose-50 text-rose-900"
    : displayedEsi === 3
      ? "border-amber-200 bg-amber-50 text-amber-900"
      : "border-emerald-200 bg-emerald-50 text-emerald-900";
  const label = isAdjusted
    ? `ESI ${aiProposedEsi} → ESI ${finalEsi}`
    : isReviewed
      ? `Điều dưỡng xác nhận ESI ${displayedEsi}`
      : `AI đề xuất ESI ${displayedEsi}`;

  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-bold", tone)}>
      {isAdjusted && <ArrowRight className="size-3.5" aria-hidden="true" />}
      {label}
    </span>
  );
}

export function SimplePilotNurseDecisionSummary({
  aiProposedEsi,
  finalEsi,
  reviewStatus,
  reviewerName,
  reviewedAt,
  decisionNote,
}: {
  aiProposedEsi: number | null;
  finalEsi: number | null;
  reviewStatus: PilotReviewStatus;
  reviewerName: string | null;
  reviewedAt: string | null;
  decisionNote: string | null;
}) {
  const isReviewed = reviewStatus === "APPROVED" || reviewStatus === "OVERRIDDEN";
  if (!isReviewed || finalEsi == null) return null;

  const isAdjusted = reviewStatus === "OVERRIDDEN";
  const tone = isAdjusted
    ? "border-amber-300 bg-amber-50"
    : "border-emerald-300 bg-emerald-50";
  const Icon = isAdjusted ? UserCheck : CheckCircle2;
  const actor = reviewerName ?? "Điều dưỡng";
  const note = decisionNote?.trim() || "Điều dưỡng không ghi chú thêm.";

  return (
    <section
      className={cn("space-y-4 rounded-2xl border p-5 text-foreground", tone)}
      aria-label="Kết quả thẩm định của điều dưỡng"
    >
      <div className="flex items-start gap-3">
        <Icon
          className={cn("mt-0.5 size-6 shrink-0", isAdjusted ? "text-amber-700" : "text-emerald-700")}
          aria-hidden="true"
        />
        <div>
          <h2 className={cn("text-base font-bold", isAdjusted ? "text-amber-950" : "text-emerald-950")}>
            {isAdjusted ? "Điều dưỡng đã điều chỉnh mức ưu tiên" : "Điều dưỡng đã xác nhận kết quả"}
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-700 dark:text-slate-200">
            {actor} đã lưu quyết định lúc {formatDecisionTime(reviewedAt)}. Kết quả thẩm định là kết quả chính thức của ca này.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3 rounded-xl border border-white bg-card/90 p-3 text-sm font-bold text-foreground">
        <span>AI đề xuất: ESI {aiProposedEsi ?? "chưa có"}</span>
        <ArrowRight className={cn("size-5", isAdjusted ? "text-amber-700" : "text-emerald-700")} aria-hidden="true" />
        <span>Kết quả điều dưỡng: ESI {finalEsi}</span>
      </div>

      <div className="flex items-start gap-2 border-t border-border/80 pt-3 text-sm leading-6 text-slate-800 dark:text-slate-100">
        <FileText className="mt-0.5 size-5 shrink-0 text-slate-600 dark:text-slate-300" aria-hidden="true" />
        <p>
          <span className="font-bold">Ghi chú điều dưỡng: </span>
          {note}
        </p>
      </div>
    </section>
  );
}
