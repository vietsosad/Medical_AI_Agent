"use client";

import { useEffect, useId, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, Loader2, Lock, MessageSquareText, Send } from "lucide-react";

import { formatClock } from "@/components/clinical/nurse-simple/case/case-format";
import { riseVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";
import {
  useMarkSimpleCaseMessagesRead,
  useSendSimpleCaseMessage,
  useSimpleCaseCareTeamThread,
  useSimpleCaseRealtime,
} from "@/queries/useSimpleNurseQueries";
import type { SimpleCareTeamMessageDTO } from "@/types/simple-care-team";

/**
 * Kênh nhắn tin giữa điều dưỡng và người bệnh của một ca.
 *
 * Ở màn rộng, thẻ này nằm ghim ở cột trái của hồ sơ ca, luôn trong tầm mắt.
 * Ở màn hẹp hơn, nó nằm trong `SimpleCaseChatDock.tsx` (nút nổi + khung bật
 * lên) -- khi còn nằm giữa trang, sau SBAR và cả bản ghi hội thoại, điều
 * dưỡng phải cuộn qua hết mới thấy chỗ trả lời.
 * `useSimpleCaseRealtime` (WebSocket, lùi về polling) làm mới luồng ngay khi
 * người bệnh trả lời. Gửi tin sẽ tự nhận ca ở backend nếu chưa ai nhận.
 */

function MessageBubble({ message, animate }: { message: SimpleCareTeamMessageDTO; animate: boolean }) {
  const fromStaff = message.sender === "staff";
  const time = formatClock(message.created_at);
  return (
    <motion.li
      variants={riseVariants}
      initial={animate ? "hidden" : false}
      animate="visible"
      className={cn("flex flex-col gap-2", fromStaff ? "items-end" : "items-start")}
    >
      <span className="text-sm font-semibold text-muted-foreground">
        {fromStaff ? "Bạn (y tá)" : "Bệnh nhân"}
        {time && (
          <>
            {" · "}
            <time dateTime={message.created_at}>{time}</time>
          </>
        )}
      </span>
      <p
        className={cn(
          "max-w-[85%] whitespace-pre-wrap break-words rounded-2xl px-4 py-2 text-sm leading-6",
          fromStaff ? "rounded-tr-md bg-brand text-brand-foreground" : "rounded-tl-md bg-muted text-foreground",
        )}
      >
        {message.content}
      </p>
    </motion.li>
  );
}

export function SimpleCaseChatPanel({
  sessionId,
  onCollapse,
  readOnly = false,
  autoFocus = false,
  className,
}: {
  sessionId: string;
  /** Có khi thẻ nằm trong khung nổi của `SimpleCaseChatDock.tsx`. */
  onCollapse?: () => void;
  /** Ca đã đóng: vẫn đọc được trao đổi cũ nhưng backend không nhận tin mới. */
  readOnly?: boolean;
  /** Đưa con trỏ vào ô soạn tin ngay khi thẻ hiện ra (điều dưỡng chủ động mở). */
  autoFocus?: boolean;
  className?: string;
}) {
  const [draft, setDraft] = useState("");
  const listRef = useRef<HTMLOListElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const ids = useId();
  const headingId = `${ids}-heading`;
  const inputId = `${ids}-input`;

  const thread = useSimpleCaseCareTeamThread(sessionId);
  const sendMessage = useSendSimpleCaseMessage(sessionId);
  const markRead = useMarkSimpleCaseMessagesRead(sessionId);
  useSimpleCaseRealtime(sessionId);

  const messages = thread.data?.messages ?? [];
  const unread = thread.data?.unread_count ?? 0;

  // Tin đã có lúc luồng tải xong thì hiện cùng thẻ; chỉ tin đến sau mới nổi
  // lên, để mắt điều dưỡng bắt đúng câu vừa tới. Mốc được chốt một lần, ngay
  // lần đầu có dữ liệu (cập nhật state trong lúc dựng, không cần effect).
  const [baseline, setBaseline] = useState<ReadonlySet<string> | null>(() =>
    thread.data ? new Set(thread.data.messages.map((message) => message.id)) : null,
  );
  if (baseline === null && thread.data) {
    setBaseline(new Set(thread.data.messages.map((message) => message.id)));
  }

  const markReadMutate = markRead.mutate;
  useEffect(() => {
    if (unread > 0) markReadMutate();
  }, [unread, markReadMutate]);

  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [messages.length]);

  useEffect(() => {
    if (autoFocus && !readOnly) inputRef.current?.focus();
  }, [autoFocus, readOnly]);

  const handleSend = (event: React.FormEvent) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sendMessage.isPending) return;
    sendMessage.mutate({ content, clientMessageId: crypto.randomUUID() }, { onSuccess: () => setDraft("") });
  };

  return (
    <section
      aria-labelledby={headingId}
      className={cn("flex flex-col gap-4 rounded-2xl border border-border bg-card p-4 shadow-xs", className)}
    >
      <div className="flex items-center justify-between gap-2">
        <h2 id={headingId} className="flex items-center gap-2 text-base font-bold text-foreground">
          <MessageSquareText className="size-5 shrink-0 text-brand" aria-hidden="true" />
          Nhắn người bệnh
          {unread > 0 && (
            <span className="inline-flex min-w-6 items-center justify-center rounded-full bg-brand px-2 text-sm font-bold tabular-nums text-brand-foreground">
              {unread}
              <span className="sr-only"> tin chưa đọc</span>
            </span>
          )}
        </h2>
        {onCollapse && (
          <button
            type="button"
            onClick={onCollapse}
            aria-label="Thu gọn khung nhắn tin"
            className="flex size-11 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          >
            <ChevronDown className="size-5" aria-hidden="true" />
          </button>
        )}
      </div>

      <ol ref={listRef} className="flex max-h-80 min-h-24 flex-col gap-4 overflow-y-auto overscroll-contain">
        {thread.isLoading ? (
          <li className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
            Đang tải hội thoại...
          </li>
        ) : thread.isError && !thread.data ? (
          <li className="rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
            Không tải được tin nhắn với người bệnh. Hệ thống sẽ tự thử lại.
          </li>
        ) : messages.length === 0 ? (
          <li className="rounded-xl bg-muted p-4 text-sm leading-6 text-foreground/75">
            {readOnly
              ? "Ca này không có trao đổi nào với người bệnh."
              : "Chưa có tin nhắn nào. Gửi tin cho bệnh nhân sẽ tự động nhận ca này nếu chưa ai nhận."}
          </li>
        ) : (
          messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              animate={baseline !== null && !baseline.has(message.id)}
            />
          ))
        )}
      </ol>

      {readOnly ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Lock className="size-4 shrink-0" aria-hidden="true" />
          Ca đã đóng, không thể nhắn thêm.
        </p>
      ) : (
        <form onSubmit={handleSend} className="flex items-end gap-2">
          <label htmlFor={inputId} className="sr-only">
            Nhắn cho bệnh nhân
          </label>
          <textarea
            ref={inputRef}
            id={inputId}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) handleSend(event);
            }}
            rows={2}
            maxLength={2000}
            placeholder="Nhắn cho người bệnh..."
            className="min-h-11 min-w-0 flex-1 resize-none rounded-xl border border-border bg-background px-4 py-2 text-sm leading-6 text-foreground placeholder:text-muted-foreground focus-visible:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
          />
          <motion.button
            type="submit"
            whileTap={{ scale: 0.97 }}
            disabled={!draft.trim() || sendMessage.isPending}
            aria-label="Gửi tin nhắn cho bệnh nhân"
            className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-brand text-brand-foreground transition-colors hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:opacity-50"
          >
            {sendMessage.isPending ? (
              <Loader2 className="size-5 animate-spin motion-reduce:animate-none" aria-hidden="true" />
            ) : (
              <Send className="size-5" aria-hidden="true" />
            )}
          </motion.button>
        </form>
      )}
      {sendMessage.isError && (
        <p role="alert" className="text-sm font-semibold text-rose-700 dark:text-rose-400">
          {sendMessage.error instanceof Error ? sendMessage.error.message : "Không gửi được tin nhắn."}
        </p>
      )}
    </section>
  );
}
