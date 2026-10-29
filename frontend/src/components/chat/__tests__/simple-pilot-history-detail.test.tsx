import { render, screen, within } from "@testing-library/react";
import { MotionGlobalConfig } from "framer-motion";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { SimpleTriageSessionDetailDTO } from "@/types/simple-triage";

const hooks = vi.hoisted(() => ({
  useSimpleTriageSessionDetail: vi.fn(),
  useSimpleCareTeamRealtime: vi.fn(),
  useGetProfiles: vi.fn(),
  searchParams: new URLSearchParams(),
}));

vi.mock("next/navigation", () => ({ useSearchParams: () => hooks.searchParams }));
vi.mock("@/queries/useSimpleTriageQueries", () => ({
  useSimpleTriageSessionDetail: hooks.useSimpleTriageSessionDetail,
  useSimpleCareTeamRealtime: hooks.useSimpleCareTeamRealtime,
}));
vi.mock("@/queries/useProfileQueries", () => ({ useGetProfiles: hooks.useGetProfiles }));
// Các khối này tự gọi API riêng; ở đây chỉ kiểm tra màn chi tiết đặt chúng đúng chỗ.
vi.mock("@/components/chat/NearbyFacilitiesCard", () => ({ NearbyFacilitiesCard: () => null }));
vi.mock("@/components/chat/SimplePilotSbarAccordion", () => ({ SimplePilotSbarAccordion: () => null }));
vi.mock("@/components/chat/SimpleCareTeamDock", () => ({
  SimpleCareTeamDock: ({ initialOpen }: { initialOpen?: boolean }) => (
    <div data-testid="care-team-dock" data-open={String(Boolean(initialOpen))} />
  ),
}));

const { SimplePilotHistoryDetail } = await import("@/components/chat/SimplePilotHistoryDetail");

function detail(overrides: Partial<SimpleTriageSessionDetailDTO>): SimpleTriageSessionDetailDTO {
  return {
    session_id: "session-abcdef12",
    status: "COMPLETED",
    profile_id: null,
    initial_message: "Khó thở dữ dội, môi tím",
    turn_count: 4,
    started_at: "2026-10-29T08:00:00",
    last_activity_at: "2026-10-29T08:10:00",
    completed_at: "2026-10-29T08:10:00",
    final_route: "TRIAGE",
    final_action: "RETURN_MATCH",
    matched_esi_levels: [1],
    final_message: null,
    final_concepts: [],
    review_status: null,
    is_overridden: false,
    final_esi: null,
    decision_type: null,
    decision_reason_code: null,
    decision_note: null,
    reviewer_name: null,
    reviewed_at: null,
    review_display_status: "PENDING_REVIEW",
    unread_from_staff: 0,
    messages: [
      {
        turn_index: 0,
        sender: "PATIENT",
        content: "Khó thở dữ dội, môi tím",
        route: null,
        action: null,
        question_target_id: null,
        decision_snapshot: {},
        created_at: "2026-10-29T08:00:00",
      },
      {
        turn_index: 0,
        sender: "AGENT",
        content: "Những gì bạn mô tả khớp tiêu chí khẩn cấp cao nhất.",
        route: "TRIAGE",
        action: "RETURN_MATCH",
        question_target_id: null,
        decision_snapshot: {
          matched_atoms: [
            { atom_id: "ATOM-1", decision_point: "A", criteria_text: "Cyanosis present", satisfied_requirements: [] },
          ],
        },
        created_at: "2026-10-29T08:00:05",
      },
    ],
    sbar: null,
    ...overrides,
  };
}

function mockDetail(data: SimpleTriageSessionDetailDTO) {
  hooks.useSimpleTriageSessionDetail.mockReturnValue({ data, isLoading: false, isError: false, error: null, refetch: vi.fn() });
}

beforeAll(() => {
  MotionGlobalConfig.skipAnimations = true;
});

afterAll(() => {
  MotionGlobalConfig.skipAnimations = false;
});

beforeEach(() => {
  hooks.useGetProfiles.mockReturnValue({ data: [] });
  hooks.searchParams = new URLSearchParams();
});

