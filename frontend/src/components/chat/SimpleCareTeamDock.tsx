"use client";

import React, { useEffect, useRef, useState } from "react";
import { ChevronDown, Loader2, MessageCircle, Send, Stethoscope, User } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  useMarkSimpleStaffMessagesRead,
  useSendSimpleMessageToStaff,
  useSimpleCareTeamRealtime,
  useSimpleCareTeamThread,
} from "@/queries/useSimpleTriageQueries";
import type { SimpleCareTeamMessageDTO } from "@/types/simple-care-team";

/**
 * Trimmed fork of `@/components/chat/CareTeamDock.tsx` for the simple_agent
 * pilot -- same visual language, but: no `care_team_status`/`care_team_name`
 * (simple_agent has no multi-stage review lifecycle label, just "phiên đã
 * kết thúc, đang chờ y tá xem"), and no auto-open-on-unread effect (a
 * `setState`-in-`useEffect` pattern already flagged by lint on the original
 * -- not reproduced here). `useSimpleCareTeamRealtime` (WebSocket, falling
 * back to polling) refreshes the thread the moment staff replies; see
 * `.claude/plans/sunny-launching-mitten.md`'s realtime addendum.
 * Only rendered once the session is `COMPLETED` (see `/triage-pilot`), so
 * `canMessage` is always true for the lifetime of this component.
 */

function formatTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function MessageBubble({ message }: { message: SimpleCareTeamMessageDTO }) {
  const fromStaff = message.sender === "staff";
  return (
    <li className={cn("flex flex-col gap-1", fromStaff ? "items-start" : "items-end")}>
      <span className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
        {fromStaff ? (
          <>
            <Stethoscope className="size-3.5 text-teal-600" aria-hidden="true" />
            Nhân viên y tế
          </>
        ) : (
          <>
            <User className="size-3.5" aria-hidden="true" />
            Bạn
          </>
        )}
      </span>
      <div
        className={cn(
          "max-w-[88%] whitespace-pre-wrap break-words rounded-2xl border px-3.5 py-2.5 text-base leading-6",
          fromStaff
            ? "rounded-tl-sm border-teal-200 bg-teal-50 text-teal-950"
            : "rounded-tr-sm border-sky-600 bg-sky-600 text-white",
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

export function SimpleCareTeamDock({
  sessionId,
  initialOpen = false,
  inline = false,
}: {
  sessionId: string;
  /** Đặt nút mở ngay trong thanh hành động của trang (cạnh "Gọi 115") thay vì
   * nổi ở góc màn hình, nơi nó từng che mất nút gọi 115 trên điện thoại. Khung
   * trò chuyện khi mở vẫn nổi như cũ. */
  inline?: boolean;
  /** True when the page was reached via a notification-bell click
   * (`?openChat=1`, see PatientNotificationBell.tsx) -- opens the dock
   * immediately instead of requiring a second click, and lets the existing
   * `unread > 0` effect below mark it read right away. Only read once, at
   * mount -- a later prop change (there shouldn't be one) intentionally
   * does not re-open a dock the patient just collapsed. */
  initialOpen?: boolean;
}) {
  const [open, setOpen] = useState(initialOpen);
  const [draft, setDraft] = useState("");
  const listRef = useRef<HTMLOListElement>(null);

  const thread = useSimpleCareTeamThread(sessionId);
  const sendMessage = useSendSimpleMessageToStaff(sessionId);
  const markRead = useMarkSimpleStaffMessagesRead(sessionId);
  useSimpleCareTeamRealtime(sessionId);

  const messages = thread.data?.messages ?? [];
  const unread = thread.data?.unread_from_staff ?? 0;

  const markReadMutate = markRead.mutate;
  useEffect(() => {
    if (open && unread > 0) markReadMutate();
  }, [open, unread, markReadMutate]);

  useEffect(() => {
    const list = listRef.current;
    if (open && list) list.scrollTop = list.scrollHeight;
  }, [open, messages.length]);

  const handleSend = (event: React.FormEvent) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sendMessage.isPending) return;
    sendMessage.mutate(
      { content, clientMessageId: crypto.randomUUID() },
      { onSuccess: () => setDraft("") },
    );
  };

  const inlineTrigger = inline ? (
    <button
      type="button"
      onClick={() => setOpen((current) => !current)}
      aria-label="Mở kênh trao đổi với nhân viên y tế"
      aria-expanded={open}
      className={cn(
        "relative flex min-h-12 items-center justify-center gap-2 rounded-xl border bg-background px-4 text-sm font-semibold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 sm:px-6 sm:text-base",
        unread > 0 ? "border-brand" : "border-border",
      )}
    >
      <MessageCircle className="size-5 shrink-0 text-brand" aria-hidden="true" />
      Nhắn nhân viên y tế
      {unread > 0 && (
        <span className="absolute -right-2 -top-2 flex size-6 items-center justify-center rounded-full bg-rose-600 text-xs font-bold text-white">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </button>
  ) : null;

  if (!open && inlineTrigger) return inlineTrigger;

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Mở kênh trao đổi với nhân viên y tế"
        className={cn(
          "fixed bottom-24 right-4 z-50 flex size-14 items-center justify-center gap-4 rounded-full border bg-card shadow-lg transition-transform hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 sm:right-6 sm:size-auto sm:min-h-14 sm:justify-start sm:rounded-2xl sm:px-4 sm:py-2",
          unread > 0 ? "border-brand ring-2 ring-brand/40" : "border-border",
        )}
      >
        <span className="relative flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand text-brand-foreground">
          <MessageCircle className="size-5 stroke-[2.2]" aria-hidden="true" />
          {unread > 0 && (
            <span className="absolute -right-1.5 -top-1.5 flex size-5 items-center justify-center rounded-full bg-rose-600 text-xs font-bold text-white">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </span>
        <span className="hidden flex-col text-left sm:flex">
          <span className="text-sm font-bold text-foreground">Nhân viên y tế</span>
          <span className="text-sm text-muted-foreground">Nhắn cho người thẩm định ca của bạn</span>
        </span>
      </button>
    );
  }

  return (
    <>
      {inlineTrigger}
      <section
        aria-label="Kênh trao đổi với nhân viên y tế"
        className="fixed inset-x-3 bottom-3 z-50 flex max-h-[70dvh] flex-col overflow-hidden rounded-2xl border border-slate-300 bg-card shadow-2xl sm:inset-x-auto sm:bottom-24 sm:right-6 sm:w-[26rem] dark:border-slate-700"
      >
        <header className="flex items-start justify-between gap-3 border-b border-slate-100 bg-background px-4 py-3">
          <div className="flex min-w-0 items-start gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white">
              <Stethoscope className="size-5 stroke-[2.2]" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h2 className="text-base font-bold text-foreground">Nhân viên y tế</h2>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Ca của bạn đang chờ hoặc đang được thẩm định.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Thu gọn kênh trao đổi"
            className="flex size-11 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 dark:hover:bg-slate-700"
          >
            <ChevronDown className="size-5" aria-hidden="true" />
          </button>
        </header>

        <ol ref={listRef} className="flex min-h-[9rem] flex-1 flex-col gap-4 overflow-y-auto px-4 py-4">
          {thread.isLoading ? (
            <li className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              Đang tải kênh trao đổi...
            </li>
          ) : messages.length === 0 ? (
            <li className="rounded-xl border border-border bg-background p-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
              Bạn nhắn được ngay bây giờ. Tin sẽ vào hàng đợi pilot và một y tá sẽ trả lời.
            </li>
          ) : (
            messages.map((message) => <MessageBubble key={message.id} message={message} />)
          )}
        </ol>

        <form onSubmit={handleSend} className="border-t border-slate-100 bg-background/70 p-3">
          <label htmlFor="simple-care-team-input" className="sr-only">
            Nhắn cho nhân viên y tế
          </label>
          <div className="flex items-end gap-2">
            <textarea
              id="simple-care-team-input"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) handleSend(event);
              }}
              rows={2}
              maxLength={2000}
              placeholder="Nhắn cho nhân viên y tế..."
              className="min-h-11 flex-1 resize-none rounded-xl border border-slate-300 bg-card px-3 py-2.5 text-base leading-6 text-foreground placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 dark:border-slate-700"
            />
            <button
              type="submit"
              disabled={!draft.trim() || sendMessage.isPending}
              aria-label="Gửi tin nhắn cho nhân viên y tế"
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
              {sendMessage.error instanceof Error ? sendMessage.error.message : "Không gửi được tin nhắn."}
            </p>
          )}
        </form>
      </section>
    </>
  );
}
