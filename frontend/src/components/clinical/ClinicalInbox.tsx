"use client";

import React, { useState } from "react";
import { Inbox, Loader2, MessageSquareText, ShieldAlert, X } from "lucide-react";

import { useClinicalRealtime } from "@/components/clinical/ClinicalRealtimeProvider";
import { QuickChatDrawer } from "@/components/clinical/nurse/QuickChatDrawer";
import { useClinicalInbox } from "@/hooks/queries/use-clinical-hitl";
import { cn } from "@/lib/utils";
import type { InboxItemDTO } from "@/types/clinical-hitl";

/**
 * ============================================================================
 * [INBOX] TIN NHẮN & HOẠT ĐỘNG MỚI CỦA TRẠM TRỰC
 * ============================================================================
 * Trả lời đúng một câu hỏi: **ngay bây giờ có ai đang chờ mình không, và ai
 * trước?** Nhân viên thấy được việc mà không phải mở từng hồ sơ ra dò.
 *
 * Mỗi dòng chỉ mang một trích ngắn. Hồ sơ đầy đủ, sinh hiệu và danh bạ liên hệ
 * vẫn nằm sau lớp kiểm quyền của từng ca.
 */

function timeAgo(value: string | null): string {
  if (!value) return "";
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds} giây trước`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} giờ trước`;
  return `${Math.floor(hours / 24)} ngày trước`;
}

