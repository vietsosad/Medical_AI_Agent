import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CareTeamMessageDTO, CareTeamThreadDTO } from "@/services/triage.service";

const mocks = vi.hoisted(() => ({
  useQuery: vi.fn(),
  useMutation: vi.fn(),
  useQueryClient: vi.fn(),
  useClinicalSocket: vi.fn(),
}));

vi.mock("@tanstack/react-query", () => ({
  useQuery: mocks.useQuery,
  useMutation: mocks.useMutation,
  useQueryClient: mocks.useQueryClient,
}));

vi.mock("@/lib/realtime/useClinicalSocket", () => ({
  useClinicalSocket: mocks.useClinicalSocket,
}));

const { CareTeamDock } = await import("@/components/chat/CareTeamDock");

const message = (over: Partial<CareTeamMessageDTO> & { id: string }): CareTeamMessageDTO => ({
  sender: "staff",
  senderName: "Điều dưỡng Trần Thị Bình",
  content: "Anh còn đau ngực không ạ?",
  createdAt: "2026-08-23T09:00:00Z",
  readAt: null,
  ...over,
});

function setup(thread: Partial<CareTeamThreadDTO> = {}, socket = "open") {
  const send = vi.fn();
  const markRead = vi.fn();

  mocks.useQuery.mockReturnValue({
    data: {
      session_id: "case-1",
      care_team_name: null,
      care_team_status: "AI_SCREENING",
      unread_from_staff: 0,
      messages: [],
      ...thread,
    },
    isLoading: false,
    isError: false,
  });
  mocks.useQueryClient.mockReturnValue({ invalidateQueries: vi.fn() });
  mocks.useClinicalSocket.mockReturnValue({ status: socket });
  // Component gọi useMutation đúng hai lần mỗi lần render, theo thứ tự cố định:
  // gửi tin rồi tới đánh dấu đã đọc. Đếm theo modulo giữ đúng cặp qua mọi lần
  // render lại, thay vì cạn mock sau lần đầu.
  let call = 0;
  mocks.useMutation.mockImplementation(() => {
    const isSend = call % 2 === 0;
    call += 1;
    return {
      mutate: isSend ? send : markRead,
      isPending: false,
      isError: false,
      error: null,
    };
  });

  return { send, markRead };
}

