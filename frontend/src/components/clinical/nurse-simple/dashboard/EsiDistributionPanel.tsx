"use client";

import { AnimatePresence } from "framer-motion";
import { Inbox } from "lucide-react";

import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { cn } from "@/lib/utils";
import type { SimpleEsiBucketDTO } from "@/types/simple-nurse";

import { AnimatedNumber } from "./AnimatedNumber";
import { formatCount, percentOf, shareOf, sumCounts } from "./dashboard-model";
import { barDelayMs, DashboardPanel, EmptyNote, MarkTooltip, TooltipBody, useMarkFocus } from "./primitives";

type EsiKey = "1" | "2" | "3" | "4" | "5" | "unknown";

function esiKey(level: SimpleEsiBucketDTO["level"]): EsiKey {
  return level === null ? "unknown" : (String(level) as EsiKey);
}

/**
 * Ca đang mở theo mức AI đề xuất. Luôn đủ sáu vạch (1..5 và "chưa đủ
 * dữ liệu") kể cả khi bằng 0: một mức vắng mặt cũng là thông tin.
 *
 * Mỗi vạch mang màu dải ESI của bảng ca (`esiTheme().rail`) và LUÔN đứng cạnh
 * nhãn mức lẫn số đếm -- màu không bao giờ là kênh duy nhất. Độ dài so theo
 * vạch lớn nhất; số đếm nằm ngay đầu vạch.
 */
export function EsiDistributionPanel({ buckets, order }: { buckets: SimpleEsiBucketDTO[]; order: number }) {
  const total = sumCounts(buckets);
  const max = buckets.reduce((peak, bucket) => Math.max(peak, bucket.count), 0);
  const { shownKey, markProps } = useMarkFocus(buckets.map((bucket) => esiKey(bucket.level)));

  return (
    <DashboardPanel
      id="esi-distribution"
      order={order}
      title="Ca đang mở theo mức AI đề xuất"
      subtitle="Đề xuất của AI, chưa phải mức điều dưỡng chốt."
    >
      {total === 0 ? (
        <EmptyNote icon={Inbox}>
          Không có ca nào đang mở. Bảng này sẽ có số ngay khi kíp trực nhận ca mới.
        </EmptyNote>
      ) : (
        <>
          <ul role="list" aria-label="Số ca theo mức AI đề xuất" className="flex flex-col">
            {buckets.map((bucket, index) => {
              const key = esiKey(bucket.level);
              const theme = esiTheme(bucket.level);
              const name = bucket.level === null ? theme.label : `ESI ${bucket.level}`;
              const fullName = bucket.level === null ? theme.label : `ESI ${bucket.level} · ${theme.label}`;
              const share = shareOf(bucket.count, max);
              const pct = percentOf(bucket.count, total);
              // Dải "chưa đủ dữ liệu" có sẵn bậc tối riêng trong esiTheme, để trên nền
              // thẻ tối nó không sáng hơn mọi vạch màu.
              const rail = theme.rail;
              return (
                <li
                  key={key}
                  aria-label={`${fullName}: ${bucket.count} ca, ${pct} trên ${total} ca chưa đóng`}
                  {...markProps(key)}
                  className="grid min-h-11 cursor-default grid-cols-[minmax(0,8rem)_minmax(0,1fr)] items-center gap-4 rounded-xl px-2 outline-hidden transition-colors duration-200 hover:bg-muted/70 focus-visible:bg-muted/70 focus-visible:ring-2 focus-visible:ring-brand sm:grid-cols-[minmax(0,11rem)_minmax(0,1fr)]"
                >
                  <span className="min-w-0 text-sm leading-6">
                    <span className="font-semibold text-foreground">{name}</span>
                    {bucket.level !== null ? <span className="text-muted-foreground"> · {theme.label}</span> : null}
                  </span>
                  <span className="relative flex min-w-0 items-center gap-2">
                    {bucket.count > 0 ? (
                      <span
                        aria-hidden="true"
                        style={{ width: `calc((100% - 3rem) * ${share})`, animationDelay: `${barDelayMs(index)}ms` }}
                        className={cn(
                          "bar-grow h-4 min-w-2 rounded-r-[4px] transition-[width] duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none",
                          rail,
                        )}
                      />
                    ) : (
                      <span aria-hidden="true" className="h-4 w-0.5 shrink-0 rounded-full bg-slate-300 dark:bg-slate-600" />
                    )}
                    <AnimatedNumber
                      value={bucket.count}
                      className={cn(
                        "text-base font-bold leading-6",
                        bucket.count === 0 ? "text-muted-foreground" : "text-foreground",
                      )}
                    />
                    <AnimatePresence>
                      {shownKey === key ? (
                        <MarkTooltip anchor={share * 80}>
                          <TooltipBody
                            value={`${formatCount(bucket.count)} ca`}
                            label={fullName}
                            detail={`${pct} trên ${total} ca chưa đóng`}
                            swatch={<span aria-hidden="true" className={cn("h-2 w-4 shrink-0 rounded-[2px]", rail)} />}
                          />
                        </MarkTooltip>
                      ) : null}
                    </AnimatePresence>
                  </span>
                </li>
              );
            })}
          </ul>
          <p className="mt-4 border-t border-border pt-4 text-sm leading-6 text-muted-foreground">
            Trên {formatCount(total)} ca chưa đóng: ca đang chờ và ca đã có người phụ trách, không tính ca tạm gác.
          </p>
        </>
      )}
    </DashboardPanel>
  );
}
