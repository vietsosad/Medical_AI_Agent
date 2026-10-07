"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Database,
  FlaskConical,
  Layers,
  Loader2,
  MessageCircleQuestion,
  Plus,
  Search,
  ShieldAlert,
  Stethoscope,
  X,
} from "lucide-react";

import { useGetProfiles } from "@/queries/useProfileQueries";
import { useSimpleTriageSessions } from "@/queries/useSimpleTriageQueries";
import { SimplePilotReviewBadge } from "@/components/chat/SimplePilotReviewBadge";
import {
  pilotAiProposedEsi,
  SimplePilotEsiBadge,
} from "@/components/chat/SimplePilotNurseDecisionSummary";
import type { SimpleTriageSessionSummaryDTO } from "@/types/simple-triage";
import { cn } from "@/lib/utils";

/**
 * Pilot's own "Lịch sử khám" list, redesigned to match production's
 * `/history` in spirit (stat cards, review-status/profile/search/ESI
 * filters + reset, clear pagination) -- see
 * `.claude/plans/sunny-launching-mitten.md` for the full investigation this
 * is built from. Deliberately still not a fork of
 * `frontend/src/app/(patient)/history/**`: different DTO shape
 * (`SimpleTriageSessionSummaryDTO`, no `chief_complaint`/`sbar_snippet`/
 * single `final_esi`), and filtering/pagination stay entirely client-side
 * (local `useState`, no new Zustand store) since this is a single page with
 * no cross-page filter persistence requirement.
 */

const PAGE_SIZE = 10;
const ESI_LEVELS = [1, 2, 3, 4, 5] as const;

type ReviewFilterValue = "ALL" | "APPROVED" | "OVERRIDDEN" | "RED_FLAG" | "PENDING";

const REVIEW_FILTER_OPTIONS: Array<{ value: ReviewFilterValue; label: string }> = [
  { value: "ALL", label: "Tất cả trạng thái thẩm định" },
  { value: "APPROVED", label: "Điều dưỡng đã duyệt" },
  { value: "OVERRIDDEN", label: "Có can thiệp (Override)" },
  // Độc lập với review_display_status -- lọc thẳng theo matched_esi_levels,
  // đúng nghĩa đen "cảnh báo đỏ ESI 1 hoặc 2" (pilot không có khái niệm
  // red-flag-locked/EMERGENCY_REJECTED như production).
  { value: "RED_FLAG", label: "Cảnh báo đỏ (ESI 1 hoặc 2)" },
  { value: "PENDING", label: "Ca chưa duyệt" },
];

function matchesReviewFilter(session: SimpleTriageSessionSummaryDTO, filter: ReviewFilterValue): boolean {
  switch (filter) {
    case "ALL":
      return true;
    case "APPROVED":
      return session.review_display_status === "APPROVED";
    case "OVERRIDDEN":
      return session.review_display_status === "OVERRIDDEN";
    case "RED_FLAG":
      return session.matched_esi_levels.some((level) => level === 1 || level === 2);
    case "PENDING":
      return session.review_display_status === "PENDING_REVIEW";
    default:
      return true;
  }
}

