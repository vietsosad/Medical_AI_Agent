"use client";

import React, { useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  History,
  Loader2,
  RefreshCw,
  AlertTriangle,
  FolderX,
  Database,
  SearchX,
  Layers,
  Activity,
  UserCheck,
  PlusCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { IS_PILOT_AGENT_ACTIVE, triageHistoryListHref, triageStartHref } from "@/lib/agent-mode";
import { useTriageHistory } from "@/hooks/queries/use-triage-history";
import { useHistoryUIStore } from "@/store/useHistoryUIStore";
import { HistoryFilterControl } from "@/components/history/HistoryFilterControl";
import { HistorySessionCard } from "@/components/history/HistorySessionCard";
import { toast } from "sonner";

/**
 * TRANG CHỦ QUẢN TRỊ KÝ ỨC LÂM SÀNG (/history)
 * Giao diện Sáng Hiện Đại Chuẩn Lâm Sàng (Pristine Light Mode - Trang trọng, tinh khôi)
 */
export default function ClinicalHistoryPage() {
  const router = useRouter();
  const { data: sessions, isLoading, isError, error, refetch, isRefetching } = useTriageHistory();
  const { searchQuery, selectedEsiFilters, statusFilter, resetFilters } = useHistoryUIStore();

  // "Lưới an toàn": trang này luôn là danh sách chung, không mang theo 1 case
  // id cụ thể -- an toàn để chuyển hẳn sang lịch sử pilot khi cờ đang bật,
  // dù ai đó vẫn vào thẳng URL cũ. Xem @/lib/agent-mode.
  useEffect(() => {
    if (IS_PILOT_AGENT_ACTIVE) {
      router.replace(triageHistoryListHref());
    }
  }, [router]);

  const filteredSessions = useMemo(() => {
    if (!sessions) return [];
    return sessions.filter((session) => {
      if (searchQuery.trim() !== "") {
        const query = searchQuery.toLowerCase().trim();
        const matchComplaint = session.chief_complaint.toLowerCase().includes(query);
        const matchSnippet = session.sbar_snippet.toLowerCase().includes(query);
        const matchId = session.session_id.toLowerCase().includes(query);
        if (!matchComplaint && !matchSnippet && !matchId) {
          return false;
        }
      }

      if (selectedEsiFilters.length > 0 && (session.final_esi == null || !selectedEsiFilters.includes(session.final_esi))) {
        return false;
      }

      if (statusFilter !== "ALL" && session.hitl_status !== statusFilter) {
        return false;
      }

      return true;
    });
  }, [sessions, searchQuery, selectedEsiFilters, statusFilter]);

  const stats = useMemo(() => {
    const list = sessions || [];
    const overrideCount = list.filter((s) => s.hitl_status === "OVERRIDDEN").length;
    const emergencyCount = list.filter((s) => s.final_esi != null && s.final_esi <= 2).length;
    const approvedCount = list.filter((s) => s.hitl_status === "APPROVED").length;
    return {
      total: list.length,
      overridden: overrideCount,
      emergent: emergencyCount,
      approved: approvedCount,
    };
  }, [sessions]);

  const isFilterActive =
    searchQuery.trim() !== "" || selectedEsiFilters.length > 0 || statusFilter !== "ALL";

  if (IS_PILOT_AGENT_ACTIVE) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center bg-background p-6">
        <div className="flex items-center gap-3 rounded-xl border border-border bg-card px-5 py-4 text-sm font-medium text-slate-700 dark:text-slate-200">
          <Loader2 className="size-5 animate-spin text-sky-700" aria-hidden="true" />
          Đang chuyển sang lịch sử khám...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-slate-800 pb-20 selection:bg-sky-100 selection:text-sky-900 font-sans">
      <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 md:pt-10 space-y-8">
        {/* ====================================================================
            HERO COMMAND HEADER & WORKFLOW BRIDGE
            ==================================================================== */}
        <div className="space-y-6">
          <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-6 border-b border-border/90">
            <div className="space-y-2.5">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-muted border border-border text-slate-700 text-[11px] font-bold uppercase tracking-wider shadow-sm dark:text-slate-200">
                <History className="w-3.5 h-3.5" />
                <span>Lưu Trữ Ký Ức &amp; Phiếu SBAR</span>
              </div>
              <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground flex items-center gap-3">
                <span>Lịch Sử Khám Triage AI</span>
              </h1>
              <p className="text-sm text-muted-foreground max-w-3xl font-medium leading-relaxed">
                Quản lý tập trung toàn bộ hồ sơ khám bệnh, bằng chứng thẩm định chuyên khoa và kiểm chứng trích lục phác đồ RAG chuẩn y khoa.
              </p>
            </div>

            {/* Cần gạt hành động luồng liên hoàn (Workflow CTAs) */}
            <div className="flex flex-wrap items-center gap-2.5 shrink-0">
              <Link
                href={triageStartHref()}
                className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs transition-all shadow-sm flex items-center gap-1.5 active:scale-95"
              >
                <PlusCircle className="w-4 h-4" />
                <span>Khám Triage Mới</span>
              </Link>

              <button
                type="button"
                onClick={() => {
                  refetch();
                  toast.success("Đang đồng bộ dữ liệu mới nhất từ Trụ Cột Lâm Sàng...");
                }}
                disabled={isRefetching}
                className="px-4 py-2.5 rounded-xl bg-card hover:bg-muted text-slate-700 border border-border/90 text-xs font-bold transition-all flex items-center gap-2 shadow-2xs disabled:opacity-50 cursor-pointer dark:text-slate-200"
                title="Đồng bộ dữ liệu mới"
              >
                <RefreshCw className={cn("w-4 h-4 text-slate-600 dark:text-slate-300", isRefetching && "animate-spin")} />
                <span>{isRefetching ? "Đang xử lý..." : "Đồng bộ"}</span>
              </button>
            </div>
          </div>

          {/* Dải Chỉ Số Lâm Sàng Nhanh (Clinical KPIs - Clean White Cards) */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-2xl bg-card border border-border/60 shadow-sm flex items-center gap-3.5 hover:border-slate-300 transition-colors dark:hover:border-slate-700">
              <div className="p-3 rounded-xl bg-background border border-slate-100 text-slate-600 shrink-0 dark:text-slate-300">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[11px] text-muted-foreground font-bold uppercase tracking-wider">Tổng hồ sơ</p>
                <p className="text-xl font-bold text-foreground">{stats.total}</p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-card border border-border/60 shadow-sm flex items-center gap-3.5 hover:border-rose-300 transition-colors">
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-100 text-rose-600 shrink-0">
                <Activity className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[11px] text-muted-foreground font-bold uppercase tracking-wider">Khẩn cấp (ESI 1-2)</p>
                <p className="text-xl font-bold text-rose-700">{stats.emergent}</p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-card border border-border/60 shadow-sm flex items-center gap-3.5 hover:border-amber-300 transition-colors">
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-100 text-amber-600 shrink-0">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[11px] text-muted-foreground font-bold uppercase tracking-wider">Có can thiệp (Override)</p>
                <p className="text-xl font-bold text-amber-700">{stats.overridden}</p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-card border border-border/60 shadow-sm flex items-center gap-3.5 hover:border-emerald-300 transition-colors">
              <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-600 shrink-0">
                <UserCheck className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[11px] text-muted-foreground font-bold uppercase tracking-wider">Đã thẩm định hợp lệ</p>
                <p className="text-xl font-bold text-emerald-700">{stats.approved}</p>
              </div>
            </div>
          </div>
        </div>

        {/* ====================================================================
            HỆ THỐNG THANH CONTROL TRA CỨU & BỘ LỌC NHANH
            ==================================================================== */}
        <section>
          <HistoryFilterControl totalResults={filteredSessions.length} />
        </section>

        {/* ====================================================================
            4-STATE HYGIENE (WORKSPACE FEED RENDERING)
            ==================================================================== */}
        <section className="pt-2">
          {/* STATE 1: LOADING SKELETON */}
          {isLoading && (
            <div className="space-y-5">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="p-6 rounded-3xl bg-card border border-border/90 shadow-sm animate-pulse space-y-4"
                >
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="h-4 w-48 bg-slate-200 rounded-md dark:bg-slate-700" />
                    <div className="flex gap-2">
                      <div className="h-6 w-28 bg-slate-200 rounded-full dark:bg-slate-700" />
                      <div className="h-6 w-32 bg-sky-100 rounded-full" />
                    </div>
                  </div>
                  <div className="h-6 w-3/4 bg-slate-200 rounded-md dark:bg-slate-700" />
                  <div className="pl-4 border-l-2 border-border py-1 space-y-2">
                    <div className="h-3 w-32 bg-slate-200 rounded dark:bg-slate-700" />
                    <div className="h-4 w-full bg-muted rounded" />
                    <div className="h-4 w-5/6 bg-muted rounded" />
                  </div>
                  <div className="pt-3 border-t border-slate-100 flex justify-between">
                    <div className="h-3 w-40 bg-slate-200 rounded dark:bg-slate-700" />
                    <div className="h-4 w-44 bg-sky-100 rounded" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* STATE 2: ERROR STATE */}
          {isError && (
            <div className="p-8 rounded-3xl bg-card border-2 border-rose-400 text-slate-800 text-center space-y-4 shadow-md max-w-2xl mx-auto my-12 dark:text-slate-100">
              <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-600 w-16 h-16 mx-auto flex items-center justify-center shadow-2xs">
                <AlertTriangle className="w-8 h-8 animate-bounce stroke-[2.5]" />
              </div>
              <h2 className="text-xl font-extrabold text-foreground tracking-tight">
                Không thể kết nối đến Trụ cột Dữ liệu Ký ức Lâm sàng
              </h2>
              <p className="text-sm text-slate-600 leading-relaxed max-w-lg mx-auto dark:text-slate-300">
                {error?.message ||
                  "Hệ thống gặp trở ngại khi truy xuất kho báu SBAR quá khứ từ máy chủ chuyên gia. Vui lòng kiểm tra kết nối đường truyền mạng."}
              </p>
              <button
                type="button"
                onClick={() => refetch()}
                className="px-6 py-3 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-extrabold text-sm shadow-sm hover:scale-105 transition-all duration-200 inline-flex items-center gap-2 cursor-pointer"
              >
                <RefreshCw className="w-4 h-4 stroke-[2.5]" />
                <span>Tải lại Trạm Ký Ức</span>
              </button>
            </div>
          )}

          {/* STATE 3: EMPTY FILTER STATE */}
          {!isLoading && !isError && filteredSessions.length === 0 && (
            <div className="py-16 px-6 rounded-3xl bg-card border border-border text-center max-w-2xl mx-auto my-6 space-y-4 shadow-sm">
              <div className="p-4 rounded-2xl bg-background border border-border text-slate-400 w-16 h-16 mx-auto flex items-center justify-center shadow-2xs">
                {isFilterActive ? <SearchX className="w-8 h-8 text-amber-600 stroke-[2]" /> : <FolderX className="w-8 h-8 text-sky-600 stroke-[2]" />}
              </div>
              <h3 className="text-lg md:text-xl font-bold text-foreground">
                {isFilterActive
                  ? "Không tìm thấy ca khám nào khớp với bộ lọc lâm sàng của bạn"
                  : "Chưa có bất kỳ hồ sơ khám bệnh quá khứ nào"}
              </h3>
              <p className="text-sm text-slate-600 max-w-md mx-auto leading-relaxed dark:text-slate-300">
                {isFilterActive
                  ? "Vui lòng kiểm tra lại từ khóa tìm kiếm hoặc nhấp vào nút dưới đây để khôi phục bộ lọc và hiển thị toàn bộ hồ sơ SBAR."
                  : "Hệ thống sẽ tự động lưu trữ và khởi tạo khối văn bản SBAR sau mỗi lần bạn thực hiện phiên hỏi bệnh và thẩm định từ AI."}
              </p>

              {isFilterActive && (
                <button
                  type="button"
                  onClick={resetFilters}
                  className="px-6 py-2.5 rounded-xl bg-muted hover:bg-slate-200 text-slate-800 border border-border text-sm font-bold transition-all inline-flex items-center gap-2 shadow-2xs cursor-pointer dark:text-slate-100 dark:hover:bg-slate-700"
                >
                  <RefreshCw className="w-4 h-4 text-sky-600" />
                  <span>Khôi phục bộ lọc mặc định</span>
                </button>
              )}
            </div>
          )}

          {/* STATE 4: SUCCESS DATA STATE */}
          {!isLoading && !isError && filteredSessions.length > 0 && (
            <div className="space-y-6">
              {filteredSessions.map((session, index) => (
                <motion.div
                  key={session.session_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{
                    delay: index * 0.05,
                    duration: 0.35,
                    ease: "easeOut",
                  }}
                >
                  <HistorySessionCard session={session} />
                </motion.div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
