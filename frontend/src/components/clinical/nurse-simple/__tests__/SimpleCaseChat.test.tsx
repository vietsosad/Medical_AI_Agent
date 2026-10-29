import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SimpleCareTeamMessageDTO } from "@/types/simple-care-team";

const hooks = vi.hoisted(() => ({
  useSimpleCaseCareTeamThread: vi.fn(),
  useSendSimpleCaseMessage: vi.fn(),
  useMarkSimpleCaseMessagesRead: vi.fn(),
  useSimpleCaseRealtime: vi.fn(),
}));

vi.mock("@/queries/useSimpleNurseQueries", () => hooks);
vi.mock("@/lib/realtime/useClinicalSocket", () => ({ useClinicalSocket: () => ({ status: "open" }) }));

const { SimpleCaseChatPanel } = await import("@/components/clinical/nurse-simple/SimpleCaseChatPanel");
const { SimpleCaseChatDock } = await import("@/components/clinical/nurse-simple/SimpleCaseChatDock");

const message = (overrides: Partial<SimpleCareTeamMessageDTO> & { id: string }): SimpleCareTeamMessageDTO => ({
  sender: "patient",
  content: "Bé vừa nôn thêm một lần.",
  created_at: "2026-10-29T08:40:00Z",
  read_at: null,
  ...overrides,
});

function setup(messages: SimpleCareTeamMessageDTO[], options: { unread?: number } = {}) {
  const send = vi.fn();
  const markRead = vi.fn();
  hooks.useSimpleCaseCareTeamThread.mockReturnValue({
    data: { session_id: "session-1", unread_count: options.unread ?? 0, messages },
    isLoading: false,
    isError: false,
  });
  hooks.useSendSimpleCaseMessage.mockReturnValue({ mutate: send, isPending: false, isError: false, error: null });
  hooks.useMarkSimpleCaseMessagesRead.mockReturnValue({ mutate: markRead });
  return { send, markRead, user: userEvent.setup() };
}

afterEach(() => Object.values(hooks).forEach((hook) => hook.mockReset()));

describe("kênh nhắn tin với người bệnh trong hồ sơ ca", () => {
  it("ghi rõ ai nói câu nào", () => {
    setup([
      message({ id: "m1", sender: "patient", content: "Tôi có nên đưa bé đi viện không?" }),
      message({ id: "m2", sender: "staff", content: "Chị đưa bé đến khoa cấp cứu nhi ngay." }),
    ]);
    render(<SimpleCaseChatPanel sessionId="session-1" />);

    expect(screen.getByText("Tôi có nên đưa bé đi viện không?").closest("li")).toHaveTextContent("Bệnh nhân");
    expect(screen.getByText("Chị đưa bé đến khoa cấp cứu nhi ngay.").closest("li")).toHaveTextContent("Bạn (y tá)");
  });

  it("đánh dấu đã đọc khi mở ca còn tin chưa đọc", () => {
    const { markRead } = setup([message({ id: "m1" })], { unread: 1 });
    render(<SimpleCaseChatPanel sessionId="session-1" />);

    expect(markRead).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("heading", { name: /Nhắn người bệnh/ })).toHaveTextContent("1 tin chưa đọc");
  });

  it("gửi tin bằng Enter, bỏ khoảng trắng thừa", async () => {
    const { send, user } = setup([]);
    render(<SimpleCaseChatPanel sessionId="session-1" />);

    await user.type(screen.getByLabelText("Nhắn cho bệnh nhân"), "  Chị giữ máy giúp em.  {Enter}");

    expect(send).toHaveBeenCalledTimes(1);
    expect(send.mock.calls[0][0]).toMatchObject({ content: "Chị giữ máy giúp em." });
  });

  it("ca đã đóng: vẫn đọc được trao đổi cũ nhưng không gửi thêm", () => {
    setup([message({ id: "m1", content: "Cảm ơn điều dưỡng." })]);
    render(<SimpleCaseChatPanel sessionId="session-1" readOnly />);

    expect(screen.getByText("Cảm ơn điều dưỡng.")).toBeInTheDocument();
    expect(screen.getByText("Ca đã đóng, không thể nhắn thêm.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Gửi tin nhắn cho bệnh nhân" })).not.toBeInTheDocument();
  });
});

describe("khung nhắn tin nổi", () => {
  it("nút nổi báo số tin chưa đọc, mở ra thì đưa con trỏ vào ô soạn tin", async () => {
    const { user } = setup([message({ id: "m1" })], { unread: 2 });
    render(<SimpleCaseChatDock sessionId="session-1" />);

    await user.click(screen.getByRole("button", { name: "Mở khung nhắn tin với bệnh nhân, 2 tin chưa đọc" }));

    await waitFor(() => expect(screen.getByLabelText("Nhắn cho bệnh nhân")).toHaveFocus());
  });

  it("thu gọn thì trả tiêu điểm về nút nổi", async () => {
    const { user } = setup([]);
    render(<SimpleCaseChatDock sessionId="session-1" initialOpen />);

    await user.click(screen.getByRole("button", { name: "Thu gọn khung nhắn tin" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Mở khung nhắn tin với bệnh nhân" })).toHaveFocus(),
    );
  });
});