function InboxRow({ item, onOpen }: { item: InboxItemDTO; onOpen: () => void }) {
  const redFlag = item.priority === "RED_FLAG";
  const urgent = item.priority === "URGENT";

  return (
    <li
      className={cn(
        "border-l-4 bg-card p-4 transition-colors hover:bg-background",
        redFlag ? "border-l-rose-600" : urgent ? "border-l-amber-500" : "border-l-slate-300",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        {redFlag && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-700 px-2.5 py-0.5 text-xs font-bold text-white">
            <ShieldAlert className="size-3.5" aria-hidden="true" />
            Red Flag
          </span>
        )}
        {item.ai_recommended_esi && (
          <span
            className={cn(
              "rounded-full border px-2.5 py-0.5 text-xs font-bold",
              item.ai_recommended_esi <= 2
                ? "border-amber-300 bg-amber-50 text-amber-900"
                : "border-slate-300 bg-muted text-slate-700 dark:text-slate-200 dark:border-slate-700",
            )}
          >
            ESI {item.ai_recommended_esi}
          </span>
        )}
        <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-300 bg-teal-50 px-2.5 py-0.5 text-xs font-bold text-teal-900">
          <MessageSquareText className="size-3.5" aria-hidden="true" />
          {item.unread_count} tin mới
        </span>
      </div>

      <p className="mt-2 text-base font-bold text-slate-950 dark:text-slate-50">
        {item.patient_name}
        <span className="ml-2 text-sm font-medium text-slate-600 dark:text-slate-300">
          {[item.age !== null ? `${item.age} tuổi` : null, item.sex].filter(Boolean).join(" · ")}
        </span>
      </p>

      {item.chief_complaint && (
        <p className="mt-1 truncate text-sm text-slate-600 dark:text-slate-300">{item.chief_complaint}</p>
      )}

      <p className="mt-2 line-clamp-2 rounded-lg bg-background px-3 py-2 text-sm italic leading-6 text-slate-700 dark:text-slate-200">
        “{item.preview}”
      </p>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted-foreground">
          {timeAgo(item.last_message_at)}
          {item.assignee ? ` · ${item.assignee.name} đang phụ trách` : " · chưa có người nhận"}
        </span>
        <button
          type="button"
          onClick={onOpen}
          className="flex min-h-11 items-center gap-2 rounded-xl bg-teal-600 px-4 text-sm font-bold text-white transition-colors hover:bg-teal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
        >
          <MessageSquareText className="size-4" aria-hidden="true" />
          Mở chat
        </button>
      </div>
    </li>
  );
}

export function ClinicalInbox() {
  const [open, setOpen] = useState(false);
  const { quickChatCaseId, openQuickChat, closeQuickChat } = useClinicalRealtime();
  const { data, isLoading, isError } = useClinicalInbox();

  const items = data?.items ?? [];
  const totalUnread = data?.total_unread ?? 0;
  const urgentUnread = data?.urgent_unread ?? 0;

  const activeItem = items.find((item) => item.case_id === quickChatCaseId);

  return (
    <>
      {/* Hộp thư nằm trong thanh Điều phối để luôn dễ tìm mà không che cảnh báo
          Red Flag hoặc hành động của màn hình hiện tại. */}
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={`Tin nhắn và hoạt động mới${totalUnread > 0 ? `, ${totalUnread} chưa đọc` : ""}`}
        title="Tin nhắn và hoạt động mới"
        className={cn(
          "group relative flex min-h-11 w-full items-center gap-3 rounded-xl border bg-card px-3 text-sm font-semibold text-slate-700 transition-colors hover:bg-muted hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 dark:text-slate-200",
          urgentUnread > 0
            ? "border-rose-300 ring-2 ring-rose-500/30"
            : totalUnread > 0
              ? "border-teal-400 ring-2 ring-teal-500/30"
              : "border-slate-300 dark:border-slate-700",
        )}
      >
        <span className="relative">
          <Inbox
            className="size-5 shrink-0 stroke-[2.1] text-muted-foreground group-hover:text-slate-700 dark:group-hover:text-slate-200"
            aria-hidden="true"
          />
          {totalUnread > 0 && (
            <span
              className={cn(
                "absolute -right-2 -top-2 flex size-5 items-center justify-center rounded-full text-xs font-bold text-white",
                urgentUnread > 0 ? "bg-rose-600" : "bg-teal-600",
              )}
            >
              {totalUnread > 9 ? "9+" : totalUnread}
            </span>
          )}
        </span>
        <span className="min-w-0 flex-1 truncate text-left">Tin nhắn mới</span>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-label="Tin nhắn và hoạt động mới">
          <button
            type="button"
            aria-label="Đóng hộp thư"
            onClick={() => setOpen(false)}
            className="flex-1 bg-slate-950/25"
          />

          <section className="flex h-full w-full max-w-md flex-col border-l border-border bg-background shadow-2xl">
            <header className="flex items-start justify-between gap-3 border-b border-border bg-card px-5 py-4">
              <div>
                <h2 className="text-base font-bold text-foreground">Tin nhắn &amp; hoạt động mới</h2>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                  {totalUnread > 0
                    ? `${totalUnread} tin chưa đọc${urgentUnread > 0 ? ` · ${urgentUnread} ở mức ưu tiên cao` : ""}`
                    : "Chưa có tin nào chờ trả lời."}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Đóng"
                className="flex size-11 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500"
              >
                <X className="size-5" aria-hidden="true" />
              </button>
            </header>

            <ol className="flex-1 divide-y divide-slate-200 overflow-y-auto">
              {isLoading ? (
                <li className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  Đang tải hộp thư...
                </li>
              ) : isError ? (
                <li className="p-6 text-sm font-medium text-amber-900">
                  Không tải được hộp thư lúc này.
                </li>
              ) : items.length === 0 ? (
                <li className="p-8 text-center text-sm text-slate-600 dark:text-slate-300">
                  Không có tin nhắn nào của người bệnh đang chờ trả lời.
                </li>
              ) : (
                items.map((item) => (
                  <InboxRow
                    key={item.case_id}
                    item={item}
                    onOpen={() => {
                      openQuickChat(item.case_id);
                      setOpen(false);
                    }}
                  />
                ))
              )}
            </ol>
          </section>
        </div>
      )}

      {quickChatCaseId && (
        <QuickChatDrawer
          caseId={quickChatCaseId}
          patientName={activeItem?.patient_name ?? "Người bệnh"}
          priority={activeItem?.priority}
          onClose={closeQuickChat}
        />
      )}
    </>
  );
}

export default ClinicalInbox;
