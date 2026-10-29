"use client";

import { AnimatePresence } from "framer-motion";
import { ClipboardCheck } from "lucide-react";

import { cn } from "@/lib/utils";
import type { SimpleAgreementDTO } from "@/types/simple-nurse";

import { AnimatedNumber } from "./AnimatedNumber";
import {
  AGREEMENT_SERIES,
  agreementCount,
  comparedTotal,
  formatCount,
  percentOf,
} from "./dashboard-model";
import {
  barDelayMs,
  DashboardPanel,
  EmptyNote,
  MarkTooltip,
  SeriesSwatch,
  TooltipBody,
  useMarkFocus,
} from "./primitives";

/**
 * Điều dưỡng đã làm gì với mức ESI mà AI đề xuất, trên các ca ĐÃ CHỐT.
 *
 * Ràng buộc nội dung quan trọng nhất của màn: đây là quyết định của điều
 * dưỡng, không phải độ chính xác của AI -- hệ thống không có kết luận chuẩn
 * nào để đối chiếu. Mọi tỉ lệ đi kèm mẫu số của nó.
 *
 * Thanh phân cực chỉ gồm các ca có mức AI để so; ca điều dưỡng tự chốt khi AI
 * chưa đề xuất mức không nằm trên thang "khẩn hơn / giữ nguyên / ít khẩn hơn"
 * nên được nêu riêng bên dưới, không chen vào thanh.
 */
export function AgreementPanel({ agreement, order }: { agreement: SimpleAgreementDTO; order: number }) {
  const total = agreement.decided_total;
  const compared = comparedTotal(agreement);
  const without = agreement.adjusted_without_proposal;

  return (
    <DashboardPanel
      id="nurse-agreement"
      order={order}
      title="Điều dưỡng đã làm gì với đề xuất của AI"
      subtitle={
        <>
          <span>Trên {formatCount(total)} ca đã chốt</span>
          <span aria-hidden="true"> · </span>
          <span className="sr-only">. </span>
          <span>không phải độ chính xác của AI</span>
        </>
      }
    >
      {total === 0 ? (
        <EmptyNote icon={ClipboardCheck}>
          Chưa có ca nào được chốt, nên chưa có gì để đối chiếu. Khi có, khối này chỉ ghi lại quyết định của điều
          dưỡng, không phải độ chính xác của AI, vì hệ thống không có kết luận chuẩn nào để so.
        </EmptyNote>
      ) : compared === 0 ? (
        <EmptyNote icon={ClipboardCheck}>
          Cả {formatCount(total)} ca đã chốt đều không có mức AI đề xuất để so: điều dưỡng tự chốt mức cho từng ca.
        </EmptyNote>
      ) : (
        <>
          <ComparisonBar agreement={agreement} compared={compared} />

          <ul role="list" className="mt-6 grid grid-cols-3 gap-4">
            {AGREEMENT_SERIES.map((series) => {
              const count = agreementCount(agreement, series.key);
              return (
                <li key={series.key} className="min-w-0">
                  <span className="flex items-center gap-2 text-sm leading-6 text-muted-foreground">
                    <SeriesSwatch color={series.color} />
                    {series.label}
                  </span>
                  <span className="mt-2 block text-2xl font-extrabold leading-none tracking-tight text-foreground">
                    <AnimatedNumber value={count} />
                  </span>
                  <span className="mt-2 block text-sm leading-6 text-muted-foreground">
                    {percentOf(count, compared)}
                  </span>
                </li>
              );
            })}
          </ul>

          {without > 0 ? (
            <p className="mt-4 text-sm leading-6 text-muted-foreground">
              Thêm {formatCount(without)} ca điều dưỡng tự chốt vì AI chưa đề xuất mức; các ca này không nằm trong
              thanh so sánh.
            </p>
          ) : null}

          <p className="mt-4 border-t border-border pt-4 text-sm leading-6 text-muted-foreground">
            Hệ thống không có kết luận chuẩn nào để đối chiếu, nên đây là thống kê quyết định của điều dưỡng. Tỉ lệ
            tính trên {formatCount(compared)} ca có mức AI đề xuất.
          </p>
        </>
      )}
    </DashboardPanel>
  );
}

/** Thanh phân cực: các đoạn cách nhau 2px, chỉ bo 4px ở hai đầu ngoài cùng. */
function ComparisonBar({ agreement, compared }: { agreement: SimpleAgreementDTO; compared: number }) {
  const shown = AGREEMENT_SERIES.filter((series) => agreementCount(agreement, series.key) > 0);
  const { shownKey, markProps } = useMarkFocus(shown.map((series) => series.key));

  let running = 0;
  const anchors = new Map<string, number>();
  for (const series of shown) {
    const count = agreementCount(agreement, series.key);
    anchors.set(series.key, ((running + count / 2) / compared) * 100);
    running += count;
  }
  const active = shown.find((series) => series.key === shownKey);

  return (
    <div className="relative">
      <div
        role="list"
        aria-label={`Quyết định của điều dưỡng trên ${compared} ca có mức AI đề xuất`}
        className="flex h-6 gap-0.5"
      >
        {shown.map((series, index) => {
          const count = agreementCount(agreement, series.key);
          return (
            <div
              key={series.key}
              role="listitem"
              aria-label={`${series.label}: ${count} ca, ${percentOf(count, compared)} trên ${compared} ca có mức AI đề xuất`}
              {...markProps(series.key)}
              style={{ flexGrow: count, backgroundColor: series.color, animationDelay: `${barDelayMs(index)}ms` }}
              className={cn(
                "bar-grow min-w-2 basis-0 cursor-default outline-hidden transition-[flex-grow,filter] duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] hover:brightness-110 focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card motion-reduce:transition-none",
                index === 0 && "rounded-l-[4px]",
                index === shown.length - 1 && "rounded-r-[4px]",
              )}
            />
          );
        })}
      </div>
      <AnimatePresence>
        {active ? (
          <MarkTooltip key={active.key} anchor={anchors.get(active.key) ?? 50}>
            <TooltipBody
              value={`${formatCount(agreementCount(agreement, active.key))} ca`}
              label={active.label}
              detail={`${percentOf(agreementCount(agreement, active.key), compared)} trên ${compared} ca có mức AI đề xuất`}
              swatch={<SeriesSwatch color={active.color} />}
            />
          </MarkTooltip>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
