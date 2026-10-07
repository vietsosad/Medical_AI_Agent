"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Calendar,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Stethoscope,
  Sparkles,
  ShieldCheck,
  Layers,
  RefreshCw,
  MessageCircle,
  FileClock,
  CircleX,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTriageSessionDetail } from "@/hooks/queries/use-triage-history";
import { getEsiBadgeConfig } from "@/lib/history-utils";
import { ConversationReplayFeed } from "@/components/history/ConversationReplayFeed";
import { HitlSignatureBadge } from "@/components/history/HitlSignatureBadge";
import { SbarViewerCard } from "@/components/history/SbarViewerCard";
import { SbarExportActions } from "@/components/history/SbarExportActions";
import type {
  HitlReviewStatus,
  TriageSessionStatus,
} from "@/types/clinical-history";
import {
  hasFinalizedSbar,
  isActiveTriageSession,
  isResumableTriageSession,
} from "@/components/history/history-session-state";

export interface HistoryDetailTerminalProps {
  sessionId: string;
}

const renderDetailStatusBadge = (
  status: HitlReviewStatus,
  sessionStatus: TriageSessionStatus,
  reviewerName?: string,
) => {
  if (sessionStatus === "CANCELLED") {
    return (
      <span className="flex min-h-12 items-center gap-2 rounded-xl border border-slate-300 bg-muted px-4 text-sm font-bold text-slate-800 dark:text-slate-100 dark:border-slate-700">
        <CircleX className="size-5 text-slate-600 dark:text-slate-300" aria-hidden="true" />
        Ca khám đã hủy
      </span>
    );
  }

  if (sessionStatus === "IN_PROGRESS") {
    return (
      <span className="flex min-h-12 items-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 text-sm font-bold text-sky-900">
        <MessageCircle className="size-5 text-sky-700" aria-hidden="true" />
        Đang thu thập thông tin
      </span>
    );
  }

  switch (status) {
    case "APPROVED":
      return (
        <span className="px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs font-extrabold flex items-center gap-2 shadow-2xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 stroke-[2.5]" />
          <span>
            Đã được nhân viên y tế thẩm định
            {reviewerName ? ` (${reviewerName})` : ""}
          </span>
        </span>
      );
    case "OVERRIDDEN":
      return (
        <span className="px-3.5 py-1.5 rounded-full bg-amber-50 border border-amber-300 text-amber-900 text-xs font-extrabold flex items-center gap-2 shadow-2xs animate-pulse">
          <Zap className="w-4 h-4 text-amber-600 stroke-[2.5]" />
          <span>
            Đã được nhân viên y tế điều chỉnh
            {reviewerName ? ` (${reviewerName})` : ""}
          </span>
        </span>
      );
    case "PENDING_REVIEW":
      return (
        <span className="px-3.5 py-1.5 rounded-full bg-sky-50 border border-sky-200 text-sky-900 text-xs font-bold flex items-center gap-2">
          <span>Đang chờ nhân viên y tế thẩm định</span>
        </span>
      );
    case "EMERGENCY_REJECTED":
      return (
        <span className="px-3.5 py-1.5 rounded-full bg-rose-50 border-2 border-rose-400 text-rose-900 text-xs font-extrabold flex items-center gap-2 shadow-2xs">
          <AlertTriangle className="w-4 h-4 text-rose-600 animate-bounce stroke-[2.5]" />
          <span>Đã chuyển sang luồng xử trí khẩn cấp</span>
        </span>
      );
    default:
      return null;
  }
};

/**
 * Khung chi tiết lịch sử khám và phiếu SBAR của người bệnh.
 */
