"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChartLine, Table2, TrendingUp, type LucideIcon } from "lucide-react";
import { useMemo, useState } from "react";
import {
  CartesianGrid,
  DefaultZIndexes,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ZIndexLayer,
  useCartesianScale,
} from "recharts";

import { DURATION, EASE_IN_OUT, EASE_OUT, layoutTransition } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { SimpleDailyPointDTO } from "@/types/simple-nurse";

import { formatCount, formatDay, niceCountAxis } from "./dashboard-model";
import { DashboardPanel, EmptyNote, SeriesSwatch } from "./primitives";

type SeriesKey = "completed" | "decided";
type VolumeView = "chart" | "table";

/** Hai chuỗi cùng đơn vị "số ca" nên nằm chung MỘT trục tung -- không bao giờ hai trục. */
const SERIES: ReadonlyArray<{ key: SeriesKey; label: string; color: string }> = [
  { key: "completed", label: "Phiên sàng lọc kết thúc", color: "var(--viz-slot-1)" },
  { key: "decided", label: "Ca được điều dưỡng chốt", color: "var(--viz-slot-2)" },
];

/** Chiều cao gồm cả dải nhãn trục hoành, để thẻ không bao giờ có thanh cuộn lồng. */
const CHART_HEIGHT = 256;
/** Đường vẽ ra sau khi thẻ đã nổi lên, theo nhịp "biểu đồ mọc lên" (700 ms). */
const DRAW_BEGIN_MS = 200;
const DRAW_MS = DURATION.slow * 1000;
/** = EASE_IN_OUT, viết dạng chuỗi mà Recharts nhận. */
const DRAW_EASING = "cubic-bezier(0.65,0,0.35,1)" as const;
/** Hai nhãn cuối đường gần nhau hơn mức này thì bỏ nhãn, dựa vào chú giải + chú thích nổi. */
const END_LABEL_MIN_GAP_PX = 18;

/**
 * Khối lượng theo ngày trong cửa sổ backend trả về (hiện là 14 ngày): phiên
 * sàng lọc kết thúc và ca được điều dưỡng chốt. Có bản bảng số liệu tương
 * đương cho người không đọc được biểu đồ.
 */
export function VolumePanel({ points, order }: { points: SimpleDailyPointDTO[]; order: number }) {
  const [view, setView] = useState<VolumeView>("chart");
  const days = points.length;
  const totalCompleted = points.reduce((sum, point) => sum + point.completed, 0);
  const totalDecided = points.reduce((sum, point) => sum + point.decided, 0);
  const max = points.reduce((peak, point) => Math.max(peak, point.completed, point.decided), 0);
  const first = points[0]?.date;
  const last = points[points.length - 1]?.date;
  const range = first && last ? `${formatDay(first)} – ${formatDay(last)}` : "";

  return (
    <DashboardPanel
      id="daily-volume"
      order={order}
      title={`Khối lượng ${days} ngày gần nhất`}
      subtitle={`${range ? `${range} · ` : ""}${formatCount(totalCompleted)} phiên sàng lọc kết thúc, ${formatCount(totalDecided)} ca được chốt`}
      action={max > 0 ? <ViewSwitch view={view} onChange={setView} /> : undefined}
    >
      {max === 0 ? (
        <EmptyNote icon={TrendingUp}>Chưa có phiên nào kết thúc trong {days} ngày qua.</EmptyNote>
      ) : (
        <>
          <AnimatePresence mode="wait" initial={false}>
            {view === "chart" ? (
              <motion.div
                key="chart"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: DURATION.quick, ease: EASE_OUT }}
              >
                <ul role="list" aria-label="Chú giải" className="flex flex-wrap gap-x-6 gap-y-2">
                  {SERIES.map((series) => (
                    <li key={series.key} className="flex items-center gap-2 text-sm leading-6 text-foreground">
                      <SeriesSwatch shape="line" color={series.color} />
                      {series.label}
                    </li>
                  ))}
                </ul>
                <VolumeChart points={points} max={max} range={range} />
              </motion.div>
            ) : (
              <motion.div
                key="table"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: DURATION.quick, ease: EASE_OUT }}
              >
                <VolumeTable points={points} />
              </motion.div>
            )}
          </AnimatePresence>
          <p className="mt-4 text-sm leading-6 text-muted-foreground">
            Mỗi ngày tính theo giờ UTC, tức từ 7:00 sáng hôm đó đến 7:00 sáng hôm sau theo giờ Việt Nam. Ngày cuối
            chưa kết thúc nên số của nó chỉ tính đến lúc cập nhật.
          </p>
        </>
      )}
    </DashboardPanel>
  );
}

