import { describe, expect, it } from "vitest";

import {
  advanceCircularPhase,
  advancePhase,
  approachVelocity,
  circularItemX,
  impulseForDistance,
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

describe("quán tính của dòng chủ đề", () => {
  it("cho dòng chảy ngược khi vận tốc âm và vẫn khép vòng", () => {
    expect(advancePhase(10, -40, 500, 500)).toBeCloseTo(490);
    expect(advancePhase(10, 40, 500, 500)).toBeCloseTo(30);
  });

  it("giảm tốc dần về đích, độc lập với nhịp khung hình", () => {
    const oneStep = approachVelocity(30, 0, 100, 0.5);
    let twoSteps = approachVelocity(30, 0, 50, 0.5);
    twoSteps = approachVelocity(twoSteps, 0, 50, 0.5);

    expect(oneStep).toBeGreaterThan(0);
    expect(oneStep).toBeLessThan(30);
    expect(twoSteps).toBeCloseTo(oneStep);
    // Sau ba hằng số thời gian, vận tốc gần như đã dừng.
    expect(approachVelocity(30, 0, 1_500, 0.5)).toBeLessThan(30 * 0.06);
  });

  it("cú đẩy một thẻ đi đúng quãng đường của một thẻ", () => {
    const settle = 0.4;
    let velocity = impulseForDistance(300, settle);
    let travelled = 0;
    for (let frame = 0; frame < 600; frame += 1) {
      travelled += velocity * (1 / 120);
      velocity = approachVelocity(velocity, 0, 1_000 / 120, settle);
    }
    expect(travelled).toBeGreaterThan(285);
    expect(travelled).toBeLessThan(315);
  });
});
