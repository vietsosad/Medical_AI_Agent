"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Clock,
  ChevronRight,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Zap,
  History,
  FolderOpen,
  MessageCircle,
  RefreshCw,
  CircleX,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTriageHistory } from "@/hooks/queries/use-triage-history";
import { groupSessionsByTime } from "@/lib/history-utils";
import type { TimeGroupKey, EsiLevel, HitlReviewStatus } from "@/types/clinical-history";
import {
  getHistorySessionHref,
  getTriageSessionStatusLabel,
} from "@/components/history/history-session-state";

export interface HistorySidebarProps {
  className?: string;
  onSelectSession?: (sessionId: string) => void;
  activeSessionId?: string;
}

const TIME_GROUP_LABELS: Record<TimeGroupKey, { label: string; icon: string }> = {
  TODAY: { label: "Hôm nay", icon: "today" },
  LAST_7_DAYS: { label: "7 ngày qua", icon: "week" },
  LAST_MONTH: { label: "Tháng trước", icon: "month" },
  OLDER: { label: "Cũ hơn", icon: "older" },
};

const getEsiDotColor = (esi: EsiLevel | null): { dot: string; bg: string; text: string } => {
  switch (esi) {
    case 1:
    case 2:
      return {
        dot: "bg-rose-600 animate-pulse",
        bg: "bg-rose-50 border-rose-200 text-rose-800",
        text: "text-rose-700 font-black",
      };
    case 3:
      return {
        dot: "bg-amber-500",
        bg: "bg-amber-50 border-amber-200 text-amber-800",
        text: "text-amber-800 font-bold",
      };
    case 4:
      return {
        dot: "bg-sky-500",
        bg: "bg-sky-50 border-sky-200 text-sky-800",
        text: "text-sky-700 font-bold",
      };
    case 5:
      return {
        dot: "bg-emerald-500",
        bg: "bg-emerald-50 border-emerald-200 text-emerald-800",
        text: "text-emerald-700 font-bold",
      };
    default:
      return {
        dot: "bg-slate-400",
        bg: "bg-muted border-border text-slate-700 dark:text-slate-200",
        text: "text-slate-600 font-medium dark:text-slate-300",
      };
  }
};

const getHitlMiniIndicator = (status: HitlReviewStatus) => {
  switch (status) {
    case "APPROVED":
      return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 inline shrink-0 stroke-[2.5]" aria-label="Bác sĩ đã duyệt" />;
    case "OVERRIDDEN":
      return <Zap className="w-3.5 h-3.5 text-amber-600 inline shrink-0 animate-pulse stroke-[2.5]" aria-label="Can thiệp Override" />;
    case "PENDING_REVIEW":
      return <Clock className="w-3.5 h-3.5 text-sky-600 inline shrink-0 stroke-[2.5]" aria-label="Đang chờ thẩm định" />;
    case "EMERGENCY_REJECTED":
      return <AlertTriangle className="w-3.5 h-3.5 text-rose-600 inline shrink-0 stroke-[2.5]" aria-label="Báo động đỏ" />;
    default:
      return null;
  }
};

const formatMiniTimestamp = (isoString: string): string => {
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return "N/A";
    const time = date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
    const day = date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
    return `${time} • ${day}`;
  } catch {
    return isoString;
  }
};

/**
 * ⭐ [SCR-HIST-01] Hợp phần Sidebar Lịch sử Tích hợp App Shell & Drawer (HistorySidebar) - G4
 * Giao diện Sáng Hiện Đại Chuẩn Lâm Sàng (Pristine Light Mode).
 */
