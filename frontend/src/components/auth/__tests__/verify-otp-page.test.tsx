import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import VerifyOtpPage from "@/app/auth/verify-otp/page";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

vi.mock("@/services/auth.service", () => ({
  authService: { verifyOtp: vi.fn() },
}));

const digitBoxes = () => screen.getAllByRole("textbox", { name: /^Chữ số thứ \d của mã$/ });

describe("registration code screen", () => {
  beforeEach(() => {
    vi.mocked(authService.verifyOtp).mockReset();
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
    window.history.replaceState(null, "", "/auth/verify-otp?email=an%40example.com");
  });

  it("verifies the typed code together with the email it was sent to", async () => {
    vi.mocked(authService.verifyOtp).mockResolvedValue({
      access_token: "access-token-value",
      refresh_token: "refresh-token-value",
      token_type: "Bearer",
      expires_in: 3600,
      user: { id: "user-1", name: "Nguyễn Văn An", email: "an@example.com", role: "PATIENT" },
    });
    const user = userEvent.setup();
    render(<VerifyOtpPage />);

    expect(screen.getByText("an@example.com")).toBeInTheDocument();
    expect(digitBoxes()).toHaveLength(6);

    await user.type(digitBoxes()[0], "123456");

    await waitFor(() =>
      expect(authService.verifyOtp).toHaveBeenCalledWith({
        email: "an@example.com",
        code: "123456",
        purpose: "REGISTRATION",
      }),
    );
    expect(await screen.findByRole("heading", { name: "Xác minh thành công" })).toBeInTheDocument();
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(document.body.textContent).not.toContain("access-token-value");
  });

  it("rejects a wrong code: says why, empties the boxes and puts the cursor back in the first one", async () => {
    const reason = "Mã bảo mật OTP không hợp lệ hoặc không thuộc về tài khoản này.";
    vi.mocked(authService.verifyOtp).mockRejectedValue(new Error(reason));
    vi.spyOn(console, "error").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<VerifyOtpPage />);

    await user.type(digitBoxes()[0], "000000");

    expect(await screen.findByText(reason)).toBeInTheDocument();
    await waitFor(() => {
      for (const box of digitBoxes()) expect(box).toHaveValue("");
    });
    await waitFor(() => expect(digitBoxes()[0]).toHaveFocus());
    expect(digitBoxes()[0]).toHaveAttribute("aria-invalid", "true");
    expect(digitBoxes()[0]).toHaveAccessibleDescription(reason);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("keeps resend locked while the cooldown runs", () => {
    render(<VerifyOtpPage />);

    expect(screen.getByRole("button", { name: "Gửi lại sau 60 giây" })).toBeDisabled();
  });

  it("warns when the link has no email, since the server only accepts a code bound to its email", () => {
    window.history.replaceState(null, "", "/auth/verify-otp");
    render(<VerifyOtpPage />);

    expect(screen.getByText(/thiếu địa chỉ email nên chưa thể xác minh mã/)).toBeInTheDocument();
  });
});
