import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionGlobalConfig } from "framer-motion";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { ProfileResponseDTO } from "@/services/profile.service";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";
import { useAuthStore } from "@/store/useAuthStore";

const hooks = vi.hoisted(() => ({
  useGetProfiles: vi.fn(),
  useDeleteProfile: vi.fn(),
  useEmergencyContacts: vi.fn(),
  useUpdateEmergencyContacts: vi.fn(),
  useUpdatePhoneNumber: vi.fn(),
}));

vi.mock("@/queries/useProfileQueries", () => ({
  PROFILE_QUERY_KEYS: { all: ["family-profiles"] },
  useGetProfiles: hooks.useGetProfiles,
  useDeleteProfile: hooks.useDeleteProfile,
}));
vi.mock("@/queries/use-clinical-profile", () => ({ useEmergencyContacts: hooks.useEmergencyContacts }));
vi.mock("@/queries/use-profile-mutations", () => ({ useUpdateEmergencyContacts: hooks.useUpdateEmergencyContacts }));
vi.mock("@/queries/useAccountMutations", () => ({ useUpdatePhoneNumber: hooks.useUpdatePhoneNumber }));
// Hai hộp thoại thêm/sửa có hook riêng; ở đây chỉ kiểm tra trang mở đúng hộp thoại nào.
vi.mock("@/components/profile/AddProfileModal", () => ({ AddProfileModal: () => null }));
vi.mock("@/components/profile/EditProfileModal", () => ({ EditProfileModal: () => null }));

const { default: PatientProfileRootPage } = await import("@/app/(patient)/profile/page");

function profile(overrides: Partial<ProfileResponseDTO>): ProfileResponseDTO {
  return {
    id: "profile",
    user_id: "user-1",
    full_name: "Không tên",
    relationship_type: "OTHER",
    is_primary: false,
    dob: null,
    avatar_color: "slate",
    age: null,
    gender: null,
    blood_type: null,
    height_cm: null,
    weight_kg: null,
    chronic_conditions: [],
    daily_medications: [],
    allergies: [],
    phone_number: null,
    emergency_contact_name: null,
    emergency_contact_phone: null,
    updated_at: null,
    ...overrides,
  };
}

const PROFILES = [
  profile({
    id: "me",
    full_name: "Nguyễn Văn Demo",
    relationship_type: "SELF",
    is_primary: true,
    avatar_color: "blue",
    age: 34,
    gender: "MALE",
    blood_type: "O+",
    phone_number: "0912345678",
    chronic_conditions: ["Tăng huyết áp", "Hen phế quản"],
    allergies: ["Penicillin"],
  }),
  profile({ id: "kid", full_name: "Bé An", relationship_type: "CHILD", avatar_color: "amber", age: 4 }),
  profile({ id: "mom", full_name: "Trần Thị Hoa", relationship_type: "PARENT", avatar_color: "rose", age: 62 }),
];

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PatientProfileRootPage />
    </QueryClientProvider>,
  );
}

beforeAll(() => {
  MotionGlobalConfig.skipAnimations = true;
});

afterAll(() => {
  MotionGlobalConfig.skipAnimations = false;
});

beforeEach(() => {
  useActiveProfileStore.getState().resetActiveProfileStore();
  useAuthStore.setState({
    user: { id: "user-1", name: "Nguyễn Văn Demo", email: "demo@example.com", role: "PATIENT" },
    isAuthenticated: true,
    isLoading: false,
  });
  hooks.useGetProfiles.mockReturnValue({ data: PROFILES, isLoading: false, isError: false, refetch: vi.fn() });
  hooks.useDeleteProfile.mockReturnValue({ mutate: vi.fn(), isPending: false });
  hooks.useEmergencyContacts.mockReturnValue({
    data: [
      {
        id: "sos-1",
        full_name: "Trần Thị Hoa",
        relationship: "PARENT",
        phone_number: "0987654321",
        is_primary: true,
      },
    ],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  });
  hooks.useUpdateEmergencyContacts.mockReturnValue({ mutate: vi.fn(), isPending: false });
  hooks.useUpdatePhoneNumber.mockReturnValue({ mutate: vi.fn(), isPending: false });
});

