import { render, screen } from "@testing-library/react";
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

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient();

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
};

const signIn = (user: UserProfile) =>
  useAuthStore.setState({ user, isAuthenticated: true, isLoading: false });

const PATIENT_ONLY_LINKS = [/Khám Triage AI/i, /Lịch Sử Khám/i, /Hồ Sơ Y Khoa/i];

describe("navbar visibility by session state", () => {
  afterEach(() => signOut());
  afterEach(() => {
    vi.clearAllMocks();
    signOut();
  });

  it("hides every patient-only feature from a signed-out visitor", () => {
    signOut();
    renderWithProviders(<ClinicalNavbar />);

    for (const label of PATIENT_ONLY_LINKS) {
      expect(screen.queryByRole("link", { name: label })).not.toBeInTheDocument();
    }
  });

  it("shows only the public brand and auth shortcuts when logged out", () => {
    signOut();
    renderWithProviders(<ClinicalNavbar />);

    expect(screen.getByRole("link", { name: /Đăng Nhập/i })).toHaveAttribute(
      "href",
      "/auth/login",
    );
    expect(screen.getByRole("link", { name: /Đăng Ký/i })).toHaveAttribute(
      "href",
      "/auth/register",
    );
    expect(screen.getByRole("link", { name: /Trang Chủ/i })).toHaveAttribute("href", "/");
  });

  it("restores the full patient menu once a session exists", () => {
    signIn(patient);
    renderWithProviders(<ClinicalNavbar />);

    expect(screen.getByRole("link", { name: /Khám Triage AI/i })).toHaveAttribute(
      "href",
      "/triage",
    );
    expect(screen.getByRole("link", { name: /Lịch Sử Khám/i })).toHaveAttribute(
      "href",
      "/history",
    );
    expect(screen.getByRole("link", { name: /Hồ Sơ Y Khoa/i })).toHaveAttribute(
      "href",
      "/profile",
    );
  });

  it("gives clinical staff their own menu, not the patient one", () => {
    signIn({ ...patient, role: "CLINICAL_NURSE" });
    render(<ClinicalNavbar />);

    expect(screen.getByRole("link", { name: /Hàng đợi/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Hồ Sơ Y Khoa/i })).not.toBeInTheDocument();
  });
});
