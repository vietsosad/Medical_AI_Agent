import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HEALTH_TOPIC_PHOTOS } from "@/components/landing/health-topic-photos";
import type { HealthTopicSummaryDTO } from "@/services/health.service";
import { useAuthStore } from "@/store/useAuthStore";

const useHealthTopicsMock = vi.hoisted(() => vi.fn());

vi.mock("@/queries/useHealthTopics", () => ({
  useHealthTopics: useHealthTopicsMock,
  useHealthTopicDetail: () => ({ data: undefined, isLoading: false, isError: false }),
}));

const { HealthTopicsSection, triageHrefForTopic } = await import("@/components/landing/HealthTopicsSection");

const dengue: HealthTopicSummaryDTO = {
  slug: "sot-xuat-huyet-dengue",
  name: "Sốt xuất huyết Dengue",
  summary: "Bệnh do virus Dengue lây qua muỗi vằn.",
  symptoms: ["Sốt cao đột ngột", "Đau đầu dữ dội", "Đau cơ và đau khớp", "Phát ban"],
  prevention: ["Ngủ màn kể cả ban ngày", "Diệt lăng quăng quanh nhà"],
  source: "WHO",
  source_url: "https://www.who.int/",
  last_updated: "2026-08-22T00:00:00",
  ai_assisted: true,
};

const flu: HealthTopicSummaryDTO = {
  ...dengue,
  slug: "cum-mua",
  name: "Cúm mùa",
  summary: "Nhiễm trùng đường hô hấp do virus cúm.",
  symptoms: ["Sốt và ớn lạnh", "Ho khan", "Đau họng"],
  prevention: ["Tiêm vắc xin cúm hằng năm"],
  ai_assisted: false,
};

/** Chủ đề backend có nhưng chưa được chọn ảnh. */
const unknownTopic: HealthTopicSummaryDTO = {
  ...flu,
  slug: "chu-de-moi",
  name: "Chủ đề mới",
  ai_assisted: false,
};

function renderSection(topics: HealthTopicSummaryDTO[]) {
  useHealthTopicsMock.mockReturnValue({ data: topics, isLoading: false, isError: false });
  return render(<HealthTopicsSection />);
}

function card(name: string): HTMLElement {
  return screen.getByRole("heading", { name }).closest("article") as HTMLElement;
}