export const HistorySidebar: React.FC<HistorySidebarProps> = ({
  className,
  onSelectSession,
  activeSessionId,
}) => {
  const pathname = usePathname();
  const { data: sessions, isLoading, isError, refetch } = useTriageHistory();

  const groupedSessions = React.useMemo(() => {
    return groupSessionsByTime(sessions || []);
  }, [sessions]);

  const groupKeys: TimeGroupKey[] = ["TODAY", "LAST_7_DAYS", "LAST_MONTH", "OLDER"];
  const totalCount = sessions?.length || 0;

  return (
    <aside
      className={cn(
        "w-full md:w-80 h-full max-h-[calc(100vh-64px)] flex flex-col bg-card border-r border-border/90 text-slate-800 select-none overflow-hidden shrink-0 shadow-xs font-sans dark:text-slate-100",
        className
      )}
    >
      {/* --- SIDEBAR HEADER --- */}
      <div className="p-4 border-b border-slate-100 bg-background flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-sky-100 border border-sky-200 text-sky-700 flex items-center justify-center">
            <History className="w-5 h-5 stroke-[2.5]" />
          </div>
          <div>
            <h2 className="text-base font-black text-foreground tracking-tight flex items-center gap-1.5">
              <span>Ký Ức Triage AI</span>
              <Sparkles className="w-3.5 h-3.5 text-sky-600 animate-pulse" />
            </h2>
            <p className="text-xs text-muted-foreground font-medium">
              Hồ sơ chẩn đoán &amp; thẩm định HITL
            </p>
          </div>
        </div>

        <div className="px-2.5 py-1 rounded-full bg-card border border-border text-xs font-extrabold text-sky-700 shadow-2xs">
          {isLoading ? "..." : totalCount}
        </div>
      </div>

      {/* --- SIDEBAR BODY --- */}
      <div className="flex-1 overflow-y-auto p-3 space-y-5 custom-scrollbar bg-card">
        {isLoading && (
          <div className="space-y-4 pt-2">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="p-3.5 rounded-2xl bg-background border border-border animate-pulse space-y-2.5 shadow-2xs"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-slate-300" />
                    <div className="h-3.5 w-20 bg-slate-200 rounded dark:bg-slate-700" />
                  </div>
                  <div className="h-3 w-16 bg-slate-200 rounded dark:bg-slate-700" />
                </div>
                <div className="h-4 w-11/12 bg-slate-200 rounded dark:bg-slate-700" />
                <div className="h-3.5 w-3/4 bg-muted rounded" />
              </div>
            ))}
          </div>
        )}

        {isError && (
          <div className="p-4 my-2 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex flex-col gap-2 shadow-2xs">
            <div className="flex items-center gap-2 font-bold text-sm">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 stroke-[2.5]" />
              <span>Lỗi đồng bộ dữ liệu ký ức!</span>
            </div>
            <p className="text-slate-700 font-normal dark:text-slate-200">
              Không thể trích xuất danh sách ca khám quá khứ từ máy chủ y khoa.
            </p>
            <button
              type="button"
              onClick={() => refetch()}
              className="mt-1 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-bold self-start text-xs transition-colors shadow-2xs cursor-pointer"
            >
              <RefreshCw className="size-4" aria-hidden="true" />
              Tải lại lịch sử
            </button>
          </div>
        )}

        {!isLoading && !isError && totalCount === 0 && (
          <div className="py-12 flex flex-col items-center justify-center text-center text-muted-foreground px-4">
            <div className="p-3 rounded-2xl bg-background border border-border text-slate-400 mb-3">
              <FolderOpen className="w-7 h-7 stroke-[2]" />
            </div>
            <p className="text-sm font-bold text-slate-800 dark:text-slate-100">Chưa có ca khám nào</p>
            <p className="text-xs text-muted-foreground mt-1">
              Các ca tư vấn Triage cùng AI và phiếu SBAR sẽ hiển thị theo trình tự thời gian tại đây.
            </p>
          </div>
        )}

        {!isLoading && !isError && totalCount > 0 && (
          <div className="space-y-6 pb-6">
            {groupKeys.map((groupKey) => {
              const items = groupedSessions[groupKey];
              if (!items || items.length === 0) return null;

              return (
                <div key={groupKey} className="space-y-2.5">
                  <div className="flex items-center gap-2 px-1">
                    <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      {TIME_GROUP_LABELS[groupKey].label}
                    </span>
                    <div className="flex-1 h-px bg-muted" />
                    <span className="text-[10px] font-bold text-muted-foreground bg-muted px-2 py-0.5 rounded-full border border-border">
                      {items.length}
                    </span>
                  </div>

                  <div className="space-y-2">
                    {items.map((session) => {
                      const esiStyles = getEsiDotColor(session.final_esi);
                      const isCurrentlyActive =
                        activeSessionId === session.session_id ||
                        pathname?.includes(`/history/${session.session_id}`);

                      return (
                        <Link
                          key={session.session_id}
                          href={getHistorySessionHref(session)}
                          onClick={() => onSelectSession?.(session.session_id)}
                          className={cn(
                            "group relative block p-3.5 rounded-2xl transition-all duration-200 text-left cursor-pointer border",
                            isCurrentlyActive
                              ? "bg-sky-50 border-sky-300 shadow-xs text-sky-950"
                              : "bg-background hover:bg-card border-border/90 text-slate-800 hover:border-slate-300 shadow-2xs hover:shadow-xs dark:text-slate-100 dark:hover:border-slate-700"
                          )}
                        >
                          <div
                            className={cn(
                              "absolute top-3 bottom-3 left-0.5 w-1 rounded-full transition-all",
                              session.final_esi != null && session.final_esi <= 2 ? "bg-rose-600" :
                              session.final_esi === 3 ? "bg-amber-500" :
                              session.final_esi === 4 ? "bg-sky-600" :
                              session.final_esi === 5 ? "bg-emerald-600" : "bg-slate-400",
                              isCurrentlyActive ? "w-1.5" : "w-1"
                            )}
                          />

                          <div className="pl-3 space-y-2">
                            <div className="flex items-center justify-between text-xs gap-2">
                              <div className="flex items-center gap-1.5">
                                <span className={cn("w-2 h-2 rounded-full shrink-0 inline-block", esiStyles.dot)} />
                                <span className={cn("text-[11px] font-bold tracking-tight uppercase", esiStyles.text)}>
                                  {session.final_esi != null
                                    ? `ESI ${session.final_esi}`
                                    : getTriageSessionStatusLabel(session.status)}
                                </span>
                                <span className="text-slate-300 font-bold">•</span>
                                {session.status === "IN_PROGRESS" ? (
                                  <MessageCircle
                                    className="size-4 shrink-0 text-sky-700"
                                    aria-label="Ca khám đang thu thập thông tin"
                                  />
                                ) : session.status === "CANCELLED" ? (
                                  <CircleX
                                    className="size-4 shrink-0 text-slate-600 dark:text-slate-300"
                                    aria-label="Ca khám đã hủy"
                                  />
                                ) : (
                                  getHitlMiniIndicator(session.hitl_status)
                                )}
                              </div>

                              <span className="text-xs font-medium text-muted-foreground shrink-0 flex items-center gap-1">
                                <Clock className="w-3 h-3 text-slate-400 inline" />
                                {formatMiniTimestamp(session.created_at)}
                              </span>
                            </div>

                            <p className="text-sm font-bold text-foreground group-hover:text-sky-700 line-clamp-2 leading-snug transition-colors">
                              {session.chief_complaint || "Ca khám đang thu thập thông tin"}
                            </p>

                            <p className="text-xs text-slate-600 font-normal line-clamp-1 italic dark:text-slate-300">
                              {session.sbar_finalized
                                ? session.sbar_snippet
                                : session.sbar_snippet || getTriageSessionStatusLabel(session.status)}
                            </p>
                          </div>
                        </Link>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* --- SIDEBAR FOOTER --- */}
      <div className="p-3 border-t border-slate-100 bg-background text-center shrink-0">
        <Link
          href="/history"
          className="w-full py-2 px-3 rounded-xl bg-card hover:bg-muted text-slate-800 border border-border text-xs font-bold transition-all duration-200 flex items-center justify-center gap-1.5 shadow-2xs active:scale-95 dark:text-slate-100"
        >
          <span>Mở Trạm Quản Trị Trung Tâm</span>
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
        </Link>
      </div>
    </aside>
  );
};

export default HistorySidebar;
