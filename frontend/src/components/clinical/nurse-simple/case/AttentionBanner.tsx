"use client";

import { motion } from "framer-motion";
import { MessageSquareText, PhoneCall, ShieldAlert } from "lucide-react";

import { formatClock, telHref, type ContactLine } from "@/components/clinical/nurse-simple/case/case-format";
import { riseIn } from "@/components/clinical/nurse-simple/case/case-motion";
import { dropVariants } from "@/lib/motion";
import type { SimpleNurseCaseDetailDTO } from "@/types/simple-nurse";

/**
 * "Cần xem ngay": cờ của bộ sàng lọc cấp cứu chạy trước mô hình. Đây là lý do
 * để một người xem ca NGAY, không phải một mức ESI, và có thể được gắn khi
 * người bệnh vẫn đang trò chuyện (phiên ACTIVE).
 *
 * Việc cần làm lúc này là gọi cho người đang cầm máy, nên nút gọi nằm ngay
 * trong dải cảnh báo và có vòng sáng ba nhịp kéo mắt tới đó.
 */
export function AttentionBanner({
  data,
  callTarget,
  closed,
}: {
  data: SimpleNurseCaseDetailDTO;
  callTarget: ContactLine | null;
  /** Ca đã chốt: cờ chỉ còn là một dòng lịch sử, không còn là việc cần làm. */
  closed: boolean;
}) {
  const reason = data.attention_reason?.trim() || "dấu hiệu nguy kịch";
  const raisedAt = formatClock(data.attention_raised_at);

  if (closed) {
    return (
      <motion.p
        {...riseIn(0.05)}
        className="flex items-start gap-2 rounded-2xl border border-border bg-card px-4 py-2 text-sm leading-6 text-muted-foreground"
      >
        <span className="flex h-6 shrink-0 items-center" aria-hidden="true">
          <ShieldAlert className="size-4" />
        </span>
        <span>
          Ca này từng được gắn cờ “Cần xem ngay”: sàng lọc tự động phát hiện {reason} trong lời người bệnh
          {raisedAt ? ` lúc ${raisedAt}` : ""}.
        </span>
      </motion.p>
    );
  }

  return (
    <motion.section
      variants={dropVariants}
      initial="hidden"
      animate="visible"
      role="alert"
      aria-live="assertive"
      className="flex flex-col gap-4 rounded-2xl border border-rose-300 bg-rose-50 p-4 text-rose-950 sm:flex-row sm:items-center sm:p-6 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-100"
    >
      <span
        className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-rose-700 text-white"
        aria-hidden="true"
      >
        <ShieldAlert className="size-6" />
      </span>

      <div className="min-w-0 flex-1">
        <p className="text-base font-extrabold">
          Cần xem ngay
          {raisedAt && <span className="font-semibold"> · gắn cờ lúc {raisedAt}</span>}
        </p>
        <p className="mt-2 text-base leading-6">
          Sàng lọc tự động phát hiện <strong>{reason}</strong> trong lời người bệnh. Đây không phải mức ESI.
          {data.session_status === "ACTIVE" && " Người bệnh vẫn đang trò chuyện với trợ lý."}
        </p>
      </div>

      {callTarget ? (
        <motion.a
          href={telHref(callTarget.phone)}
          whileTap={{ scale: 0.97 }}
          aria-label={`${callTarget.callLabel}: ${callTarget.name}, số ${callTarget.phone}`}
          className="ring-pulse inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-xl bg-rose-700 px-6 text-base font-extrabold text-white transition-colors hover:bg-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2 focus-visible:ring-offset-rose-50 dark:focus-visible:ring-offset-rose-950"
        >
          <PhoneCall className="size-5 shrink-0" aria-hidden="true" />
          <span className="flex flex-col items-start leading-tight">
            {callTarget.callLabel}
            <span className="text-sm font-semibold tabular-nums opacity-90">{callTarget.phone}</span>
          </span>
        </motion.a>
      ) : (
        <p className="flex items-center gap-2 text-sm font-semibold sm:max-w-56">
          <MessageSquareText className="size-4 shrink-0" aria-hidden="true" />
          Hồ sơ chưa có số điện thoại. Hãy nhắn tin cho người bệnh ngay.
        </p>
      )}
    </motion.section>
  );
}
