import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SimpleNurseDashboardDTO } from "@/types/simple-nurse";

const hooks = vi.hoisted(() => ({ useSimpleNurseDashboard: vi.fn() }));
const motionPrefs = vi.hoisted(() => ({ reduce: true }));

vi.mock("@/queries/useSimpleNurseQueries", () => ({
  useSimpleNurseDashboard: hooks.useSimpleNurseDashboard,
}));

// Mặc định giả lập người dùng đã bật "giảm chuyển động": mọi con số hiện thẳng
// giá trị cuối nên kiểm thử không phụ thuộc nhịp khung hình. Ca kiểm thử nào
// cần xem hiệu ứng thì tự tắt cờ này.
vi.mock("framer-motion", async (importOriginal) => {
  const actual = await importOriginal<typeof import("framer-motion")>();
  return { ...actual, useReducedMotion: () => motionPrefs.reduce };
});

const { SimpleNurseDashboard } = await import(
  "@/components/clinical/nurse-simple/SimpleNurseDashboard"
);

function dashboard(overrides: Partial<SimpleNurseDashboardDTO> = {}): SimpleNurseDashboardDTO {
  return {
    generated_at: "2026-09-14T09:30:00",
    waiting: 5,
    assigned_total: 2,
    assigned_to_me: 1,
    parked: 3,
    decided: 4,
    insufficient_live: 1,
    longest_wait_minutes: 95,
    esi_distribution: [
      { level: 1, count: 0 },
      { level: 2, count: 6 },
      { level: 3, count: 1 },
      { level: 4, count: 0 },
      { level: 5, count: 0 },
      { level: null, count: 0 },
    ],
    wait_buckets: [
      { key: "UNDER_WARNING", count: 1 },
      { key: "WARNING", count: 2 },
      { key: "CRITICAL", count: 4 },
    ],
    agreement: {
      decided_total: 4,
      confirmed: 2,
      escalated: 1,
      de_escalated: 1,
      adjusted_without_proposal: 0,
    },
    reason_codes: [
      { code: "MATCHES_PROTOCOL", count: 2 },
      { code: "ADDITIONAL_CLINICAL_JUDGMENT", count: 2 },
    ],
    daily_volume: Array.from({ length: 14 }, (_, index) => ({
      date: `2026-09-${String(index + 1).padStart(2, "0")}`,
      completed: index === 13 ? 3 : 0,
      decided: index === 13 ? 1 : 0,
    })),
    ...overrides,
  };
}

function setup(
  data: SimpleNurseDashboardDTO | undefined,
  flags: { isLoading?: boolean; isError?: boolean; isFetching?: boolean } = {},
) {
  const refetch = vi.fn();
  hooks.useSimpleNurseDashboard.mockReturnValue({
    data,
    isLoading: flags.isLoading ?? false,
    isError: flags.isError ?? false,
    error: undefined,
    refetch,
    isFetching: flags.isFetching ?? false,
  });
  return { refetch };
}

/** Giá trị mà trình đọc màn hình nhận được (bản sao cố định cạnh số đang chạy). */
function spokenValue(container: HTMLElement, text: string) {
  return within(container).getByText(text, { selector: ".sr-only" });
}

afterEach(() => {
  hooks.useSimpleNurseDashboard.mockReset();
  motionPrefs.reduce = true;
});

