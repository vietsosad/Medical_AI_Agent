"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import {
  ChevronLeft,
  ChevronRight,
  History,
  PhoneCall,
  Plus,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";

import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { esiTileClass } from "@/components/patient/EsiTile";
import { HistorySessionCard, InProgressSessionCard } from "@/components/patient/HistorySessionCard";
import { SegmentedControl, segmentTabId, type SegmentOption } from "@/components/patient/SegmentedControl";
import {
  activityDateOf,
  displayedEsiOf,
  formatClock,
  formatSubject,
  groupByDay,
  matchesSegment,
  relationShortLabel,
  sessionStatusKind,
  subjectLabelFor,
  type ConfirmedKind,
  type HistorySegment,
} from "@/components/patient/history-model";
import { DURATION, EASE_OUT, enterTransition, layoutTransition, staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useGetProfiles } from "@/queries/useProfileQueries";
import { useSimpleTriageSessions } from "@/queries/useSimpleTriageQueries";
import { isPilotUnavailableError } from "@/services/simple-triage.service";
import type { SimpleTriageSessionSummaryDTO } from "@/types/simple-triage";

/**
 * "Lịch sử sàng lọc" của Triage Agent. Ba nút lọc chính theo trạng thái thẩm
 * định, phiên đang hỏi dở ghim trên đầu, các phiên đã xong xếp theo ngày.
 * Lọc, tìm kiếm và phân trang chạy hoàn toàn ở máy khách (state cục bộ, không
 * cần store chung) vì không có yêu cầu giữ bộ lọc khi rời trang.
 *
 * Bộ lọc cũ được giữ đủ: "Điều dưỡng đã duyệt" / "Có can thiệp" thành bộ lọc
 * phụ dưới "Đã xác nhận"; "Cảnh báo đỏ ESI 1-2" tương đương chọn ESI 1 và 2
 * trong "Bộ lọc".
 */

const PAGE_SIZE = 10;
const ESI_LEVELS = [1, 2, 3, 4, 5] as const;
const PANEL_ID = "history-results";
const SEGMENT_ID_PREFIX = "history-segment";

const SEGMENTS: ReadonlyArray<SegmentOption<HistorySegment>> = [
  { value: "ALL", label: "Tất cả" },
  { value: "PENDING", label: "Chờ xác nhận" },
  { value: "CONFIRMED", label: "Đã xác nhận" },
];

const CONFIRMED_KINDS: ReadonlyArray<{ value: ConfirmedKind; label: string }> = [
  { value: "ALL", label: "Tất cả" },
  { value: "APPROVED", label: "Giữ nguyên đề xuất" },
  { value: "OVERRIDDEN", label: "Điều dưỡng điều chỉnh" },
];

type ProfileFilter = "ALL" | "ANONYMOUS" | (string & {});

/** Mục vào lần lượt khi danh sách hiện ra; mục đã nằm trên màn hình không chạy lại. */
const listItemVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: { ...enterTransition, delay: staggerDelay(index) },
  }),
};

/** Bật tắt bảng lọc: 180 ms, như mọi thao tác bật tắt khác. */
const panelVariants: Variants = {
  hidden: { opacity: 0, y: -8 },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.quick, ease: EASE_OUT } },
  exit: { opacity: 0, transition: { duration: DURATION.quick * 0.75 } },
};

function matchesProfile(session: SimpleTriageSessionSummaryDTO, filter: ProfileFilter): boolean {
  if (filter === "ALL") return true;
  if (filter === "ANONYMOUS") return session.profile_id === null;
  return session.profile_id === filter;
}

function matchesSearch(session: SimpleTriageSessionSummaryDTO, query: string): boolean {
  if (!query) return true;
  const haystacks = [session.session_id, session.initial_message, session.final_message ?? ""];
  return haystacks.some((text) => text.toLowerCase().includes(query));
}

