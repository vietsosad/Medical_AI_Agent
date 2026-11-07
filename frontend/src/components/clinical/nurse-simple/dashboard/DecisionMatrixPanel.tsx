"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ClipboardCheck, Grid3x3 } from "lucide-react";
import { useState, type CSSProperties } from "react";

import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { DURATION, EASE_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { SimpleDecisionMatrixDTO, SimpleMatrixRowKey } from "@/types/simple-nurse";

import { AnimatedNumber } from "./AnimatedNumber";
import {
  DECISION_RELATION_LABELS,
  decisionRelation,
  formatCount,
  heatStep,
  matrixRowLabel,
  matrixRowMeta,
  percentOf,
  sumCounts,
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

const FINAL_LEVELS = [1, 2, 3, 4, 5] as const;

/** Các ô hiện dần theo đường chéo từ góc trên-trái, cùng nhịp với ma trận chờ. */
const DIAGONAL_STEP_MS = 40;

type CellKey = `${SimpleMatrixRowKey}:${number}`;

function cellKey(row: SimpleMatrixRowKey, finalEsi: number): CellKey {
  return `${row}:${finalEsi}`;
}

/**
 * Mức AI đề xuất (hàng) × mức điều dưỡng chốt (cột), trên đúng các ca của khối
 * "Điều dưỡng đã làm gì với đề xuất của AI" -- khối này là bản chi tiết theo
 * từng mức của khối đó, không phải độ chính xác của AI.
 *
 * Mỗi ô IN số ca; màu (thang một sắc của ma trận chờ) chỉ là kênh phụ. Ô trên
 * đường chéo -- điều dưỡng giữ nguyên -- có viền trong. Thang ESI chạy ngược,
 * nên trong mỗi hàng ô bên TRÁI ô có viền là điều dưỡng chốt KHẨN HƠN, ô bên
 * phải là chốt ít khẩn hơn; màn ghi rõ điều đó bằng chữ ngay dưới bảng.
 */
export function DecisionMatrixPanel({
  matrix,
  windowDays,
  order,
}: {
  matrix: SimpleDecisionMatrixDTO;
  windowDays: number;
  order: number;
}) {
  const [view, setView] = useState<ChartView>("chart");
  const total = matrix.decided_total;
  const rows = matrix.rows.filter((row) => row.key !== "IN_PROGRESS" || sumCounts(row.counts) > 0);
  const hasCells = rows.some((row) => sumCounts(row.counts) > 0);

  return (
    <DashboardPanel
      id="decision-matrix"
      order={order}
      title="Điều dưỡng đã làm gì với đề xuất của AI, theo từng mức"
      subtitle={
        <>
          <span>
            Hàng là mức AI đề xuất, cột là mức điều dưỡng chốt, trên {formatCount(total)} ca đã chốt trong {windowDays}{" "}
            ngày qua
          </span>
          <span aria-hidden="true"> · </span>
          <span className="sr-only">. </span>
          <span>không phải độ chính xác của AI</span>
        </>
      }
      action={
        hasCells ? (
          <ViewSwitch
            id="decision-matrix-view"
            label="Cách xem ma trận quyết định"
            view={view}
            onChange={setView}
            chartIcon={Grid3x3}
          />
        ) : undefined
      }
    >
      {total === 0 ? (
        <EmptyNote icon={ClipboardCheck}>
          Chưa có ca nào được chốt trong {windowDays} ngày qua, nên ma trận chưa có ô nào có số. Khi có, mỗi ô là số ca
          theo mức AI đề xuất và mức điều dưỡng chốt.
        </EmptyNote>
      ) : (
        <>
          {hasCells ? (
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={view}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: DURATION.quick, ease: EASE_OUT }}
              >
                {view === "chart" ? (
                  <MatrixGrid matrix={matrix} rows={rows} />
                ) : (
                  <MatrixTable matrix={matrix} rows={rows} />
                )}
              </motion.div>
            </AnimatePresence>
          ) : null}
          <RelationTotals matrix={matrix} />
          <div className="mt-4 flex flex-wrap items-end justify-between gap-4 border-t border-border pt-4">
            <p className="max-w-xl text-sm leading-6 text-muted-foreground">
              Trong mỗi hàng, ô bên trái ô có viền là điều dưỡng chốt mức khẩn hơn AI đề xuất (thang ESI chạy ngược: số
              nhỏ hơn là khẩn hơn), ô bên phải là chốt ít khẩn hơn.
              {matrix.without_final_esi > 0
                ? ` Thêm ${formatCount(matrix.without_final_esi)} ca đã chốt không ghi mức nào nên không nằm trong ô nào.`
                : null}
            </p>
            {hasCells ? <HeatScaleLegend max={maxCell(rows)} unit="ca" /> : null}
          </div>
        </>
      )}
    </DashboardPanel>
  );
}

