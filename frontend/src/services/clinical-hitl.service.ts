import axios, { type AxiosError } from "axios";
import { z } from "zod";

import { axiosClient } from "@/lib/api/axios.client";
import {
  caseMessagesResponseSchema,
  emergencyContactResponseSchema,
  inboxResponseSchema,
  nurseActionResponseSchema,
  nurseCaseDetailSchema,
  nurseQueueResponseSchema,
  piiAccessResponseSchema,
} from "@/lib/validations/clinical-hitl.schema";
import type {
  CaseMessagesResponseDTO,
  ClaimCasePayload,
  EmergencyContactResponseDTO,
  InboxResponseDTO,
  EscalateCasePayload,
  HandoffCasePayload,
  IntakeUpdatePayload,
  NurseActionResponseDTO,
  NurseCaseDetailDTO,
  NurseQueueResponseDTO,
  ObservationUpdatePayload,
  PiiAccessResponseDTO,
  TriageDecisionPayload,
} from "@/types/clinical-hitl";

export interface QueueFilters {
  mineOnly?: boolean;
  urgentOnly?: boolean;
  needsInfoOnly?: boolean;
  specialistOnly?: boolean;
}

export function getClinicalApiError(error: unknown): Error {
  if (error instanceof z.ZodError) {
    const invalidPaths = Array.from(
      new Set(error.issues.map((issue) => issue.path.join(".")).filter(Boolean)),
    );
    const fieldMessage = invalidPaths.length > 0
      ? ` Trường chưa khớp: ${invalidPaths.slice(0, 3).join(", ")}.`
      : "";
    return new Error(`Dữ liệu từ máy chủ không đúng hợp đồng Nurse Triage an toàn.${fieldMessage}`);
  }
  if (axios.isAxiosError(error)) {
    const responseError = error as AxiosError<{
      detail?: string | { message?: string; missing_fields?: string[] };
    }>;
    const detail = responseError.response?.data?.detail;
    if (typeof detail === "string") return new Error(detail);
    if (detail?.message) return new Error(detail.message);
    if (detail?.missing_fields) {
      return new Error(`Còn thiếu: ${detail.missing_fields.join(", ")}.`);
    }
    if (!responseError.response) {
      return new Error("Không thể kết nối máy chủ Triage. Không có dữ liệu mẫu thay thế.");
    }
  }
  return error instanceof Error ? error : new Error("Yêu cầu Triage không thành công.");
}

/**
 * Suy kiểu trả về từ **đầu ra** của schema, không phải đầu vào.
 *
 * Một trường có `.default()`/`.catch()` được phép vắng mặt trong payload nhưng
 * luôn có giá trị sau khi parse. Nếu suy kiểu từ đầu vào, TypeScript sẽ tưởng
 * trường đó có thể `undefined` và bắt mọi nơi dùng phải kiểm tra thừa.
 */
async function request<S extends z.ZodTypeAny>(
  operation: () => Promise<{ data: unknown }>,
  schema: S,
): Promise<z.output<S>> {
  try {
    const response = await operation();
    return schema.parse(response.data);
  } catch (error) {
    throw getClinicalApiError(error);
  }
}

