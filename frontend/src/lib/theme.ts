/**
 * Lớp lõi của chế độ sáng/tối. Thuần TypeScript, không phụ thuộc React, nên
 * kiểm thử được mà không cần dựng cây component.
 *
 * Tailwind trong dự án này đã cấu hình sẵn biến thể tối theo **class**:
 *
 *     @custom-variant dark (&:is(.dark *));   // frontend/src/app/globals.css
 *
 * Nghĩa là mọi class `dark:` chỉ có hiệu lực khi một phần tử tổ tiên mang class
 * `.dark`. Bộ token "Clinical Night Mode" cũng đã nằm sẵn trong `globals.css`.
 * Thứ duy nhất còn thiếu từ trước tới nay là một chỗ thực sự gắn class đó vào
 * thẻ `<html>` -- toàn bộ phần dark mode đã viết nằm đó nhưng chưa bao giờ bật
 * lên được.
 */

/** Lựa chọn của người dùng. "system" nghĩa là đi theo cài đặt hệ điều hành. */
export type ThemePreference = "light" | "dark" | "system";

/** Chế độ thực sự đang hiển thị, sau khi đã giải nghĩa "system". */
export type ResolvedTheme = "light" | "dark";

/** Khoá localStorage. Có tiền tố dự án để không đụng khoá của ứng dụng khác trên cùng origin. */
export const THEME_STORAGE_KEY = "ai20k_theme";

export const SYSTEM_DARK_QUERY = "(prefers-color-scheme: dark)";

/** Class mà Tailwind dò để bật biến thể `dark:`. */
export const DARK_CLASS = "dark";

export function isThemePreference(value: unknown): value is ThemePreference {
  return value === "light" || value === "dark" || value === "system";
}

/** Giải nghĩa lựa chọn thành chế độ hiển thị thật. */
export function resolveTheme(
  preference: ThemePreference,
  systemPrefersDark: boolean,
): ResolvedTheme {
  if (preference === "system") return systemPrefersDark ? "dark" : "light";
  return preference;
}

/** Hệ điều hành đang để chế độ tối hay không. An toàn khi chạy phía máy chủ. */
export function systemPrefersDark(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia(SYSTEM_DARK_QUERY).matches;
}

/**
 * Đọc lựa chọn đã lưu. Mặc định là "system": lần đầu vào, ứng dụng tôn trọng
 * cài đặt của máy thay vì tự ép một chế độ.
 *
 * localStorage có thể ném lỗi ở cửa sổ ẩn danh hoặc khi người dùng chặn dữ liệu
 * trang, nên mọi lần đọc đều được bọc lại; hỏng thì rơi về "system" chứ không
 * làm sập trang.
 */
export function readStoredPreference(): ThemePreference {
  if (typeof window === "undefined") return "system";
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isThemePreference(stored) ? stored : "system";
  } catch {
    return "system";
  }
}

function storePreference(preference: ThemePreference): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    // Không lưu được thì chế độ chỉ sống trong phiên này. Đó là một bất tiện
    // nhỏ, không phải lý do để hỏng giao diện.
  }
}

// ---------------------------------------------------------------------------
// Kho trạng thái ngoài React
// ---------------------------------------------------------------------------
// Chế độ hiển thị vốn không sống trong React: nó nằm ở localStorage và ở cài
// đặt hệ điều hành. Gói lại thành một kho có thể đăng ký theo dõi để React đọc
// bằng `useSyncExternalStore`, thay vì sao chép vào state rồi phải đồng bộ
// ngược bằng effect.
const listeners = new Set<() => void>();

function notify(): void {
  for (const listener of listeners) listener();
}

/**
 * Theo dõi mọi nguồn có thể làm chế độ đổi:
 *
 * - `setThemePreference` gọi trong chính tab này,
 * - sự kiện `storage` khi người dùng đổi chế độ ở **tab khác**,
 * - hệ điều hành chuyển sáng/tối khi đang để "theo hệ thống".
 */
export function subscribeToTheme(onChange: () => void): () => void {
  listeners.add(onChange);

  const handleStorage = (event: StorageEvent) => {
    if (event.key === null || event.key === THEME_STORAGE_KEY) onChange();
  };
  const media =
    typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia(SYSTEM_DARK_QUERY)
      : null;

  if (typeof window !== "undefined") window.addEventListener("storage", handleStorage);
  media?.addEventListener("change", onChange);

  return () => {
    listeners.delete(onChange);
    if (typeof window !== "undefined") window.removeEventListener("storage", handleStorage);
    media?.removeEventListener("change", onChange);
  };
}

/** Ghi lựa chọn mới và báo cho mọi nơi đang theo dõi. */
export function setThemePreference(preference: ThemePreference): void {
  storePreference(preference);
  notify();
}

/**
 * Gắn chế độ vào tài liệu.
 *
 * Ngoài class `.dark` cho Tailwind, hàm này còn đặt thuộc tính CSS
 * ``color-scheme``. Đó là thứ quyết định màu của những phần **trình duyệt tự
 * vẽ** mà không stylesheet nào với tới: thanh cuộn, con trỏ nhập liệu, ô
 * checkbox, hộp chọn ngày. Thiếu nó thì trang tối vẫn dính thanh cuộn trắng và
 * caret đen — dấu hiệu rõ nhất của một chế độ tối làm nửa vời.
 */
export function applyTheme(resolved: ResolvedTheme): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle(DARK_CLASS, resolved === "dark");
  root.style.colorScheme = resolved;
}

/**
 * Đoạn mã chạy trước khi trang vẽ khung hình đầu tiên.
 *
 * Không có nó, trang luôn vẽ ở chế độ sáng rồi mới nhảy sang tối khi React
 * hydrate xong — một cú chớp trắng vào mặt người dùng đang ở chế độ tối. Đoạn
 * này phải là chuỗi thuần, không phụ thuộc bundle, và được sinh từ **chính** các
 * hằng số ở trên để hai nơi không bao giờ lệch nhau.
 */
export function themeBootstrapScript(): string {
  return `(function(){try{var k=${JSON.stringify(THEME_STORAGE_KEY)};var p=localStorage.getItem(k);if(p!=="light"&&p!=="dark"&&p!=="system"){p="system"}var d=p==="dark"||(p==="system"&&window.matchMedia(${JSON.stringify(SYSTEM_DARK_QUERY)}).matches);var r=document.documentElement;r.classList.toggle(${JSON.stringify(DARK_CLASS)},d);r.style.colorScheme=d?"dark":"light"}catch(e){}})();`;
}
