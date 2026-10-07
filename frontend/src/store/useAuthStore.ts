import { create } from "zustand";
import Cookies from "js-cookie";
import { authService } from "@/services/auth.service";

// ============================================================================
// 1. BIẾN MÔI TRƯỜNG & CẤU HÌNH KEY COOKIE
// ============================================================================
const ACCESS_TOKEN_KEY = process.env.NEXT_PUBLIC_ACCESS_TOKEN_KEY || "ai20k_access_token";
const REFRESH_TOKEN_KEY = process.env.NEXT_PUBLIC_REFRESH_TOKEN_KEY || "ai20k_refresh_token";

// ============================================================================
// 2. ĐỊNH NGHĨA TYPESCRIPT CHO PHIÊN ĐĂNG NHẬP (STRICT CONTRACT)
// ============================================================================

/**
 * Các vai trò người dùng trong hệ thống Clinical AI Triage (RBAC Registry)
 */
export type UserRole = 
  | "PATIENT" 
  | "GUEST" 
  | "CLINICAL_NURSE" 
  | "SYSTEM_ADMIN" 
  | "AI_OPS";

/**
 * Thông tin định danh của nhân viên lâm sàng hoặc Bệnh nhân trong hệ thống
 */
export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
  department?: string; // Ví dụ: "Khoa Cấp Cứu Triage ESI", "Khoa Tim Mạch"
  phoneNumber?: string;
  /**
   * Năng lực bổ sung ngoài quyền nền của vai trò, ví dụ SPECIALIST_REVIEW của
   * bác sĩ. Tài khoản bác sĩ dùng chung vai trò công khai CLINICAL_NURSE nên
   * đây là chỗ duy nhất phân biệt được hai loại nhân viên lâm sàng.
   */
  capabilities?: string[];
}

/**
 * Interface Quản lý Trang Thái (State)
 */
export interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

/**
 * Interface Quản lý Các Hành Động (Actions / Mutations)
 */
export interface AuthActions {
  /**
   * Cập nhật thông tin người dùng và lưu trữ Access/Refresh Tokens vào Cookie sau khi Login
   */
  loginSuccess: (user: UserProfile, accessToken: string, refreshToken?: string) => void;
  
  /**
   * Xóa token khỏi Cookie, xả sạch bộ nhớ State và thông báo hủy phiên tới Backend
   */
  logout: (shouldRedirect?: boolean) => Promise<void>;
  
  /**
   * Hàm khôi phục (Hydration) chạy lúc tải trang: kiểm tra Token ở Cookie và gọi API /me
   */
  hydrate: () => Promise<void>;

  /**
   * Các setter cập nhật thông tin UI thủ công khi cần (ví dụ: sau khi chỉnh sửa Profile)
   */
  setUser: (user: UserProfile | null) => void;
  setError: (error: string | null) => void;
}

export type AuthStore = AuthState & AuthActions;

// ============================================================================
// 3. KHỞI TẠO ZUSTAND STORE HOÀN CHỈNH (CLIENT SESSION OWNERSHIP)
// ============================================================================
export const useAuthStore = create<AuthStore>((set) => ({
  // --- TRẠNG THÁI KHỞI TẠO (INITIAL STATE) ---
  user: null,
  isAuthenticated: false,
  isLoading: true, // Mặc định true để chờ hydrate thi hành lúc load trang
  error: null,

  // --- ACTIONS IMPLEMENTATION ---

  setUser: (user: UserProfile | null) => {
    set({
      user,
      isAuthenticated: !!user,
      error: null,
    });
  },

  setError: (error: string | null) => {
    set({ error });
  },

  loginSuccess: (user: UserProfile, accessToken: string, refreshToken?: string) => {
    const isHttps = typeof window !== "undefined" && window.location.protocol === "https:";

    // 1. Lưu Access Token vào Cookie (Thời hạn 1 ngày)
    Cookies.set(ACCESS_TOKEN_KEY, accessToken, {
      secure: isHttps,
      sameSite: "strict",
      path: "/",
      expires: 1,
    });

    // 2. Lưu Refresh Token vào Cookie (Thời hạn 7 ngày)
    if (refreshToken) {
      Cookies.set(REFRESH_TOKEN_KEY, refreshToken, {
        secure: isHttps,
        sameSite: "strict",
        path: "/",
        expires: 7,
      });
    }

    // 3. Cập nhật Zustand State
    set({
      user,
      isAuthenticated: true,
      isLoading: false,
      error: null,
    });

  },

  logout: async (shouldRedirect: boolean = true) => {
    set({ isLoading: true });

    try {
      // Tùy chọn: Gọi API thu hồi quyền hạn / chốt sổ Audit Ledger trên Backend FastAPI
      const accessToken = Cookies.get(ACCESS_TOKEN_KEY);
      if (accessToken) {
        await authService.logout().catch((err: unknown) => {
          // Chỉ log lỗi nhẹ, không ngắt luồng logout vì mục tiêu quan trọng nhất là xóa sạch phía Client
          console.warn("⚠️ Bỏ qua lỗi ngắt phiên trên Backend Server:", err);
        });
      }
    } finally {
      // 1. Xóa sạch toàn bộ Tokens ra khỏi Cookie
      Cookies.remove(ACCESS_TOKEN_KEY, { path: "/" });
      Cookies.remove(REFRESH_TOKEN_KEY, { path: "/" });

      // 2. Đón trắng toàn bộ thông tin phiên làm việc trong Memory State
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });


      // 3. Tự động chuyển hướng về trang Đăng Nhập nếu được yêu cầu
      if (shouldRedirect && typeof window !== "undefined") {
        if (!window.location.pathname.startsWith("/auth/")) {
          window.location.href = "/auth/login?reason=logout";
        }
      }
    }
  },

  hydrate: async () => {
    set({ isLoading: true, error: null });

    const accessToken = Cookies.get(ACCESS_TOKEN_KEY);

    // Trường hợp 1: Không có token trong Cookie -> Đưa về trạng thái Guest / Chưa đăng nhập
    if (!accessToken) {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
      return;
    }

    // Trường hợp 2: Có Token -> Gọi API /api/v1/auth/me để kiểm chứng hợp lệ và bồi đắp thông tin User
    try {
      
      // authService.getMe() sẽ gọi qua axiosClient và tự động xử lý 401 Refresh ngầm nếu Token hết hạn!
      const userProfile = await authService.getMe();

      set({
        user: userProfile,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });

    } catch (error) {
      console.error("❌ [Zustand Hydration] Token không hợp lệ hoặc đã bị xả bỏ:", error);

      // Nếu gia hạn Token thất bại, làm sạch hoàn toàn Cookie và chuyển trạng thái về Chưa đăng nhập
      Cookies.remove(ACCESS_TOKEN_KEY, { path: "/" });
      Cookies.remove(REFRESH_TOKEN_KEY, { path: "/" });

      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: "Phiên đăng nhập đã hết hiệu lực. Vui lòng xác thực lại tài khoản.",
      });
    }
  },
}));
