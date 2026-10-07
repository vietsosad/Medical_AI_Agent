"use client";

import React from "react";
import Link from "next/link";
import {
  Clock,
  ShieldCheck,
  AlertTriangle,
  Zap,
  FileText,
  CheckCircle2,
  Stethoscope,
  ChevronRight,
  MessageCircle,
  CircleX,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getEsiBadgeConfig } from "@/lib/history-utils";
import type { TriageHistoryListItemDTO, HitlReviewStatus } from "@/types/clinical-history";
import {
  getHistorySessionHref,
  getTriageSessionStatusLabel,
  isResumableTriageSession,
} from "@/components/history/history-session-state";

export interface HistorySessionCardProps {
  session: TriageHistoryListItemDTO;
  className?: string;
}

const renderHitlBadge = (status: HitlReviewStatus) => {
  switch (status) {
    case "APPROVED":
      return (
        <span className="px-2.5 py-1 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] font-bold flex items-center gap-1.5 shadow-sm shrink-0">
          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
          <span>Đã Duyệt</span>
        </span>
      );
    case "OVERRIDDEN":
      return (
        <span className="px-2.5 py-1 rounded-md bg-amber-50 border border-amber-200 text-amber-800 text-[11px] font-bold flex items-center gap-1.5 shadow-sm shrink-0">
          <Zap className="w-3 h-3 text-amber-600" />
          <span>Điều chỉnh lâm sàng</span>
        </span>
      );
    case "PENDING_REVIEW":
      return (
        <span className="px-2.5 py-1 rounded-md bg-muted border border-border text-slate-700 text-[11px] font-bold flex items-center gap-1.5 shadow-sm shrink-0 dark:text-slate-200">
          <Clock className="w-3 h-3 text-muted-foreground animate-spin" style={{ animationDuration: "10s" }} />
          <span>Chờ Thẩm Định</span>
        </span>
      );
    case "EMERGENCY_REJECTED":
      return (
        <span className="px-2.5 py-1 rounded-md bg-rose-50 border border-rose-200 text-rose-800 text-[11px] font-bold flex items-center gap-1.5 shadow-sm shrink-0">
          <AlertTriangle className="w-3 h-3 text-rose-600" />
          <span>Cấp cứu khẩn cấp</span>
        </span>
      );
    default:
      return null;
  }
};

const formatCardTimestamp = (isoString: string): string => {
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return "Thời gian không xác định";
    const time = date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
    const day = date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
    return `${time} • Ngày ${day}`;
  } catch {
    return isoString;
  }
};

/**
 * Thẻ ca khám trong lịch sử của người bệnh.
 */