function formatDate(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function esiBadgeClass(level: number): string {
  if (level <= 2) return "border-rose-200 bg-rose-50 text-rose-900";
  if (level === 3) return "border-amber-200 bg-amber-50 text-amber-900";
  return "border-emerald-200 bg-emerald-50 text-emerald-900";
}

function StatCard({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: typeof Database;
  label: string;
  value: number;
  tone?: "rose" | "amber" | "emerald";
}) {
  const toneClass =
    tone === "rose"
      ? "text-rose-700"
      : tone === "amber"
        ? "text-amber-700"
        : tone === "emerald"
          ? "text-emerald-700"
          : "text-slate-800 dark:text-slate-100";
  return (
    <div className="rounded-2xl border border-border bg-card p-4">
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">
        <Icon className="size-4" aria-hidden="true" />
        {label}
      </div>
      <p className={cn("mt-2 text-2xl font-black", toneClass)}>{value}</p>
    </div>
  );
}

function SessionCard({
  session,
  profileName,
}: {
  session: SimpleTriageSessionSummaryDTO;
  profileName: string | null;
}) {
  const isActive = session.status === "ACTIVE";
  const aiProposedEsi = pilotAiProposedEsi(session.matched_esi_levels);
  return (
    <Link
      href={isActive ? `/triage-pilot?session_id=${session.session_id}` : `/triage-pilot/history/${session.session_id}`}
      className="block rounded-2xl border border-slate-200 bg-card p-4 transition-colors hover:border-sky-300 hover:bg-sky-50/40 sm:p-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {isActive ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-xs font-bold text-sky-900">
              <MessageCircleQuestion className="size-3.5" aria-hidden="true" />
              Đang thu thập
            </span>
          ) : (
            <SimplePilotReviewBadge status={session.review_display_status} />
          )}
          <SimplePilotEsiBadge
            aiProposedEsi={aiProposedEsi}
            finalEsi={session.final_esi}
            reviewStatus={session.review_display_status}
          />
          {session.unread_from_staff > 0 && (
            <span
              title="Nhân viên y tế vừa nhắn thêm"
              className="inline-flex items-center gap-1 rounded-full bg-teal-600 px-2.5 py-0.5 text-xs font-bold text-white"
            >
              <Stethoscope className="size-3.5" aria-hidden="true" />
              {session.unread_from_staff} tin mới
            </span>
          )}
        </div>
        <span className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
          <Clock3 className="size-3.5" aria-hidden="true" />
          {formatDate(session.started_at)}
        </span>
      </div>
      <p className="mt-3 line-clamp-2 text-base leading-6 text-foreground">
        {session.initial_message.trim() || "Chưa có mô tả triệu chứng"}
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
        <span>{session.turn_count} lượt hội thoại</span>
        <span aria-hidden="true">·</span>
        <span>{profileName ?? "Ẩn danh / chưa gắn hồ sơ"}</span>
      </div>
      <span className="mt-3 inline-block text-sm font-semibold text-sky-800">
        {isActive ? "Tiếp tục ca khám →" : "Xem chi tiết →"}
      </span>
    </Link>
  );
}

