import { describe, expect, it } from "vitest";

import {
  advanceCircularPhase,
  circularItemX,
  positiveModulo,
} from "@/components/landing/topic-stream-motion";

describe("chuyển động vòng kín của dòng chủ đề", () => {
  it("giữ vận tốc không đổi theo thời gian khung hình", () => {
    expect(advanceCircularPhase(12, 500, 16, 500)).toBeCloseTo(20);
    expect(advanceCircularPhase(20, 250, 16, 500)).toBeCloseTo(24);
  });

  it("khép vòng tại đường nối mà không đảo chiều", () => {
    expect(advanceCircularPhase(498, 250, 16, 500)).toBeCloseTo(2);
    expect(positiveModulo(-2, 500)).toBe(498);
  });

  it("chỉ đưa một phần tử về cuối sau khi phần tử đó rời hẳn mép trái", () => {
    expect(circularItemX(0, 100, 99, 500)).toBeCloseTo(-99);
    expect(circularItemX(0, 100, 101, 500)).toBeCloseTo(399);
  });
});
