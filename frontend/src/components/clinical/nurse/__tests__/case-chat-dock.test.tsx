import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const hooks = vi.hoisted(() => ({
  useCaseMessages: vi.fn(),
  useCaseRealtime: vi.fn(),
  useSendCaseMessage: vi.fn(),
  useMarkCaseMessagesRead: vi.fn(),
  useClinicalSocket: vi.fn(),
}));

vi.mock("@/hooks/queries/use-clinical-hitl", () => ({
  useCaseMessages: hooks.useCaseMessages,
  useCaseRealtime: hooks.useCaseRealtime,
  useSendCaseMessage: hooks.useSendCaseMessage,
  useMarkCaseMessagesRead: hooks.useMarkCaseMessagesRead,
}));

vi.mock("@/lib/realtime/useClinicalSocket", () => ({
  useClinicalSocket: hooks.useClinicalSocket,
}));

const { CaseChatDock } = await import("@/components/clinical/nurse/CaseChatDock");

function setup(unread = 0) {
  hooks.useCaseMessages.mockReturnValue({
    data: { case_id: "case-1", messages: [], unread_count: unread },
    isLoading: false,
    isError: false,
  });
  hooks.useCaseRealtime.mockReturnValue("open");
  hooks.useSendCaseMessage.mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
  });
  hooks.useMarkCaseMessagesRead.mockReturnValue({ mutate: vi.fn() });
  hooks.useClinicalSocket.mockReturnValue({ status: "open" });
}

describe("khung hội thoại nổi trong hồ sơ ca", () => {
  afterEach(() => Object.values(hooks).forEach((hook) => hook.mockReset()));

  it("luôn với tới được mà không phải cuộn tìm trong hồ sơ", () => {
    setup();
    render(<CaseChatDock caseId="case-1" isAssignedToMe patientName="Nguyễn Văn A" />);

    expect(screen.getByRole("button", { name: /Mở hội thoại với người bệnh/ })).toBeInTheDocument();
  });

  it("hiện số tin chưa đọc ngay trên viên thu gọn", () => {
    setup(4);
    render(<CaseChatDock caseId="case-1" isAssignedToMe patientName="Nguyễn Văn A" />);

    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("4 tin chưa đọc")).toBeInTheDocument();
  });

  it("nói rõ phải nhận ca trước khi mở hội thoại", () => {
    setup();
    render(
      <CaseChatDock caseId="case-1" isAssignedToMe={false} patientName="Nguyễn Văn A" />,
    );

    expect(screen.getByText("Cần nhận ca trước")).toBeInTheDocument();
  });

  it("mở ra rồi thu gọn lại được", async () => {
    const user = userEvent.setup();
    setup();
    render(<CaseChatDock caseId="case-1" isAssignedToMe patientName="Nguyễn Văn A" />);

    await user.click(screen.getByRole("button", { name: /Mở hội thoại với người bệnh/ }));
    expect(screen.getByLabelText("Nội dung nhắn cho người bệnh")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Thu gọn hội thoại" }));
    expect(screen.getByRole("button", { name: /Mở hội thoại với người bệnh/ })).toBeInTheDocument();
  });

  it("chỉ mở kênh thời gian thực khi nhân viên đang phụ trách ca", () => {
    setup();
    render(
      <CaseChatDock caseId="case-1" isAssignedToMe={false} patientName="Nguyễn Văn A" />,
    );

    expect(hooks.useClinicalSocket).toHaveBeenCalledWith(
      expect.objectContaining({ enabled: false }),
    );
  });

  it("tự bật khung khi người bệnh vừa nhắn", async () => {
    setup();
    render(<CaseChatDock caseId="case-1" isAssignedToMe patientName="Nguyễn Văn A" />);

    const { onEvent } = hooks.useClinicalSocket.mock.calls.at(-1)![0];
    // Sự kiện thật do backend phát khi người bệnh gửi tin.
    await Promise.resolve(onEvent({ event: "message.created", payload: { sender: "PATIENT" } }));

    expect(
      await screen.findByLabelText("Nội dung nhắn cho người bệnh"),
    ).toBeInTheDocument();
  });
});