export default function SimpleTriageHistoryPage() {
  const { data, isLoading, isError, error, refetch } = useSimpleTriageSessions();
  const { data: profiles } = useGetProfiles();

  const [searchQuery, setSearchQuery] = useState("");
  const [reviewFilter, setReviewFilter] = useState<ReviewFilterValue>("ALL");
  // "ALL" | "ANONYMOUS" | a real profile id.
  const [profileFilter, setProfileFilter] = useState<string>("ALL");
  const [esiFilters, setEsiFilters] = useState<number[]>([]);
  const [page, setPage] = useState(1);

  const sessions = useMemo(() => data ?? [], [data]);

  const profileNameById = useMemo(() => {
    const map = new Map<string, string>();
    (profiles ?? []).forEach((profile) => {
      map.set(profile.id, `${profile.full_name} (${profile.relationship_type})`);
    });
    return map;
  }, [profiles]);

  // Tính từ toàn bộ danh sách chưa lọc, giống hệt cách production làm cho 4
  // thẻ thống kê của nó -- các thẻ này luôn phản ánh cả tài khoản, không đổi
  // theo bộ lọc đang chọn.
  const stats = useMemo(
    () => ({
      total: sessions.length,
      emergent: sessions.filter((session) => session.matched_esi_levels.some((level) => level === 1 || level === 2))
        .length,
      overridden: sessions.filter((session) => session.review_display_status === "OVERRIDDEN").length,
      approved: sessions.filter((session) => session.review_display_status === "APPROVED").length,
    }),
    [sessions],
  );

  const filteredSessions = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return sessions.filter((session) => {
      if (!matchesReviewFilter(session, reviewFilter)) return false;
      if (profileFilter === "ANONYMOUS" && session.profile_id !== null) return false;
      if (profileFilter !== "ALL" && profileFilter !== "ANONYMOUS" && session.profile_id !== profileFilter) {
        return false;
      }
      if (esiFilters.length > 0 && !session.matched_esi_levels.some((level) => esiFilters.includes(level))) {
        return false;
      }
      if (query) {
        const haystacks = [session.session_id, session.initial_message, session.final_message ?? ""];
        if (!haystacks.some((text) => text.toLowerCase().includes(query))) return false;
      }
      return true;
    });
  }, [sessions, reviewFilter, profileFilter, esiFilters, searchQuery]);

  const isFilterActive =
    searchQuery.trim() !== "" || reviewFilter !== "ALL" || profileFilter !== "ALL" || esiFilters.length > 0;

  const resetFilters = () => {
    setSearchQuery("");
    setReviewFilter("ALL");
    setProfileFilter("ALL");
    setEsiFilters([]);
  };

  const toggleEsiFilter = (level: number) => {
    setEsiFilters((prev) => (prev.includes(level) ? prev.filter((l) => l !== level) : [...prev, level]));
  };

  // Reset về trang 1 mỗi khi bất kỳ bộ lọc/tìm kiếm nào đổi -- tránh kẹt ở
  // một trang trống khi danh sách đã lọc ngắn lại. Theo đúng khuyến nghị của
  // React (đặt state trong lúc render khi 1 giá trị suy ra từ props/state
  // đổi, thay vì dùng useEffect chỉ để gọi setState) -- xem
  // https://react.dev/learn/you-might-not-need-an-effect.
  const filterKey = `${searchQuery}|${reviewFilter}|${profileFilter}|${esiFilters.join(",")}`;
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey);
  if (filterKey !== prevFilterKey) {
    setPrevFilterKey(filterKey);
    setPage(1);
  }

  const totalPages = Math.max(1, Math.ceil(filteredSessions.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageStart = (currentPage - 1) * PAGE_SIZE;
  const pagedSessions = filteredSessions.slice(pageStart, pageStart + PAGE_SIZE);

  const is503 = error instanceof Error && error.message.includes("SIMPLE_AGENT_ENABLED");

  return (
    <div className="h-full w-full overflow-y-auto bg-background rounded-3xl">
      <div className="w-full space-y-4 p-4 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card p-4">
          <h1 className="flex items-center gap-2 text-lg font-bold text-slate-950 dark:text-slate-50">
            <FlaskConical className="size-5 text-amber-600" aria-hidden="true" />
            Lịch sử sàng lọc Triage AI
          </h1>
          <Link
            href="/triage-pilot"
            className="flex min-h-10 items-center gap-2 rounded-xl bg-sky-700 px-4 text-sm font-semibold text-white hover:bg-sky-800"
          >
            <Plus className="size-4" aria-hidden="true" />
            Phiên mới
          </Link>
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center gap-3 py-16 text-slate-400">
            <Loader2 className="size-8 animate-spin text-sky-600" aria-hidden="true" />
            <span className="font-mono text-sm font-bold uppercase tracking-wider">Đang tải lịch sử...</span>
          </div>
        ) : isError ? (
          is503 ? (
            <div className="mx-auto flex max-w-lg flex-col items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center">
              <ShieldAlert className="size-10 text-amber-600" aria-hidden="true" />
              <p className="text-sm font-semibold text-amber-950">Triage Agent đang tắt trên môi trường này.</p>
            </div>
          ) : (
            <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center">
              <p className="text-sm font-semibold text-rose-900">Không thể tải lịch sử phiên.</p>
              <p className="mt-2 text-sm text-rose-800">
                {error instanceof Error ? error.message : "Vui lòng thử lại."}
              </p>
              <button
                type="button"
                onClick={() => void refetch()}
                className="mt-4 mx-auto flex min-h-10 items-center gap-2 rounded-xl border border-rose-300 bg-card px-4 text-sm font-semibold text-rose-800 hover:bg-rose-100"
              >
                Tải lại
              </button>
            </div>
          )
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard icon={Database} label="Tổng hồ sơ" value={stats.total} />
              <StatCard icon={AlertTriangle} label="Khẩn cấp (ESI 1-2)" value={stats.emergent} tone="rose" />
              <StatCard icon={Layers} label="Có can thiệp (Override)" value={stats.overridden} tone="amber" />
              <StatCard icon={CheckCircle2} label="Đã thẩm định hợp lệ" value={stats.approved} tone="emerald" />
            </div>

            <div className="space-y-3 rounded-2xl border border-border bg-card p-4">
              <div className="flex flex-col gap-3 sm:flex-row">
                <div className="relative flex-1">
                  <Search
                    className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400"
                    aria-hidden="true"
                  />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    placeholder="Tìm theo triệu chứng hoặc mã ca..."
                    className="h-10 w-full rounded-xl border border-slate-300 pl-9 pr-3 text-sm text-slate-800 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:text-slate-100 dark:border-slate-700"
                  />
                </div>
                <select
                  value={reviewFilter}
                  onChange={(event) => setReviewFilter(event.target.value as ReviewFilterValue)}
                  className="h-10 rounded-xl border border-slate-300 px-3 text-sm text-slate-800 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:text-slate-100 dark:border-slate-700"
                >
                  {REVIEW_FILTER_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <select
                  value={profileFilter}
                  onChange={(event) => setProfileFilter(event.target.value)}
                  className="h-10 rounded-xl border border-slate-300 px-3 text-sm text-slate-800 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:text-slate-100 dark:border-slate-700"
                >
                  <option value="ALL">Tất cả hồ sơ</option>
                  {(profiles ?? []).map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.full_name} ({profile.relationship_type})
                    </option>
                  ))}
                  <option value="ANONYMOUS">Ẩn danh / chưa gắn hồ sơ</option>
                </select>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Phân độ ESI:</span>
                {ESI_LEVELS.map((level) => (
                  <button
                    key={level}
                    type="button"
                    onClick={() => toggleEsiFilter(level)}
                    className={cn(
                      "rounded-full border px-3 py-1 text-xs font-bold transition-colors",
                      esiFilters.includes(level)
                        ? esiBadgeClass(level)
                        : "border-border bg-card text-muted-foreground hover:bg-background",
                    )}
                  >
                    ESI {level}
                  </button>
                ))}
                {isFilterActive && (
                  <button
                    type="button"
                    onClick={resetFilters}
                    className="ml-auto flex items-center gap-1.5 rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-bold text-rose-800 hover:bg-rose-100"
                  >
                    <X className="size-3.5" aria-hidden="true" />
                    Xóa bộ lọc
                  </button>
                )}
                <span className="text-xs font-semibold text-muted-foreground">{filteredSessions.length} ca phù hợp</span>
              </div>
            </div>

            {pagedSessions.length > 0 ? (
              <div className="space-y-3">
                {pagedSessions.map((session) => (
                  <SessionCard
                    key={session.session_id}
                    session={session}
                    profileName={session.profile_id ? profileNameById.get(session.profile_id) ?? null : null}
                  />
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
                {isFilterActive ? (
                  <div className="space-y-3">
                    <p>Không có ca nào khớp bộ lọc hiện tại.</p>
                    <button
                      type="button"
                      onClick={resetFilters}
                      className="mx-auto flex min-h-10 items-center gap-2 rounded-xl border border-slate-300 bg-card px-4 text-sm font-semibold text-slate-800 hover:bg-muted dark:text-slate-100 dark:border-slate-700"
                    >
                      Khôi phục bộ lọc mặc định
                    </button>
                  </div>
                ) : (
                  <>Bạn chưa có phiên sàng lọc nào. Nhấn &quot;Phiên mới&quot; để bắt đầu.</>
                )}
              </div>
            )}

            {filteredSessions.length > 0 && (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card p-3">
                <span className="text-xs font-semibold text-muted-foreground">
                  Hiển thị {pageStart + 1}-{Math.min(pageStart + PAGE_SIZE, filteredSessions.length)} trên{" "}
                  {filteredSessions.length} ca phù hợp
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={currentPage === 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    aria-label="Trang trước"
                    className="flex size-9 items-center justify-center rounded-lg border border-slate-300 text-slate-700 disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-200 dark:border-slate-700"
                  >
                    <ChevronLeft className="size-4" aria-hidden="true" />
                  </button>
                  <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                    Trang {currentPage} / {totalPages}
                  </span>
                  <button
                    type="button"
                    disabled={currentPage === totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    aria-label="Trang sau"
                    className="flex size-9 items-center justify-center rounded-lg border border-slate-300 text-slate-700 disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-200 dark:border-slate-700"
                  >
                    <ChevronRight className="size-4" aria-hidden="true" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
