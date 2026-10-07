"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Inbox, Loader2, MessageSquareText, X } from "lucide-react";

import { useSimpleNurseQueue, useSimpleNurseQueueRealtime } from "@/queries/useSimpleNurseQueries";
import type { SimpleNurseQueueItemDTO } from "@/types/simple-nurse";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

/**
 * Pilot-mode equivalent of `@/components/clinical/ClinicalInbox.tsx`, wired
 * into `ClinicalSidebar.tsx`'s "Tin nhắn mới" slot in place of it whenever
 * `IS_PILOT_AGENT_ACTIVE` -- same button/badge/slide-in-panel shape, sourced
 * from pilot data instead of production's `useClinicalInbox()`.
 *
 * Real bug this replaces (2026-08-29): a `SimpleNurseNotificationBell` was
 * first added to `ClinicalNavbar.tsx`'s top bar, but that whole navbar
 * returns `null` for every `/clinical/*` route (`isDedicatedRoleRoute`,
 * see that file) -- a nurse can never actually be on a page where it
 * renders. `ClinicalSidebar.tsx` (this component's real home) is the one
 * persistent surface `/clinical/layout.tsx` actually keeps mounted across
 * every clinical page, exactly like production's own `ClinicalInbox`
 * already relies on -- this fixes the underlying visibility bug instead of
 * layering another one.
 *
 * Same "seen" idiom as everywhere else in this pilot: no separate
 * notification-read flag, an item disappears the moment `unread_count` for
 * that session goes back to 0 (which happens via `SimpleCaseChatDock`'s own
 * mark-read effect once its panel opens -- see that file's `initialOpen`).
 * Deliberately scoped to claimed cases (`mineOnly: true`) only -- an
 * unclaimed case's new message already has its own "+N tin mới" badge
 * directly on the shared queue row, and has no single nurse to notify.
 *
 * Simpler than production's `ClinicalInbox`: no inline `QuickChatDrawer`
 * (that's built around production's own case-chat data model) -- a row
 * links straight to `/clinical/cases-pilot/{id}?openChat=1`, which opens
 * `SimpleCaseChatDock` immediately on arrival instead of replying inline
 * here.
 */
function InboxRow({
  item,
  index,
  onOpen,
}: {
  item: SimpleNurseQueueItemDTO;
  index: number;
  onOpen: () => void;
}) {
  return (
    <li
      style={{ "--rise-delay": `${Math.min(index, 6) * 60}ms` } as React.CSSProperties}
      className="glow-soft glow-teal rise-in border border-transparent bg-card p-4 hover:bg-teal-50/40"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded-full border px-2.5 py-0.5 text-xs font-bold",
            item.ai_proposed_esi && item.ai_proposed_esi <= 2
              ? "border-amber-300 bg-amber-50 text-amber-900"
              : "border-slate-300 bg-muted text-slate-700 dark:text-slate-200 dark:border-slate-700",
          )}
        >
          {item.ai_proposed_esi ? `ESI ${item.ai_proposed_esi}` : "Chưa đủ dữ liệu"}
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-300 bg-teal-50 px-2.5 py-0.5 text-xs font-bold text-teal-900">
          <MessageSquareText className="size-3.5" aria-hidden="true" />
          <span className="tabular-nums">{item.unread_count}</span> tin mới
        </span>
      </div>

      <p className="mt-2 line-clamp-2 rounded-lg bg-background px-3 py-2 text-sm leading-6 text-slate-700 dark:text-slate-200">
        {item.initial_message}
      </p>

      <div className="mt-3 flex justify-end">
        <Link
          href={`/clinical/cases-pilot/${item.session_id}?openChat=1`}
          onClick={onOpen}
          className="glow-soft glow-teal flex min-h-11 items-center gap-2 rounded-xl border border-teal-600 bg-teal-600 px-4 text-sm font-bold text-white hover:bg-teal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
        >
          <MessageSquareText className="size-4" aria-hidden="true" />
          Mở chat
        </Link>
      </div>
    </li>
  );
}

