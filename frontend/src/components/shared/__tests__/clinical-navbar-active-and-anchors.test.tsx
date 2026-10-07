import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ClinicalNavbar } from "@/components/shared/ClinicalNavbar";
import { useAuthStore, type UserProfile } from "@/store/useAuthStore";

/**
 * Hai lỗi điều hướng có thật đã được sửa, giữ lại test để không tái phát:
 *
 * 1. Đứng ở "/triage-pilot/history" thì CẢ "Khám Triage AI" lẫn "Lịch Sử Khám"
 *    cùng sáng, vì mỗi mục tự kiểm tra `startsWith` một cách độc lập và
 *    "/triage-pilot/history" đương nhiên bắt đầu bằng "/triage-pilot".
 *
 * 2. Bấm các mỏ neo trang chủ không cuộn đi đâu: nội dung trang chủ chỉ được
 *    dựng sau khi phiên hydrate xong (xem RoleHomeRedirect), nên tại thời điểm
 *    điều hướng phần tử đích chưa tồn tại trong DOM.
 */

let mockPathname = "/";
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

// Ép chế độ pilot: chỉ khi đó hai mục điều hướng mới lồng tiền tố vào nhau
// ("/triage-pilot" và "/triage-pilot/history") và bộc lộ được lỗi số 1.
vi.mock("@/lib/agent-mode", () => ({
  IS_PILOT_AGENT_ACTIVE: true,
  triageStartHref: () => "/triage-pilot",
  triageHistoryListHref: () => "/triage-pilot/history",
  nurseQueueHref: () => "/clinical/queue-pilot",
}));

const patient: UserProfile = {
  id: "user-1",
  name: "Người Bệnh",
  email: "patient@example.com",
  role: "PATIENT",
};

function renderNavbar() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ClinicalNavbar />
    </QueryClientProvider>,
  );
}

/** Mục điều hướng đang được chọn được đánh dấu bằng aria-current="page". */
function activeNavNames(): string[] {
  return screen
    .getAllByRole("link")
    .filter((link) => link.getAttribute("aria-current") === "page")
    .map((link) => link.textContent?.trim() ?? "");
}

afterEach(() => {
  mockPathname = "/";
  useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
});

describe("tô sáng mục điều hướng theo đường dẫn sâu nhất", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: patient, isAuthenticated: true, isLoading: false });
  });

  it('ở trang lịch sử chỉ sáng "Lịch Sử Khám", không sáng lây "Khám Triage AI"', () => {
    mockPathname = "/triage-pilot/history";
    renderNavbar();

    const active = activeNavNames();
    expect(active).toContain("Lịch Sử Khám");
    expect(active).not.toContain("Khám Triage AI");
  });

  it('ở trang khám thì sáng đúng "Khám Triage AI"', () => {
    mockPathname = "/triage-pilot";
    renderNavbar();

    const active = activeNavNames();
    expect(active).toContain("Khám Triage AI");
    expect(active).not.toContain("Lịch Sử Khám");
  });

  it("trang con của hồ sơ vẫn giữ mục Hồ Sơ Y Khoa đang sáng", () => {
    mockPathname = "/profile/ehr";
    renderNavbar();

    expect(activeNavNames()).toContain("Hồ Sơ Y Khoa");
  });

  it("không có mục nào sáng nhầm khi đứng ở một tuyến không thuộc menu", () => {
    mockPathname = "/khong-ton-tai";
    renderNavbar();

    expect(activeNavNames()).toHaveLength(0);
  });
});

describe("cuộn tới khối nội dung khi trang chủ mang mỏ neo", () => {
  it("vẫn cuộn đúng dù khối nội dung chỉ xuất hiện sau khi hydrate", async () => {
    mockPathname = "/";
    window.location.hash = "#an-toan-lam-sang";

    const scrollIntoView = vi.fn();
    renderNavbar();

    // Khối đích CHƯA có mặt lúc navbar mount -- đúng tình huống thật trên trang
    // chủ. Chỉ gắn vào DOM sau một nhịp, để kiểm tra vòng thử lại theo khung hình.
    await new Promise((resolve) => setTimeout(resolve, 30));
    const section = document.createElement("section");
    section.id = "an-toan-lam-sang";
    section.scrollIntoView = scrollIntoView;
    document.body.appendChild(section);

    await waitFor(() => expect(scrollIntoView).toHaveBeenCalled());
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" });

    section.remove();
    window.location.hash = "";
  });

  it("không cuộn khi đường dẫn không mang mỏ neo nào", async () => {
    mockPathname = "/";
    window.location.hash = "";

    const scrollIntoView = vi.fn();
    const section = document.createElement("section");
    section.id = "an-toan-lam-sang";
    section.scrollIntoView = scrollIntoView;
    document.body.appendChild(section);

    renderNavbar();
    await new Promise((resolve) => setTimeout(resolve, 60));

    expect(scrollIntoView).not.toHaveBeenCalled();
    section.remove();
  });
});

