import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const hooks = vi.hoisted(() => ({
  useClinicalInbox: vi.fn(),
  useClinicalRealtime: vi.fn(),
}));

vi.mock("@/hooks/queries/use-clinical-hitl", () => ({
  useClinicalInbox: hooks.useClinicalInbox,
}));

vi.mock("@/components/clinical/ClinicalRealtimeProvider", () => ({
  useClinicalRealtime: hooks.useClinicalRealtime,
}));

const { ClinicalInbox } = await import("@/components/clinical/ClinicalInbox");

function setupInbox() {
  hooks.useClinicalInbox.mockReturnValue({
    data: { items: [], total_unread: 0, urgent_unread: 0 },
    isLoading: false,
    isError: false,
  });
  hooks.useClinicalRealtime.mockReturnValue({
    quickChatCaseId: null,
    openQuickChat: vi.fn(),
    closeQuickChat: vi.fn(),
  });
}

describe("vị trí hộp thư lâm sàng", () => {
  afterEach(() => Object.values(hooks).forEach((hook) => hook.mockReset()));

  it("nằm trong luồng thanh điều phối thay vì nổi che nội dung", () => {
    setupInbox();
    render(<ClinicalInbox />);

    const trigger = screen.getByRole("button", { name: "Tin nhắn và hoạt động mới" });
    expect(trigger).not.toHaveClass("fixed");
    expect(trigger).toHaveClass("relative", "min-h-11", "w-full");

    fireEvent.click(trigger);
    expect(screen.getByRole("dialog", { name: "Tin nhắn và hoạt động mới" })).toBeInTheDocument();
  });
});