export const HistoryDetailTerminal: React.FC<HistoryDetailTerminalProps> = ({ sessionId }) => {
  const { data: session, isLoading, isError, error, refetch } = useTriageSessionDetail(sessionId);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 animate-pulse bg-background min-h-screen">
        <div className="h-10 w-48 bg-slate-200 rounded-xl dark:bg-slate-700" />
        <div className="p-6 rounded-3xl bg-card border border-border space-y-4 shadow-sm">
          <div className="h-8 w-2/3 bg-slate-200 rounded-md dark:bg-slate-700" />
          <div className="flex gap-3">
            <div className="h-7 w-36 bg-muted rounded-full" />
            <div className="h-7 w-40 bg-sky-100 rounded-full" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-4">
          <div className="lg:col-span-7 h-[600px] bg-card rounded-2xl border border-border" />
          <div className="lg:col-span-5 h-[600px] bg-card rounded-2xl border border-border" />
        </div>
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className="min-h-screen bg-background max-w-2xl mx-auto px-4 py-16 text-center font-sans">
        <div className="p-8 rounded-3xl bg-card border-2 border-rose-400 text-slate-800 space-y-5 shadow-md dark:text-slate-100">
          <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-600 w-16 h-16 mx-auto flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 animate-bounce stroke-[2.5]" />
          </div>
          <h2 className="text-2xl font-black text-foreground">
            Không tìm thấy hồ sơ chi tiết cho Ca Khám #{sessionId.slice(-8)}
          </h2>
          <p className="text-sm text-slate-600 max-w-md mx-auto leading-relaxed font-medium dark:text-slate-300">
            {error?.message || "Dữ liệu ca khám có thể đã được phân tán hoặc bạn không đủ đặc quyền truy cập hồ sơ lưu trữ."}
          </p>
          <div className="flex justify-center gap-3 pt-2">
            <Link
              href="/history"
              className="px-6 py-2.5 rounded-xl bg-muted hover:bg-slate-200 text-slate-800 font-bold text-xs sm:text-sm border border-border transition-colors dark:text-slate-100 dark:hover:bg-slate-700"
            >
              ← Quay Lại Danh Sách Lịch Sử
            </Link>
            <button
              type="button"
              onClick={() => refetch()}
              className="px-6 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs sm:text-sm shadow-sm transition-transform hover:scale-105 inline-flex items-center gap-2 cursor-pointer"
            >
              <RefreshCw className="w-4 h-4 stroke-[2.5]" />
              <span>Thử lại ngay</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  const esiConfig = getEsiBadgeConfig(session.final_esi);
  const hitlSig = session.hitl_signature;
  const hasSbar = hasFinalizedSbar(session);
  const isActiveSession = isActiveTriageSession(session.status);
  const canResume = isResumableTriageSession(session.status);

  return (
    <div className="min-h-screen bg-background text-slate-800 pb-24 selection:bg-sky-100 selection:text-sky-900 font-sans">
      <div className="relative z-10 max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 md:pt-8 space-y-6">
        {/* ====================================================================
            NAVIGATION BAR & OVERHEAD COMMAND TITLE
            ==================================================================== */}
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Link
              href="/history"
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-card hover:bg-muted text-slate-700 hover:text-foreground border border-border/90 font-bold text-xs sm:text-sm transition-all duration-200 shadow-2xs active:scale-95 dark:text-slate-200"
            >
              <ArrowLeft className="w-4 h-4 text-sky-600 stroke-[2.5]" />
              <span>Quay lại lịch sử khám</span>
            </Link>
            {isActiveSession && (
              <Link
                href={`/triage?session_id=${session.session_id}`}
                className="inline-flex min-h-12 items-center gap-2 rounded-xl bg-sky-700 px-4 text-sm font-bold text-white transition-colors hover:bg-sky-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
              >
                <MessageCircle className="size-5" aria-hidden="true" />
                {canResume ? "Tiếp tục ca khám" : "Theo dõi ca đang thẩm định"}
              </Link>
            )}
          </div>

          {/* Banner Hồ Sơ Ca Khám */}
          <div className="p-6 sm:p-8 rounded-3xl bg-card border border-border/90 shadow-sm space-y-5">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-5 border-b border-slate-100">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-mono font-black text-sky-700 uppercase tracking-widest">
                  <Stethoscope className="w-4 h-4 text-sky-600 stroke-[2.5]" />
                  <span>Mã ca Triage: #{session.session_id}</span>
                </div>
                <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-foreground leading-snug">
                  {session.chief_complaint || "Ca khám đang thu thập thông tin"}
                </h1>
                <p className="text-xs sm:text-sm text-muted-foreground font-medium flex items-center gap-2 pt-0.5">
                  <Calendar className="w-4 h-4 text-sky-600 inline shrink-0 stroke-[2.5]" />
                  <span>
                    Thời điểm ghi nhận lâm sàng:{" "}
                    <strong className="text-slate-800 font-bold dark:text-slate-100">
                      {new Date(session.created_at).toLocaleString("vi-VN", {
                        dateStyle: "full",
                        timeStyle: "medium",
                      })}
                    </strong>
                  </span>
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3 shrink-0">
                {renderDetailStatusBadge(
                  session.hitl_status,
                  session.status,
                  hitlSig?.reviewer_name ?? undefined,
                )}

                <span
                  className={cn(
                    "px-4 py-2 rounded-full text-sm font-black border tracking-tight flex items-center gap-2 shadow-2xs",
                    esiConfig.colorClass,
                    esiConfig.glowingBorder
                  )}
                >
                  <Sparkles className="w-4 h-4 animate-pulse shrink-0" />
                  <span>{esiConfig.label}</span>
                </span>
              </div>
            </div>

            {hitlSig?.justification_note && (
              <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-950 text-xs sm:text-sm leading-relaxed shadow-2xs flex items-start gap-3">
                <ShieldCheck className="w-6 h-6 text-amber-600 shrink-0 mt-0.5 stroke-[2.5]" />
                <div className="space-y-1">
                  <p className="font-extrabold text-amber-900 uppercase tracking-wider text-xs">
                      Ghi chú thẩm định từ {hitlSig.reviewer_name}:
                  </p>
                  <p className="text-slate-800 font-semibold italic dark:text-slate-100">&quot;{hitlSig.justification_note}&quot;</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ====================================================================
            DUAL TERMINAL WORKSPACE
            ==================================================================== */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-2 items-start">
          {/* CỘT TRÁI (58%): CONVERSATION REPLAY FEED */}
          <section className="lg:col-span-7 h-[calc(100vh-140px)] min-h-[680px] flex flex-col bg-card border border-border/90 rounded-3xl p-4 sm:p-6 shadow-sm overflow-hidden">
            <div className="pb-3 border-b border-slate-100 mb-2 flex items-center justify-between">
              <h2 className="text-base sm:text-lg font-black text-foreground flex items-center gap-2 tracking-tight">
                <Layers className="w-5 h-5 text-sky-600 stroke-[2.5]" />
                <span>Diễn biến hội thoại</span>
              </h2>
              <span className="text-xs font-mono font-extrabold text-sky-900 bg-sky-100 px-3 py-1 rounded-full border border-sky-200">
                {session.messages.length} tin nhắn
              </span>
            </div>

            <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar">
              <ConversationReplayFeed messages={session.messages} chiefComplaint={session.chief_complaint} />
            </div>
          </section>

          {/* CỘT PHẢI (42%): STICKY HITL & SBAR WORKSPACE */}
          <aside className="lg:col-span-5 lg:sticky lg:top-6 space-y-6">
            <div className="space-y-4">
              {(session.hitl_signature || session.status === "HITL_REVIEWING") && (
                <HitlSignatureBadge signature={session.hitl_signature} />
              )}
              {hasSbar ? (
                <>
                  <SbarViewerCard
                    sbar={session.sbar_report}
                    sbarFinalized={session.sbar_finalized}
                  />
                  <SbarExportActions session={session} />
                </>
              ) : (
                <section
                  role="status"
                  className="space-y-4 rounded-2xl border border-slate-300 bg-background p-6 text-slate-800 dark:text-slate-100 dark:border-slate-700"
                >
                  <div className="flex items-start gap-4">
                    <FileClock className="size-6 shrink-0 text-slate-600 dark:text-slate-300" aria-hidden="true" />
                    <div className="space-y-2">
                      <h2 className="text-base font-bold text-slate-950 dark:text-slate-50">
                        Chưa có SBAR đã hoàn tất
                      </h2>
                      <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">
                        {canResume
                          ? "Ca khám vẫn đang thu thập thông tin. SBAR và hành động tải sẽ chỉ xuất hiện sau khi backend xác nhận kết quả đã hoàn tất."
                          : "Backend chưa xác nhận một SBAR hoàn tất cho ca này, nên nội dung và hành động tải được ẩn để tránh dùng nhầm dữ liệu tạm thời."}
                      </p>
                    </div>
                  </div>
                  {isActiveSession && (
                    <Link
                      href={`/triage?session_id=${session.session_id}`}
                      className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-sky-700 px-4 text-sm font-bold text-white hover:bg-sky-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
                    >
                      <MessageCircle className="size-5" aria-hidden="true" />
                      {canResume ? "Tiếp tục cung cấp thông tin" : "Theo dõi trạng thái ca khám"}
                    </Link>
                  )}
                </section>
              )}
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
};

export default HistoryDetailTerminal;
