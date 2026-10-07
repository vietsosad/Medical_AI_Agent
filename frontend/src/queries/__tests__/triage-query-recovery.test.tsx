import type { PropsWithChildren } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useTriageHistory } from "@/hooks/queries/use-triage-history";
import { TRIAGE_QUERY_KEYS } from "@/queries/triage-query-keys";
import {
  useGetPatientHistory,
  useSubmitChatTurn,
} from "@/queries/useTriageQueries";
import {
  triageService,
  type SessionMessagesResponseDTO,
} from "@/services/triage.service";
import type { TriageHistoryListItemDTO } from "@/types/clinical-history";

function createClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function wrapperFor(client: QueryClient) {
  return function QueryWrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

const historyItem: TriageHistoryListItemDTO = {
  session_id: "session-1",
  chief_complaint: "Đau ngực",
  created_at: "2026-08-20T00:00:00Z",
  status: "IN_PROGRESS",
  final_esi: null,
  hitl_status: "PENDING_REVIEW",
  sbar_snippet: "",
  sbar_finalized: false,
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("canonical current-history cache", () => {
  it("shares the wrapper cache shape while the sidebar selector deduplicates sessions", async () => {
    vi.spyOn(triageService, "getPatientHistory").mockResolvedValue({
      items: [historyItem, { ...historyItem }],
    });
    const client = createClient();
    const wrapper = wrapperFor(client);
    const fullHistory = renderHook(() => useGetPatientHistory(), { wrapper });
    const sidebarHistory = renderHook(() => useTriageHistory(), { wrapper });

    await waitFor(() => {
      expect(fullHistory.result.current.isSuccess).toBe(true);
      expect(sidebarHistory.result.current.isSuccess).toBe(true);
    });

    expect(fullHistory.result.current.data?.items).toHaveLength(2);
    expect(sidebarHistory.result.current.data).toEqual([historyItem]);
    expect(client.getQueryData(TRIAGE_QUERY_KEYS.history())).toEqual({
      items: [historyItem, historyItem],
    });

    fullHistory.unmount();
    sidebarHistory.unmount();
    client.clear();
  });
});

describe("chat-turn cache recovery", () => {
  it("updates the current session and invalidates messages, history, and replay detail", async () => {
    const client = createClient();
    const invalidateSpy = vi.spyOn(client, "invalidateQueries");
    const cachedSession: SessionMessagesResponseDTO = {
      session_status: {
        session_id: "session-1",
        status: "IN_PROGRESS",
        hitl_status: "PENDING_REVIEW",
        is_red_flag_triggered: false,
        created_at: "2026-08-20T00:00:00Z",
        sbar_finalized: false,
        intake_confirmation_status: "NOT_READY",
        retrieval_degraded_modes: [],
      },
      messages: [
        {
          id: "question-1",
          sender: "bot",
          timestamp: "2026-08-20T00:00:00Z",
          content: "Bạn đau ở đâu?",
          step: 1,
          structured: { optionsType: "text_only", submitted: false },
        },
      ],
    };
    client.setQueryData(TRIAGE_QUERY_KEYS.messages("session-1"), cachedSession);
    vi.spyOn(triageService, "submitChatTurnStream").mockResolvedValue({
      id: "answer-1",
      sender: "bot",
      timestamp: "2026-08-20T00:00:02Z",
      content: "Đã ghi nhận",
      step: 2,
      decisionStatus: "COLLECTING",
      evidenceStatus: "NOT_REQUESTED",
      workflowPhase: "CLARIFICATION",
      retrievalDegradedModes: [],
      sbarFinalized: false,
    });
    const mutation = renderHook(() => useSubmitChatTurn(), {
      wrapper: wrapperFor(client),
    });

    await act(async () => {
      await mutation.result.current.mutateAsync({
        sessionId: "session-1",
        answeredMessageId: "question-1",
        payload: { message: "Bên trái" },
      });
    });

    const cached = client.getQueryData<SessionMessagesResponseDTO>(
      TRIAGE_QUERY_KEYS.messages("session-1"),
    );
    expect(cached?.messages.find((item) => item.id === "question-1")?.structured)
      .toMatchObject({ submitted: true, selectedAnswer: "Bên trái" });
    expect(cached?.messages.some((item) => item.id === "answer-1")).toBe(true);

    const invalidatedKeys = invalidateSpy.mock.calls.map(([filters]) =>
      (filters as { queryKey?: readonly unknown[] }).queryKey,
    );
    expect(invalidatedKeys).toEqual(
      expect.arrayContaining([
        TRIAGE_QUERY_KEYS.messages("session-1"),
        TRIAGE_QUERY_KEYS.history(),
        TRIAGE_QUERY_KEYS.replayDetail("session-1"),
      ]),
    );

    mutation.unmount();
    client.clear();
  });
});
