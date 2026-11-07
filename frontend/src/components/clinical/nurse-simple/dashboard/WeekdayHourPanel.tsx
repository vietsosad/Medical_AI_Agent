"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CalendarClock, Grid3x3 } from "lucide-react";
import { useState, type CSSProperties } from "react";

import { DURATION, EASE_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { SimpleWeekdayHourDTO } from "@/types/simple-nurse";

import {
  describeWeekdayDays,
  formatCount,
  formatDay,
  heatStep,
  hourRangeLabel,
  percentOf,
  weekdayHourPeak,
  weekdayLabel,
} from "./dashboard-model";
import {
  type ChartView,
  DashboardPanel,
  EmptyNote,
  HeatScaleLegend,
  MarkTooltip,
  TooltipBody,
  useMarkFocus,
  ViewSwitch,
} from "./primitives";

const HOURS = Array.from({ length: 24 }, (_, hour) => hour);
/** Nhãn trục giờ cách nhau 3 giờ, như biểu đồ giờ trong ngày. */
const LABEL_EVERY_HOURS = 3;
const CELL_STEP_MS = 20;

type CellKey = `${number}:${number}`;

function cellKey(weekday: number, hour: number): CellKey {
  return `${weekday}:${hour}`;
}

/**
 * Phiên kết thúc theo thứ × giờ, GIỜ VIỆT NAM: trả lời "kíp trực đông vào thứ
 * nào, giờ nào" để xếp người trực.
 *
 * Backend đã đổi giờ UTC sang giờ Việt Nam và chia cửa sổ theo lịch Việt Nam
 * (`weekday_hour` trong `simple_nurse_dashboard.py`), nên màn chỉ hiển thị,
 * không tự đổi múi giờ, không đọc mốc giờ nào bằng `new Date`.
 *
 * Thang một sắc của ma trận chờ (đã kiểm định); ô có phiên in số, ô trống để
 * trống -- 168 số 0 chỉ là nhiễu. Mỗi hàng có tổng ở cuối; cửa sổ không chia
 * đều cho 7 thì màn nói rõ thứ nào có thêm một ngày.
 */
export function WeekdayHourPanel({
  panel,
  windowDays,
  order,
}: {
  panel: SimpleWeekdayHourDTO;
  windowDays: number;
  order: number;
}) {
  const [view, setView] = useState<ChartView>("chart");
  const peak = weekdayHourPeak(panel);
  const range = `${formatDay(panel.first_day)} – ${formatDay(panel.last_day)}`;

  return (
    <DashboardPanel
      id="weekday-hour"
      order={order}
      title="Phiên kết thúc theo thứ và giờ"
      subtitle={`${formatCount(panel.total)} phiên trong ${windowDays} ngày theo lịch Việt Nam (${range}), giờ Việt Nam.`}
      action={
        panel.total > 0 ? (
          <ViewSwitch
            id="weekday-hour-view"
            label="Cách xem phiên theo thứ và giờ"
            view={view}
            onChange={setView}
            chartIcon={Grid3x3}
          />
        ) : undefined
      }
    >
      {panel.total === 0 || peak === null ? (
        <EmptyNote icon={CalendarClock}>
          Chưa có phiên nào kết thúc trong {windowDays} ngày qua theo lịch Việt Nam.
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
              {view === "chart" ? <HeatGrid panel={panel} /> : <HeatTable panel={panel} />}
            </motion.div>
          </AnimatePresence>
          <p className="mt-4 text-sm leading-6 text-muted-foreground">
            Đông nhất{" "}
            <span className="font-semibold text-foreground">
              {weekdayLabel(peak.weekday)}, {hourRangeLabel(peak.hour)}
            </span>{" "}
            với {formatCount(peak.count)} trên {formatCount(panel.total)} phiên ({percentOf(peak.count, panel.total)})
            {peak.ties > 0 ? `; ${formatCount(peak.ties)} khung giờ khác cũng có ${formatCount(peak.count)} phiên` : ""}
            .
          </p>
          <div className="mt-4 flex flex-wrap items-end justify-between gap-4 border-t border-border pt-4">
            <p className="max-w-xl text-sm leading-6 text-muted-foreground">
              {describeWeekdayDays(panel)} Ngày cuối ({formatDay(panel.last_day)}) chỉ tính đến lúc cập nhật. Ngày tính
              từ 0:00 đến 24:00 giờ Việt Nam, nên tổng có thể lệch vài phiên so với các biểu đồ chia ngày theo UTC ở
              trên.
            </p>
            <HeatScaleLegend max={peak.count} unit="phiên" />
          </div>
        </>
      )}
    </DashboardPanel>
  );
}

function HeatGrid({ panel }: { panel: SimpleWeekdayHourDTO }) {
  const peak = panel.rows.reduce((best, row) => Math.max(best, ...row.hours), 0);
  const keys = panel.rows.flatMap((row) => HOURS.map((hour) => cellKey(row.weekday, hour)));
  const { shownKey, markProps } = useMarkFocus(keys, { columns: HOURS.length });

  return (
    <div className="-mx-2 overflow-x-auto px-2 pt-2">
      <table role="grid" className="w-full min-w-[44rem] table-fixed border-separate border-spacing-0.5 text-sm">
        <caption className="sr-only">
          Số phiên kết thúc theo thứ (hàng) và giờ Việt Nam (cột). Dùng phím mũi tên để đi qua từng ô.
        </caption>
        <colgroup>
          <col className="w-[5.5rem]" />
          {HOURS.map((hour) => (
            <col key={hour} />
          ))}
          <col className="w-[3.5rem]" />
        </colgroup>
        <thead>
          <tr>
            <th scope="col" className="pb-2 pr-2 text-left align-bottom font-semibold text-muted-foreground">
              Thứ
            </th>
            {HOURS.map((hour) => (
              <th
                key={hour}
                scope="col"
                className="pb-2 text-center align-bottom font-normal tabular-nums text-muted-foreground"
              >
                <span aria-hidden="true">{hour % LABEL_EVERY_HOURS === 0 ? `${hour}h` : ""}</span>
                <span className="sr-only">{hourRangeLabel(hour)}</span>
              </th>
            ))}
            <th scope="col" className="pb-2 pl-2 text-left align-bottom font-semibold text-muted-foreground">
              Tổng
            </th>
          </tr>
        </thead>
        <tbody>
          {panel.rows.map((row, rowIndex) => {
            const name = weekdayLabel(row.weekday);
            const rowTotal = row.hours.reduce((sum, count) => sum + count, 0);
            return (
              <tr key={row.weekday}>
                <th scope="row" className="pr-2 text-left align-middle font-semibold text-foreground">
                  {name}
                </th>
                {row.hours.map((count, hour) => {
                  const key = cellKey(row.weekday, hour);
                  const step = heatStep(count, peak);
                  const style = {
                    ...(step > 0
                      ? { backgroundColor: `var(--viz-heat-${step})`, color: `var(--viz-heat-ink-${step})` }
                      : {}),
                    "--cell-delay": `${(rowIndex * 2 + Math.floor(hour / LABEL_EVERY_HOURS)) * CELL_STEP_MS}ms`,
                  } as CSSProperties;
                  return (
                    <td
                      key={hour}
                      role="gridcell"
                      aria-label={`${name}, ${hourRangeLabel(hour)}: ${count} phiên`}
                      {...markProps(key)}
                      className="group relative cursor-default rounded-md p-0 outline-hidden focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card"
                    >
                      <div
                        style={style}
                        className={cn(
                          "heat-in flex h-11 items-center justify-center rounded-md text-sm font-semibold tabular-nums",
                          "transition-[background-color,color,filter] duration-300 group-hover:brightness-95 dark:group-hover:brightness-110 motion-reduce:transition-none",
                          step === 0 && "bg-muted/70",
                        )}
                      >
                        {count > 0 ? formatCount(count) : null}
                      </div>
                      <AnimatePresence>
                        {shownKey === key ? (
                          <MarkTooltip anchor={((hour + 0.5) / HOURS.length) * 100}>
                            <TooltipBody
                              value={`${formatCount(count)} phiên`}
                              label={`${name}, ${hourRangeLabel(hour)}`}
                              detail={`${percentOf(count, panel.total)} trên ${formatCount(panel.total)} phiên · ${row.days} ngày ${name.toLowerCase()} trong khoảng này`}
                            />
                          </MarkTooltip>
                        ) : null}
                      </AnimatePresence>
                    </td>
                  );
                })}
                <td className="pl-2 align-middle text-base font-bold tabular-nums text-foreground">
                  {formatCount(rowTotal)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Bản bảng: chỉ các khung giờ có phiên, đọc theo dòng. */
function HeatTable({ panel }: { panel: SimpleWeekdayHourDTO }) {
  const entries = panel.rows.flatMap((row) =>
    row.hours.flatMap((count, hour) => (count > 0 ? [{ weekday: row.weekday, hour, count, days: row.days }] : [])),
  );
  return (
    <div className="max-h-80 overflow-y-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">
          Các khung giờ có phiên kết thúc, theo giờ Việt Nam; khung giờ không có trong bảng là 0 phiên.
        </caption>
        <thead className="sticky top-0 bg-card">
          <tr className="border-b border-border">
            <th scope="col" className="py-2 pr-4 font-semibold text-muted-foreground">
              Thứ
            </th>
            <th scope="col" className="px-4 py-2 font-semibold text-muted-foreground">
              Khung giờ
            </th>
            <th scope="col" className="py-2 pl-4 text-right font-semibold text-muted-foreground">
              Phiên kết thúc
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {entries.map((entry) => (
            <tr key={cellKey(entry.weekday, entry.hour)}>
              <th scope="row" className="py-2 pr-4 font-medium text-foreground">
                {weekdayLabel(entry.weekday)}
                <span className="block font-normal text-muted-foreground">{entry.days} ngày trong khoảng này</span>
              </th>
              <td className="px-4 py-2 tabular-nums text-foreground">{hourRangeLabel(entry.hour)}</td>
              <td className="py-2 pl-4 text-right font-semibold tabular-nums text-foreground">
                {formatCount(entry.count)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
