"use client";

import React, { useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useTriageStore } from "@/store/useTriageStore";
import { DisclaimerConsentModal } from "@/components/chat/DisclaimerConsentModal";
import { VerifiedClinicalContextHeader } from "@/components/chat/VerifiedClinicalContextHeader";
import StickyProfileContextBar from "@/components/profile/StickyProfileContextBar";
import { IntakeStepper } from "@/components/chat/IntakeStepper";
import { AgentActivityCard } from "@/components/chat/AgentActivityCard";
import { PatientIntakeReviewCard } from "@/components/chat/PatientIntakeReviewCard";
import { MessageItem } from "@/components/chat/MessageItem";
import { ChatInput } from "@/components/chat/ChatInput";
import { EmergencyFloatingButton } from "@/components/chat/EmergencyFloatingButton";
import { CareTeamDock } from "@/components/chat/CareTeamDock";
import { RedFlagAlertCard } from "@/components/chat/RedFlagAlertCard";
import { HitlWaitingRoom } from "@/components/chat/HitlWaitingRoom";
import { HitlSignatureBadge } from "@/components/history/HitlSignatureBadge";
import { VerifiedRecommendationCard } from "@/components/chat/VerifiedRecommendationCard";
import { SbarSummaryAccordion } from "@/components/chat/SbarSummaryAccordion";
import { TriageProfileSelector } from "@/components/chat/TriageProfileSelector";
import { Activity, BookOpen, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { IS_PILOT_AGENT_ACTIVE } from "@/lib/agent-mode";
import { useGetSessionMessages, useSubmitChatTurn, useStartTriage } from "@/queries/useTriageQueries";
import { SbarReportSchema } from "@/lib/validations/clinical-history.schema";
import type { AgentStreamEvent, ChatMessage, WorkflowPhase } from "@/types/triage-chat";
import type { EsiLevel, HitlSignatureDTO } from "@/types/clinical-history";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";
import {
  deriveHitlUiStatus,
  isFinalizedSbar,
  isSessionWritable,
  latestActionableQuestionId,
} from "@/lib/triage-ui-state";

/**
 * Danh tính của một sự kiện khẩn cấp, dùng để tránh bật lại thẻ cảnh báo mà
 * người bệnh đã đóng. Mức ESI thay đổi (ví dụ 2 -> 1) tạo ra một sự kiện mới
 * nghiêm trọng hơn nên được phép hiển thị cảnh báo mới.
 */
function emergencyAlertKey(sessionId: string, esiLevel: number | null | undefined): string {
  return `${sessionId}:${esiLevel ?? "unknown"}`;
}

export default function TriagePage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");
  // Chủ đề người dùng vừa đọc ở mục "Thông tin sức khỏe đáng chú ý" trên trang chủ.
  // Chỉ dùng để mở lời chào cho tự nhiên, không phải một triệu chứng được khai báo.
  const healthTopic = searchParams.get("health_topic");
  const router = useRouter();

  // Lưới an toàn: chỉ chuyển hướng khi CHƯA có session_id (bắt đầu ca mới) --
  // 1 ca production đang khám dở (có session_id thật) không bao giờ bị đụng
  // tới, vì dữ liệu đó chỉ tồn tại ở bảng TriageCase. Xem @/lib/agent-mode.
  useEffect(() => {
    if (IS_PILOT_AGENT_ACTIVE && !sessionId) {
      router.replace("/triage-pilot");
    }
  }, [sessionId, router]);

  const [agentActivity, setAgentActivity] = useState<{
    sessionId: string;
    event: AgentStreamEvent;
  } | null>(null);
  const agentEvent =
    agentActivity?.sessionId === sessionId ? agentActivity.event : null;

  const {
    isChatLocked: isLocallyLocked,
    redFlagTriggered,
    triggerRedFlag,
    resetSession,
  } = useTriageStore();

  const {
    data: sessionData,
    error: messagesError,
    isError: isMessagesError,
    isLoading: isLoadingMessages,
    refetch: refetchMessages,
  } = useGetSessionMessages(sessionId);
  const submitChatMutation = useSubmitChatTurn();
  const startTriageMutation = useStartTriage();
  const setActiveProfileId = useActiveProfileStore((state) => state.setActiveProfileId);
  const messages = sessionData?.messages ?? [];
  const sessionStatus = sessionData?.session_status;
  const hitlStatus = deriveHitlUiStatus(sessionStatus);
  const persistedEsi = sessionStatus?.final_esi ?? sessionStatus?.ai_proposed_esi;
  const hasFinalizedEsi =
    sessionStatus?.sbar_finalized === true &&
    persistedEsi != null &&
    [1, 2, 3, 4, 5].includes(persistedEsi);
  const esiResultKey = hasFinalizedEsi ? `${sessionId}:${persistedEsi}` : null;

  const chatScrollRef = useRef<HTMLDivElement>(null);
  const esiResultRef = useRef<HTMLDivElement>(null);
  const displayedEsiResultRef = useRef<string | null>(null);
  const requestAbortRef = useRef<AbortController | null>(null);
  const activeSessionRef = useRef<string | null>(sessionId);
  const previousSessionRef = useRef<string | null>(null);

  useEffect(() => {
    activeSessionRef.current = sessionId;
    requestAbortRef.current?.abort();
    requestAbortRef.current = null;
    resetSession();
    return () => requestAbortRef.current?.abort();
  }, [sessionId, resetSession]);

  useEffect(() => {
    const session = sessionData?.session_status;
    if (!session) return;
    if (session.profile_id) setActiveProfileId(session.profile_id);
    // Cùng một sự kiện khẩn cấp được báo lại sau mỗi lần refetch sẽ không bật lại
    // thẻ cảnh báo mà người bệnh đã đóng; chỉ mức độ cấp cứu mới mới bật thẻ mới.
    if (session.is_red_flag_triggered) {
      triggerRedFlag(emergencyAlertKey(session.session_id, session.final_esi ?? session.ai_proposed_esi));
    }
  }, [sessionData?.session_status, setActiveProfileId, triggerRedFlag]);

  // Chỉ cuộn khung chat. scrollIntoView ở đây sẽ kéo cả page/layout ancestor.
  // Trong màn hình demo/triage, câu hỏi hoặc nhận định mới của agent phải hiện
  // ngay trong vùng nhìn thấy; nếu giữ điều kiện "chỉ cuộn khi đang gần cuối",
  // người bệnh dễ bỏ lỡ câu hỏi tiếp theo sau khi vừa trả lời.
  useEffect(() => {
    const scrollContainer = chatScrollRef.current;
    if (!scrollContainer || isLoadingMessages || isMessagesError) return;

    const sessionChanged = previousSessionRef.current !== sessionId;
    previousSessionRef.current = sessionId;

    const animationFrame = window.requestAnimationFrame(() => {
      // ESI là kết quả quan trọng nhất của phiên. Khi nó vừa xuất hiện (hoặc
      // người bệnh mở lại một phiên đã có kết quả), đặt đầu thẻ vào viewport
      // thay vì kéo xuống cuối SBAR/HITL. Khi đã có ESI, các lần refetch sau đó
      // cũng không được giật màn hình trở lại cuối trang.
      const resultElement = esiResultRef.current;
      if (esiResultKey && resultElement) {
        if (displayedEsiResultRef.current !== esiResultKey) {
          const containerRect = scrollContainer.getBoundingClientRect();
          const resultRect = resultElement.getBoundingClientRect();
          scrollContainer.scrollTo({
            top: scrollContainer.scrollTop + resultRect.top - containerRect.top - 16,
            behavior: sessionChanged ? "auto" : "smooth",
          });
          displayedEsiResultRef.current = esiResultKey;
        }
        return;
      }

      scrollContainer.scrollTo({
        top: scrollContainer.scrollHeight,
        behavior: sessionChanged ? "auto" : "smooth",
      });
    });
    return () => window.cancelAnimationFrame(animationFrame);
  }, [
    hitlStatus,
    agentEvent?.sequence,
    esiResultKey,
    isLoadingMessages,
    isMessagesError,
    submitChatMutation.isPending,
    sessionData?.messages?.length,
    sessionData?.session_status?.intake_confirmation_status,
    sessionData?.session_status?.workflow_phase,
    sessionId,
  ]);

  const handleStartNewSession = async (profileId: string | null) => {
    try {
      const response = await startTriageMutation.mutateAsync({
        profile_id: profileId,
        initial_symptom: "",
        health_topic: healthTopic,
      });
      toast.success("Đã thiết lập Không gian khám Triage an toàn.");
      router.push(`/triage?session_id=${response.session_id}`);
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : "Khởi tạo ca khám thất bại.");
    }
  };

  if (IS_PILOT_AGENT_ACTIVE && !sessionId) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center bg-background p-6">
        <div className="flex items-center gap-3 rounded-xl border border-border bg-card px-5 py-4 text-sm font-medium text-slate-700 dark:text-slate-200">
          <Loader2 className="size-5 animate-spin text-sky-700" aria-hidden="true" />
          Đang chuyển sang Triage Agent...
        </div>
      </div>
    );
  }

  // Nếu KHÔNG có session_id => Hiển thị màn hình Profile Selector
  if (!sessionId) {
    return (
      <div className="h-full w-full bg-background relative selection:bg-sky-100 selection:text-sky-900 font-sans antialiased overflow-x-hidden rounded-3xl">
        <DisclaimerConsentModal />

        {/* Chủ đề mang sang từ trang chủ. Nói rõ đây là mối quan tâm, không phải chẩn đoán. */}
        {healthTopic && (
          <div className="mx-auto mt-4 flex w-full max-w-2xl items-start gap-2.5 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm leading-6 text-teal-900">
            <BookOpen className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span>
              Bạn vừa tìm hiểu một chủ đề sức khỏe trên trang chủ. Việc quan tâm tới chủ đề đó
              không có nghĩa là bạn đang mắc tình trạng này &mdash; hãy mô tả triệu chứng thật của
              bạn để AI sàng lọc chính xác.
            </span>
          </div>
        )}

        <TriageProfileSelector onProfileSelected={handleStartNewSession} />
        
        {/* Loading overlay for start */}
        {startTriageMutation.isPending && (
          <div className="absolute inset-0 bg-card/60 backdrop-blur-[2px] z-50 flex flex-col items-center justify-center gap-3">
             <Loader2 className="w-8 h-8 animate-spin text-sky-600" />
             <span className="font-mono text-sm font-bold text-slate-700 dark:text-slate-200">ĐANG TẠO PHIÊN KHÁM...</span>
          </div>
        )}
      </div>
    );
  }

  const parsedSbar = SbarReportSchema.safeParse(sessionStatus?.sbar_summary);
  const savedSbar =
    parsedSbar.success && isFinalizedSbar(sessionStatus) ? parsedSbar.data : null;
  const finalEsi =
    hasFinalizedEsi
      ? (persistedEsi as EsiLevel)
      : null;
  const nurseDecisionSignature: HitlSignatureDTO | null =
    sessionStatus?.reviewed_at &&
    sessionStatus.decision_type &&
    sessionStatus.ai_proposed_esi != null &&
    sessionStatus.final_esi != null &&
    [1, 2, 3, 4, 5].includes(sessionStatus.ai_proposed_esi) &&
    [1, 2, 3, 4, 5].includes(sessionStatus.final_esi)
      ? {
          reviewer_name: sessionStatus.reviewer_name ?? null,
          review_timestamp: sessionStatus.reviewed_at,
          status: sessionStatus.hitl_status,
          original_esi: sessionStatus.ai_proposed_esi as EsiLevel,
          final_esi: sessionStatus.final_esi as EsiLevel,
          justification_note: sessionStatus.decision_note ?? null,
        }
      : null;
  const requiresPatientConfirmation =
    sessionStatus?.intake_confirmation_status === "AWAITING_CONFIRMATION" &&
    sessionStatus.intake_summary != null;
  const progressPhase: WorkflowPhase | null =
    hitlStatus === "approved" || hitlStatus === "overridden"
      ? "COMPLETE"
      : hitlStatus === "waiting_for_hitl_review"
        ? "HANDOFF"
        : agentEvent?.phase ??
    sessionStatus?.workflow_phase ??
    null;
  const latestQuestionId = latestActionableQuestionId(messages);
  const backendRedFlag = sessionStatus?.is_red_flag_triggered === true;
  // Chỉ dùng để TRÌNH BÀY thẻ cảnh báo. Quyền gửi lượt mới vẫn do trạng thái
  // phiên phía backend quyết định (isSessionWritable + chốt chặn 400 khi phiên
  // đã bị khóa an toàn), không do cờ hiển thị phía client.
  const hasEmergencyAlert = redFlagTriggered || backendRedFlag;
  const sessionWritable = isSessionWritable(sessionStatus);
  const emergencyHandoffClosedSession = backendRedFlag && !sessionWritable;
  const canSubmit =
    !isLoadingMessages &&
    !isMessagesError &&
    sessionWritable &&
    !isLocallyLocked &&
    hitlStatus === "idle" &&
    !submitChatMutation.isPending;

  const handleUserResponse = async (
    messageId?: string,
    answer?: string | string[] | number,
    optionId?: string,
  ) => {
    if (!canSubmit) return;

    const textToCheck = Array.isArray(answer) ? answer.join(" ") : String(answer || "");
    const requestSessionId = sessionId;

    const abortController = new AbortController();
    requestAbortRef.current = abortController;
    try {
      const result = await submitChatMutation.mutateAsync({
        sessionId: requestSessionId,
        payload: {
          message: messageId ? undefined : textToCheck,
          selected_option: messageId ? textToCheck : undefined,
          selected_option_id: messageId ? optionId : undefined,
        },
        answeredMessageId: messageId,
        onProgress: (event) => {
          if (activeSessionRef.current === requestSessionId) {
            setAgentActivity({ sessionId: requestSessionId, event });
          }
        },
        signal: abortController.signal,
      });
      if (activeSessionRef.current !== requestSessionId) return;
      if (result.responseType === "EMERGENCY") {
        triggerRedFlag(emergencyAlertKey(requestSessionId, result.esiLevel));
      }
      setAgentActivity(null);
    } catch (error: unknown) {
      if (activeSessionRef.current !== requestSessionId) return;
      setAgentActivity(null);
      const isAbort =
        !!error && typeof error === "object" && "name" in error && error.name === "AbortError";
      if (!isAbort) {
        toast.error(error instanceof Error ? error.message : "Lỗi khi gửi thông điệp.");
      }
    } finally {
      if (requestAbortRef.current === abortController) {
        requestAbortRef.current = null;
      }
    }
  };

  const handleTextSubmit = (content: string) => {
    handleUserResponse(undefined, content);
  };

  const handleConfirmIntake = async () => {
    if (!canSubmit) return;
    const requestSessionId = sessionId;
    const abortController = new AbortController();
    requestAbortRef.current = abortController;
    try {
      const result = await submitChatMutation.mutateAsync({
        sessionId: requestSessionId,
        payload: {
          confirm_intake: true,
        },
        onProgress: (event) => {
          if (activeSessionRef.current === requestSessionId) {
            setAgentActivity({ sessionId: requestSessionId, event });
          }
        },
        signal: abortController.signal,
      });
      if (activeSessionRef.current !== requestSessionId) return;
      if (result.responseType === "EMERGENCY") {
        triggerRedFlag(emergencyAlertKey(requestSessionId, result.esiLevel));
      }
      setAgentActivity(null);
    } catch (error: unknown) {
      if (activeSessionRef.current !== requestSessionId) return;
      setAgentActivity(null);
      const isAbort =
        !!error && typeof error === "object" && "name" in error && error.name === "AbortError";
      if (!isAbort) {
        toast.error(error instanceof Error ? error.message : "Không thể xác nhận thông tin lúc này.");
      }
    } finally {
      if (requestAbortRef.current === abortController) {
        requestAbortRef.current = null;
      }
    }
  };

  const handleRequestIntakeChanges = async (correction: string) => {
    await handleUserResponse(undefined, correction);
  };

  const handleResetWorkspace = () => {
    resetSession();
    toast.info("Đã khôi phục trạng thái ban đầu của workspace khám lâm sàng AI.");
    window.location.href = "/triage";
  };

  return (
    <div className="h-full bg-background text-slate-800 flex flex-col relative selection:bg-sky-100 selection:text-sky-900 font-sans antialiased overflow-hidden rounded-3xl">
      <DisclaimerConsentModal />

      <div
        ref={chatScrollRef}
        className="min-h-0 flex-1 w-full overflow-y-auto overscroll-contain"
      >
        <div className="max-w-5xl mx-auto p-4 sm:p-6 lg:p-8 space-y-4 pb-4">
        {/* Banner */}
        <div className="bg-card border border-border/90 shadow-2xs rounded-2xl p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all duration-200">
          <div className="flex items-center gap-4">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-sky-600 text-white">
              <Activity className="size-6 stroke-[2.5]" aria-hidden="true" />
            </div>
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight text-slate-950 dark:text-slate-50">
                  Phòng khám AI Triage lâm sàng
                </h1>
                <span className="rounded-lg border border-sky-200 bg-sky-50 px-2 py-2 text-sm font-semibold text-sky-900">
                  Có bước xác nhận của người bệnh
                </span>
              </div>
              <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
                AI thu thập thông tin trước; chỉ bắt đầu phân loại sau khi bạn kiểm tra và xác nhận.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleResetWorkspace}
            aria-label="Bắt đầu phiên khám mới"
            className="flex min-h-12 min-w-12 shrink-0 items-center justify-center rounded-xl border border-slate-300 bg-muted text-slate-700 transition-colors hover:bg-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 dark:text-slate-200 dark:hover:bg-slate-700 dark:border-slate-700"
          >
            <RefreshCw className="size-5" aria-hidden="true" />
          </button>
        </div>

        <StickyProfileContextBar lockedProfileId={sessionStatus?.profile_id} />
        <VerifiedClinicalContextHeader profileId={sessionStatus?.profile_id} />
        <IntakeStepper
          phase={progressPhase}
          intent={agentEvent?.intent}
          isProcessing={submitChatMutation.isPending}
        />

        <main className="pt-2">
          <div className="flex flex-col space-y-3">
            {isMessagesError ? (
              <div
                role="alert"
                className="mx-auto flex w-full max-w-2xl flex-col items-center gap-4 rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center"
              >
                <p className="text-base font-semibold text-rose-900">
                  Không thể tải lịch sử hội thoại của phiên này.
                </p>
                <p className="text-sm leading-6 text-rose-800">
                  {messagesError instanceof Error
                    ? messagesError.message
                    : "Vui lòng kiểm tra kết nối và thử tải lại."}
                </p>
                <button
                  type="button"
                  onClick={() => void refetchMessages()}
                  className="flex min-h-12 items-center gap-2 rounded-xl border border-rose-300 bg-card px-4 text-base font-semibold text-rose-800 hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600"
                >
                  <RefreshCw className="size-5" aria-hidden="true" />
                  Tải lại hội thoại
                </button>
              </div>
            ) : isLoadingMessages ? (
              <div
                role="status"
                aria-live="polite"
                className="py-12 flex justify-center items-center text-slate-400 flex-col gap-3"
              >
                <Loader2 className="w-8 h-8 animate-spin text-sky-600" />
                <span className="font-mono text-sm uppercase tracking-wider font-bold">Đang tải cấu trúc hội thoại...</span>
              </div>
            ) : messages.length === 0 ? (
              <div className="mx-auto w-full max-w-2xl rounded-2xl border border-border bg-card p-6 text-center">
                <p className="text-base font-semibold text-foreground">Phiên này chưa có tin nhắn.</p>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                  Bạn có thể mô tả triệu chứng hiện tại ở ô nhập bên dưới.
                </p>
              </div>
            ) : (
              messages.map((msg: ChatMessage) => (
                <MessageItem
                  key={msg.id}
                  message={msg}
                  onSelectAnswer={handleUserResponse}
                  disabled={
                    !canSubmit ||
                    msg.sender === "user" ||
                    (msg.structured != null && msg.id !== latestQuestionId)
                  }
                />
              ))
            )}

            {submitChatMutation.isPending && (
              <div className="flex justify-start py-2">
                {agentEvent && (
                  <AgentActivityCard
                    event={agentEvent}
                    onCancel={() => requestAbortRef.current?.abort()}
                  />
                )}
              </div>
            )}

            {requiresPatientConfirmation && sessionStatus.intake_summary && (
              <PatientIntakeReviewCard
                summary={sessionStatus.intake_summary}
                isSubmitting={submitChatMutation.isPending}
                onConfirm={handleConfirmIntake}
                onRequestChanges={handleRequestIntakeChanges}
              />
            )}

            {savedSbar && finalEsi && (
              <>
                <div ref={esiResultRef} aria-live="polite">
                  <VerifiedRecommendationCard
                    esiLevel={finalEsi}
                    reviewStatus={sessionStatus?.hitl_status ?? "PENDING_REVIEW"}
                    recommendation={savedSbar.recommendation}
                  />
                </div>
                {nurseDecisionSignature && (
                  <HitlSignatureBadge signature={nurseDecisionSignature} />
                )}
                <SbarSummaryAccordion
                  sessionId={sessionId}
                  sbar={savedSbar}
                  finalized={sessionStatus?.sbar_finalized === true}
                />
              </>
            )}

            {hitlStatus === "waiting_for_hitl_review" && <HitlWaitingRoom />}

            {/* Cảnh báo khẩn cấp nằm trong dòng hội thoại, không che tin nhắn cũ
                và người bệnh có thể đóng lại rồi mở ra khi cần. */}
            {hasEmergencyAlert && <RedFlagAlertCard />}
          </div>
        </main>
        </div>
      </div>

      {/* Kênh trao đổi với nhân viên y tế luôn hiện diện trong suốt phiên khám.
          Ẩn nó cho tới lúc có người trực đồng nghĩa với việc người bệnh không
          bao giờ biết mình có thể nhắn cho nhân viên y tế. */}
      {sessionId && <CareTeamDock sessionId={sessionId} />}

      <EmergencyFloatingButton />

      {/* Static Bottom Area (Not absolute) */}
      {!requiresPatientConfirmation && sessionWritable && hitlStatus === "idle" && (
        <div className="shrink-0 z-40 w-full">
          <ChatInput
            key={sessionId}
            onSendMessage={handleTextSubmit}
            isProcessing={submitChatMutation.isPending}
            disabled={!canSubmit}
          />
        </div>
      )}

      {/* Phiên đã được backend chốt an toàn và chuyển cho nhân viên y tế.
          Không chặn màn hình: hội thoại vẫn đọc được, chỉ ô nhập là đóng. */}
      {emergencyHandoffClosedSession && (
        <div className="shrink-0 z-40 border-t border-rose-200 bg-card">
          <div className="mx-auto flex max-w-5xl flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">
              Phiên khám này đã được chuyển cho nhân viên y tế thẩm định nên không nhận thêm
              câu trả lời. Nếu cần trao đổi tiếp, hãy mở một phiên khám mới.
            </p>
            <button
              type="button"
              onClick={handleResetWorkspace}
              className="flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-background px-4 text-sm font-semibold text-slate-800 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 dark:text-slate-100 dark:border-slate-700"
            >
              <RefreshCw className="size-4" aria-hidden="true" />
              Bắt đầu phiên khám mới
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
