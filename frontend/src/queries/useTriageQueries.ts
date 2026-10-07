import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { triageService, StartTriageRequestDTO, PatientChatInputDTO, SessionMessagesResponseDTO } from "@/services/triage.service";
import type { AgentStreamEvent, ChatMessage } from "@/types/triage-chat";
import { TRIAGE_QUERY_KEYS } from "@/queries/triage-query-keys";

export { TRIAGE_QUERY_KEYS } from "@/queries/triage-query-keys";

export function useStartTriage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: StartTriageRequestDTO) => triageService.startTriage(payload),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: TRIAGE_QUERY_KEYS.history() });
    },
  });
}

export function useGetSessionMessages(sessionId: string | null) {
  return useQuery({
    queryKey: TRIAGE_QUERY_KEYS.messages(sessionId ?? "inactive"),
    queryFn: () => triageService.getSessionMessages(sessionId as string),
    enabled: !!sessionId,
    staleTime: 0,
    refetchOnMount: "always",
    refetchOnReconnect: "always",
    refetchInterval: (query) => {
      const data = query?.state?.data;
      // Nếu đang chờ duyệt, tự động poll mỗi 5s để cập nhật kết quả HITL
      if (data?.session_status?.status === "HITL_REVIEWING") return 5000;
      return false;
    }
  });
}

export function useSubmitChatTurn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, payload, onProgress, signal }: {
      sessionId: string;
      payload: PatientChatInputDTO;
      answeredMessageId?: string;
      onProgress?: (event: AgentStreamEvent) => void;
      signal?: AbortSignal;
    }) => triageService.submitChatTurnStream(
      sessionId,
      payload,
      onProgress || (() => {}),
      signal,
    ),
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: TRIAGE_QUERY_KEYS.messages(variables.sessionId) });
      const previousData = queryClient.getQueryData<SessionMessagesResponseDTO>(TRIAGE_QUERY_KEYS.messages(variables.sessionId));
      
      const userMessageText = variables.payload.confirm_intake
        ? "Tôi xác nhận thông tin đã thu thập là đúng và đồng ý bắt đầu phân loại."
        : variables.payload.selected_option || variables.payload.message || "";
      
      if (userMessageText) {
        queryClient.setQueryData<SessionMessagesResponseDTO>(TRIAGE_QUERY_KEYS.messages(variables.sessionId), (old) => {
          if (!old) return old;
          return {
            ...old,
            messages: [
              ...(old.messages || []).map((message) =>
                message.id === variables.answeredMessageId && message.structured
                  ? {
                      ...message,
                      structured: {
                        ...message.structured,
                        submitted: true,
                        selectedAnswer: userMessageText,
                      },
                    }
                  : message,
              ),
              {
                id: `optimistic-${Date.now()}`,
                sender: "user" as const,
                content: userMessageText,
                timestamp: new Date().toISOString(),
                step: old.messages.at(-1)?.step ?? 1,
              } satisfies ChatMessage,
            ]
          };
        });
      }
      return { previousData };
    },
    onSuccess: (result, variables) => {
      queryClient.setQueryData<SessionMessagesResponseDTO>(
        TRIAGE_QUERY_KEYS.messages(variables.sessionId),
        (old) => {
          if (!old) return old;
          const messages = old.messages.some(
            (message) => message.id === result.id,
          )
            ? old.messages
            : [...old.messages, result];
          const clearsFinalizedOutput =
            result.decisionStatus === "RETRIEVAL_FAILURE" ||
            result.decisionStatus === "INSUFFICIENT_EVIDENCE" ||
            result.decisionStatus === "NEEDS_CLARIFICATION";
          return {
            ...old,
            session_status: {
              ...old.session_status,
              decision_status: result.decisionStatus ?? null,
              evidence_status: result.evidenceStatus ?? null,
              workflow_phase: result.workflowPhase ?? null,
              retrieval_degraded_modes: result.retrievalDegradedModes ?? [],
              sbar_finalized: result.sbarFinalized ?? false,
              ...(clearsFinalizedOutput
                ? {
                    ai_proposed_esi: null,
                    final_esi: null,
                    sbar_summary: null,
                    sbar_finalized: false,
                  }
                : {}),
            },
            messages,
          };
        },
      );
    },
    onError: (_err, variables, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(TRIAGE_QUERY_KEYS.messages(variables.sessionId), context.previousData);
      }
    },
    onSettled: (_data, _error, variables) => {
      void queryClient.invalidateQueries({
        queryKey: TRIAGE_QUERY_KEYS.messages(variables.sessionId),
      });
      void queryClient.invalidateQueries({ queryKey: TRIAGE_QUERY_KEYS.history() });
      void queryClient.invalidateQueries({
        queryKey: TRIAGE_QUERY_KEYS.replayDetail(variables.sessionId),
      });
    },
  });
}

export function useGetPatientHistory() {
  return useQuery({
    queryKey: TRIAGE_QUERY_KEYS.history(),
    queryFn: () => triageService.getPatientHistory(),
  });
}
