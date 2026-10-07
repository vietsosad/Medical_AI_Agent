"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowDown,
  ExternalLink,
  Loader2,
  Send,
  ShieldAlert,
  Stethoscope,
  User,
  X,
} from "lucide-react";

import { useCareTeamThread, useSendCaseMessage, useMarkCaseMessagesRead } from "@/hooks/queries/use-clinical-hitl";
import { cn } from "@/lib/utils";
import type { ClinicalTranscriptMessageDTO } from "@/types/clinical-hitl";

/**
 * ============================================================================
 * [QUICK CHAT] TRẢ LỜI NGƯỜI BỆNH NGAY TỪ HÀNG ĐỢI
 * ============================================================================
 * Không bắt nhân viên mở toàn bộ hồ sơ lâm sàng chỉ để nhắn một câu. Ngăn này
 * chỉ mang **kênh liên lạc**: lời qua tiếng lại giữa hai con người. Hội thoại
 * hỏi bệnh với AI, sinh hiệu và danh bạ liên hệ vẫn nằm trong hồ sơ đầy đủ và
 * vẫn đòi phải nhận ca.
 *
 * Gửi câu đầu tiên đồng nghĩa với nhận ca: trả lời người bệnh là đã nhận trách
 * nhiệm, nên backend nhận ca ngay trong cùng thao tác đó.
 */

function formatTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function Bubble({ message }: { message: ClinicalTranscriptMessageDTO }) {
  const fromStaff = message.sender === "NURSE";
  return (
    <li className={cn("flex flex-col gap-1", fromStaff ? "items-end" : "items-start")}>
      <span className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
        {fromStaff ? (
          <>
            <Stethoscope className="size-3.5 text-teal-600" aria-hidden="true" />
            {message.sender_name ?? "Nhân viên y tế"}
          </>
        ) : (
          <>
            <User className="size-3.5" aria-hidden="true" />
            Người bệnh
          </>
        )}
      </span>
      <div
        className={cn(
          "max-w-[88%] whitespace-pre-wrap break-words rounded-2xl border px-3.5 py-2.5 text-sm leading-6",
          fromStaff
            ? "rounded-tr-sm border-teal-700 bg-teal-600 text-white"
            : "rounded-tl-sm border-border bg-card text-slate-800 dark:text-slate-100",
        )}
      >
        {message.content}
      </div>
      <time dateTime={message.created_at} className="text-xs text-slate-400">
        {formatTime(message.created_at)}
      </time>
    </li>
  );
}

interface QuickChatDrawerProps {
  caseId: string;
  patientName: string;
  priority?: "RED_FLAG" | "URGENT" | "NORMAL";
  onClose: () => void;
}

