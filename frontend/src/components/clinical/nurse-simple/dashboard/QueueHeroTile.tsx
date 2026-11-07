"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, ShieldAlert } from "lucide-react";
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
 * tìm ca chờ lâu nhất và đếm ma trận mức khẩn, nên mọi phần trong ô này cộng
 * lại khớp nhau. Bên dưới là hai câu hỏi đầu ca: ai đang giữ những ca này
 * (phần "chưa ai nhận" là con số mà thẻ "Hàng đợi" ở thanh bên đếm) và các ca
 * đã chờ bao lâu.
 *
 * Nền tối ở cả hai chế độ: ô duy nhất được nhấn mạnh, các màu trạng thái bên
 * trong vì thế chỉ cần một bộ giá trị.
 */
export function QueueHeroTile({ dashboard, className }: { dashboard: SimpleNurseDashboardDTO; className?: string }) {
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
        "flex min-w-0 flex-col rounded-2xl bg-slate-900 p-6 text-white shadow-sm ring-1 ring-slate-900/10",
        "dark:bg-slate-800 dark:ring-white/10",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <h3 id="queue-hero-title" className="text-sm font-semibold leading-6 text-slate-300">
          Ca đang mở
        </h3>
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

      {dashboard.attention_live > 0 ? (
        <p className="mt-4 flex items-center gap-2 text-sm leading-6 text-rose-100">
          <ShieldAlert className="size-4 shrink-0 text-rose-300" aria-hidden="true" />
          <span>
            <strong className="font-bold text-white">{formatCount(dashboard.attention_live)}</strong> ca có dấu hiệu
            cần xem ngay
          </span>
        </p>
      ) : null}

      {/* Ô cao bằng ma trận bên cạnh: phần dư chia đều trên hai nhóm "ai đang
          giữ" và "chờ bao lâu" (hai margin tự động), thay vì dồn thành một
          khoảng trống. Màn hẹp không có phần dư, khoảng cách còn đúng pt-6. */}
      <div className="mt-auto pt-6">
        <h4 className="text-sm font-semibold leading-6 text-slate-300">Ai đang giữ ca</h4>
        {live === 0 ? (
          <p className="mt-2 text-sm leading-6 text-slate-300">Không có ca nào đang mở.</p>
        ) : (
          <OwnershipBar waiting={dashboard.waiting} assigned={dashboard.assigned_total} />
        )}
        <ul role="list" aria-label="Chú giải" className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
          {OWNERSHIP_PARTS.map((part) => (
            <li key={part.key} className="flex items-center gap-2 text-sm leading-6 text-slate-200">
              <span aria-hidden="true" className={cn("h-2 w-4 shrink-0 rounded-[2px]", part.fill)} />
              {part.label}
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-auto pt-6">
        <h4 className="text-sm font-semibold leading-6 text-slate-300">Thời gian chờ tiếp nhận</h4>
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

type OwnershipKey = "waiting" | "assigned";

/**
 * Hai phần của "ai đang giữ ca". Phần cần hành động (chưa ai nhận) mang màu
 * nhấn, phần đã có người lo mang xám lùi -- nhấn mạnh một phần, không phải hai
 * màu tranh nhau. Cả hai đặt trên nền tối của ô ở MỌI chế độ; số in bên trong
 * dùng mực gần đen (>= 7:1 trên cả hai màu).
 */
const OWNERSHIP_PARTS: ReadonlyArray<{ key: OwnershipKey; label: string; fill: string }> = [
  { key: "waiting", label: "Chưa ai nhận", fill: "bg-teal-300" },
  { key: "assigned", label: "Đã có người phụ trách", fill: "bg-slate-400" },
];

/** Dưới tỉ lệ này đoạn quá hẹp để in số: số nằm ở chú thích nổi và ở luồng xử lý ca. */
const MIN_LABELLED_SHARE = 0.15;

/**
 * Thanh phân đoạn cao (28px): một tổng chia làm hai phần, số ca in ngay trong
 * từng đoạn, chú giải bên dưới chỉ ghi tên. Đoạn bằng 0 không vẽ gì.
 */
function OwnershipBar({ waiting, assigned }: { waiting: number; assigned: number }) {
  const total = waiting + assigned;
  const counts: Record<OwnershipKey, number> = { waiting, assigned };
  const shown = OWNERSHIP_PARTS.filter((part) => counts[part.key] > 0);
  const { shownKey, markProps } = useMarkFocus(shown.map((part) => part.key));

  let running = 0;
  const anchors = new Map<OwnershipKey, number>();
  for (const part of shown) {
    anchors.set(part.key, ((running + counts[part.key] / 2) / total) * 100);
    running += counts[part.key];
  }
  const active = shown.find((part) => part.key === shownKey);

  return (
    <div className="relative mt-2">
      <div role="list" aria-label={`Ai đang giữ ${total} ca đang mở`} className="flex h-7 gap-0.5">
        {shown.map((part, index) => {
          const count = counts[part.key];
          return (
            <div
              key={part.key}
              role="listitem"
              aria-label={`${part.label}: ${count} ca, ${percentOf(count, total)} trên ${total} ca đang mở`}
              {...markProps(part.key)}
              style={{ flexGrow: count, animationDelay: `${barDelayMs(index)}ms` }}
              className={cn(
                "bar-grow flex min-w-2 basis-0 cursor-default items-center rounded-[4px] px-2 text-sm font-bold text-slate-950 outline-hidden",
                "transition-[flex-grow,filter] duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] hover:brightness-110 focus-visible:ring-2 focus-visible:ring-white motion-reduce:transition-none",
                part.fill,
              )}
            >
              {count / total >= MIN_LABELLED_SHARE ? (
                <span aria-hidden="true" className="tabular-nums">
                  {formatCount(count)}
                </span>
              ) : null}
            </div>
          );
        })}
      </div>
      <AnimatePresence>
        {active ? (
          <MarkTooltip key={active.key} anchor={anchors.get(active.key) ?? 50}>
            <TooltipBody
              value={`${formatCount(counts[active.key])} ca`}
              label={active.label}
              detail={`${percentOf(counts[active.key], total)} trên ${total} ca đang mở`}
              swatch={<span aria-hidden="true" className={cn("h-2 w-4 shrink-0 rounded-[2px]", active.fill)} />}
            />
          </MarkTooltip>
        ) : null}
      </AnimatePresence>
    </div>
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
