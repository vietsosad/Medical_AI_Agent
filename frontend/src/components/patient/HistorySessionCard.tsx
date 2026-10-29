"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight, MessageCircle } from "lucide-react";

import { SimplePilotReviewBadge } from "@/components/chat/SimplePilotReviewBadge";
import { EsiTile } from "@/components/patient/EsiTile";
import { aiProposedEsiOf, displayedEsiOf, sessionStatusKind } from "@/components/patient/history-model";
import { popVariants } from "@/lib/motion";
import type { SimpleTriageSessionSummaryDTO } from "@/types/simple-triage";

type Session = SimpleTriageSessionSummaryDTO;

export function sessionMessage(session: Pick<Session, "initial_message">): string {
  return session.initial_message.trim() || "Chưa có mô tả triệu chứng";
}

export function continueSessionHref(sessionId: string): string {
  return `/triage-pilot?session_id=${encodeURIComponent(sessionId)}`;
}

/**
 * Phiên có tin mới của nhân viên y tế mở thẳng kênh trao đổi (`openChat=1`,
 * cùng cơ chế với chuông thông báo), để chip "n tin mới" dẫn tới đúng tin đó.
 */
export function sessionDetailHref(session: Pick<Session, "session_id" | "unread_from_staff">): string {
  const base = `/triage-pilot/history/${encodeURIComponent(session.session_id)}`;
  return session.unread_from_staff > 0 ? `${base}?openChat=1` : base;
}

interface CardProps {
  session: Session;
  /** "Bạn", "Trần Thị Hoa · cha/mẹ"... null khi hồ sơ còn đang tải. */
  subject: string | null;
  /** Giờ hoạt động gần nhất; ngày đã nằm ở tiêu đề nhóm. */
  timeLabel: string | null;
}

/**
 * Một phiên trong danh sách: ô ESI (mức điều dưỡng đã chốt, hoặc mức AI đề
 * xuất khi chưa có quyết định, "?" khi chưa có mức nào), lời mô tả đầu tiên,
 * phiên dành cho ai và lúc nào, trạng thái thẩm định, số tin mới.
 */
export function HistorySessionCard({ session, subject, timeLabel }: CardProps) {
  const kind = sessionStatusKind(session);
  const esi = displayedEsiOf(session);
  const isInProgress = kind === "IN_PROGRESS";
  const href = isInProgress ? continueSessionHref(session.session_id) : sessionDetailHref(session);
  const noProposalNote =
    esi === null && session.final_action === "RETURN_INCOMPLETE" ? "chưa đủ dữ liệu để đề xuất mức" : null;
  const meta = [subject, timeLabel, noProposalNote].filter(Boolean).join(" · ");
  const unread = session.unread_from_staff;

  return (
    <Link
      href={href}
      className="flex items-start gap-4 rounded-2xl border border-border bg-card p-4 shadow-xs transition duration-[180ms] ease-out hover:-translate-y-0.5 hover:border-brand-edge hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.97] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100"
    >
      {isInProgress ? (
        <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl border border-brand-edge bg-brand-soft text-brand">
          <MessageCircle className="size-6" aria-hidden="true" />
        </span>
      ) : (
        <EsiTile level={esi} />
      )}

      <span className="min-w-0 flex-1">
        <span className="block truncate text-base font-bold leading-6 text-foreground">{sessionMessage(session)}</span>
        {meta && <span className="block text-sm leading-6 text-muted-foreground">{meta}</span>}
        <span className="mt-2 flex flex-wrap items-center gap-2">
          <SimplePilotReviewBadge kind={kind} aiProposedEsi={aiProposedEsiOf(session)} />
          {/* Chỉ hoạt ảnh khi tin mới đến lúc thẻ đã nằm trên màn hình. */}
          <AnimatePresence initial={false}>
            {unread > 0 && (
              <motion.span
                key="unread"
                variants={popVariants}
                initial="hidden"
                animate="visible"
                exit="hidden"
                className="inline-flex items-center gap-2 whitespace-nowrap rounded-2xl bg-brand px-2 text-sm font-bold leading-6 text-brand-foreground"
              >
                <MessageCircle className="size-4 shrink-0" aria-hidden="true" />
                {unread} tin mới
              </motion.span>
            )}
          </AnimatePresence>
        </span>
      </span>
    </Link>
  );
}

/**
 * Phiên đang hỏi dở được ghim trên đầu danh sách, nền tối để tách hẳn khỏi các
 * phiên đã xong: đây là việc duy nhất người bệnh có thể làm tiếp ngay. Chấm
 * xanh nhấp nháy nói rằng phiên vẫn đang mở.
 */
export function InProgressSessionCard({ session, subject, timeLabel }: CardProps) {
  const message = sessionMessage(session);
  const meta = [subject, timeLabel].filter(Boolean).join(" · ");
  const titleId = `in-progress-${session.session_id}`;

  return (
    <article
      aria-labelledby={titleId}
      className="flex items-center gap-4 rounded-2xl bg-slate-900 p-4 text-white shadow-md dark:border dark:border-brand-edge dark:bg-slate-800"
    >
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-2 text-sm font-bold leading-6 text-teal-300">
          <span aria-hidden="true" className="live-dot live-teal size-2 shrink-0 rounded-full bg-teal-400" />
          Đang hỏi dở · {session.turn_count} lượt hội thoại
        </p>
        <h3 id={titleId} className="truncate text-base font-bold leading-6 text-white">
          {message}
        </h3>
        {meta && <p className="text-sm leading-6 text-slate-300">{meta}</p>}
      </div>
      <Link
        href={continueSessionHref(session.session_id)}
        aria-label={`Tiếp tục phiên: ${message}`}
        className="flex min-h-11 shrink-0 items-center gap-2 rounded-xl bg-white px-4 text-sm font-extrabold text-slate-900 transition duration-[180ms] hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 active:scale-[0.97] motion-reduce:transition-none motion-reduce:active:scale-100"
      >
        Tiếp tục
        <ChevronRight className="size-4" aria-hidden="true" />
      </Link>
    </article>
  );
}