function HistorySkeleton() {
  return (
    <div aria-busy="true" aria-label="Đang tải lịch sử sàng lọc" className="space-y-2">
      <div className="h-6 w-24 rounded-lg bg-muted" />
      {[0, 1, 2].map((item) => (
        <div
          key={item}
          className="skeleton-sweep relative flex items-center gap-4 overflow-hidden rounded-2xl border border-border bg-card p-4"
        >
          <div className="size-12 shrink-0 rounded-2xl bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-3/4 rounded-lg bg-muted" />
            <div className="h-4 w-1/2 rounded-lg bg-muted" />
            <div className="h-6 w-40 rounded-full bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function SimpleTriageHistoryPage() {
  const { data, isLoading, isError, error, refetch } = useSimpleTriageSessions();
  const { data: profiles } = useGetProfiles();

  const [segment, setSegment] = useState<HistorySegment>("ALL");
  const [confirmedKind, setConfirmedKind] = useState<ConfirmedKind>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [profileFilter, setProfileFilter] = useState<ProfileFilter>("ALL");
  const [esiFilters, setEsiFilters] = useState<number[]>([]);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [page, setPage] = useState(1);
  const listTopRef = useRef<HTMLDivElement>(null);

  const sessions = useMemo(() => data ?? [], [data]);
  const pendingCount = useMemo(
    () => sessions.filter((session) => sessionStatusKind(session) === "AWAITING_NURSE").length,
    [sessions],
  );

  const filteredSessions = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return sessions.filter((session) => {
      if (!matchesSegment(session, segment, confirmedKind)) return false;
      if (!matchesProfile(session, profileFilter)) return false;
      if (esiFilters.length > 0) {
        // Lọc theo đúng mức đang hiện trên ô ESI của từng phiên, để không bao
        // giờ có cảnh chọn "ESI 2" mà thấy một ô ghi ESI 4.
        const level = displayedEsiOf(session);
        if (level === null || !esiFilters.includes(level)) return false;
      }
      return matchesSearch(session, query);
    });
  }, [sessions, segment, confirmedKind, profileFilter, esiFilters, searchQuery]);

  // Phiên đang hỏi dở gần nhất được ghim lên đầu ở chế độ "Tất cả"; máy chủ đã
  // xếp theo lần hoạt động gần nhất nên phiên đầu tiên tìm thấy là phiên mới nhất.
  const pinnedSession = segment === "ALL" ? filteredSessions.find((session) => session.status === "ACTIVE") : undefined;
  const listedSessions = pinnedSession
    ? filteredSessions.filter((session) => session.session_id !== pinnedSession.session_id)
    : filteredSessions;

  const totalPages = Math.max(1, Math.ceil(listedSessions.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageStart = (currentPage - 1) * PAGE_SIZE;
  const pagedSessions = listedSessions.slice(pageStart, pageStart + PAGE_SIZE);
  const now = new Date();
  const dayGroups = groupByDay(pagedSessions, activityDateOf, now);

  const advancedFilterCount = (profileFilter !== "ALL" ? 1 : 0) + esiFilters.length;
  const isFilterActive =
    segment !== "ALL" || confirmedKind !== "ALL" || searchQuery.trim() !== "" || advancedFilterCount > 0;

  const subjectOf = (session: SimpleTriageSessionSummaryDTO) =>
    formatSubject(subjectLabelFor(session.profile_id, profiles));
  const timeOf = (session: SimpleTriageSessionSummaryDTO) => {
    const date = activityDateOf(session);
    return date ? formatClock(date) : null;
  };

  // Mọi thay đổi bộ lọc đưa về trang 1, để không kẹt ở một trang đã rỗng.
  const changeSegment = (next: HistorySegment) => {
    setSegment(next);
    setConfirmedKind("ALL");
    setPage(1);
  };
  const changeConfirmedKind = (next: ConfirmedKind) => {
    setConfirmedKind(next);
    setPage(1);
  };
  const changeSearch = (next: string) => {
    setSearchQuery(next);
    setPage(1);
  };
  const changeProfileFilter = (next: ProfileFilter) => {
    setProfileFilter(next);
    setPage(1);
  };
  const toggleEsiFilter = (level: number) => {
    setEsiFilters((prev) => (prev.includes(level) ? prev.filter((item) => item !== level) : [...prev, level]));
    setPage(1);
  };
  const resetFilters = () => {
    setSegment("ALL");
    setConfirmedKind("ALL");
    setSearchQuery("");
    setProfileFilter("ALL");
    setEsiFilters([]);
    setPage(1);
  };
  const goToPage = (next: number) => {
    setPage(next);
    listTopRef.current?.scrollIntoView({ block: "start" });
  };

  const isUnavailable = isPilotUnavailableError(error);
  const hasSessions = sessions.length > 0;
  const hasResults = pinnedSession !== undefined || pagedSessions.length > 0;
  // Thứ tự vào lần lượt theo đúng thứ tự đọc: thẻ ghim trước, rồi từng phiên.
  const staggerOffset = pinnedSession ? 1 : 0;
  const staggerIndexById = new Map(
    pagedSessions.map((session, index) => [session.session_id, index + staggerOffset] as const),
  );

  return (
    <div className="h-full w-full overflow-y-auto bg-background">
      <div className="mx-auto w-full max-w-3xl space-y-6 px-4 pb-8 pt-6 sm:px-6">
        <header className="page-enter space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">Lịch sử sàng lọc</h1>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {isLoading
                  ? "Đang tải các phiên của bạn..."
                  : hasSessions
                    ? `${sessions.length} phiên · ${
                        pendingCount > 0
                          ? `${pendingCount} phiên đang chờ điều dưỡng xác nhận`
                          : "không có phiên nào đang chờ xác nhận"
                      }`
                    : "Các phiên sàng lọc của bạn và người thân sẽ được lưu ở đây."}
              </p>
            </div>
            {/* Trên điện thoại, "Sàng lọc" ở thanh điều hướng đáy đã là lối bắt đầu phiên mới. */}
            <Link
              href="/triage-pilot"
              className="hidden min-h-11 shrink-0 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-bold text-brand-foreground shadow-sm transition duration-[180ms] hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.97] motion-reduce:transition-none motion-reduce:active:scale-100 md:flex"
            >
              <Plus className="size-4" aria-hidden="true" />
              Phiên mới
            </Link>
          </div>

          <SegmentedControl
            label="Lọc theo trạng thái thẩm định"
            options={SEGMENTS}
            value={segment}
            onChange={changeSegment}
            idPrefix={SEGMENT_ID_PREFIX}
            panelId={PANEL_ID}
            layoutId="history-segment-highlight"
          />

          <AnimatePresence initial={false}>
            {segment === "CONFIRMED" && (
              <motion.div
                key="confirmed-kind"
                variants={panelVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                role="group"
                aria-label="Kết quả thẩm định"
                className="flex flex-wrap gap-2"
              >
                {CONFIRMED_KINDS.map((option) => {
                  const selected = confirmedKind === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => changeConfirmedKind(option.value)}
                      className={cn(
                        "min-h-11 rounded-full border px-4 text-sm font-semibold transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                        selected
                          ? "border-brand-edge bg-brand-soft text-brand-ink"
                          : "border-border bg-card text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>

          <div className="flex gap-2">
            <div className="relative min-w-0 flex-1">
              <Search
                className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <input
                type="search"
                value={searchQuery}
                onChange={(event) => changeSearch(event.target.value)}
                aria-label="Tìm phiên sàng lọc"
                placeholder="Tìm triệu chứng, mã ca"
                className={cn(
                  "min-h-11 w-full rounded-xl border border-border bg-card pl-10 text-base text-foreground placeholder:text-muted-foreground focus-visible:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30 [&::-webkit-search-cancel-button]:hidden",
                  searchQuery ? "pr-12" : "pr-4",
                )}
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => changeSearch("")}
                  aria-label="Xóa nội dung tìm kiếm"
                  className="absolute right-0 top-0 flex size-11 items-center justify-center rounded-xl text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                >
                  <X className="size-4" aria-hidden="true" />
                </button>
              )}
            </div>
            <button
              type="button"
              aria-expanded={filtersOpen}
              aria-controls="history-advanced-filters"
              onClick={() => setFiltersOpen((open) => !open)}
              className={cn(
                "flex min-h-11 shrink-0 items-center gap-2 rounded-xl border px-4 text-sm font-semibold transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                filtersOpen || advancedFilterCount > 0
                  ? "border-brand-edge bg-brand-soft text-brand-ink"
                  : "border-border bg-card text-foreground hover:bg-muted",
              )}
            >
              <SlidersHorizontal className="size-4" aria-hidden="true" />
              Bộ lọc
              {advancedFilterCount > 0 && (
                <span className="rounded-full bg-brand px-2 text-sm font-bold leading-6 text-brand-foreground">
                  {advancedFilterCount}
                  <span className="sr-only"> bộ lọc đang bật</span>
                </span>
              )}
            </button>
          </div>

          <AnimatePresence initial={false}>
            {filtersOpen && (
              <motion.div
                key="advanced-filters"
                id="history-advanced-filters"
                variants={panelVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="space-y-4 rounded-2xl border border-border bg-card p-4"
              >
                <div>
                  <label htmlFor="history-profile-filter" className="text-sm font-semibold text-foreground">
                    Sàng lọc cho ai
                  </label>
                  <select
                    id="history-profile-filter"
                    value={profileFilter}
                    onChange={(event) => changeProfileFilter(event.target.value)}
                    className="mt-2 min-h-11 w-full rounded-xl border border-border bg-background px-4 text-base text-foreground focus-visible:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30"
                  >
                    <option value="ALL">Tất cả hồ sơ</option>
                    {(profiles ?? []).map((profile) => (
                      <option key={profile.id} value={profile.id}>
                        {profile.full_name} ({relationShortLabel(profile.relationship_type)})
                      </option>
                    ))}
                    <option value="ANONYMOUS">Ẩn danh / chưa gắn hồ sơ</option>
                  </select>
                </div>

                <fieldset>
                  <legend className="text-sm font-semibold text-foreground">Mức ESI đang hiển thị</legend>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {ESI_LEVELS.map((level) => {
                      const selected = esiFilters.includes(level);
                      return (
                        <button
                          key={level}
                          type="button"
                          aria-pressed={selected}
                          onClick={() => toggleEsiFilter(level)}
                          className={cn(
                            "min-h-11 rounded-xl border px-4 text-sm font-bold transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                            selected
                              ? esiTileClass(level)
                              : "border-border bg-background text-muted-foreground hover:text-foreground",
                          )}
                        >
                          ESI {level} · {esiTheme(level).label}
                        </button>
                      );
                    })}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    Là mức điều dưỡng đã chốt, hoặc mức AI đề xuất khi phiên chưa được xác nhận.
                  </p>
                </fieldset>
              </motion.div>
            )}
          </AnimatePresence>
        </header>

        <div
          ref={listTopRef}
          id={PANEL_ID}
          role="tabpanel"
          aria-labelledby={segmentTabId(SEGMENT_ID_PREFIX, segment)}
          className="scroll-mt-24 space-y-6"
        >
          {isLoading ? (
            <HistorySkeleton />
          ) : isError ? (
            isUnavailable ? (
              <div className="space-y-4 rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
                <p className="text-base font-bold">Chưa xem được lịch sử lúc này.</p>
                <p className="text-sm leading-6">
                  {error instanceof Error ? error.message : "Dịch vụ sàng lọc AI tạm thời chưa hoạt động."} Lịch sử sẽ
                  hiện lại khi dịch vụ hoạt động. Nếu đang có dấu hiệu nguy kịch, hãy gọi 115.
                </p>
                <a
                  href="tel:115"
                  aria-label="Gọi Tổng đài Cấp cứu Quốc gia 115"
                  className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-rose-700 px-4 text-sm font-bold text-white transition-colors hover:bg-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
                >
                  <PhoneCall className="size-4" aria-hidden="true" />
                  Gọi 115
                </a>
              </div>
            ) : (
              <div
                role="alert"
                className="space-y-4 rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-900 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-100"
              >
                <div>
                  <p className="text-base font-bold">Không thể tải lịch sử phiên.</p>
                  <p className="mt-2 text-sm leading-6">
                    {error instanceof Error ? error.message : "Vui lòng thử lại."}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void refetch()}
                  className="flex min-h-11 items-center gap-2 rounded-xl border border-rose-300 bg-card px-4 text-sm font-semibold text-rose-800 transition-colors hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 dark:border-rose-800 dark:text-rose-200 dark:hover:bg-rose-950"
                >
                  Tải lại
                </button>
              </div>
            )
          ) : !hasSessions ? (
            <div className="flex flex-col items-center gap-4 rounded-3xl border border-dashed border-border bg-card px-6 py-12 text-center">
              <span className="flex size-14 items-center justify-center rounded-2xl bg-brand-soft text-brand">
                <History className="size-7" aria-hidden="true" />
              </span>
              <div className="max-w-sm space-y-2">
                <p className="text-base font-bold text-foreground">Bạn chưa có phiên sàng lọc nào</p>
                <p className="text-sm leading-6 text-muted-foreground">
                  Mỗi lần bạn mô tả triệu chứng, phiên đó được lưu ở đây cùng kết quả xác nhận của điều dưỡng.
                </p>
              </div>
              <Link
                href="/triage-pilot"
                className="flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-bold text-brand-foreground transition-colors hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2"
              >
                <Plus className="size-4" aria-hidden="true" />
                Bắt đầu sàng lọc
              </Link>
            </div>
          ) : (
            <>
              {isFilterActive && (
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p aria-live="polite" className="text-sm font-semibold text-muted-foreground">
                    {filteredSessions.length} phiên phù hợp
                  </p>
                  <button
                    type="button"
                    onClick={resetFilters}
                    className="flex min-h-11 items-center gap-2 rounded-xl px-2 text-sm font-semibold text-brand hover:text-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                  >
                    <X className="size-4" aria-hidden="true" />
                    Xóa bộ lọc
                  </button>
                </div>
              )}

              {!hasResults ? (
                <div className="space-y-4 rounded-3xl border border-dashed border-border bg-card px-6 py-12 text-center">
                  <p className="text-base font-semibold text-foreground">Không có phiên nào khớp bộ lọc hiện tại.</p>
                  <button
                    type="button"
                    onClick={resetFilters}
                    className="mx-auto flex min-h-11 items-center gap-2 rounded-xl border border-border bg-background px-4 text-sm font-semibold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                  >
                    Khôi phục bộ lọc mặc định
                  </button>
                </div>
              ) : (
                <>
                  {pinnedSession && (
                    <motion.div
                      key={`pinned-${pinnedSession.session_id}`}
                      custom={0}
                      variants={listItemVariants}
                      initial="hidden"
                      animate="visible"
                    >
                      <InProgressSessionCard
                        session={pinnedSession}
                        subject={subjectOf(pinnedSession)}
                        timeLabel={timeOf(pinnedSession)}
                      />
                    </motion.div>
                  )}

                  {dayGroups.map((group) => {
                    const headingId = `history-day-${group.key}`;
                    return (
                      <section key={group.key} aria-labelledby={headingId}>
                        <h2 id={headingId} className="px-2 pb-2 text-sm font-bold text-muted-foreground">
                          {group.label}
                        </h2>
                        <ol className="space-y-2">
                          {group.items.map((session) => (
                            <motion.li
                              key={session.session_id}
                              layout="position"
                              custom={staggerIndexById.get(session.session_id) ?? 0}
                              variants={listItemVariants}
                              initial="hidden"
                              animate="visible"
                              transition={{ layout: layoutTransition }}
                            >
                              <HistorySessionCard
                                session={session}
                                subject={subjectOf(session)}
                                timeLabel={timeOf(session)}
                              />
                            </motion.li>
                          ))}
                        </ol>
                      </section>
                    );
                  })}
                </>
              )}

              {totalPages > 1 && (
                <nav aria-label="Phân trang" className="flex flex-wrap items-center justify-between gap-4">
                  <p className="text-sm text-muted-foreground">
                    Hiển thị {pageStart + 1}–{Math.min(pageStart + PAGE_SIZE, listedSessions.length)} trên{" "}
                    {listedSessions.length} phiên
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={currentPage === 1}
                      onClick={() => goToPage(Math.max(1, currentPage - 1))}
                      aria-label="Trang trước"
                      className="flex size-11 items-center justify-center rounded-xl border border-border bg-card text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <ChevronLeft className="size-4" aria-hidden="true" />
                    </button>
                    <span className="text-sm font-semibold text-foreground">
                      Trang {currentPage} / {totalPages}
                    </span>
                    <button
                      type="button"
                      disabled={currentPage === totalPages}
                      onClick={() => goToPage(Math.min(totalPages, currentPage + 1))}
                      aria-label="Trang sau"
                      className="flex size-11 items-center justify-center rounded-xl border border-border bg-card text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <ChevronRight className="size-4" aria-hidden="true" />
                    </button>
                  </div>
                </nav>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
