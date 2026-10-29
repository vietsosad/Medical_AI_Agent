import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "@/app/auth/login/page";
import { getHomeRouteForRole } from "@/lib/auth-routing";
import { authService, type AuthResponseDTO } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), loading: vi.fn(), dismiss: vi.fn() },
}));

vi.mock("@/services/auth.service", () => ({
  authService: { login: vi.fn(), getOAuthUrl: vi.fn() },
}));

const session = (role: AuthResponseDTO["user"]["role"]): AuthResponseDTO => ({
  access_token: "access-token-value",
  refresh_token: "refresh-token-value",
  token_type: "Bearer",
  expires_in: 3600,
  user: { id: "user-1", name: "Người Bệnh", email: "patient@example.com", role },
});

const signOut = () =>
  useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });

async function fillAndSubmit(email: string, password: string) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Mật khẩu"), password);
  await user.click(screen.getByRole("button", { name: "Đăng nhập" }));
}

describe("login screen", () => {
  beforeEach(() => {
    replace.mockClear();
    vi.mocked(authService.login).mockReset();
    vi.mocked(authService.getOAuthUrl).mockReset();
    vi.mocked(toast.error).mockClear();
    signOut();
  });

  afterEach(() => {
    signOut();
    window.history.replaceState(null, "", "/");
  });

  it("shows the sign-in board: greeting, labelled fields and every way out", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", { level: 1, name: "Chào mừng bạn trở lại" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("type", "email");
    expect(screen.getByLabelText("Mật khẩu")).toHaveAttribute("type", "password");
    expect(screen.getByRole("link", { name: "Quên mật khẩu?" })).toHaveAttribute(
      "href",
      "/auth/forgot-password",
    );
    expect(screen.getByRole("link", { name: "Đăng ký" })).toHaveAttribute("href", "/auth/register");
    expect(screen.getByRole("button", { name: "Tiếp tục với Google" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tiếp tục với GitHub" })).toBeInTheDocument();
  });

  it("reveals and hides the password through a labelled toggle", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);
    const password = screen.getByLabelText("Mật khẩu");

    await user.click(screen.getByRole("button", { name: "Hiện mật khẩu" }));
    expect(password).toHaveAttribute("type", "text");

    await user.click(screen.getByRole("button", { name: "Ẩn mật khẩu" }));
    expect(password).toHaveAttribute("type", "password");
  });

  it("announces validation errors under their own field and never calls the server", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.click(screen.getByRole("button", { name: "Đăng nhập" }));

    const emailError = await screen.findByText("Vui lòng nhập địa chỉ Email.");
    expect(emailError.closest("[aria-live]")).toHaveAttribute("aria-live", "polite");
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Email")).toHaveAccessibleDescription("Vui lòng nhập địa chỉ Email.");
    expect(
      screen.getByText("Mật khẩu bảo mật bắt buộc có độ dài tối thiểu 8 ký tự."),
    ).toBeInTheDocument();
    expect(authService.login).not.toHaveBeenCalled();
  });

  it("sends exactly the typed credentials, stores the session and routes a patient home", async () => {
    vi.mocked(authService.login).mockResolvedValue(session("PATIENT"));
    render(<LoginPage />);

    await fillAndSubmit("patient@example.com", "matkhau123");

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
    expect(authService.login).toHaveBeenCalledWith({
      email: "patient@example.com",
      password: "matkhau123",
    });
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(document.body.textContent).not.toContain("access-token-value");
    expect(document.body.textContent).not.toContain("refresh-token-value");
  });

  it("routes clinical staff to their own workspace", async () => {
    vi.mocked(authService.login).mockResolvedValue(session("CLINICAL_NURSE"));
    render(<LoginPage />);

    await fillAndSubmit("nurse@example.com", "matkhau123");

    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith(getHomeRouteForRole("CLINICAL_NURSE")),
    );
  });

  it("shows the server's reason in an alert when sign-in is refused", async () => {
    const reason = "Thông tin tài khoản Email hoặc mật khẩu không chính xác.";
    vi.mocked(authService.login).mockRejectedValue(new Error(reason));
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(<LoginPage />);

    await fillAndSubmit("patient@example.com", "saimatkhau1");

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(reason));
    expect(toast.error).toHaveBeenCalledWith(reason);
    expect(replace).not.toHaveBeenCalled();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("starts Google sign-in at the URL the server hands back", async () => {
    vi.mocked(authService.getOAuthUrl).mockResolvedValue({ url: "#google-consent", provider: "google" });
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.click(screen.getByRole("button", { name: "Tiếp tục với Google" }));

    await waitFor(() => expect(window.location.hash).toBe("#google-consent"));
    expect(authService.getOAuthUrl).toHaveBeenCalledWith("google");
  });
});