describe("kênh trao đổi với nhân viên y tế", () => {
  afterEach(() => Object.values(mocks).forEach((m) => m.mockReset()));

  it("luôn hiện diện ngay cả khi chưa ai tiếp nhận ca", () => {
    // Đây chính là lỗi đã báo: kênh bị ẩn hoàn toàn ở phiên mới, nên người bệnh
    // không hề biết mình có thể nhắn cho nhân viên y tế.
    setup({ care_team_status: "AI_SCREENING" });
    render(<CareTeamDock sessionId="case-1" />);

    expect(screen.getByRole("button", { name: /Mở kênh trao đổi/ })).toBeInTheDocument();
    expect(screen.getByText("Nhân viên y tế")).toBeInTheDocument();
  });

  it("cho nhắn ngay cả khi chưa ai nhận ca", async () => {
    // Chặn ở đây đồng nghĩa với việc tin của người bệnh không bao giờ tới được
    // trạm trực trước khi có người chủ động mở hồ sơ ra.
    const user = userEvent.setup();
    setup({ care_team_status: "WAITING_REVIEW" });
    render(<CareTeamDock sessionId="case-1" />);

    await user.click(screen.getByRole("button", { name: /Mở kênh trao đổi/ }));

    expect(screen.getByLabelText("Nhắn cho nhân viên y tế")).toBeInTheDocument();
    expect(screen.getByText(/trạm trực sẽ thấy ngay/)).toBeInTheDocument();
  });

  it("khoá kênh lại khi ca đã hoàn tất", async () => {
    const user = userEvent.setup();
    setup({ care_team_status: "COMPLETED" });
    render(<CareTeamDock sessionId="case-1" />);

    await user.click(screen.getByRole("button", { name: /Mở kênh trao đổi/ }));

    expect(screen.queryByLabelText("Nhắn cho nhân viên y tế")).not.toBeInTheDocument();
    expect(screen.getByText(/Ca đã hoàn tất/)).toBeInTheDocument();
  });

  it("chỉ mở ô nhập khi thực sự có người đang phụ trách ca", async () => {
    const user = userEvent.setup();
    setup({ care_team_status: "STAFF_REVIEWING", care_team_name: "Điều dưỡng Trần Thị Bình" });
    render(<CareTeamDock sessionId="case-1" />);

    await user.click(screen.getByRole("button", { name: /Mở kênh trao đổi/ }));

    expect(screen.getByLabelText("Nhắn cho nhân viên y tế")).toBeInTheDocument();
    expect(screen.getByText("Điều dưỡng Trần Thị Bình")).toBeInTheDocument();
  });

  it("gửi được tin và không gửi chuỗi rỗng", async () => {
    const user = userEvent.setup();
    const { send } = setup({ care_team_status: "STAFF_REVIEWING" });
    render(<CareTeamDock sessionId="case-1" />);

    await user.click(screen.getByRole("button", { name: /Mở kênh trao đổi/ }));
    const submit = screen.getByRole("button", { name: "Gửi tin nhắn cho nhân viên y tế" });
    expect(submit).toBeDisabled();

    await user.type(screen.getByLabelText("Nhắn cho nhân viên y tế"), "Em vẫn tức ngực ạ");
    await user.click(submit);
    expect(send).toHaveBeenCalledWith("Em vẫn tức ngực ạ");
  });

  it("tự mở kênh và đánh dấu đã đọc khi có tin mới", async () => {
    const { markRead } = setup({ care_team_status: "STAFF_REVIEWING", unread_from_staff: 3 });
    render(<CareTeamDock sessionId="case-1" />);

    expect(
      await screen.findByRole("region", { name: "Kênh trao đổi với nhân viên y tế" }),
    ).toBeInTheDocument();
    await waitFor(() => expect(markRead).toHaveBeenCalledOnce());
  });

  it("phân biệt rõ lời của nhân viên y tế với lời của chính người bệnh", async () => {
    const user = userEvent.setup();
    setup({
      care_team_status: "STAFF_REVIEWING",
      messages: [
        message({ id: "m1" }),
        message({ id: "m2", sender: "patient", senderName: null, content: "Dạ vẫn còn ạ." }),
      ],
    });
    render(<CareTeamDock sessionId="case-1" />);

    await user.click(screen.getByRole("button", { name: /Mở kênh trao đổi/ }));

    expect(screen.getAllByText("Điều dưỡng Trần Thị Bình").length).toBeGreaterThan(0);
    expect(screen.getByText("Bạn")).toBeInTheDocument();
  });

  it("báo mất kết nối nhưng vẫn giữ nội dung đã tải", async () => {
    const user = userEvent.setup();
    setup(
      { care_team_status: "STAFF_REVIEWING", messages: [message({ id: "m1" })] },
      "reconnecting",
    );
    render(<CareTeamDock sessionId="case-1" />);

    await user.click(screen.getByRole("button", { name: /Mở kênh trao đổi/ }));

    expect(screen.getByText(/Mất kết nối realtime/)).toBeInTheDocument();
    expect(screen.getByText("Anh còn đau ngực không ạ?")).toBeInTheDocument();
  });

  it("thu gọn lại được sau khi mở", async () => {
    const user = userEvent.setup();
    setup({ care_team_status: "STAFF_REVIEWING" });
    render(<CareTeamDock sessionId="case-1" />);

    await user.click(screen.getByRole("button", { name: /Mở kênh trao đổi/ }));
    await user.click(screen.getByRole("button", { name: "Thu gọn kênh trao đổi" }));

    expect(screen.getByRole("button", { name: /Mở kênh trao đổi/ })).toBeInTheDocument();
  });
});