afterEach(() => {
  hooks.useSimpleTriageSessionDetail.mockReset();
  hooks.useGetProfiles.mockReset();
});

describe("Chi tiết một phiên trong lịch sử", () => {
  it("ESI 1 chưa xác nhận: thẻ kết quả báo động kèm 115, rồi trạng thái chờ điều dưỡng", () => {
    mockDetail(detail({}));
    render(<SimplePilotHistoryDetail sessionId="session-abcdef12" />);

    expect(screen.getByRole("heading", { level: 1, name: "Kết quả sàng lọc" })).toBeInTheDocument();
    const alert = screen.getByRole("alert");
    expect(within(alert).getByRole("link", { name: /115/ })).toHaveAttribute("href", "tel:115");
    expect(within(alert).getByText(/Mức đề xuất của AI/)).toBeInTheDocument();
    expect(screen.getByText("Đang chờ điều dưỡng xác nhận")).toBeInTheDocument();
    expect(screen.getByText("Cyanosis present")).toBeInTheDocument();
    // Bản ghi hội thoại vẫn còn, ở chế độ chỉ đọc.
    expect(screen.getByRole("heading", { name: "Hội thoại" })).toBeInTheDocument();
    expect(screen.getByText("Những gì bạn mô tả khớp tiêu chí khẩn cấp cao nhất.")).toBeInTheDocument();
    expect(screen.getByTestId("care-team-dock")).toHaveAttribute("data-open", "false");
  });

  it("điều dưỡng hạ mức: mức hiển thị là mức điều dưỡng, không còn nút 115", () => {
    mockDetail(
      detail({
        matched_esi_levels: [2],
        final_esi: 4,
        is_overridden: true,
        review_display_status: "OVERRIDDEN",
        reviewer_name: "Điều dưỡng Minh Anh",
        reviewed_at: "2026-10-29T09:30:00",
        decision_note: "Đã gọi lại, triệu chứng ổn định.",
      }),
    );
    hooks.searchParams = new URLSearchParams("openChat=1");
    render(<SimplePilotHistoryDetail sessionId="session-abcdef12" />);

    expect(screen.getByText("Kết quả điều dưỡng: ESI 4")).toBeInTheDocument();
    expect(screen.getByText("Điều dưỡng điều chỉnh từ ESI 2")).toBeInTheDocument();
    // Mức trên thẻ kết quả là mức điều dưỡng chốt, không được ghi là "đề xuất của AI".
    expect(screen.getByText("Điều dưỡng đã xác nhận mức này")).toBeInTheDocument();
    expect(screen.queryByText(/Mức đề xuất của AI/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /115/ })).not.toBeInTheDocument();
    expect(screen.queryByText("Đang chờ điều dưỡng xác nhận")).not.toBeInTheDocument();
    // Đến từ chip "n tin mới": kênh trao đổi mở sẵn.
    expect(screen.getByTestId("care-team-dock")).toHaveAttribute("data-open", "true");
  });

  it("chưa đủ dữ liệu: nói thẳng là chưa có mức, không tô màu khẩn cấp", () => {
    mockDetail(detail({ matched_esi_levels: [], final_action: "RETURN_INCOMPLETE", messages: [] }));
    render(<SimplePilotHistoryDetail sessionId="session-abcdef12" />);

    expect(screen.getByText("Chưa có mức ưu tiên đề xuất")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("phiên đang hỏi dở: mời trả lời tiếp, chưa mở kênh nhắn tin", () => {
    mockDetail(detail({ status: "ACTIVE", matched_esi_levels: [], final_action: null }));
    render(<SimplePilotHistoryDetail sessionId="session-abcdef12" />);

    expect(screen.getByRole("heading", { level: 1, name: "Phiên đang hỏi dở" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Tiếp tục/ })).toHaveAttribute(
      "href",
      "/triage-pilot?session_id=session-abcdef12",
    );
    expect(screen.queryByTestId("care-team-dock")).not.toBeInTheDocument();
  });
});
