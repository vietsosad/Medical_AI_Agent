import { afterEach, describe, expect, it, vi } from "vitest";

import { formatWait, serverTimeMs, waitingMinutes } from "@/components/clinical/nurse-simple/wait-time";

describe("cách đọc thời gian chờ", () => {
  it.each([
    [0, "Dưới 1 phút"],
    [45, "45 phút"],
    [60, "1 giờ"],
    [95, "1 giờ 35 phút"],
    [24 * 60, "1 ngày"],
    // 1460 giờ 27 phút từng hiện nguyên văn như vậy trên bảng ca.
    [1460 * 60 + 27, "60 ngày 20 giờ"],
  ])("%i phút -> %s", (minutes, text) => {
    expect(formatWait(minutes)).toBe(text);
  });
});

describe("mốc giờ từ backend", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  /**
   * Backend gửi giờ UTC không kèm hậu tố ("2026-11-03T08:00:00"). Trình duyệt
   * đọc chuỗi đó là giờ địa phương, nên ở Việt Nam một ca vừa tới 10 phút từng
   * hiện thành "7 giờ 10 phút". Kiểm thử chạy ở mọi múi giờ đều phải ra 10.
   */
  it("chuỗi không có múi giờ được đọc là UTC, ở bất kỳ múi giờ nào của máy", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-03T08:10:00Z"));

    expect(waitingMinutes("2026-11-03T08:00:00")).toBe(10);
    // Backend in micro giây (isoformat của Python).
    expect(waitingMinutes("2026-11-03T07:59:59.123456")).toBe(10);
    expect(serverTimeMs("2026-11-03T08:00:00")).toBe(Date.UTC(2026, 10, 3, 8, 0, 0));
  });

  it("chuỗi đã có múi giờ thì giữ nguyên", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-03T08:10:00Z"));

    expect(waitingMinutes("2026-11-03T08:00:00Z")).toBe(10);
    expect(waitingMinutes("2026-11-03T15:00:00+07:00")).toBe(10);
  });

  it("mốc nằm sau đồng hồ máy thì không ra thời gian chờ âm", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-03T08:10:00Z"));

    expect(waitingMinutes("2026-11-03T08:30:00")).toBe(0);
  });
});
