"use client";

import React from "react";
import { useTriageHistory } from "@/hooks/queries/use-triage-history";
import {
  AlertTriangle,
  Loader2,
  MessageSquare,
  Plus,
  RefreshCw,
  UserCircle2,
} from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { triageStartHref } from "@/lib/agent-mode";
import {
  getHistorySessionHref,
  getTriageSessionStatusLabel,
} from "@/components/history/history-session-state";

export function TriageSidebar() {
  const { data: sessions, isLoading, isError, refetch } = useTriageHistory();
  const searchParams = useSearchParams();
  const currentSessionId = searchParams.get("session_id");

  return (
    <div className="h-full w-full bg-background/50 rounded-3xl border border-border flex flex-col overflow-hidden font-sans shadow-sm">
      <div className="p-4 border-b border-border/80 bg-card">
        <Link
          href={triageStartHref()}
          scroll={false}
          className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-sky-600 text-sm font-bold text-white shadow-sm transition-colors hover:bg-sky-500 active:bg-sky-700"
        >
          <Plus className="w-4 h-4" />
          Mở Phòng Khám Mới
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <div className="text-xs font-bold text-slate-400 uppercase tracking-wider px-2 py-1">
          Lịch sử của bạn
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
            Chưa có lịch sử khám bệnh.
          </div>
        ) : (
          sessions?.map((item) => {
            const isActive = currentSessionId === item.session_id;
            return (
              <Link
                key={item.session_id}
                href={getHistorySessionHref(item)}
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
                    <div className={cn("text-sm font-bold truncate", isActive ? "text-sky-900" : "text-slate-700 dark:text-slate-200")}>
                      {item.chief_complaint || "Phiên khám Triage"}
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-sm font-medium text-muted-foreground">
                      <UserCircle2 className="w-3 h-3" />
                      <span className="truncate max-w-[100px]">{item.profile_name || "Khám Nhanh"}</span>
                      <span>•</span>
                      <span className="font-semibold text-slate-700 dark:text-slate-200">
                        {getTriageSessionStatusLabel(item.status)}
                      </span>
                      <span>•</span>
                      <span className={cn("font-bold", item.final_esi != null && item.final_esi <= 2 ? "text-rose-600" : "text-muted-foreground")}>
                        {item.final_esi != null ? `ESI ${item.final_esi}` : "Chưa có ESI"}
                      </span>
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
