"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { formatWait } from "@/components/clinical/nurse-simple/wait-time";
import { cn } from "@/lib/utils";
import type { SimpleNurseDashboardDTO, SimpleWaitBucketDTO } from "@/types/simple-nurse";

import { AnimatedNumber } from "./AnimatedNumber";
import {
  formatCount,
  orderedWaitBuckets,
  percentOf,
  sumCounts,
  WAIT_BUCKET_META,
  waitBucketOf,
} from "./dashboard-model";
import { barDelayMs, cardRiseVariants, MarkTooltip, TooltipBody, useMarkFocus } from "./primitives";

/**
 * Con số chính của màn: số ca đang mở (đang chờ + đã có người phụ trách, không
 * tính ca tạm gác). Đây đúng là tập ca mà backend dùng để chia thời gian chờ,
 * tìm ca chờ lâu nhất và đếm phân bố mức ESI, nên mọi phần trong ô này cộng
 * lại khớp nhau. Số "chưa ai nhận" đứng ngay dưới, là con số mà thẻ "Hàng đợi"
 * ở thanh bên đang đếm -- hai nơi gọi hai đại lượng bằng hai tên khác nhau.
 *
 * Nền tối ở cả hai chế độ: ô duy nhất được nhấn mạnh, các màu trạng thái bên
 * trong vì thế chỉ cần một bộ giá trị.
 */
export function QueueHeroTile({ dashboard }: { dashboard: SimpleNurseDashboardDTO }) {
  const live = dashboard.waiting + dashboard.assigned_total;
  const buckets = orderedWaitBuckets(dashboard.wait_buckets);
  const bucketTotal = sumCounts(buckets);
  const longest = dashboard.longest_wait_minutes;
  const longestMeta = longest === null ? null : WAIT_BUCKET_META[waitBucketOf(longest)];
  const LongestIcon = longestMeta?.icon;

  return (
    <motion.section
      aria-labelledby="queue-hero-title"
      custom={0}
      variants={cardRiseVariants}
      initial="hidden"
      animate="visible"
      className={cn(
        "col-span-2 flex min-w-0 flex-col rounded-2xl bg-slate-900 p-6 text-white shadow-sm ring-1 ring-slate-900/10",
        "md:col-span-4 lg:col-span-2 xl:col-span-1 xl:row-span-2",
        "dark:bg-slate-800 dark:ring-white/10",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <h2 id="queue-hero-title" className="text-sm font-semibold leading-6 text-slate-300">
          Ca đang mở
        </h2>
        <Link
          href="/clinical/queue-pilot"
          className="-my-2 -mr-2 inline-flex min-h-11 shrink-0 items-center gap-2 rounded-xl px-4 text-sm font-semibold text-teal-200 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-teal-300"
        >
          Xem hàng đợi
          <ArrowRight className="size-4" aria-hidden="true" />
        </Link>
      </div>

      <p className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-2">
        <AnimatedNumber
          value={live}
          countUp
          className="text-6xl font-extrabold leading-none tracking-tight text-white"
          flashClassName="bg-teal-300/25"
        />
        {longest === null || !longestMeta || !LongestIcon ? (
          <span className="text-sm leading-6 text-slate-300">Không có ca nào đang chờ</span>
        ) : (
          <span className="inline-flex flex-wrap items-center gap-x-2 text-sm leading-6 text-slate-300">
            <LongestIcon className={cn("size-4 shrink-0", longestMeta.iconTone)} aria-hidden="true" />
            chờ lâu nhất
            <strong className="text-base font-bold text-white">{formatWait(longest)}</strong>
          </span>
        )}
      </p>

      <p className="mt-4 text-sm leading-6 text-slate-300">
        <strong className="font-bold text-white">{formatCount(dashboard.waiting)}</strong> chưa ai nhận
        <span aria-hidden="true"> · </span>
        <span className="sr-only">, </span>
        <strong className="font-bold text-white">{formatCount(dashboard.assigned_total)}</strong> đã có người phụ
        trách
      </p>

      <div className="mt-auto pt-6">
        <h3 className="text-sm font-semibold leading-6 text-slate-300">Thời gian chờ tiếp nhận</h3>
        {bucketTotal === 0 ? (
          <p className="mt-2 text-sm leading-6 text-slate-300">Chưa có ca nào để tính thời gian chờ.</p>
        ) : (
          <WaitSplitBar buckets={buckets} total={bucketTotal} />
        )}
        <ul role="list" className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
          {buckets.map((bucket) => {
            const meta = WAIT_BUCKET_META[bucket.key];
            const Icon = meta.icon;
            return (
              <li key={bucket.key} className="flex items-center gap-2 text-sm leading-6">
                <Icon className={cn("size-4 shrink-0", meta.iconTone)} aria-hidden="true" />
                <span className="text-slate-200">{meta.label}</span>
                <span className="font-bold text-white">{formatCount(bucket.count)}</span>
              </li>
            );
          })}
        </ul>
      </div>
    </motion.section>
  );
}

/**
 * Thanh chia ba nhóm chờ: phần-trên-tổng, các đoạn cách nhau 2px đúng màu nền
 * để mắt tách ranh giới mà không cần viền. Vạch sơn mảnh (8px) nhưng vùng di
 * chuột / chạm cao 24px.
 */
function WaitSplitBar({ buckets, total }: { buckets: SimpleWaitBucketDTO[]; total: number }) {
  const shown = buckets.filter((bucket) => bucket.count > 0);
  const { shownKey, markProps } = useMarkFocus(shown.map((bucket) => bucket.key));

  let running = 0;
  const anchors = new Map<string, number>();
  for (const bucket of shown) {
    anchors.set(bucket.key, ((running + bucket.count / 2) / total) * 100);
    running += bucket.count;
  }
  const active = shown.find((bucket) => bucket.key === shownKey);

  return (
    <div className="relative mt-2">
      <div role="list" aria-label={`Thời gian chờ của ${total} ca đang mở`} className="flex gap-0.5">
        {shown.map((bucket, index) => {
          const meta = WAIT_BUCKET_META[bucket.key];
          return (
            <div
              key={bucket.key}
              role="listitem"
              aria-label={`${meta.label}: ${bucket.count} ca, ${percentOf(bucket.count, total)} trên ${total} ca đang mở`}
              {...markProps(bucket.key)}
              style={{ flexGrow: bucket.count }}
              className="group min-w-2 basis-0 cursor-default rounded-[4px] py-2 outline-hidden transition-[flex-grow] duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] focus-visible:ring-2 focus-visible:ring-teal-300 motion-reduce:transition-none"
            >
              <div
                style={{ animationDelay: `${barDelayMs(index)}ms` }}
                className={cn(
                  "bar-grow h-2 transition-[filter] duration-200 group-hover:brightness-110 group-focus-visible:brightness-110",
                  meta.bar,
                  index === 0 && "rounded-l-[4px]",
                  index === shown.length - 1 && "rounded-r-[4px]",
                )}
              />
            </div>
          );
        })}
      </div>
      <AnimatePresence>
        {active ? (
          <MarkTooltip key={active.key} anchor={anchors.get(active.key) ?? 50}>
            <TooltipBody
              value={`${formatCount(active.count)} ca`}
              label={`Chờ ${WAIT_BUCKET_META[active.key].label.toLowerCase()}`}
              detail={`${percentOf(active.count, total)} trên ${total} ca đang mở`}
              swatch={<span aria-hidden="true" className={cn("h-2 w-4 shrink-0 rounded-[2px]", WAIT_BUCKET_META[active.key].bar)} />}
            />
          </MarkTooltip>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