export function SimpleClinicalInbox() {
  const [open, setOpen] = useState(false);
  const { data, isLoading, isError } = useSimpleNurseQueue({ bucket: "QUEUE", mineOnly: true, pageSize: 50 });
  useSimpleNurseQueueRealtime();

  const items = (data?.items ?? []).filter((item) => item.unread_count > 0);
  const totalUnread = items.reduce((sum, item) => sum + item.unread_count, 0);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button
          type="button"
          aria-label={`Tin nhắn mới từ ca bạn phụ trách${totalUnread > 0 ? `, ${totalUnread} chưa đọc` : ""}`}
          title="Tin nhắn mới (ca bạn phụ trách)"
          className={cn(
            "group glow-soft glow-teal relative flex min-h-11 w-full items-center gap-3 rounded-xl border bg-card px-3 text-sm font-semibold text-slate-700 hover:bg-muted hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 dark:text-slate-200",
            totalUnread > 0 ? "border-teal-400 ring-2 ring-teal-500/30" : "border-slate-300 dark:border-slate-700",
          )}
        >
          <span className="relative">
            <Inbox className="size-5 shrink-0 stroke-[2.1] text-muted-foreground group-hover:text-slate-700 dark:group-hover:text-slate-200" aria-hidden="true" />
            {totalUnread > 0 && (
              <span className="absolute -right-2 -top-2 flex size-5 items-center justify-center rounded-full bg-teal-600 text-xs font-bold tabular-nums text-white">
                {totalUnread > 9 ? "9+" : totalUnread}
              </span>
            )}
          </span>
          <span className="min-w-0 flex-1 truncate text-left">Tin nhắn mới</span>
        </button>
      </DialogTrigger>

      <DialogContent
        hideCloseButton
        overlayClassName="bg-slate-950/25 backdrop-blur-none"
        className="inset-y-0 right-0 left-auto top-0 flex h-dvh w-full max-w-md translate-x-0 translate-y-0 flex-col gap-0 overflow-hidden rounded-none border-0 border-l border-border bg-background p-0 text-foreground shadow-2xl backdrop-blur-none sm:rounded-none"
      >
        <header className="flex shrink-0 items-start justify-between gap-3 border-b border-border bg-card p-4">
          <div className="min-w-0">
            <DialogTitle className="text-base font-bold text-foreground">Tin nhắn mới</DialogTitle>
            <DialogDescription className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Tin nhắn từ các ca bạn phụ trách.
            </DialogDescription>
          </div>
          <DialogClose asChild>
            <button
              type="button"
              aria-label="Đóng hộp thư"
              className="glow-soft glow-sky flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-xl border border-transparent text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500"
            >
              <X className="size-5" aria-hidden="true" />
            </button>
          </DialogClose>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex min-h-full items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              Đang tải hộp thư...
            </div>
          ) : isError ? (
            <div className="p-6 text-sm font-medium text-amber-900">Không tải được hộp thư lúc này.</div>
          ) : items.length === 0 ? (
            <div className="flex min-h-full flex-col items-center justify-center gap-4 p-6 text-center">
              <span className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
                <Inbox className="size-6" aria-hidden="true" />
              </span>
              <div className="space-y-2">
                <h3 className="text-base font-bold text-foreground">Hộp thư đang trống</h3>
                <p className="max-w-xs text-sm leading-6 text-slate-600 dark:text-slate-300">
                  Hiện chưa có bệnh nhân nào đang chờ bạn trả lời.
                </p>
              </div>
              <DialogClose asChild>
                <button
                  type="button"
                  className="glow-soft glow-sky min-h-11 min-w-11 rounded-xl border border-slate-300 bg-card px-4 text-sm font-bold text-slate-700 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 dark:text-slate-200 dark:border-slate-700"
                >
                  Đóng
                </button>
              </DialogClose>
            </div>
          ) : (
            <ol className="divide-y divide-slate-200">
              {items.map((item, index) => (
                <InboxRow
                  key={item.session_id}
                  item={item}
                  index={index}
                  onOpen={() => setOpen(false)}
                />
              ))}
            </ol>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default SimpleClinicalInbox;
