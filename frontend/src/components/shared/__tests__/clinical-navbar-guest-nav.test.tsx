import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClinicalNavbar } from "@/components/shared/ClinicalNavbar";
import { useAuthStore, type UserProfile } from "@/store/useAuthStore";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

const patient: UserProfile = {
  id: "user-1",
  name: "Người Bệnh",
  email: "patient@example.com",
  role: "PATIENT",
};

const signOut = () =>
  useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });

function renderNavbar() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ClinicalNavbar />
    </QueryClientProvider>,
  );
}

/** Các mỏ neo công khai phải khớp đúng id của khối nội dung trên trang chủ. */
const GUEST_ANCHORS: Array<[RegExp, string]> = [
  [/An Toàn Y Khoa/i, "/#an-toan-lam-sang"],
  [/Trải Nghiệm/i, "/#trai-nghiem-triage"],
  [/Kiến Thức Sức Khỏe/i, "/#thong-tin-suc-khoe"],
];

describe("điều hướng công khai cho khách chưa đăng nhập", () => {
  afterEach(() => signOut());

  it("dẫn khách tới các khối nội dung công khai ngay trên trang chủ", () => {
    signOut();
    renderNavbar();

    for (const [label, href] of GUEST_ANCHORS) {
      expect(screen.getByRole("link", { name: label })).toHaveAttribute("href", href);
    }
  });

  it("chỉ dùng mỏ neo trong trang, không mở thêm tuyến nào cần đăng nhập", () => {
    signOut();
    renderNavbar();

    for (const [label] of GUEST_ANCHORS) {
      const href = screen.getByRole("link", { name: label }).getAttribute("href");
      expect(href).toMatch(/^\/#/);
    }
  });

  it("vẫn giữ nguyên đường về trang chủ bên cạnh các mỏ neo", () => {
    signOut();
    renderNavbar();

    expect(screen.getByRole("link", { name: /Trang Chủ/i })).toHaveAttribute("href", "/");
  });

  it("không hiện mỏ neo trang chủ khi người bệnh đã có phiên đăng nhập", () => {
    useAuthStore.setState({ user: patient, isAuthenticated: true, isLoading: false });
    renderNavbar();

    for (const [label] of GUEST_ANCHORS) {
      expect(screen.queryByRole("link", { name: label })).not.toBeInTheDocument();
    }
  });
});
