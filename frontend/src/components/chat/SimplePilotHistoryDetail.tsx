"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion, type Variants } from "framer-motion";
import { ArrowLeft, ChevronRight, CirclePause, Clock3, PhoneCall, Plus } from "lucide-react";

import { NearbyFacilitiesCard } from "@/components/chat/NearbyFacilitiesCard";
import { SimpleCareTeamDock } from "@/components/chat/SimpleCareTeamDock";
import { SimpleEsiResultCard } from "@/components/chat/SimpleEsiResultCard";
import { SimpleMatchedProtocolsCard } from "@/components/chat/SimpleMatchedProtocolsCard";
import { SimplePilotNurseDecisionSummary } from "@/components/chat/SimplePilotNurseDecisionSummary";
import { SimplePilotReplayFeed } from "@/components/chat/SimplePilotReplayFeed";
import { SimplePilotReviewBadge } from "@/components/chat/SimplePilotReviewBadge";
import { SimplePilotSbarAccordion } from "@/components/chat/SimplePilotSbarAccordion";
import { EsiTile } from "@/components/patient/EsiTile";
import { continueSessionHref, sessionMessage } from "@/components/patient/HistorySessionCard";
import {
  aiProposedEsiOf,
  displayedEsiOf,
  formatDateTime,
  formatSubject,
  hasNurseDecision,
  parseDate,
  sessionStatusKind,
  subjectLabelFor,
} from "@/components/patient/history-model";
import { dropVariants, enterTransition, staggerDelay } from "@/lib/motion";
import { useGetProfiles } from "@/queries/useProfileQueries";
import { useSimpleCareTeamRealtime, useSimpleTriageSessionDetail } from "@/queries/useSimpleTriageQueries";
import { isPilotUnavailableError } from "@/services/simple-triage.service";
import type { EsiLevel } from "@/types/clinical-history";
import type { SimpleTriageMessageRowDTO, SimpleTriageSessionDetailDTO } from "@/types/simple-triage";
import type { ChatMessage, DecisionStatus } from "@/types/triage-chat";

/**
 * Detail/replay screen for one pilot session, `/triage-pilot/history/[id]`,
 * laid out like the chat's own result screen: the ESI the patient should act
 * on first (the nurse's level once decided, else the AI proposal), then where
 * the review stands, the matched protocol criteria, nearby facilities for
 * urgent levels, the SBAR summary, and the read-only transcript replay.
 * Every result block is the same component the chat page renders, used as-is.
 *
 * Reuses `useSimpleTriageSessionDetail` as-is (one call returns messages +
 * sbar together). The message-mapping helper below is a small deliberate
 * duplicate of `triage-pilot/page.tsx`'s own `mapRowToChatMessage` rather
 * than an extraction from that file.
 */

const ACTION_TO_DECISION_STATUS: Record<string, DecisionStatus> = {
  ASK_CLARIFICATION: "NEEDS_CLARIFICATION",
  ASK_CONFIRMATION: "AWAITING_PATIENT_CONFIRMATION",
  RETURN_MATCH: "PROPOSED",
  RETURN_INCOMPLETE: "INSUFFICIENT_EVIDENCE",
};

function mapRowToChatMessage(row: SimpleTriageMessageRowDTO, sessionId: string): ChatMessage {
  const isPatient = row.sender === "PATIENT";
  return {
    id: `${sessionId}-${row.turn_index}-${row.sender}`,
    sender: isPatient ? "user" : row.route === "GUARDRAIL" ? "system_shield" : "bot",
    timestamp: row.created_at,
    content: row.content,
    step: row.turn_index + 1,
    decisionStatus: !isPatient && row.action ? ACTION_TO_DECISION_STATUS[row.action] ?? null : null,
  };
}

/** Tiêu chí phác đồ của lượt chốt kết quả (RETURN_MATCH), như màn hội thoại hiển thị. */
function matchedAtomsOf(data: SimpleTriageSessionDetailDTO) {
  const matchRow = [...data.messages]
    .reverse()
    .find((row) => row.sender === "AGENT" && row.action === "RETURN_MATCH");
  return matchRow?.decision_snapshot.matched_atoms ?? [];
}

