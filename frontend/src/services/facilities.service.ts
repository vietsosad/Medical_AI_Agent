import axios, { AxiosError } from "axios";
import { ZodError } from "zod";

import { axiosClient } from "@/lib/api/axios.client";
import { nearbyFacilitiesResponseSchema } from "@/schemas/facilities.schema";
import type { NearbyFacilitiesRequestDTO, NearbyFacilitiesResponseDTO } from "@/types/facilities";

/**
 * Client mỏng cho `/api/v1/facilities/nearby` (`src/api/routes_facilities.py`).
 *
 * Toạ độ đi trong **thân request**, không phải query string: vị trí của một
 * người đang cấp cứu không nên đọng lại trong access log của web server, trong
 * lịch sử trình duyệt hay trong header `Referer`.
 *
 * Backend đã tự nuốt mọi sự cố hạ tầng thành cờ `degraded` kèm dữ liệu dự
 * phòng, nên một lỗi ném ra từ đây gần như luôn là lỗi mạng hoặc lỗi phiên đăng
 * nhập -- thông điệp vì thế nói đúng chuyện đó thay vì đổ cho "không tìm thấy
 * cơ sở y tế nào".
 */

const handleFacilityApiError = (error: unknown): never => {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<{ detail?: string; message?: string }>;
    if (!axiosErr.response) {
      throw new Error("Không kết nối được tới máy chủ. Vui lòng kiểm tra mạng rồi thử lại.");
    }
    if (axiosErr.response.status === 401) {
      throw new Error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại để tra cứu cơ sở y tế.");
    }
    const backendMessage = axiosErr.response.data?.detail || axiosErr.response.data?.message;
    if (backendMessage) {
      throw new Error(backendMessage);
    }
  }
  // Lệch schema là lỗi của chính tầng frontend này, không phải lỗi người dùng.
  if (error instanceof ZodError) {
    throw new Error("Dữ liệu máy chủ trả về không đúng hợp đồng dữ liệu của tính năng tìm cơ sở y tế.");
  }
  throw new Error("Không tra cứu được cơ sở y tế gần bạn. Vui lòng thử lại.");
};

export const facilitiesService = {
  async searchNearby(payload: NearbyFacilitiesRequestDTO): Promise<NearbyFacilitiesResponseDTO> {
    try {
      const { data } = await axiosClient.post("/api/v1/facilities/nearby", payload);
      return nearbyFacilitiesResponseSchema.parse(data);
    } catch (error) {
      return handleFacilityApiError(error);
    }
  },
};
