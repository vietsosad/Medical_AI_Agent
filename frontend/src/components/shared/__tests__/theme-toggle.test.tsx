import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { ThemeProvider } from "@/components/providers/theme-provider";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { DARK_CLASS, THEME_STORAGE_KEY } from "@/lib/theme";

afterEach(() => {
  document.documentElement.classList.remove(DARK_CLASS);
  document.documentElement.style.colorScheme = "";
  window.localStorage.clear();
});

function renderToggle(variant?: "compact" | "full") {
  return render(
    <ThemeProvider>
      <ThemeToggle variant={variant} />
    </ThemeProvider>,
  );
}

describe("ThemeToggle", () => {
  it("chỉ có hai lựa chọn, và cả hai đều hiện ra", () => {
    renderToggle();

    expect(screen.getAllByRole("button")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Sáng" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tối" })).toBeInTheDocument();
    // Không có nút thứ ba: cài đặt hệ điều hành vẫn quyết định điểm khởi đầu,
    // nhưng nó không cần một biểu tượng riêng trên thanh điều hướng.
    expect(screen.queryByRole("button", { name: /hệ thống/i })).toBeNull();
  });

  it("luôn có đúng một chế độ được đánh dấu, kể cả khi người dùng chưa bấm bao giờ", () => {
    renderToggle();

    const pressed = screen
      .getAllByRole("button")
      .filter((button) => button.getAttribute("aria-pressed") === "true");
    expect(pressed).toHaveLength(1);
  });

  it("chọn chế độ tối thì gắn class lên thẻ html và lưu lại lựa chọn", async () => {
    const user = userEvent.setup();
    renderToggle();

    await user.click(screen.getByRole("button", { name: "Tối" }));

    expect(document.documentElement.classList.contains(DARK_CLASS)).toBe(true);
    expect(document.documentElement.style.colorScheme).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(screen.getByRole("button", { name: "Tối" })).toHaveAttribute("aria-pressed", "true");
  });

  it("quay lại chế độ sáng thì gỡ sạch class", async () => {
    const user = userEvent.setup();
    renderToggle();

    await user.click(screen.getByRole("button", { name: "Tối" }));
    await user.click(screen.getByRole("button", { name: "Sáng" }));

    expect(document.documentElement.classList.contains(DARK_CLASS)).toBe(false);
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
  });

  it("khôi phục lựa chọn đã lưu ở lần vào sau", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");
    renderToggle();

    expect(screen.getByRole("button", { name: "Tối" })).toHaveAttribute("aria-pressed", "true");
    expect(document.documentElement.classList.contains(DARK_CLASS)).toBe(true);
  });

  it("bản đầy đủ hiện nhãn chữ cho màn hình hẹp", () => {
    renderToggle("full");

    // Cùng một nhãn, nhưng ở bản compact nó nằm trong sr-only.
    expect(screen.getByRole("button", { name: "Tối" })).toHaveTextContent("Tối");
  });

  it("nằm ngoài provider thì ẩn hẳn, không dựng một nút bấm vô tác dụng", () => {
    const { container } = render(<ThemeToggle />);
    expect(container).toBeEmptyDOMElement();
  });

  it("không dùng emoji", () => {
    const { container } = renderToggle("full");
    expect(container.textContent ?? "").not.toMatch(/\p{Extended_Pictographic}/u);
  });
});
