import { describe, expect, it } from "vitest";

import {
  AGREEMENT_SERIES,
  claimBinBucket,
  claimBinLabel,
  DECISION_RELATION_LABELS,
  decisionRelation,
  describeWeekdayDays,
  hasEnoughCases,
  weekdayHourPeak,
  weekdayLabel,
} from "@/components/clinical/nurse-simple/dashboard/dashboard-model";
import type { SimpleWeekdayHourDTO } from "@/types/simple-nurse";

function weekdayPanel(days: number[], cells: Record<string, number> = {}): SimpleWeekdayHourDTO {
  return {
    utc_offset_hours: 7,
    first_day: "2026-08-16",
    last_day: "2026-09-14",
    total: Object.values(cells).reduce((sum, value) => sum + value, 0),
    rows: days.map((dayCount, index) => {
      const weekday = (index + 1) as 1 | 2 | 3 | 4 | 5 | 6 | 7;
      return {
        weekday,
        days: dayCount,
        hours: Array.from({ length: 24 }, (_, hour) => cells[`${weekday}:${hour}`] ?? 0),
      };
    }),
  };
}

describe("điều dưỡng đã làm gì ở một ô của ma trận", () => {
  it("thang ESI chạy ngược: chốt số nhỏ hơn là khẩn hơn", () => {
    expect(decisionRelation("4", 2)).toBe("more_urgent");
    expect(decisionRelation("2", 4)).toBe("less_urgent");
    expect(decisionRelation("3", 3)).toBe("kept");
  });

  it("hàng không có mức AI thì không có chiều nào để so", () => {
    expect(decisionRelation("INSUFFICIENT", 1)).toBe("no_proposal");
    expect(decisionRelation("IN_PROGRESS", 5)).toBe("no_proposal");
  });

  it("dùng đúng chữ của khối đối chiếu, không bao giờ nói độ chính xác", () => {
    const agreementLabels = AGREEMENT_SERIES.map((series) => series.label);
    expect(agreementLabels).toContain(DECISION_RELATION_LABELS.kept);
    expect(agreementLabels).toContain(DECISION_RELATION_LABELS.more_urgent);
    expect(agreementLabels).toContain(DECISION_RELATION_LABELS.less_urgent);
    expect(Object.values(DECISION_RELATION_LABELS).join(" ")).not.toMatch(/chính xác/i);
  });
});

describe("cột của phân bố thời gian nhận ca", () => {
  it("đọc khoảng phút như người trực nói", () => {
    expect(claimBinLabel({ min_minutes: 0, max_minutes: 5, count: 1 })).toBe("0 – 4 phút");
    expect(claimBinLabel({ min_minutes: 60, max_minutes: null, count: 1 })).toBe("Từ 60 phút");
  });

  it("gắn đúng mốc tô màu của bảng ca", () => {
    expect(claimBinBucket({ min_minutes: 25, max_minutes: 30, count: 0 })).toBe("UNDER_WARNING");
    expect(claimBinBucket({ min_minutes: 30, max_minutes: 35, count: 0 })).toBe("WARNING");
    expect(claimBinBucket({ min_minutes: 60, max_minutes: null, count: 0 })).toBe("CRITICAL");
  });

  it("chưa đủ ca thì không nêu tỉ lệ", () => {
    expect(hasEnoughCases(0, 5)).toBe(false);
    expect(hasEnoughCases(4, 5)).toBe(false);
    expect(hasEnoughCases(5, 5)).toBe(true);
  });
});

describe("thứ × giờ", () => {
  it("tên thứ theo ISO", () => {
    expect(weekdayLabel(1)).toBe("Thứ Hai");
    expect(weekdayLabel(7)).toBe("Chủ nhật");
  });

  it("khung giờ đông nhất, hòa thì nói rõ số khung hòa", () => {
    const peak = weekdayHourPeak(weekdayPanel([2, 2, 2, 2, 2, 2, 2], { "1:9": 3, "5:14": 3, "6:2": 1 }));
    expect(peak).toEqual({ weekday: 1, hour: 9, count: 3, ties: 1 });
    expect(weekdayHourPeak(weekdayPanel([2, 2, 2, 2, 2, 2, 2]))).toBeNull();
  });

  it("nói rõ thứ nào có thêm một ngày trong khoảng", () => {
    expect(describeWeekdayDays(weekdayPanel([2, 2, 2, 2, 2, 2, 2]))).toBe("Mỗi thứ có 2 ngày trong khoảng này.");
    expect(describeWeekdayDays(weekdayPanel([5, 4, 4, 4, 4, 4, 5]))).toMatch(
      /^Thứ Hai, Chủ nhật có 5 ngày trong khoảng này, các thứ khác có 4 ngày/,
    );
  });
});
