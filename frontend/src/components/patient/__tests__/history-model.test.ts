import { describe, expect, it } from "vitest";

import {
  dayLabel,
  displayedEsiOf,
  groupByDay,
  matchesSegment,
  sessionStatusKind,
  subjectLabelFor,
} from "@/components/patient/history-model";
import type { ProfileResponseDTO } from "@/services/profile.service";
import type { SimpleTriageSessionSummaryDTO } from "@/types/simple-triage";

function session(overrides: Partial<SimpleTriageSessionSummaryDTO> = {}): SimpleTriageSessionSummaryDTO {
  return {
    session_id: "session-1",
    status: "COMPLETED",
    profile_id: null,
    initial_message: "Đau đầu nhẹ",
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

function profile(overrides: Partial<ProfileResponseDTO> = {}): ProfileResponseDTO {
  return {
    id: "profile-self",
    user_id: "user-1",
    full_name: "Nguyễn Văn Demo",
    relationship_type: "SELF",
    is_primary: true,
    dob: null,
    avatar_color: "blue",
    age: 34,
    gender: "MALE",
    blood_type: "O+",
    height_cm: null,
    weight_kg: null,
    chronic_conditions: [],
    daily_medications: [],
    allergies: [],
    phone_number: null,
    emergency_contact_name: null,
    emergency_contact_phone: null,
    updated_at: null,
    ...overrides,
  };
}

describe("mức ESI hiển thị trên ô", () => {
  it("dùng mức điều dưỡng đã chốt khi có quyết định", () => {
    expect(
      displayedEsiOf(session({ matched_esi_levels: [4], final_esi: 2, review_display_status: "OVERRIDDEN" })),
    ).toBe(2);
  });

  it("dùng mức AI nặng nhất khi chưa có quyết định, kể cả khi có final_esi rác", () => {
    expect(displayedEsiOf(session({ matched_esi_levels: [3, 2], final_esi: 5 }))).toBe(2);
  });

  it("trả null khi chưa có mức nào", () => {
    expect(displayedEsiOf(session({ matched_esi_levels: [] }))).toBeNull();
  });
});

describe("trạng thái phiên và bộ lọc chính", () => {
  it("phiên đang hỏi dở không bao giờ là 'chờ điều dưỡng xác nhận'", () => {
    const active = session({ status: "ACTIVE", matched_esi_levels: [] });
    expect(sessionStatusKind(active)).toBe("IN_PROGRESS");
    expect(matchesSegment(active, "PENDING", "ALL")).toBe(false);
    expect(matchesSegment(active, "ALL", "ALL")).toBe(true);
  });

  it("'Đã xác nhận' gồm cả giữ nguyên và điều chỉnh; bộ lọc phụ tách hai loại", () => {
    const approved = session({ review_display_status: "APPROVED", final_esi: 4 });
    const overridden = session({ review_display_status: "OVERRIDDEN", final_esi: 2 });
    expect(matchesSegment(approved, "CONFIRMED", "ALL")).toBe(true);
    expect(matchesSegment(overridden, "CONFIRMED", "ALL")).toBe(true);
    expect(matchesSegment(approved, "CONFIRMED", "OVERRIDDEN")).toBe(false);
    expect(matchesSegment(overridden, "CONFIRMED", "APPROVED")).toBe(false);
    expect(matchesSegment(approved, "PENDING", "ALL")).toBe(false);
  });

  it("phiên đã xong chưa có quyết định là đang chờ điều dưỡng", () => {
    expect(sessionStatusKind(session())).toBe("AWAITING_NURSE");
    expect(matchesSegment(session(), "PENDING", "ALL")).toBe(true);
  });
});

describe("phiên dành cho ai", () => {
  const profiles = [
    profile(),
    profile({ id: "profile-mom", full_name: "Trần Thị Hoa", relationship_type: "PARENT", is_primary: false }),
  ];

  it("gọi hồ sơ chính là 'Bạn' và ghi quan hệ cho người thân", () => {
    expect(subjectLabelFor("profile-self", profiles)).toEqual({ name: "Bạn", relation: null });
    expect(subjectLabelFor("profile-mom", profiles)).toEqual({ name: "Trần Thị Hoa", relation: "cha/mẹ" });
  });

  it("không đoán tên khi hồ sơ còn đang tải, và báo rõ hồ sơ đã xóa", () => {
    expect(subjectLabelFor("profile-mom", undefined)).toBeNull();
    expect(subjectLabelFor("profile-gone", profiles)).toEqual({ name: "Hồ sơ đã xóa", relation: null });
    expect(subjectLabelFor(null, undefined)).toEqual({ name: "Ẩn danh", relation: null });
  });
});

describe("nhóm theo ngày", () => {
  const now = new Date(2026, 9, 29, 15, 0);

  it("đặt tên Hôm nay, Hôm qua, rồi thứ và ngày", () => {
    expect(dayLabel(new Date(2026, 9, 29, 0, 5), now)).toBe("Hôm nay");
    expect(dayLabel(new Date(2026, 9, 28, 23, 50), now)).toBe("Hôm qua");
    expect(dayLabel(new Date(2026, 9, 24, 8, 0), now)).toBe("Thứ Bảy, 24/10");
    expect(dayLabel(new Date(2025, 9, 24, 8, 0), now)).toContain("2025");
  });

  it("giữ thứ tự đầu vào và dồn mục không có ngày xuống cuối", () => {
    const items = [
      { id: "a", date: new Date(2026, 9, 29, 9) },
      { id: "b", date: null },
      { id: "c", date: new Date(2026, 9, 29, 8) },
      { id: "d", date: new Date(2026, 9, 27, 8) },
    ];
    const groups = groupByDay(items, (item) => item.date, now);
    expect(groups.map((group) => group.label)).toEqual(["Hôm nay", "Thứ Ba, 27/10", "Không rõ thời gian"]);
    expect(groups[0].items.map((item) => item.id)).toEqual(["a", "c"]);
  });
});
