"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Loader2, Send, Stethoscope, User } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  useMarkSimpleCaseMessagesRead,
  useSendSimpleCaseMessage,
  useSimpleCaseCareTeamThread,
  useSimpleCaseRealtime,
} from "@/queries/useSimpleNurseQueries";
import type { SimpleCareTeamMessageDTO } from "@/types/simple-care-team";

/**
 * Chat panel content for a nurse's pilot case. Rendered inside
 * `SimpleCaseChatDock.tsx` (a floating dock, mirroring
 * `@/components/clinical/nurse/CaseChatDock.tsx`) rather than inline in the
 * page -- it used to sit inline, past the SBAR summary and the entire AI
 * transcript, which meant scrolling past both just to find where to reply.
 * `useSimpleCaseRealtime` (WebSocket, falling back to polling) refreshes the
 * thread as soon as the patient replies. Sending auto-claims the case on the
 * backend if nobody has claimed it yet.
 */

function formatTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function MessageBubble({ message }: { message: SimpleCareTeamMessageDTO }) {
  const fromStaff = message.sender === "staff";
  return (
    <li className={cn("flex flex-col gap-1", fromStaff ? "items-end" : "items-start")}>
      <span className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
        {fromStaff ? (
          <>
            <Stethoscope className="size-3.5 text-teal-600" aria-hidden="true" />
            Bạn (y tá)
          </>
        ) : (
          <>
            <User className="size-3.5" aria-hidden="true" />
            Bệnh nhân
          </>
        )}
      </span>
      <div
        className={cn(
          "max-w-[85%] whitespace-pre-wrap break-words rounded-2xl border px-3.5 py-2.5 text-base leading-6",
          fromStaff
            ? "rounded-tr-sm border-teal-600 bg-teal-600 text-white"
            : "rounded-tl-sm border-border bg-background text-foreground",
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

export function SimpleCaseChatPanel({
  sessionId,
  onCollapse,
}: {
  sessionId: string;
  /** Present only when rendered inside `SimpleCaseChatDock.tsx`'s floating shell. */
  onCollapse?: () => void;
}) {
  const [draft, setDraft] = useState("");
  const listRef = useRef<HTMLOListElement>(null);

  const thread = useSimpleCaseCareTeamThread(sessionId);
  const sendMessage = useSendSimpleCaseMessage(sessionId);
  const markRead = useMarkSimpleCaseMessagesRead(sessionId);
  useSimpleCaseRealtime(sessionId);

  const messages = thread.data?.messages ?? [];
  const unread = thread.data?.unread_count ?? 0;

  const markReadMutate = markRead.mutate;
  useEffect(() => {
    if (unread > 0) markReadMutate();
  }, [unread, markReadMutate]);

  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [messages.length]);

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
    <section className="space-y-3 rounded-2xl border border-border bg-card p-4 shadow-sm sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-base font-bold text-slate-950 dark:text-slate-50">
          <Stethoscope className="size-5 text-teal-700" aria-hidden="true" />
          Nhắn với bệnh nhân
        </h2>
        {onCollapse && (
          <button
            type="button"
            onClick={onCollapse}
            aria-label="Thu gọn khung nhắn tin"
            className="flex size-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
          >
            <ChevronDown className="size-5" aria-hidden="true" />
          </button>
        )}
      </div>

      <ol ref={listRef} className="flex max-h-80 min-h-[6rem] flex-col gap-4 overflow-y-auto rounded-xl border border-slate-100 bg-background/60 p-3">
        {thread.isLoading ? (
          <li className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            Đang tải hội thoại...
          </li>
        ) : messages.length === 0 ? (
          <li className="rounded-xl border border-border bg-card p-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
            Chưa có tin nhắn nào. Gửi tin cho bệnh nhân sẽ tự động nhận ca này nếu chưa ai nhận.
          </li>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
      </ol>

      <form onSubmit={handleSend} className="flex items-end gap-2">
        <label htmlFor="simple-case-chat-input" className="sr-only">
          Nhắn cho bệnh nhân
        </label>
        <textarea
          id="simple-case-chat-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) handleSend(event);
          }}
          rows={2}
          maxLength={2000}
          placeholder="Nhắn cho bệnh nhân..."
          className="min-h-11 flex-1 resize-none rounded-xl border border-slate-300 bg-card px-3 py-2.5 text-base leading-6 text-foreground placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 dark:border-slate-700"
        />
        <button
          type="submit"
          disabled={!draft.trim() || sendMessage.isPending}
          aria-label="Gửi tin nhắn cho bệnh nhân"
          className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-45"
        >
          {sendMessage.isPending ? (
            <Loader2 className="size-5 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="size-5" aria-hidden="true" />
          )}
        </button>
      </form>
      {sendMessage.isError && (
        <p role="alert" className="text-sm font-semibold text-rose-700">
          {sendMessage.error instanceof Error ? sendMessage.error.message : "Không gửi được tin nhắn."}
        </p>
      )}
    </section>
  );
}
