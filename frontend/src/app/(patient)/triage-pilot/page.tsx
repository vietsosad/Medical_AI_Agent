"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { AlertTriangle, FlaskConical, History, Loader2, PhoneCall, RefreshCw, ShieldAlert } from "lucide-react";

import { DisclaimerConsentModal } from "@/components/chat/DisclaimerConsentModal";
import { EmergencyCallHint } from "@/components/chat/EmergencyCallHint";
import { MessageItem } from "@/components/chat/MessageItem";
import { ChatInput } from "@/components/chat/ChatInput";
import { SimpleCareTeamDock } from "@/components/chat/SimpleCareTeamDock";
import { SimplePilotProfileSelector } from "@/components/chat/SimplePilotProfileSelector";
import { SimpleEsiResultCard, isUrgentEsi } from "@/components/chat/SimpleEsiResultCard";
import { NearbyFacilitiesCard } from "@/components/chat/NearbyFacilitiesCard";
import { SimpleMatchedProtocolsCard } from "@/components/chat/SimpleMatchedProtocolsCard";
import { SimplePilotNurseDecisionSummary } from "@/components/chat/SimplePilotNurseDecisionSummary";
import type { EsiLevel } from "@/types/clinical-history";
import { SimplePilotSbarAccordion } from "@/components/chat/SimplePilotSbarAccordion";
import { SimpleProcessingIndicator } from "@/components/chat/SimpleProcessingIndicator";
import { SimpleTurnErrorCard } from "@/components/chat/SimpleTurnErrorCard";
// Read-only, account-level profile display -- neither component touches
// TriageCase/production triage state, safe to reuse directly (see plan).
import StickyProfileContextBar from "@/components/profile/StickyProfileContextBar";
import { VerifiedClinicalContextHeader } from "@/components/chat/VerifiedClinicalContextHeader";
import {
  useSimpleTriageSessionDetail,
  useStartSimpleTriage,
  useSubmitSimpleTriageChat,
} from "@/queries/useSimpleTriageQueries";
import { isPilotUnavailableError } from "@/services/simple-triage.service";
import type { SimpleTriageMessageRowDTO } from "@/types/simple-triage";
import type { ChatMessage, DecisionStatus } from "@/types/triage-chat";

