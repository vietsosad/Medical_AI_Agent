import axios, { AxiosError } from "axios";
import { ZodError } from "zod";
import { axiosClient } from "@/lib/api/axios.client";
import type {
  SimpleClaimPayload,
  SimpleDecisionPayload,
  SimpleNurseActionResponseDTO,
  SimpleNurseCaseDetailDTO,
  SimpleNurseDashboardDTO,
  SimpleNurseQueueParams,
  SimpleNurseQueueResponseDTO,
} from "@/types/simple-nurse";
import type { SimpleCaseMessagesDTO } from "@/types/simple-care-team";
import {
  simpleNurseActionResponseSchema,
  simpleNurseCaseDetailSchema,
  simpleNurseDashboardSchema,
  simpleNurseQueueResponseSchema,
} from "@/schemas/simple-nurse.schema";
import { simpleCaseMessagesSchema } from "@/schemas/simple-care-team.schema";

/**
 * Thin client for the nurse-review pilot routes
 * (`src/api/routes_nurse_simple.py`, prefix `/api/v1/nurse-simple`) --
 * parallel to `@/services/clinical-hitl.service`, never shares a table or a
 * URL prefix with it.
 */

/**
 * Lỗi từ máy chủ, giữ nguyên mã lỗi (vd. `CASE_VERSION_CONFLICT` của
 * `_assert_version`) để giao diện nhận ra xung đột phiên bản mà không phải dò
 * câu chữ thông báo.
 */
export class SimpleNurseApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string | null,
  ) {
    super(message);
    this.name = "SimpleNurseApiError";
  }
}

const handlePilotApiError = (error: unknown, fallbackMessage: string): never => {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<{ detail?: unknown }>;
    if (!axiosErr.response) {
      throw new Error("Không thể kết nối tới máy chủ AI Triage FastAPI. Vui lòng kiểm tra dịch vụ Backend.");
    }
    const { status } = axiosErr.response;
    if (status === 503) {
      throw new SimpleNurseApiError("Triage Agent đang tắt trên môi trường này (SIMPLE_AGENT_ENABLED=false).", status, null);
    }
    const detail = axiosErr.response.data?.detail;
    if (typeof detail === "string") throw new SimpleNurseApiError(detail, status, null);
    if (detail && typeof detail === "object" && "message" in detail) {
      const code = "code" in detail && typeof detail.code === "string" ? detail.code : null;
      throw new SimpleNurseApiError(String((detail as { message: unknown }).message), status, code);
    }
  }
  if (error instanceof ZodError) {
    throw new Error("Dữ liệu máy chủ trả về không đúng hợp đồng dữ liệu (lỗi ở phía frontend, không phải do bạn).");
  }
  if (error instanceof Error) throw error;
  throw new Error(fallbackMessage);
};

export const simpleNurseService = {
  /** `GET /nurse-simple/queue` */
  getQueue: async (params: SimpleNurseQueueParams = {}): Promise<SimpleNurseQueueResponseDTO> => {
    try {
      const response = await axiosClient.get("/api/v1/nurse-simple/queue", {
        params: {
          bucket: params.bucket,
          mine_only: params.mineOnly || undefined,
          q: params.q || undefined,
          patient_email: params.patientEmail || undefined,
          // Chuỗi phân cách dấu phẩy, không phải mảng -- tránh phụ thuộc vào
          // cách axios tự nối tham số dạng danh sách vào query string (xem
          // routes_nurse_simple.py's esi_levels param).
          esi_levels: params.esiLevels && params.esiLevels.length > 0 ? params.esiLevels.join(",") : undefined,
          page: params.page,
          page_size: params.pageSize,
        },
      });
      return simpleNurseQueueResponseSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không thể tải hàng đợi.");
    }
  },

  /** `GET /nurse-simple/cases/{sessionId}` */
  /** `GET /nurse-simple/dashboard` */
  getDashboard: async (): Promise<SimpleNurseDashboardDTO> => {
    try {
      const response = await axiosClient.get("/api/v1/nurse-simple/dashboard");
      return simpleNurseDashboardSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không thể tải số liệu tổng quan.");
    }
  },

  getCase: async (sessionId: string): Promise<SimpleNurseCaseDetailDTO> => {
    try {
      const response = await axiosClient.get(`/api/v1/nurse-simple/cases/${encodeURIComponent(sessionId)}`);
      return simpleNurseCaseDetailSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không thể tải chi tiết ca.");
    }
  },

  /** `POST /nurse-simple/cases/{sessionId}/claim` */
  claim: async (sessionId: string, payload: SimpleClaimPayload): Promise<SimpleNurseActionResponseDTO> => {
    try {
      const response = await axiosClient.post(
        `/api/v1/nurse-simple/cases/${encodeURIComponent(sessionId)}/claim`,
        payload,
      );
      return simpleNurseActionResponseSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không thể nhận ca này.");
    }
  },

  /** `POST /nurse-simple/cases/{sessionId}/decision` */
  submitDecision: async (
    sessionId: string,
    payload: SimpleDecisionPayload,
  ): Promise<SimpleNurseActionResponseDTO> => {
    try {
      const response = await axiosClient.post(
        `/api/v1/nurse-simple/cases/${encodeURIComponent(sessionId)}/decision`,
        payload,
      );
      return simpleNurseActionResponseSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không thể lưu quyết định phân luồng.");
    }
  },

  /** `GET /nurse-simple/cases/{sessionId}/care-team` */
  getCareTeamThread: async (sessionId: string): Promise<SimpleCaseMessagesDTO> => {
    try {
      const response = await axiosClient.get(
        `/api/v1/nurse-simple/cases/${encodeURIComponent(sessionId)}/care-team`,
      );
      return simpleCaseMessagesSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không tải được kênh trao đổi với bệnh nhân.");
    }
  },

  /** `POST /nurse-simple/cases/{sessionId}/messages` */
  sendCaseMessage: async (
    sessionId: string,
    content: string,
    clientMessageId: string,
  ): Promise<SimpleCaseMessagesDTO> => {
    try {
      const response = await axiosClient.post(
        `/api/v1/nurse-simple/cases/${encodeURIComponent(sessionId)}/messages`,
        { content, client_message_id: clientMessageId },
      );
      return simpleCaseMessagesSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không gửi được tin nhắn tới bệnh nhân.");
    }
  },

  /** `POST /nurse-simple/cases/{sessionId}/messages/read` */
  markCaseMessagesRead: async (sessionId: string): Promise<SimpleCaseMessagesDTO> => {
    try {
      const response = await axiosClient.post(
        `/api/v1/nurse-simple/cases/${encodeURIComponent(sessionId)}/messages/read`,
      );
      return simpleCaseMessagesSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không cập nhật được trạng thái đã đọc.");
    }
  },
};
