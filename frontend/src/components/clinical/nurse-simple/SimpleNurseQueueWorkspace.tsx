"use client";

import { useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import { CircleAlert, FlaskConical } from "lucide-react";

import { DURATION, EASE_OUT, enterTransition, exitTransition, staggerDelay } from "@/lib/motion";
import { SIMPLE_NURSE_QUERY_KEYS } from "@/queries/simple-nurse-query-keys";
import { useSimpleNurseQueue, useSimpleNurseQueueRealtime } from "@/queries/useSimpleNurseQueries";

import {
  ClearFiltersButton,
  EsiFilterChips,
  MineOnlySwitch,
  QUEUE_PANEL_ID,
  QueueBucketTabs,
  QueueSearchFields,
  bucketTabId,
} from "./queue/QueueControls";
import { QueueList } from "./queue/QueueList";
import { QueueLiveStatus } from "./queue/QueueLiveStatus";
import { QueuePagination } from "./queue/QueuePagination";
import {
  QueueEmptyState,
  QueueErrorState,
  QueueSkeleton,
  QueueStaleNotice,
  type QueueEmptyVariant,
} from "./queue/QueueStates";
import { useDebouncedValue } from "./queue/queue-hooks";
import {
  QUEUE_PAGE_SIZE,
  QUEUE_VIEWS,
  SHARED_PARKED_PARAMS,
  SHARED_QUEUE_PARAMS,
  parseQueueTab,
  type QueueBucketKey,
  type QueueTab,
} from "./queue/queue-model";

/**
 * Bảng điều phối ca Triage Agent (HITL), tuyến `/clinical/queue-pilot`.
 *
 * Mọi góc nhìn đều đọc chung `GET /nurse-simple/queue` (qua
 * `useSimpleNurseQueue`), chỉ khác `bucket`/`mine_only`. Góc nhìn nằm trên URL
 * (`?tab=queue|mine|parked|decided`) để thanh điều phối và các màn khác trỏ
 * thẳng vào được: ba nhóm ca là thanh chọn, "Chỉ ca của tôi" là công tắc của
 * nhóm "Đang chờ" (`tab=mine`).
 *
 * Thứ tự ca do backend quyết định (`_urgency_rank`): dấu hiệu nguy kịch xếp
 * ngang ESI 1, rồi theo ESI, rồi ca chờ lâu hơn; nhóm "Đã quyết định" xếp ca
 * chốt gần nhất lên trên. Màn hình giữ nguyên thứ tự đó, không tự sắp lại.
 */

const SEARCH_DEBOUNCE_MS = 300;

/** Trang mới: nội dung nổi lên 8 px theo từng khối, cách nhau 50 ms. */
const blockVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: (index: number) => ({ opacity: 1, y: 0, transition: { ...enterTransition, delay: staggerDelay(index) } }),
};

