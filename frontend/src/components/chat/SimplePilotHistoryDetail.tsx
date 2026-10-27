"use client";

import Link from "next/link";
import { ArrowLeft, Clock3, FileWarning, Loader2, MessageCircleQuestion, ShieldAlert } from "lucide-react";

import { SimplePilotReplayFeed } from "@/components/chat/SimplePilotReplayFeed";
import {
  pilotAiProposedEsi,
  SimplePilotEsiBadge,
  SimplePilotNurseDecisionSummary,
} from "@/components/chat/SimplePilotNurseDecisionSummary";
import { SimplePilotReviewBadge } from "@/components/chat/SimplePilotReviewBadge";
import { SimplePilotSbarAccordion } from "@/components/chat/SimplePilotSbarAccordion";
import { useSimpleCareTeamRealtime, useSimpleTriageSessionDetail } from "@/queries/useSimpleTriageQueries";
import { isPilotUnavailableError } from "@/services/simple-triage.service";
import type { SimpleTriageMessageRowDTO } from "@/types/simple-triage";
import type { ChatMessage, DecisionStatus } from "@/types/triage-chat";

/**
 * Detail/replay screen for one pilot session, `/triage-pilot/history/[id]`.
 * Reuses `useSimpleTriageSessionDetail` as-is (already built for the active
 * chat page -- one call already returns messages + sbar together, no new
 * hook needed). See `.claude/plans/sunny-launching-mitten.md` for why the
 * message-mapping helper below is a small deliberate duplicate of
 * `triage-pilot/page.tsx`'s own `mapRowToChatMessage` rather than an
 * extraction from that working file.
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

export function SimplePilotHistoryDetail({ sessionId }: { sessionId: string }) {
  const { data, isLoading, isError, error, refetch } = useSimpleTriageSessionDetail(sessionId);
  // A nurse decision only signals this page to re-read persisted data.
  useSimpleCareTeamRealtime(sessionId);

  const is503 = isPilotUnavailableError(error);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-slate-400">
        <Loader2 className="size-8 animate-spin text-sky-600" aria-hidden="true" />
        <span className="font-mono text-sm font-bold uppercase tracking-wider">Đang tải ca khám...</span>
      </div>
    );
  }

  if (isError || !data) {
    if (is503) {
      return (
        <div className="mx-auto flex max-w-lg flex-col items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center">
          <ShieldAlert className="size-10 text-amber-600" aria-hidden="true" />
          <p className="text-sm font-semibold text-amber-950">Triage Agent đang tắt trên môi trường này.</p>
        </div>
      );
    }
    return (
      <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center">
        <p className="text-sm font-semibold text-rose-900">Không thể tải ca khám này.</p>
        <p className="mt-2 text-sm text-rose-800">
          {error instanceof Error ? error.message : "Vui lòng thử lại."}
        </p>
        <button
          type="button"
          onClick={() => void refetch()}
          className="mt-4 mx-auto flex min-h-10 items-center gap-2 rounded-xl border border-rose-300 bg-card px-4 text-sm font-semibold text-rose-800 hover:bg-rose-100"
        >
          Tải lại
        </button>
      </div>
    );
  }

  const isActive = data.status === "ACTIVE";
  const replayMessages = data.messages.map((row) => mapRowToChatMessage(row, sessionId));
  const aiProposedEsi = pilotAiProposedEsi(data.matched_esi_levels);
  const hasNurseDecision =
    data.review_display_status === "APPROVED" || data.review_display_status === "OVERRIDDEN";

  return (
    <div className="space-y-4">
      <Link
        href="/triage-pilot/history"
        className="inline-flex items-center gap-2 text-sm font-semibold text-sky-800 hover:underline"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Quay lại lịch sử khám pilot
      </Link>

      <div className="rounded-2xl border border-border bg-card p-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs font-bold uppercase tracking-wide text-muted-foreground">
            Mã ca: #{data.session_id.slice(-8)}
          </span>
          <span className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
            <Clock3 className="size-3.5" aria-hidden="true" />
            {new Date(data.started_at).toLocaleString("vi-VN")}
          </span>
        </div>
        <h1 className="mt-2 text-xl font-bold text-slate-950 dark:text-slate-50">
          {data.initial_message.trim() || "Chưa có mô tả triệu chứng"}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {isActive ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-xs font-bold text-sky-900">
              <MessageCircleQuestion className="size-3.5" aria-hidden="true" />
              Đang thu thập thông tin
            </span>
          ) : (
            <SimplePilotReviewBadge status={data.review_display_status} />
          )}
          <SimplePilotEsiBadge
            aiProposedEsi={aiProposedEsi}
            finalEsi={data.final_esi}
            reviewStatus={data.review_display_status}
          />
        </div>
        {hasNurseDecision && (
          <div className="mt-4">
            <SimplePilotNurseDecisionSummary
              aiProposedEsi={aiProposedEsi}
              finalEsi={data.final_esi}
              reviewStatus={data.review_display_status}
              reviewerName={data.reviewer_name}
              reviewedAt={data.reviewed_at}
              decisionNote={data.decision_note}
            />
          </div>
        )}
        {isActive && (
          <Link
            href={`/triage-pilot?session_id=${data.session_id}`}
            className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-xl bg-sky-700 px-4 text-sm font-semibold text-white hover:bg-sky-800"
          >
            Tiếp tục ca khám
          </Link>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <SimplePilotReplayFeed messages={replayMessages} />
        </div>
        <div className="space-y-4 lg:col-span-5">
          {data.sbar ? (
            <SimplePilotSbarAccordion sbar={data.sbar} sessionId={data.session_id} />
          ) : (
            <div className="flex flex-col items-center gap-3 rounded-2xl border border-border bg-card p-6 text-center">
              <FileWarning className="size-8 text-slate-400" aria-hidden="true" />
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                {isActive
                  ? "Ca khám chưa hoàn tất nên chưa có bản tóm tắt SBAR."
                  : "Ca khám này chưa có bản tóm tắt SBAR."}
              </p>
              {isActive && (
                <Link
                  href={`/triage-pilot?session_id=${data.session_id}`}
                  className="text-sm font-semibold text-sky-800 hover:underline"
                >
                  Tiếp tục cung cấp thông tin
                </Link>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
