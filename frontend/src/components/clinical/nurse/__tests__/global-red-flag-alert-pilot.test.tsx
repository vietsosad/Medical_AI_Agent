import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SimpleNurseQueueItemDTO } from "@/types/simple-nurse";

const hooks = vi.hoisted(() => ({
  useSimpleNurseQueue: vi.fn(),
  useNurseQueue: vi.fn(),
  useAcknowledgeAlert: vi.fn(),
}));

vi.mock("@/lib/agent-mode", () => ({ IS_PILOT_AGENT_ACTIVE: true }));
vi.mock("@/queries/useSimpleNurseQueries", () => ({ useSimpleNurseQueue: hooks.useSimpleNurseQueue }));
vi.mock("@/hooks/queries/use-clinical-hitl", () => ({ useNurseQueue: hooks.useNurseQueue }));
vi.mock("@/hooks/mutations/use-hitl-mutations", () => ({ useAcknowledgeAlert: hooks.useAcknowledgeAlert }));

const { GlobalRedFlagAlert, pickUrgentUnclaimedCase } = await import(
  "@/components/clinical/nurse/GlobalRedFlagAlert"
);

/**
 * Khi Triage Agent là luồng đang chạy, cảnh báo toàn cục phải đọc hàng đợi
 * của nó: một ca ESI 1/2 chưa ai nhận phải hiện ở mọi trang lâm sàng và dẫn
 * tới hồ sơ pilot, không phải tới hồ sơ của runtime cũ.
 */

function queueItem(overrides: Partial<SimpleNurseQueueItemDTO>): SimpleNurseQueueItemDTO {
  return {
    session_id: "session-1",
    initial_message: "con tôi tím tái, thở rất mệt",
    final_action: "RETURN_MATCH",
    ai_proposed_esi: 1,
    is_insufficient: false,
    turn_count: 2,
    waiting_since: "2026-10-27T08:00:00Z",
    review_status: "WAITING_REVIEW",
    assigned_nurse_id: null,
    case_version: 1,
    unread_count: 0,
    patient_email: "nguoi.nha@example.com",
    patient_name: "Nguyễn Văn A",
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

function withQueue(items: SimpleNurseQueueItemDTO[]) {
  hooks.useSimpleNurseQueue.mockReturnValue({ data: { items } });
}

describe("cảnh báo ca khẩn toàn cục ở chế độ Triage Agent", () => {
  afterEach(() => Object.values(hooks).forEach((hook) => hook.mockReset()));

  it("đọc hàng đợi pilot và mở hồ sơ pilot của ca ESI 1 chưa ai nhận", () => {
    withQueue([queueItem({ session_id: "phiên/khẩn 01" })]);

    render(<GlobalRedFlagAlert />);

    expect(screen.getByRole("alert")).toHaveTextContent("Ca ESI 1 chưa có người nhận");
    expect(screen.getByRole("link", { name: "Mở hồ sơ lâm sàng của Nguyễn Văn A" })).toHaveAttribute(
      "href",
      "/clinical/cases-pilot/phi%C3%AAn%2Fkh%E1%BA%A9n%2001",
    );
    expect(hooks.useSimpleNurseQueue).toHaveBeenCalledWith(expect.objectContaining({ esiLevels: [1, 2] }));
    // Không còn thăm dò hàng đợi của runtime cũ ở chế độ này.
    expect(hooks.useNurseQueue).not.toHaveBeenCalled();
  });

  it("im lặng khi ca khẩn đã có người nhận", () => {
    withQueue([queueItem({ review_status: "ASSIGNED", assigned_nurse_id: "nurse-1" })]);

    render(<GlobalRedFlagAlert />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("ưu tiên ESI 1 trước ESI 2, rồi ca chờ lâu nhất", () => {
    const esi2Oldest = queueItem({ session_id: "esi2", ai_proposed_esi: 2, waiting_since: "2026-10-27T07:00:00Z" });
    const esi1Later = queueItem({ session_id: "esi1-later", waiting_since: "2026-10-27T09:00:00Z" });
    const esi1Earlier = queueItem({ session_id: "esi1-earlier", waiting_since: "2026-10-27T08:30:00Z" });
    const esi3 = queueItem({ session_id: "esi3", ai_proposed_esi: 3 });

    expect(pickUrgentUnclaimedCase([esi2Oldest, esi1Later, esi3, esi1Earlier])?.session_id).toBe("esi1-earlier");
    expect(pickUrgentUnclaimedCase([esi3])).toBeNull();
  });

  it("báo cả ca bị sàng lọc cấp cứu gắn cờ khi người bệnh còn đang trò chuyện, dù chưa có ESI", () => {
    withQueue([
      queueItem({
        session_id: "co-co",
        final_action: null,
        ai_proposed_esi: null,
        session_status: "ACTIVE",
        attention_required: true,
        attention_reason: "ngất hoặc bất tỉnh",
      }),
    ]);

    render(<GlobalRedFlagAlert />);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Ca cần xem ngay (ngất hoặc bất tỉnh) chưa có người nhận");
    // Cờ không phải mức ESI -- cảnh báo không được tự gán "ESI 1" cho ca này.
    expect(alert).not.toHaveTextContent("ESI 1");
  });

  it("xếp ca gắn cờ ngang ESI 1, trước ca ESI 2", () => {
    const esi2 = queueItem({ session_id: "esi2", ai_proposed_esi: 2, waiting_since: "2026-10-27T07:00:00Z" });
    const flagged = queueItem({
      session_id: "flagged",
      ai_proposed_esi: null,
      attention_required: true,
      waiting_since: "2026-10-27T09:00:00Z",
    });

    expect(pickUrgentUnclaimedCase([esi2, flagged])?.session_id).toBe("flagged");
  });
});
