"use client";

import { useCallback, useState } from "react";
import { MessageSquareText } from "lucide-react";

import { SimpleCaseChatPanel } from "@/components/clinical/nurse-simple/SimpleCaseChatPanel";
import { useSimpleCaseCareTeamThread } from "@/queries/useSimpleNurseQueries";
import { useClinicalSocket, type ClinicalRealtimeEvent } from "@/lib/realtime/useClinicalSocket";
import { cn } from "@/lib/utils";

/**
 * Floating fork of `@/components/clinical/nurse/CaseChatDock.tsx` for the
 * simple_agent pilot case page. `SimpleCaseChatPanel` used to sit inline,
 * wedged between the SBAR summary and the full AI transcript -- a nurse
 * reading vitals or the transcript had to scroll past both just to find
 * where to reply, and a new patient message was invisible unless already
 * scrolled down there. Same fix as production: always-in-reach floating
 * button with an unread badge, expanding into the same panel.
 */

export function SimpleCaseChatDock({
  sessionId,
  initialOpen = false,
}: {
  sessionId: string;
  /** True when reached via a "Tin nhắn mới" inbox click (`?openChat=1`, see
   * SimpleClinicalInbox.tsx) -- opens the dock immediately instead of
   * requiring a click, same idiom as patient-side SimpleCareTeamDock's own
   * `initialOpen`. Read once at mount only. */
  initialOpen?: boolean;
}) {
  const [open, setOpen] = useState(initialOpen);

  // Same query key as the panel below, so TanStack Query shares one fetch
  // whether or not the dock is currently expanded.
  const thread = useSimpleCaseCareTeamThread(sessionId);
  const unread = thread.data?.unread_count ?? 0;

  const handleRealtimeEvent = useCallback((event: ClinicalRealtimeEvent) => {
    // Bệnh nhân vừa nhắn thì bật khung lên ngay -- một tin nằm im trong
    // khung đã thu gọn không khác gì không có kênh nào.
    if (event.event === "message.created" && event.payload?.sender === "PATIENT") {
      setOpen(true);
    }
  }, []);

  useClinicalSocket({
    path: `/ws/simple-case/${encodeURIComponent(sessionId)}`,
    onEvent: handleRealtimeEvent,
  });

  if (open) {
    return (
      <div className="fixed inset-x-3 bottom-3 z-40 max-h-[85dvh] overflow-y-auto sm:inset-x-auto sm:bottom-6 sm:right-6 sm:w-[28rem]">
        <SimpleCaseChatPanel sessionId={sessionId} onCollapse={() => setOpen(false)} />
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setOpen(true)}
      aria-label={`Mở khung nhắn tin với bệnh nhân${unread > 0 ? `, ${unread} tin chưa đọc` : ""}`}
      className={cn(
        "glow-soft glow-teal rise-in fixed bottom-6 right-6 z-40 flex min-h-14 items-center gap-3 rounded-2xl border bg-card px-4 py-2.5 shadow-lg hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 motion-reduce:hover:translate-y-0",
        unread > 0 ? "border-teal-400 ring-2 ring-teal-500/40" : "border-slate-300 dark:border-slate-700",
      )}
    >
      <span className="relative flex size-10 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white">
        <MessageSquareText className="size-5 stroke-[2.2]" aria-hidden="true" />
        {unread > 0 && (
          <span className="live-dot live-rose absolute -right-1.5 -top-1.5 flex size-5 items-center justify-center rounded-full bg-rose-600 text-xs font-bold tabular-nums text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </span>
      <span className="flex flex-col text-left">
        <span className="text-sm font-bold text-foreground">Nhắn với bệnh nhân</span>
        <span className="text-xs font-semibold text-muted-foreground">
          {unread > 0 ? `${unread} tin chưa đọc` : "Nhắn trực tiếp cho bệnh nhân"}
        </span>
      </span>
    </button>
  );
}

export default SimpleCaseChatDock;
