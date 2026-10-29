import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { activeBottomNavHref, isChatScreen, PatientBottomNav } from "@/components/shared/PatientBottomNav";

let mockPathname = "/";
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

afterEach(() => {
  mockPathname = "/";
});

describe("thanh điều hướng đáy của người bệnh", () => {
  it("ẩn trên màn hội thoại, nơi ô soạn tin nằm sát đáy", () => {
    mockPathname = "/triage-pilot";
    const { container } = render(<PatientBottomNav />);
    expect(container).toBeEmptyDOMElement();
    expect(isChatScreen("/triage")).toBe(true);
    expect(isChatScreen("/triage-pilot/history")).toBe(false);
  });

  it("ở màn chi tiết phiên: chỉ 'Lịch sử' sáng, không sáng cả 'Sàng lọc'", () => {
    mockPathname = "/triage-pilot/history/session-1";
    render(<PatientBottomNav />);

    const nav = screen.getByRole("navigation", { name: "Điều hướng chính" });
    expect(nav).toHaveClass("md:hidden");
    expect(screen.getByRole("link", { name: "Lịch sử" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Sàng lọc" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Hồ sơ" })).toHaveAttribute("href", "/profile");
  });

  it("trang EHR thuộc mục 'Hồ sơ'", () => {
    mockPathname = "/profile/ehr";
    render(<PatientBottomNav />);
    expect(screen.getByRole("link", { name: "Hồ sơ" })).toHaveAttribute("aria-current", "page");
  });

  it("tiền tố khớp dài nhất thắng, ở cả bản pilot lẫn bản DeepAgent", () => {
    const items = [
      { href: "/triage-pilot", match: ["/triage-pilot", "/triage"] },
      { href: "/triage-pilot/history", match: ["/triage-pilot/history", "/history"] },
      { href: "/profile", match: ["/profile"] },
    ];
    expect(activeBottomNavHref("/triage-pilot/history", items)).toBe("/triage-pilot/history");
    expect(activeBottomNavHref("/history/case-1", items)).toBe("/triage-pilot/history");
    expect(activeBottomNavHref("/profiles", items)).toBeNull();
  });
});
