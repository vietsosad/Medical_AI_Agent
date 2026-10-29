import { describe, expect, it } from "vitest";

import { formatWait } from "@/components/clinical/nurse-simple/wait-time";

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