/**
 * Pilot page for `src/simple_agent`, kept deliberately separate from
 * `/triage` (see `.claude/plans/sunny-launching-mitten.md`): reuses only the
 * presentational leaf components (`MessageItem`, `ChatInput`,
 * `DisclaimerConsentModal`) and talks to the additive `/api/v1/simple-triage/*`
 * routes through `@/services/simple-triage.service`, never touching the
 * production `/api/v1/triage/*` contract or its page.
 *
 * No structured option cards here (see plan for why: `fact_target` enum
 * values are machine codes with no ready Vietnamese label) -- every question
 * is plain text, the patient always types a free-form reply, exactly like
 * `scripts/run_agent.py`'s already-verified CLI flow.
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

// No-op: MessageItem's onSelectAnswer only fires from structured option
// cards, which this pilot page never renders (every message has
// `structured: undefined`).
function noopSelectAnswer() {}

// Purely cosmetic, client-side only -- never sent to or persisted by the
// backend. Production's /triage opens a real session with an empty first
// symptom just to get this same opening line back from the server before
// the patient types anything; simple_agent's /start always requires a real
// first message (the symptom itself doubles as the session-opening turn),
// so there is no equivalent "empty start" call to make here. Showing this
// canned line client-side gets the same "already an active chat" look
// production has, at zero backend risk, until the patient's real first
// message creates the actual session exactly as before.
const PILOT_GREETING_CONTENT = "Chào bạn! Bạn có đang gặp vấn đề sức khỏe nào cần hỗ trợ không?";

export default function TriagePilotPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");

  const sessionQuery = useSimpleTriageSessionDetail(sessionId);
  const startMutation = useStartSimpleTriage();
  const chatMutation = useSubmitSimpleTriageChat();
  // "Đang khám cho ai?" gate, shown once before the first message: undefined
  // = not chosen yet (still showing SimplePilotProfileSelector), null =
  // patient explicitly picked "ẩn danh / người mới". Only affects which EHR
  // profile card's gender/relationship gets attached to /start (see
  // agent.py's _sex_compatible) -- nothing else in the pilot depends on it.
  const [chosenProfileId, setChosenProfileId] = useState<string | null | undefined>(undefined);
  // Optimistic-send + inline failure state, shared by both handleStart
  // (pre-session) and handleSend (active chat): the patient's own message
  // must appear the instant they hit "Gửi", not only once the round trip
  // resolves, and a failure must show up *in the transcript* (not just a
  // corner toast that's easy to miss) with a way to retry the exact same
  // content. pendingOutgoing is cleared on success; kept on failure so the
  // error card renders right under what the patient actually tried to send.
  const [pendingOutgoing, setPendingOutgoing] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  // See PILOT_GREETING_CONTENT above -- computed once per mount, not on
  // every render, so its displayed time doesn't drift while idle.
  const greetingMessage = useMemo<ChatMessage>(
    () => ({
      id: "pilot-greeting",
      sender: "bot",
      timestamp: new Date().toISOString(),
      content: PILOT_GREETING_CONTENT,
      step: 1,
      decisionStatus: null,
    }),
    [],
  );

  const messages = useMemo<ChatMessage[]>(
    () => (sessionQuery.data?.messages ?? []).map((row) => mapRowToChatMessage(row, sessionId ?? "")),
    [sessionQuery.data?.messages, sessionId],
  );

  // Lời chào mở đầu được giữ lại ở đầu hội thoại thay vì biến mất khi phiên
  // được tạo. Mốc thời gian bám theo tin nhắn đầu tiên của máy chủ (chứ không
  // phải "bây giờ"), nếu không mở lại một phiên cũ sẽ thấy lời chào mang giờ
  // hôm nay nằm trên những tin nhắn của hôm trước.
  const transcript = useMemo<ChatMessage[]>(() => {
    if (messages.length === 0) return messages;
    return [{ ...greetingMessage, timestamp: messages[0].timestamp }, ...messages];
  }, [greetingMessage, messages]);

  const isCompleted = sessionQuery.data?.status === "COMPLETED";
  // Single most severe (lowest-numbered) matched level, for the prominent
  // SimpleEsiResultCard below -- same narrowing as agent.py's matched_atoms/
  // sbar.py's citations, kept in sync (2026-08-29 feedback: this card and
  // the outcome message text now consistently reflect only this one level,
  // never the full matched_esi_levels list).
  const rawTopEsiLevel = sessionQuery.data?.matched_esi_levels.length
    ? Math.min(...sessionQuery.data.matched_esi_levels)
    : null;
  const topEsiLevel: EsiLevel | null =
    rawTopEsiLevel !== null && rawTopEsiLevel >= 1 && rawTopEsiLevel <= 5 ? (rawTopEsiLevel as EsiLevel) : null;
  const rawFinalEsi = sessionQuery.data?.final_esi;
  const finalEsiLevel: EsiLevel | null =
    rawFinalEsi != null && rawFinalEsi >= 1 && rawFinalEsi <= 5 ? (rawFinalEsi as EsiLevel) : null;
  const hasNurseDecision =
    sessionQuery.data?.review_display_status === "APPROVED" ||
    sessionQuery.data?.review_display_status === "OVERRIDDEN";
  const displayedEsiLevel = hasNurseDecision && finalEsiLevel !== null ? finalEsiLevel : topEsiLevel;
  const showUrgentCall = isCompleted && displayedEsiLevel !== null && isUrgentEsi(displayedEsiLevel);
  const isSending = chatMutation.isPending;
  const canSubmit = !!sessionId && !isCompleted && !isSending && !sessionQuery.isLoading;
  // Bộ sàng lọc cấp cứu ở backend gắn `safety_alert` vào lượt có dấu hiệu nguy
  // kịch. Tin nhắn đó có thể bị cuộn khuất, nên nút 115 ở lại ngay trên ô nhập
  // cho tới hết phiên -- phiên vẫn tiếp tục, không bị khoá.
  const hasSafetyAlert = useMemo(
    () => (sessionQuery.data?.messages ?? []).some((row) => row.decision_snapshot.safety_alert),
    [sessionQuery.data?.messages],
  );

  const handleStart = async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || chosenProfileId === undefined) return;
    setPendingOutgoing(trimmed);
    setLastError(null);
    try {
      const result = await startMutation.mutateAsync({ message: trimmed, profileId: chosenProfileId });
      setPendingOutgoing(null);
      router.push(`/triage-pilot?session_id=${result.session_id}`);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Khởi tạo phiên sàng lọc thất bại.";
      setLastError(message);
      toast.error(message);
    }
  };

  const handleSend = async (content: string) => {
    const trimmed = content.trim();
    if (!sessionId || !trimmed) return;
    setPendingOutgoing(trimmed);
    setLastError(null);
    try {
      await chatMutation.mutateAsync({ sessionId, message: trimmed });
      setPendingOutgoing(null);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Gửi thông điệp thất bại.";
      setLastError(message);
      toast.error(message);
    }
  };

  const handleRetry = () => {
    if (!pendingOutgoing) return;
    if (sessionId) {
      void handleSend(pendingOutgoing);
    } else {
      void handleStart(pendingOutgoing);
    }
  };

  const handleNewSession = () => {
    window.location.href = "/triage-pilot";
  };

  // `scrollIntoView` tự tìm vùng cuộn gần nhất (chính là khung hội thoại), nên
  // chỉ cần một mốc neo ở cuối danh sách, không cần giữ ref tới container.
  const bottomRef = useRef<HTMLDivElement>(null);
  // Khi phiên đã có kết quả, mốc cuộn là chính thẻ kết quả chứ không phải đáy:
  // bên dưới thẻ còn danh sách cơ sở y tế, tiêu chí phác đồ và SBAR, nên cuộn
  // tới đáy sẽ đẩy mức ESI -- và nút gọi 115 của ESI 1/2 -- ra khỏi tầm mắt.
  const resultRef = useRef<HTMLDivElement>(null);

  // Đưa hội thoại về cuối mỗi khi có nội dung mới. Lần đầu vào phiên thì nhảy
  // thẳng (không cần diễn hoạt cả trang), các lượt sau thì cuộn mượt.
  const hasAutoScrolledRef = useRef(false);
  useEffect(() => {
    if (transcript.length === 0 && !pendingOutgoing && !isSending) return;

    const behavior: ScrollBehavior = hasAutoScrolledRef.current ? "smooth" : "auto";
    hasAutoScrolledRef.current = true;
    // Chờ trình duyệt dựng xong khối vừa thêm rồi mới đo chiều cao.
    const id = window.requestAnimationFrame(() => {
      if (resultRef.current) {
        resultRef.current.scrollIntoView({ behavior, block: "start" });
      } else {
        bottomRef.current?.scrollIntoView({ behavior, block: "end" });
      }
    });
    return () => window.cancelAnimationFrame(id);
  }, [transcript.length, pendingOutgoing, isSending, isCompleted, displayedEsiLevel]);

  // -- Start screen: no session_id yet -------------------------------------
  // Same flex-column + bottom-pinned-input shell as the active chat screen
  // below (not a plain top-to-bottom stack) -- once a profile is chosen,
  // this already looks like an active conversation (context cards + a
  // greeting bubble), with ChatInput anchored to the bottom exactly like a
  // real session, instead of floating wherever it happens to fall after the
  // picker card.
  if (!sessionId) {
    const profileChosen = chosenProfileId !== undefined;
    return (
      <div className="h-full bg-background text-slate-800 flex flex-col rounded-3xl overflow-hidden dark:text-slate-100">
        <DisclaimerConsentModal />

        <div className="min-h-0 flex-1 w-full overflow-y-auto overscroll-contain">
          <div className="max-w-3xl mx-auto p-4 sm:p-6 space-y-4 pb-4">
            <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
              <FlaskConical className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
              <span>
                AI Triage hỗ trợ ghi nhận triệu chứng và sàng lọc mức độ ưu tiên dựa trên thông tin bạn cung cấp. Hãy mô tả đầy đủ, chính xác để
                nhận được gợi ý phù hợp, chủ động theo dõi và trao đổi với nhân viên y tế. Nếu xuất hiện dấu hiệu nguy hiểm hoặc tình trạng xấu đi,
                hãy gọi 115 hoặc đến cơ sở y tế gần nhất.
              </span>
            </div>

            {!profileChosen && (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card p-5">
                  <div>
                    <h1 className="text-lg font-bold text-slate-950 dark:text-slate-50">Bắt đầu phiên sàng lọc</h1>
                    <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                      Mô tả triệu chứng hiện tại của bạn để bắt đầu.
                    </p>
                  </div>
                  <Link
                    href="/triage-pilot/history"
                    className="flex min-h-10 shrink-0 items-center gap-2 rounded-xl border border-slate-300 bg-background px-4 text-sm font-semibold text-slate-800 hover:bg-muted dark:text-slate-100 dark:border-slate-700"
                  >
                    <History className="size-4" aria-hidden="true" />
                    Lịch sử phiên
                  </Link>
                </div>
                <SimplePilotProfileSelector onProfileChosen={setChosenProfileId} />
              </>
            )}

            {profileChosen && (
              <>
                {/* Cùng logic ẩn/hiện với màn chat active bên dưới: bỏ hẳn
                    StickyProfileContextBar khi ẩn danh thay vì truyền null. */}
                {chosenProfileId && <StickyProfileContextBar lockedProfileId={chosenProfileId} />}
                <VerifiedClinicalContextHeader profileId={chosenProfileId ?? null} />
                <MessageItem message={greetingMessage} onSelectAnswer={noopSelectAnswer} disabled />

                {pendingOutgoing && (
                  <MessageItem
                    message={{
                      id: "pending-outgoing",
                      sender: "user",
                      timestamp: new Date().toISOString(),
                      content: pendingOutgoing,
                      step: 2,
                      decisionStatus: null,
                    }}
                    onSelectAnswer={noopSelectAnswer}
                    disabled
                  />
                )}
                {startMutation.isPending && <SimpleProcessingIndicator />}
                {lastError && !startMutation.isPending && (
                  <SimpleTurnErrorCard message={lastError} onRetry={handleRetry} />
                )}
              </>
            )}
          </div>
        </div>

        {profileChosen && (
          <div className="shrink-0 z-10 w-full">
            <ChatInput
              onSendMessage={handleStart}
              isProcessing={startMutation.isPending}
              disabled={startMutation.isPending}
              placeholder="Ví dụ: tôi bị đau bụng từ sáng nay..."
            />
          </div>
        )}
      </div>
    );
  }

  // -- 503: pilot disabled on this environment ----------------------------
  // Người bệnh không bật được cờ nào ở máy chủ, nên màn này không nói về cấu
  // hình -- chỉ nói việc họ làm được ngay bây giờ.
  if (sessionQuery.isError && isPilotUnavailableError(sessionQuery.error)) {
    return (
      <div className="mx-auto flex h-full max-w-lg flex-col items-center justify-center gap-4 p-8 text-center">
        <ShieldAlert className="size-12 text-amber-600" aria-hidden="true" />
        <h1 className="text-xl font-bold text-slate-950 dark:text-slate-50">Dịch vụ sàng lọc AI tạm thời chưa hoạt động</h1>
        <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">
          Bạn vẫn có thể liên hệ trực tiếp cơ sở y tế gần nhất để được thăm khám.
        </p>
        <EmergencyCallHint className="justify-center" />
      </div>
    );
  }

  // -- Chat screen: session_id present -------------------------------------
  return (
    <div className="h-full bg-background text-slate-800 flex flex-col rounded-3xl overflow-hidden dark:text-slate-100">
      <DisclaimerConsentModal />

      <div className="min-h-0 flex-1 w-full overflow-y-auto overscroll-contain">
        <div className="max-w-3xl mx-auto p-4 sm:p-6 space-y-4 pb-4">
          <div className="flex items-center justify-between gap-3 rounded-2xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-200">
              <FlaskConical className="size-4 text-amber-600" aria-hidden="true" />
              Triage Agent — kết quả chưa qua thẩm định của nhân viên y tế
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleNewSession}
                aria-label="Bắt đầu phiên mới"
                className="flex min-h-10 min-w-10 shrink-0 items-center justify-center rounded-xl border border-slate-300 bg-muted text-slate-700 transition-colors hover:bg-slate-200 dark:text-slate-200 dark:hover:bg-slate-700 dark:border-slate-700"
              >
                <RefreshCw className="size-4" aria-hidden="true" />
              </button>
            </div>
          </div>

          {/* "Đang khám cho ai" -- chỉ hiện khi thẻ được chọn (không phải ẩn
              danh, xem SimplePilotProfileSelector): StickyProfileContextBar
              không có trạng thái "ẩn danh" sạch, truyền null sẽ tự fallback
              về hồ sơ chính chủ và hiện nút đổi hồ sơ -- gây hiểu lầm cho
              phiên ẩn danh nên ẩn hẳn thay vì truyền null.
              VerifiedClinicalContextHeader thì luôn hiện được, kể cả ẩn danh
              (tự hiện cảnh báo "chưa đồng bộ hồ sơ" một cách trung thực). */}
          {sessionQuery.data?.profile_id && (
            <StickyProfileContextBar lockedProfileId={sessionQuery.data.profile_id} />
          )}
          <VerifiedClinicalContextHeader profileId={sessionQuery.data?.profile_id ?? null} />

          {sessionQuery.isError && !isPilotUnavailableError(sessionQuery.error) ? (
            <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center">
              <p className="text-sm font-semibold text-rose-900">Không thể tải phiên này.</p>
              <p className="mt-2 text-sm text-rose-800">
                {sessionQuery.error instanceof Error ? sessionQuery.error.message : "Vui lòng thử lại."}
              </p>
              <button
                type="button"
                onClick={() => void sessionQuery.refetch()}
                className="mt-4 flex min-h-11 mx-auto items-center gap-2 rounded-xl border border-rose-300 bg-card px-4 text-sm font-semibold text-rose-800 hover:bg-rose-100"
              >
                <RefreshCw className="size-4" aria-hidden="true" />
                Tải lại
              </button>
              <EmergencyCallHint className="mt-4 justify-center" />
            </div>
          ) : sessionQuery.isLoading ? (
            <div className="flex flex-col items-center gap-3 py-12 text-slate-400">
              <Loader2 className="size-8 animate-spin text-sky-600" aria-hidden="true" />
              <span className="font-mono text-sm font-bold uppercase tracking-wider">
                Đang tải hội thoại...
              </span>
            </div>
          ) : (
            <>
              {transcript.map((msg) => (
                <MessageItem key={msg.id} message={msg} onSelectAnswer={noopSelectAnswer} disabled />
              ))}

              {pendingOutgoing && (
                <MessageItem
                  message={{
                    id: "pending-outgoing",
                    sender: "user",
                    timestamp: new Date().toISOString(),
                    content: pendingOutgoing,
                    step: messages.length + 1,
                    decisionStatus: null,
                  }}
                  onSelectAnswer={noopSelectAnswer}
                  disabled
                />
              )}
            </>
          )}

          {isSending && <SimpleProcessingIndicator />}
          {lastError && !isSending && <SimpleTurnErrorCard message={lastError} onRetry={handleRetry} />}

          {/* Khung nổi bật riêng cho kết quả ESI, ngay sau tin nhắn cuối cùng của
              chatbot -- phản hồi trực tiếp yêu cầu "phải làm nổi bật là ESI2"
              thay vì chỉ có 1 câu chữ chìm trong khối cảnh báo bên dưới. */}
          {isCompleted && displayedEsiLevel !== null && (
            <div ref={resultRef} className="scroll-mt-4">
              <SimpleEsiResultCard esiLevel={displayedEsiLevel} />
            </div>
          )}

          {/* Tìm cơ sở y tế gần nhất. Chỉ là phần hiển thị thêm bên dưới kết
              quả: nó đọc đúng `displayedEsiLevel` mà backend đã chốt ở trên và
              tự ẩn với mọi mức không khẩn (ESI 4/5) hoặc khi chưa có mức nào --
              xem NearbyFacilitiesCard. Không có nhánh nào ở đây chạm vào trạng
              thái phiên hay vào kết luận lâm sàng. */}
          {isCompleted && <NearbyFacilitiesCard esiLevel={displayedEsiLevel} />}

          {isCompleted && !hasNurseDecision && (
            <div className="flex items-start gap-3 rounded-2xl border-2 border-amber-300 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
              <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
              <p className="font-bold">
                Đây là gợi ý sơ bộ từ AI, CHƯA qua thẩm định của nhân viên y tế. Vui lòng đến cơ sở y tế để
                được thăm khám và phân loại chính thức.
              </p>
            </div>
          )}

          {isCompleted && sessionQuery.data && (
            <SimplePilotNurseDecisionSummary
              aiProposedEsi={topEsiLevel}
              finalEsi={finalEsiLevel}
              reviewStatus={sessionQuery.data.review_display_status}
              reviewerName={sessionQuery.data.reviewer_name}
              reviewedAt={sessionQuery.data.reviewed_at}
              decisionNote={sessionQuery.data.decision_note}
            />
          )}

          {isCompleted && (
            <SimpleMatchedProtocolsCard
              matchedAtoms={sessionQuery.data?.messages.at(-1)?.decision_snapshot.matched_atoms ?? []}
            />
          )}

          {isCompleted && sessionQuery.data?.sbar && (
            <SimplePilotSbarAccordion sbar={sessionQuery.data.sbar} sessionId={sessionId} />
          )}

          {/* Mốc neo để tự cuộn xuống đáy sau mỗi lượt (xem effect ở trên). */}
          <div ref={bottomRef} aria-hidden="true" className="h-px w-full" />
        </div>
      </div>

      {!isCompleted && (
        <div className="shrink-0 z-10 w-full">
          {hasSafetyAlert && (
            <div className="border-t border-rose-300 bg-rose-50 px-4 py-2 dark:border-rose-900 dark:bg-rose-950/40">
              <EmergencyCallHint className="mx-auto max-w-3xl justify-center" />
            </div>
          )}
          <ChatInput
            key={sessionId}
            onSendMessage={handleSend}
            isProcessing={isSending}
            disabled={!canSubmit}
          />
        </div>
      )}

      {/* Thanh ghim đáy luôn trong tầm mắt, kể cả khi người bệnh cuộn đọc SBAR.
          Với ESI 1/2, hành động chính ở đây là gọi 115 -- "Bắt đầu phiên mới"
          lùi xuống làm lựa chọn phụ. Mức hiển thị là mức điều dưỡng đã chốt
          nếu có, nên khi điều dưỡng hạ mức thì nút 115 cũng rút đi. */}
      {isCompleted && (
        <div className="shrink-0 z-10 flex flex-col items-stretch gap-2 border-t border-border bg-card p-4 sm:flex-row sm:justify-center">
          {showUrgentCall && (
            <a
              href="tel:115"
              aria-label="Gọi Tổng đài Cấp cứu Quốc gia 115"
              className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-rose-700 px-6 text-base font-black text-white transition-colors hover:bg-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
            >
              <PhoneCall className="size-5 shrink-0" aria-hidden="true" />
              Gọi 115
            </a>
          )}
          <button
            type="button"
            onClick={handleNewSession}
            className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-background px-4 text-sm font-semibold text-slate-800 hover:bg-muted dark:text-slate-100 dark:border-slate-700"
          >
            <RefreshCw className="size-4" aria-hidden="true" />
            Bắt đầu phiên mới
          </button>
        </div>
      )}

      {/* Chỉ mở kênh nhắn tin sau khi phiên đã COMPLETED -- trước đó chưa có
          review row nào để y tá theo dõi, khớp điều kiện phía backend. */}
      {isCompleted && sessionId && (
        <SimpleCareTeamDock sessionId={sessionId} initialOpen={searchParams.get("openChat") === "1"} />
      )}
    </div>
  );
}
