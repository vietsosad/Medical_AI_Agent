import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DARK_CLASS,
  THEME_STORAGE_KEY,
  applyTheme,
  isThemePreference,
  readStoredPreference,
  resolveTheme,
  setThemePreference,
  subscribeToTheme,
  themeBootstrapScript,
} from "@/lib/theme";

/**
 * Lớp lõi của chế độ sáng/tối. Hai thứ được canh chừng kỹ nhất:
 *
 * 1. **Không có nhánh nào làm sập trang.** localStorage ném lỗi ở cửa sổ ẩn
 *    danh và khi người dùng chặn dữ liệu trang; một tuỳ chọn hiển thị không
 *    đáng để làm hỏng cả ứng dụng y tế.
 * 2. **Đoạn mã chống chớp trắng phải khớp với phần còn lại.** Nó là chuỗi thuần
 *    chạy trước cả React, nên không trình biên dịch nào bắt được nếu nó lệch
 *    khoá lưu trữ hay lệch tên class.
 */

afterEach(() => {
  document.documentElement.classList.remove(DARK_CLASS);
  document.documentElement.style.colorScheme = "";
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("resolveTheme", () => {
  it("giữ nguyên lựa chọn đã chốt, bất kể hệ điều hành đang để gì", () => {
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });

  it('"system" đi theo cài đặt hệ điều hành', () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
  });
});

describe("isThemePreference", () => {
  it.each(["light", "dark", "system"])("nhận %s", (value) => {
    expect(isThemePreference(value)).toBe(true);
  });

  it.each([null, undefined, "", "DARK", "auto", 1, {}])("từ chối %p", (value) => {
    expect(isThemePreference(value)).toBe(false);
  });
});

describe("readStoredPreference", () => {
  it('chưa chọn gì thì mặc định là "system", không tự ép một chế độ', () => {
    expect(readStoredPreference()).toBe("system");
  });

  it("đọc lại đúng lựa chọn đã lưu", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");
    expect(readStoredPreference()).toBe("dark");
  });

  it("giá trị rác trong localStorage không lọt ra ngoài", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "midnight");
    expect(readStoredPreference()).toBe("system");
  });

  it("localStorage ném lỗi thì vẫn trả về mặc định thay vì làm sập", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("bị chặn");
    });
    expect(readStoredPreference()).toBe("system");
  });
});

describe("setThemePreference", () => {
  it("không làm sập khi localStorage bị chặn ghi", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("bị chặn");
    });
    expect(() => setThemePreference("dark")).not.toThrow();
  });

  it("báo cho nơi đang theo dõi ngay trong cùng một tab", () => {
    const listener = vi.fn();
    const unsubscribe = subscribeToTheme(listener);

    setThemePreference("dark");

    expect(listener).toHaveBeenCalled();
    unsubscribe();
  });

  it("huỷ theo dõi rồi thì không nhận thông báo nữa", () => {
    const listener = vi.fn();
    subscribeToTheme(listener)();

    setThemePreference("light");

    expect(listener).not.toHaveBeenCalled();
  });
});

describe("applyTheme", () => {
  it("bật class mà Tailwind dò, và đặt color-scheme cho phần trình duyệt tự vẽ", () => {
    applyTheme("dark");

    expect(document.documentElement.classList.contains(DARK_CLASS)).toBe(true);
    // color-scheme là thứ quyết định màu thanh cuộn và con trỏ nhập liệu --
    // thiếu nó là chế độ tối làm nửa vời.
    expect(document.documentElement.style.colorScheme).toBe("dark");
  });

  it("tắt lại sạch khi quay về chế độ sáng", () => {
    applyTheme("dark");
    applyTheme("light");

    expect(document.documentElement.classList.contains(DARK_CLASS)).toBe(false);
    expect(document.documentElement.style.colorScheme).toBe("light");
  });
});

describe("themeBootstrapScript", () => {
  const script = themeBootstrapScript();

  it("mang đúng khoá lưu trữ và tên class của phần còn lại", () => {
    expect(script).toContain(JSON.stringify(THEME_STORAGE_KEY));
    expect(script).toContain(JSON.stringify(DARK_CLASS));
  });

  it("tự bọc lỗi, vì nó chạy trước mọi thứ khác", () => {
    expect(script).toContain("try");
    expect(script).toContain("catch");
  });

  it("chạy được thật và đặt đúng chế độ đã lưu", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");

    new Function(script)();

    expect(document.documentElement.classList.contains(DARK_CLASS)).toBe(true);
    expect(document.documentElement.style.colorScheme).toBe("dark");
  });

  it("không văng lỗi khi localStorage bị chặn", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("bị chặn");
    });

    expect(() => new Function(themeBootstrapScript())()).not.toThrow();
  });
});
