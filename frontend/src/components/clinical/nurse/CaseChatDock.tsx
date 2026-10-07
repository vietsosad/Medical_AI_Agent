"use client";

import React, { useCallback, useState } from "react";
import { MessageSquareText } from "lucide-react";

import { CaseChatPanel } from "@/components/clinical/nurse/CaseChatPanel";
import { useCaseMessages } from "@/hooks/queries/use-clinical-hitl";
import {
  useClinicalSocket,
  type ClinicalRealtimeEvent,
} from "@/lib/realtime/useClinicalSocket";
import { cn } from "@/lib/utils";

/**
 * ============================================================================
 * [CASE CHAT DOCK] KHUNG HỘI THOẠI NỔI TRONG HỒ SƠ CA
 * ============================================================================
 * Hội thoại với người bệnh từng nằm giữa hồ sơ ca, kẹp giữa phần đề xuất của AI
 * và phần chốt phân luồng. Nhân viên đang nhập sinh hiệu hoặc đọc SBAR phải cuộn
 * đi tìm mới thấy, và một tin nhắn vừa tới thì hoàn toàn nằm ngoài tầm mắt.
 *
 * Đưa ra thành khung nổi giải quyết đúng chỗ đó: hội thoại luôn trong tầm với ở
 * mọi bước làm việc, thu gọn được khi cần chỗ, và có huy hiệu tin chưa đọc.
 */

interface CaseChatDockProps {
  caseId: string;
  isAssignedToMe: boolean;
  patientName: string;
}

export function CaseChatDock({ caseId, isAssignedToMe, patientName }: CaseChatDockProps) {
  const [open, setOpen] = useState(false);

  // Cùng query key với khung hội thoại bên trong nên TanStack Query dùng chung
  // một lần gọi mạng.
  const { data } = useCaseMessages(caseId, isAssignedToMe);
  const unread = data?.unread_count ?? 0;

  const handleRealtimeEvent = useCallback((event: ClinicalRealtimeEvent) => {
    // Người bệnh vừa nhắn thì bật khung lên ngay. Một tin nằm im trong khung đã
    // thu gọn không khác gì không có kênh nào.
    if (event.event === "message.created" && event.payload?.sender === "PATIENT") {
      setOpen(true);
    }
  }, []);

  useClinicalSocket({
    path: caseId ? `/ws/case/${encodeURIComponent(caseId)}` : null,
    onEvent: handleRealtimeEvent,
    enabled: isAssignedToMe && Boolean(caseId),
  });

  if (open) {
    return (
      <div className="fixed inset-x-3 bottom-3 z-40 sm:inset-x-auto sm:bottom-6 sm:right-6 sm:w-[28rem]">
        <CaseChatPanel
          caseId={caseId}
          isAssignedToMe={isAssignedToMe}
          patientName={patientName}
          onCollapse={() => setOpen(false)}
        />
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setOpen(true)}
      aria-label={`Mở hội thoại với người bệnh${unread > 0 ? `, ${unread} tin chưa đọc` : ""}`}
      className={cn(
        "fixed bottom-6 right-6 z-40 flex min-h-14 items-center gap-3 rounded-2xl border bg-card px-4 py-2.5 shadow-lg transition-transform hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 motion-reduce:hover:translate-y-0",
        unread > 0 ? "border-teal-400 ring-2 ring-teal-500/40" : "border-slate-300 dark:border-slate-700",
      )}
    >
      <span className="relative flex size-10 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white">
        <MessageSquareText className="size-5 stroke-[2.2]" aria-hidden="true" />
        {unread > 0 && (
          <span className="absolute -right-1.5 -top-1.5 flex size-5 items-center justify-center rounded-full bg-rose-600 text-xs font-bold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </span>
      <span className="flex flex-col text-left">
        <span className="text-sm font-bold text-foreground">Hội thoại với người bệnh</span>
        <span className="text-xs font-semibold text-muted-foreground">
          {isAssignedToMe
            ? unread > 0
              ? `${unread} tin chưa đọc`
              : "Nhắn trực tiếp cho người bệnh"
            : "Cần nhận ca trước"}
        </span>
      </span>
    </button>
  );
}

export default CaseChatDock;
