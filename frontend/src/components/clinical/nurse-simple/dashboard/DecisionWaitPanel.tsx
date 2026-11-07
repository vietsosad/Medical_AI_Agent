"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ChartBarBig, ChevronsRight, Hourglass } from "lucide-react";
import { useState } from "react";

import { formatWait, WAIT_CRITICAL_MINUTES, WAIT_WARNING_MINUTES } from "@/components/clinical/nurse-simple/wait-time";
import { DURATION, EASE_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { SimpleDecisionWaitDTO, SimpleWaitBucketKey } from "@/types/simple-nurse";

import { formatCount, matrixRowLabel, matrixRowMeta, WAIT_BUCKET_META, waitBucketOf } from "./dashboard-model";
import {
  barDelayMs,
  type ChartView,
  DashboardPanel,
  EmptyNote,
  MarkTooltip,
  TooltipBody,
  useMarkFocus,
  ViewSwitch,
} from "./primitives";

/**
 * Trục cố định 0 - 120 phút: luôn chứa cả hai mốc tô màu của bảng ca (30 và
 * 60 phút) ở cùng một chỗ, nên đổi khoảng thời gian hay làm mới số liệu không
 * làm trục nhảy. Trung vị dài hơn thì thanh chạm mép và mang dấu "vượt khung";
 * số đúng luôn in ở cột bên phải.
 */
const AXIS_MAX_MINUTES = 2 * WAIT_CRITICAL_MINUTES;
const AXIS_TICKS = [0, WAIT_WARNING_MINUTES, WAIT_CRITICAL_MINUTES, 90, AXIS_MAX_MINUTES];

const MARK_ICON_INK: Record<SimpleWaitBucketKey, string> = {
  UNDER_WARNING: "text-emerald-600 dark:text-emerald-400",
  WARNING: "text-amber-600 dark:text-amber-400",
  CRITICAL: "text-rose-600 dark:text-rose-400",
};

/** Bề ngang cột nhãn và cột số: dùng chung cho hàng thanh và lớp vạch mốc vẽ đè lên. */
const LAYOUT_VARS = "[--label-w:6.5rem] [--value-w:5.5rem] sm:[--label-w:9rem] sm:[--value-w:7rem]";

/**
 * Trung vị thời gian chờ tới khi được chốt, theo mức AI đề xuất: từ
 * `waiting_since` của bảng ca (lúc ca vào hàng đợi) tới lúc điều dưỡng chốt.
 *
 * Mọi hàng nêu số ca của nó. Dưới `min_cases` ca, hàng chỉ nêu số ca và nói rõ
 * là chưa đủ để tính trung vị -- không vẽ thanh. Hai vạch đứng là hai mốc tô màu
 * của bảng ca, không phải chỉ tiêu.
 */
export function DecisionWaitPanel({
  wait,
  windowDays,
  order,
}: {
  wait: SimpleDecisionWaitDTO;
  windowDays: number;
  order: number;
}) {
  const [view, setView] = useState<ChartView>("chart");
  const rows = wait.rows.filter((row) => row.key !== "IN_PROGRESS" || row.count > 0);

  return (
    <DashboardPanel
      id="decision-wait"
      order={order}
      title="Thời gian chờ tới khi được chốt"
      subtitle={`Trung vị số phút từ lúc ca vào hàng đợi tới lúc điều dưỡng chốt, theo mức AI đề xuất, trên ${formatCount(wait.decided_total)} ca đã chốt trong ${windowDays} ngày qua.`}
      action={
        wait.decided_total > 0 ? (
          <ViewSwitch
            id="decision-wait-view"
            label="Cách xem thời gian chờ tới khi được chốt"
            view={view}
            onChange={setView}
            chartIcon={ChartBarBig}
          />
        ) : undefined
      }
    >
      {wait.decided_total === 0 ? (
        <EmptyNote icon={Hourglass}>
          Chưa có ca nào được chốt trong {windowDays} ngày qua nên chưa có thời gian chờ nào để tính.
        </EmptyNote>
      ) : (
        <>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={view}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: DURATION.quick, ease: EASE_OUT }}
            >
              {view === "chart" ? (
                <WaitBars rows={rows} minCases={wait.min_cases} />
              ) : (
                <WaitTable rows={rows} minCases={wait.min_cases} />
              )}
            </motion.div>
          </AnimatePresence>
          <p className="mt-4 border-t border-border pt-4 text-sm leading-6 text-muted-foreground">
            Vạch {WAIT_WARNING_MINUTES} và {WAIT_CRITICAL_MINUTES} phút là hai mốc tô màu thời gian chờ của bảng ca,
            không phải chỉ tiêu. Dưới {formatCount(wait.min_cases)} ca, một hàng chỉ nêu số ca, chưa nêu trung vị.
          </p>
        </>
      )}
    </DashboardPanel>
  );
}

