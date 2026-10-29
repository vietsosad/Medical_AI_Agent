import axios, { AxiosError } from "axios";
import { axiosClient } from "@/lib/api/axios.client";
import { UserProfile } from "@/store/useAuthStore";

// ============================================================================
// 1. ĐỊNH NGHĨA KHO THÔNG ĐIỆP (DTO INTERFACES - STRICT CONTRACTS)
// ============================================================================

export interface LoginRequestDTO {
  email: string;
  password: string;
}

export interface RegisterRequestDTO {
  name: string;
  email: string;
  password: string;
  department?: string;
  phoneNumber?: string;
}

export interface VerifyOtpRequestDTO {
  email?: string;
  code: string;
  purpose?: "REGISTRATION" | "PASSWORD_RESET" | "TWO_FACTOR";
}

export interface ForgotPasswordRequestDTO {
  email: string;
}

export interface ResetPasswordRequestDTO {
  email?: string;
  token?: string; // Token hoặc OTP khôi phục
  otp?: string;
  newPassword: string;
}

export interface AuthResponseDTO {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
  user: UserProfile;
}

export interface StandardMessageResponseDTO {
  success: boolean;
  message: string;
}

export interface OAuthUrlResponseDTO {
  url: string;
  provider: string;
}

export interface OAuthCallbackRequestDTO {
  code: string;
}

export interface UpdatePhoneNumberRequestDTO {
  /** Số điện thoại Việt Nam đã trim; null hoặc chuỗi rỗng nghĩa là gỡ bỏ số hiện tại. */
  phoneNumber: string | null;
}

// ============================================================================
// 2. HỆ THỐNG XỬ LÝ LỖI CHUẨN KHI GIAO TIẾP VỚI FASTAPI (8000)
// ============================================================================
const handleApiError = (error: unknown, fallbackMessage: string): never => {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<{ detail?: unknown; message?: unknown }>;

    // Nếu lỗi kết nối mạng (Network Error / Port 8000 down)
    if (!axiosErr.response) {
      console.error("[API Service Error] Máy chủ không phản hồi:", axiosErr.message);
      throw new Error("Không kết nối được tới hệ thống. Vui lòng kiểm tra mạng rồi thử lại.");
    }

    // Câu lỗi do backend viết là chuỗi tiếng Việt; lỗi 422 của Pydantic lại là
    // một mảng, hiện thẳng ra sẽ thành "[object Object]" -- khi đó dùng câu dự phòng.
    const backendMsg = axiosErr.response.data?.detail ?? axiosErr.response.data?.message;
    if (typeof backendMsg === "string" && backendMsg.trim()) {
      throw new Error(backendMsg);
    }
    throw new Error(fallbackMessage);
  }

  if (error instanceof Error) {
    throw error;
  }

  throw new Error(fallbackMessage);
};

