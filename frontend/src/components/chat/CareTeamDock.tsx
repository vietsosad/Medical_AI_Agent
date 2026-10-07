"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronDown,
  Loader2,
  MessageCircle,
  Send,
  Stethoscope,
  User,
  WifiOff,
} from "lucide-react";

import {
  useClinicalSocket,
  type ClinicalRealtimeEvent,
} from "@/lib/realtime/useClinicalSocket";
import { cn } from "@/lib/utils";
import { TRIAGE_QUERY_KEYS } from "@/queries/triage-query-keys";
import {
  triageService,
  type CareTeamMessageDTO,
  type CareTeamStatus,
} from "@/services/triage.service";

/**
 * ============================================================================
 * [CARE TEAM DOCK] KÊNH TRAO ĐỔI TRỰC TIẾP VỚI NHÂN VIÊN Y TẾ
 * ============================================================================
 * Kênh này **luôn hiện diện** trong suốt phiên khám, kể cả khi chưa ai tiếp
 * nhận ca. Ẩn nó đi cho tới lúc có người trực là một lỗi thiết kế: người bệnh
 * sẽ không bao giờ biết mình có thể nhắn cho nhân viên y tế.
 *
 * Đổi lại, trạng thái phải trung thực. Ô nhập chỉ mở khi thực sự có một người
 * đang phụ trách ca; những lúc khác nó nói rõ vì sao chưa nhắn được và chỉ
 * đường tới 115 nếu tình huống gấp. Hứa hẹn có người trả lời trong khi không ai
 * đang nghe còn nguy hiểm hơn là không có kênh nào.
 */

interface CareTeamCopy {
  label: string;
  detail: string;
  /** Câu thay cho ô nhập khi kênh chưa mở. */
  closedNote: string | null;
  chip: string;
  dot: string;
}

const CARE_TEAM_COPY: Record<CareTeamStatus, CareTeamCopy> = {
  AI_SCREENING: {
    label: "Trợ lý AI đang sàng lọc",
    detail:
      "Bạn nhắn được ngay bây giờ. Tin sẽ vào hộp thư của trạm trực và nhân viên y tế sẽ trả lời.",
    closedNote: null,
    chip: "border-slate-300 bg-muted text-slate-700 dark:text-slate-200 dark:border-slate-700",
    dot: "bg-slate-400",
  },
  WAITING_REVIEW: {
    label: "Đang chờ nhân viên y tế",
    detail:
      "Hồ sơ của bạn đã vào hàng đợi lâm sàng. Bạn cứ nhắn, trạm trực sẽ thấy ngay.",
    closedNote: null,
    chip: "border-amber-300 bg-amber-100 text-amber-900",
    dot: "bg-amber-500",
  },
  STAFF_REVIEWING: {
    label: "Nhân viên y tế đang hỗ trợ bạn",
    detail: "Bạn có thể nhắn trực tiếp cho người đang phụ trách ca này.",
    closedNote: null,
    chip: "border-teal-300 bg-teal-100 text-teal-900",
    dot: "bg-teal-500",
  },
  SPECIALIST_REVIEW: {
    label: "Đã chuyển bác sĩ",
    detail:
      "Ca của bạn đã được chuyển đến bác sĩ để tiếp tục đánh giá. Bạn vẫn nhắn được tại đây.",
    closedNote: null,
    chip: "border-sky-300 bg-sky-100 text-sky-900",
    dot: "bg-sky-500",
  },
  COMPLETED: {
    label: "Đã hoàn tất đánh giá",
    detail: "Bạn vẫn đọc lại được toàn bộ nội dung đã trao đổi.",
    closedNote: "Ca đã hoàn tất nên kênh trao đổi được đóng lại.",
    chip: "border-emerald-300 bg-emerald-100 text-emerald-900",
    dot: "bg-emerald-500",
  },
};

function formatTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function MessageBubble({ message }: { message: CareTeamMessageDTO }) {
  const fromStaff = message.sender === "staff";
  return (
    <li className={cn("flex flex-col gap-1", fromStaff ? "items-start" : "items-end")}>
      <span className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
        {fromStaff ? (
          <>
            <Stethoscope className="size-3.5 text-teal-600" aria-hidden="true" />
            {message.senderName ?? "Nhân viên y tế"}
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

      <time dateTime={message.createdAt} className="text-xs text-slate-400">
        {formatTime(message.createdAt)}
      </time>
    </li>
  );
}

interface CareTeamDockProps {
  sessionId: string;
}

export function CareTeamDock({ sessionId }: CareTeamDockProps) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const listRef = useRef<HTMLOListElement>(null);
  const queryClient = useQueryClient();

  const thread = useQuery({
    queryKey: TRIAGE_QUERY_KEYS.careTeam(sessionId),
    queryFn: () => triageService.getCareTeamThread(sessionId),
    enabled: Boolean(sessionId),
    // WebSocket là nguồn đánh thức chính; nhịp nền chỉ là lưới an toàn khi kênh
    // đang đứt, để một tin của nhân viên y tế không nằm im quá lâu.
    refetchInterval: 20_000,
    staleTime: 2_000,
    retry: 1,
  });

  const refresh = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: TRIAGE_QUERY_KEYS.careTeam(sessionId) });
    void queryClient.invalidateQueries({ queryKey: TRIAGE_QUERY_KEYS.messages(sessionId) });
    void queryClient.invalidateQueries({ queryKey: TRIAGE_QUERY_KEYS.history() });
  }, [queryClient, sessionId]);

  const handleRealtimeEvent = useCallback(
    (event: ClinicalRealtimeEvent) => {
      refresh();
      // Tin mới của nhân viên y tế tự bật kênh lên. Người bệnh đang mệt không
      // nên phải tự đi tìm xem có ai vừa nhắn gì cho mình hay không.
      if (event.event === "message.created" && event.payload?.sender === "NURSE") {
        setOpen(true);
      }
    },
    [refresh],
  );

  const { status: socketStatus } = useClinicalSocket({
    path: sessionId ? `/ws/case/${encodeURIComponent(sessionId)}` : null,
    onEvent: handleRealtimeEvent,
    enabled: Boolean(sessionId),
  });

  const sendMessage = useMutation({
    mutationFn: (content: string) =>
      triageService.sendMessageToStaff(sessionId, content, crypto.randomUUID()),
    onSuccess: () => {
      setDraft("");
      refresh();
    },
  });

  const markRead = useMutation({
    mutationFn: () => triageService.markStaffMessagesRead(sessionId),
    onSuccess: refresh,
  });

  const status: CareTeamStatus = thread.data?.care_team_status ?? "AI_SCREENING";
  const copy = CARE_TEAM_COPY[status] ?? CARE_TEAM_COPY.AI_SCREENING;
  const messages = thread.data?.messages ?? [];
  const unread = thread.data?.unread_from_staff ?? 0;
  // Nhắn được suốt phiên khám. Chỉ khi ca đã đóng sổ thì kênh mới khoá lại:
  // chặn lúc chưa ai nhận ca đồng nghĩa với việc tin không bao giờ tới trạm trực.
  const canMessage = status !== "COMPLETED";

  const markReadMutate = markRead.mutate;
  useEffect(() => {
    if (open && unread > 0) markReadMutate();
  }, [open, unread, markReadMutate]);

  // Tự động mở khung chat nếu vào trang mà có tin nhắn chưa đọc
  useEffect(() => {
    if (unread > 0 && !open) {
      // Giữ hành vi sản phẩm: tin mới của nhân viên phải hiện ngay, không chờ
      // người bệnh phát hiện badge rồi tự mở kênh.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setOpen(true);
    }
  }, [unread, open]);

  useEffect(() => {
    const list = listRef.current;
    if (open && list) list.scrollTop = list.scrollHeight;
  }, [open, messages.length]);

  const handleSend = (event: React.FormEvent) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sendMessage.isPending || !canMessage) return;
    sendMessage.mutate(content);
  };

  // ---------------------------------------------------------------- thu gọn
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={`Mở kênh trao đổi với nhân viên y tế. ${copy.label}.`}
        className={cn(
          "fixed bottom-44 right-4 z-50 flex min-h-14 items-center gap-3 rounded-2xl border bg-card px-4 py-2.5 shadow-lg transition-transform hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 motion-reduce:hover:translate-y-0 sm:right-6",
          // Tải lại trang mà vẫn còn tin chưa đọc thì viên thu gọn phải tự nổi bật.
          unread > 0
            ? "border-teal-400 ring-2 ring-teal-500/40"
            : "border-slate-300 dark:border-slate-700",
        )}
      >
        <span className="relative flex size-10 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white">
          <MessageCircle className="size-5 stroke-[2.2]" aria-hidden="true" />
          {unread > 0 && (
            <span className="absolute -right-1.5 -top-1.5 flex size-5 items-center justify-center rounded-full bg-rose-600 text-xs font-bold text-white">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </span>
        <span className="flex flex-col text-left">
          <span className="text-sm font-bold text-foreground">Nhân viên y tế</span>
          <span className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
            <span className={cn("size-2 rounded-full", copy.dot)} aria-hidden="true" />
            {copy.label}
          </span>
        </span>
      </button>
    );
  }

  // ---------------------------------------------------------------- mở rộng
  return (
    <section
      aria-label="Kênh trao đổi với nhân viên y tế"
      className="fixed inset-x-3 bottom-3 z-50 flex max-h-[70dvh] flex-col overflow-hidden rounded-2xl border border-slate-300 bg-card shadow-2xl sm:inset-x-auto sm:bottom-44 sm:right-6 sm:w-[26rem] dark:border-slate-700"
    >
      <header className="flex items-start justify-between gap-3 border-b border-slate-100 bg-background px-4 py-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white">
            <Stethoscope className="size-5 stroke-[2.2]" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h2 className="text-base font-bold text-foreground">Nhân viên y tế</h2>
            <p className="mt-0.5 flex items-center gap-1.5 text-xs font-semibold">
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5",
                  copy.chip,
                )}
              >
                <span className={cn("size-1.5 rounded-full", copy.dot)} aria-hidden="true" />
                {copy.label}
              </span>
            </p>
            {thread.data?.care_team_name && (
              <p className="mt-1 truncate text-sm font-semibold text-slate-700 dark:text-slate-200">
                {thread.data.care_team_name}
              </p>
            )}
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

      {socketStatus === "reconnecting" && (
        <p
          role="status"
          className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-900"
        >
          <WifiOff className="size-4 shrink-0" aria-hidden="true" />
          Mất kết nối realtime. Đang kết nối lại...
        </p>
      )}

      <ol
        ref={listRef}
        className="flex min-h-[9rem] flex-1 flex-col gap-4 overflow-y-auto px-4 py-4"
      >
        {thread.isLoading ? (
          <li className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            Đang tải kênh trao đổi...
          </li>
        ) : messages.length === 0 ? (
          <li className="rounded-xl border border-border bg-background p-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
            {copy.detail}
          </li>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
      </ol>

      {canMessage ? (
        <form onSubmit={handleSend} className="border-t border-slate-100 bg-background/70 p-3">
          <label htmlFor="care-team-input" className="sr-only">
            Nhắn cho nhân viên y tế
          </label>
          <div className="flex items-end gap-2">
            <textarea
              id="care-team-input"
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
              {sendMessage.error instanceof Error
                ? sendMessage.error.message
                : "Không gửi được tin nhắn."}
            </p>
          )}
        </form>
      ) : (
        <p className="border-t border-slate-100 bg-background/70 p-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
          {copy.closedNote}
        </p>
      )}
    </section>
  );
}

export default CareTeamDock;