type WaitRows = SimpleDecisionWaitDTO["rows"];

function medianNote(count: number, minCases: number): string {
  return count === 0 ? "Chưa có ca nào" : `Chưa đủ ca để tính trung vị (cần ít nhất ${formatCount(minCases)})`;
}

function WaitBars({ rows, minCases }: { rows: WaitRows; minCases: number }) {
  const { shownKey, markProps } = useMarkFocus(rows.map((row) => row.key));

  return (
    <div className={LAYOUT_VARS}>
      <div className="relative pt-8">
        {/* Hai vạch mốc vẽ một lần cho cả cột thanh, để chúng liền một nét qua mọi hàng. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 left-[calc(var(--label-w)+1rem)] right-[calc(var(--value-w)+1rem)]"
        >
          {[WAIT_WARNING_MINUTES, WAIT_CRITICAL_MINUTES].map((minutes) => {
            const bucket = waitBucketOf(minutes);
            const Icon = WAIT_BUCKET_META[bucket].icon;
            return (
              <span
                key={minutes}
                style={{ left: `${(minutes / AXIS_MAX_MINUTES) * 100}%` }}
                className="absolute inset-y-0 w-0.5 -translate-x-1/2 bg-foreground/50"
              >
                <span className="absolute left-2 top-0 flex items-center gap-1 whitespace-nowrap text-sm font-semibold leading-6 text-foreground">
                  <Icon className={cn("size-4 shrink-0", MARK_ICON_INK[bucket])} />
                  {minutes} phút
                </span>
              </span>
            );
          })}
        </div>

        <ul
          role="list"
          aria-label="Trung vị thời gian chờ tới khi được chốt, theo mức AI đề xuất"
          className="flex flex-col gap-2"
        >
          {rows.map((row, index) => {
            const meta = matrixRowMeta(row.key);
            const median = row.median_minutes;
            const bucket = median === null ? null : waitBucketOf(median);
            const share = median === null ? 0 : Math.min(median, AXIS_MAX_MINUTES) / AXIS_MAX_MINUTES;
            const beyond = median !== null && median > AXIS_MAX_MINUTES;
            const spoken =
              median === null
                ? `${matrixRowLabel(row.key)}: ${row.count} ca, ${medianNote(row.count, minCases).toLowerCase()}`
                : `${matrixRowLabel(row.key)}: trung vị ${formatWait(median)}, trên ${row.count} ca`;
            return (
              <li
                key={row.key}
                aria-label={spoken}
                {...markProps(row.key)}
                className="relative grid min-h-11 cursor-default grid-cols-[var(--label-w)_minmax(0,1fr)_var(--value-w)] items-center gap-x-4 rounded-xl outline-hidden focus-visible:ring-2 focus-visible:ring-brand"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span aria-hidden="true" className={cn("h-6 w-1 shrink-0 rounded-full", meta.rail)} />
                  <span className="min-w-0 leading-5">
                    <span className="block font-semibold text-foreground">{meta.name}</span>
                    <span className="block text-sm text-muted-foreground">{formatCount(row.count)} ca</span>
                  </span>
                </span>

                <span className="relative flex h-6 items-center">
                  <span aria-hidden="true" className="absolute inset-x-0 top-1/2 h-px bg-[var(--viz-grid)]" />
                  {median === null ? (
                    <span className="relative bg-card pr-2 text-sm leading-5 text-muted-foreground">
                      {medianNote(row.count, minCases)}
                    </span>
                  ) : (
                    <span
                      aria-hidden="true"
                      style={{
                        width: `${share * 100}%`,
                        backgroundColor: "var(--viz-slot-1)",
                        animationDelay: `${barDelayMs(index)}ms`,
                      }}
                      className="bar-grow relative flex h-3 min-w-2 items-center justify-end rounded-r-[4px] transition-[width] duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none"
                    >
                      {beyond ? <ChevronsRight className="mr-0.5 size-3 text-white" /> : null}
                    </span>
                  )}
                </span>

                <span className="flex items-center gap-1 text-base font-bold leading-6 text-foreground">
                  {median === null ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    <>
                      {bucket !== null && bucket !== "UNDER_WARNING"
                        ? (() => {
                            const Icon = WAIT_BUCKET_META[bucket].icon;
                            return <Icon className={cn("size-4 shrink-0", MARK_ICON_INK[bucket])} aria-hidden="true" />;
                          })()
                        : null}
                      <span className="min-w-0 leading-5">{formatWait(median)}</span>
                    </>
                  )}
                </span>

                <AnimatePresence>
                  {shownKey === row.key ? (
                    <MarkTooltip anchor={50}>
                      <TooltipBody
                        value={median === null ? `${formatCount(row.count)} ca` : `Trung vị ${formatWait(median)}`}
                        label={matrixRowLabel(row.key)}
                        detail={
                          median === null
                            ? medianNote(row.count, minCases)
                            : `Trên ${formatCount(row.count)} ca đã chốt${bucket && bucket !== "UNDER_WARNING" ? `, từ mốc ${bucket === "CRITICAL" ? WAIT_CRITICAL_MINUTES : WAIT_WARNING_MINUTES} phút của bảng ca` : ""}`
                        }
                      />
                    </MarkTooltip>
                  ) : null}
                </AnimatePresence>
              </li>
            );
          })}
        </ul>
      </div>

      <div
        aria-hidden="true"
        className="relative ml-[calc(var(--label-w)+1rem)] mr-[calc(var(--value-w)+1rem)] mt-2 h-6 text-sm leading-6 tabular-nums text-muted-foreground"
      >
        {AXIS_TICKS.map((tick) => (
          <span
            key={tick}
            style={{ left: `${(tick / AXIS_MAX_MINUTES) * 100}%` }}
            className="absolute -translate-x-1/2"
          >
            {tick}
          </span>
        ))}
      </div>
      <p aria-hidden="true" className="ml-[calc(var(--label-w)+1rem)] text-sm leading-6 text-muted-foreground">
        Phút, trục dừng ở {AXIS_MAX_MINUTES}; thanh có dấu mũi tên là trung vị dài hơn
      </p>
    </div>
  );
}

function WaitTable({ rows, minCases }: { rows: WaitRows; minCases: number }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Trung vị thời gian chờ tới khi được chốt, theo mức AI đề xuất</caption>
        <thead>
          <tr className="border-b border-border">
            <th scope="col" className="py-2 pr-4 font-semibold text-muted-foreground">
              Mức AI đề xuất
            </th>
            <th scope="col" className="px-4 py-2 text-right font-semibold text-muted-foreground">
              Số ca đã chốt
            </th>
            <th scope="col" className="py-2 pl-4 text-right font-semibold text-muted-foreground">
              Trung vị chờ
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row) => (
            <tr key={row.key}>
              <th scope="row" className="py-2 pr-4 font-medium text-foreground">
                {matrixRowLabel(row.key)}
              </th>
              <td className="px-4 py-2 text-right font-semibold tabular-nums text-foreground">
                {formatCount(row.count)}
              </td>
              <td className="py-2 pl-4 text-right text-foreground">
                {row.median_minutes === null ? (
                  <span className="text-muted-foreground">{medianNote(row.count, minCases)}</span>
                ) : (
                  formatWait(row.median_minutes)
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
