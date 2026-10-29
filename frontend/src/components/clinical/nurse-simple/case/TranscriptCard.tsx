"use client";

import { memo } from "react";
import { motion } from "framer-motion";
import { MessagesSquare } from "lucide-react";

import { ClinicalMarkdown } from "@/components/chat/ClinicalMarkdown";
import { formatClock } from "@/components/clinical/nurse-simple/case/case-format";
import { riseIn, useInitialIds } from "@/components/clinical/nurse-simple/case/case-motion";
import { staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { SimpleNurseTranscriptRowDTO } from "@/types/simple-nurse";

/**
 * Bản ghi đầy đủ giữa người bệnh và trợ lý sàng lọc, chỉ để đọc và đối chiếu.
 * Trợ lý trả lời bằng markdown nên đi qua ClinicalMarkdown (chặn HTML thô và
 * đường dẫn không an toàn); lời người bệnh hiện nguyên văn.
 */

function rowKey(row: SimpleNurseTranscriptRowDTO): string {
  return `${row.turn_index}-${row.sender}-${row.created_at}`;
}

function TranscriptCardView({ messages, delay = 0 }: { messages: SimpleNurseTranscriptRowDTO[]; delay?: number }) {
  const initialIds = useInitialIds(messages.map(rowKey));

  return (
    <motion.section
      {...riseIn(delay)}
      aria-labelledby="case-transcript-title"
      className="rounded-2xl border border-border bg-card p-4 shadow-xs sm:p-6"
    >
      <h2 id="case-transcript-title" className="flex items-center gap-2 text-base font-bold text-foreground">
        <MessagesSquare className="size-5 shrink-0 text-brand" aria-hidden="true" />
        Hội thoại gốc
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Bản ghi đầy đủ giữa người bệnh và trợ lý sàng lọc, để đối chiếu khi cần.
      </p>

      {messages.length === 0 ? (
        <p className="mt-4 rounded-xl bg-muted p-4 text-sm text-foreground/75">Phiên chưa có tin nhắn nào.</p>
      ) : (
        <ol className="mt-4 flex flex-col gap-2">
          {messages.map((row, index) => {
            const key = rowKey(row);
            const fromPatient = row.sender === "PATIENT";
            const time = formatClock(row.created_at);
            return (
              <motion.li
                key={key}
                {...riseIn(initialIds.has(key) ? delay + 0.1 + staggerDelay(index) : 0)}
                className={cn(
                  "flex max-w-[85%] flex-col gap-2 rounded-2xl px-4 py-2 text-sm leading-6",
                  fromPatient
                    ? "self-end rounded-tr-md bg-brand text-brand-foreground"
                    : "self-start rounded-tl-md bg-muted text-foreground",
                )}
              >
                <span className="sr-only">
                  {fromPatient ? "Người bệnh" : "Trợ lý sàng lọc"}
                  {time ? ` lúc ${time}` : ""}:
                </span>
                {fromPatient ? (
                  <p className="whitespace-pre-wrap break-words">{row.content}</p>
                ) : (
                  <ClinicalMarkdown content={row.content} className="space-y-2 text-sm leading-6" />
                )}
                {time && (
                  <time aria-hidden="true" dateTime={row.created_at} className="self-end text-xs font-medium tabular-nums">
                    {time}
                  </time>
                )}
              </motion.li>
            );
          })}
        </ol>
      )}
    </motion.section>
  );
}

/**
 * Ca được làm mới mỗi 5 giây. TanStack Query giữ nguyên tham chiếu của mảng
 * tin nhắn khi không có gì mới (structural sharing), nên bọc memo là đủ để
 * không phải phân tích lại markdown của từng lượt trợ lý ở mỗi nhịp.
 */
export const TranscriptCard = memo(TranscriptCardView);
