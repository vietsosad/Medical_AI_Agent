"use client";

import { useCallback, useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  useClinicalSocket,
  type ClinicalRealtimeEvent,
  type ClinicalSocketStatus,
} from "@/lib/realtime/useClinicalSocket";
import {
  clinicalHitlService,
  type QueueFilters,
} from "@/services/clinical-hitl.service";

export const CLINICAL_HITL_QUERY_KEYS = {
  all: ["nurse-triage"] as const,
  queueRoot: () => [...CLINICAL_HITL_QUERY_KEYS.all, "queue"] as const,
  queue: (filters: QueueFilters) => [...CLINICAL_HITL_QUERY_KEYS.queueRoot(), filters] as const,
  caseRoot: () => [...CLINICAL_HITL_QUERY_KEYS.all, "case"] as const,
  case: (caseId: string) => [...CLINICAL_HITL_QUERY_KEYS.caseRoot(), caseId] as const,
  messages: (caseId: string) => [...CLINICAL_HITL_QUERY_KEYS.all, "messages", caseId] as const,
  careTeam: (caseId: string) => [...CLINICAL_HITL_QUERY_KEYS.all, "care-team", caseId] as const,
  inbox: () => [...CLINICAL_HITL_QUERY_KEYS.all, "inbox"] as const,
  contacts: (caseId: string) => [...CLINICAL_HITL_QUERY_KEYS.all, "contacts", caseId] as const,
};

export function useNurseQueue(filters: QueueFilters) {
  return useQuery({
    queryKey: CLINICAL_HITL_QUERY_KEYS.queue(filters),
    queryFn: () => clinicalHitlService.getQueue(filters),
    refetchInterval: 10_000,
    staleTime: 5_000,
    retry: 1,
  });
}

export function useNurseCase(caseId: string) {
  return useQuery({
    queryKey: CLINICAL_HITL_QUERY_KEYS.case(caseId),
    queryFn: () => clinicalHitlService.getCase(caseId),
    enabled: Boolean(caseId),
    staleTime: 3_000,
    retry: 1,
  });
}


// ============================================================================
// HỘI THOẠI TRỰC TIẾP VỚI NGƯỜI BỆNH
// ============================================================================

export function useCaseMessages(caseId: string, enabled: boolean) {
  return useQuery({
    queryKey: CLINICAL_HITL_QUERY_KEYS.messages(caseId),
    queryFn: () => clinicalHitlService.getCaseMessages(caseId),
    enabled: Boolean(caseId) && enabled,
    // Kênh WebSocket là nguồn đánh thức chính; nhịp nền chỉ là lưới an toàn khi
    // kênh đang đứt để hội thoại lâm sàng không bao giờ đứng im quá lâu.
    refetchInterval: 20_000,
    staleTime: 2_000,
    retry: 1,
  });
}

export function useSendCaseMessage(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ content, clientMessageId }: { content: string; clientMessageId: string }) =>
      clinicalHitlService.sendCaseMessage(caseId, content, clientMessageId),
    onSuccess: (data) => {
      queryClient.setQueryData(CLINICAL_HITL_QUERY_KEYS.messages(caseId), data);
      queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.queueRoot() });
      queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.inbox() });
      queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.careTeam(caseId) });
    },
  });
}

export function useMarkCaseMessagesRead(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => clinicalHitlService.markCaseMessagesRead(caseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.messages(caseId) });
      queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.queueRoot() });
      queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.inbox() });
      queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.careTeam(caseId) });
    },
  });
}

/** Danh bạ khẩn cấp chỉ được tải khi nhân viên chủ động mở, và có ghi kiểm toán. */
export function useEmergencyContacts(caseId: string, enabled: boolean) {
  return useQuery({
    queryKey: CLINICAL_HITL_QUERY_KEYS.contacts(caseId),
    queryFn: () => clinicalHitlService.getEmergencyContacts(caseId),
    enabled: Boolean(caseId) && enabled,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    retry: 1,
  });
}

// ============================================================================
// KÊNH THỜI GIAN THỰC
// ============================================================================

/** Hộp thư trạm trực: ca nào đang có tin người bệnh chưa ai đọc. */
export function useClinicalInbox(enabled = true) {
  return useQuery({
    queryKey: CLINICAL_HITL_QUERY_KEYS.inbox(),
    queryFn: () => clinicalHitlService.getInbox(),
    enabled,
    // Kênh realtime là nguồn đánh thức chính; nhịp nền là lưới an toàn khi đứt.
    refetchInterval: 30_000,
    staleTime: 5_000,
    retry: 1,
  });
}

/** Luồng trao đổi với người bệnh, đọc được từ hàng đợi mà không cần nhận ca. */
export function useCareTeamThread(caseId: string, enabled: boolean) {
  return useQuery({
    queryKey: CLINICAL_HITL_QUERY_KEYS.careTeam(caseId),
    queryFn: () => clinicalHitlService.getCareTeamThread(caseId),
    enabled: Boolean(caseId) && enabled,
    refetchInterval: 20_000,
    staleTime: 2_000,
    retry: 1,
  });
}

export interface ClinicalRealtimeOptions {
  enabled?: boolean;
  /** Gọi khi người bệnh vừa nhắn, để trạm trực báo cho người đang trực. */
  onPatientMessage?: (event: ClinicalRealtimeEvent) => void;
}

/**
 * Kênh trạm trực, mở ở cấp workspace nên nhân viên nhận được việc dù đang ở
 * hàng đợi, một ca khác hay bất kỳ màn hình nào — không cần mở hồ sơ trước.
 */
export function useClinicalQueueRealtime(
  options: ClinicalRealtimeOptions = {},
): ClinicalSocketStatus {
  const { enabled = true, onPatientMessage } = options;
  const queryClient = useQueryClient();

  const handlerRef = useRef(onPatientMessage);
  useEffect(() => {
    handlerRef.current = onPatientMessage;
  }, [onPatientMessage]);

  const onEvent = useCallback(
    (event: ClinicalRealtimeEvent) => {
      // Sự kiện chỉ nói "có thay đổi"; nội dung lâm sàng luôn đọc lại từ API.
      queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.queueRoot() });

      if (event.event === "message.created") {
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.inbox() });
        const caseId = typeof event.payload?.case_id === "string" ? event.payload.case_id : null;
        if (caseId) {
          // Chỉ làm mới đúng ca liên quan, không quét lại toàn bộ hội thoại.
          queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.careTeam(caseId) });
          queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.messages(caseId) });
        }
        if (event.payload?.sender === "PATIENT") handlerRef.current?.(event);
      }
    },
    [queryClient],
  );

  const { status } = useClinicalSocket({ path: "/ws/clinical", onEvent, enabled });
  return status;
}

/** Hội thoại và trạng thái của đúng một ca. */
export function useCaseRealtime(caseId: string, enabled = true): ClinicalSocketStatus {
  const queryClient = useQueryClient();
  const onEvent = useCallback(
    () => {
      queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.messages(caseId) });
      queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.case(caseId) });
    },
    [queryClient, caseId],
  );

  const { status } = useClinicalSocket({
    path: caseId ? `/ws/case/${encodeURIComponent(caseId)}` : null,
    onEvent,
    enabled: enabled && Boolean(caseId),
  });
  return status;
}
