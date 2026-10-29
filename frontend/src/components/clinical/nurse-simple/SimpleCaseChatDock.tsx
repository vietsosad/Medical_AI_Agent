"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { MessageSquareText } from "lucide-react";

import { SimpleCaseChatPanel } from "@/components/clinical/nurse-simple/SimpleCaseChatPanel";
import { useSimpleCaseCareTeamThread } from "@/queries/useSimpleNurseQueries";
import { useClinicalSocket, type ClinicalRealtimeEvent } from "@/lib/realtime/useClinicalSocket";
import { DURATION, EASE_OUT, enterTransition, exitTransition } from "@/lib/motion";
import { cn } from "@/lib/utils";

/**
 * Khung nhắn tin nổi của hồ sơ ca, dùng khi màn hình chưa đủ rộng để ghim
 * thẻ nhắn tin ở cột trái. Luôn trong tầm tay với số tin chưa đọc, và tự bật
 * lên khi người bệnh vừa nhắn -- một tin nằm im trong khung đã thu gọn không
 * khác gì không có kênh nào.
 */

export function SimpleCaseChatDock({
  sessionId,
  initialOpen = false,
  readOnly = false,
}: {
  sessionId: string;
  /** True when reached via a "Tin nhắn mới" inbox click (`?openChat=1`, see
   * SimpleClinicalInbox.tsx) -- opens the dock immediately instead of
   * requiring a click. Read once at mount only. */
  initialOpen?: boolean;
  /** Ca đã đóng: đọc lại được trao đổi cũ, không gửi thêm. */
  readOnly?: boolean;
}) {
  const [open, setOpen] = useState(initialOpen);
  // Chỉ đưa con trỏ vào ô soạn tin khi chính điều dưỡng mở khung. Khung tự bật
  // vì tin mới thì không được giành tiêu điểm khỏi việc họ đang gõ dở.
  const [openedByUser, setOpenedByUser] = useState(initialOpen);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const restoreFocus = useRef(false);

  // Same query key as the panel, so TanStack Query shares one fetch whether
  // or not the dock is currently expanded.
  const thread = useSimpleCaseCareTeamThread(sessionId);
  const unread = thread.data?.unread_count ?? 0;

  const handleRealtimeEvent = useCallback((event: ClinicalRealtimeEvent) => {
    if (event.event === "message.created" && event.payload?.sender === "PATIENT") {
      setOpenedByUser(false);
      setOpen(true);
    }
  }, []);

  useClinicalSocket({
    path: `/ws/simple-case/${encodeURIComponent(sessionId)}`,
    onEvent: handleRealtimeEvent,
  });

  useEffect(() => {
    if (!open && restoreFocus.current) {
      restoreFocus.current = false;
      launcherRef.current?.focus();
    }
  }, [open]);

  const expand = () => {
    setOpenedByUser(true);
    setOpen(true);
  };

  const collapse = () => {
    restoreFocus.current = true;
    setOpen(false);
  };

  return (
    <AnimatePresence initial={false}>
      {open ? (
        <motion.div
          key="panel"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0, transition: enterTransition }}
          exit={{ opacity: 0, y: 8, transition: exitTransition }}
          className="fixed inset-x-4 bottom-4 z-40 max-h-[85dvh] overflow-y-auto rounded-2xl shadow-xl sm:inset-x-auto sm:bottom-6 sm:right-6 sm:w-[28rem]"
        >
          <SimpleCaseChatPanel
            sessionId={sessionId}
            onCollapse={collapse}
            readOnly={readOnly}
            autoFocus={openedByUser}
          />
        </motion.div>
      ) : (
        <motion.button
          key="launcher"
          ref={launcherRef}
          type="button"
          onClick={expand}
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1, transition: { duration: DURATION.quick, ease: EASE_OUT } }}
          exit={{ opacity: 0, transition: exitTransition }}
          whileTap={{ scale: 0.97 }}
          aria-label={`Mở khung nhắn tin với bệnh nhân${unread > 0 ? `, ${unread} tin chưa đọc` : ""}`}
          className={cn(
            "fixed bottom-6 right-6 z-40 flex min-h-14 items-center gap-4 rounded-2xl border bg-card px-4 py-2 shadow-lg transition-[translate,border-color] duration-200 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background motion-reduce:hover:translate-y-0",
            unread > 0 ? "border-brand ring-2 ring-brand/30" : "border-border",
          )}
        >
          <span className="relative flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand text-brand-foreground">
            <MessageSquareText className="size-5" aria-hidden="true" />
            {unread > 0 && (
              <span className="live-dot live-rose absolute -right-2 -top-2 flex size-6 items-center justify-center rounded-full bg-rose-600 text-xs font-bold tabular-nums text-white">
                {unread > 9 ? "9+" : unread}
              </span>
            )}
          </span>
          <span className="flex flex-col text-left">
            <span className="text-sm font-bold text-foreground">Nhắn người bệnh</span>
            <span className="text-sm text-muted-foreground">
              {unread > 0 ? `${unread} tin chưa đọc` : "Nhắn trực tiếp cho người bệnh"}
            </span>
          </span>
        </motion.button>
      )}
    </AnimatePresence>
  );
}

export default SimpleCaseChatDock;
