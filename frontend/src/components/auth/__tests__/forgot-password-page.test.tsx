import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ForgotPasswordPage from "@/app/auth/forgot-password/page";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

vi.mock("@/services/auth.service", () => ({
  authService: { forgotPassword: vi.fn(), verifyOtp: vi.fn(), resetPassword: vi.fn() },
}));

describe("forgot password flow", () => {
  beforeEach(() => {
    vi.mocked(authService.forgotPassword).mockReset();
    vi.mocked(authService.verifyOtp).mockReset();
    vi.mocked(authService.resetPassword).mockReset();
    vi.mocked(toast.error).mockClear();
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
  });

  it("walks email, code and new password with every call bound to the email, and never opens a session", async () => {
    vi.mocked(authService.forgotPassword).mockResolvedValue({ success: true, message: "sent" });
    vi.mocked(authService.verifyOtp).mockResolvedValue({ success: true, message: "valid" });
    vi.mocked(authService.resetPassword).mockResolvedValue({ success: true, message: "done" });
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText("Email"), "an@example.com");
    await user.click(screen.getByRole("button", { name: "Gửi mã xác minh" }));
    expect(authService.forgotPassword).toHaveBeenCalledWith({ email: "an@example.com" });

    const firstDigit = await screen.findByRole("textbox", { name: "Chữ số thứ 1 của mã" });
    await user.type(firstDigit, "654321");
    await waitFor(() =>
      expect(authService.verifyOtp).toHaveBeenCalledWith({
        email: "an@example.com",
        code: "654321",
        purpose: "PASSWORD_RESET",
      }),
    );

    await user.type(await screen.findByLabelText("Mật khẩu mới"), "matkhaumoi123");
    await user.type(screen.getByLabelText("Xác nhận mật khẩu mới"), "matkhaumoi123");
    await user.click(screen.getByRole("button", { name: "Cập nhật mật khẩu" }));

    await waitFor(() =>
      expect(authService.resetPassword).toHaveBeenCalledWith({
        email: "an@example.com",
        otp: "654321",
        newPassword: "matkhaumoi123",
      }),
    );
    expect(await screen.findByRole("heading", { name: "Đã đổi mật khẩu" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Đăng nhập bằng mật khẩu mới/ })).toHaveAttribute(
      "href",
      "/auth/login",
    );
    // Xác minh mã khôi phục không bao giờ cấp phiên đăng nhập.
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("labels both visibility toggles on the new-password step", async () => {
    vi.mocked(authService.forgotPassword).mockResolvedValue({ success: true, message: "sent" });
    vi.mocked(authService.verifyOtp).mockResolvedValue({ success: true, message: "valid" });
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText("Email"), "an@example.com");
    await user.click(screen.getByRole("button", { name: "Gửi mã xác minh" }));
    await user.type(await screen.findByRole("textbox", { name: "Chữ số thứ 1 của mã" }), "654321");

    expect(await screen.findByRole("button", { name: "Hiện mật khẩu mới" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hiện xác nhận mật khẩu mới" })).toBeInTheDocument();
  });

  it("shows a failed request inside the page instead of a blocking browser dialog", async () => {
    const reason = "Không kết nối được tới hệ thống. Vui lòng kiểm tra mạng rồi thử lại.";
    vi.mocked(authService.forgotPassword).mockRejectedValue(new Error(reason));
    vi.spyOn(console, "error").mockImplementation(() => {});
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText("Email"), "an@example.com");
    await user.click(screen.getByRole("button", { name: "Gửi mã xác minh" }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(reason));
    expect(toast.error).toHaveBeenCalledWith(reason);
    expect(alertSpy).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Quên mật khẩu?" })).toBeInTheDocument();
  });
});