// ============================================================================
// 3. AUTH SERVICE - TỔNG HỢP CÁC ENDPOINTS (FASTAPI MODULAR ROUTING)
// ============================================================================
export const authService = {
  /**
   * Tạo định danh khách không chứa PII để vào luồng triage khẩn cấp.
   */
  loginAsGuest: async (): Promise<AuthResponseDTO> => {
    try {
      const response = await axiosClient.post<AuthResponseDTO>("/api/v1/auth/guest");
      return response.data;
    } catch (error) {
      return handleApiError(
        error,
        "Không thể khởi tạo phiên khám nhanh. Vui lòng thử lại hoặc gọi 115 nếu đang nguy cấp.",
      );
    }
  },

  /**
   * Đăng nhập vào hệ thống AI Triage (POST /api/v1/auth/login)
   */
  login: async (payload: LoginRequestDTO): Promise<AuthResponseDTO> => {
    try {
      const response = await axiosClient.post<AuthResponseDTO>("/api/v1/auth/login", payload);
      return response.data;
    } catch (error) {
      return handleApiError(error, "Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin xác thực.");
    }
  },

  /**
   * Đăng ký mới tài khoản Y khoa (POST /api/v1/auth/register)
   */
  register: async (payload: RegisterRequestDTO): Promise<AuthResponseDTO | StandardMessageResponseDTO> => {
    try {
      const response = await axiosClient.post<AuthResponseDTO | StandardMessageResponseDTO>(
        "/api/v1/auth/register",
        payload
      );
      return response.data;
    } catch (error) {
      return handleApiError(error, "Đăng ký tài khoản thất bại. Email có thể đã tồn tại trên hệ thống.");
    }
  },

  /**
   * Xác thực mã PIN 6 chữ số (POST /api/v1/auth/verify-otp)
   */
  verifyOtp: async (payload: VerifyOtpRequestDTO): Promise<AuthResponseDTO | StandardMessageResponseDTO> => {
    try {
      const response = await axiosClient.post<AuthResponseDTO | StandardMessageResponseDTO>(
        "/api/v1/auth/verify-otp",
        payload
      );
      return response.data;
    } catch (error) {
      return handleApiError(error, "Mã xác minh y khoa OTP không hợp lệ hoặc đã hết hạn.");
    }
  },

  /**
   * Yêu cầu gửi mã OTP/link khôi phục mật khẩu (POST /api/v1/auth/forgot-password)
   */
  forgotPassword: async (payload: ForgotPasswordRequestDTO): Promise<StandardMessageResponseDTO> => {
    try {
      const response = await axiosClient.post<StandardMessageResponseDTO>(
        "/api/v1/auth/forgot-password",
        payload
      );
      return response.data;
    } catch (error) {
      return handleApiError(error, "Yêu cầu khôi phục thất bại. Vui lòng thử lại sau.");
    }
  },

  /**
   * Gửi lại mã xác minh đăng ký (POST /api/v1/auth/resend-registration-otp).
   * Máy chủ trả cùng một câu cho mọi email và mã mới huỷ mã cũ.
   */
  resendRegistrationOtp: async (payload: ForgotPasswordRequestDTO): Promise<StandardMessageResponseDTO> => {
    try {
      const response = await axiosClient.post<StandardMessageResponseDTO>(
        "/api/v1/auth/resend-registration-otp",
        payload
      );
      return response.data;
    } catch (error) {
      return handleApiError(error, "Chưa gửi lại được mã. Vui lòng thử lại sau.");
    }
  },

  /**
   * Thực thi đặt lại mật khẩu mới cùng mã xác thực (POST /api/v1/auth/reset-password)
   */
  resetPassword: async (payload: ResetPasswordRequestDTO): Promise<StandardMessageResponseDTO> => {
    try {
      const response = await axiosClient.post<StandardMessageResponseDTO>(
        "/api/v1/auth/reset-password",
        payload
      );
      return response.data;
    } catch (error) {
      return handleApiError(error, "Cập nhật mật khẩu thất bại. Mã xác nhận có thể đã hết thời gian hiệu lực.");
    }
  },

  /**
   * Lấy thông tin hồ sơ định danh hiện tại qua Token (GET /api/v1/auth/me)
   */
  getMe: async (): Promise<UserProfile> => {
    try {
      const response = await axiosClient.get<UserProfile>("/api/v1/auth/me");
      return response.data;
    } catch (error) {
      return handleApiError(error, "Không thể xác minh định danh từ máy chủ (Token hết hạn hoặc vô hiệu).");
    }
  },

  /**
   * Cập nhật số điện thoại liên lạc của CHÍNH tài khoản đang đăng nhập
   * → PATCH /api/v1/auth/me/phone
   *
   * Không gửi kèm user id: máy chủ luôn lấy danh tính từ Bearer Token, nên client
   * không thể sửa thông tin liên lạc của người khác.
   */
  updatePhoneNumber: async (phoneNumber: string | null): Promise<UserProfile> => {
    try {
      const payload: UpdatePhoneNumberRequestDTO = { phoneNumber };
      const response = await axiosClient.patch<UserProfile>("/api/v1/auth/me/phone", payload);
      return response.data;
    } catch (error) {
      return handleApiError(error, "Cập nhật số điện thoại thất bại. Vui lòng thử lại sau.");
    }
  },

  /**
   * Lấy đường link chuyển hướng đăng nhập OAuth 2.0 (GET /api/v1/auth/oauth/{provider}/url)
   */
  getOAuthUrl: async (provider: "google" | "github"): Promise<OAuthUrlResponseDTO> => {
    try {
      const response = await axiosClient.get<OAuthUrlResponseDTO>(`/api/v1/auth/oauth/${provider}/url`);
      return response.data;
    } catch (error) {
      return handleApiError(error, `Không thể lấy đường dẫn xác thực OAuth cho ${provider}.`);
    }
  },

  /**
   * Tráo đổi mã Authorization Code lấy Tokens & thông tin hồ sơ định danh (POST /api/v1/auth/oauth/{provider}/callback)
   */
  oauthCallback: async (provider: string, code: string): Promise<AuthResponseDTO> => {
    try {
      const payload: OAuthCallbackRequestDTO = { code };
      const response = await axiosClient.post<AuthResponseDTO>(`/api/v1/auth/oauth/${provider}/callback`, payload);
      return response.data;
    } catch (error) {
      return handleApiError(error, `Định danh OAuth qua ${provider} thất bại hoặc mã xác nhận đã hết hạn.`);
    }
  },

  /**
   * Hủy phiên Đăng nhập trên Server (POST /api/v1/auth/logout)
   */
  logout: async (): Promise<StandardMessageResponseDTO> => {
    try {
      const response = await axiosClient.post<StandardMessageResponseDTO>("/api/v1/auth/logout");
      return response.data;
    } catch (error) {
      // Khi logout thất bại trên server, trả về message giả định để phía client vẫn thanh tẩy state bình thường
      console.warn("⚠️ [Auth Service] Ngoại lệ khi ngắt phiên server-side:", error);
      return { success: true, message: "Logged out locally." };
    }
  },
};
