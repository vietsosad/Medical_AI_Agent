import axios, { AxiosError } from "axios";
import { ZodError } from "zod";
import { axiosClient } from "@/lib/api/axios.client";
import type {
  SimpleTriageSessionDetailDTO,
  SimpleTriageSessionSummaryDTO,
  SimpleTriageTurnResponseDTO,
} from "@/types/simple-triage";
import type { SimpleCareTeamThreadDTO, SimpleStaffConversationDTO } from "@/types/simple-care-team";
import {
  simpleTriageSessionDetailSchema,
  simpleTriageSessionSummarySchema,
  simpleTriageTurnResponseSchema,
} from "@/schemas/simple-triage.schema";
import { simpleCareTeamThreadSchema, simpleStaffConversationSchema } from "@/schemas/simple-care-team.schema";

// axiosClient's shared default (15s, see axios.client.ts) is sized for a
// normal fast DB-backed call. One simple_agent turn is a single blocking
// request that can run Phase A's deepagents tool-calling loop up to 6 times
// (each its own OpenAI round trip) before Phase B/C even start -- unlike
// production's own `/triage` turn, which streams over SSE and so was never
// bound by one flat request timeout in the first place. A real turn hitting
// the shared 15s cap fails with no server-side trace at all (the request is
// aborted client-side before FastAPI ever finishes, sometimes before it can
// even log a response) -- observed live, and easy to mistake for a backend
// outage. Only override it for the two calls that actually run a turn.
const TURN_TIMEOUT_MS = 90_000;

/**
 * Thin client for the `simple_agent` pilot routes
 * (`src/api/routes_simple_triage.py`, prefix `/api/v1/simple-triage`).
 *
 * Deliberately separate from `triageService` (`@/services/triage.service`):
 * this pilot API is plain request/response JSON, not SSE, and returns
 * `simple_agent`'s own native shape rather than the DeepAgent `ChatMessage`
 * contract -- see `@/types/simple-triage` for why that's not reused here.
 */

const handlePilotApiError = (error: unknown, fallbackMessage: string): never => {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<{ detail?: string; message?: string }>;
    if (!axiosErr.response) {
      throw new Error("Không thể kết nối tới máy chủ AI Triage FastAPI. Vui lòng kiểm tra dịch vụ Backend.");
    }
    if (axiosErr.response.status === 503) {
      throw new Error(
        "Triage Agent đang tắt trên môi trường này (SIMPLE_AGENT_ENABLED=false).",
      );
    }
    const backendMsg = axiosErr.response.data?.detail || axiosErr.response.data?.message;
    if (backendMsg) {
      throw new Error(backendMsg);
    }
  }
  // A schema mismatch here is a bug in this file's types, not a backend
  // fault -- surface a short, readable message instead of the raw
  // JSON-stringified issues array Zod puts in `error.message`.
  if (error instanceof ZodError) {
    throw new Error("Dữ liệu máy chủ trả về không đúng hợp đồng dữ liệu (lỗi ở phía frontend, không phải do bạn).");
  }
  if (error instanceof Error) {
    throw error;
  }
  throw new Error(fallbackMessage);
};