export const clinicalHitlService = {
  getQueue(filters: QueueFilters = {}): Promise<NurseQueueResponseDTO> {
    return request(
      () => axiosClient.get<unknown>("/api/v1/nurse/queue", {
        params: {
          mine_only: filters.mineOnly ?? false,
          urgent_only: filters.urgentOnly ?? false,
          needs_info_only: filters.needsInfoOnly ?? false,
          specialist_only: filters.specialistOnly ?? false,
        },
      }),
      nurseQueueResponseSchema,
    );
  },

  getCase(caseId: string): Promise<NurseCaseDetailDTO> {
    return request(
      () => axiosClient.get<unknown>(`/api/v1/nurse/cases/${caseId}`),
      nurseCaseDetailSchema,
    );
  },

  claimCase(caseId: string, payload: ClaimCasePayload): Promise<NurseActionResponseDTO> {
    return request(
      () => axiosClient.post<unknown>(`/api/v1/nurse/cases/${caseId}/claim`, payload),
      nurseActionResponseSchema,
    );
  },

  updateObservations(
    caseId: string,
    payload: ObservationUpdatePayload,
  ): Promise<NurseActionResponseDTO> {
    return request(
      () => axiosClient.patch<unknown>(
        `/api/v1/nurse/cases/${caseId}/observations`,
        payload,
      ),
      nurseActionResponseSchema,
    );
  },

  updateIntake(caseId: string, payload: IntakeUpdatePayload): Promise<NurseActionResponseDTO> {
    return request(
      () => axiosClient.patch<unknown>(`/api/v1/nurse/cases/${caseId}/intake`, payload),
      nurseActionResponseSchema,
    );
  },

  submitDecision(caseId: string, payload: TriageDecisionPayload): Promise<NurseActionResponseDTO> {
    return request(
      () => axiosClient.post<unknown>(`/api/v1/nurse/cases/${caseId}/decision`, payload),
      nurseActionResponseSchema,
    );
  },

  requestSpecialistReview(
    caseId: string,
    payload: EscalateCasePayload,
  ): Promise<NurseActionResponseDTO> {
    return request(
      () => axiosClient.post<unknown>(`/api/v1/nurse/cases/${caseId}/escalate`, payload),
      nurseActionResponseSchema,
    );
  },

  handoffCase(caseId: string, payload: HandoffCasePayload): Promise<NurseActionResponseDTO> {
    return request(
      () => axiosClient.post<unknown>(`/api/v1/nurse/cases/${caseId}/handoff`, payload),
      nurseActionResponseSchema,
    );
  },

  acknowledgeAlert(caseId: string, caseVersion: number): Promise<NurseActionResponseDTO> {
    return request(
      () => axiosClient.post<unknown>(`/api/v1/nurse/alerts/${caseId}/acknowledge`, {
        case_version: caseVersion,
      }),
      nurseActionResponseSchema,
    );
  },

  /** Các ca có tin của người bệnh chưa ai đọc, dùng cho hộp thư trạm trực. */
  getInbox(): Promise<InboxResponseDTO> {
    return request(
      () => axiosClient.get("/api/v1/nurse/inbox"),
      inboxResponseSchema,
    );
  },

  /**
   * Riêng luồng trao đổi với người bệnh, đọc được mà không cần nhận ca.
   * Hội thoại hỏi bệnh với AI vẫn nằm sau `getCaseMessages`.
   */
  getCareTeamThread(caseId: string): Promise<CaseMessagesResponseDTO> {
    return request(
      () => axiosClient.get(`/api/v1/nurse/cases/${encodeURIComponent(caseId)}/care-team`),
      caseMessagesResponseSchema,
    );
  },

  /** Hội thoại của ca; chỉ nhân viên đang phụ trách đọc được. */
  getCaseMessages(caseId: string): Promise<CaseMessagesResponseDTO> {
    return request(
      () => axiosClient.get(`/api/v1/nurse/cases/${encodeURIComponent(caseId)}/messages`),
      caseMessagesResponseSchema,
    );
  },

  /** Nhắn trực tiếp cho người bệnh. `clientMessageId` chống tạo trùng bản ghi. */
  sendCaseMessage(
    caseId: string,
    content: string,
    clientMessageId: string,
  ): Promise<CaseMessagesResponseDTO> {
    return request(
      () =>
        axiosClient.post(`/api/v1/nurse/cases/${encodeURIComponent(caseId)}/messages`, {
          content,
          client_message_id: clientMessageId,
        }),
      caseMessagesResponseSchema,
    );
  },

  async markCaseMessagesRead(caseId: string): Promise<void> {
    await axiosClient.post(`/api/v1/nurse/cases/${encodeURIComponent(caseId)}/messages/read`);
  },

  /** Danh bạ khẩn cấp, tách rõ số bệnh nhân với số người giám hộ. */
  getEmergencyContacts(caseId: string): Promise<EmergencyContactResponseDTO> {
    return request(
      () =>
        axiosClient.get(
          `/api/v1/nurse/cases/${encodeURIComponent(caseId)}/emergency-contacts`,
        ),
      emergencyContactResponseSchema,
    );
  },

  accessPii(caseId: string, reason: string): Promise<PiiAccessResponseDTO> {
    return request(
      () => axiosClient.post<unknown>(`/api/v1/nurse/cases/${caseId}/pii-access`, {
        reason,
      }),
      piiAccessResponseSchema,
    );
  },
};
