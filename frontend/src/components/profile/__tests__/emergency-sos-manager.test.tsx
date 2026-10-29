import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MotionGlobalConfig } from "framer-motion";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { EmergencyContactDTO } from "@/types/clinical-profile";

const hooks = vi.hoisted(() => ({
  useEmergencyContacts: vi.fn(),
  useUpdateEmergencyContacts: vi.fn(),
}));

vi.mock("@/queries/use-clinical-profile", () => ({ useEmergencyContacts: hooks.useEmergencyContacts }));
vi.mock("@/queries/use-profile-mutations", () => ({ useUpdateEmergencyContacts: hooks.useUpdateEmergencyContacts }));

const { EmergencySosManager } = await import("@/components/profile/EmergencySosManager");

const HOA: EmergencyContactDTO = {
  id: "sos-1",
  full_name: "Trần Thị Hoa",
  relationship: "PARENT",
  phone_number: "0987654321",
  is_primary: true,
};
const HUNG: EmergencyContactDTO = {
  id: "sos-2",
  full_name: "Lê Văn Hùng",
  relationship: "SIBLING",
  phone_number: "0901 234 567",
  is_primary: false,
};

const mutate = vi.fn();

function mockContacts(contacts: EmergencyContactDTO[]) {
  hooks.useEmergencyContacts.mockReturnValue({ data: contacts, isLoading: false, isError: false, refetch: vi.fn() });
}

beforeAll(() => {
  MotionGlobalConfig.skipAnimations = true;
});

afterAll(() => {
  MotionGlobalConfig.skipAnimations = false;
});

beforeEach(() => {
  hooks.useUpdateEmergencyContacts.mockReturnValue({ mutate, isPending: false });
});

afterEach(() => {
  mutate.mockReset();
  Object.values(hooks).forEach((hook) => hook.mockReset());
});

describe("Người liên hệ khẩn cấp", () => {
  it("mỗi người có nút gọi; người số 1 được đánh dấu; câu chữ không hứa tự gọi 115", () => {
    mockContacts([HOA, HUNG]);
    render(<EmergencySosManager subjectName="Nguyễn Văn Demo" />);

    expect(screen.getByText("2/3")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Gọi Trần Thị Hoa" })).toHaveAttribute("href", "tel:0987654321");
    // Khoảng trắng người dùng gõ không lọt vào đường dẫn tel:.
    expect(screen.getByRole("link", { name: "Gọi Lê Văn Hùng" })).toHaveAttribute("href", "tel:0901234567");
    expect(screen.getByText("Liên hệ số 1").closest("li")).toHaveTextContent("Trần Thị Hoa");
    expect(screen.getByText(/không tự gọi số này và không tự điều xe 115/)).toBeInTheDocument();
  });

  it("xóa người số 1 phải xác nhận, rồi người kế tiếp lên làm số 1", async () => {
    const user = userEvent.setup();
    mockContacts([HOA, HUNG]);
    render(<EmergencySosManager />);

    await user.click(screen.getByRole("button", { name: "Xóa người liên hệ Trần Thị Hoa" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Xóa người liên hệ số 1?" });
    expect(mutate).not.toHaveBeenCalled();

    await user.click(within(dialog).getByRole("button", { name: /Xóa người này/ }));
    expect(mutate).toHaveBeenCalledWith([{ ...HUNG, is_primary: true }], expect.anything());
  });

  it("xóa người không phải số 1 thì xóa ngay", async () => {
    const user = userEvent.setup();
    mockContacts([HOA, HUNG]);
    render(<EmergencySosManager />);

    await user.click(screen.getByRole("button", { name: "Xóa người liên hệ Lê Văn Hùng" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(mutate).toHaveBeenCalledWith([HOA], expect.anything());
  });

  it("biểu mẫu thêm mới kiểm tra họ tên và số điện thoại trước khi lưu", async () => {
    const user = userEvent.setup();
    mockContacts([HOA]);
    render(<EmergencySosManager />);

    await user.click(screen.getByRole("button", { name: /Thêm người liên hệ/ }));
    const dialog = await screen.findByRole("dialog", { name: "Thêm người liên hệ khẩn cấp" });
    await user.type(within(dialog).getByLabelText("Họ và tên người liên hệ"), "A");
    await user.type(within(dialog).getByLabelText("Số điện thoại"), "12");
    await user.click(within(dialog).getByRole("button", { name: /Thêm người liên hệ/ }));

    expect(await within(dialog).findByText("Họ tên người liên hệ phải có ít nhất 2 ký tự")).toBeInTheDocument();
    expect(within(dialog).getByText(/Số điện thoại không hợp lệ/)).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Số điện thoại")).toHaveAttribute("aria-invalid", "true");
    expect(mutate).not.toHaveBeenCalled();
  });

  it("đủ 3 người thì không cho thêm nữa", () => {
    mockContacts([HOA, HUNG, { ...HUNG, id: "sos-3", full_name: "Phạm Thu", phone_number: "0911111111" }]);
    render(<EmergencySosManager />);

    expect(screen.getByText(/Đã đủ 3 người liên hệ/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Thêm người liên hệ/ })).not.toBeInTheDocument();
  });
});