export const simpleTriageService = {
  /**
   * `POST /simple-triage/start`. `profileId` is which EHR profile card the
   * patient picked ("thẻ của tôi" / "thẻ người thân") -- omit (or pass
   * `null`) for "ẩn danh / người mới": no demographics are known, and
   * sex-gated fact targets (see `agent.py`'s `_sex_compatible`) stay askable
   * exactly as before this existed.
   */
  start: async (message: string, profileId?: string | null): Promise<SimpleTriageTurnResponseDTO> => {
    try {
      const response = await axiosClient.post(
        "/api/v1/simple-triage/start",
        { message, profile_id: profileId ?? null },
        { timeout: TURN_TIMEOUT_MS },
      );
      return simpleTriageTurnResponseSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Khởi tạo phiên sàng lọc thất bại. Vui lòng thử lại sau.");
    }
  },

  /** `POST /simple-triage/chat/{sessionId}` */
  chat: async (sessionId: string, message: string): Promise<SimpleTriageTurnResponseDTO> => {
    try {
      const response = await axiosClient.post(
        `/api/v1/simple-triage/chat/${encodeURIComponent(sessionId)}`,
        { message },
        { timeout: TURN_TIMEOUT_MS },
      );
      return simpleTriageTurnResponseSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Gửi thông điệp thất bại. Phiên này có thể đã kết thúc.");
    }
  },

  /** `GET /simple-triage/sessions` */
  listSessions: async (): Promise<SimpleTriageSessionSummaryDTO[]> => {
    try {
      const response = await axiosClient.get("/api/v1/simple-triage/sessions");
      return simpleTriageSessionSummarySchema.array().parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không thể tải danh sách phiên.");
    }
  },

  /** `GET /simple-triage/sessions/{sessionId}` */
  getSession: async (sessionId: string): Promise<SimpleTriageSessionDetailDTO> => {
    try {
      const response = await axiosClient.get(
        `/api/v1/simple-triage/sessions/${encodeURIComponent(sessionId)}`,
      );
      return simpleTriageSessionDetailSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không thể tải nội dung phiên.");
    }
  },

  /**
   * `GET /simple-triage/sessions/{sessionId}/pdf` -- triggers a browser
   * download of the pilot's own SBAR handoff PDF. Deliberately its own small
   * function rather than reusing `@/lib/download-sbar-pdf.ts`: same blob/
   * anchor-click mechanics, but that helper is hardcoded to production's
   * `/triage/session/{id}/pdf` URL. Downloadable as soon as the session is
   * COMPLETED, regardless of nurse-review status -- see
   * `routes_simple_triage.py`'s `export_simple_triage_pdf` for why that's
   * safe (the PDF itself always states review status + reviewer honestly).
   */
  downloadPdf: async (sessionId: string): Promise<void> => {
    try {
      const response = await axiosClient.get<Blob>(
        `/api/v1/simple-triage/sessions/${encodeURIComponent(sessionId)}/pdf`,
        { responseType: "blob" },
      );
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `Phieu_SBAR_${sessionId.slice(-8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      return handlePilotApiError(error, "Không thể tạo phiếu SBAR lúc này.");
    }
  },

  /** `GET /simple-triage/chat/{sessionId}/care-team` */
  getCareTeamThread: async (sessionId: string): Promise<SimpleCareTeamThreadDTO> => {
    try {
      const response = await axiosClient.get(
        `/api/v1/simple-triage/chat/${encodeURIComponent(sessionId)}/care-team`,
      );
      return simpleCareTeamThreadSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không tải được kênh trao đổi với nhân viên y tế.");
    }
  },

  /** `POST /simple-triage/chat/{sessionId}/message-to-staff` */
  sendMessageToStaff: async (
    sessionId: string,
    content: string,
    clientMessageId: string,
  ): Promise<SimpleStaffConversationDTO> => {
    try {
      const response = await axiosClient.post(
        `/api/v1/simple-triage/chat/${encodeURIComponent(sessionId)}/message-to-staff`,
        { content, client_message_id: clientMessageId },
      );
      return simpleStaffConversationSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không gửi được tin nhắn tới nhân viên y tế.");
    }
  },

  /** `POST /simple-triage/chat/{sessionId}/mark-staff-read` */
  markStaffMessagesRead: async (sessionId: string): Promise<SimpleStaffConversationDTO> => {
    try {
      const response = await axiosClient.post(
        `/api/v1/simple-triage/chat/${encodeURIComponent(sessionId)}/mark-staff-read`,
      );
      return simpleStaffConversationSchema.parse(response.data);
    } catch (error) {
      return handlePilotApiError(error, "Không cập nhật được trạng thái đã đọc.");
    }
  },
};
