import { describe, expect, it } from "vitest";

import { NEAREST_HOSPITAL_QUERY, buildMapsSearchUrl, formatDistance } from "@/lib/maps";

/**
 * Hai bất biến của tầng bản đồ, cả hai đều là ràng buộc chứ không phải chi tiết
 * trình bày: đường dẫn Google Maps phải dùng được **mà không có API key** (nếu
 * không, một khoá sẽ phải nằm trong bundle trình duyệt), và khoảng cách phải
 * luôn đọc ra được là một con số ước lượng.
 */

describe("buildMapsSearchUrl", () => {
  it("dựng đường dẫn tìm kiếm công khai, không kèm khoá", () => {
    const url = buildMapsSearchUrl(NEAREST_HOSPITAL_QUERY);

    expect(url.startsWith("https://www.google.com/maps/search/?api=1&query=")).toBe(true);
    expect(url).not.toContain("key=");
  });

  it("mã hoá câu tìm kiếm tiếng Việt có dấu", () => {
    const url = buildMapsSearchUrl("bệnh viện gần đây");

    expect(url).not.toContain(" ");
    expect(decodeURIComponent(new URL(url).searchParams.get("query") ?? "")).toBe(
      "bệnh viện gần đây",
    );
  });

  it("không để câu tìm kiếm thoát ra khỏi tham số query", () => {
    const url = buildMapsSearchUrl("a&destination=nơi-khác");
    expect(new URL(url).searchParams.get("destination")).toBeNull();
  });
});

describe("formatDistance", () => {
  it.each([
    [0, "0 m"],
    [42, "40 m"],
    [850, "850 m"],
    [999, "1000 m"],
    [1000, "1.0 km"],
    [1200, "1.2 km"],
    [12_340, "12.3 km"],
  ])("%i mét hiển thị thành %s", (meters, expected) => {
    expect(formatDistance(meters)).toBe(expected);
  });

  it("không hiển thị gì cho giá trị vô nghĩa", () => {
    expect(formatDistance(Number.NaN)).toBe("");
    expect(formatDistance(-1)).toBe("");
    expect(formatDistance(Number.POSITIVE_INFINITY)).toBe("");
  });
});
