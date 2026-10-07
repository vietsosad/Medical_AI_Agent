import axios, { AxiosError } from "axios";
import Cookies from "js-cookie";
import { axiosClient } from "@/lib/api/axios.client";
import type {
  AgentStreamEvent,
  ChatMessage,
  DecisionStatus,
  EvidenceStatus,
  IntakeConfirmationStatus,
  IntakeSummary,
  WorkflowPhase,
} from "@/types/triage-chat";
import type {
  HitlReviewStatus,
  TriageHistoryListItemDTO,
  TriageSessionDetailDTO,
} from "@/types/clinical-history";
import {
  agentStreamEventSchema,
  chatMessageSchema,
  sessionMessagesResponseSchema,
  startTriageResponseSchema,
} from "@/schemas/triage-stream.schema";
import {
  TriageHistoryListItemSchema,
  TriageSessionDetailSchema,
} from "@/lib/validations/clinical-history.schema";

// ============================================================================
// 1. ĐỊNH NGHĨA KHO THÔNG ĐIỆP (DTO INTERFACES - STRICT CONTRACTS)
// ============================================================================

export interface StartTriageRequestDTO {
  profile_id?: string | null;
  initial_symptom: string;
  /**
   * Slug chủ đề sức khỏe người dùng vừa đọc trên trang chủ. Chỉ là mối quan tâm,
   * KHÔNG phải triệu chứng khai báo: backend dùng nó để cá nhân hóa lời chào mở
   * đầu và không bao giờ ghi vào trạng thái lâm sàng.
   */
  health_topic?: string | null;
}

export interface StartTriageResponseDTO {
  session_id: string;
  status: TriageSessionStatus;
  message: string;
  is_red_flag: boolean;
}

export interface PatientChatInputDTO {
  message?: string | null;
  selected_option?: string | null;
  selected_option_id?: string | null;
  step?: number;
  confirm_intake?: boolean;
}

export interface HistoryListResponseDTO {
  items: TriageHistoryListItemDTO[];
}

export interface SessionStatusDTO {
  session_id: string;
  status: TriageSessionStatus;
  profile_id?: string | null;
  ai_proposed_esi?: number | null;
  final_esi?: number | null;
  hitl_status: HitlReviewStatus;
  reviewer_name?: string | null;
  reviewed_at?: string | null;
  decision_type?: "CONFIRM_ESI" | "ADJUST_ESI" | null;
  decision_note?: string | null;
  is_red_flag_triggered: boolean;
  created_at: string;
  updated_at?: string | null;
  sbar_summary?: unknown;
  sbar_finalized: boolean;
  intake_confirmation_status: IntakeConfirmationStatus;
  intake_summary?: IntakeSummary | null;
  workflow_phase?: WorkflowPhase | null;
  decision_status?: DecisionStatus | null;
  evidence_status?: EvidenceStatus | null;
  retrieval_degraded_modes: string[];
  care_team_name?: string | null;
  care_team_status?: CareTeamStatus;
  unread_from_staff?: number;
}

/** Trạng thái ca diễn đạt theo ngôn ngữ người bệnh hiểu được. */
export type CareTeamStatus =
  | "AI_SCREENING"
  | "WAITING_REVIEW"
  | "STAFF_REVIEWING"
  | "SPECIALIST_REVIEW"
  | "COMPLETED";

export interface CareTeamMessageDTO {
  id: string;
  /** Không có 'bot': kênh này chỉ có hai con người. */
  sender: "patient" | "staff";
  senderName: string | null;
  content: string;
  createdAt: string;
  readAt: string | null;
}

export interface CareTeamThreadDTO {
  session_id: string;
  care_team_name: string | null;
  care_team_status: CareTeamStatus;
  unread_from_staff: number;
  messages: CareTeamMessageDTO[];
}

export interface StaffConversationDTO {
  session_id: string;
  care_team_name: string | null;
  care_team_status: CareTeamStatus;
  unread_from_staff: number;
}

export type TriageSessionStatus =
  | "IN_PROGRESS"
  | "HITL_REVIEWING"
  | "COMPLETED"
  | "RED_FLAG_LOCKED"
  | "CANCELLED";

export interface SessionMessagesResponseDTO {
  session_status: SessionStatusDTO;
  messages: ChatMessage[];
}

// ============================================================================
// 2. HỆ THỐNG XỬ LÝ LỖI CHUẨN KHI GIAO TIẾP VỚI FASTAPI
// ============================================================================
const handleApiError = (error: unknown, fallbackMessage: string): never => {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<{ detail?: string; message?: string }>;
    if (!axiosErr.response) {
      throw new Error("Không thể kết nối tới máy chủ AI Triage FastAPI. Vui lòng kiểm tra dịch vụ Backend.");
    }
    const backendMsg = axiosErr.response.data?.detail || axiosErr.response.data?.message;
    if (backendMsg) {
      throw new Error(backendMsg);
    }
  }
  if (error instanceof Error) {
    throw error;
  }
  throw new Error(fallbackMessage);
};

