import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BACKDROP_PHOTOS } from "@/components/landing/backdrop-photos";
import { triageHistoryListHref, triageStartHref } from "@/lib/agent-mode";
import { useAuthStore } from "@/store/useAuthStore";

const reducedMotion = vi.hoisted(() => ({ value: false }));

vi.mock("framer-motion", async (importOriginal) => {
  const actual = await importOriginal<typeof import("framer-motion")>();
  return { ...actual, useReducedMotion: () => reducedMotion.value };
});

vi.mock("@/queries/useHealthTopics", () => ({
  useHealthTopics: () => ({ data: [], isLoading: false, isError: false }),
  useHealthTopicDetail: () => ({ data: undefined, isLoading: false, isError: false }),
}));

const { default: ClinicalLandingClient } = await import("@/components/landing/ClinicalLandingClient");

const PATIENT = { id: "u-1", name: "Nguyễn Văn Demo", email: "demo@example.com", role: "PATIENT" as const };

/** Mỗi mốc của phiên mẫu chỉ hẹn mốc kế tiếp sau khi React vẽ lại, nên phải tiến từng nhịp nhỏ. */
function advance(ms: number) {
  for (let elapsed = 0; elapsed < ms; elapsed += 100) {
    act(() => {
      vi.advanceTimersByTime(100);
    });
  }
}

function heroScale() {
  return screen.getByRole("list", { name: "Thang ESI 5 cấp" });
}

