"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowDown,
  Bot,
  CheckCheck,
  ChevronDown,
  Loader2,
  Send,
  ShieldAlert,
  Stethoscope,
  User,
  WifiOff,
} from "lucide-react";

import {
  useCaseMessages,
  useCaseRealtime,
  useMarkCaseMessagesRead,
  useSendCaseMessage,
} from "@/hooks/queries/use-clinical-hitl";
import { cn } from "@/lib/utils";
import type { ClinicalTranscriptMessageDTO, TranscriptSender } from "@/types/clinical-hitl";

/**
 * ============================================================================
 * [CASE CHAT] HỘI THOẠI TRỰC TIẾP GIỮA NHÂN VIÊN LÂM SÀNG VÀ NGƯỜI BỆNH
 * ============================================================================
 * Nguyên tắc bắt buộc: mỗi dòng tin phải nói rõ ai viết. Trộn lời của mô hình
 * với lời của một nhân viên y tế sẽ khiến hồ sơ giao tiếp lâm sàng không quy
 * được trách nhiệm về ai — đó là sai sót hồ sơ, không phải chi tiết trình bày.
 */

interface SenderStyle {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  bubble: string;
  badge: string;
  align: "start" | "end";
}

const SENDER_STYLES: Record<TranscriptSender, SenderStyle> = {
  PATIENT: {
    label: "Người bệnh",
    icon: User,
    bubble: "bg-card border-border text-slate-800 dark:text-slate-100",
    badge: "bg-muted text-slate-700 border-border dark:text-slate-200",
    align: "start",
  },
  AI_AGENT: {
    label: "Trợ lý AI",
    icon: Bot,
    bubble: "bg-sky-50/70 border-sky-200 text-slate-800",
    badge: "bg-sky-100 text-sky-800 border-sky-200",
    align: "start",
  },
  SYSTEM_SHIELD: {
    label: "Lớp chắn an toàn",
    icon: ShieldAlert,
    bubble: "bg-amber-50 border-amber-200 text-amber-950",
    badge: "bg-amber-100 text-amber-900 border-amber-300",
    align: "start",
  },
  NURSE: {
    label: "Nhân viên y tế",
    icon: Stethoscope,
    bubble: "bg-teal-600 border-teal-700 text-white",
    badge: "bg-teal-100 text-teal-900 border-teal-300",
    align: "end",
  },
};

function formatTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function MessageRow({ message }: { message: ClinicalTranscriptMessageDTO }) {
  const style = SENDER_STYLES[message.sender] ?? SENDER_STYLES.AI_AGENT;
  const Icon = style.icon;
  const fromStaff = message.sender === "NURSE";

  return (
    <li
      className={cn(
        "flex w-full flex-col gap-1.5",
        style.align === "end" ? "items-end" : "items-start",
      )}
    >
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
          style.badge,
        )}
      >
        <Icon className="size-3.5 shrink-0" aria-hidden="true" />
        {/* Tên thật của nhân viên đứng trước nhãn vai trò, để người đọc biết
            chính xác ai đã nói câu này. */}
        {fromStaff && message.sender_name ? message.sender_name : style.label}
      </span>

      <div
        className={cn(
          "max-w-[85%] whitespace-pre-wrap break-words rounded-2xl border px-4 py-2.5 text-sm leading-6 shadow-xs",
          style.bubble,
        )}
      >
        {message.content}
      </div>

      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <time dateTime={message.created_at}>{formatTime(message.created_at)}</time>
        {message.sender === "PATIENT" && message.read_at && (
          <>
            <CheckCheck className="size-3.5 text-teal-600" aria-hidden="true" />
            <span>Đã đọc</span>
          </>
        )}
      </span>
    </li>
  );
}

interface CaseChatPanelProps {
  caseId: string;
  /** Chỉ nhân viên đang phụ trách ca mới đọc và nhắn được. */
  isAssignedToMe: boolean;
  patientName: string;
  /** Có mặt khi khung được nhúng trong một khung nổi thu gọn được. */
  onCollapse?: () => void;
}

