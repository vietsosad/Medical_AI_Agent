import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MotionGlobalConfig } from "framer-motion";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { SimpleTriageApiError } from "@/services/simple-triage.service";
import type { ProfileResponseDTO } from "@/services/profile.service";
import type { SimpleTriageSessionSummaryDTO } from "@/types/simple-triage";

const queries = vi.hoisted(() => ({
  useSimpleTriageSessions: vi.fn(),
  useGetProfiles: vi.fn(),
}));

vi.mock("@/queries/useSimpleTriageQueries", () => ({ useSimpleTriageSessions: queries.useSimpleTriageSessions }));
vi.mock("@/queries/useProfileQueries", () => ({ useGetProfiles: queries.useGetProfiles }));

const { default: SimpleTriageHistoryPage } = await import("@/app/(patient)/triage-pilot/history/page");

function session(overrides: Partial<SimpleTriageSessionSummaryDTO>): SimpleTriageSessionSummaryDTO {
  return {
    session_id: "session",
    status: "COMPLETED",
    profile_id: null,
    initial_message: "Mô tả",
    turn_count: 3,
    started_at: "2026-10-29T08:00:00",
    last_activity_at: "2026-10-29T08:10:00",
    completed_at: "2026-10-29T08:10:00",
    final_route: "TRIAGE",
    final_action: "RETURN_MATCH",
    matched_esi_levels: [4],
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
    ...overrides,
  };
}

const profiles: ProfileResponseDTO[] = [
  {
    id: "profile-kid",
    user_id: "user-1",
    full_name: "Bé Nguyễn An",
    relationship_type: "CHILD",
    is_primary: false,
    dob: null,
    avatar_color: "amber",
    age: 4,
    gender: "MALE",
    blood_type: null,
    height_cm: null,
    weight_kg: null,
    chronic_conditions: [],
    daily_medications: [],
    allergies: [],
    phone_number: null,
    emergency_contact_name: null,
    emergency_contact_phone: null,
    updated_at: null,
  },
];

// Thứ tự giống máy chủ: lần hoạt động gần nhất trước.
const SESSIONS = [
  session({
    session_id: "active-1",
    status: "ACTIVE",
    initial_message: "Đau bụng âm ỉ từ tối qua",
    turn_count: 5,
    matched_esi_levels: [],
    final_action: null,
    last_activity_at: "2026-10-29T09:42:00",
  }),
  session({
    session_id: "pending-1",
    profile_id: "profile-kid",
    initial_message: "Bé sốt 39 độ, li bì từ sáng",
    matched_esi_levels: [2],
    unread_from_staff: 2,
    last_activity_at: "2026-10-29T08:12:00",
  }),
  session({
    session_id: "adjusted-1",
    initial_message: "Ho kéo dài hai tuần",
    matched_esi_levels: [4],
    final_esi: 3,
    is_overridden: true,
    review_display_status: "OVERRIDDEN",
    last_activity_at: "2026-10-28T20:00:00",
  }),
  session({
    session_id: "incomplete-1",
    initial_message: "Chóng mặt khi đứng dậy",
    matched_esi_levels: [],
    final_action: "RETURN_INCOMPLETE",
    last_activity_at: "2026-10-28T07:00:00",
  }),
];

function mockSessions(data: SimpleTriageSessionSummaryDTO[]) {
  queries.useSimpleTriageSessions.mockReturnValue({
    data,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  });
}

beforeAll(() => {
  MotionGlobalConfig.skipAnimations = true;
});

afterAll(() => {
  MotionGlobalConfig.skipAnimations = false;
});

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 9, 29, 15, 0));
  queries.useGetProfiles.mockReturnValue({ data: profiles });
});

afterEach(() => {
  vi.useRealTimers();
  Object.values(queries).forEach((hook) => hook.mockReset());
});