export const HistorySessionCard: React.FC<HistorySessionCardProps> = ({
  session,
  className,
}) => {
  const esiConfig = getEsiBadgeConfig(session.final_esi);
  const href = getHistorySessionHref(session);
  const canResume = isResumableTriageSession(session.status);

  return (
    <div
      className={cn(
        "group relative bg-card border border-border/90 rounded-2xl p-5 md:p-6 shadow-sm hover:border-sky-300 hover:shadow-md transition-all duration-300 text-left overflow-hidden font-sans",
        className
      )}
    >
      {/* Dải phản quang dọc vách trái thẻ */}
      <div
        className={cn(
          "absolute top-0 bottom-0 left-0 w-2 transition-all duration-300 group-hover:w-2.5",
          session.final_esi != null && session.final_esi <= 2 ? "bg-rose-600" :
          session.final_esi === 3 ? "bg-amber-500" :
          session.final_esi === 4 ? "bg-sky-600" :
          session.final_esi === 5 ? "bg-emerald-600" : "bg-slate-400"
        )}
      />

      <div className="pl-3 space-y-4">
        {/* ====================================================================
            TẦNG 1 (HEADER): TIMESTAMP + HUY HIỆU ESI + HUY HIỆU HITL
            ==================================================================== */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono font-bold">
            <span className="p-1.5 rounded-lg bg-muted border border-border text-sky-700">
              <Clock className="w-3.5 h-3.5 stroke-[2.5]" />
            </span>
            <span className="text-slate-800 font-extrabold dark:text-slate-100">{formatCardTimestamp(session.created_at)}</span>
            <span className="text-slate-300">|</span>
            <span className="text-[11px] text-muted-foreground uppercase font-mono">
              ID: #{session.session_id.slice(-8)}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {session.status === "IN_PROGRESS" ? (
              <span className="flex min-h-12 items-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 text-sm font-bold text-sky-900">
                <MessageCircle className="size-5 text-sky-700" aria-hidden="true" />
                Đang thu thập
              </span>
            ) : session.status === "CANCELLED" ? (
              <span className="flex min-h-12 items-center gap-2 rounded-xl border border-slate-300 bg-muted px-4 text-sm font-bold text-slate-800 dark:text-slate-100 dark:border-slate-700">
                <CircleX className="size-5 text-slate-600 dark:text-slate-300" aria-hidden="true" />
                Đã hủy
              </span>
            ) : (
              renderHitlBadge(session.hitl_status)
            )}

            <span
              className={cn(
                "px-2 py-1 rounded-md text-[11px] border tracking-tight shrink-0 flex items-center gap-1.5 font-bold shadow-sm",
                esiConfig.colorClass
              )}
            >
              <span>{esiConfig.badgeText}</span>
            </span>
          </div>
        </div>

        {/* ====================================================================
            TẦNG 2 (BODY): TRIỆU CHỨNG CHÍNH + TÓM TẮT SBAR
            ==================================================================== */}
        <Link href={href} className="block space-y-3 pt-1 group/body">
          <h3 className="text-lg md:text-xl font-extrabold text-foreground group-hover/body:text-sky-700 transition-colors duration-200 flex items-start gap-2.5 leading-snug">
            <Stethoscope className="w-5 h-5 text-sky-600 shrink-0 mt-1 stroke-[2.5]" />
            <span>{session.chief_complaint || "Ca khám đang thu thập thông tin"}</span>
          </h3>

          <div className="pl-3 sm:pl-4 border-l-2 border-slate-300 group-hover/body:border-sky-500 transition-colors py-1 my-2 bg-background rounded-r-xl dark:border-slate-700">
            <p className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1 flex items-center gap-1.5 dark:text-slate-200">
              <FileText className="w-3.5 h-3.5 text-sky-600 stroke-[2.5]" />
              <span>
                {session.sbar_finalized ? "Trích lục SBAR đã hoàn tất:" : "Trạng thái ca khám:"}
              </span>
            </p>
            <p className="text-sm text-slate-700 font-normal leading-relaxed line-clamp-2 italic dark:text-slate-200">
              {session.sbar_finalized
                ? session.sbar_snippet
                : session.sbar_snippet || getTriageSessionStatusLabel(session.status)}
            </p>
          </div>
        </Link>

        {/* ====================================================================
            TẦNG 3 (FOOTER CTA)
            ==================================================================== */}
        <div className="pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs sm:text-sm">
          <span className="text-slate-400 text-xs font-medium flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            <span>Được bảo vệ bởi AI Triage</span>
          </span>

          <div className="flex items-center gap-2">
            <Link
              href={href}
              className="px-3.5 py-2 rounded-lg bg-background hover:bg-muted border border-border text-slate-700 font-semibold text-xs flex items-center gap-1.5 transition-all shadow-sm group/link1 dark:text-slate-200"
            >
              {canResume ? (
                <MessageCircle className="size-5 text-sky-700" aria-hidden="true" />
              ) : (
                <FileText className="size-5 text-muted-foreground" aria-hidden="true" />
              )}
              <span>
                {canResume
                  ? "Tiếp tục ca khám"
                  : session.status === "HITL_REVIEWING"
                    ? "Theo dõi thẩm định"
                    : session.sbar_finalized
                      ? "Xem SBAR"
                      : "Xem diễn biến"}
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover/link1:translate-x-0.5 transition-transform" />
            </Link>

          </div>
        </div>
      </div>
    </div>
  );
};

export default HistorySessionCard;
