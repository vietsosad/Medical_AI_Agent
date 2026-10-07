import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { simpleTriageService } from "@/services/simple-triage.service";
import { SIMPLE_TRIAGE_QUERY_KEYS } from "@/queries/simple-triage-query-keys";
import { useClinicalSocket } from "@/lib/realtime/useClinicalSocket";

export { SIMPLE_TRIAGE_QUERY_KEYS } from "@/queries/simple-triage-query-keys";

/** Same 20s fallback-poll cadence as the production `CareTeamDock.tsx`. */
const CARE_TEAM_POLL_MS = 20_000;

export function useStartSimpleTriage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ message, profileId }: { message: string; profileId?: string | null }) =>
      simpleTriageService.start(message, profileId),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: SIMPLE_TRIAGE_QUERY_KEYS.sessions() });
    },
  });
}

export function useSubmitSimpleTriageChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, message }: { sessionId: string; message: string }) =>
      simpleTriageService.chat(sessionId, message),
    onSettled: (_data, _error, variables) => {
      void queryClient.invalidateQueries({
        queryKey: SIMPLE_TRIAGE_QUERY_KEYS.session(variables.sessionId),
      });
      void queryClient.invalidateQueries({ queryKey: SIMPLE_TRIAGE_QUERY_KEYS.sessions() });
    },
  });
}

export function useSimpleTriageSessions() {
  return useQuery({
    queryKey: SIMPLE_TRIAGE_QUERY_KEYS.sessions(),
    queryFn: () => simpleTriageService.listSessions(),
  });
}

export function useSimpleTriageSessionDetail(sessionId: string | null) {
  return useQuery({
    queryKey: SIMPLE_TRIAGE_QUERY_KEYS.session(sessionId ?? "inactive"),
    queryFn: () => simpleTriageService.getSession(sessionId as string),
    enabled: !!sessionId,
    staleTime: 0,
    refetchOnMount: "always",
  });
}

const careTeamKey = (sessionId: string | null) =>
  [...SIMPLE_TRIAGE_QUERY_KEYS.all, "care-team", sessionId ?? "inactive"] as const;

export function useSimpleCareTeamThread(sessionId: string | null) {
  return useQuery({
    queryKey: careTeamKey(sessionId),
    queryFn: () => simpleTriageService.getCareTeamThread(sessionId as string),
    enabled: !!sessionId,
    refetchInterval: CARE_TEAM_POLL_MS,
    staleTime: 2_000,
  });
}

export function useSendSimpleMessageToStaff(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ content, clientMessageId }: { content: string; clientMessageId: string }) =>
      simpleTriageService.sendMessageToStaff(sessionId, content, clientMessageId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: careTeamKey(sessionId) });
    },
  });
}

export function useMarkSimpleStaffMessagesRead(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => simpleTriageService.markStaffMessagesRead(sessionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: careTeamKey(sessionId) });
    },
  });
}

/**
 * Realtime companion to `CARE_TEAM_POLL_MS` above -- a nurse's reply lands in
 * the open thread almost immediately instead of waiting for the next poll
 * tick. Polling stays as-is: an event only means "something changed, go
 * re-read REST", so a dropped event just falls back to the existing 20s
 * cadence rather than showing wrong data. See
 * `.claude/plans/sunny-launching-mitten.md`'s realtime addendum.
 */
export function useSimpleCareTeamRealtime(sessionId: string | null) {
  const queryClient = useQueryClient();
  const onEvent = useCallback(() => {
    if (!sessionId) return;
    void queryClient.invalidateQueries({ queryKey: careTeamKey(sessionId) });
    void queryClient.invalidateQueries({ queryKey: SIMPLE_TRIAGE_QUERY_KEYS.session(sessionId) });
    void queryClient.invalidateQueries({ queryKey: SIMPLE_TRIAGE_QUERY_KEYS.sessions() });
  }, [queryClient, sessionId]);
  return useClinicalSocket({
    path: sessionId ? `/ws/simple-case/${encodeURIComponent(sessionId)}` : null,
    onEvent,
    enabled: Boolean(sessionId),
  });
}

/**
 * One socket per patient, scoped to *all* of their pilot sessions -- lets
 * `SimplePilotSidebar.tsx` show a fresh "tin mới" badge the moment a nurse
 * replies on any session, not just the one currently open.
 */
export function useSimplePatientRealtime() {
  const queryClient = useQueryClient();
  const onEvent = useCallback((event: { payload?: Record<string, unknown> }) => {
    void queryClient.invalidateQueries({ queryKey: SIMPLE_TRIAGE_QUERY_KEYS.sessions() });
    const sessionId = event.payload?.session_id;
    if (typeof sessionId === "string" && sessionId) {
      void queryClient.invalidateQueries({ queryKey: SIMPLE_TRIAGE_QUERY_KEYS.session(sessionId) });
    }
  }, [queryClient]);
  return useClinicalSocket({ path: "/ws/simple-patient", onEvent });
}