describe("trang chủ", () => {
  beforeEach(() => {
    reducedMotion.value = false;
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
  });

  afterEach(() => {
    vi.useRealTimers();
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
  });

  it("đặt câu hỏi của người bệnh làm tiêu đề và đưa khách qua đăng nhập trước khi sàng lọc", () => {
    render(<ClinicalLandingClient />);

    expect(screen.getByRole("heading", { level: 1, name: "Bạn cần khám gấp đến mức nào?" })).toBeInTheDocument();
    const hero = screen.getByRole("heading", { level: 1 }).closest("section") as HTMLElement;
    expect(within(hero).getByRole("link", { name: /Bắt đầu sàng lọc/ })).toHaveAttribute("href", "/auth/login");
    expect(within(hero).getByRole("link", { name: "Xem cách hoạt động" })).toHaveAttribute("href", "#an-toan-lam-sang");
  });

  it("người bệnh đã đăng nhập đi thẳng vào màn sàng lọc đang bật", () => {
    useAuthStore.setState({ user: PATIENT, isAuthenticated: true, isLoading: false });
    render(<ClinicalLandingClient />);

    const links = screen.getAllByRole("link", { name: /Bắt đầu sàng lọc/ });
    expect(links).toHaveLength(2);
    links.forEach((link) => expect(link).toHaveAttribute("href", triageStartHref()));
    expect(screen.queryByRole("link", { name: "Tạo tài khoản" })).not.toBeInTheDocument();
  });

  it("giữ đủ ba mỏ neo mà thanh điều hướng trỏ tới", () => {
    const { container } = render(<ClinicalLandingClient />);

    for (const id of ["an-toan-lam-sang", "trai-nghiem-triage", "thong-tin-suc-khoe"]) {
      expect(container.querySelector(`section#${id}`), id).not.toBeNull();
    }
  });

  it("ghi rõ phiên mẫu là minh họa", () => {
    render(<ClinicalLandingClient />);

    expect(screen.getByRole("img", { name: /^Ví dụ minh họa một phiên sàng lọc/ })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /^Ví dụ minh họa: kết quả ESI 3/ })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /không đoán/ })).toBeInTheDocument();
  });

  it("phiên mẫu chạy tới kết quả thì thang ESI sáng đúng mức 3, rồi lặp lại từ đầu", () => {
    vi.useFakeTimers();
    render(<ClinicalLandingClient />);

    expect(within(heroScale()).queryByRole("listitem", { current: "step" })).toBeNull();

    advance(9_200);
    expect(within(heroScale()).getByRole("listitem", { current: "step" })).toHaveTextContent("3");
    expect(screen.getByText("Mức đề xuất của AI, chờ điều dưỡng xem lại")).toBeInTheDocument();

    advance(2_000);
    expect(screen.getByText("Điều dưỡng đã xác nhận mức này")).toBeInTheDocument();

    advance(3_000);
    expect(within(heroScale()).queryByRole("listitem", { current: "step" })).toBeNull();
    expect(screen.queryByText("Điều dưỡng đã xác nhận mức này")).not.toBeInTheDocument();
  });

  it("người đã tắt hiệu ứng chuyển động thấy ngay khung cuối, không có gì lặp", () => {
    reducedMotion.value = true;
    vi.useFakeTimers();
    render(<ClinicalLandingClient />);

    expect(screen.getByText("Điều dưỡng đã xác nhận mức này")).toBeInTheDocument();
    expect(within(heroScale()).getByRole("listitem", { current: "step" })).toHaveTextContent("3");
    // Màn điện thoại trong khối "hai màn hình" cũng đã đổi sang xác nhận.
    expect(screen.getAllByText("Điều dưỡng đã xác nhận").length).toBeGreaterThan(0);

    advance(20_000);
    expect(screen.getByText("Điều dưỡng đã xác nhận mức này")).toBeInTheDocument();
    // Không có gì chạy thì không cần nút dừng.
    expect(screen.queryAllByRole("button", { name: /^Dừng / })).toHaveLength(0);
  });

  it("nền động của cả ba khối chỉ là phông nền: trình đọc màn hình bỏ qua, ảnh không có alt", () => {
    const { container } = render(<ClinicalLandingClient />);

    const backdrops = [...container.querySelectorAll<HTMLElement>("[data-landing-backdrop]")];
    expect(backdrops.map((backdrop) => backdrop.dataset.landingBackdrop)).toEqual(["hero", "evidence", "care"]);
    // Chỉ bức tường đầu trang dùng ảnh; hai nền bên dưới vẽ bằng nét.
    expect(backdrops[0].querySelectorAll("img").length).toBeGreaterThan(0);
    for (const backdrop of backdrops) {
      expect(backdrop).toHaveAttribute("aria-hidden", "true");
      backdrop.querySelectorAll("img").forEach((image) => expect(image).toHaveAttribute("alt", ""));
    }
  });

  it("một nút dừng cả phiên mẫu lẫn bức tường ảnh, bấm lại thì chạy tiếp", () => {
    vi.useFakeTimers();
    const { container } = render(<ClinicalLandingClient />);
    const wall = container.querySelector('[data-landing-backdrop="hero"]') as HTMLElement;

    const pause = screen.getByRole("button", { name: "Dừng hình động đầu trang" });
    expect(pause).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(pause);
    expect(screen.getByRole("button", { name: "Cho hình động đầu trang chạy tiếp" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(wall).toHaveAttribute("data-paused");

    advance(12_000);
    expect(within(heroScale()).queryByRole("listitem", { current: "step" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Cho hình động đầu trang chạy tiếp" }));
    expect(wall).not.toHaveAttribute("data-paused");
    advance(9_200);
    expect(within(heroScale()).getByRole("listitem", { current: "step" })).toHaveTextContent("3");
  });

  it("mỗi khối có nút dừng riêng, chỉ dừng ví dụ và nền của chính khối đó", () => {
    vi.useFakeTimers();
    const { container } = render(<ClinicalLandingClient />);
    const care = container.querySelector('[data-landing-backdrop="care"]') as HTMLElement;
    const evidence = container.querySelector('[data-landing-backdrop="evidence"]') as HTMLElement;

    fireEvent.click(screen.getByRole("button", { name: "Dừng ví dụ hai màn hình" }));
    expect(care).toHaveAttribute("data-paused");
    expect(evidence).not.toHaveAttribute("data-paused");

    // Đứng yên ở khung đầu: ca chưa tới hàng đợi nên điều dưỡng chưa xác nhận gì.
    advance(12_000);
    expect(screen.queryAllByText("Đã xác nhận ESI 3")).toHaveLength(0);

    fireEvent.click(screen.getByRole("button", { name: "Cho ví dụ hai màn hình chạy tiếp" }));
    advance(7_200);
    expect(screen.getAllByText("Đã xác nhận ESI 3").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Dừng sơ đồ đối chiếu" }));
    expect(evidence).toHaveAttribute("data-paused");
  });

  it("mỗi ảnh nền đều được ghi công ở chân trang", () => {
    const { container } = render(<ClinicalLandingClient />);

    // next/image đổi src thành /_next/image?url=...; đường dẫn gốc nằm trong tham số url.
    const shown = new Set(
      [...container.querySelectorAll("[data-landing-backdrop] img")].map((image) => {
        const src = image.getAttribute("src") ?? "";
        return new URL(src, "http://localhost").searchParams.get("url") ?? src;
      }),
    );
    const credited = Object.values(BACKDROP_PHOTOS).map((photo) => photo.src);
    expect([...shown].sort()).toEqual([...credited].sort());

    const credits = screen.getByText("Ảnh nền: Wikimedia Commons").closest("details") as HTMLElement;
    expect(within(credits).getAllByRole("listitem")).toHaveLength(credited.length);
    expect(within(credits).getByRole("link", { name: "Windrain" })).toHaveAttribute(
      "href",
      "https://commons.wikimedia.org/wiki/File:Bệnh_viện_tỉnh_Ninh_Thuận.jpg",
    );
  });

  it("chỉ nhắc 115 bằng chữ: trang chủ không có nút gọi", () => {
    const { container } = render(<ClinicalLandingClient />);

    expect(screen.getByText("Trường hợp nguy kịch, gọi ngay 115.")).toBeInTheDocument();
    expect(container.querySelector('a[href^="tel:"]')).toBeNull();
  });

  it("các lối tắt cuối trang trỏ đúng chức năng, khách thì đi qua đăng nhập", () => {
    const { unmount } = render(<ClinicalLandingClient />);
    for (const name of ["Hồ sơ sức khỏe", "Lịch sử sàng lọc", "Khám giúp người thân"]) {
      expect(screen.getByRole("link", { name })).toHaveAttribute("href", "/auth/login");
    }
    expect(screen.getByRole("link", { name: "Tạo tài khoản" })).toHaveAttribute("href", "/auth/register");
    unmount();

    useAuthStore.setState({ user: PATIENT, isAuthenticated: true, isLoading: false });
    render(<ClinicalLandingClient />);
    expect(screen.getByRole("link", { name: "Hồ sơ sức khỏe" })).toHaveAttribute("href", "/profile/ehr");
    expect(screen.getByRole("link", { name: "Lịch sử sàng lọc" })).toHaveAttribute("href", triageHistoryListHref());
    expect(screen.getByRole("link", { name: "Khám giúp người thân" })).toHaveAttribute("href", "/profile");
  });
});
