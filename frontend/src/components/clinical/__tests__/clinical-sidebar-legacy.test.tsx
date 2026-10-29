import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const hooks = vi.hoisted(() => ({
  useSimpleNurseQueue: vi.fn(),
  useSimpleNurseQueueRealtime: vi.fn(),
  useNurseQueue: vi.fn(),
  useClinicalInbox: vi.fn(),
  useClinicalRealtime: vi.fn(),
}));

vi.mock("@/lib/agent-mode", () => ({
  IS_PILOT_AGENT_ACTIVE: false,
  nurseQueueHref: () => "/clinical/queue",
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/clinical/queue",
  useSearchParams: () => new URLSearchParams("specialist=1"),
}));

vi.mock("@/queries/useSimpleNurseQueries", () => ({
  useSimpleNurseQueue: hooks.useSimpleNurseQueue,
  useSimpleNurseQueueRealtime: hooks.useSimpleNurseQueueRealtime,
}));

vi.mock("@/hooks/queries/use-clinical-hitl", () => ({
  useNurseQueue: hooks.useNurseQueue,
  useClinicalInbox: hooks.useClinicalInbox,
}));

vi.mock("@/components/clinical/ClinicalRealtimeProvider", () => ({
  useClinicalRealtime: hooks.useClinicalRealtime,
}));

vi.mock("@/store/useAuthStore", () => ({
  useAuthStore: () => ({
    user: { id: "doctor-1", name: "Trần Văn Bác", capabilities: ["SPECIALIST_REVIEW"] },
    logout: vi.fn(),
  }),
}));

const { ClinicalSidebar } = await import("@/components/clinical/ClinicalSidebar");

/** Khi Triage Agent không chạy, thanh vẫn dẫn về đúng ba màn của hàng đợi cũ. */
describe("thanh điều phối ở chế độ hàng đợi cũ", () => {
  afterEach(() => Object.values(hooks).forEach((hook) => hook.mockReset()));

  it("giữ ba đường dẫn cũ, bộ đếm của hàng đợi cũ và nhãn bác sĩ", () => {
    hooks.useNurseQueue.mockReturnValue({
      data: { summary: { total_waiting: 5, mine_count: 1, specialist_count: 2 } },
    });
    hooks.useClinicalInbox.mockReturnValue({
      data: { items: [], total_unread: 0, urgent_unread: 0 },
      isLoading: false,
      isError: false,
    });
    hooks.useClinicalRealtime.mockReturnValue({
      status: "reconnecting",
      quickChatCaseId: null,
      openQuickChat: vi.fn(),
      closeQuickChat: vi.fn(),
    });

    render(<ClinicalSidebar />);

    const nav = screen.getByRole("navigation", { name: "Điều hướng nhân viên lâm sàng" });
    const hrefs = Array.from(nav.querySelectorAll("a")).map((link) => link.getAttribute("href"));
    expect(hrefs).toEqual(["/clinical/queue", "/clinical/queue?mine=1", "/clinical/queue?specialist=1"]);
    expect(screen.getByRole("link", { name: /^Đánh giá chuyên sâu/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /^Hàng đợi/ })).toHaveTextContent("5");
    expect(screen.getByText("Bác sĩ · đánh giá chuyên sâu")).toBeInTheDocument();
    expect(screen.getAllByText("Đang kết nối lại").length).toBeGreaterThan(0);
    // Hộp thư production vẫn ở đúng chỗ; hàng đợi pilot không bị gọi.
    expect(screen.getByRole("button", { name: "Tin nhắn và hoạt động mới" })).toBeInTheDocument();
    expect(hooks.useSimpleNurseQueue).not.toHaveBeenCalled();
  });
});
