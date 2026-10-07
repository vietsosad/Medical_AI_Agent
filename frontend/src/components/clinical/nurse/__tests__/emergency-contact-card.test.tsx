import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { EmergencyContactPersonDTO } from "@/types/clinical-hitl";

const hooks = vi.hoisted(() => ({ useEmergencyContacts: vi.fn() }));

vi.mock("@/hooks/queries/use-clinical-hitl", () => hooks);

const { EmergencyContactCard } = await import(
  "@/components/clinical/nurse/EmergencyContactCard"
);

const CHILD_CASE: EmergencyContactPersonDTO[] = [
  {
    label: "Bệnh nhân",
    full_name: "Bé Nguyễn Văn C",
    relationship: "CHILD",
    phone: "0987654321",
  },
  {
    label: "Chủ tài khoản / người giám hộ",
    full_name: "Nguyễn Văn A",
    relationship: "Người tạo hồ sơ",
    phone: "0912345678",
  },
];

function setContacts(contacts: EmergencyContactPersonDTO[]) {
  hooks.useEmergencyContacts.mockImplementation((_caseId: string, enabled: boolean) => ({
    data: enabled ? { case_id: "case-1", contacts, expires_at: "2026-08-22T10:00:00Z" } : undefined,
    isLoading: false,
    isError: false,
  }));
}

describe("danh bạ khẩn cấp của một ca", () => {
  afterEach(() => hooks.useEmergencyContacts.mockReset());

  it("che số điện thoại cho tới khi nhân viên chủ động mở", () => {
    setContacts(CHILD_CASE);
    render(<EmergencyContactCard caseId="case-1" isAssignedToMe />);

    expect(screen.queryByText("0987654321")).not.toBeInTheDocument();
    expect(screen.getByText(/ghi vào nhật ký kiểm toán/)).toBeInTheDocument();
  });

  it("giữ số của bệnh nhân tách hẳn số của người giám hộ", async () => {
    const user = userEvent.setup();
    setContacts(CHILD_CASE);
    render(<EmergencyContactCard caseId="case-1" isAssignedToMe />);

    await user.click(screen.getByRole("button", { name: /Hiện số liên hệ/ }));

    const patientRow = screen.getByText("Bé Nguyễn Văn C").closest("li");
    const guardianRow = screen.getByText("Nguyễn Văn A").closest("li");

    expect(within(patientRow as HTMLElement).getByRole("link")).toHaveAttribute(
      "href",
      "tel:0987654321",
    );
    expect(within(guardianRow as HTMLElement).getByRole("link")).toHaveAttribute(
      "href",
      "tel:0912345678",
    );
  });

  it("nói rõ chưa cập nhật thay vì mượn số của người khác", async () => {
    const user = userEvent.setup();
    setContacts([{ ...CHILD_CASE[0], phone: null }, CHILD_CASE[1]]);
    render(<EmergencyContactCard caseId="case-1" isAssignedToMe />);

    await user.click(screen.getByRole("button", { name: /Hiện số liên hệ/ }));

    const patientRow = screen.getByText("Bé Nguyễn Văn C").closest("li");
    expect(within(patientRow as HTMLElement).getByText("Chưa cập nhật")).toBeInTheDocument();
    expect(within(patientRow as HTMLElement).queryByRole("link")).not.toBeInTheDocument();
  });

  it("chặn nhân viên chưa nhận ca xem thông tin liên hệ", () => {
    setContacts(CHILD_CASE);
    render(<EmergencyContactCard caseId="case-1" isAssignedToMe={false} />);

    expect(screen.getByText(/Cần nhận ca trước khi xem thông tin liên hệ/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Hiện số liên hệ/ })).toBeDisabled();
  });

  it("dịch mã quan hệ sang tiếng Việt cho người đọc", async () => {
    const user = userEvent.setup();
    setContacts(CHILD_CASE);
    render(<EmergencyContactCard caseId="case-1" isAssignedToMe />);

    await user.click(screen.getByRole("button", { name: /Hiện số liên hệ/ }));
    expect(screen.getByText("Con")).toBeInTheDocument();
  });
});