/** Biểu đồ / Bảng số liệu: nền nổi trượt sang nút được chọn (layoutId chung). */
function ViewSwitch({ view, onChange }: { view: VolumeView; onChange: (next: VolumeView) => void }) {
  const options: ReadonlyArray<{ value: VolumeView; label: string; icon: LucideIcon }> = [
    { value: "chart", label: "Biểu đồ", icon: ChartLine },
    { value: "table", label: "Bảng số liệu", icon: Table2 },
  ];
  return (
    <div role="group" aria-label="Cách xem khối lượng" className="inline-flex rounded-xl bg-muted p-0.5">
      {options.map((option) => {
        const selected = view === option.value;
        const Icon = option.icon;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(option.value)}
            className={cn(
              "relative inline-flex min-h-11 items-center gap-2 rounded-xl px-4 text-sm font-semibold outline-hidden transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-brand",
              selected ? "text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {selected ? (
              <motion.span
                layoutId="volume-view-highlight"
                transition={layoutTransition}
                aria-hidden="true"
                className="absolute inset-0 rounded-xl bg-card shadow-xs"
              />
            ) : null}
            <Icon className="relative size-4" aria-hidden="true" />
            <span className="relative">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}

function VolumeChart({ points, max, range }: { points: SimpleDailyPointDTO[]; max: number; range: string }) {
  const reduceMotion = useReducedMotion() ?? false;
  const axis = niceCountAxis(max);
  const lastPoint = points[points.length - 1];
  const rowsByDate = useMemo(() => new Map(points.map((point) => [point.date, point])), [points]);
  // Chừa đủ chỗ bên phải cho nhãn số ở cuối mỗi đường.
  const endDigits = Math.max(formatCount(lastPoint.completed).length, formatCount(lastPoint.decided).length);
  const rightMargin = 24 + endDigits * 9;

  return (
    <div
      className={cn(
        "mt-4 w-full",
        "[&_.recharts-cartesian-axis-tick-value]:tabular-nums",
        "[&_.recharts-surface:focus-visible]:outline-2 [&_.recharts-surface:focus-visible]:outline-offset-4 [&_.recharts-surface:focus-visible]:outline-brand",
      )}
    >
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <LineChart
          data={points}
          margin={{ top: 16, right: rightMargin, bottom: 0, left: 0 }}
          title={`Biểu đồ đường số phiên sàng lọc kết thúc và số ca được điều dưỡng chốt theo ngày, ${range}`}
          desc={`Ngày ${formatDay(lastPoint.date)}, tính đến lúc cập nhật: ${lastPoint.completed} phiên kết thúc, ${lastPoint.decided} ca được chốt. Dùng phím mũi tên trái, phải để xem từng ngày, hoặc chọn Bảng số liệu để đọc toàn bộ.`}
        >
          <CartesianGrid vertical={false} stroke="var(--viz-grid)" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDay}
            tickLine={false}
            axisLine={{ stroke: "var(--viz-axis)" }}
            tick={{ fill: "var(--muted-foreground)", fontSize: 14 }}
            tickMargin={8}
            interval="preserveStartEnd"
            minTickGap={16}
            padding={{ left: 8, right: 8 }}
            height={32}
          />
          <YAxis
            allowDecimals={false}
            domain={[0, axis.top]}
            ticks={axis.ticks}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "var(--muted-foreground)", fontSize: 14 }}
            tickMargin={8}
            width={40}
          />
          <Tooltip
            cursor={{ stroke: "var(--viz-axis)", strokeWidth: 1 }}
            isAnimationActive={!reduceMotion}
            animationDuration={DURATION.quick * 1000}
            wrapperStyle={{ outline: "none", zIndex: 30 }}
            content={({ active, label, accessibilityLayer }) => (
              <VolumeTooltipCard
                active={active}
                row={typeof label === "string" ? rowsByDate.get(label) : undefined}
                isOngoingDay={label === lastPoint.date}
                announce={accessibilityLayer}
              />
            )}
          />
          {SERIES.map((series) => (
            <Line
              key={series.key}
              dataKey={series.key}
              name={series.label}
              type="linear"
              stroke={series.color}
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              dot={false}
              activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--card)", fill: series.color }}
              isAnimationActive={!reduceMotion}
              animationBegin={DRAW_BEGIN_MS}
              animationDuration={DRAW_MS}
              animationEasing={DRAW_EASING}
            />
          ))}
          <EndMarkers point={lastPoint} reduceMotion={reduceMotion} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Chấm cuối mỗi đường (10px, viền 2px màu nền thẻ) kèm số của ngày gần nhất.
 * Bật lên sau khi đường vẽ xong; các lần làm mới sau đó chấm trượt theo đường
 * cùng nhịp, không bật lại. Hai nhãn sát nhau thì bỏ nhãn thay vì chồng lên.
 */
function EndMarkers({ point, reduceMotion }: { point: SimpleDailyPointDTO; reduceMotion: boolean }) {
  const completed = useCartesianScale({ x: point.date, y: point.completed });
  const decided = useCartesianScale({ x: point.date, y: point.decided });
  if (!completed || !decided) return null;

  const labelsFit = Math.abs(completed.y - decided.y) >= END_LABEL_MIN_GAP_PX;
  const marks = [
    { key: "completed", at: completed, value: point.completed, color: "var(--viz-slot-1)" },
    { key: "decided", at: decided, value: point.decided, color: "var(--viz-slot-2)" },
  ];

  return (
    <ZIndexLayer zIndex={DefaultZIndexes.scatter}>
      <g aria-hidden="true" pointerEvents="none">
        {marks.map((mark) => (
          <motion.g
            key={mark.key}
            initial={false}
            animate={{ x: mark.at.x, y: mark.at.y }}
            transition={
              reduceMotion
                ? { duration: 0 }
                : { delay: DRAW_BEGIN_MS / 1000, duration: DURATION.slow, ease: EASE_IN_OUT }
            }
          >
            <motion.circle
              cx={0}
              cy={0}
              fill={mark.color}
              stroke="var(--card)"
              strokeWidth={2}
              initial={reduceMotion ? false : { r: 0 }}
              animate={{ r: 5 }}
              transition={{ delay: (DRAW_BEGIN_MS + DRAW_MS) / 1000, duration: DURATION.base, ease: EASE_OUT }}
            />
            {labelsFit ? (
              <motion.text
                x={12}
                y={0}
                dy="0.35em"
                fill="var(--foreground)"
                fontSize={14}
                fontWeight={700}
                initial={reduceMotion ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: (DRAW_BEGIN_MS + DRAW_MS) / 1000, duration: DURATION.base, ease: EASE_OUT }}
              >
                {formatCount(mark.value)}
              </motion.text>
            ) : null}
          </motion.g>
        ))}
      </g>
    </ZIndexLayer>
  );
}