export class TriageStreamError extends Error {
  constructor(
    message: string,
    readonly errorCode: string,
    readonly retryable: boolean,
  ) {
    super(message);
    this.name = "TriageStreamError";
  }
}

const parseSseBlock = (block: string): AgentStreamEvent | null => {
  const data = block
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (!data) return null;

  let rawEvent: unknown;
  try {
    rawEvent = JSON.parse(data);
  } catch {
    throw new TriageStreamError(
      "Máy chủ trả về sự kiện SSE không phải JSON hợp lệ.",
      "INVALID_SSE_JSON",
      true,
    );
  }
  const parsedEvent = agentStreamEventSchema.safeParse(rawEvent);
  if (!parsedEvent.success) {
    throw new TriageStreamError(
      "Máy chủ trả về sự kiện không đúng hợp đồng dữ liệu.",
      "INVALID_SSE_CONTRACT",
      true,
    );
  }
  return parsedEvent.data;
};

export const splitSseBuffer = (
  buffer: string,
): { blocks: string[]; remainder: string } => {
  const parts = buffer.split(/\r?\n\r?\n/);
  return { blocks: parts.slice(0, -1), remainder: parts.at(-1) ?? "" };
};

const readHttpError = async (response: Response): Promise<string> => {
  try {
    const payload = (await response.json()) as { detail?: unknown; message?: unknown };
    const detail = payload.detail ?? payload.message;
    if (typeof detail === "string" && detail.trim()) return detail;
  } catch {
    // The status code below remains useful when the server did not return JSON.
  }
  return `Lỗi máy chủ (${response.status}).`;
};

