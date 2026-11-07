"use client";

import { motion } from "framer-motion";
import { ArrowRight, CircleCheck, CloudOff, MessageSquareText, ShieldAlert, TriangleAlert } from "lucide-react";
import Link from "next/link";

import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { formatWait, waitClasses, waitingMinutes } from "@/components/clinical/nurse-simple/wait-time";
import { DURATION, EASE_OUT, staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useSimpleNurseQueue } from "@/queries/useSimpleNurseQueries";
import type { SimpleNurseQueueItemDTO } from "@/types/simple-nurse";

import { formatCount } from "./dashboard-model";
import { DashboardPanel, EmptyNote } from "./primitives";

/** Số ca hiện trên bảng tổng quan; phần còn lại ở hàng đợi. */
export const PRIORITY_LIST_SIZE = 5;

/**
 * Cùng tham số mà màn hàng đợi dùng cho tab "Hàng đợi": backend tự sắp theo
 * hạng khẩn (ca bị gắn cờ xếp cùng ESI 1) rồi theo thời gian chờ, và chỉ trả
 * ca CHƯA AI NHẬN. Trang 1 cỡ 5 vì thế đúng là 5 ca cần người nhận trước nhất
 * -- bảng tổng quan không tự sắp lại thứ tự nào.
 */
const PRIORITY_QUERY = { bucket: "QUEUE", page: 1, pageSize: PRIORITY_LIST_SIZE } as const;

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card";

/**
 * Ca cần người nhận trước: đúng đầu hàng đợi chung, mỗi hàng mở thẳng hồ sơ
 * ca. Một nút chính duy nhất ở chân thẻ dẫn sang hàng đợi đầy đủ.
 */
export function PriorityCasesPanel({ order }: { order: number }) {
  const queue = useSimpleNurseQueue(PRIORITY_QUERY);
  const items = queue.data?.items ?? [];
  const totalUnclaimed = queue.data?.pagination.total_items ?? 0;

  let body;
  if (queue.isLoading) {
    body = (
      <ul aria-hidden="true" className="flex flex-col gap-2">
        {["a", "b", "c"].map((key) => (
          <li key={key} className="skeleton-sweep relative h-16 overflow-hidden rounded-xl bg-muted/70" />
        ))}
      </ul>
    );
  } else if (queue.isError) {
    body = (
      <EmptyNote icon={CloudOff}>
        Không tải được danh sách ca. Hàng đợi đầy đủ vẫn mở được bằng nút bên dưới.
      </EmptyNote>
    );
  } else if (items.length === 0) {
    body = <EmptyNote icon={CircleCheck}>Không có ca nào đang chờ người nhận.</EmptyNote>;
  } else {
    body = (
      <ol role="list" aria-label="Ca chưa ai nhận, theo thứ tự ưu tiên của hàng đợi" className="flex flex-col gap-2">
        {items.map((item, index) => (
          <PriorityRow key={item.session_id} item={item} index={index} />
        ))}
      </ol>
    );
  }

  return (
    <DashboardPanel
      id="priority-cases"
      order={order}
      title="Ca cần người nhận trước"
      subtitle="Đầu hàng đợi chung: ca có dấu hiệu nguy cấp và mức khẩn cao trước, rồi tới ca chờ lâu hơn."
    >
      {body}
      <div className="mt-auto flex flex-wrap items-center justify-between gap-4 pt-4">
        <p className="text-sm leading-6 text-muted-foreground">
          {queue.isSuccess
            ? totalUnclaimed > items.length
              ? `Còn ${formatCount(totalUnclaimed - items.length)} ca chưa ai nhận khác trong hàng đợi.`
              : "Đây là toàn bộ ca chưa ai nhận."
            : null}
        </p>
        <Link
          href="/clinical/queue-pilot"
          className={cn(
            "inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-bold text-brand-foreground shadow-xs transition-colors duration-200 hover:bg-brand-strong",
            focusRing,
          )}
        >
          Mở hàng đợi
          <ArrowRight className="size-4" aria-hidden="true" />
        </Link>
      </div>
    </DashboardPanel>
  );
}

