"use client";

import { useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import { Inbox, LoaderCircle, MessageSquareText, ShieldAlert, X } from "lucide-react";

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
import { enterTransition, popVariants, staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { AnimatedCount } from "@/components/clinical/nurse-simple/queue/AnimatedCount";

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
 *
 * Styling: the trigger lives inside the sidebar's dark token island, so it is
 * written with theme tokens only; the drawer is portalled to `<body>` and
 * follows the page theme.
 */

const rowRise: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: { ...enterTransition, delay: staggerDelay(index, 0.12) },
  }),
};

function InboxRow({
  item,
  index,
  onOpen,
}: {
  item: SimpleNurseQueueItemDTO;
  index: number;
  onOpen: () => void;
}) {
  const esi = item.ai_proposed_esi;
  const message = item.initial_message.trim();

  return (
    <motion.li variants={rowRise} custom={index} initial="hidden" animate="visible" className="p-4">
      <div className="flex flex-wrap items-center gap-2">
        {item.attention_required && (
          <span className="inline-flex items-center gap-2 rounded-full bg-rose-700 px-2 text-sm font-bold leading-6 text-white">
            <ShieldAlert className="size-4" aria-hidden="true" />
            Cần xem ngay
          </span>
        )}
        <span
          className={cn(
            "rounded-full border px-2 text-sm font-bold leading-6",
            esi ? esiTheme(esi).chip : "border-border bg-muted text-muted-foreground",
          )}
        >
          {esi ? `ESI ${esi}` : "Chưa đủ dữ liệu"}
        </span>
        <span className="inline-flex items-center gap-2 rounded-full border border-brand-edge bg-brand-soft px-2 text-sm font-bold leading-6 text-brand-ink">
          <MessageSquareText className="size-4" aria-hidden="true" />
          <span className="tabular-nums">{item.unread_count}</span> tin mới
        </span>
      </div>

      {item.patient_name?.trim() && (
        <p className="mt-2 text-base font-bold text-foreground">{item.patient_name.trim()}</p>
      )}
      <p className="mt-2 line-clamp-2 text-sm leading-6 text-muted-foreground">
        {message ? `“${message}”` : "Chưa có mô tả triệu chứng"}
      </p>

      <div className="mt-4 flex justify-end">
        <Link
          href={`/clinical/cases-pilot/${item.session_id}?openChat=1`}
          onClick={onOpen}
          className="flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-bold text-brand-foreground transition-colors hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <MessageSquareText className="size-4" aria-hidden="true" />
          Mở chat
        </Link>
      </div>
    </motion.li>
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
            "group relative flex min-h-11 w-full items-center gap-2 rounded-xl border px-4 text-sm font-semibold transition-colors duration-200",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand",
            totalUnread > 0
              ? "border-brand-edge bg-brand-soft text-brand-ink hover:bg-brand-edge/30"
              : "border-border text-muted-foreground hover:bg-muted hover:text-foreground",
          )}
        >
          <Inbox className="size-5 shrink-0" strokeWidth={2.1} aria-hidden="true" />
          <span className="min-w-0 flex-1 truncate text-left">Tin nhắn mới</span>
          {/* Còn người bệnh chờ trả lời: số tin bật vào và tỏa vòng sáng -- "có việc đang chờ bạn". */}
          <AnimatePresence initial={false}>
            {totalUnread > 0 && (
              <motion.span
                key="badge"
                aria-hidden="true"
                variants={popVariants}
                initial="hidden"
                animate="visible"
                exit="hidden"
                className="live-dot live-teal inline-flex min-w-8 shrink-0 items-center justify-center rounded-full bg-brand px-2 text-sm font-bold leading-6 text-brand-foreground"
              >
                {totalUnread > 99 ? "99+" : <AnimatedCount value={totalUnread} />}
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </DialogTrigger>

      <DialogContent
        hideCloseButton
        overlayClassName="bg-slate-950/25 backdrop-blur-none"
        className={cn(
          "inset-y-0 right-0 left-auto top-0 flex h-dvh w-full max-w-md translate-x-0 translate-y-0 flex-col gap-0 overflow-hidden rounded-none border-0 border-l border-border bg-background p-0 text-foreground shadow-2xl backdrop-blur-none sm:rounded-none",
          // Ngăn kéo nằm ở mép phải thì trượt vào từ mép phải, không bay từ giữa màn hình ra.
          "motion-safe:data-[state=open]:[--tw-enter-translate-x:100%]! motion-safe:data-[state=closed]:[--tw-exit-translate-x:100%]!",
          "motion-reduce:data-[state=open]:[--tw-enter-translate-x:0]! motion-reduce:data-[state=closed]:[--tw-exit-translate-x:0]!",
          "data-[state=open]:[--tw-enter-translate-y:0]! data-[state=open]:[--tw-enter-scale:1]!",
          "data-[state=closed]:[--tw-exit-translate-y:0]! data-[state=closed]:[--tw-exit-scale:1]!",
        )}
      >
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-border bg-card p-4">
          <div className="min-w-0">
            <DialogTitle className="text-base font-bold text-foreground">Tin nhắn mới</DialogTitle>
            <DialogDescription className="mt-2 text-sm text-muted-foreground">
              Tin nhắn từ các ca bạn phụ trách.
            </DialogDescription>
          </div>
          <DialogClose asChild>
            <button
              type="button"
              aria-label="Đóng hộp thư"
              className="flex size-11 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              <X className="size-5" aria-hidden="true" />
            </button>
          </DialogClose>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex min-h-full items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
              <LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
              Đang tải hộp thư...
            </div>
          ) : isError ? (
            <div className="p-6 text-sm font-medium text-amber-900 dark:text-amber-200">Không tải được hộp thư lúc này.</div>
          ) : items.length === 0 ? (
            <div className="flex min-h-full flex-col items-center justify-center gap-4 p-6 text-center">
              <span className="flex size-12 items-center justify-center rounded-2xl bg-brand-soft text-brand-ink">
                <Inbox className="size-6" aria-hidden="true" />
              </span>
              <div>
                <h3 className="text-base font-bold text-foreground">Hộp thư đang trống</h3>
                <p className="mt-2 max-w-xs text-sm leading-6 text-muted-foreground">
                  Hiện chưa có bệnh nhân nào đang chờ bạn trả lời.
                </p>
              </div>
              <DialogClose asChild>
                <button
                  type="button"
                  className="min-h-11 min-w-11 rounded-xl border border-border bg-card px-4 text-sm font-bold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                >
                  Đóng
                </button>
              </DialogClose>
            </div>
          ) : (
            <ol className="divide-y divide-border">
              {items.map((item, index) => (
                <InboxRow key={item.session_id} item={item} index={index} onOpen={() => setOpen(false)} />
              ))}
            </ol>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default SimpleClinicalInbox;
