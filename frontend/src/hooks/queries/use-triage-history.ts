"use client";

import { useQuery, UseQueryResult } from "@tanstack/react-query";
import {
  triageService,
  type HistoryListResponseDTO,
} from "@/services/triage.service";
import { TRIAGE_QUERY_KEYS } from "@/queries/triage-query-keys";
import type {
  TriageHistoryListItemDTO,
  TriageSessionDetailDTO,
} from "@/types/clinical-history";
import {
  TriageHistoryListResponseSchema,
  TriageSessionDetailSchema,
} from "@/lib/validations/clinical-history.schema";

export function dedupeHistoryItems(
  items: TriageHistoryListItemDTO[],
): TriageHistoryListItemDTO[] {
  const sessionsById = new Map<string, TriageHistoryListItemDTO>();
  for (const item of items) {
    if (!sessionsById.has(item.session_id)) {
      sessionsById.set(item.session_id, item);
    }
  }
  return Array.from(sessionsById.values());
}

// ============================================================================
// 2. TANSTACK QUERY V5 CUSTOM HOOKS
// ============================================================================

/**
 * Hook fetch Danh Sách Ca Khám Quá Khứ (Triage History List).
 */
export const useTriageHistory = (): UseQueryResult<TriageHistoryListItemDTO[], Error> => {
  return useQuery<
    HistoryListResponseDTO,
    Error,
    TriageHistoryListItemDTO[]
  >({
    queryKey: TRIAGE_QUERY_KEYS.history(),
    queryFn: async (): Promise<HistoryListResponseDTO> => {
      const response = await triageService.getPatientHistory();
      return TriageHistoryListResponseSchema.parse(response);
    },
    select: (response) => dedupeHistoryItems(response.items),
    staleTime: 0,
    gcTime: 20 * 60 * 1000,
    retry: 1,
    refetchOnMount: "always",
    refetchOnReconnect: true,
    refetchOnWindowFocus: true,
  });
};

/**
 * Hook fetch Chi Tiết Một Ca Khám Quá Khứ theo `sessionId` (Triage Session Detail).
 */
export const useTriageSessionDetail = (
  sessionId: string | null | undefined
): UseQueryResult<TriageSessionDetailDTO, Error> => {
  const isValidId = Boolean(sessionId && sessionId.trim() !== "");

  return useQuery<TriageSessionDetailDTO, Error>({
    queryKey: TRIAGE_QUERY_KEYS.replayDetail(sessionId || "unknown"),
    queryFn: async (): Promise<TriageSessionDetailDTO> => {
      if (!sessionId) {
        throw new Error("ID ca khám lâm sàng không hợp lệ hoặc thiếu (sessionId cannot be empty)");
      }
      const response = await triageService.getSessionReplayDetail(sessionId);
      return TriageSessionDetailSchema.parse(response);
    },
    enabled: isValidId,
    staleTime: 0,
    gcTime: 30 * 60 * 1000,
    retry: 1,
    refetchOnMount: "always",
    refetchOnReconnect: true,
    refetchOnWindowFocus: true,
  });
};
