import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/store/useAuthStore";
import type { HealthTopicSummaryDTO } from "@/services/health.service";
import { HealthTopicArtwork } from "@/components/landing/HealthTopicArtwork";

const useHealthTopicsMock = vi.hoisted(() => vi.fn());

vi.mock("@/queries/useHealthTopics", () => ({
  useHealthTopics: useHealthTopicsMock,
  useHealthTopicDetail: () => ({ data: undefined, isLoading: false, isError: false }),
}));

const { HealthTopicsSection } = await import("@/components/landing/HealthTopicsSection");

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

describe("spotlight chủ đề sức khỏe", () => {
  afterEach(() => {
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
    useHealthTopicsMock.mockReset();
  });

  const renderSection = (topics: HealthTopicSummaryDTO[]) => {
    useHealthTopicsMock.mockReturnValue({ data: topics, isLoading: false, isError: false });
    return render(<HealthTopicsSection />);
  };

  it("chỉ đặt một chủ đề làm tiêu điểm và cung cấp bộ chọn rõ ràng", () => {
    renderSection([dengue, flu]);

    const stage = screen.getByTestId("active-health-topic");
    expect(within(stage).getByRole("heading", { name: "Sốt xuất huyết Dengue" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sốt xuất huyết Dengue" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Cúm mùa" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(
      within(screen.getByTestId("health-topic-stream")).getAllByRole("button"),
    ).toHaveLength(2);
  });

  it("chuyển chủ đề bằng bộ chọn và thay đúng minh họa", async () => {
    const user = userEvent.setup();
    renderSection([dengue, flu]);

    expect(
      screen
        .getByRole("button", { name: "Phóng to minh họa Sốt xuất huyết Dengue" })
        .querySelector("[data-artwork-kind]"),
    ).toHaveAttribute(
      "data-artwork-kind",
      "dengue",
    );

    await user.click(screen.getByRole("button", { name: "Cúm mùa" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Cúm mùa" })).toHaveAttribute("aria-pressed", "true");
    });
    await waitFor(() => {
      expect(
        screen
          .getByRole("button", { name: "Phóng to minh họa Cúm mùa" })
          .querySelector("[data-artwork-kind]"),
      ).toHaveAttribute(
        "data-artwork-kind",
        "flu",
      );
    });
  });

  it("vận hành rail như một dòng chảy và tạm dừng khi người dùng chạm vào", () => {
    renderSection([dengue, flu]);

    const rail = screen.getByTestId("health-topic-stream");
    expect(rail).toHaveAttribute("data-flow-state", "running");

    fireEvent.pointerDown(rail);
    expect(rail).toHaveAttribute("data-flow-state", "paused");

    fireEvent.pointerUp(rail);
    expect(rail).toHaveAttribute("data-flow-state", "running");
  });

  it("có minh họa riêng cho toàn bộ chủ đề sức khỏe hiện có", () => {
    const topics = [
      "sot-xuat-huyet-dengue",
      "cum-mua",
      "tay-chan-mieng",
      "tang-huyet-ap",
      "dai-thao-duong-type-2",
      "sot-ret",
      "lao-phoi",
      "viem-gan-b",
      "dot-quy",
      "hen-phe-quan",
      "benh-phoi-tac-nghen-man-tinh",
      "tieu-chay-cap",
      "soi",
      "benh-dai",
      "ngo-doc-thuc-pham",
      "tram-cam",
    ];
    const { container } = render(
      <div>
        {topics.map((slug) => <HealthTopicArtwork key={slug} slug={slug} name={slug} />)}
      </div>,
    );

    const kinds = Array.from(container.querySelectorAll("[data-artwork-kind]"), (node) =>
      node.getAttribute("data-artwork-kind"),
    );
    expect(kinds).toHaveLength(topics.length);
    expect(kinds).not.toContain("general");
    expect(new Set(kinds).size).toBe(topics.length);

    const artworkSignatures = Array.from(
      container.querySelectorAll<SVGElement>("[data-artwork-kind]"),
      (node) => node.innerHTML,
    );
    expect(new Set(artworkSignatures).size).toBe(topics.length);
  });

  it("phóng lớn minh họa toàn màn hình và trả tiêu điểm về nút mở", async () => {
    const user = userEvent.setup();
    renderSection([dengue, flu]);

    const trigger = screen.getByRole("button", {
      name: "Phóng to minh họa Sốt xuất huyết Dengue",
    });
    await user.click(trigger);

    const dialog = await screen.findByRole("dialog", {
      name: "Minh họa y khoa: Sốt xuất huyết Dengue",
    });
    expect(within(dialog).getByRole("img", {
      name: "Minh họa chủ đề Sốt xuất huyết Dengue",
    })).toHaveAttribute("data-artwork-kind", "dengue");
    expect(screen.getByRole("button", { name: "Đóng ảnh phóng to" })).toHaveFocus();
    expect(screen.getByTestId("health-topic-stream")).toHaveAttribute("data-flow-state", "paused");

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });

  it("cho phép chuyển tuần tự bằng nút trước và tiếp theo", async () => {
    const user = userEvent.setup();
    renderSection([dengue, flu]);

    await user.click(screen.getByRole("button", { name: "Xem chủ đề tiếp theo" }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Cúm mùa" })).toHaveAttribute("aria-pressed", "true");
    });

    await user.click(screen.getByRole("button", { name: "Xem chủ đề trước" }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Sốt xuất huyết Dengue" })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    });
  });

  it("có điều khiển tạm dừng tự chuyển với trạng thái trợ năng rõ ràng", async () => {
    const user = userEvent.setup();
    renderSection([dengue, flu]);

    const pause = screen.getByRole("button", { name: "Tạm dừng tự chuyển chủ đề" });
    expect(pause).toHaveAttribute("aria-pressed", "false");

    await user.click(pause);

    expect(screen.getByRole("button", { name: "Tiếp tục tự chuyển chủ đề" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("progressbar", { name: "Thời gian tới chủ đề tiếp theo" })).toHaveAttribute(
      "aria-valuetext",
      "Đã tạm dừng",
    );
  });

  it("giữ nguyên đích triage và hành động mở nội dung đầy đủ", () => {
    renderSection([dengue]);

    expect(screen.getByRole("link", { name: /Kiểm tra triệu chứng/ })).toHaveAttribute(
      "href",
      "/auth/login",
    );
    expect(screen.getByRole("button", { name: "Xem hướng dẫn đầy đủ" })).toBeInTheDocument();
  });

  it("chỉ gắn nhãn AI lên chủ đề đang hiển thị nếu dữ liệu xác nhận", async () => {
    const user = userEvent.setup();
    renderSection([dengue, flu]);

    expect(screen.getByText("AI diễn giải")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cúm mùa" }));

    await waitFor(() => {
      expect(screen.queryByText("AI diễn giải")).not.toBeInTheDocument();
    });
  });
});
