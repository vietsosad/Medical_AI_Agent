import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ClinicalTranscriptMessageDTO } from "@/types/clinical-hitl";

const hooks = vi.hoisted(() => ({
  useCaseMessages: vi.fn(),
  useCaseRealtime: vi.fn(),
  useSendCaseMessage: vi.fn(),
  useMarkCaseMessagesRead: vi.fn(),
}));

vi.mock("@/hooks/queries/use-clinical-hitl", () => hooks);

const { CaseChatPanel } = await import("@/components/clinical/nurse/CaseChatPanel");

const message = (
  overrides: Partial<ClinicalTranscriptMessageDTO> & { id: string },
): ClinicalTranscriptMessageDTO => ({
  sender: "PATIENT",
  content: "Nội dung",
  created_at: "2026-08-22T09:00:00Z",
  sender_name: null,
  read_at: null,
  ...overrides,
});

function setup(
  messages: ClinicalTranscriptMessageDTO[],
  options: { unread?: number; realtime?: string } = {},
) {
  hooks.useCaseRealtime.mockReturnValue(options.realtime ?? "open");
  hooks.useCaseMessages.mockReturnValue({
    data: { case_id: "case-1", messages, unread_count: options.unread ?? 0 },
    isLoading: false,
    isError: false,
  });
  hooks.useSendCaseMessage.mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
  });
  hooks.useMarkCaseMessagesRead.mockReturnValue({ mutate: vi.fn() });
}

describe("hội thoại của ca trong console lâm sàng", () => {
  afterEach(() => {
    Object.values(hooks).forEach((hook) => hook.mockReset());
  });

  it("dán nhãn khác nhau cho tin của AI và tin của nhân viên y tế", () => {
    setup([
      message({ id: "m1", sender: "AI_AGENT", content: "Tôi ghi nhận triệu chứng." }),
      message({
        id: "m2",
        sender: "NURSE",
        content: "Anh giữ máy giúp em.",
        sender_name: "Điều dưỡng Trần B",
      }),
    ]);
    render(<CaseChatPanel caseId="case-1" isAssignedToMe patientName="Nguyễn Văn A" />);

    expect(screen.getByText("Trợ lý AI")).toBeInTheDocument();
    // Tên thật của nhân viên thay cho nhãn vai trò chung chung.
    expect(screen.getByText("Điều dưỡng Trần B")).toBeInTheDocument();
  });

  it("không bao giờ hiển thị tin của nhân viên dưới nhãn của AI", () => {
    setup([
      message({ id: "m1", sender: "NURSE", content: "Em là điều dưỡng trực.", sender_name: null }),
    ]);
    render(<CaseChatPanel caseId="case-1" isAssignedToMe patientName="Nguyễn Văn A" />);

    const bubble = screen.getByText("Em là điều dưỡng trực.").closest("li");
    expect(bubble).not.toBeNull();
    expect(within(bubble as HTMLElement).queryByText("Trợ lý AI")).not.toBeInTheDocument();
    expect(within(bubble as HTMLElement).getByText("Nhân viên y tế")).toBeInTheDocument();
  });

  it("khoá hội thoại lại khi nhân viên chưa nhận ca", () => {
    setup([]);
    render(
      <CaseChatPanel caseId="case-1" isAssignedToMe={false} patientName="Nguyễn Văn A" />,
    );

    expect(screen.getByText(/Cần nhận ca trước khi đọc hoặc nhắn tin/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Gửi/ })).not.toBeInTheDocument();
  });

  it("báo mất kết nối mà vẫn giữ nguyên hội thoại đã tải", () => {
    setup([message({ id: "m1", content: "Em vẫn tức ngực." })], { realtime: "reconnecting" });
    render(<CaseChatPanel caseId="case-1" isAssignedToMe patientName="Nguyễn Văn A" />);

    expect(screen.getByText(/Mất kết nối realtime\. Đang kết nối lại/)).toBeInTheDocument();
    expect(screen.getByText("Em vẫn tức ngực.")).toBeInTheDocument();
  });

  it("đánh dấu đã đọc khi mở ca còn tin chưa đọc", () => {
    const markRead = vi.fn();
    setup([message({ id: "m1" })], { unread: 2 });
    hooks.useMarkCaseMessagesRead.mockReturnValue({ mutate: markRead });

    render(<CaseChatPanel caseId="case-1" isAssignedToMe patientName="Nguyễn Văn A" />);
    expect(markRead).toHaveBeenCalledTimes(1);
  });

  it("không gọi đánh dấu đã đọc khi không còn tin nào chưa đọc", () => {
    const markRead = vi.fn();
    setup([message({ id: "m1" })], { unread: 0 });
    hooks.useMarkCaseMessagesRead.mockReturnValue({ mutate: markRead });

    render(<CaseChatPanel caseId="case-1" isAssignedToMe patientName="Nguyễn Văn A" />);
    expect(markRead).not.toHaveBeenCalled();
  });
});
