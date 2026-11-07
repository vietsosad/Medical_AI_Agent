"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Clock3 } from "lucide-react";
import { useState, type CSSProperties } from "react";

import { DURATION, EASE_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { SimpleHourOfDayDTO } from "@/types/simple-nurse";

import {
  formatCount,
  hourOfDayInLocalTime,
  hourRangeLabel,
  localOffsetMinutes,
  niceCountAxis,
  percentOf,
  type LocalHourPoint,
} from "./dashboard-model";
import { type ChartView, DashboardPanel, EmptyNote, MarkTooltip, TooltipBody, useMarkFocus, ViewSwitch } from "./primitives";

/** Chiều cao vùng vẽ; dải nhãn trục hoành nằm ngoài con số này. */
const PLOT_HEIGHT_CLASS = "h-48";
/** Nhãn trục hoành cách nhau 3 giờ: đủ định vị mà không chen chúc. */
const TICK_EVERY_HOURS = 3;

/**
 * Giờ trong ngày có nhiều phiên kết thúc, cộng dồn trong cửa sổ đang xem:
 * trả lời "kíp trực đông vào lúc nào". Một chuỗi nên một màu (slot-1), không
 * chú giải; giờ đông nhất được ghi số ngay trên cột, các giờ khác đọc qua trục,
 * chú thích nổi hoặc bản bảng số liệu.
 *
 * Backend đếm theo giờ UTC; màn xoay sang giờ trên máy người xem. Độ lệch lẻ
 * (không tròn giờ) thì giữ nhãn UTC và nói rõ, thay vì gán sai giờ.
 */
export function HourProfilePanel({
  points,
  windowDays,
  order,
}: {
  points: SimpleHourOfDayDTO[];
  windowDays: number;
  order: number;
}) {
  const [view, setView] = useState<ChartView>("chart");
  const local = hourOfDayInLocalTime(points, localOffsetMinutes());
  const series: LocalHourPoint[] =
    local ?? points.map((point) => ({ hour: point.hour_utc, completed: point.completed }));
  const total = series.reduce((sum, point) => sum + point.completed, 0);
  const peak = series.reduce<LocalHourPoint | null>(
    (best, point) => (point.completed > 0 && (best === null || point.completed > best.completed) ? point : best),
    null,
  );
  const clock = local ? "theo giờ trên máy của bạn" : "theo giờ UTC";

  return (
    <DashboardPanel
      id="busy-hours"
      order={order}
      title="Giờ có nhiều phiên kết thúc"
      subtitle={`Cộng dồn ${windowDays} ngày qua, ${clock}.`}
      action={total > 0 ? <ViewSwitch id="busy-hours-view" label="Cách xem giờ trong ngày" view={view} onChange={setView} /> : undefined}
    >
      {total === 0 || !peak ? (
        <EmptyNote icon={Clock3}>Chưa có phiên nào kết thúc trong {windowDays} ngày qua.</EmptyNote>
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
                <HourColumns series={series} total={total} peakHour={peak.hour} />
              ) : (
                <HourTable series={series} />
              )}
            </motion.div>
          </AnimatePresence>
          <p className="mt-4 text-sm leading-6 text-muted-foreground">
            Đông nhất <span className="font-semibold text-foreground">{hourRangeLabel(peak.hour)}</span> với{" "}
            {formatCount(peak.completed)} trên {formatCount(total)} phiên ({percentOf(peak.completed, total)}).
          </p>
        </>
      )}
    </DashboardPanel>
  );
}