describe("Lịch sử sàng lọc", () => {
  it("tóm tắt số phiên và ghim phiên đang hỏi dở lên đầu với lối tiếp tục", () => {
    mockSessions(SESSIONS);
    render(<SimpleTriageHistoryPage />);

    expect(screen.getByText("4 phiên · 2 phiên đang chờ điều dưỡng xác nhận")).toBeInTheDocument();

    const pinned = screen.getByRole("article", { name: "Đau bụng âm ỉ từ tối qua" });
    expect(within(pinned).getByText(/Đang hỏi dở · 5 lượt hội thoại/)).toBeInTheDocument();
    expect(within(pinned).getByRole("link", { name: /^Tiếp tục/ })).toHaveAttribute(
      "href",
      "/triage-pilot?session_id=active-1",
    );
  });

  it("nhóm theo ngày và mỗi thẻ cho đúng ô ESI, người, trạng thái và tin mới", () => {
    mockSessions(SESSIONS);
    render(<SimpleTriageHistoryPage />);

    expect(screen.getByRole("heading", { name: "Hôm nay" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hôm qua" })).toBeInTheDocument();

    const pending = screen.getByRole("link", { name: /Bé sốt 39 độ/ });
    expect(pending).toHaveAttribute("href", "/triage-pilot/history/pending-1?openChat=1");
    expect(within(pending).getByText(/Bé Nguyễn An · con · 08:12/)).toBeInTheDocument();
    expect(within(pending).getByText("Chờ điều dưỡng xác nhận")).toBeInTheDocument();
    expect(within(pending).getByText("2 tin mới")).toBeInTheDocument();
    expect(within(pending).getByText("Cấp cứu", { exact: false })).toBeInTheDocument();

    const adjusted = screen.getByRole("link", { name: /Ho kéo dài hai tuần/ });
    expect(adjusted).toHaveAttribute("href", "/triage-pilot/history/adjusted-1");
    expect(within(adjusted).getByText("3")).toBeInTheDocument();
    expect(within(adjusted).getByText("Điều dưỡng điều chỉnh từ ESI 4")).toBeInTheDocument();

    const incomplete = screen.getByRole("link", { name: /Chóng mặt khi đứng dậy/ });
    expect(within(incomplete).getByText("Chưa có mức ESI")).toBeInTheDocument();
    expect(within(incomplete).getByText(/chưa đủ dữ liệu để đề xuất mức/)).toBeInTheDocument();
  });

  it("'Chờ xác nhận' không gồm phiên đang hỏi dở; 'Đã xác nhận' có bộ lọc phụ", async () => {
    const user = userEvent.setup();
    mockSessions(SESSIONS);
    render(<SimpleTriageHistoryPage />);

    await user.click(screen.getByRole("tab", { name: "Chờ xác nhận" }));
    expect(screen.getByRole("tab", { name: "Chờ xác nhận" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Bé sốt 39 độ/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Chóng mặt khi đứng dậy/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Ho kéo dài hai tuần/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Đã xác nhận" }));
    await user.click(screen.getByRole("button", { name: "Giữ nguyên đề xuất" }));
    expect(screen.getByText("Không có phiên nào khớp bộ lọc hiện tại.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Điều dưỡng điều chỉnh" }));
    expect(screen.getByRole("link", { name: /Ho kéo dài hai tuần/ })).toBeInTheDocument();
    expect(screen.getByText("1 phiên phù hợp")).toBeInTheDocument();
  });

  it("tìm kiếm và bộ lọc ESI lọc theo đúng mức đang hiển thị", async () => {
    const user = userEvent.setup();
    mockSessions(SESSIONS);
    render(<SimpleTriageHistoryPage />);

    await user.type(screen.getByRole("searchbox", { name: "Tìm phiên sàng lọc" }), "chóng mặt");
    expect(screen.getByRole("link", { name: /Chóng mặt khi đứng dậy/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Bé sốt 39 độ/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Xóa nội dung tìm kiếm" }));
    await user.click(screen.getByRole("button", { name: /Bộ lọc/ }));
    // AI đề xuất ESI 4 nhưng điều dưỡng chốt ESI 3: phiên thuộc về ESI 3.
    await user.click(screen.getByRole("button", { name: /ESI 3/ }));
    expect(screen.getByRole("link", { name: /Ho kéo dài hai tuần/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Bé sốt 39 độ/ })).not.toBeInTheDocument();
  });

  it("dịch vụ tắt: nói điều người bệnh làm được, không nói về cờ cấu hình", () => {
    queries.useSimpleTriageSessions.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new SimpleTriageApiError("UNAVAILABLE", "Dịch vụ sàng lọc AI tạm thời chưa hoạt động."),
      refetch: vi.fn(),
    });
    render(<SimpleTriageHistoryPage />);

    expect(document.body).not.toHaveTextContent(/SIMPLE_AGENT_ENABLED|backend|Triage Agent đang tắt/i);
    expect(screen.getByRole("link", { name: /115/ })).toHaveAttribute("href", "tel:115");
  });

  it("chưa có phiên nào: mời bắt đầu sàng lọc", () => {
    mockSessions([]);
    render(<SimpleTriageHistoryPage />);

    expect(screen.getByText("Bạn chưa có phiên sàng lọc nào")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Bắt đầu sàng lọc/ })).toHaveAttribute("href", "/triage-pilot");
  });
});