/**
 * Thẻ kết quả tự trượt vào (SimpleEsiResultCard); các phần bổ trợ nổi lên lần
 * lượt sau nó, đúng nhịp màn hội thoại, không cùng lúc với thẻ.
 */
const supportBlockVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: { ...enterTransition, delay: 0.12 + staggerDelay(index) },
  }),
};

function toEsiLevel(level: number | null): EsiLevel | null {
  return level !== null && level >= 1 && level <= 5 ? (level as EsiLevel) : null;
}

const BACK_LINK =
  "-ml-2 inline-flex min-h-11 items-center gap-2 rounded-xl px-2 text-sm font-semibold text-brand transition-colors hover:text-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand";

function BackToHistory() {
  return (
    <Link href="/triage-pilot/history" className={BACK_LINK}>
      <ArrowLeft className="size-4" aria-hidden="true" />
      Lịch sử sàng lọc
    </Link>
  );
}

function DetailSkeleton() {
  return (
    <div aria-busy="true" aria-label="Đang tải phiên sàng lọc" className="space-y-6">
      <div className="space-y-2">
        <div className="h-8 w-56 rounded-xl bg-muted" />
        <div className="h-4 w-40 rounded-lg bg-muted" />
      </div>
      {[0, 1].map((item) => (
        <div
          key={item}
          className="skeleton-sweep relative h-32 overflow-hidden rounded-2xl border border-border bg-card"
        />
      ))}
    </div>
  );
}

/** Chưa có mức nào để làm theo: nói thẳng là chưa có, không tô màu khẩn cấp. */
function NoProposalCard({ insufficient }: { insufficient: boolean }) {
  return (
    <motion.div
      variants={dropVariants}
      initial="hidden"
      animate="visible"
      className="flex items-start gap-4 rounded-2xl border border-border bg-card p-4 shadow-xs sm:p-6"
    >
      <EsiTile level={null} />
      <div className="min-w-0 space-y-2">
        <p className="text-base font-bold text-foreground">Chưa có mức ưu tiên đề xuất</p>
        <p className="text-sm leading-6 text-muted-foreground">
          {insufficient
            ? "Thông tin trong phiên chưa đủ để đối chiếu với tiêu chí phác đồ, nên hệ thống không tự đặt mức ESI."
            : "Phiên này kết thúc mà không có mức ESI nào được đề xuất."}
        </p>
      </div>
    </motion.div>
  );
}

/**
 * Ứng với hàng "Đang chờ điều dưỡng xác nhận" trên bảng thiết kế. Lời nhắc
 * "đây là đề xuất của AI, không phải chẩn đoán" đã nằm trong thẻ kết quả nên
 * không lặp lại ở đây.
 */
function PendingReviewNotice() {
  return (
    <div className="flex items-start gap-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
      <Clock3 className="mt-1 size-5 shrink-0 text-amber-700 dark:text-amber-300" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-base font-bold leading-7">Đang chờ điều dưỡng xác nhận</p>
        <p className="text-sm leading-6">
          Kết quả chính thức sẽ hiện ở đây khi điều dưỡng xác nhận. Trong lúc chờ, nếu triệu chứng nặng lên, hãy đến
          cơ sở y tế hoặc gọi 115.
        </p>
      </div>
    </div>
  );
}

function ContinueSessionCard({ sessionId, turnCount }: { sessionId: string; turnCount: number }) {
  return (
    <div className="flex items-center gap-4 rounded-2xl bg-slate-900 p-4 text-white shadow-md dark:border dark:border-brand-edge dark:bg-slate-800">
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-2 text-sm font-bold leading-6 text-teal-300">
          <span aria-hidden="true" className="live-dot live-teal size-2 shrink-0 rounded-full bg-teal-400" />
          Đang hỏi dở · {turnCount} lượt hội thoại
        </p>
        <p className="text-base font-bold leading-6">Trả lời tiếp để hoàn tất phiên và nhận mức ưu tiên đề xuất.</p>
      </div>
      <Link
        href={continueSessionHref(sessionId)}
        className="flex min-h-11 shrink-0 items-center gap-2 rounded-xl bg-white px-4 text-sm font-extrabold text-slate-900 transition duration-[180ms] hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 active:scale-[0.97] motion-reduce:transition-none motion-reduce:active:scale-100"
      >
        Tiếp tục
        <ChevronRight className="size-4" aria-hidden="true" />
      </Link>
    </div>
  );
}

