import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SimpleNurseQueueItemDTO } from "@/types/simple-nurse";

const hooks = vi.hoisted(() => ({
  useSimpleNurseQueue: vi.fn(),
  useSimpleNurseQueueRealtime: vi.fn(),
  useNurseQueue: vi.fn(),
  useClinicalInbox: vi.fn(),
  useClinicalRealtime: vi.fn(),
  logout: vi.fn(),
  search: { value: "tab=parked" },
}));

vi.mock("@/lib/agent-mode", () => ({
  IS_PILOT_AGENT_ACTIVE: true,
  nurseQueueHref: () => "/clinical/queue-pilot",
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/clinical/queue-pilot",
  useSearchParams: () => new URLSearchParams(hooks.search.value),
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
    user: { id: "nurse-1", name: "Nguyễn Minh Anh", capabilities: [] },
    logout: hooks.logout,
  }),
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn() } }));

const { ClinicalSidebar } = await import("@/components/clinical/ClinicalSidebar");

/**
 * Thanh điều phối sau khi thiết kế lại phải giữ mọi đường dẫn cũ, cho thấy số
 * ca chưa ai nhận (đỏ khi trong đó có ca khẩn) và luôn có lối đăng xuất.
 */

function queueItem(overrides: Partial<SimpleNurseQueueItemDTO>): SimpleNurseQueueItemDTO {
  return {
    session_id: "session-1",
    initial_message: "Khó thở",
    final_action: "RETURN_MATCH",
    ai_proposed_esi: 3,
    is_insufficient: false,
    turn_count: 2,
    waiting_since: "2026-10-29T08:00:00Z",
    review_status: "WAITING_REVIEW",
    assigned_nurse_id: null,
    case_version: 1,
    unread_count: 0,
    patient_email: null,
    patient_name: null,
    final_esi: null,
    decision_type: null,
    decision_note: null,
    decided_at: null,
    parked_at: null,
    parked_by_nurse_id: null,
    parked_reason: null,
    ...overrides,
  };
}

function serveQueue(items: SimpleNurseQueueItemDTO[], mineCount: number) {
  hooks.useSimpleNurseQueue.mockReturnValue({
    data: {
      items,
      summary: { total_waiting: items.length + mineCount, mine_count: mineCount, insufficient_count: 0 },
      pagination: { page: 1, page_size: 20, total_items: items.length, total_pages: 1 },
    },
    isLoading: false,
    isError: false,
  });
}

describe("thanh điều phối ở chế độ Triage Agent", () => {
  beforeEach(() => {
    hooks.search.value = "tab=parked";
    hooks.useClinicalRealtime.mockReturnValue({ status: "open" });
    hooks.logout.mockResolvedValue(undefined);
  });

  afterEach(() => {
    Object.values(hooks).forEach((hook) => {
      if (typeof hook === "function") hook.mockReset();
    });
  });

  it("giữ đủ năm đường dẫn của trạm và đánh dấu mục đang mở", () => {
    serveQueue([queueItem({ session_id: "a" })], 0);
    render(<ClinicalSidebar />);

    const nav = screen.getByRole("navigation", { name: "Điều hướng nhân viên lâm sàng" });
    const hrefs = Array.from(nav.querySelectorAll("a")).map((link) => link.getAttribute("href"));
    expect(hrefs).toEqual([
      "/clinical/dashboard-pilot",
      "/clinical/queue-pilot?tab=queue",
      "/clinical/queue-pilot?tab=mine",
      "/clinical/queue-pilot?tab=parked",
      "/clinical/queue-pilot?tab=decided",
    ]);
    expect(screen.getByRole("link", { name: /^Tạm gác/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /^Hàng đợi/ })).not.toHaveAttribute("aria-current");
    // Hàng đợi cũ không bị thăm dò khi Triage Agent là luồng đang chạy.
    expect(hooks.useNurseQueue).not.toHaveBeenCalled();
  });

  it("đếm ca chưa ai nhận và báo đỏ khi trong đó có ca khẩn", () => {
    serveQueue(
      [
        queueItem({ session_id: "co", ai_proposed_esi: null, attention_required: true }),
        queueItem({ session_id: "b", ai_proposed_esi: 4 }),
        queueItem({ session_id: "c", ai_proposed_esi: 5 }),
      ],
      2,
    );
    render(<ClinicalSidebar />);

    const queueLink = screen.getByRole("link", { name: /^Hàng đợi/ });
    expect(queueLink).toHaveTextContent("3");
    expect(queueLink).toHaveTextContent("ca chưa ai nhận, có ca khẩn");
    expect(screen.getByRole("link", { name: /^Ca của tôi/ })).toHaveTextContent("2");
  });

  it("không báo đỏ khi hàng đợi chỉ có ca ít khẩn", () => {
    serveQueue([queueItem({ session_id: "b", ai_proposed_esi: 4 })], 0);
    render(<ClinicalSidebar />);

    const queueLink = screen.getByRole("link", { name: /^Hàng đợi/ });
    expect(queueLink).toHaveTextContent("ca chưa ai nhận");
    expect(queueLink).not.toHaveTextContent("có ca khẩn");
  });

  it("cho biết kênh trực tiếp và người đang trực, đăng xuất được", async () => {
    serveQueue([], 0);
    render(<ClinicalSidebar />);

    expect(screen.getByText("Nguyễn Minh Anh")).toBeInTheDocument();
    expect(screen.getByText("Điều dưỡng phân luồng")).toBeInTheDocument();
    expect(screen.getAllByText("Trực tuyến").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));
    expect(hooks.logout).toHaveBeenCalledWith(true);
  });
});
