import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RegisterPage from "@/app/auth/register/page";
import { authService } from "@/services/auth.service";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), loading: vi.fn(), dismiss: vi.fn() },
}));

vi.mock("@/services/auth.service", () => ({
  authService: { register: vi.fn(), getOAuthUrl: vi.fn() },
}));

describe("register screen", () => {
  beforeEach(() => {
    push.mockClear();
    vi.mocked(authService.register).mockReset();
  });

  it("creates the account from name, email and password, then opens the code screen for that email", async () => {
    vi.mocked(authService.register).mockResolvedValue({ success: true, message: "ok" });
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Họ và tên"), "Nguyễn Văn An");
    await user.type(screen.getByLabelText("Email"), "an@example.com");
    await user.type(screen.getByLabelText("Mật khẩu"), "matkhau123");
    await user.type(screen.getByLabelText("Xác nhận mật khẩu"), "matkhau123");
    await user.click(screen.getByRole("button", { name: "Tạo tài khoản" }));

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/auth/verify-otp?email=an%40example.com"),
    );
    expect(authService.register).toHaveBeenCalledWith({
      name: "Nguyễn Văn An",
      email: "an@example.com",
      password: "matkhau123",
    });
  });

  it("flags a mismatched confirmation under the confirmation field only", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Họ và tên"), "Nguyễn Văn An");
    await user.type(screen.getByLabelText("Email"), "an@example.com");
    await user.type(screen.getByLabelText("Mật khẩu"), "matkhau123");
    await user.type(screen.getByLabelText("Xác nhận mật khẩu"), "matkhau999");
    await user.click(screen.getByRole("button", { name: "Tạo tài khoản" }));

    const confirm = screen.getByLabelText("Xác nhận mật khẩu");
    await waitFor(() =>
      expect(confirm).toHaveAccessibleDescription("Mật khẩu xác nhận không khớp với mật khẩu vừa nhập."),
    );
    expect(confirm).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Mật khẩu")).not.toHaveAttribute("aria-invalid");
    expect(authService.register).not.toHaveBeenCalled();
  });

  it("keeps separate accessible names for the two visibility toggles", () => {
    render(<RegisterPage />);

    expect(screen.getByRole("button", { name: "Hiện mật khẩu" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hiện xác nhận mật khẩu" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Đăng nhập" })).toHaveAttribute("href", "/auth/login");
  });
});
