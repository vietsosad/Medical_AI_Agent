import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import OAuthCallbackPage from "@/app/auth/callback/[provider]/page";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";

const replace = vi.fn();
let search = "code=abc";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useParams: () => ({ provider: "google" }),
  useSearchParams: () => new URLSearchParams(search),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("@/services/auth.service", () => ({
  authService: { oauthCallback: vi.fn() },
}));

describe("OAuth callback screen", () => {
  beforeEach(() => {
    replace.mockClear();
    search = "code=abc";
    vi.mocked(authService.oauthCallback).mockReset();
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
  });

  it("exchanges the code once, stores the session and moves on by role", async () => {
    vi.mocked(authService.oauthCallback).mockResolvedValue({
      access_token: "access-token-value",
      refresh_token: "refresh-token-value",
      token_type: "Bearer",
      expires_in: 3600,
      user: { id: "user-1", name: "Người Bệnh", email: "patient@example.com", role: "PATIENT" },
    });
    render(<OAuthCallbackPage />);

    expect(await screen.findByRole("heading", { name: "Đăng nhập thành công" })).toBeInTheDocument();
    expect(authService.oauthCallback).toHaveBeenCalledTimes(1);
    expect(authService.oauthCallback).toHaveBeenCalledWith("google", "abc");
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"), { timeout: 3000 });
    expect(document.body.textContent).not.toContain("access-token-value");
  });

  it("explains a missing code and offers a way back without calling the server", async () => {
    search = "";
    render(<OAuthCallbackPage />);

    expect(
      await screen.findByRole("heading", { name: "Chưa đăng nhập được với Google" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Không tìm thấy mã xác thực");
    expect(screen.getByRole("link", { name: "Thử đăng nhập lại" })).toHaveAttribute("href", "/auth/login");
    expect(screen.getByRole("link", { name: "Về trang chủ" })).toHaveAttribute("href", "/");
    expect(authService.oauthCallback).not.toHaveBeenCalled();
  });
});
