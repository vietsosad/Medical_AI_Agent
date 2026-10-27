import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AppError from "@/app/error";

describe("ranh giới lỗi cấp ứng dụng", () => {
  it("không lộ chi tiết lỗi và luôn giữ lối gọi 115", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const error = new Error("TypeError: Cannot read properties of undefined (reading 'matched_esi_levels')");

    render(<AppError error={error} unstable_retry={vi.fn()} />);

    expect(document.body).not.toHaveTextContent("matched_esi_levels");
    expect(document.body).not.toHaveTextContent("TypeError");
    expect(screen.getByRole("link", { name: /115/ })).toHaveAttribute("href", "tel:115");
    expect(screen.getByRole("button", { name: /Thử lại/ })).toBeInTheDocument();
  });
});
