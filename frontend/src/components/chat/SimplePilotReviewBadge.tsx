import React from "react";
import { CheckCircle2, Layers, Clock3 } from "lucide-react";

import type { SimpleTriageSessionSummaryDTO } from "@/types/simple-triage";

/**
 * Small badge for `review_display_status` (see `routes_simple_triage.py`'s
 * `_map_pilot_review_status` -- the single source of truth this mirrors),
 * shared by the pilot history list cards and the detail page so the 3
 * colors/labels are defined exactly once. Deliberately only 3 states, unlike
 * production's `HitlReviewStatus` (4 states): the pilot has no equivalent of
 * a red-flag-locked/EMERGENCY_REJECTED case.
 */

export type PilotReviewDisplayStatus = SimpleTriageSessionSummaryDTO["review_display_status"];

export function reviewBadgeConfig(status: PilotReviewDisplayStatus): {
  label: string;
  className: string;
  icon: typeof CheckCircle2;
} {
  switch (status) {
    case "APPROVED":
      return {
        label: "Điều dưỡng đã duyệt",
        className: "border-emerald-200 bg-emerald-50 text-emerald-900",
        icon: CheckCircle2,
      };
    case "OVERRIDDEN":
      return {
        label: "Có can thiệp (Override)",
        className: "border-amber-200 bg-amber-50 text-amber-900",
        icon: Layers,
      };
    case "PENDING_REVIEW":
    default:
      return {
        label: "Chưa duyệt",
        className: "border-sky-200 bg-sky-50 text-sky-900",
        icon: Clock3,
      };
  }
}

export function SimplePilotReviewBadge({ status }: { status: PilotReviewDisplayStatus }) {
  const { label, className, icon: Icon } = reviewBadgeConfig(status);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-bold ${className}`}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {label}
    </span>
  );
}
