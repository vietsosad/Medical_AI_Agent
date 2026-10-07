import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const hooks = vi.hoisted(() => ({
  useSimpleNurseQueue: vi.fn(),
  useSimpleNurseQueueRealtime: vi.fn(),
}));

vi.mock("@/queries/useSimpleNurseQueries", () => ({
  useSimpleNurseQueue: hooks.useSimpleNurseQueue,
  useSimpleNurseQueueRealtime: hooks.useSimpleNurseQueueRealtime,
}));

const { SimpleClinicalInbox } = await import("@/components/clinical/nurse-simple/SimpleClinicalInbox");

function setupInbox() {
  hooks.useSimpleNurseQueue.mockReturnValue({
    data: { items: [] },
    isLoading: false,
    isError: false,
  });
}

describe("hộp thư Simple Agent của điều dưỡng", () => {
  afterEach(() => Object.values(hooks).forEach((hook) => hook.mockReset()));

  it("hiển thị trạng thái rỗng gọn trong drawer thay vì một danh sách trống kéo giãn", () => {
    setupInbox();
    render(<SimpleClinicalInbox />);

    fireEvent.click(screen.getByRole("button", { name: "Tin nhắn mới từ ca bạn phụ trách" }));

    const dialog = screen.getByRole("dialog", { name: "Tin nhắn mới" });
    expect(dialog).toHaveClass("flex", "h-dvh", "overflow-hidden");
    expect(screen.getByText("Hộp thư đang trống")).toBeVisible();
    expect(screen.getByText("Hiện chưa có bệnh nhân nào đang chờ bạn trả lời.")).toBeVisible();
    expect(screen.queryByText("Không có tin nhắn nào của bệnh nhân đang chờ trả lời.")).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Đóng hộp thư" })[0]);
    expect(screen.queryByRole("dialog", { name: "Tin nhắn mới" })).not.toBeInTheDocument();
  });
});