// ============================================================================
// 3. TRIAGE SERVICE - TỔNG HỢP ENDPOINTS (FASTAPI MODULAR ROUTING)
// ============================================================================
export const triageService = {
  /**
   * Khởi xướng ca khám Triage mới (POST /api/v1/triage/start)
   */
  startTriage: async (payload: StartTriageRequestDTO): Promise<StartTriageResponseDTO> => {
    try {
      const response = await axiosClient.post<StartTriageResponseDTO>("/api/v1/triage/start", payload);
      return startTriageResponseSchema.parse(response.data);
    } catch (error) {
      return handleApiError(error, "Khởi xướng ca khám thất bại. Vui lòng thử lại sau.");
    }
  },

  submitChatTurn: async (sessionId: string, payload: PatientChatInputDTO): Promise<ChatMessage> => {
    try {
      const response = await axiosClient.post<ChatMessage>(`/api/v1/triage/chat/${sessionId}`, payload);
      return chatMessageSchema.parse(response.data);
    } catch (error) {
      return handleApiError(error, "Gửi thông điệp thất bại. Phiên khám có thể đã bị ngắt kết nối hoặc đã kết thúc.");
    }
  },

  /**
   * Gửi phản hồi tin nhắn hoặc thẻ trắc nghiệm và nhận luồng SSE trạng thái (POST /api/v1/triage/chat/{sessionId})
   */
  submitChatTurnStream: async (
    sessionId: string,
    payload: PatientChatInputDTO,
    onProgress: (event: AgentStreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<ChatMessage> => {
    try {
      const openStream = () => {
        const accessToken = Cookies.get(
          process.env.NEXT_PUBLIC_ACCESS_TOKEN_KEY || "ai20k_access_token",
        );
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
        return fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/triage/chat/${sessionId}`,
          {
            method: "POST",
            headers,
            body: JSON.stringify(payload),
            credentials: "include",
            signal,
          },
        );
      };

      let response = await openStream();
      if (response.status === 401) {
        // A rejected authorization request has not entered the clinical turn.
        // Reuse the shared interceptor to rotate credentials, then open SSE once.
        await axiosClient.get("/api/v1/auth/me", { signal });
        response = await openStream();
      }

      if (!response.ok) {
        throw new TriageStreamError(
          await readHttpError(response),
          `HTTP_${response.status}`,
          response.status >= 500,
        );
      }

      if (!response.body) {
        throw new Error("Không có dữ liệu trả về từ máy chủ.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const { blocks, remainder } = splitSseBuffer(buffer);
          buffer = remainder;

          for (const block of blocks) {
            const event = parseSseBlock(block);
            if (!event) continue;
            onProgress(event);
            if (event.type === "result" && event.result) {
              return event.result;
            }
            if (
              event.type === "error" &&
              event.errorCode &&
              event.retryable != null
            ) {
              throw new TriageStreamError(
                event.message,
                event.errorCode,
                event.retryable,
              );
            }
          }
        }

        buffer += decoder.decode();
        const finalEvent = parseSseBlock(buffer);
        if (finalEvent) {
          onProgress(finalEvent);
          if (finalEvent.type === "result" && finalEvent.result) {
            return finalEvent.result;
          }
          if (
            finalEvent.type === "error" &&
            finalEvent.errorCode &&
            finalEvent.retryable != null
          ) {
            throw new TriageStreamError(
              finalEvent.message,
              finalEvent.errorCode,
              finalEvent.retryable,
            );
          }
        }
      } finally {
        reader.releaseLock();
      }
      throw new Error("Luồng dữ liệu kết thúc mà không có kết quả hoàn chỉnh.");
    } catch (error) {
      // DOMException (the runtime's real AbortError) does not extend Error,
      // so identity must be checked by name rather than `instanceof Error`.
      if (error && typeof error === "object" && "name" in error && error.name === "AbortError") {
        throw error;
      }
      if (error instanceof Error) throw error;
      throw new Error("Gửi thông điệp thất bại. Vui lòng thử lại.");
    }
  },

  /**
   * Lấy lịch sử hội thoại của 1 ca khám (GET /api/v1/triage/chat/{sessionId}/messages)
   */
  getSessionMessages: async (sessionId: string): Promise<SessionMessagesResponseDTO> => {
    try {
      const response = await axiosClient.get<SessionMessagesResponseDTO>(`/api/v1/triage/chat/${sessionId}/messages`);
      return sessionMessagesResponseSchema.parse(response.data);
    } catch (error) {
      return handleApiError(error, "Không thể tải nội dung hội thoại từ máy chủ.");
    }
  },

  /**
   * Tra cứu danh sách lịch sử ca bệnh cũ của Bệnh nhân (GET /api/v1/triage/history)
   */
  /** Luồng trao đổi với nhân viên y tế, tách khỏi hội thoại hỏi bệnh của AI. */
  getCareTeamThread: async (sessionId: string): Promise<CareTeamThreadDTO> => {
    try {
      const response = await axiosClient.get<CareTeamThreadDTO>(
        `/api/v1/triage/chat/${encodeURIComponent(sessionId)}/care-team`,
      );
      return response.data;
    } catch (error) {
      return handleApiError(error, "Không tải được kênh trao đổi với nhân viên y tế.");
    }
  },

  /** Người bệnh nhắn cho nhân viên lâm sàng đang phụ trách ca của mình. */
  sendMessageToStaff: async (
    sessionId: string,
    content: string,
    clientMessageId: string,
  ): Promise<StaffConversationDTO> => {
    try {
      const response = await axiosClient.post<StaffConversationDTO>(
        `/api/v1/triage/chat/${encodeURIComponent(sessionId)}/message-to-staff`,
        { content, clientMessageId },
      );
      return response.data;
    } catch (error) {
      return handleApiError(error, "Không gửi được tin nhắn tới nhân viên y tế.");
    }
  },

  /** Đánh dấu đã đọc các tin của nhân viên lâm sàng. */
  markStaffMessagesRead: async (sessionId: string): Promise<StaffConversationDTO> => {
    try {
      const response = await axiosClient.post<StaffConversationDTO>(
        `/api/v1/triage/chat/${encodeURIComponent(sessionId)}/mark-staff-read`,
      );
      return response.data;
    } catch (error) {
      return handleApiError(error, "Không cập nhật được trạng thái đã đọc.");
    }
  },

  getPatientHistory: async (): Promise<HistoryListResponseDTO> => {
    try {
      const response = await axiosClient.get<HistoryListResponseDTO>("/api/v1/triage/history");
      return {
        items: TriageHistoryListItemSchema.array().parse(response.data.items),
      };
    } catch (error) {
      return handleApiError(error, "Không thể tải danh sách lịch sử phiên khám y tế.");
    }
  },

  /**
   * Tra cứu chi tiết ca bệnh cũ (Read-Only Replay, toàn văn SBAR & chữ ký) (GET /api/v1/triage/history/{sessionId})
   */
  getSessionReplayDetail: async (sessionId: string): Promise<TriageSessionDetailDTO> => {
    try {
      const response = await axiosClient.get<TriageSessionDetailDTO>(`/api/v1/triage/history/${sessionId}`);
      return TriageSessionDetailSchema.parse(response.data);
    } catch (error) {
      return handleApiError(error, "Không thể tra cứu hồ sơ chi tiết và chữ ký thẩm định của ca bệnh.");
    }
  },
};