export function CaseChatPanel({
  caseId,
  isAssignedToMe,
  patientName,
  onCollapse,
}: CaseChatPanelProps) {
  const [draft, setDraft] = useState("");
  const [pinned, setPinned] = useState(true);
  const [seenCount, setSeenCount] = useState(0);
  const listRef = useRef<HTMLOListElement>(null);

  const realtimeStatus = useCaseRealtime(caseId, isAssignedToMe);
  const { data, isLoading, isError } = useCaseMessages(caseId, isAssignedToMe);
  const sendMessage = useSendCaseMessage(caseId);
  const { mutate: markRead } = useMarkCaseMessagesRead(caseId);

  const messages = useMemo(() => data?.messages ?? [], [data]);
  const unread = data?.unread_count ?? 0;

  // Mở hội thoại tức là đã đọc; đánh dấu một lần cho mỗi đợt tin mới.
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

  if (!isAssignedToMe) {
    return (
      <section className="rounded-2xl border border-border bg-background p-6 text-sm text-slate-600 dark:text-slate-300">
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-base font-bold text-foreground">Hội thoại với người bệnh</h3>
          {onCollapse && (
            <button
              type="button"
              onClick={onCollapse}
              aria-label="Thu gọn hội thoại"
              className="flex size-11 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 dark:hover:bg-slate-700"
            >
              <ChevronDown className="size-5" aria-hidden="true" />
            </button>
          )}
        </div>
        <p className="mt-2 leading-6">
          Cần nhận ca trước khi đọc hoặc nhắn tin. Nội dung hội thoại là lời kể bệnh, chỉ
          nhân viên đang phụ trách mới được xem.
        </p>
      </section>
    );
  }

  const handleSend = (event: React.FormEvent) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sendMessage.isPending) return;
    sendMessage.mutate(
      { content, clientMessageId: crypto.randomUUID() },
      { onSuccess: () => setDraft("") },
    );
  };

  const offline = realtimeStatus === "reconnecting";

  return (
    <section className="flex flex-col overflow-hidden rounded-2xl border border-border bg-card">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 bg-background/80 px-5 py-4">
        <div>
          <h3 className="text-base font-bold text-foreground">Hội thoại với người bệnh</h3>
          <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-300">{patientName}</p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
            realtimeStatus === "open"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-amber-200 bg-amber-50 text-amber-900",
          )}
        >
          {realtimeStatus === "open" ? (
            <>
              <span className="size-2 rounded-full bg-emerald-500" aria-hidden="true" />
              Trực tuyến
            </>
          ) : (
            <>
              <WifiOff className="size-3.5" aria-hidden="true" />
              Đang kết nối lại
            </>
          )}
        </span>

        {onCollapse && (
          <button
            type="button"
            onClick={onCollapse}
            aria-label="Thu gọn hội thoại"
            className="flex size-11 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 dark:hover:bg-slate-700"
          >
            <ChevronDown className="size-5" aria-hidden="true" />
          </button>
        )}
        </div>
      </header>

      {offline && (
        <p
          role="status"
          className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-5 py-2.5 text-sm font-medium text-amber-900"
        >
          <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
          Mất kết nối realtime. Đang kết nối lại... Hội thoại đã tải vẫn được giữ nguyên.
        </p>
      )}

      <div className="relative">
      <ol
        ref={listRef}
        onScroll={handleScroll}
        className="flex max-h-[22rem] min-h-[12rem] flex-col gap-4 overflow-y-auto px-5 py-4"
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
          <li className="py-10 text-center text-sm text-muted-foreground">
            Chưa có tin nhắn nào trong ca này.
          </li>
        ) : (
          messages.map((message) => <MessageRow key={message.id} message={message} />)
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

      <form onSubmit={handleSend} className="border-t border-slate-100 bg-background/60 p-4">
        <label htmlFor="case-chat-input" className="sr-only">
          Nội dung nhắn cho người bệnh
        </label>
        <div className="flex items-end gap-2">
          <textarea
            id="case-chat-input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) handleSend(event);
            }}
            rows={2}
            maxLength={2000}
            placeholder="Nhắn cho người bệnh. Nội dung này được lưu vào hồ sơ giao tiếp của ca."
            className="min-h-11 flex-1 resize-none rounded-xl border border-slate-300 bg-card px-3.5 py-2.5 text-sm leading-6 text-foreground placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 dark:border-slate-700"
          />
          <button
            type="submit"
            disabled={!draft.trim() || sendMessage.isPending}
            className="flex min-h-11 items-center gap-2 rounded-xl bg-teal-600 px-4 text-sm font-bold text-white transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
          >
            {sendMessage.isPending ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <Send className="size-4" aria-hidden="true" />
            )}
            Gửi
          </button>
        </div>

        {sendMessage.isError && (
          <p role="alert" className="mt-2 text-sm font-medium text-amber-800">
            {sendMessage.error instanceof Error
              ? sendMessage.error.message
              : "Không gửi được tin nhắn."}
          </p>
        )}
      </form>
    </section>
  );
}

export default CaseChatPanel;