/**
 * Chú thích nổi theo ngày: một chú thích liệt kê cả hai chuỗi, giá trị đứng
 * trước và đậm, khóa màu là nét ngắn như chính đường. Với lớp trợ năng của
 * Recharts (phím mũi tên), nội dung được đọc lên qua vùng `status`.
 */
function VolumeTooltipCard({
  active,
  row,
  isOngoingDay,
  announce,
}: {
  active: boolean;
  row: SimpleDailyPointDTO | undefined;
  /** Ngày cuối của cửa sổ còn đang chạy: số của nó chưa phải số cả ngày. */
  isOngoingDay: boolean;
  announce: boolean;
}) {
  const visible = active && row !== undefined;
  return (
    <div
      role={announce ? "status" : undefined}
      aria-live={announce ? "polite" : undefined}
      className={cn(
        "min-w-48 rounded-xl border border-border bg-popover px-4 py-2 text-popover-foreground shadow-lg",
        !visible && "hidden",
      )}
    >
      {visible ? (
        <>
          <p className="text-sm leading-6 text-muted-foreground">
            Ngày {formatDay(row.date)}
            {isOngoingDay ? " · tính đến lúc cập nhật" : null}
          </p>
          <ul role="list" className="flex flex-col">
            {SERIES.map((series) => (
              <li key={series.key} className="flex items-center gap-2">
                <SeriesSwatch shape="line" color={series.color} />
                <span className="text-base font-bold leading-6 tabular-nums">{formatCount(row[series.key])}</span>
                <span className="text-sm leading-6 text-muted-foreground">{series.label}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}

/** Bản bảng của biểu đồ: cùng số liệu, đọc được không cần nhìn hình. */
function VolumeTable({ points }: { points: SimpleDailyPointDTO[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">
          Số phiên sàng lọc kết thúc và số ca được điều dưỡng chốt theo từng ngày
        </caption>
        <thead>
          <tr className="border-b border-border">
            <th scope="col" className="py-2 pr-4 font-semibold text-muted-foreground">
              Ngày
            </th>
            {SERIES.map((series) => (
              <th key={series.key} scope="col" className="py-2 pl-4 text-right font-semibold text-muted-foreground">
                <SeriesSwatch shape="line" color={series.color} className="mr-2 align-middle" />
                {series.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {points.map((point, index) => (
            <tr key={point.date}>
              <th scope="row" className="py-2 pr-4 font-medium tabular-nums text-foreground">
                {formatDay(point.date)}
                {index === points.length - 1 ? (
                  <>
                    {" "}
                    <span className="block font-normal text-muted-foreground">tính đến lúc cập nhật</span>
                  </>
                ) : null}
              </th>
              {SERIES.map((series) => (
                <td key={series.key} className="py-2 pl-4 text-right font-semibold tabular-nums text-foreground">
                  {formatCount(point[series.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