describe("bảng số liệu tổng quan của trạm điều phối", () => {
  it("hiển thị đúng các con số đếm được từ hàng đợi", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    expect(screen.getByRole("heading", { level: 1, name: "Tổng quan trạm điều phối" })).toBeInTheDocument();
    // Giờ chụp số liệu luôn kèm ngày, dạng "hh:mm ngày dd/mm".
    expect(screen.getByText(/^\d{2}:\d{2} ngày \d{2}\/\d{2}$/)).toBeInTheDocument();

    // Con số chính = ca đang chờ + ca đã có người phụ trách (5 + 2): đúng tập
    // ca mà thanh thời gian chờ và phân bố ESI cùng đếm trên đó. Số "chưa ai
    // nhận" (thứ thẻ Hàng đợi ở thanh bên đếm) đứng ngay dưới, mang tên riêng.
    const hero = screen.getByRole("region", { name: "Ca đang mở" });
    expect(spokenValue(hero, "7")).toBeInTheDocument();
    expect(within(hero).getByText("1 giờ 35 phút")).toBeInTheDocument();
    expect(hero).toHaveTextContent("5 chưa ai nhận");
    expect(hero).toHaveTextContent("2 đã có người phụ trách");
    expect(within(hero).getByRole("link", { name: /Xem hàng đợi/ })).toHaveAttribute("href", "/clinical/queue-pilot");

    const mine = screen.getByRole("region", { name: "Bạn phụ trách" });
    expect(spokenValue(mine, "1")).toBeInTheDocument();
    expect(within(mine).getByText(/Cả kíp đang giữ 2 ca/)).toBeInTheDocument();
    expect(spokenValue(screen.getByRole("region", { name: "Tạm gác" }), "3")).toBeInTheDocument();
    expect(spokenValue(screen.getByRole("region", { name: "Đã chốt" }), "4")).toBeInTheDocument();
    expect(spokenValue(screen.getByRole("region", { name: "Thiếu dữ liệu kết luận" }), "1")).toBeInTheDocument();
  });

  it("chia thời gian chờ đúng hai mốc của bảng ca, mỗi nhóm có nhãn chữ và số", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    const hero = screen.getByRole("region", { name: "Ca đang mở" });
    const split = within(hero).getByRole("list", { name: "Thời gian chờ của 7 ca đang mở" });
    expect(within(split).getByRole("listitem", { name: /^Dưới 30 phút: 1 ca, 14% trên 7 ca/ })).toBeInTheDocument();
    expect(within(split).getByRole("listitem", { name: /^30 – 59 phút: 2 ca, 29% trên 7 ca/ })).toBeInTheDocument();
    expect(within(split).getByRole("listitem", { name: /^Từ 60 phút: 4 ca, 57% trên 7 ca/ })).toBeInTheDocument();
  });

  it("nhóm chờ bằng không không có đoạn trên thanh nhưng vẫn có mặt trong chú giải", () => {
    setup(
      dashboard({
        wait_buckets: [
          { key: "UNDER_WARNING", count: 7 },
          { key: "WARNING", count: 0 },
          { key: "CRITICAL", count: 0 },
        ],
        longest_wait_minutes: 12,
      }),
    );
    render(<SimpleNurseDashboard />);

    const hero = screen.getByRole("region", { name: "Ca đang mở" });
    const split = within(hero).getByRole("list", { name: "Thời gian chờ của 7 ca đang mở" });
    expect(within(split).getAllByRole("listitem")).toHaveLength(1);
    expect(within(hero).getByText("Từ 60 phút")).toBeInTheDocument();
    expect(within(hero).getByText("12 phút")).toBeInTheDocument();
  });

  it("phát đủ sáu vạch mức độ, kể cả mức đang bằng không", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    const list = screen.getByRole("list", { name: "Số ca theo mức AI đề xuất" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(6);
    for (const level of [1, 2, 3, 4, 5]) {
      expect(within(list).getByText(`ESI ${level}`)).toBeInTheDocument();
    }
    expect(within(list).getByText("Chưa đủ dữ liệu")).toBeInTheDocument();

    // Một mức vắng mặt cũng là thông tin: vẫn có hàng của nó, đọc ra "0 ca".
    expect(within(list).getByRole("listitem", { name: /^ESI 1 · Hồi sức: 0 ca/ })).toBeInTheDocument();
    expect(
      within(list).getByRole("listitem", { name: "ESI 2 · Cấp cứu: 6 ca, 86% trên 7 ca chưa đóng" }),
    ).toBeInTheDocument();
  });

  /**
   * Ràng buộc nội dung quan trọng nhất của màn này: khối đối chiếu chỉ được
   * gọi là quyết định của điều dưỡng. Hệ thống không có kết luận chuẩn nào để
   * so, nên mọi cách gọi kiểu "độ chính xác của AI" đều là tuyên bố sai.
   */
  it.each([
    ["khi đã có ca chốt", dashboard()],
    [
      "khi chưa có ca nào chốt",
      dashboard({
        decided: 0,
        agreement: { decided_total: 0, confirmed: 0, escalated: 0, de_escalated: 0, adjusted_without_proposal: 0 },
        reason_codes: [],
      }),
    ],
  ])("không bao giờ gọi phần đối chiếu là độ chính xác của AI (%s)", (_label, data) => {
    setup(data);
    const { container } = render(<SimpleNurseDashboard />);
    const text = container.textContent ?? "";

    // Cụm "độ chính xác" chỉ được phép xuất hiện trong đúng câu phủ định.
    // Đếm hai bên phải bằng nhau: một lần dùng nó như một nhãn khẳng định là
    // đã tuyên bố sai về năng lực của hệ thống.
    const mentions = text.match(/độ chính xác/gi) ?? [];
    const denials = text.match(/không phải độ chính xác/gi) ?? [];
    expect(mentions.length).toBeGreaterThan(0);
    expect(mentions).toHaveLength(denials.length);

    expect(
      screen.getByRole("heading", { name: "Điều dưỡng đã làm gì với đề xuất của AI" }),
    ).toBeInTheDocument();
  });

  it("luôn nêu mẫu số đi kèm mọi tỉ lệ", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    expect(screen.getByText("Trên 4 ca đã chốt")).toBeInTheDocument();
    expect(screen.getByText(/Trên 7 ca chưa đóng/)).toBeInTheDocument();
    expect(screen.getByText(/Tỉ lệ tính trên 4 ca có mức AI đề xuất/)).toBeInTheDocument();
    expect(screen.getByText(/trên 4 ca đã chốt có ghi lý do/)).toBeInTheDocument();
  });

  it("nói rõ chiều của thang ESI trong nhãn, không để người đọc tự đoán", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    expect(screen.getByText("Chốt khẩn hơn AI")).toBeInTheDocument();
    expect(screen.getByText("Chốt ít khẩn hơn AI")).toBeInTheDocument();
    expect(screen.getByText("Giữ nguyên mức AI")).toBeInTheDocument();
  });

  it("ca tự chốt khi AI chưa đề xuất mức được nêu riêng, không chen vào thanh so sánh", () => {
    setup(
      dashboard({
        decided: 5,
        agreement: { decided_total: 5, confirmed: 2, escalated: 1, de_escalated: 1, adjusted_without_proposal: 1 },
      }),
    );
    render(<SimpleNurseDashboard />);

    const panel = screen.getByRole("region", { name: "Điều dưỡng đã làm gì với đề xuất của AI" });
    expect(within(panel).getByText("Trên 5 ca đã chốt")).toBeInTheDocument();
    expect(panel).toHaveTextContent("Thêm 1 ca điều dưỡng tự chốt vì AI chưa đề xuất mức");

    const bar = within(panel).getByRole("list", { name: "Quyết định của điều dưỡng trên 4 ca có mức AI đề xuất" });
    expect(within(bar).getAllByRole("listitem")).toHaveLength(3);
    expect(
      within(bar).getByRole("listitem", { name: "Giữ nguyên mức AI: 2 ca, 50% trên 4 ca có mức AI đề xuất" }),
    ).toBeInTheDocument();
  });

  it("chưa có ca nào chốt thì nói thẳng, không vẽ một biểu đồ rỗng", () => {
    setup(
      dashboard({
        decided: 0,
        agreement: {
          decided_total: 0,
          confirmed: 0,
          escalated: 0,
          de_escalated: 0,
          adjusted_without_proposal: 0,
        },
        reason_codes: [],
      }),
    );
    render(<SimpleNurseDashboard />);

    expect(screen.getByText(/Chưa có ca nào được chốt, nên chưa có gì để đối chiếu/)).toBeInTheDocument();
    expect(screen.queryByText("Chốt khẩn hơn AI")).not.toBeInTheDocument();
    expect(screen.getByText("Chưa có ca nào được chốt nên chưa ghi nhận lý do nào.")).toBeInTheDocument();
  });

  it("liệt kê lý do chốt ca bằng đúng chữ của biểu mẫu quyết định", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    const reasons = screen.getByRole("region", { name: "Lý do điều dưỡng ghi lại" });
    expect(within(reasons).getByText("Dữ liệu phù hợp với phác đồ đã tham chiếu")).toBeInTheDocument();
    expect(within(reasons).getByText("Nhận định lâm sàng bổ sung")).toBeInTheDocument();
  });

  it("chú thích nổi hiện khi focus, mũi tên đi qua từng vạch, Esc ẩn đi", async () => {
    const user = userEvent.setup();
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    const rows = within(screen.getByRole("list", { name: "Số ca theo mức AI đề xuất" })).getAllByRole("listitem");
    // Mỗi biểu đồ chỉ là một điểm dừng Tab.
    expect(rows.filter((row) => row.tabIndex === 0)).toHaveLength(1);

    act(() => rows[1].focus());
    expect(screen.getByText("86% trên 7 ca chưa đóng")).toBeInTheDocument();

    await user.keyboard("{ArrowDown}");
    expect(rows[2]).toHaveFocus();
    expect(rows[2].tabIndex).toBe(0);
    expect(await screen.findByText("14% trên 7 ca chưa đóng")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByText("14% trên 7 ca chưa đóng")).not.toBeInTheDocument());
  });

  it("di chuột lên một đoạn của thanh so sánh thì hiện số ca và mẫu số", async () => {
    const user = userEvent.setup();
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    const segment = screen.getByRole("listitem", { name: /^Chốt khẩn hơn AI: 1 ca/ });
    await user.hover(segment);
    expect(screen.getByText("25% trên 4 ca có mức AI đề xuất")).toBeInTheDocument();

    await user.unhover(segment);
    await waitFor(() => expect(screen.queryByText("25% trên 4 ca có mức AI đề xuất")).not.toBeInTheDocument());
  });

  it("biểu đồ khối lượng có chú giải hai chuỗi và bản bảng số liệu tương đương", async () => {
    const user = userEvent.setup();
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    const panel = screen.getByRole("region", { name: "Khối lượng 14 ngày gần nhất" });
    expect(within(panel).getByText("01/09 – 14/09 · 3 phiên sàng lọc kết thúc, 1 ca được chốt")).toBeInTheDocument();
    const legend = within(panel).getByRole("list", { name: "Chú giải" });
    expect(within(legend).getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "Phiên sàng lọc kết thúc",
      "Ca được điều dưỡng chốt",
    ]);
    expect(within(panel).queryByRole("table")).not.toBeInTheDocument();

    await user.click(within(panel).getByRole("button", { name: "Bảng số liệu" }));
    expect(within(panel).getByRole("button", { name: "Bảng số liệu" })).toHaveAttribute("aria-pressed", "true");

    const table = await within(panel).findByRole("table");
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(15);
    // Ngày cuối còn đang chạy: bảng nói rõ số của nó chưa phải số cả ngày.
    expect(within(rows[14]).getByRole("rowheader")).toHaveTextContent("14/09 tính đến lúc cập nhật");
    expect(within(rows[13]).getByRole("rowheader")).toHaveTextContent(/^13\/09$/);
    expect(within(rows[14]).getAllByRole("cell").map((cell) => cell.textContent)).toEqual(["3", "1"]);
  });

  it("con số chính đếm lên một lần; vòng làm mới cùng số liệu không đếm lại", async () => {
    motionPrefs.reduce = false;
    setup(dashboard());
    const { rerender } = render(<SimpleNurseDashboard />);

    const hero = screen.getByRole("region", { name: "Ca đang mở" });
    // Trình đọc màn hình nhận ngay giá trị cuối, không nghe các số trung gian.
    expect(spokenValue(hero, "7")).toBeInTheDocument();
    // Phần hiển thị bắt đầu từ 0 rồi đếm lên.
    expect(within(hero).getByText("0")).toBeInTheDocument();
    await waitFor(() => expect(within(hero).getAllByText("7")).toHaveLength(2));

    // Lần làm mới trả về cùng số liệu (đối tượng mới): không đếm lại từ 0.
    setup(dashboard());
    rerender(<SimpleNurseDashboard />);
    expect(within(hero).queryByText("0")).not.toBeInTheDocument();
    expect(within(hero).getAllByText("7")).toHaveLength(2);

    // Số thật sự đổi: giá trị đọc được đổi ngay, phần hiển thị trượt tới.
    setup(dashboard({ waiting: 6 }));
    rerender(<SimpleNurseDashboard />);
    expect(spokenValue(hero, "8")).toBeInTheDocument();
    await waitFor(() => expect(within(hero).getAllByText("8")).toHaveLength(2));
  });

  it("nút tải lại gọi lại truy vấn và khóa trong lúc đang tải", async () => {
    const user = userEvent.setup();
    const { refetch } = setup(dashboard());
    const { rerender } = render(<SimpleNurseDashboard />);

    await user.click(screen.getByRole("button", { name: "Tải lại" }));
    expect(refetch).toHaveBeenCalledTimes(1);

    setup(dashboard(), { isFetching: true });
    rerender(<SimpleNurseDashboard />);
    expect(screen.getByRole("button", { name: "Tải lại" })).toBeDisabled();
  });

  it("đang tải lần đầu thì hiện khung chờ, chưa hiện con số nào", () => {
    setup(undefined, { isLoading: true });
    render(<SimpleNurseDashboard />);

    expect(screen.getByRole("status")).toHaveTextContent("Đang tải số liệu tổng quan");
    expect(screen.getByRole("heading", { level: 1, name: "Tổng quan trạm điều phối" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Ca đang mở" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tải lại" })).not.toBeInTheDocument();
  });

  it("hỏng đường truyền thì báo lỗi kèm lối thử lại, không hiện số cũ", async () => {
    const user = userEvent.setup();
    const { refetch } = setup(undefined, { isError: true });
    render(<SimpleNurseDashboard />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Thử tải lại/ }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("lần làm mới hỏng thì ẩn cả số liệu cũ đang có trong bộ nhớ đệm", () => {
    setup(dashboard(), { isError: true });
    render(<SimpleNurseDashboard />);

    expect(screen.getByRole("alert")).toHaveTextContent("Không tải được số liệu tổng quan.");
    expect(screen.queryByRole("region", { name: "Ca đang mở" })).not.toBeInTheDocument();
    expect(screen.queryByText("Trên 4 ca đã chốt")).not.toBeInTheDocument();
  });
});