afterEach(() => {
  Object.values(hooks).forEach((hook) => hook.mockReset());
});

describe("Hồ sơ sức khỏe gia đình", () => {
  it("chọn sẵn hồ sơ chính và hiện đúng những gì điều dưỡng sẽ thấy", () => {
    renderPage();

    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual([
      expect.stringContaining("Tôi"),
      expect.stringContaining("Bé An"),
      expect.stringContaining("Hoa"),
    ]);
    expect(screen.getByRole("tab", { name: /^Tôi/ })).toHaveAttribute("aria-selected", "true");

    const card = screen.getByRole("region", { name: "Nguyễn Văn Demo" });
    expect(within(card).getByText("Hồ sơ chính · nam · 34 tuổi")).toBeInTheDocument();
    expect(within(card).getByText("O+")).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: "0912 345 678" })).toHaveAttribute("href", "tel:0912345678");
    expect(within(card).getByText("Tăng huyết áp")).toBeInTheDocument();
    expect(within(card).getByText("Penicillin").closest("li")).toHaveTextContent("Dị ứng: Penicillin");
    // Lối vào khai báo chỉ số sức khỏe là nút chính của thẻ, nói rõ bên trong có gì.
    expect(within(card).getByRole("link", { name: /^Cập nhật hồ sơ sức khỏe/ })).toHaveAttribute("href", "/profile/ehr");
    expect(within(card).getByRole("link", { name: /^Cập nhật hồ sơ sức khỏe/ })).toHaveTextContent(
      "Chiều cao, cân nặng, BMI, bệnh nền, dị ứng, thuốc",
    );
    // Hồ sơ chính không xóa được.
    expect(within(card).queryByRole("button", { name: /Xóa hồ sơ/ })).not.toBeInTheDocument();

    expect(screen.getByRole("link", { name: "Gọi Trần Thị Hoa" })).toHaveAttribute("href", "tel:0987654321");
    expect(screen.getByRole("link", { name: /Sàng lọc cho Nguyễn Văn Demo/ })).toHaveAttribute(
      "href",
      expect.stringMatching(/^\/triage/),
    );
  });

  it("nút sửa mở đúng hồ sơ; chưa khai báo dị ứng thì nói là chưa ghi nhận", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: "Sửa hồ sơ của Nguyễn Văn Demo" }));
    expect(useActiveProfileStore.getState()).toMatchObject({ isEditProfileModalOpen: true, editProfileId: "me" });

    await user.click(screen.getByRole("tab", { name: /Bé An/ }));
    const card = await screen.findByRole("region", { name: "Bé An" });
    expect(within(card).getByText("Chưa ghi nhận dị ứng.")).toBeInTheDocument();
    expect(useActiveProfileStore.getState().activeProfileId).toBe("kid");
  });

  it("phím mũi tên chuyển người; người thân có nút xóa kèm xác nhận", async () => {
    const user = userEvent.setup();
    renderPage();

    screen.getByRole("tab", { name: /^Tôi/ }).focus();
    await user.keyboard("{End}");
    expect(screen.getByRole("tab", { name: /Hoa/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /Hoa/ })).toHaveFocus();

    const card = await screen.findByRole("region", { name: "Trần Thị Hoa" });
    expect(within(card).getByText("Cha / mẹ · 62 tuổi")).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: /Xóa hồ sơ/ }));

    const dialog = await screen.findByRole("alertdialog", { name: "Xóa hồ sơ thành viên" });
    expect(dialog).toHaveTextContent("Trần Thị Hoa");
  });

  it("chưa có hồ sơ nào: mời thêm thành viên đầu tiên", async () => {
    const user = userEvent.setup();
    hooks.useGetProfiles.mockReturnValue({ data: [], isLoading: false, isError: false, refetch: vi.fn() });
    renderPage();

    await user.click(screen.getByRole("button", { name: /Thêm thành viên đầu tiên/ }));
    expect(useActiveProfileStore.getState().isAddProfileModalOpen).toBe(true);
  });
});
