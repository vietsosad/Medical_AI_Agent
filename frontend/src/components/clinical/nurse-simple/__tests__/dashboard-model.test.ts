import { describe, expect, it } from "vitest";

import {
  DASHBOARD_WINDOWS,
  HEAT_STEPS,
  heatStep,
  hourOfDayInLocalTime,
  hourRangeLabel,
  matrixRowLabel,
  matrixRowMeta,
} from "@/components/clinical/nurse-simple/dashboard/dashboard-model";

const utcHours = (counts: Record<number, number>) =>
  Array.from({ length: 24 }, (_, hour) => ({ hour_utc: hour, completed: counts[hour] ?? 0 }));

describe("thang màu của ma trận", () => {
  it("ô bằng 0 không tô; ô nhiều nhất luôn đậm nhất", () => {
    expect(heatStep(0, 9)).toBe(0);
    expect(heatStep(9, 9)).toBe(HEAT_STEPS);
    expect(heatStep(1, 9)).toBe(1);
    expect(heatStep(2, 9)).toBe(2);
  });

  it("không bao giờ vượt quá số bậc đã kiểm định", () => {
    for (let count = 1; count <= 40; count += 1) {
      const step = heatStep(count, 40);
      expect(step).toBeGreaterThanOrEqual(1);
      expect(step).toBeLessThanOrEqual(HEAT_STEPS);
    }
  });
});

describe("nhãn hàng của ma trận", () => {
  it("phiên đang sàng lọc không bao giờ mang chữ ESI", () => {
    expect(matrixRowMeta("IN_PROGRESS").name).toBe("Đang sàng lọc");
    expect(matrixRowLabel("IN_PROGRESS")).not.toMatch(/ESI/);
  });

  it("mức ESI đọc đúng tên của thang phân loại", () => {
    expect(matrixRowLabel("1")).toBe("ESI 1 · Hồi sức");
    expect(matrixRowLabel("INSUFFICIENT")).toBe("Chưa đủ dữ liệu");
  });
});

describe("giờ trong ngày theo máy người xem", () => {
  it("xoay giờ UTC sang giờ Việt Nam (UTC+7)", () => {
    const local = hourOfDayInLocalTime(utcHours({ 7: 5, 20: 2 }), 420);

    expect(local).not.toBeNull();
    expect(local?.[14].completed).toBe(5);
    // 20 giờ UTC là 3 giờ sáng hôm sau ở Việt Nam.
    expect(local?.[3].completed).toBe(2);
    expect(local?.reduce((sum, point) => sum + point.completed, 0)).toBe(7);
  });

  it("độ lệch âm cũng xoay đúng chiều", () => {
    const local = hourOfDayInLocalTime(utcHours({ 2: 4 }), -300);
    expect(local?.[21].completed).toBe(4);
  });

  it("độ lệch lẻ giờ thì từ chối thay vì gán sai giờ", () => {
    expect(hourOfDayInLocalTime(utcHours({ 2: 4 }), 330)).toBeNull();
  });

  it("đọc khung giờ theo cách người trực nói", () => {
    expect(hourRangeLabel(9)).toBe("09:00 – 09:59");
  });
});

describe("cửa sổ lịch sử", () => {
  it("trùng đúng danh sách backend nhận", () => {
    // src/services/simple_nurse_dashboard.py: WINDOW_DAYS_CHOICES = (7, 14, 30, 90)
    expect(DASHBOARD_WINDOWS).toEqual([7, 14, 30, 90]);
  });
});
