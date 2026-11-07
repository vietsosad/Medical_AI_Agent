"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/utils";
import type { SimpleHourPointDTO } from "@/types/simple-nurse";

import { AnimatedNumber } from "./AnimatedNumber";
import { formatCount, hourRangeLabel, parseSnapshot } from "./dashboard-model";
import { cardRiseVariants, MarkTooltip, TooltipBody, useMarkFocus } from "./primitives";

export type KpiTone = "neutral" | "critical";

export interface KpiTrend {
  points: SimpleHourPointDTO[];
  series: "completed" | "decided";
  /** Đơn vị đọc trong chú thích nổi: "phiên" hoặc "ca". */
  unit: string;
}

/**
 * Ô chỉ số: một con số hiện tại thì đọc bằng chữ số. `critical` chỉ đổi viền
 * và biểu tượng sang đỏ khi con số lớn hơn 0 -- nền thẻ không bao giờ thành một
 * khối đỏ, và nghĩa luôn nằm ở nhãn chữ, không ở màu.
 *
 * `trend` vẽ thêm 24 cột nhỏ của dải 24 giờ qua. Con số của ô là tổng của
 * chính các cột này, nên đường xu hướng không bao giờ kể một câu chuyện khác.
 */
export function KpiTile({
  id,
  label,
  value,
  hint,
  icon: Icon,
  tone = "neutral",
  trend,
  order,
}: {
  id: string;
  label: string;
  value: number;
  hint: ReactNode;
  icon: LucideIcon;
  tone?: KpiTone;
  trend?: KpiTrend;
  order: number;
}) {
  const labelId = `${id}-label`;
  const critical = tone === "critical" && value > 0;
  return (
    <motion.section
      aria-labelledby={labelId}
      custom={order}
      variants={cardRiseVariants}
      initial="hidden"
      animate="visible"
      className={cn(
        "flex min-w-0 flex-col rounded-2xl border bg-card p-4 shadow-xs transition-colors duration-300 sm:p-6",
        critical ? "border-rose-300 dark:border-rose-800" : "border-border",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <h3 id={labelId} className="text-sm font-semibold leading-6 text-muted-foreground">
          {label}
        </h3>
        <span
          className={cn(
            "flex size-8 shrink-0 items-center justify-center rounded-xl transition-colors duration-300",
            critical
              ? "bg-rose-100 text-rose-700 dark:bg-rose-950/70 dark:text-rose-300"
              : "bg-brand-soft text-brand-ink",
          )}
        >
          <Icon className="size-4" aria-hidden="true" />
        </span>
      </div>
      <p className="mt-2 text-4xl font-extrabold leading-none tracking-tight text-foreground">
        <AnimatedNumber value={value} flashClassName={critical ? "bg-rose-200/70 dark:bg-rose-900/50" : undefined} />
      </p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{hint}</p>
      {trend ? <HourSparkline id={id} trend={trend} /> : null}
    </motion.section>
  );
}

/** "2026-11-03T08:00:00" (UTC) -> giờ trên máy người xem. */
function localHour(hourStart: string): number | null {
  const parsed = parseSnapshot(hourStart);
  return parsed ? parsed.getHours() : null;
}

/**
 * 24 cột mảnh của dải 24 giờ qua: xám lùi, giờ đang chạy mang màu nhấn. Một
 * điểm dừng Tab, mũi tên đi qua từng giờ, chú thích nổi ghi khung giờ và số.
 * Cột mọc từ đáy lần lượt từ trái sang phải khi ô hiện lần đầu.
 */
function HourSparkline({ id, trend }: { id: string; trend: KpiTrend }) {
  const { points, series, unit } = trend;
  const max = points.reduce((peak, point) => Math.max(peak, point[series]), 0);
  const keys = points.map((point) => point.hour_start);
  const { shownKey, markProps } = useMarkFocus(keys);
  const activeIndex = shownKey === null ? -1 : keys.indexOf(shownKey);
  const active = activeIndex >= 0 ? points[activeIndex] : undefined;
  const activeHour = active ? localHour(active.hour_start) : null;

  return (
    <div className="relative mt-4 h-8">
      {/* Đường đáy liền một nét: giờ bằng 0 không vẽ gì riêng, nên dải toàn 0
          không thành một hàng gạch trông như đường kẻ đứt. */}
      <span aria-hidden="true" className="absolute inset-x-0 bottom-0 h-px bg-[var(--viz-axis)]" />
      {max === 0 ? (
        <span className="sr-only">Không có {unit} nào trong 24 giờ qua.</span>
      ) : (
        <div role="list" aria-label="Theo từng giờ trong 24 giờ qua" className="relative flex h-full items-end gap-0.5">
          {points.map((point, index) => {
            const value = point[series];
            const hour = localHour(point.hour_start);
            const isCurrent = index === points.length - 1;
            const share = value / max;
            const name = hour === null ? point.hour_start : hourRangeLabel(hour);
            return (
              <div
                key={point.hour_start}
                role="listitem"
                aria-label={`${name}${isCurrent ? " (giờ đang chạy)" : ""}: ${value} ${unit}`}
                {...markProps(point.hour_start)}
                className="relative h-full min-w-0 flex-1 cursor-default rounded-[2px] outline-hidden focus-visible:ring-2 focus-visible:ring-brand"
              >
                {value > 0 ? (
                  <span
                    aria-hidden="true"
                    style={
                      {
                        "--col-h": `${Math.max(share * 100, 12)}%`,
                        "--col-delay": `${120 + index * 12}ms`,
                        backgroundColor: isCurrent ? "var(--viz-slot-1)" : "var(--viz-spark)",
                      } as CSSProperties
                    }
                    className="col-fill col-reveal absolute inset-0"
                  />
                ) : null}
              </div>
            );
          })}
        </div>
      )}
      <AnimatePresence>
        {active ? (
          <MarkTooltip key={`${id}-${active.hour_start}`} anchor={((activeIndex + 0.5) / points.length) * 100}>
            <TooltipBody
              value={`${formatCount(active[series])} ${unit}`}
              label={activeHour === null ? active.hour_start : hourRangeLabel(activeHour)}
              detail={activeIndex === points.length - 1 ? "Giờ đang chạy, tính đến lúc cập nhật" : undefined}
            />
          </MarkTooltip>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
