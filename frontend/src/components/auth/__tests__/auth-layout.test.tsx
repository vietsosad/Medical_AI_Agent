import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuthLayout from "@/app/auth/layout";
import { useAuthStore } from "@/store/useAuthStore";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/auth/login",
}));

const renderLayout = () =>
  render(
    <AuthLayout>
      <p>Biểu mẫu xác thực</p>
    </AuthLayout>,
  );

describe("auth layout", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
  });

  it("keeps a one-tap 115 call on every auth screen, no sign-in needed", () => {
    renderLayout();

    expect(screen.getByText("Biểu mẫu xác thực")).toBeInTheDocument();
    const strip = screen.getByRole("complementary", { name: "Cấp cứu" });
    expect(strip).toHaveTextContent("Đang cấp cứu? Gọi ngay, không cần đăng nhập.");
    expect(within(strip).getByRole("link", { name: "Gọi cấp cứu 115" })).toHaveAttribute(
      "href",
      "tel:115",
    );
  });

  it("states only verifiable product facts beside the form", () => {
    renderLayout();

    const panel = screen.getByRole("complementary", { name: /Sàng lọc mức độ khẩn cấp/ });
    expect(panel).toHaveTextContent("Mức độ khẩn cấp là gợi ý, không phải chẩn đoán");
    expect(panel).toHaveTextContent("Hỗ trợ sàng lọc, không thay thế chẩn đoán của bác sĩ.");
    // Không chỉ số chưa đo, không nhãn tuân thủ.
    expect(panel.textContent ?? "").not.toMatch(/%|HIPAA|ISO|độ chính xác|\d+\s*ms/i);
  });
});
