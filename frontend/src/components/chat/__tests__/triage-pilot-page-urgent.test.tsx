import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SimpleTriageApiError } from "@/services/simple-triage.service";
import { useTriageStore } from "@/store/useTriageStore";

const queries = vi.hoisted(() => ({
  useSimpleTriageSessionDetail: vi.fn(),
  useStartSimpleTriage: vi.fn(),
  useSubmitSimpleTriageChat: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams("session_id=session-1"),
}));
vi.mock("@/queries/useSimpleTriageQueries", () => queries);

// Các thẻ phụ bên dưới kết quả tự gọi API riêng; ở đây chỉ kiểm tra khung trang.
vi.mock("@/components/profile/StickyProfileContextBar", () => ({ default: () => null }));
vi.mock("@/components/chat/VerifiedClinicalContextHeader", () => ({ VerifiedClinicalContextHeader: () => null }));
vi.mock("@/components/chat/NearbyFacilitiesCard", () => ({ NearbyFacilitiesCard: () => null }));
vi.mock("@/components/chat/SimpleCareTeamDock", () => ({ SimpleCareTeamDock: () => null }));
vi.mock("@/components/chat/SimplePilotSbarAccordion", () => ({ SimplePilotSbarAccordion: () => null }));
vi.mock("@/components/chat/SimpleMatchedProtocolsCard", () => ({ SimpleMatchedProtocolsCard: () => null }));
vi.mock("@/components/chat/SimplePilotNurseDecisionSummary", () => ({ SimplePilotNurseDecisionSummary: () => null }));

const { default: TriagePilotPage } = await import("@/app/(patient)/triage-pilot/page");

/**
 * Hai trạng thái mà người bệnh đang nguy kịch có thể gặp: dịch vụ tắt, và một
 * kết quả ESI 1. Ở cả hai, lối gọi 115 phải có mặt và màn hình không được nói
 * về cấu hình máy chủ.
 */

function completedSession(level: number) {
  return {
    data: {
      session_id: "session-1",
      status: "COMPLETED",
      matched_esi_levels: [level],
      final_esi: null,
      review_display_status: "PENDING",
      reviewer_name: null,
      reviewed_at: null,
      decision_note: null,
      profile_id: null,
      sbar: null,
      messages: [],
    },
    isError: false,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  };
}

function callLinks(): HTMLElement[] {
  return screen.queryAllByRole("link").filter((link) => link.getAttribute("href") === "tel:115");
}

beforeEach(() => {
  useTriageStore.setState({ hasConsented: true });
  queries.useStartSimpleTriage.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  queries.useSubmitSimpleTriageChat.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  vi.spyOn(window, "requestAnimationFrame").mockImplementation(() => 0);
});

afterEach(() => Object.values(queries).forEach((hook) => hook.mockReset()));

describe("trang sàng lọc Triage Agent", () => {
  it("khi dịch vụ tắt: nói điều người bệnh làm được, không nói về cờ cấu hình", () => {
    queries.useSimpleTriageSessionDetail.mockReturnValue({
      data: undefined,
      isError: true,
      isLoading: false,
      error: new SimpleTriageApiError("UNAVAILABLE", "Dịch vụ sàng lọc AI tạm thời chưa hoạt động."),
      refetch: vi.fn(),
    });

    render(<TriagePilotPage />);

    expect(document.body).not.toHaveTextContent(/SIMPLE_AGENT_ENABLED|backend/i);
    expect(callLinks().length).toBeGreaterThan(0);
  });

  it("kết quả ESI 1: thẻ được thông báo và thanh đáy ghim nút gọi 115", () => {
    queries.useSimpleTriageSessionDetail.mockReturnValue(completedSession(1));

    render(<TriagePilotPage />);

    const result = screen.getByRole("alert");
    expect(within(result).getByRole("link", { name: /115/ })).toHaveAttribute("href", "tel:115");
    // Một nút trong thẻ, một nút ở thanh đáy luôn trong tầm mắt.
    expect(callLinks()).toHaveLength(2);
    // "Bắt đầu phiên mới" vẫn còn, chỉ lùi xuống làm lựa chọn phụ.
    expect(screen.getAllByRole("button", { name: /Bắt đầu phiên mới/ }).length).toBeGreaterThan(0);
  });

  it("kết quả ESI 4: không có nút gọi 115 nào được đẩy lên", () => {
    queries.useSimpleTriageSessionDetail.mockReturnValue(completedSession(4));

    render(<TriagePilotPage />);

    expect(callLinks()).toHaveLength(0);
  });

  it("phiên đang chạy có lượt bị sàng lọc cấp cứu gắn cờ: nút 115 ở ngay trên ô nhập, chat không bị khoá", () => {
    queries.useSimpleTriageSessionDetail.mockReturnValue(activeSession({
      rule_id: "SA_SCREEN_SYNCOPE_V1",
      kind: "EMERGENCY",
      label: "ngất hoặc bất tỉnh",
      trigger: "ngất xỉu",
    }));

    render(<TriagePilotPage />);

    expect(callLinks()).toHaveLength(1);
    // Cờ không khoá hội thoại: ô nhập vẫn còn để người bệnh tiếp tục kể.
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("phiên đang chạy không có cờ: không đẩy nút 115 lên", () => {
    queries.useSimpleTriageSessionDetail.mockReturnValue(activeSession(undefined));

    render(<TriagePilotPage />);

    expect(callLinks()).toHaveLength(0);
  });
});

function activeSession(safetyAlert: Record<string, string> | undefined) {
  const session = completedSession(1);
  return {
    ...session,
    data: {
      ...session.data,
      status: "ACTIVE",
      matched_esi_levels: [],
      messages: [
        {
          turn_index: 0,
          sender: "AGENT",
          content: "Lưu ý an toàn: bạn có nhắc tới ngất hoặc bất tỉnh.",
          route: "TRIAGE",
          action: "ASK_NEXT",
          question_target_id: null,
          decision_snapshot: safetyAlert ? { safety_alert: safetyAlert } : {},
          created_at: "2026-10-27T08:00:00Z",
        },
      ],
    },
  };
}
