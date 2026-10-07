import axios from "axios";
import { axiosClient } from "@/lib/api/axios.client";

// ============================================================================
// DTO — ánh xạ 100% với backend src/models/health_schemas.py
// ============================================================================

export interface HealthTopicSummaryDTO {
  slug: string;
  name: string;
  summary: string;
  symptoms: string[];
  prevention: string[];
  source: string;
  source_url: string;
  last_updated: string;
  /** True khi phần tóm tắt đã được mô hình ngôn ngữ diễn giải lại từ nội dung seed. */
  ai_assisted: boolean;
}

export interface HealthTopicDetailDTO extends HealthTopicSummaryDTO {
  warning_signs: string[];
  when_to_seek_care: string;
  /** Lời miễn trừ do server phát ra; giao diện không tự viết lời riêng. */
  disclaimer: string;
}

const handleApiError = (error: unknown, fallbackMessage: string): never => {
  if (axios.isAxiosError(error)) {
    const serverMessage = error.response?.data?.detail || error.response?.data?.message;
    if (serverMessage && typeof serverMessage === "string") {
      throw new Error(serverMessage);
    }
  }
  if (error instanceof Error) throw error;
  throw new Error(fallbackMessage);
};

/**
 * ============================================================================
 * HEALTH EDUCATION SERVICE — NỘI DUNG SỨC KHỎE CÔNG KHAI
 * ============================================================================
 * Endpoint công khai: khách chưa đăng nhập vẫn đọc được. Chỉ nút "Kiểm tra
 * triệu chứng với AI" mới đi qua luồng đăng nhập hiện có.
 *
 * Backend trả về nội dung đã xử lý sẵn (kể cả phần LLM diễn giải), nên các hàm
 * ở đây không bao giờ gọi thẳng tới mô hình ngôn ngữ.
 */
export const healthService = {
  /** GET /api/v1/health-topics — danh sách thẻ hiển thị trên trang chủ. */
  getTopics: async (): Promise<HealthTopicSummaryDTO[]> => {
    try {
      const response = await axiosClient.get<HealthTopicSummaryDTO[]>("/api/v1/health-topics");
      return response.data;
    } catch (error) {
      return handleApiError(error, "Không thể tải thông tin sức khỏe lúc này.");
    }
  },

  /** GET /api/v1/health-topics/{slug} — nội dung đầy đủ cho màn hình chi tiết. */
  getTopicBySlug: async (slug: string): Promise<HealthTopicDetailDTO> => {
    try {
      const response = await axiosClient.get<HealthTopicDetailDTO>(
        `/api/v1/health-topics/${encodeURIComponent(slug)}`,
      );
      return response.data;
    } catch (error) {
      return handleApiError(error, "Không thể tải nội dung chủ đề sức khỏe này.");
    }
  },
};