type MatrixRows = SimpleDecisionMatrixDTO["rows"];

function countAt(row: MatrixRows[number], finalEsi: number): number {
  return row.counts.find((cell) => cell.final_esi === finalEsi)?.count ?? 0;
}

function maxCell(rows: MatrixRows): number {
  return rows.reduce((peak, row) => Math.max(peak, ...row.counts.map((cell) => cell.count)), 0);
}

function cellLabel(rowKey: SimpleMatrixRowKey, finalEsi: number, count: number): string {
  const relation = DECISION_RELATION_LABELS[decisionRelation(rowKey, finalEsi)];
  return `AI đề xuất ${matrixRowLabel(rowKey)}, điều dưỡng chốt ESI ${finalEsi}: ${count} ca. ${relation}`;
}

function MatrixGrid({ matrix, rows }: { matrix: SimpleDecisionMatrixDTO; rows: MatrixRows }) {
  const total = matrix.decided_total;
  const peak = maxCell(rows);
  const keys = rows.flatMap((row) => FINAL_LEVELS.map((level) => cellKey(row.key, level)));
  const { shownKey, markProps } = useMarkFocus(keys, { columns: FINAL_LEVELS.length });

  return (
    <div className="-mx-2 overflow-x-auto px-2 pt-2">
      <table role="grid" className="w-full min-w-[22rem] table-fixed border-separate border-spacing-0.5 text-sm">
        <caption className="sr-only">
          Số ca đã chốt theo mức AI đề xuất (hàng) và mức điều dưỡng chốt (cột). Dùng phím mũi tên để đi qua từng ô.
        </caption>
        <colgroup>
          <col className="w-[27%]" />
          {FINAL_LEVELS.map((level) => (
            <col key={level} />
          ))}
          <col className="w-[12%]" />
        </colgroup>
        <thead>
          <tr>
            <td aria-hidden="true" />
            <th
              scope="colgroup"
              colSpan={FINAL_LEVELS.length}
              className="px-2 pb-2 text-left text-sm font-semibold text-muted-foreground"
            >
              Mức điều dưỡng chốt
            </th>
            <td aria-hidden="true" />
          </tr>
          <tr>
            <th scope="col" className="pb-2 pr-2 text-left align-bottom font-semibold text-muted-foreground">
              Mức AI đề xuất
            </th>
            {FINAL_LEVELS.map((level) => (
              <th key={level} scope="col" className="px-1 pb-2 text-center align-bottom font-semibold text-foreground">
                <span
                  aria-hidden="true"
                  className={cn("mx-auto mb-2 block h-1 w-6 rounded-full", esiTheme(level).rail)}
                />
                ESI {level}
              </th>
            ))}
            <th scope="col" className="pb-2 pl-2 text-left align-bottom font-semibold text-muted-foreground">
              Tổng
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => {
            const meta = matrixRowMeta(row.key);
            const rowTotal = sumCounts(row.counts);
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
                {FINAL_LEVELS.map((level, colIndex) => {
                  const key = cellKey(row.key, level);
                  const count = countAt(row, level);
                  const step = heatStep(count, peak);
                  const kept = decisionRelation(row.key, level) === "kept";
                  const ink = step > 0 ? `var(--viz-heat-ink-${step})` : "var(--muted-foreground)";
                  const style = {
                    ...(step > 0 ? { backgroundColor: `var(--viz-heat-${step})`, color: ink } : {}),
                    // Viền trong cùng màu chữ của ô: luôn đủ tương phản trên nền của chính ô đó.
                    ...(kept ? { boxShadow: `inset 0 0 0 2px ${ink}` } : {}),
                    "--cell-delay": `${(rowIndex + colIndex) * DIAGONAL_STEP_MS}ms`,
                  } as CSSProperties;
                  return (
                    <td
                      key={level}
                      role="gridcell"
                      aria-label={cellLabel(row.key, level, count)}
                      {...markProps(key)}
                      className="group relative cursor-default rounded-lg p-0 outline-hidden focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card"
                    >
                      <div
                        style={style}
                        className={cn(
                          "heat-in flex h-11 items-center justify-center rounded-lg text-base font-bold tabular-nums",
                          "transition-[background-color,color,filter] duration-300 group-hover:brightness-95 dark:group-hover:brightness-110 motion-reduce:transition-none",
                          step === 0 && "bg-muted/70 font-semibold text-muted-foreground",
                        )}
                      >
                        <AnimatedNumber value={count} />
                      </div>
                      <AnimatePresence>
                        {shownKey === key ? (
                          <MarkTooltip anchor={50}>
                            <TooltipBody
                              value={`${formatCount(count)} ca`}
                              label={`AI đề xuất ${matrixRowLabel(row.key)} · điều dưỡng chốt ESI ${level}`}
                              detail={`${DECISION_RELATION_LABELS[decisionRelation(row.key, level)]} · ${percentOf(count, total)} trên ${formatCount(total)} ca đã chốt`}
                            />
                          </MarkTooltip>
                        ) : null}
                      </AnimatePresence>
                    </td>
                  );
                })}
                <td className="pl-2 align-middle">
                  <AnimatedNumber
                    value={rowTotal}
                    className={cn("text-base font-bold", rowTotal === 0 ? "text-muted-foreground" : "text-foreground")}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Tổng theo việc điều dưỡng đã làm. Nhãn kèm vị trí trên bảng ("bên trái ô có
 * viền") để người đọc biết ngay tổng đó đếm những ô nào.
 */
function RelationTotals({ matrix }: { matrix: SimpleDecisionMatrixDTO }) {
  const items = [
    { key: "kept", label: `${DECISION_RELATION_LABELS.kept} (ô có viền)`, value: matrix.kept },
    {
      key: "more_urgent",
      label: `${DECISION_RELATION_LABELS.more_urgent} (bên trái ô có viền)`,
      value: matrix.more_urgent,
    },
    {
      key: "less_urgent",
      label: `${DECISION_RELATION_LABELS.less_urgent} (bên phải ô có viền)`,
      value: matrix.less_urgent,
    },
    ...(matrix.without_proposal > 0
      ? [{ key: "no_proposal", label: DECISION_RELATION_LABELS.no_proposal, value: matrix.without_proposal }]
      : []),
  ];
  return (
    <ul
      role="list"
      aria-label="Tổng theo việc điều dưỡng đã làm"
      className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4"
    >
      {items.map((item) => (
        <li key={item.key} className="min-w-0">
          <span className="flex items-start gap-2 text-sm leading-6 text-muted-foreground">
            {item.key === "kept" ? (
              <span
                aria-hidden="true"
                className="mt-1 size-4 shrink-0 rounded-[4px] bg-muted shadow-[inset_0_0_0_2px_var(--muted-foreground)]"
              />
            ) : null}
            {item.label}
          </span>
          <span className="mt-2 block text-2xl font-extrabold leading-none tracking-tight text-foreground">
            <AnimatedNumber value={item.value} />
          </span>
          <span className="mt-2 block text-sm leading-6 text-muted-foreground">
            {percentOf(item.value, matrix.decided_total)} trên {formatCount(matrix.decided_total)} ca
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Bản bảng: chỉ các cặp mức có ca, kèm việc điều dưỡng đã làm, đọc theo dòng. */
function MatrixTable({ matrix, rows }: { matrix: SimpleDecisionMatrixDTO; rows: MatrixRows }) {
  const entries = rows.flatMap((row) =>
    FINAL_LEVELS.map((level) => ({ row: row.key, level, count: countAt(row, level) })).filter(
      (entry) => entry.count > 0,
    ),
  );
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">
          Các cặp mức AI đề xuất và mức điều dưỡng chốt có ít nhất một ca; cặp không có trong bảng là 0 ca.
        </caption>
        <thead>
          <tr className="border-b border-border">
            <th scope="col" className="py-2 pr-4 font-semibold text-muted-foreground">
              Mức AI đề xuất
            </th>
            <th scope="col" className="px-4 py-2 font-semibold text-muted-foreground">
              Điều dưỡng chốt
            </th>
            <th scope="col" className="px-4 py-2 text-right font-semibold text-muted-foreground">
              Số ca
            </th>
            <th scope="col" className="py-2 pl-4 font-semibold text-muted-foreground">
              Điều dưỡng đã làm gì
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {entries.map((entry) => (
            <tr key={cellKey(entry.row, entry.level)}>
              <th scope="row" className="py-2 pr-4 font-medium text-foreground">
                {matrixRowLabel(entry.row)}
              </th>
              <td className="px-4 py-2 text-foreground">ESI {entry.level}</td>
              <td className="px-4 py-2 text-right font-semibold tabular-nums text-foreground">
                {formatCount(entry.count)}
              </td>
              <td className="py-2 pl-4 text-muted-foreground">
                {DECISION_RELATION_LABELS[decisionRelation(entry.row, entry.level)]}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Tổng {formatCount(matrix.decided_total)} ca đã chốt.
      </p>
    </div>
  );
}
