import axios from "axios";
import { axiosClient } from "@/lib/api/axios.client";

// ============================================================================
// 1. ĐỊNH NGHĨA KHO THÔNG ĐIỆP (DTO INTERFACES - STRICT CONTRACTS)
// Ánh xạ 100% với backend src/models/profile_schemas.py
// ============================================================================

export type RelationshipType = "SELF" | "CHILD" | "SPOUSE" | "PARENT" | "SIBLING" | "OTHER";
export type AvatarColorToken = "emerald" | "blue" | "purple" | "rose" | "amber" | "zinc" | "slate";
export type GenderType = "MALE" | "FEMALE" | "OTHER";
export type BloodTypeValue = "A+" | "A-" | "B+" | "B-" | "O+" | "O-" | "AB+" | "AB-" | "UNKNOWN";
export type EmergencyRelationshipType = "SPOUSE" | "PARENT" | "CHILD" | "SIBLING" | "FRIEND" | "OTHER";

export interface ProfileResponseDTO {
  id: string;
  user_id: string;
  full_name: string;
  relationship_type: RelationshipType;
  is_primary: boolean;
  dob: string | null;
  avatar_color: AvatarColorToken;

  age: number | null;
  gender: GenderType | null;
  blood_type: BloodTypeValue | null;
  height_cm: number | null;
  weight_kg: number | null;

  chronic_conditions: string[] | null;
  daily_medications: string[] | null;
  allergies: string[] | null;

  /** Số liên lạc của chính thành viên này (khác với emergency_contact_phone). */
  phone_number: string | null;

  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  updated_at: string | null;
}

export interface CreateProfileRequestDTO {
  full_name: string;
  relationship_type: RelationshipType;
  dob?: string | null;
  age?: number | null;
  gender?: GenderType | null;
  avatar_color?: AvatarColorToken;
  blood_type?: BloodTypeValue | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  chronic_conditions?: string[] | null;
  daily_medications?: string[] | null;
  allergies?: string[] | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  phone_number?: string | null;
}

export interface UpdateProfileRequestDTO {
  full_name?: string;
  relationship_type?: RelationshipType;
  dob?: string | null;
  age?: number | null;
  gender?: GenderType | null;
  avatar_color?: AvatarColorToken;

  blood_type?: BloodTypeValue | null;
  height_cm?: number | null;
  weight_kg?: number | null;

  chronic_conditions?: string[] | null;
  daily_medications?: string[] | null;
  allergies?: string[] | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  phone_number?: string | null;
}

export interface DeleteProfileResponseDTO {
  success: boolean;
  message: string;
}

// ============================================================================
// 2. BỘ XỬ LÝ LỖI CHUẨN HOÁ
// ============================================================================
const handleApiError = (error: unknown, fallbackMessage: string): never => {
  if (axios.isAxiosError(error)) {
    const serverMessage = error.response?.data?.detail || error.response?.data?.message;
    if (serverMessage && typeof serverMessage === "string") {
      throw new Error(serverMessage);
    }
  }
  if (error instanceof Error) {
    throw error;
  }
  throw new Error(fallbackMessage);
};

// ============================================================================
// 3. PROFILE SERVICE — HỆ THỐNG GIAO TIẾP API FASTAPI
// Ánh xạ đầy đủ tới: src/api/routes_profiles.py
// ============================================================================
export const profileService = {
  /**
   * Lấy danh sách toàn bộ hồ sơ trong gia đình thuộc thẩm quyền tài khoản
   * → GET /api/v1/profiles
   */
  getProfiles: async (): Promise<ProfileResponseDTO[]> => {
    try {
      const response = await axiosClient.get<ProfileResponseDTO[]>("/api/v1/profiles");
      return response.data;
    } catch (error) {
      return handleApiError(error, "Không thể tải danh sách hồ sơ gia đình. Vui lòng kiểm tra lại kết nối mạng.");
    }
  },

  /**
   * Tạo nhanh hồ sơ thân nhân gia đình (<15s Onboarding)
   * → POST /api/v1/profiles
   */
  createProfile: async (payload: CreateProfileRequestDTO): Promise<ProfileResponseDTO> => {
    try {
      const response = await axiosClient.post<ProfileResponseDTO>("/api/v1/profiles", payload);
      return response.data;
    } catch (error) {
      return handleApiError(error, "Thêm mới hồ sơ người thân thất bại. Vui lòng thử lại sau.");
    }
  },

  /**
   * Truy vấn chi tiết một hồ sơ y khoa cụ thể
   * → GET /api/v1/profiles/{id}
   */
  getProfileById: async (profileId: string): Promise<ProfileResponseDTO> => {
    try {
      const response = await axiosClient.get<ProfileResponseDTO>(`/api/v1/profiles/${profileId}`);
      return response.data;
    } catch (error) {
      return handleApiError(error, "Hồ sơ y tế này không tồn tại hoặc bạn không có thẩm quyền truy cập.");
    }
  },

  /**
   * Cập nhật thông tin cơ bản / sinh trắc học / bệnh nền
   * → PUT /api/v1/profiles/{id}
   */
  updateProfile: async (profileId: string, payload: UpdateProfileRequestDTO): Promise<ProfileResponseDTO> => {
    try {
      const response = await axiosClient.put<ProfileResponseDTO>(`/api/v1/profiles/${profileId}`, payload);
      return response.data;
    } catch (error) {
      return handleApiError(error, "Cập nhật thông tin y tế thất bại. Vui lòng kiểm tra lại quyền thực hiện.");
    }
  },

  /**
   * Xóa hồ sơ thân nhân phụ thuộc (KHÔNG thể xóa hồ sơ SELF)
   * → DELETE /api/v1/profiles/{id}
   */
  deleteProfile: async (profileId: string): Promise<DeleteProfileResponseDTO> => {
    try {
      const response = await axiosClient.delete<DeleteProfileResponseDTO>(`/api/v1/profiles/${profileId}`);
      return response.data;
    } catch (error) {
      return handleApiError(
        error,
        "Không thể xóa hồ sơ này. Ghi chú: Hồ sơ gốc chính chủ (SELF) không thể bị loại bỏ."
      );
    }
  },
};