export function SimpleNurseQueueWorkspace() {
  // Kênh trực tiếp chỉ mang tín hiệu "có thay đổi, đọc lại"; trạng thái của nó
  // cho biết thay đổi có được đẩy tới ngay hay chờ nhịp tự tải lại.
  const { status: channelStatus } = useSimpleNurseQueueRealtime();
  const queryClient = useQueryClient();

  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const tab = parseQueueTab(searchParams.get("tab"));
  const view = QUEUE_VIEWS[tab];

  const [q, setQ] = useState("");
  const [patientEmail, setPatientEmail] = useState("");
  const [esiLevels, setEsiLevels] = useState<number[]>([]);
  const [page, setPage] = useState(1);
  const [refreshing, setRefreshing] = useState(false);

  // Ô tìm kiếm chỉ gửi đi khi người dùng ngừng gõ; xóa trắng thì áp dụng ngay.
  const debouncedQ = useDebouncedValue(q.trim(), SEARCH_DEBOUNCE_MS);
  const debouncedEmail = useDebouncedValue(patientEmail.trim(), SEARCH_DEBOUNCE_MS);
  const appliedQ = q.trim() === "" ? "" : debouncedQ;
  const appliedEmail = patientEmail.trim() === "" ? "" : debouncedEmail;
  const filtersApplied = appliedQ !== "" || appliedEmail !== "" || esiLevels.length > 0;
  const isFilterActive = q.trim() !== "" || patientEmail.trim() !== "" || esiLevels.length > 0;

  // Reset về trang 1 khi đổi tab/bộ lọc -- đặt state ngay trong lúc render
  // thay vì dùng useEffect chỉ để gọi setState (khuyến nghị của React).
  const filterKey = `${tab}|${appliedQ}|${appliedEmail}|${esiLevels.join(",")}`;
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey);
  if (filterKey !== prevFilterKey) {
    setPrevFilterKey(filterKey);
    if (page !== 1) setPage(1);
  }

  const queue = useSimpleNurseQueue({
    bucket: view.bucket,
    mineOnly: view.mineOnly,
    q: appliedQ || undefined,
    patientEmail: appliedEmail || undefined,
    esiLevels: esiLevels.length > 0 ? esiLevels : undefined,
    page,
    pageSize: QUEUE_PAGE_SIZE,
  });
  // Bộ đếm của từng nhóm là cả nhóm, không theo bộ lọc. Hai lời gọi này trùng
  // khóa với lời gọi mặc định của tab tương ứng (và của thanh điều phối), nên
  // TanStack Query dùng chung kết quả thay vì gọi mạng thêm.
  const queueTotals = useSimpleNurseQueue(SHARED_QUEUE_PARAMS);
  const parkedTotals = useSimpleNurseQueue(SHARED_PARKED_PARAMS);

  const counts: Partial<Record<QueueBucketKey, number>> = {
    // Số ca chưa ai nhận -- đúng bằng số hàng của tab "Đang chờ".
    queue: queueTotals.data?.pagination.total_items,
    parked: parkedTotals.data?.pagination.total_items,
  };
  const mineCount = queueTotals.data?.summary.mine_count;
  const insufficientCount = queueTotals.data?.summary.insufficient_count ?? 0;

  const goToTab = (next: QueueTab) => {
    router.replace(`${pathname}?tab=${next}`, { scroll: false });
  };

  const toggleEsiLevel = (level: number) => {
    setEsiLevels((current) =>
      current.includes(level) ? current.filter((value) => value !== level) : [...current, level].sort(),
    );
  };

  const resetFilters = () => {
    setQ("");
    setPatientEmail("");
    setEsiLevels([]);
  };

  const refresh = () => {
    setRefreshing(true);
    void queryClient
      .invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.queueAll() })
      .finally(() => setRefreshing(false));
  };

  const changePage = (next: number) => {
    setPage(next);
    // Bấm "Trang sau" ở cuối danh sách thì đưa mắt về đầu trang mới.
    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;
    document.getElementById(QUEUE_PANEL_ID)?.scrollIntoView?.({
      block: "start",
      behavior: reduceMotion ? "auto" : "smooth",
    });
  };

  const emptyVariant: QueueEmptyVariant = filtersApplied ? "filtered" : tab;
  const emptyAction = filtersApplied
    ? { label: "Xóa bộ lọc để xem toàn bộ", onClick: resetFilters }
    : tab === "mine"
      ? { label: "Xem hàng đợi chung", onClick: () => goToTab("queue") }
      : undefined;
  const errorMessage = queue.error instanceof Error ? queue.error.message : "Không thể tải hàng đợi.";
  const viewKey = `${filterKey}|${page}`;

  return (
    <motion.div initial="hidden" animate="visible" className="flex flex-col gap-6">
      {/* ------------------------------------------------------ ĐẦU TRANG */}
      <motion.header custom={0} variants={blockVariants} className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0 max-w-2xl">
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">Hàng đợi điều phối</h1>
            <AnimatePresence mode="wait" initial={false}>
              <motion.p
                key={tab}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0, transition: { duration: DURATION.quick, ease: EASE_OUT } }}
                exit={{ opacity: 0, transition: exitTransition }}
                className="mt-2 text-sm leading-6 text-muted-foreground sm:text-base"
              >
                {view.description}
              </motion.p>
            </AnimatePresence>
          </div>
          <QueueLiveStatus
            updatedAt={queue.dataUpdatedAt}
            failed={queue.isError}
            channel={channelStatus}
            refreshing={refreshing}
            onRefresh={refresh}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <p className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-4 py-2 text-sm font-medium text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
            <FlaskConical className="size-4 shrink-0" aria-hidden="true" />
            Hàng đợi Triage Agent — tách biệt hoàn toàn với hàng đợi Triage chính thức
          </p>
          {view.bucket === "QUEUE" && insufficientCount > 0 && (
            <p className="inline-flex items-center gap-2 rounded-full bg-muted px-4 py-2 text-sm font-medium text-foreground">
              <CircleAlert className="size-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
              <span>
                <span className="font-bold tabular-nums">{insufficientCount}</span> ca trong hàng đợi thiếu dữ liệu kết luận
              </span>
            </p>
          )}
        </div>
      </motion.header>

      {/* ------------------------------------------------ NHÓM CA & BỘ LỌC */}
      <motion.section custom={1} variants={blockVariants} aria-label="Nhóm ca và bộ lọc" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <QueueBucketTabs
            active={view.bucketKey}
            counts={counts}
            onSelect={goToTab}
          />
          {view.bucket === "QUEUE" && (
            <MineOnlySwitch
              checked={view.mineOnly}
              count={mineCount}
              onChange={(next) => goToTab(next ? "mine" : "queue")}
            />
          )}
        </div>

        <div className="flex flex-col gap-4 2xl:flex-row 2xl:items-center">
          <QueueSearchFields q={q} email={patientEmail} onQueryChange={setQ} onEmailChange={setPatientEmail} />
          <div className="flex flex-wrap items-center gap-2">
            <EsiFilterChips selected={esiLevels} onToggle={toggleEsiLevel} />
            <ClearFiltersButton visible={isFilterActive} onClear={resetFilters} />
          </div>
        </div>
      </motion.section>

      {/* --------------------------------------------------------- BẢNG CA */}
      <motion.section
        custom={2}
        variants={blockVariants}
        id={QUEUE_PANEL_ID}
        role="tabpanel"
        aria-labelledby={bucketTabId(view.bucketKey)}
        aria-busy={!queue.data && !queue.isError}
        className="scroll-mt-4"
      >
        <AnimatePresence initial={false}>
          {queue.isError && queue.data && (
            <QueueStaleNotice
              key="stale"
              className="mb-4"
              message={errorMessage}
              retrying={refreshing}
              onRetry={refresh}
            />
          )}
        </AnimatePresence>

        {queue.data ? (
          <>
            <QueueList
              key={viewKey}
              items={queue.data.items}
              view={view}
              empty={<QueueEmptyState variant={emptyVariant} action={emptyAction} />}
            />
            {queue.data.pagination.total_items > 0 && (
              <QueuePagination pagination={queue.data.pagination} onPageChange={changePage} />
            )}
          </>
        ) : queue.isError ? (
          <QueueErrorState message={errorMessage} retrying={refreshing} onRetry={refresh} />
        ) : (
          <QueueSkeleton />
        )}
      </motion.section>
    </motion.div>
  );
}
