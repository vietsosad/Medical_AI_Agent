import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DisclaimerConsentModal } from "@/components/chat/DisclaimerConsentModal";
import { SimpleEsiResultCard } from "@/components/chat/SimpleEsiResultCard";
import { SimpleTurnErrorCard } from "@/components/chat/SimpleTurnErrorCard";
import { useTriageStore } from "@/store/useTriageStore";

/**
 * Lối gọi 115 là lối thoát không được phép mất: ở kết quả ESI 1/2 và ở mọi
 * màn lỗi phía người bệnh. Ở chiều ngược lại, kết quả không khẩn không được
 * mang còi báo động, và giao diện không được hứa điều hệ thống không làm.
 */

function callLinks(): HTMLElement[] {
  return screen.queryAllByRole("link").filter((link) => link.getAttribute("href") === "tel:115");
}

describe("thẻ kết quả ESI", () => {
  it.each([1, 2] as const)("ESI %i được thông báo ngay và có nút gọi 115", (level) => {
    render(<SimpleEsiResultCard esiLevel={level} />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(callLinks()).toHaveLength(1);
  });

  it.each([3, 4, 5] as const)("ESI %i không bật cảnh báo và không đẩy người bệnh gọi 115", (level) => {
    render(<SimpleEsiResultCard esiLevel={level} />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(callLinks()).toHaveLength(0);
  });
});

describe("thẻ lỗi lượt hội thoại", () => {
  it("giữ lối gọi 115 cạnh nút gửi lại", () => {
    const onRetry = vi.fn();
    render(<SimpleTurnErrorCard message="Không kết nối được tới hệ thống." onRetry={onRetry} />);

    expect(screen.getByRole("button", { name: /Gửi lại/ })).toBeInTheDocument();
    expect(callLinks()).toHaveLength(1);
  });
});

describe("cam kết trước phiên sàng lọc", () => {
  it("nói đúng rằng hệ thống không tự gọi 115 và không nhắc công nghệ không còn dùng", () => {
    useTriageStore.setState({ hasConsented: false });
    render(<DisclaimerConsentModal />);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("không tự gọi 115");
    expect(dialog).not.toHaveTextContent(/kích hoạt lệnh/i);
    expect(dialog).not.toHaveTextContent(/Hybrid RAG|DeepAgent/);
  });
});
