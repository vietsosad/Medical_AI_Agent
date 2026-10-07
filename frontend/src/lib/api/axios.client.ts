import axios, {
  AxiosInstance,
  AxiosError,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from "axios";
import Cookies from "js-cookie";

// ============================================================================
// 1. BIẾN MÔI TRƯỜNG & KEY COOKIE (ENVIRONMENT CONFIG)
// ============================================================================
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ACCESS_TOKEN_KEY = process.env.NEXT_PUBLIC_ACCESS_TOKEN_KEY || "ai20k_access_token";
const REFRESH_TOKEN_KEY = process.env.NEXT_PUBLIC_REFRESH_TOKEN_KEY || "ai20k_refresh_token";
const REFRESH_ENDPOINT = "/api/v1/auth/refresh";

// Mở rộng kiểu dữ liệu InternalAxiosRequestConfig để thêm cờ _retry tránh lặp vô hạn
interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

// Kiểu dữ liệu chuẩn của payload trả về khi refresh token thành công
interface RefreshTokenResponseDTO {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
  expires_in?: number;
}

// ============================================================================
// 2. KHỞI TẠO AXIOS INSTANCE CHÍNH THỨC
// ============================================================================
export const axiosClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, // 15 giây chuẩn lâm sàng cho các request RAG/LLM
  headers: {
    "Content-Type": "application/json",
    "Accept": "application/json",
  },
  withCredentials: true, // Cho phép truyền Cookie an toàn khi gọi CORS
});

// ============================================================================
// 3. CƠ CHẾ QUEUE CHỐNG ĐỤNG ĐỘ KHI CÓ NHIỀU REQUEST 401 CÙNG LÚC
// ============================================================================
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

/**
 * Xử lý hàng đợi các request bị tạm ngưng trong thời gian đang xin lại token mới.
 */
const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else if (token) {
      promise.resolve(token);
    }
  });
  failedQueue = [];
};

/**
 * Hàm hỗ trợ xóa toàn bộ token tại Cookies và quay về cổng Đăng Nhập
 */
export const handleLogoutAndRedirect = (): void => {
  Cookies.remove(ACCESS_TOKEN_KEY, { path: "/" });
  Cookies.remove(REFRESH_TOKEN_KEY, { path: "/" });
  
  // Đảm bảo chỉ thực thi trên môi trường Client (Next.js App Router safety)
  if (typeof window !== "undefined") {
    // Không redirect nếu như đang ở trang auth để tránh loop URL
    if (!window.location.pathname.startsWith("/auth/")) {
      window.location.href = "/auth/login?reason=session_expired";
    }
  }
};

// ============================================================================
// 4. REQUEST INTERCEPTOR: TỰ ĐỘNG NẠP ACCESS TOKEN VÀO HEADER
// ============================================================================
axiosClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const accessToken = Cookies.get(ACCESS_TOKEN_KEY);
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// ============================================================================
// 5. RESPONSE INTERCEPTOR: BẮT LỖI 401 & REFRESH TOKEN TỰ ĐỘNG
// ============================================================================
axiosClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as CustomAxiosRequestConfig | undefined;

    // Nếu lỗi không liên quan đến cấu hình request hoặc không có response
    if (!originalRequest || !error.response) {
      return Promise.reject(error);
    }

    // Trường hợp 1: Nếu lỗi là 401 Unauthorized và không phải từ chính endpoint refresh token
    if (
      error.response.status === 401 &&
      originalRequest.url &&
      !originalRequest.url.includes(REFRESH_ENDPOINT)
    ) {
      // KIỂM SOÁT VÒNG LẶP VÔ HẠN: Nếu request này đã được retry một lần rồi mà vẫn 401 -> Logout
      if (originalRequest._retry) {
        handleLogoutAndRedirect();
        return Promise.reject(error);
      }

      // Nếu đang có một tiến trình refresh token khác chạy ngầm, hãy cho request này vào hàng đợi (Queue)
      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((newAccessToken) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
            }
            return axiosClient(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      // Đánh dấu cờ _retry và bật trạng thái isRefreshing = true
      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = Cookies.get(REFRESH_TOKEN_KEY);

      // Nếu không tìm thấy refresh token trong cookie -> Logout thẳng
      if (!refreshToken) {
        isRefreshing = false;
        handleLogoutAndRedirect();
        return Promise.reject(
          new Error("Không tìm thấy Refresh Token y khoa hợp lệ.")
        );
      }

      try {
        
        // Gọi thẳng bằng axios nguyên thủy (không dùng axiosClient để tránh bị dính Interceptors)
        const refreshResponse = await axios.post<RefreshTokenResponseDTO>(
          `${API_BASE_URL}${REFRESH_ENDPOINT}`,
          {
            refresh_token: refreshToken,
          },
          {
            headers: {
              "Content-Type": "application/json",
            },
            timeout: 10000,
          }
        );

        const newAccessToken = refreshResponse.data.access_token;
        const newRefreshToken = refreshResponse.data.refresh_token || refreshToken;

        // Lưu Access Token mới vào Cookie (áp dụng cấu hình bảo mật SameSite)
        Cookies.set(ACCESS_TOKEN_KEY, newAccessToken, {
          secure: typeof window !== "undefined" && window.location.protocol === "https:",
          sameSite: "strict",
          path: "/",
          expires: 1, // Hạn cookie 1 ngày
        });

        // Lưu Refresh Token mới (nếu Backend có thực hiện xoay vòng token - Refresh Token Rotation)
        if (refreshResponse.data.refresh_token) {
          Cookies.set(REFRESH_TOKEN_KEY, newRefreshToken, {
            secure: typeof window !== "undefined" && window.location.protocol === "https:",
            sameSite: "strict",
            path: "/",
            expires: 7, // Hạn cookie 7 ngày
          });
        }

        // Cập nhật lại header Authorization cho request gốc đang bị lỗi
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        }

        // Giải phóng hàng đợi (process queue) cho tất cả các request đang xếp hàng chờ token mới
        processQueue(null, newAccessToken);

        // Gọi lại request ban đầu với Token mới
        return axiosClient(originalRequest);
      } catch (refreshError) {
        // Nếu refresh token cũng thất bại hoặc hết hạn -> Giải phóng hàng đợi với thông báo lỗi và Logout
        processQueue(refreshError, null);
        console.error("❌ [Token Refresher] Gia hạn Token thất bại, thực hiện xả bỏ phiên cờ ACID:", refreshError);
        handleLogoutAndRedirect();
        return Promise.reject(refreshError);
      } finally {
        // Hoàn tất quá trình gia hạn, mở khóa cờ isRefreshing
        isRefreshing = false;
      }
    }

    // Các mã lỗi khác (403, 404, 500...) trả ra bình thường cho TanStack Query hoặc Service layer xử lý
    return Promise.reject(error);
  }
);
