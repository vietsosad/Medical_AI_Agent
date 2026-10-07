import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { simpleNurseService } from "@/services/simple-nurse.service";
import { SIMPLE_NURSE_QUERY_KEYS } from "@/queries/simple-nurse-query-keys";
import type { SimpleClaimPayload, SimpleDecisionPayload, SimpleNurseQueueParams } from "@/types/simple-nurse";
import { useClinicalSocket } from "@/lib/realtime/useClinicalSocket";

export { SIMPLE_NURSE_QUERY_KEYS } from "@/queries/simple-nurse-query-keys";

// Polling stays as the fallback (an event only means "something changed, go
// re-read REST" -- see .claude/plans/sunny-launching-mitten.md's realtime
// addendum), but `/ws/simple-clinical` and `/ws/simple-case/{id}` below now
// close most of the gap between a message landing and the screen showing it.
const QUEUE_POLL_MS = 15_000;
const CASE_POLL_MS = 5_000;
const CARE_TEAM_POLL_MS = 20_000;
// Bảng số liệu đọc cùng tập ca với hàng đợi nên nhịp làm mới bám theo hàng đợi;
// mọi thao tác nhận ca / tạm gác / chốt ca đều làm mới nó ngay qua
// `invalidateQueries` bên dưới, nhịp này chỉ là lưới an toàn.
const DASHBOARD_POLL_MS = 30_000;

/**
 * `enabled` (mặc định bật) để nơi gọi có thể tắt hẳn truy vấn thay vì bắn một
 * request vô ích -- ClinicalSidebar dùng nó khi Triage Agent không phải là
 * luồng đang hoạt động (xem IS_PILOT_AGENT_ACTIVE), lúc đó endpoint pilot còn
 * có thể trả 503.
 */
export function useSimpleNurseQueue(params: SimpleNurseQueueParams = {}, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: SIMPLE_NURSE_QUERY_KEYS.queue(params),
    queryFn: () => simpleNurseService.getQueue(params),
    refetchInterval: QUEUE_POLL_MS,
    staleTime: 5_000,
    enabled: options.enabled ?? true,
  });
}

/**
 * Realtime companion to `useSimpleNurseQueue` -- any pilot message (either
 * direction) or auto-claim on send nudges every open queue tab/filter to
 * re-read immediately instead of waiting up to `QUEUE_POLL_MS`.
 */
export function useSimpleNurseQueueRealtime() {
  const queryClient = useQueryClient();
  const onEvent = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.queueAll() });
      void queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.dashboard() });
  }, [queryClient]);
  return useClinicalSocket({ path: "/ws/simple-clinical", onEvent });
}

/** Số liệu tổng quan trạm điều phối. `enabled` dùng chung idiom với hàng đợi. */
export function useSimpleNurseDashboard(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: SIMPLE_NURSE_QUERY_KEYS.dashboard(),
    queryFn: () => simpleNurseService.getDashboard(),
    refetchInterval: DASHBOARD_POLL_MS,
    staleTime: 10_000,
    enabled: options.enabled ?? true,
  });
}

export function useSimpleNurseCase(sessionId: string | null) {
  return useQuery({
    queryKey: SIMPLE_NURSE_QUERY_KEYS.case(sessionId ?? "inactive"),
    queryFn: () => simpleNurseService.getCase(sessionId as string),
    enabled: !!sessionId,
    refetchInterval: CASE_POLL_MS,
    staleTime: 3_000,
  });
}

export function useClaimSimpleCase(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SimpleClaimPayload) => simpleNurseService.claim(sessionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.case(sessionId) });
      void queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.queueAll() });
      void queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.dashboard() });
    },
  });
}

export function useSubmitSimpleDecision(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SimpleDecisionPayload) => simpleNurseService.submitDecision(sessionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.case(sessionId) });
      void queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.queueAll() });
      void queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.dashboard() });
    },
  });
}

const careTeamKey = (sessionId: string) => [...SIMPLE_NURSE_QUERY_KEYS.all, "care-team", sessionId] as const;

export function useSimpleCaseCareTeamThread(sessionId: string | null) {
  return useQuery({
    queryKey: careTeamKey(sessionId ?? "inactive"),
    queryFn: () => simpleNurseService.getCareTeamThread(sessionId as string),
    enabled: !!sessionId,
    refetchInterval: CARE_TEAM_POLL_MS,
    staleTime: 2_000,
  });
}

export function useSendSimpleCaseMessage(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ content, clientMessageId }: { content: string; clientMessageId: string }) =>
      simpleNurseService.sendCaseMessage(sessionId, content, clientMessageId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: careTeamKey(sessionId) });
      void queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.queueAll() });
      void queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.dashboard() });
    },
  });
}

export function useMarkSimpleCaseMessagesRead(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => simpleNurseService.markCaseMessagesRead(sessionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: careTeamKey(sessionId) });
      void queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.queueAll() });
      void queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.dashboard() });
    },
  });
}

/**
 * Realtime companion to `useSimpleCaseCareTeamThread` -- the patient's
 * message (or this case's claim state) refreshes as soon as it happens
 * instead of waiting up to `CASE_POLL_MS`/`CARE_TEAM_POLL_MS`.
 */
export function useSimpleCaseRealtime(sessionId: string | null) {
  const queryClient = useQueryClient();
  const onEvent = useCallback(() => {
    if (!sessionId) return;
    queryClient.invalidateQueries({ queryKey: careTeamKey(sessionId) });
    queryClient.invalidateQueries({ queryKey: SIMPLE_NURSE_QUERY_KEYS.case(sessionId) });
  }, [queryClient, sessionId]);
  return useClinicalSocket({
    path: sessionId ? `/ws/simple-case/${encodeURIComponent(sessionId)}` : null,
    onEvent,
    enabled: Boolean(sessionId),
  });
}
