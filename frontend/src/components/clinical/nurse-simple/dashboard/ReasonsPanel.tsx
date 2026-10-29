"use client";

import { AnimatePresence } from "framer-motion";
import { NotebookPen } from "lucide-react";

import type { SimpleReasonCountDTO } from "@/types/simple-nurse";

import { AnimatedNumber } from "./AnimatedNumber";
import { formatCount, percentOf, reasonLabel, shareOf, sumCounts } from "./dashboard-model";
import {
  barDelayMs,
  DashboardPanel,
  EmptyNote,
  MarkTooltip,
  SeriesSwatch,
  TooltipBody,
  useMarkFocus,
} from "./primitives";

/** Một chuỗi duy nhất thì một màu duy nhất: ô màu thứ nhất của bảng biểu đồ. */
const BAR_COLOR = "var(--viz-slot-1)";

/**
 * Lý do điều dưỡng chọn khi chốt ca, đúng chữ của biểu mẫu quyết định. Backend
 * đã sắp từ nhiều tới ít. Độ dài so theo lý do nhiều nhất; số đếm ở đầu vạch.
 */
export function ReasonsPanel({ reasons, order }: { reasons: SimpleReasonCountDTO[]; order: number }) {
  const total = sumCounts(reasons);
  const max = reasons.reduce((peak, reason) => Math.max(peak, reason.count), 0);
  const { shownKey, markProps } = useMarkFocus(reasons.map((reason) => reason.code));

  return (
    <DashboardPanel
      id="decision-reasons"
      order={order}
      title="Lý do điều dưỡng ghi lại"
      subtitle={
        total > 0
          ? `Đúng lựa chọn trong biểu mẫu quyết định, trên ${formatCount(total)} ca đã chốt có ghi lý do`
          : "Đúng lựa chọn trong biểu mẫu quyết định"
      }
    >
      {reasons.length === 0 ? (
        <EmptyNote icon={NotebookPen}>Chưa có ca nào được chốt nên chưa ghi nhận lý do nào.</EmptyNote>
      ) : (
        <ul role="list" aria-label="Số ca theo lý do chốt" className="flex flex-col gap-2">
          {reasons.map((reason, index) => {
            const label = reasonLabel(reason.code);
            const share = shareOf(reason.count, max);
            const pct = percentOf(reason.count, total);
            return (
              <li
                key={reason.code}
                aria-label={`${label}: ${reason.count} ca, ${pct} trên ${total} ca có ghi lý do`}
                {...markProps(reason.code)}
                className="cursor-default rounded-xl px-2 py-2 outline-hidden transition-colors duration-200 hover:bg-muted/70 focus-visible:bg-muted/70 focus-visible:ring-2 focus-visible:ring-brand"
              >
                <span className="block text-sm font-medium leading-6 text-foreground">{label}</span>
                <span className="relative mt-2 flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    style={{
                      width: `calc((100% - 3rem) * ${share})`,
                      backgroundColor: BAR_COLOR,
                      animationDelay: `${barDelayMs(index)}ms`,
                    }}
                    className="bar-grow h-2 min-w-2 rounded-r-[4px] transition-[width] duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none"
                  />
                  <AnimatedNumber value={reason.count} className="text-base font-bold leading-6 text-foreground" />
                  <AnimatePresence>
                    {shownKey === reason.code ? (
                      <MarkTooltip anchor={share * 80}>
                        <TooltipBody
                          value={`${formatCount(reason.count)} ca`}
                          label={label}
                          detail={`${pct} trên ${total} ca có ghi lý do`}
                          swatch={<SeriesSwatch color={BAR_COLOR} />}
                        />
                      </MarkTooltip>
                    ) : null}
                  </AnimatePresence>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </DashboardPanel>
  );
}