/**
 * Lỗi số 3 (2026-09-14): đứng ở đầu trang chủ nhưng "An Toàn Y Khoa" vẫn sáng.
 *
 * Scroll-spy cũ dựng trên IntersectionObserver, mà callback của observer chỉ
 * chạy khi có khối ĐỔI trạng thái cắt nhau. Cuộn ngược từ một khối lên đỉnh
 * trang thì khối đó rời vùng quan sát lúc scrollY còn lớn, sau đó không còn sự
 * kiện nào nữa, nên mục điều hướng cũ nằm sáng vĩnh viễn.
 */
describe("scroll-spy trên trang chủ", () => {
  const ANCHOR_IDS = ["an-toan-lam-sang", "trai-nghiem-triage", "thong-tin-suc-khoe"];

  /** Dựng các khối mỏ neo với vị trí giả lập; jsdom không tự tính bố cục. */
  function placeAnchors(tops: Record<string, number>) {
    return ANCHOR_IDS.map((id) => {
      const section = document.createElement("section");
      section.id = id;
      section.getBoundingClientRect = () =>
        ({ top: tops[id], bottom: tops[id] + 600, height: 600 }) as DOMRect;
      document.body.appendChild(section);
      return section;
    });
  }

  /** Đẩy khối lên phía trên đường ngắm rồi báo cho navbar biết trang vừa cuộn. */
  function moveTo(id: string, top: number) {
    const section = document.getElementById(id) as HTMLElement;
    section.getBoundingClientRect = () => ({ top, bottom: top + 600, height: 600 }) as DOMRect;
    window.dispatchEvent(new Event("scroll"));
  }

  afterEach(() => {
    ANCHOR_IDS.forEach((id) => document.getElementById(id)?.remove());
  });

  it("cuộn ngược lên đỉnh trang thì trả lại Trang Chủ, không kẹt ở mục vừa rời", async () => {
    mockPathname = "/";
    // Mọi khối đều nằm dưới đường ngắm: người đọc đang ở Hero.
    placeAnchors({
      "an-toan-lam-sang": 2000,
      "trai-nghiem-triage": 2600,
      "thong-tin-suc-khoe": 3200,
    });
    renderNavbar();

    await waitFor(() => expect(activeNavNames()).toContain("Trang Chủ"));

    // Cuộn xuống khối An Toàn Y Khoa.
    moveTo("an-toan-lam-sang", -100);
    await waitFor(() => expect(activeNavNames()).toContain("An Toàn Y Khoa"));
    expect(activeNavNames()).not.toContain("Trang Chủ");

    // Cuộn ngược lên đỉnh. Đây chính là bước mà bản cũ nằm kẹt.
    moveTo("an-toan-lam-sang", 2000);
    await waitFor(() => expect(activeNavNames()).toContain("Trang Chủ"));
    expect(activeNavNames()).not.toContain("An Toàn Y Khoa");
  });

  it("xuống tới chân trang thì vẫn giữ mục cuối cùng đang sáng", async () => {
    mockPathname = "/";
    // Cả ba khối đã trôi lên trên đường ngắm: người đọc đang ở khối cuối trở đi.
    placeAnchors({
      "an-toan-lam-sang": -3000,
      "trai-nghiem-triage": -2000,
      "thong-tin-suc-khoe": -1000,
    });
    renderNavbar();

    await waitFor(() => expect(activeNavNames()).toContain("Kiến Thức Sức Khỏe"));
    expect(activeNavNames()).not.toContain("Trang Chủ");
  });
});
