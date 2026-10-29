import { Check, CirclePause, Clock3, MessageCircle, UserCheck, type LucideIcon } from "lucide-react";

import type { SessionStatusKind } from "@/components/patient/history-model";
import { cn } from "@/lib/utils";

/**
 * Nhãn trạng thái của một phiên trên màn lịch sử và màn chi tiết, theo đúng
 * ngôn ngữ người bệnh dùng: đang hỏi dở, chờ điều dưỡng, đã xác nhận, hay đã
 * được điều chỉnh. Trạng thái thẩm định đến từ `review_display_status` của
 * `routes_simple_triage.py` (`_map_pilot_review_status`), nguồn duy nhất; xem
 * `sessionStatusKind` về lý do phiên đang hỏi dở không mang nhãn "chờ xác nhận".
 */

interface StatusChipConfig {
  label: string;
  icon: LucideIcon;
  className: string;
}

function statusChipConfig(kind: SessionStatusKind, aiProposedEsi: number | null): StatusChipConfig {
  switch (kind) {
    case "IN_PROGRESS":
      return {
        label: "Đang hỏi dở",
        icon: MessageCircle,
        className: "border-brand-edge bg-brand-soft text-brand-ink",
      };
    case "STOPPED":
      return {
        label: "Phiên đã dừng",
        icon: CirclePause,
        className: "border-border bg-muted text-slate-700 dark:text-slate-300",
      };
    case "CONFIRMED":
      return {
        label: "Đã xác nhận",
        icon: Check,
        className:
          "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200",
      };
    case "ADJUSTED":
      return {
        label:
          aiProposedEsi !== null ? `Điều dưỡng điều chỉnh từ ESI ${aiProposedEsi}` : "Điều dưỡng đã đặt mức ưu tiên",
        icon: UserCheck,
        className:
          "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200",
      };
    case "AWAITING_NURSE":
    default:
      return {
        label: "Chờ điều dưỡng xác nhận",
        icon: Clock3,
        className:
          "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-200",
      };
  }
}

export function SimplePilotReviewBadge({
  kind,
  aiProposedEsi = null,
  className,
}: {
  kind: SessionStatusKind;
  /** Mức AI đề xuất, chỉ dùng để ghi "điều chỉnh từ ESI x". */
  aiProposedEsi?: number | null;
  className?: string;
}) {
  const { label, icon: Icon, className: tone } = statusChipConfig(kind, aiProposedEsi);
  return (
    <span
      className={cn(
        // rounded-2xl thay vì rounded-full: một dòng vẫn là viên thuốc, còn khi
        // màn hẹp buộc nhãn xuống dòng thì thành khối bo tròn chứ không méo.
        "inline-flex items-center gap-2 rounded-2xl border px-2 text-sm font-semibold leading-6",
        tone,
        className,
      )}
    >
      <Icon className="size-4 shrink-0" aria-hidden="true" />
      {label}
    </span>
  );
}
