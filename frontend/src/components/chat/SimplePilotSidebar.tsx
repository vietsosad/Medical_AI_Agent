"use client";

import React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  MessageCircleQuestion,
  MessageSquare,
  Plus,
  RefreshCw,
  Stethoscope,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSimplePatientRealtime, useSimpleTriageSessions } from "@/queries/useSimpleTriageQueries";
import type { SimpleTriageSessionSummaryDTO } from "@/types/simple-triage";

/**
 * Left history sidebar for `/triage-pilot/*`, structurally forked from
 * production's `TriageSidebar.tsx` (same shell/behavior) but reading
 * `useSimpleTriageSessions()` instead of `useTriageHistory()` -- the pilot's
 * `SimpleTriageSessionSummaryDTO` has a fully different shape
 * (`status`/`final_action`/`matched_esi_levels`, no `chief_complaint`/
 * production `hitl_status`), so `TriageSidebar` itself can't be reused
 * as-is. The status-label logic below intentionally mirrors
 * `/triage-pilot/history/page.tsx`'s own `StatusBadge` rather than
 * refactoring that already-working page to share it.
 */

function statusLabel(session: SimpleTriageSessionSummaryDTO): { text: string; className: string } {
  if (session.status === "ACTIVE") {
    return { text: "Đang hỏi bệnh", className: "text-sky-700" };
  }
  if (session.final_action === "RETURN_MATCH" && session.matched_esi_levels.length > 0) {
    // Chỉ hiện mức nghiêm trọng nhất (số nhỏ nhất) đã khớp, không liệt kê hết
    // (vd 2 và 3 cùng khớp -> chỉ hiện "ESI 2") -- đồng bộ với cách các nơi
    // khác (chat, PDF, màn hình điều dưỡng) đã hiển thị (2026-08-29).
    const topLevel = Math.min(...session.matched_esi_levels);
    const isReviewed =
      session.review_display_status === "APPROVED" || session.review_display_status === "OVERRIDDEN";
    if (isReviewed && session.final_esi != null) {
      if (session.review_display_status === "OVERRIDDEN") {
        return {
          text: `ESI ${topLevel} → ESI ${session.final_esi}`,
          className: session.final_esi <= 2 ? "text-rose-600" : "text-amber-700",
        };
      }
      return {
        text: `Điều dưỡng xác nhận ESI ${session.final_esi}`,
        className: session.final_esi <= 2 ? "text-rose-600" : "text-emerald-700",
      };
    }
    return {
      text: `AI đề xuất ESI ${topLevel}`,
      className: topLevel <= 2 ? "text-rose-600" : "text-emerald-700",
    };
  }
  return { text: "Chưa đủ dữ liệu", className: "text-amber-700" };
}

function statusIcon(session: SimpleTriageSessionSummaryDTO) {
  if (session.status === "ACTIVE") return MessageCircleQuestion;
  if (session.final_action === "RETURN_MATCH") return CheckCircle2;
  return AlertTriangle;
}

export function SimplePilotSidebar() {
  const { data: sessions, isLoading, isError, refetch } = useSimpleTriageSessions();
  // "Tin mới" badge dưới đây cập nhật gần như ngay lập tức thay vì chờ vòng
  // poll tiếp theo, dù y tá vừa trả lời trên phiên nào của bệnh nhân này.
  useSimplePatientRealtime();
  const searchParams = useSearchParams();
  const currentSessionId = searchParams.get("session_id");

  return (
    <div className="h-full w-full bg-background/50 rounded-3xl border border-border flex flex-col overflow-hidden font-sans shadow-sm">
      <div className="p-4 border-b border-border/80 bg-card">
        <Link
          href="/triage-pilot"
          scroll={false}
          className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-sky-600 text-sm font-bold text-white shadow-sm transition-colors hover:bg-sky-500 active:bg-sky-700"
        >
          <Plus className="w-4 h-4" />
          Phiên sàng lọc mới
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <div className="text-xs font-bold text-slate-400 uppercase tracking-wider px-2 py-1">
          Lịch sử của bạn (pilot)
        </div>

        {isLoading ? (
          <div role="status" aria-live="polite" className="flex justify-center py-8 text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="sr-only">Đang tải danh sách ca khám</span>
          </div>
        ) : isError ? (
          <div
            role="alert"
            className="space-y-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-950"
          >
            <div className="flex items-start gap-2 font-semibold">
              <AlertTriangle className="size-5 shrink-0 text-rose-700" aria-hidden="true" />
              <span>Không thể đồng bộ danh sách ca khám.</span>
            </div>
            <button
              type="button"
              onClick={() => void refetch()}
              className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-rose-300 bg-card px-4 font-semibold text-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600"
            >
              <RefreshCw className="size-5" aria-hidden="true" />
              Tải lại
            </button>
          </div>
        ) : sessions?.length === 0 ? (
          <div className="text-sm text-muted-foreground text-center py-6 px-4">
            Chưa có lịch sử khám pilot.
          </div>
        ) : (
          sessions?.map((item) => {
            const isActive = currentSessionId === item.session_id;
            const status = statusLabel(item);
            const StatusIcon = statusIcon(item);
            return (
              <Link
                key={item.session_id}
                href={`/triage-pilot?session_id=${item.session_id}`}
                scroll={false}
                className={cn(
                  "block rounded-xl border p-3 text-left transition-colors",
                  isActive
                    ? "bg-sky-50 border-sky-200 shadow-sm"
                    : "bg-card border-transparent hover:border-border hover:bg-muted/50"
                )}
              >
                <div className="flex items-start gap-2">
                  <MessageSquare className={cn("w-4 h-4 mt-0.5 shrink-0", isActive ? "text-sky-600" : "text-slate-400")} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <div className={cn("min-w-0 flex-1 truncate text-sm font-bold", isActive ? "text-sky-900" : "text-slate-700 dark:text-slate-200")}>
                        {item.initial_message.trim() || "Phiên sàng lọc"}
                      </div>
                      {item.unread_from_staff > 0 && (
                        <span
                          title="Nhân viên y tế vừa nhắn thêm"
                          className="flex shrink-0 items-center gap-1 rounded-full bg-teal-600 px-2 py-0.5 text-xs font-bold text-white"
                        >
                          <Stethoscope className="size-3" aria-hidden="true" />
                          {item.unread_from_staff}
                        </span>
                      )}
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-sm font-medium text-muted-foreground">
                      <StatusIcon className="w-3 h-3" aria-hidden="true" />
                      <span className={cn("font-semibold", status.className)}>{status.text}</span>
                      <span>•</span>
                      <span>{item.turn_count} lượt</span>
                    </div>
                  </div>
                </div>
              </Link>
            );
          })
        )}
      </div>
    </div>
  );
}
