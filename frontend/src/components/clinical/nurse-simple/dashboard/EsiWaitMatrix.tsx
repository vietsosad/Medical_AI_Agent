"use client";

import { AnimatePresence } from "framer-motion";
import { Inbox } from "lucide-react";
import type { CSSProperties } from "react";

import { cn } from "@/lib/utils";
import type {
  SimpleMatrixRowKey,
  SimpleNurseDashboardDTO,
  SimpleWaitBucketKey,
} from "@/types/simple-nurse";

import { AnimatedNumber } from "./AnimatedNumber";
import {
  formatCount,
  HEAT_STEPS,
  heatStep,
  matrixRowLabel,
  matrixRowMeta,
  orderedWaitBuckets,
  percentOf,
  shareOf,
  sumCounts,
  WAIT_BUCKET_META,
} from "./dashboard-model";
import { barDelayMs, DashboardPanel, EmptyNote, MarkTooltip, TooltipBody, useMarkFocus } from "./primitives";

const WAIT_KEYS: readonly SimpleWaitBucketKey[] = ["UNDER_WARNING", "WARNING", "CRITICAL"];

/**
 * Sắc của biểu tượng mốc chờ trên nền thẻ sáng/tối. Bảng màu trong
 * `WAIT_BUCKET_META.iconTone` được chọn cho nền tối của ô chính nên quá nhạt ở
 * đây. Biểu tượng luôn đi kèm nhãn chữ của mốc.
 */
const WAIT_ICON_INK: Record<SimpleWaitBucketKey, string> = {
  UNDER_WARNING: "text-emerald-600 dark:text-emerald-400",
  WARNING: "text-amber-600 dark:text-amber-400",
  CRITICAL: "text-rose-600 dark:text-rose-400",
};

/** Các ô hiện dần theo đường chéo từ góc trên-trái; mỗi đường chéo trễ hơn ngần này. */
const DIAGONAL_STEP_MS = 40;

type CellKey = `${SimpleMatrixRowKey}:${SimpleWaitBucketKey}`;

function cellKey(row: SimpleMatrixRowKey, wait: SimpleWaitBucketKey): CellKey {
  return `${row}:${wait}`;
}

/**
 * Ma trận mức khẩn × thời gian chờ của các ca đang mở.
 *
 * Hàng là mức AI đề xuất (chưa phải mức điều dưỡng chốt), cột là ba mốc chờ
 * của bảng ca. Mỗi ô IN số ca -- màu chỉ là kênh phụ, đậm dần theo số ca so
 * với ô nhiều nhất -- nên bảng này cũng chính là bản bảng số liệu của nó. Cột
 * cuối là tổng theo hàng, kèm vạch màu ESI như bảng ca.
 *
 * Đọc từ góc trên-phải: ca khẩn nhất đã chờ lâu nhất. Màn không tự đặt thêm
 * một luật "quá hạn" nào: mốc chờ và mức ESI đã là hai thang mà điều dưỡng
 * dùng hằng ngày.
 *
 * Hàng "Đang sàng lọc" chỉ xuất hiện khi có phiên đã bị bộ lọc khẩn cấp gắn cờ
 * mà người bệnh chưa khai xong: chính việc hàng đó hiện ra là một tín hiệu.
 */