function HourColumns({ series, total, peakHour }: { series: LocalHourPoint[]; total: number; peakHour: number }) {
  const max = series.reduce((best, point) => Math.max(best, point.completed), 0);
  const axis = niceCountAxis(max);
  const keys = series.map((point) => String(point.hour));
  const { shownKey, markProps } = useMarkFocus(keys);
  const activeIndex = shownKey === null ? -1 : keys.indexOf(shownKey);
  const active = activeIndex >= 0 ? series[activeIndex] : undefined;

  return (
    <div className="mt-2 grid grid-cols-[2rem_minmax(0,1fr)] gap-x-2">
      {/* Trục tung: vạch tròn số, lưới mảnh lùi về sau, đường đáy đậm hơn một bậc. */}
      <div aria-hidden="true" className={cn("relative", PLOT_HEIGHT_CLASS)}>
        {axis.ticks.map((tick) => (
          <span
            key={tick}
            style={{ bottom: `${(tick / axis.top) * 100}%` }}
            className="absolute right-0 translate-y-1/2 text-sm leading-none tabular-nums text-muted-foreground"
          >
            {formatCount(tick)}
          </span>
        ))}
      </div>

      <div className={cn("relative", PLOT_HEIGHT_CLASS)}>
        {axis.ticks.map((tick) => (
          <span
            key={tick}
            aria-hidden="true"
            style={{ bottom: `${(tick / axis.top) * 100}%` }}
            className={cn(
              "absolute inset-x-0 h-px",
              tick === 0 ? "bg-[var(--viz-axis)]" : "bg-[var(--viz-grid)]",
            )}
          />
        ))}

        <div
          role="list"
          aria-label={`Số phiên kết thúc theo từng giờ trong ngày, tổng ${total} phiên`}
          className="relative flex h-full items-end gap-0.5"
        >
          {series.map((point, index) => {
            const height = (point.completed / axis.top) * 100;
            return (
              <div
                key={point.hour}
                role="listitem"
                aria-label={`${hourRangeLabel(point.hour)}: ${point.completed} phiên`}
                {...markProps(String(point.hour))}
                className="group relative h-full min-w-0 flex-1 cursor-default rounded-t-[4px] outline-hidden focus-visible:ring-2 focus-visible:ring-brand"
              >
                <span
                  aria-hidden="true"
                  style={
                    {
                      "--col-h": `${height}%`,
                      "--col-delay": `${index * 12}ms`,
                      backgroundColor: "var(--viz-slot-1)",
                    } as CSSProperties
                  }
                  className="col-fill col-reveal absolute inset-y-0 left-1/2 w-full max-w-6 -translate-x-1/2 group-hover:brightness-110 group-focus-visible:brightness-110"
                />
                {point.hour === peakHour ? (
                  <span
                    aria-hidden="true"
                    style={{ bottom: `calc(${height}% + 4px)` }}
                    className="absolute inset-x-0 text-center text-sm font-bold leading-none text-foreground"
                  >
                    {formatCount(point.completed)}
                  </span>
                ) : null}
              </div>
            );
          })}
        </div>

        <AnimatePresence>
          {active ? (
            <MarkTooltip key={active.hour} anchor={((activeIndex + 0.5) / series.length) * 100}>
              <TooltipBody
                value={`${formatCount(active.completed)} phiên`}
                label={hourRangeLabel(active.hour)}
                detail={`${percentOf(active.completed, total)} trên ${formatCount(total)} phiên`}
              />
            </MarkTooltip>
          ) : null}
        </AnimatePresence>
      </div>

      <span aria-hidden="true" />
      <div aria-hidden="true" className="mt-2 flex gap-0.5">
        {series.map((point) => (
          <span key={point.hour} className="min-w-0 flex-1 text-center text-sm leading-6 tabular-nums text-muted-foreground">
            {point.hour % TICK_EVERY_HOURS === 0 ? `${point.hour}h` : ""}
          </span>
        ))}
      </div>
    </div>
  );
}

function HourTable({ series }: { series: LocalHourPoint[] }) {
  return (
    <div className="max-h-80 overflow-y-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Số phiên kết thúc theo từng giờ trong ngày</caption>
        <thead className="sticky top-0 bg-card">
          <tr className="border-b border-border">
            <th scope="col" className="py-2 pr-4 font-semibold text-muted-foreground">
              Khung giờ
            </th>
            <th scope="col" className="py-2 pl-4 text-right font-semibold text-muted-foreground">
              Phiên kết thúc
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {series.map((point) => (
            <tr key={point.hour}>
              <th scope="row" className="py-2 pr-4 font-medium tabular-nums text-foreground">
                {hourRangeLabel(point.hour)}
              </th>
              <td className="py-2 pl-4 text-right font-semibold tabular-nums text-foreground">
                {formatCount(point.completed)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
