"use client";

import React from "react";
import Link from "next/link";
import {
  AlertCircle,
  ExternalLink,
  Eye,
  Loader2,
  MessageSquare,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  X,
} from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { patientEntryHref } from "@/lib/auth-routing";
import { useHealthTopicDetail } from "@/queries/useHealthTopics";

interface HealthTopicDetailDialogProps {
  slug: string | null;
  isAuthenticated: boolean;
  onClose: () => void;
}

function formatUpdatedDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

interface ListBlockProps {
  title: string;
  items: string[];
  tone: "neutral" | "caution";
  icon: React.ReactNode;
}

function ListBlock({ title, items, tone, icon }: ListBlockProps) {
  if (items.length === 0) return null;

  const cautionTone = tone === "caution";
  return (
    <section
      className={
        cautionTone
          ? "rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/50"
          : "rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900"
      }
    >
      <h3
        className={
          cautionTone
            ? "flex items-center gap-2 text-sm font-bold text-amber-900 dark:text-amber-200"
            : "flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100"
        }
      >
        {icon}
        {title}
      </h3>
      <ul
        className={
          cautionTone
            ? "mt-2.5 list-disc space-y-1.5 pl-5 text-sm leading-6 text-amber-900 marker:text-amber-600 dark:text-amber-100"
            : "mt-2.5 list-disc space-y-1.5 pl-5 text-sm leading-6 text-slate-700 marker:text-slate-400 dark:text-slate-300"
        }
      >
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

/**
 * ============================================================================
 * [HEALTH TOPIC DETAIL] NỘI DUNG ĐẦY ĐỦ CỦA MỘT CHỦ ĐỀ SỨC KHỎE
 * ============================================================================
 * Dùng lại Dialog của design system hiện có thay vì dựng một trang riêng, nên
 * người đọc không rời khỏi trang chủ. Khách chưa đăng nhập vẫn xem được toàn bộ
 * nội dung; chỉ nút "Kiểm tra triệu chứng với AI" mới đi qua luồng đăng nhập.
 */
export function HealthTopicDetailDialog({
  slug,
  isAuthenticated,
  onClose,
}: HealthTopicDetailDialogProps) {
  const { data: topic, isLoading, isError } = useHealthTopicDetail(slug);

  return (
    <Dialog open={slug !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        hideCloseButton
        overlayClassName="bg-slate-950/55 backdrop-blur-sm"
        className="max-h-[calc(100dvh-32px)] max-w-2xl gap-0 overflow-y-auto rounded-2xl border-slate-200 bg-white p-0 text-slate-800 shadow-xl dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
      >
        <DialogHeader className="flex-row items-start justify-between gap-3 space-y-0 border-b border-slate-100 bg-slate-50/80 p-6 text-left dark:border-slate-800 dark:bg-slate-900">
          <div className="flex min-w-0 items-start gap-3">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-teal-100 bg-teal-50 text-teal-700 dark:border-teal-900 dark:bg-teal-950 dark:text-teal-300">
              <Stethoscope className="size-5 stroke-[2.2]" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <DialogTitle className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
                {topic?.name ?? "Thông tin sức khỏe"}
              </DialogTitle>
              <DialogDescription className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
                {topic?.summary ?? "Đang tải nội dung chủ đề..."}
              </DialogDescription>
              {topic?.ai_assisted && (
                <span className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  <Sparkles className="size-3.5" aria-hidden="true" />
                  Tóm tắt do AI diễn giải từ nguồn được trích dẫn
                </span>
              )}
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng nội dung chủ đề sức khỏe"
            className="flex size-11 shrink-0 items-center justify-center rounded-xl text-slate-500 transition-colors hover:bg-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 dark:hover:bg-slate-800"
          >
            <X className="size-5" aria-hidden="true" />
          </button>
        </DialogHeader>

        <div className="space-y-4 p-6">
          {isLoading ? (
            <div
              role="status"
              aria-live="polite"
              className="flex items-center justify-center gap-3 py-12 text-sm font-medium text-slate-500"
            >
              <Loader2 className="size-5 animate-spin" aria-hidden="true" />
              Đang tải nội dung chủ đề...
            </div>
          ) : isError || !topic ? (
            <div
              role="alert"
              className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm font-medium text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"
            >
              <AlertCircle className="size-5 shrink-0" aria-hidden="true" />
              Không thể tải nội dung chủ đề này lúc này.
            </div>
          ) : (
            <>
              <ListBlock
                title="Triệu chứng thường gặp"
                items={topic.symptoms}
                tone="neutral"
                icon={<Stethoscope className="size-4 shrink-0" aria-hidden="true" />}
              />

              <ListBlock
                title="Dấu hiệu cần chú ý"
                items={topic.warning_signs}
                tone="caution"
                icon={<ShieldAlert className="size-4 shrink-0" aria-hidden="true" />}
              />

              <ListBlock
                title="Cách phòng ngừa"
                items={topic.prevention}
                tone="neutral"
                icon={<ShieldCheck className="size-4 shrink-0" aria-hidden="true" />}
              />

              {topic.when_to_seek_care && (
                <section className="rounded-xl border border-teal-200 bg-teal-50 p-4 dark:border-teal-800 dark:bg-teal-950/50">
                  <h3 className="flex items-center gap-2 text-sm font-bold text-teal-900 dark:text-teal-200">
                    <Eye className="size-4 shrink-0" aria-hidden="true" />
                    Khi nào nên đi khám
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-teal-900 dark:text-teal-100">
                    {topic.when_to_seek_care}
                  </p>
                </section>
              )}

              <p className="flex items-start gap-2.5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                <ShieldCheck
                  className="mt-0.5 size-5 shrink-0 text-emerald-600 dark:text-emerald-400"
                  aria-hidden="true"
                />
                {topic.disclaimer}
              </p>

              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
                <a
                  href={topic.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex min-h-11 items-center gap-1.5 font-semibold text-slate-700 underline underline-offset-4 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 dark:text-slate-200 dark:hover:text-white"
                >
                  Nguồn: {topic.source}
                  <ExternalLink className="size-3.5 shrink-0" aria-hidden="true" />
                </a>
                <span>Cập nhật {formatUpdatedDate(topic.last_updated)}</span>
              </div>

              <Link
                href={patientEntryHref(
                  `/triage?health_topic=${encodeURIComponent(topic.slug)}`,
                  isAuthenticated,
                )}
                onClick={onClose}
                className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-teal-600 px-5 text-base font-bold text-white transition-colors hover:bg-teal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
              >
                <MessageSquare className="size-5 shrink-0" aria-hidden="true" />
                Kiểm tra triệu chứng với AI
              </Link>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default HealthTopicDetailDialog;