export function QuickChatDrawer({
  caseId,
  patientName,
  priority = "NORMAL",
  onClose,
}: QuickChatDrawerProps) {
  const [draft, setDraft] = useState("");
  const [pinned, setPinned] = useState(true);
  const [seenCount, setSeenCount] = useState(0);
  const listRef = useRef<HTMLOListElement>(null);

  const { data, isLoading, isError } = useCareTeamThread(caseId, true);
  const sendMessage = useSendCaseMessage(caseId);
  const { mutate: markRead } = useMarkCaseMessagesRead(caseId);
  
  const messages = data?.messages ?? [];
  const unread = data?.unread_count ?? 0;

  useEffect(() => {
    if (unread > 0) markRead();
  }, [unread, markRead]);

  // Cuộn thông minh. `seenCount` chỉ đổi trong trình xử lý sự kiện cuộn, kể cả
  // khi chính ta cuộn bằng mã: đặt scrollTop cũng phát ra sự kiện scroll, nên
  // không cần đặt state bên trong effect và không tạo vòng render dây chuyền.
  const handleScroll = () => {
    const list = listRef.current;
    if (!list) return;
    const atBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 48;
    setPinned(atBottom);
    if (atBottom) setSeenCount(messages.length);
  };

  useEffect(() => {
    const list = listRef.current;
    // Chỉ kéo xuống khi người đọc đang ở cuối. Đang xem lại tin cũ mà bị kéo
    // tụt xuống đáy là hành vi làm mất chỗ đang đọc.
    if (list && pinned) list.scrollTop = list.scrollHeight;
  }, [messages.length, pinned]);

  const hasNewBelow = !pinned && messages.length > seenCount;

  const jumpToLatest = () => {
    const list = listRef.current;
    if (!list) return;
    list.scrollTop = list.scrollHeight;
    setPinned(true);
    setSeenCount(messages.length);
  };

  const handleSend = (event: React.FormEvent) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sendMessage.isPending) return;
    sendMessage.mutate(
      { content, clientMessageId: crypto.randomUUID() },
      { onSuccess: () => setDraft("") },
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-label="Hội thoại nhanh với người bệnh">
      <button
        type="button"
        aria-label="Đóng hội thoại"
        onClick={onClose}
        className="flex-1 bg-slate-950/25"
      />

      <section className="flex h-full w-full max-w-md flex-col border-l border-border bg-background shadow-2xl">
        <header className="flex items-start justify-between gap-3 border-b border-border bg-card px-5 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-base font-bold text-foreground">{patientName}</h2>
            <p className="mt-1 flex flex-wrap items-center gap-2 text-xs font-semibold">
              {priority === "RED_FLAG" && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-700 px-2.5 py-1 text-white">
                  <ShieldAlert className="size-3.5" aria-hidden="true" />
                  Red Flag
                </span>
              )}
              {priority === "URGENT" && (
                <span className="rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-amber-900">
                  Ưu tiên cao
                </span>
              )}
              <span className="text-muted-foreground">Kênh liên lạc · không phải hồ sơ đầy đủ</span>
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng"
            className="flex size-11 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500"
          >
            <X className="size-5" aria-hidden="true" />
          </button>
        </header>

        <div className="relative flex-1 overflow-hidden">
          <ol
            ref={listRef}
            onScroll={handleScroll}
            className="flex h-full flex-col gap-4 overflow-y-auto px-5 py-4"
          >
            {isLoading ? (
              <li className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                Đang tải hội thoại...
              </li>
            ) : isError ? (
              <li className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
                Không tải được hội thoại lúc này.
              </li>
            ) : messages.length === 0 ? (
              <li className="rounded-xl border border-border bg-card p-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
                Chưa có trao đổi nào. Gửi câu đầu tiên đồng nghĩa với việc bạn nhận ca này.
              </li>
            ) : (
              messages.map((message) => <Bubble key={message.id} message={message} />)
            )}
          </ol>

          {hasNewBelow && (
            <button
              type="button"
              onClick={jumpToLatest}
              className="absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-teal-300 bg-card px-3.5 py-2 text-sm font-bold text-teal-800 shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
            >
              <ArrowDown className="size-4" aria-hidden="true" />
              Tin nhắn mới
            </button>
          )}
        </div>

        <form onSubmit={handleSend} className="border-t border-border bg-card p-4">
          <label htmlFor="quick-chat-input" className="sr-only">
            Nhắn cho người bệnh
          </label>
          <div className="flex items-end gap-2">
            <textarea
              id="quick-chat-input"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) handleSend(event);
              }}
              rows={2}
              maxLength={2000}
              placeholder="Nhắn cho người bệnh..."
              className="min-h-11 flex-1 resize-none rounded-xl border border-slate-300 bg-card px-3 py-2.5 text-sm leading-6 text-foreground placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 dark:border-slate-700"
            />
            <button
              type="submit"
              disabled={!draft.trim() || sendMessage.isPending}
              aria-label="Gửi tin nhắn cho người bệnh"
              className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
            >
              {sendMessage.isPending ? (
                <Loader2 className="size-5 animate-spin" aria-hidden="true" />
              ) : (
                <Send className="size-5" aria-hidden="true" />
              )}
            </button>
          </div>

          {sendMessage.isError && (
            <p role="alert" className="mt-2 text-sm font-semibold text-rose-700">
              {sendMessage.error instanceof Error
                ? sendMessage.error.message
                : "Không gửi được · Thử lại"}
            </p>
          )}

          <Link
            href={`/clinical/cases/${encodeURIComponent(caseId)}`}
            className="mt-3 inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-sky-800 hover:text-sky-950"
          >
            Mở hồ sơ lâm sàng đầy đủ
            <ExternalLink className="size-4" aria-hidden="true" />
          </Link>
        </form>
      </section>
    </div>
  );
}

export default QuickChatDrawer;