function PriorityRow({ item, index }: { item: SimpleNurseQueueItemDTO; index: number }) {
  const minutes = waitingMinutes(item.waiting_since);
  const name = item.patient_name?.trim() || "Người bệnh chưa ghi tên";
  const message = item.initial_message.trim();
  return (
    <motion.li
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE_OUT, delay: staggerDelay(index, 0.2) } }}
    >
      <Link
        href={`/clinical/cases-pilot/${item.session_id}`}
        className={cn(
          "group flex min-h-16 items-start gap-4 rounded-xl px-2 py-2 transition-colors duration-200 hover:bg-muted/70 sm:items-center",
          focusRing,
        )}
      >
        <UrgencyMark item={item} />
        <span className="min-w-0 flex-1">
          {/* Tên và thời gian chờ chung một dòng: hai thứ cần đọc trước nhất. */}
          <span className="flex items-start justify-between gap-2">
            <span className="min-w-0 truncate text-base font-semibold leading-6 text-foreground">{name}</span>
            <span
              className={cn(
                "inline-flex shrink-0 items-center whitespace-nowrap rounded-full border px-2 text-sm font-semibold leading-6 tabular-nums",
                waitClasses(minutes),
              )}
            >
              <span className="sr-only">Đã chờ </span>
              {formatWait(minutes)}
            </span>
          </span>
          <span className="flex flex-wrap items-center gap-x-2">
            <StatusChip item={item} />
            {item.unread_count > 0 ? (
              <span className="inline-flex items-center gap-2 whitespace-nowrap text-sm font-semibold leading-6 text-brand-ink">
                <MessageSquareText className="size-4" aria-hidden="true" />
                {formatCount(item.unread_count)}
                <span className="sr-only"> tin nhắn chưa đọc</span>
              </span>
            ) : null}
          </span>
          {message ? <span className="block truncate text-sm leading-6 text-muted-foreground">{message}</span> : null}
        </span>
        <ArrowRight
          className="hidden size-4 shrink-0 self-center text-muted-foreground transition-transform duration-200 group-hover:translate-x-0.5 motion-reduce:transition-none sm:block"
          aria-hidden="true"
        />
      </Link>
    </motion.li>
  );
}

/** Ô mức độ thu nhỏ, cùng quy ước với hàng của bảng ca: cờ không bao giờ ghi thành "ESI". */
function UrgencyMark({ item }: { item: SimpleNurseQueueItemDTO }) {
  const esi = item.ai_proposed_esi;
  if (esi === null && item.attention_required) {
    return (
      <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-rose-700 text-white dark:bg-rose-600">
        <TriangleAlert className="size-5" strokeWidth={2.4} aria-hidden="true" />
        <span className="sr-only">Chưa có mức ESI</span>
      </span>
    );
  }
  if (esi === null) {
    return (
      <span className="flex size-11 shrink-0 items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-muted text-base font-extrabold text-muted-foreground dark:border-slate-600">
        <span aria-hidden="true">?</span>
        <span className="sr-only">Chưa có mức ESI</span>
      </span>
    );
  }
  return (
    <span
      className={cn(
        "flex size-11 shrink-0 flex-col items-center justify-center rounded-xl border leading-none",
        esiTheme(esi).chip,
      )}
    >
      <span className="text-xs font-bold" aria-hidden="true">
        ESI
      </span>
      <span className="text-lg font-extrabold tabular-nums" aria-hidden="true">
        {esi}
      </span>
      <span className="sr-only">ESI {esi}</span>
    </span>
  );
}

function StatusChip({ item }: { item: SimpleNurseQueueItemDTO }) {
  if (item.attention_required) {
    return (
      <span className="inline-flex items-center gap-2 whitespace-nowrap rounded-full bg-rose-700 px-2 text-sm font-bold leading-6 text-white dark:bg-rose-600">
        <ShieldAlert className="size-4" aria-hidden="true" />
        Cần xem ngay
      </span>
    );
  }
  if (item.ai_proposed_esi !== null) {
    return <span className="text-sm leading-6 text-muted-foreground">{esiTheme(item.ai_proposed_esi).label}</span>;
  }
  return (
    <span className="text-sm leading-6 text-muted-foreground">
      {item.is_insufficient ? "Chưa đủ dữ liệu để đề xuất" : "Chưa có đề xuất ESI"}
    </span>
  );
}
