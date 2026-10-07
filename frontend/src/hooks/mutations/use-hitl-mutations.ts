"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { CLINICAL_HITL_QUERY_KEYS } from "@/hooks/queries/use-clinical-hitl";
import { clinicalHitlService } from "@/services/clinical-hitl.service";
import type {
  ClaimCasePayload,
  EscalateCasePayload,
  HandoffCasePayload,
  IntakeUpdatePayload,
  ObservationUpdatePayload,
  TriageDecisionPayload,
} from "@/types/clinical-hitl";

export function useClaimCase(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ClaimCasePayload) => clinicalHitlService.claimCase(caseId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.queueRoot() }),
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.case(caseId) }),
      ]);
    },
  });
}

export function useUpdateObservations(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ObservationUpdatePayload) =>
      clinicalHitlService.updateObservations(caseId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.case(caseId) }),
  });
}

export function useUpdateIntake(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: IntakeUpdatePayload) =>
      clinicalHitlService.updateIntake(caseId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.case(caseId) }),
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.queueRoot() }),
      ]);
    },
  });
}

export function useSubmitTriageDecision(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TriageDecisionPayload) =>
      clinicalHitlService.submitDecision(caseId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.case(caseId) }),
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.queueRoot() }),
      ]);
    },
  });
}

export function useRequestSpecialistReview(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: EscalateCasePayload) =>
      clinicalHitlService.requestSpecialistReview(caseId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.case(caseId) }),
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.queueRoot() }),
      ]);
    },
  });
}

export function useHandoffCase(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: HandoffCasePayload) => clinicalHitlService.handoffCase(caseId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.case(caseId) }),
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.queueRoot() }),
      ]);
    },
  });
}

export function useAcknowledgeAlert(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (caseVersion: number) => clinicalHitlService.acknowledgeAlert(caseId, caseVersion),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.queueRoot() }),
        queryClient.invalidateQueries({ queryKey: CLINICAL_HITL_QUERY_KEYS.case(caseId) }),
      ]);
    },
  });
}

export function useAccessPii(caseId: string) {
  return useMutation({
    mutationFn: (reason: string) => clinicalHitlService.accessPii(caseId, reason),
  });
}