export function EsiWaitMatrix({ dashboard, order }: { dashboard: SimpleNurseDashboardDTO; order: number }) {
  const rows = dashboard.esi_wait_matrix
    .filter((row) => row.key !== "IN_PROGRESS" || sumCounts(row.counts) > 0)
    .map((row) => ({ key: row.key, counts: orderedWaitBuckets(row.counts) }));
  const cells = rows.flatMap((row) => row.counts.map((cell) => ({ row: row.key, wait: cell.key, count: cell.count })));
  const total = sumCounts(cells);
  const maxCell = cells.reduce((peak, cell) => Math.max(peak, cell.count), 0);
  const rowTotals = rows.map((row) => sumCounts(row.counts));
  const maxRow = rowTotals.reduce((peak, value) => Math.max(peak, value), 0);
  const showsInProgress = rows.some((row) => row.key === "IN_PROGRESS");

  const { shownKey, markProps } = useMarkFocus(
    cells.map((cell) => cellKey(cell.row, cell.wait)),
    { columns: WAIT_KEYS.length },
  );

  return (
    <DashboardPanel
      id="esi-wait-matrix"
      order={order}
      title="Mức khẩn và thời gian chờ"
      subtitle="Ca đang mở theo mức AI đề xuất (chưa phải mức điều dưỡng chốt) và thời gian đã chờ tiếp nhận."
    >
      {total === 0 ? (
        <EmptyNote icon={Inbox}>
          Không có ca nào đang mở. Ma trận sẽ có số ngay khi có ca mới vào hàng đợi.
        </EmptyNote>
      ) : (
        <>
          <div className="-mx-2 overflow-x-auto px-2 pt-2">
            <table role="grid" className="w-full min-w-[18rem] table-fixed border-separate border-spacing-0.5 text-sm">
              <caption className="sr-only">
                Số ca đang mở theo mức AI đề xuất (hàng) và thời gian chờ tiếp nhận (cột). Dùng phím mũi tên để đi
                qua từng ô.
              </caption>
              <colgroup>
                <col className="w-[27%]" />
                <col />
                <col />
                <col />
                <col className="w-[17%]" />
              </colgroup>
              <thead>
                <tr>
                  <th scope="col" className="pb-2 pr-2 text-left align-bottom text-sm font-semibold text-muted-foreground">
                    Mức AI đề xuất
                  </th>
                  {WAIT_KEYS.map((key) => {
                    const meta = WAIT_BUCKET_META[key];
                    const Icon = meta.icon;
                    return (
                      <th key={key} scope="col" className="px-2 pb-2 text-left align-bottom font-semibold text-muted-foreground">
                        {/* Màn hẹp: biểu tượng đứng trên nhãn để nhãn có trọn bề ngang cột. */}
                        <span className="flex flex-col items-start leading-5 break-words sm:flex-row sm:items-center sm:gap-2">
                          <Icon className={cn("size-4 shrink-0", WAIT_ICON_INK[key])} aria-hidden="true" />
                          <span className="min-w-0">{meta.label}</span>
                        </span>
                      </th>
                    );
                  })}
                  <th scope="col" className="pb-2 pl-2 text-left align-bottom font-semibold text-muted-foreground">
                    Tổng
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, rowIndex) => {
                  const meta = matrixRowMeta(row.key);
                  const rowTotal = rowTotals[rowIndex];
                  return (
                    <tr key={row.key}>
                      <th scope="row" className="pr-2 text-left align-middle font-normal">
                        <span className="flex min-h-11 items-center gap-2">
                          <span aria-hidden="true" className={cn("h-6 w-1 shrink-0 rounded-full", meta.rail)} />
                          <span className="min-w-0 leading-5">
                            <span className="block font-semibold text-foreground">{meta.name}</span>
                            {meta.detail ? (
                              <>
                                <span className="sr-only">, </span>
                                <span className="block text-muted-foreground">{meta.detail}</span>
                              </>
                            ) : null}
                          </span>
                        </span>
                      </th>

                      {row.counts.map((cell, colIndex) => {
                        const key = cellKey(row.key, cell.key);
                        const step = heatStep(cell.count, maxCell);
                        const fill: CSSProperties =
                          step > 0
                            ? { backgroundColor: `var(--viz-heat-${step})`, color: `var(--viz-heat-ink-${step})` }
                            : {};
                        return (
                          <td
                            key={cell.key}
                            role="gridcell"
                            {...markProps(key)}
                            className="group relative cursor-default rounded-lg p-0 outline-hidden focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card"
                          >
                            <div
                              style={{ ...fill, "--cell-delay": `${(rowIndex + colIndex) * DIAGONAL_STEP_MS}ms` } as CSSProperties}
                              className={cn(
                                "heat-in flex h-11 items-center justify-center rounded-lg text-base font-bold tabular-nums",
                                "transition-[background-color,color,filter] duration-300 group-hover:brightness-95 dark:group-hover:brightness-110 motion-reduce:transition-none",
                                step === 0 && "bg-muted/70 font-semibold text-muted-foreground",
                              )}
                            >
                              <AnimatedNumber value={cell.count} />
                            </div>
                            <AnimatePresence>
                              {shownKey === key ? (
                                <MarkTooltip anchor={50}>
                                  <TooltipBody
                                    value={`${formatCount(cell.count)} ca`}
                                    label={`${matrixRowLabel(row.key)} · chờ ${WAIT_BUCKET_META[cell.key].label.toLowerCase()}`}
                                    detail={`${percentOf(cell.count, total)} trên ${formatCount(total)} ca đang mở`}
                                  />
                                </MarkTooltip>
                              ) : null}
                            </AnimatePresence>
                          </td>
                        );
                      })}

                      <td role="gridcell" className="pl-2 align-middle">
                        <span className="flex min-h-11 items-center gap-2">
                          {rowTotal > 0 ? (
                            <span
                              aria-hidden="true"
                              style={{
                                width: `calc((100% - 2.5rem) * ${shareOf(rowTotal, maxRow)})`,
                                animationDelay: `${barDelayMs(rowIndex)}ms`,
                              }}
                              className={cn(
                                "bar-grow h-2 min-w-2 rounded-r-[4px] transition-[width] duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none",
                                meta.rail,
                              )}
                            />
                          ) : (
                            <span aria-hidden="true" className="h-2 w-0.5 shrink-0 rounded-full bg-slate-300 dark:bg-slate-600" />
                          )}
                          <AnimatedNumber
                            value={rowTotal}
                            className={cn("text-base font-bold", rowTotal === 0 ? "text-muted-foreground" : "text-foreground")}
                          />
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-wrap items-end justify-between gap-4 border-t border-border pt-4">
            <p className="max-w-xl text-sm leading-6 text-muted-foreground">
              Trên {formatCount(total)} ca đang mở: ca đang chờ và ca đã có người phụ trách, không tính ca tạm gác.
              {showsInProgress
                ? " Hàng “Đang sàng lọc” là phiên bộ lọc khẩn cấp đã gắn cờ khi người bệnh còn đang khai, nên chưa có mức AI đề xuất."
                : null}
            </p>
            <HeatLegend max={maxCell} />
          </div>
        </>
      )}
    </DashboardPanel>
  );
}

/**
 * Chú giải của thang màu: ghi rõ hai đầu vì thang tương đối (đậm nhất = ô
 * nhiều nhất của chính ma trận này), không phải một ngưỡng cố định.
 */
function HeatLegend({ max }: { max: number }) {
  const steps = max <= 1 ? [HEAT_STEPS] : Array.from({ length: HEAT_STEPS }, (_, index) => index + 1);
  return (
    <div className="flex items-center gap-2 text-sm leading-6 text-muted-foreground">
      <span>Màu ô theo số ca:</span>
      <span className="font-semibold tabular-nums text-foreground">1</span>
      <span aria-hidden="true" className="flex gap-0.5">
        {steps.map((step) => (
          <span
            key={step}
            style={{ backgroundColor: `var(--viz-heat-${step})` }}
            className="h-4 w-6 rounded-[4px] ring-1 ring-inset ring-black/5 dark:ring-white/10"
          />
        ))}
      </span>
      {max > 1 ? <span className="font-semibold tabular-nums text-foreground">{formatCount(max)}</span> : null}
    </div>
  );
}