describe("dòng chủ đề sức khỏe", () => {
  afterEach(() => {
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
    useHealthTopicsMock.mockReset();
    vi.restoreAllMocks();
  });

  it("đặt mỗi chủ đề vào một thẻ ảnh mang đúng mô tả ảnh của chủ đề đó", () => {
    renderSection([dengue, flu]);

    const stream = screen.getByTestId("health-topic-stream");
    expect(within(stream).getAllByRole("article")).toHaveLength(2);
    expect(within(card("Sốt xuất huyết Dengue")).getByRole("img")).toHaveAttribute(
      "alt",
      HEALTH_TOPIC_PHOTOS["sot-xuat-huyet-dengue"].alt,
    );
    expect(within(card("Cúm mùa")).getByRole("img")).toHaveAttribute("alt", HEALTH_TOPIC_PHOTOS["cum-mua"].alt);
  });

  it("có ảnh và ghi công cho toàn bộ 16 chủ đề đang có, không ảnh nào thiếu giấy phép", () => {
    const slugs = [
      "sot-xuat-huyet-dengue", "cum-mua", "tay-chan-mieng", "tang-huyet-ap", "dai-thao-duong-type-2",
      "sot-ret", "lao-phoi", "viem-gan-b", "dot-quy", "hen-phe-quan", "benh-phoi-tac-nghen-man-tinh",
      "tieu-chay-cap", "soi", "benh-dai", "ngo-doc-thuc-pham", "tram-cam",
    ];

    for (const slug of slugs) {
      const photo = HEALTH_TOPIC_PHOTOS[slug];
      expect(photo, slug).toBeDefined();
      expect(photo.src).toBe(`/health-topics/${slug}.webp`);
      expect(photo.alt.length, slug).toBeGreaterThan(10);
      expect(photo.credit.author, slug).not.toBe("");
      expect(photo.credit.license, slug).toMatch(/^(Public domain|CC0|CC BY(-SA)? \d\.\d)$/);
      expect(photo.credit.sourceUrl, slug).toMatch(/^https:\/\/commons\.wikimedia\.org\/wiki\/File:/);
    }
  });

  it("vẫn hiển thị chủ đề chưa có ảnh bằng biểu tượng thay thế", () => {
    renderSection([dengue, flu, unknownTopic]);

    const fallback = card("Chủ đề mới");
    expect(within(fallback).queryByRole("img")).not.toBeInTheDocument();
    expect(within(fallback).getByText(unknownTopic.summary)).toBeInTheDocument();
  });

  it("mở hướng dẫn đầy đủ khi bấm vào tên chủ đề", async () => {
    const user = userEvent.setup();
    renderSection([dengue, flu]);

    await user.click(screen.getByRole("button", { name: "Cúm mùa" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("giữ nguyên đích triage của từng chủ đề", () => {
    renderSection([dengue]);

    expect(within(card("Sốt xuất huyết Dengue")).getByRole("link", { name: /Kiểm tra triệu chứng/ })).toHaveAttribute(
      "href",
      "/auth/login",
    );
    expect(triageHrefForTopic("sot-xuat-huyet-dengue", true)).toBe("/triage?health_topic=sot-xuat-huyet-dengue");
  });

  it("chỉ gắn nhãn AI lên chủ đề mà dữ liệu xác nhận", () => {
    renderSection([dengue, flu]);

    expect(within(card("Sốt xuất huyết Dengue")).getByText("AI diễn giải")).toBeInTheDocument();
    expect(within(card("Cúm mùa")).queryByText("AI diễn giải")).not.toBeInTheDocument();
  });

  it("dòng chậm lại rồi dừng dưới con trỏ chuột và chạy tiếp khi con trỏ rời đi", () => {
    renderSection([dengue, flu]);
    const stream = screen.getByTestId("health-topic-stream");
    expect(stream).toHaveAttribute("data-flow-state", "running");

    fireEvent.pointerEnter(stream, { pointerType: "mouse" });
    expect(stream).toHaveAttribute("data-flow-state", "paused");

    fireEvent.pointerLeave(stream, { pointerType: "mouse" });
    expect(stream).toHaveAttribute("data-flow-state", "running");
  });

  it("ngón tay chạm vào không làm dòng dừng: chạm là để kéo, không phải để rê", () => {
    renderSection([dengue, flu]);
    const stream = screen.getByTestId("health-topic-stream");

    fireEvent.pointerEnter(stream, { pointerType: "touch" });

    expect(stream).toHaveAttribute("data-flow-state", "running");
  });

  it("dừng khi bàn phím đi vào một thẻ để người dùng đọc kịp", async () => {
    const user = userEvent.setup();
    renderSection([dengue, flu]);
    const stream = screen.getByTestId("health-topic-stream");

    // Nút trước / dừng / sau đứng trước dòng trong thứ tự tab: người dùng bàn phím
    // gặp nút dừng trước khi gặp nội dung đang chuyển động.
    await user.tab();
    expect(screen.getByRole("button", { name: "Xem chủ đề trước" })).toHaveFocus();
    await user.tab();
    await user.tab();
    expect(stream).toHaveAttribute("data-flow-state", "running");

    await user.tab();
    expect(screen.getByRole("button", { name: "Sốt xuất huyết Dengue" })).toHaveFocus();
    expect(stream).toHaveAttribute("data-flow-state", "paused");
  });

  it("có nút dừng với trạng thái trợ năng rõ ràng", async () => {
    const user = userEvent.setup();
    renderSection([dengue, flu]);
    const stream = screen.getByTestId("health-topic-stream");

    const pause = screen.getByRole("button", { name: "Dừng dòng chủ đề" });
    expect(pause).toHaveAttribute("aria-pressed", "false");
    await user.click(pause);

    expect(screen.getByRole("button", { name: "Cho dòng chủ đề trôi tiếp" })).toHaveAttribute("aria-pressed", "true");
    expect(stream).toHaveAttribute("data-flow-state", "paused");
  });

  it("nút trước và sau đưa dòng đi đúng hướng khi dòng đứng yên", async () => {
    const user = userEvent.setup();
    const scrollBy = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "scrollBy", { value: scrollBy, configurable: true, writable: true });
    renderSection([dengue, flu]);

    await user.click(screen.getByRole("button", { name: "Xem chủ đề tiếp theo" }));
    await user.click(screen.getByRole("button", { name: "Xem chủ đề trước" }));

    expect(scrollBy.mock.calls[0][0].left).toBeGreaterThan(0);
    expect(scrollBy.mock.calls[1][0].left).toBeLessThan(0);
  });

  it("ghi công từng ảnh với tác giả và giấy phép", () => {
    renderSection([dengue, flu]);

    const credits = screen.getByText("Nguồn ảnh: Wikimedia Commons").closest("details") as HTMLElement;
    expect(within(credits).getByRole("link", { name: "James Gathany, CDC" })).toHaveAttribute(
      "href",
      HEALTH_TOPIC_PHOTOS["sot-xuat-huyet-dengue"].credit.sourceUrl,
    );
    expect(within(credits).getByRole("link", { name: "CC BY 2.0" })).toHaveAttribute(
      "href",
      "https://creativecommons.org/licenses/by/2.0",
    );
  });
});