export function SimplePilotHistoryDetail({ sessionId }: { sessionId: string }) {
  const searchParams = useSearchParams();
  const { data, isLoading, isError, error, refetch } = useSimpleTriageSessionDetail(sessionId);
  const { data: profiles } = useGetProfiles();
  // A nurse decision only signals this page to re-read persisted data.
  useSimpleCareTeamRealtime(sessionId);

  if (isLoading) {
    return <DetailSkeleton />;
  }

  if (isError || !data) {
    if (isPilotUnavailableError(error)) {
      return (
        <div className="space-y-4">
          <BackToHistory />
          <div className="space-y-4 rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
            <p className="text-base font-bold">Chưa mở được phiên này lúc này.</p>
            <p className="text-sm leading-6">
              {error instanceof Error ? error.message : "Dịch vụ sàng lọc AI tạm thời chưa hoạt động."} Nếu đang có
              dấu hiệu nguy kịch, hãy gọi 115.
            </p>
            <a
              href="tel:115"
              aria-label="Gọi Tổng đài Cấp cứu Quốc gia 115"
              className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-rose-700 px-4 text-sm font-bold text-white transition-colors hover:bg-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
            >
              <PhoneCall className="size-4" aria-hidden="true" />
              Gọi 115
            </a>
          </div>
        </div>
      );
    }
    return (
      <div className="space-y-4">
        <BackToHistory />
        <div
          role="alert"
          className="space-y-4 rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-900 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-100"
        >
          <div>
            <p className="text-base font-bold">Không thể tải phiên sàng lọc này.</p>
            <p className="mt-2 text-sm leading-6">{error instanceof Error ? error.message : "Vui lòng thử lại."}</p>
          </div>
          <button
            type="button"
            onClick={() => void refetch()}
            className="flex min-h-11 items-center gap-2 rounded-xl border border-rose-300 bg-card px-4 text-sm font-semibold text-rose-800 transition-colors hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 dark:border-rose-800 dark:text-rose-200 dark:hover:bg-rose-950"
          >
            Tải lại
          </button>
        </div>
      </div>
    );
  }

  const kind = sessionStatusKind(data);
  const isCompleted = data.status === "COMPLETED";
  const decided = hasNurseDecision(data);
  const aiProposedEsi = aiProposedEsiOf(data);
  const displayedEsi = toEsiLevel(displayedEsiOf(data));
  const finalEsi = toEsiLevel(data.final_esi);
  const replayMessages = data.messages.map((row) => mapRowToChatMessage(row, sessionId));
  const subject = formatSubject(subjectLabelFor(data.profile_id, profiles));
  const startedAt = parseDate(data.started_at);
  const meta = [subject, startedAt ? formatDateTime(startedAt) : null].filter(Boolean).join(" · ");
  const title = kind === "IN_PROGRESS" ? "Phiên đang hỏi dở" : kind === "STOPPED" ? "Phiên đã dừng" : "Kết quả sàng lọc";

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <header className="page-enter space-y-4">
        <BackToHistory />
        <div className="space-y-2">
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">{title}</h1>
          {meta && <p className="text-sm leading-6 text-muted-foreground">{meta}</p>}
          <div className="flex flex-wrap items-center gap-2">
            <SimplePilotReviewBadge kind={kind} aiProposedEsi={aiProposedEsi} />
            <span className="font-mono text-sm text-muted-foreground">Mã ca #{data.session_id.slice(-8)}</span>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
        <section aria-labelledby="session-outcome-heading" className="space-y-4 lg:col-span-7">
          <h2 id="session-outcome-heading" className="sr-only">
            Kết quả và trạng thái thẩm định
          </h2>

          {/* Nhắc lại phiên này nói về chuyện gì, ngay trên kết quả của nó. */}
          <figure className="rounded-2xl border border-border bg-card p-4">
            <figcaption className="text-sm font-semibold text-muted-foreground">Mô tả ban đầu</figcaption>
            <blockquote className="mt-2 text-base leading-7 text-foreground">{sessionMessage(data)}</blockquote>
          </figure>

          {kind === "IN_PROGRESS" && <ContinueSessionCard sessionId={data.session_id} turnCount={data.turn_count} />}

          {kind === "STOPPED" && (
            <div className="flex items-start gap-4 rounded-2xl border border-border bg-card p-4">
              <CirclePause className="mt-1 size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
              <p className="text-sm leading-6 text-muted-foreground">
                Phiên này đã dừng trước khi có kết quả. Bạn có thể bắt đầu một phiên mới nếu vẫn còn triệu chứng.
              </p>
            </div>
          )}

          {isCompleted && (
            <>
              {/* Cùng thứ tự với màn hội thoại: mức cần làm theo, nơi cần đến (ESI
                  1-3), ai đã/chưa xác nhận, vì sao ra mức đó, rồi bản SBAR. */}
              {displayedEsi !== null ? (
                <SimpleEsiResultCard
                  esiLevel={displayedEsi}
                  source={decided && finalEsi !== null ? "NURSE" : "AI"}
                />
              ) : (
                <NoProposalCard insufficient={data.final_action === "RETURN_INCOMPLETE"} />
              )}

              {[
                { key: "nearby", node: <NearbyFacilitiesCard esiLevel={displayedEsi} /> },
                {
                  key: "review",
                  node: decided ? (
                    <SimplePilotNurseDecisionSummary
                      aiProposedEsi={aiProposedEsi}
                      finalEsi={finalEsi}
                      reviewStatus={data.review_display_status}
                      reviewerName={data.reviewer_name}
                      reviewedAt={data.reviewed_at}
                      decisionNote={data.decision_note}
                    />
                  ) : (
                    <PendingReviewNotice />
                  ),
                },
                { key: "criteria", node: <SimpleMatchedProtocolsCard matchedAtoms={matchedAtomsOf(data)} /> },
                {
                  key: "sbar",
                  node: data.sbar ? (
                    <SimplePilotSbarAccordion sbar={data.sbar} sessionId={data.session_id} />
                  ) : (
                    <p className="rounded-2xl border border-dashed border-border bg-card p-4 text-sm leading-6 text-muted-foreground">
                      Phiên này chưa có bản tóm tắt SBAR.
                    </p>
                  ),
                },
              ].map(({ key, node }, index) => (
                // Khối nào tự ẩn (ví dụ cơ sở y tế với ESI 4-5) thì vỏ rỗng cũng ẩn theo.
                <motion.div
                  key={key}
                  custom={index}
                  variants={supportBlockVariants}
                  initial="hidden"
                  animate="visible"
                  className="empty:hidden"
                >
                  {node}
                </motion.div>
              ))}
            </>
          )}

          {kind !== "IN_PROGRESS" && (
            <Link
              href="/triage-pilot"
              className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-border bg-card px-4 text-base font-semibold text-foreground transition duration-[180ms] hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.97] motion-reduce:transition-none motion-reduce:active:scale-100 sm:w-auto sm:px-6"
            >
              <Plus className="size-4" aria-hidden="true" />
              Bắt đầu phiên mới
            </Link>
          )}
        </section>

        <div className="lg:col-span-5">
          <SimplePilotReplayFeed messages={replayMessages} />
        </div>
      </div>

      {/* Kênh nhắn với nhân viên y tế chỉ mở khi phiên đã xong, như màn hội thoại.
          `openChat=1` (từ chip "n tin mới" của danh sách) mở sẵn kênh. */}
      {isCompleted && (
        <SimpleCareTeamDock sessionId={data.session_id} initialOpen={searchParams.get("openChat") === "1"} />
      )}
    </div>
  );
}
