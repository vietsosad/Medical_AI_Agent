import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { simpleNurseDashboardSchema } from "@/schemas/simple-nurse.schema";
import type {
  SimpleDecisionMatrixDTO,
  SimpleDecisionWaitDTO,
  SimpleFlaggedClaimDTO,
  SimpleMatrixRowKey,
  SimpleNurseDashboardDTO,
  SimpleWeekdayHourDTO,
} from "@/types/simple-nurse";

const hooks = vi.hoisted(() => ({ useSimpleNurseDashboard: vi.fn(), useSimpleNurseQueue: vi.fn() }));

vi.mock("@/queries/useSimpleNurseQueries", () => ({
  useSimpleNurseDashboard: hooks.useSimpleNurseDashboard,
  useSimpleNurseQueue: hooks.useSimpleNurseQueue,
}));

// Giảm chuyển động: số hiện thẳng giá trị cuối, kiểm thử không phụ thuộc khung hình.
vi.mock("framer-motion", async (importOriginal) => {
  const actual = await importOriginal<typeof import("framer-motion")>();
  return { ...actual, useReducedMotion: () => true };
});

const { DecisionMatrixPanel } = await import("@/components/clinical/nurse-simple/dashboard/DecisionMatrixPanel");
const { ClaimTimePanel } = await import("@/components/clinical/nurse-simple/dashboard/ClaimTimePanel");
const { DecisionWaitPanel } = await import("@/components/clinical/nurse-simple/dashboard/DecisionWaitPanel");
const { WeekdayHourPanel } = await import("@/components/clinical/nurse-simple/dashboard/WeekdayHourPanel");
const { SimpleNurseDashboard } = await import("@/components/clinical/nurse-simple/SimpleNurseDashboard");

const ROW_KEYS: SimpleMatrixRowKey[] = ["1", "2", "3", "4", "5", "INSUFFICIENT", "IN_PROGRESS"];

/** `cells` = { "hàng:mức chốt": số ca }. Tổng tự tính đúng chiều thang ESI. */
function decisionMatrix(cells: Record<string, number> = {}, withoutFinal = 0): SimpleDecisionMatrixDTO {
  let kept = 0;
  let more = 0;
  let less = 0;
  let without = 0;
  const rows = ROW_KEYS.map((key) => ({
    key,
    counts: ([1, 2, 3, 4, 5] as const).map((level) => {
      const count = cells[`${key}:${level}`] ?? 0;
      if (key === "INSUFFICIENT" || key === "IN_PROGRESS") without += count;
      else if (level === Number(key)) kept += count;
      else if (level < Number(key)) more += count;
      else less += count;
      return { final_esi: level, count };
    }),
  }));
  return {
    decided_total: kept + more + less + without + withoutFinal,
    kept,
    more_urgent: more,
    less_urgent: less,
    without_proposal: without,
    without_final_esi: withoutFinal,
    rows,
  };
}

function flaggedClaim(counts: number[] = [], extra: Partial<SimpleFlaggedClaimDTO> = {}): SimpleFlaggedClaimDTO {
  const bins = Array.from({ length: 13 }, (_, index) => ({
    min_minutes: index * 5,
    max_minutes: index === 12 ? null : index * 5 + 5,
    count: counts[index] ?? 0,
  }));
  const claimed = bins.reduce((sum, bin) => sum + bin.count, 0);
  const underWarning = bins.filter((bin) => bin.min_minutes < 30).reduce((sum, bin) => sum + bin.count, 0);
  return {
    min_cases: 5,
    flagged_total: claimed + (extra.unclaimed ?? 0) + (extra.untimed ?? 0),
    claimed,
    unclaimed: 0,
    untimed: 0,
    claimed_under_warning: underWarning,
    bins,
    ...extra,
  };
}

function decisionWait(rows: Partial<Record<SimpleMatrixRowKey, [number, number | null]>> = {}): SimpleDecisionWaitDTO {
  const list = ROW_KEYS.map((key) => {
    const [count, median] = rows[key] ?? [0, null];
    return { key, count, median_minutes: median };
  });
  return { min_cases: 5, decided_total: list.reduce((sum, row) => sum + row.count, 0), rows: list };
}

function weekdayHour(cells: Record<string, number> = {}, days = [2, 2, 2, 2, 2, 2, 2]): SimpleWeekdayHourDTO {
  return {
    utc_offset_hours: 7,
    first_day: "2026-09-01",
    last_day: "2026-09-14",
    total: Object.values(cells).reduce((sum, value) => sum + value, 0),
    rows: days.map((dayCount, index) => {
      const weekday = (index + 1) as 1 | 2 | 3 | 4 | 5 | 6 | 7;
      return { weekday, days: dayCount, hours: Array.from({ length: 24 }, (_, hour) => cells[`${weekday}:${hour}`] ?? 0) };
    }),
  };
}

afterEach(() => {
  hooks.useSimpleNurseDashboard.mockReset();
  hooks.useSimpleNurseQueue.mockReset();
});

// ----------------------------------------------------------------------------
// Ma trận mức AI × mức điều dưỡng chốt
// ----------------------------------------------------------------------------

describe("ma trận điều dưỡng đã làm gì với đề xuất của AI", () => {
  const matrix = decisionMatrix({ "3:3": 6, "4:2": 2, "2:4": 1, "INSUFFICIENT:2": 1 });

  it("gọi đúng tên, không bao giờ là độ chính xác của AI", () => {
    const { container } = render(<DecisionMatrixPanel matrix={matrix} windowDays={14} order={0} />);

    expect(
      screen.getByRole("region", { name: "Điều dưỡng đã làm gì với đề xuất của AI, theo từng mức" }),
    ).toBeInTheDocument();
    const text = container.textContent ?? "";
    const mentions = text.match(/độ chính xác/gi) ?? [];
    expect(mentions.length).toBeGreaterThan(0);
    expect(mentions).toHaveLength((text.match(/không phải độ chính xác/gi) ?? []).length);
  });

  it("ô bên trái đường chéo là chốt khẩn hơn AI, ô trên đường chéo là giữ nguyên", () => {
    render(<DecisionMatrixPanel matrix={matrix} windowDays={14} order={0} />);
    const grid = screen.getByRole("grid");

    expect(
      within(grid).getByRole("gridcell", {
        name: "AI đề xuất ESI 4 · Ít khẩn cấp, điều dưỡng chốt ESI 2: 2 ca. Chốt khẩn hơn AI",
      }),
    ).toBeInTheDocument();
    expect(
      within(grid).getByRole("gridcell", {
        name: "AI đề xuất ESI 2 · Cấp cứu, điều dưỡng chốt ESI 4: 1 ca. Chốt ít khẩn hơn AI",
      }),
    ).toBeInTheDocument();
    expect(
      within(grid).getByRole("gridcell", {
        name: "AI đề xuất ESI 3 · Khẩn trương, điều dưỡng chốt ESI 3: 6 ca. Giữ nguyên mức AI",
      }),
    ).toBeInTheDocument();
    // Không có phiên nào đang sàng lọc thì không có hàng đó.
    expect(within(grid).queryByRole("rowheader", { name: /Đang sàng lọc/ })).not.toBeInTheDocument();
  });

  it("nêu tổng giữ nguyên, khẩn hơn, ít khẩn hơn kèm mẫu số", () => {
    render(<DecisionMatrixPanel matrix={matrix} windowDays={14} order={0} />);
    const totals = screen.getByRole("list", { name: "Tổng theo việc điều dưỡng đã làm" });
    const items = within(totals).getAllByRole("listitem");

    const expected = [
      ["Giữ nguyên mức AI (ô có viền)", "6", "60% trên 10 ca"],
      ["Chốt khẩn hơn AI (bên trái ô có viền)", "2", "20% trên 10 ca"],
      ["Chốt ít khẩn hơn AI (bên phải ô có viền)", "1", "10% trên 10 ca"],
      ["AI chưa đề xuất mức để so", "1", "10% trên 10 ca"],
    ];
    expect(items).toHaveLength(expected.length);
    expected.forEach(([label, value, share], index) => {
      expect(within(items[index]).getByText(label)).toBeInTheDocument();
      // Giá trị trình đọc màn hình nhận (bản sao cố định cạnh số đang chạy).
      expect(within(items[index]).getByText(value, { selector: ".sr-only" })).toBeInTheDocument();
      expect(within(items[index]).getByText(share)).toBeInTheDocument();
    });
  });

  it("một điểm dừng Tab; mũi tên đi qua từng ô và hiện chú thích", async () => {
    const user = userEvent.setup();
    render(<DecisionMatrixPanel matrix={matrix} windowDays={14} order={0} />);
    const grid = screen.getByRole("grid");
    const cells = within(grid).getAllByRole("gridcell").filter((cell) => cell.tabIndex >= 0);
    expect(cells).toHaveLength(1);

    const target = within(grid).getByRole("gridcell", { name: /ESI 4 · Ít khẩn cấp, điều dưỡng chốt ESI 2/ });
    act(() => target.focus());
    expect(screen.getByText("Chốt khẩn hơn AI · 20% trên 10 ca đã chốt")).toBeInTheDocument();
    await user.keyboard("{ArrowRight}");
    expect(within(grid).getByRole("gridcell", { name: /ESI 4 · Ít khẩn cấp, điều dưỡng chốt ESI 3/ })).toHaveFocus();
  });

  it("bản bảng chỉ liệt kê cặp mức có ca, kèm việc điều dưỡng đã làm", async () => {
    const user = userEvent.setup();
    render(<DecisionMatrixPanel matrix={matrix} windowDays={14} order={0} />);
    await user.click(screen.getByRole("button", { name: "Bảng số liệu" }));

    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(4);
    expect(rows[2]).toHaveTextContent("ESI 4 · Ít khẩn cấpESI 22Chốt khẩn hơn AI");
  });

  it("chưa có ca nào chốt thì nói thẳng, không vẽ bảng rỗng", () => {
    render(<DecisionMatrixPanel matrix={decisionMatrix()} windowDays={7} order={0} />);

    expect(screen.queryByRole("grid")).not.toBeInTheDocument();
    expect(screen.getByText(/Chưa có ca nào được chốt trong 7 ngày qua, nên ma trận chưa có ô nào/)).toBeInTheDocument();
  });
});

// ----------------------------------------------------------------------------
// Từ lúc gắn cờ tới khi có người nhận
// ----------------------------------------------------------------------------

describe("thời gian từ lúc gắn cờ tới khi có người nhận", () => {
  it("nêu tỉ lệ nhận trước mốc kèm mẫu số và nói rõ mốc không phải chỉ tiêu", () => {
    render(<ClaimTimePanel claim={flaggedClaim([4, 2, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1])} windowDays={14} order={0} />);
    const panel = screen.getByRole("region", { name: "Từ lúc gắn cờ tới khi có người nhận" });

    expect(panel).toHaveTextContent("75%");
    expect(panel).toHaveTextContent("nhận trước mốc 30 phút: 6 trên 8 ca đã có người nhận");
    expect(panel).toHaveTextContent("không phải chỉ tiêu lâm sàng");
    expect(panel).not.toHaveTextContent(/mục tiêu|đạt/i);

    const bars = within(panel).getByRole("list", { name: /Số ca có cờ theo số phút/ });
    expect(within(bars).getAllByRole("listitem")).toHaveLength(13);
    expect(within(bars).getByRole("listitem", { name: "0 – 4 phút: 4 ca" })).toBeInTheDocument();
    expect(within(bars).getByRole("listitem", { name: "Từ 60 phút: 1 ca" })).toBeInTheDocument();
  });

  it("cột là điểm dừng bàn phím, chú thích nêu mẫu số", async () => {
    const user = userEvent.setup();
    render(<ClaimTimePanel claim={flaggedClaim([4, 2, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1])} windowDays={14} order={0} />);
    const first = screen.getByRole("listitem", { name: "0 – 4 phút: 4 ca" });

    act(() => first.focus());
    expect(screen.getByText("50% trên 8 ca đã có người nhận")).toBeInTheDocument();
    await user.keyboard("{End}");
    expect(screen.getByRole("listitem", { name: "Từ 60 phút: 1 ca" })).toHaveFocus();
    expect(await screen.findByText("Nhận sau 60 phút trở lên")).toBeInTheDocument();
  });

  it("ca chưa có người nhận được nêu riêng, không vào phần thời gian", () => {
    render(<ClaimTimePanel claim={flaggedClaim([6], { unclaimed: 2 })} windowDays={14} order={0} />);
    const panel = screen.getByRole("region", { name: "Từ lúc gắn cờ tới khi có người nhận" });

    expect(panel).toHaveTextContent("2 ca có cờ trong khoảng này hiện chưa có người nhận");
    expect(panel).toHaveTextContent("6 trên 6 ca đã có người nhận");
  });

  it("ít hơn số ca tối thiểu thì không vẽ, không nêu tỉ lệ", () => {
    render(<ClaimTimePanel claim={flaggedClaim([2, 1])} windowDays={14} order={0} />);

    expect(screen.queryByRole("list", { name: /Số ca có cờ theo số phút/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    expect(
      screen.getByText("Chưa đủ ca để vẽ: mới có 3 ca có cờ được nhận trong 14 ngày qua, cần ít nhất 5 ca."),
    ).toBeInTheDocument();
  });

  it("có cờ mà chưa ai nhận, và chưa có cờ nào: hai câu khác nhau", () => {
    const { rerender } = render(<ClaimTimePanel claim={flaggedClaim([], { unclaimed: 2 })} windowDays={14} order={0} />);
    expect(screen.getByText("Chưa có ca có cờ nào được nhận trong 14 ngày qua.")).toBeInTheDocument();

    rerender(<ClaimTimePanel claim={flaggedClaim()} windowDays={14} order={0} />);
    expect(screen.getByText("Bộ lọc khẩn cấp chưa gắn cờ ca nào trong 14 ngày qua.")).toBeInTheDocument();
  });

  it("bản bảng đủ mười ba khoảng", async () => {
    const user = userEvent.setup();
    render(<ClaimTimePanel claim={flaggedClaim([4, 2, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1])} windowDays={14} order={0} />);
    await user.click(screen.getByRole("button", { name: "Bảng số liệu" }));

    const table = await screen.findByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(14);
    expect(within(table).getByRole("rowheader", { name: /30 – 34 phút, từ mốc 30 phút/ })).toBeInTheDocument();
  });
});

// ----------------------------------------------------------------------------
// Trung vị chờ tới khi được chốt
// ----------------------------------------------------------------------------

describe("trung vị thời gian chờ tới khi được chốt", () => {
  it("mọi hàng nêu số ca; chưa đủ ca thì không nêu trung vị", () => {
    render(<DecisionWaitPanel wait={decisionWait({ "2": [7, 42], "3": [2, null] })} windowDays={14} order={0} />);
    const list = screen.getByRole("list", { name: /Trung vị thời gian chờ/ });

    expect(within(list).getByRole("listitem", { name: "ESI 2 · Cấp cứu: trung vị 42 phút, trên 7 ca" })).toBeInTheDocument();
    expect(
      within(list).getByRole("listitem", {
        name: "ESI 3 · Khẩn trương: 2 ca, chưa đủ ca để tính trung vị (cần ít nhất 5)",
      }),
    ).toBeInTheDocument();
    expect(within(list).getByRole("listitem", { name: "ESI 1 · Hồi sức: 0 ca, chưa có ca nào" })).toBeInTheDocument();
    expect(within(list).queryByRole("listitem", { name: /Đang sàng lọc/ })).not.toBeInTheDocument();
    expect(screen.getByText(/không phải chỉ tiêu/)).toBeInTheDocument();
  });

  it("trung vị dài hơn trục vẫn in đúng số", () => {
    render(<DecisionWaitPanel wait={decisionWait({ "4": [6, 3 * 24 * 60 + 60] })} windowDays={30} order={0} />);
    expect(screen.getByRole("listitem", { name: "ESI 4 · Ít khẩn cấp: trung vị 3 ngày 1 giờ, trên 6 ca" })).toBeInTheDocument();
  });

  it("chưa có ca nào chốt thì nói thẳng", () => {
    render(<DecisionWaitPanel wait={decisionWait()} windowDays={7} order={0} />);
    expect(screen.getByText("Chưa có ca nào được chốt trong 7 ngày qua nên chưa có thời gian chờ nào để tính.")).toBeInTheDocument();
  });
});

// ----------------------------------------------------------------------------
// Thứ × giờ theo giờ Việt Nam
// ----------------------------------------------------------------------------

describe("phiên kết thúc theo thứ và giờ", () => {
  it("bảy hàng thứ, ô mang số phiên, nói rõ giờ Việt Nam và khung đông nhất", () => {
    render(<WeekdayHourPanel panel={weekdayHour({ "1:3": 2, "1:9": 4, "5:14": 1 })} windowDays={14} order={0} />);
    const panel = screen.getByRole("region", { name: "Phiên kết thúc theo thứ và giờ" });
    const grid = within(panel).getByRole("grid");

    expect(within(grid).getAllByRole("rowheader").map((header) => header.textContent)).toEqual([
      "Thứ Hai",
      "Thứ Ba",
      "Thứ Tư",
      "Thứ Năm",
      "Thứ Sáu",
      "Thứ Bảy",
      "Chủ nhật",
    ]);
    expect(within(grid).getAllByRole("gridcell")).toHaveLength(7 * 24);
    expect(within(grid).getByRole("gridcell", { name: "Thứ Hai, 09:00 – 09:59: 4 phiên" })).toHaveTextContent("4");
    expect(panel).toHaveTextContent("7 phiên trong 14 ngày theo lịch Việt Nam (01/09 – 14/09), giờ Việt Nam.");
    expect(panel).toHaveTextContent("Đông nhất Thứ Hai, 09:00 – 09:59 với 4 trên 7 phiên (57%).");
    expect(panel).toHaveTextContent("Mỗi thứ có 2 ngày trong khoảng này.");
  });

  it("cửa sổ không chia đều cho 7 thì nói thứ nào có thêm ngày", () => {
    render(<WeekdayHourPanel panel={weekdayHour({ "1:3": 1 }, [5, 4, 4, 4, 4, 4, 5])} windowDays={30} order={0} />);
    expect(screen.getByText(/Thứ Hai, Chủ nhật có 5 ngày trong khoảng này, các thứ khác có 4 ngày/)).toBeInTheDocument();
  });

  it("đi theo hàng và cột bằng phím mũi tên", async () => {
    const user = userEvent.setup();
    render(<WeekdayHourPanel panel={weekdayHour({ "1:9": 4 })} windowDays={14} order={0} />);
    const grid = screen.getByRole("grid");

    act(() => within(grid).getByRole("gridcell", { name: "Thứ Hai, 09:00 – 09:59: 4 phiên" }).focus());
    expect(screen.getByText("100% trên 4 phiên · 2 ngày thứ hai trong khoảng này")).toBeInTheDocument();
    await user.keyboard("{ArrowDown}");
    expect(within(grid).getByRole("gridcell", { name: "Thứ Ba, 09:00 – 09:59: 0 phiên" })).toHaveFocus();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByText(/trên 4 phiên ·/)).not.toBeInTheDocument());
  });

  it("bản bảng chỉ liệt kê khung giờ có phiên", async () => {
    const user = userEvent.setup();
    render(<WeekdayHourPanel panel={weekdayHour({ "1:3": 2, "5:14": 1 })} windowDays={14} order={0} />);
    await user.click(screen.getByRole("button", { name: "Bảng số liệu" }));

    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      "Thứ Hai2 ngày trong khoảng này03:00 – 03:592",
      "Thứ Sáu2 ngày trong khoảng này14:00 – 14:591",
    ]);
  });

  it("chưa có phiên nào thì nói thẳng", () => {
    render(<WeekdayHourPanel panel={weekdayHour()} windowDays={14} order={0} />);
    expect(screen.queryByRole("grid")).not.toBeInTheDocument();
    expect(screen.getByText("Chưa có phiên nào kết thúc trong 14 ngày qua theo lịch Việt Nam.")).toBeInTheDocument();
  });
});

// ----------------------------------------------------------------------------
// Ghép vào bảng tổng quan, và tương thích với máy chủ cũ
// ----------------------------------------------------------------------------

function baseDashboard(overrides: Partial<SimpleNurseDashboardDTO> = {}): SimpleNurseDashboardDTO {
  const zeroCounts = [
    { key: "UNDER_WARNING" as const, count: 0 },
    { key: "WARNING" as const, count: 0 },
    { key: "CRITICAL" as const, count: 0 },
  ];
  return {
    generated_at: "2026-09-14T09:30:00",
    window_days: 14,
    waiting: 0,
    assigned_total: 0,
    assigned_to_me: 0,
    parked: 0,
    decided: 0,
    insufficient_live: 0,
    attention_live: 0,
    in_progress_live: 0,
    longest_wait_minutes: null,
    esi_distribution: [1, 2, 3, 4, 5, null].map((level) => ({ level: level as 1 | null, count: 0 })),
    wait_buckets: zeroCounts,
    esi_wait_matrix: ROW_KEYS.map((key) => ({ key, counts: zeroCounts })),
    completed_in_window: 0,
    decided_in_window: 0,
    agreement: { decided_total: 0, confirmed: 0, escalated: 0, de_escalated: 0, adjusted_without_proposal: 0 },
    reason_codes: [],
    daily_volume: Array.from({ length: 14 }, (_, index) => ({
      date: `2026-09-${String(index + 1).padStart(2, "0")}`,
      completed: 0,
      decided: 0,
    })),
    hour_of_day: Array.from({ length: 24 }, (_, hour) => ({ hour_utc: hour, completed: 0 })),
    recent_hours: Array.from({ length: 24 }, (_, index) => ({ hour_start: `2026-09-14T${String(index).padStart(2, "0")}:00:00`, completed: 0, decided: 0 })),
    ...overrides,
  };
}

function renderDashboard(data: SimpleNurseDashboardDTO) {
  hooks.useSimpleNurseDashboard.mockReturnValue({
    data,
    isLoading: false,
    isError: false,
    error: undefined,
    refetch: vi.fn(),
    isFetching: false,
    isPlaceholderData: false,
  });
  hooks.useSimpleNurseQueue.mockReturnValue({
    data: { items: [], summary: { total_waiting: 0, mine_count: 0, insufficient_count: 0 }, pagination: { page: 1, page_size: 5, total_items: 0, total_pages: 1 } },
    isLoading: false,
    isError: false,
    isSuccess: true,
  });
  return render(<SimpleNurseDashboard />);
}

describe("bốn khối trên bảng tổng quan", () => {
  const full = baseDashboard({
    decision_matrix: decisionMatrix(),
    flagged_claim: flaggedClaim([], { unclaimed: 2 }),
    decision_wait: decisionWait(),
    weekday_hour: weekdayHour({ "5:16": 12, "4:17": 2 }),
  });

  it("nằm trong phần lịch sử, dưới hàng chọn khoảng thời gian", () => {
    renderDashboard(full);
    const history = screen.getByRole("region", { name: /^Diễn biến/ });

    for (const name of [
      "Điều dưỡng đã làm gì với đề xuất của AI, theo từng mức",
      "Từ lúc gắn cờ tới khi có người nhận",
      "Thời gian chờ tới khi được chốt",
      "Phiên kết thúc theo thứ và giờ",
    ]) {
      expect(within(history).getByRole("region", { name })).toBeInTheDocument();
    }
  });

  it("máy chủ cũ chưa có bốn khối thì phần còn lại vẫn hiện đủ", () => {
    renderDashboard(baseDashboard());

    expect(screen.getByRole("region", { name: "Điều dưỡng đã làm gì với đề xuất của AI" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Phiên kết thúc theo thứ và giờ" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Từ lúc gắn cờ tới khi có người nhận" })).not.toBeInTheDocument();
  });

  it("lược đồ kiểm tra nhận cả payload cũ lẫn payload mới, và chặn hàng giờ thiếu", () => {
    expect(simpleNurseDashboardSchema.parse(baseDashboard())).not.toHaveProperty("weekday_hour");
    expect(simpleNurseDashboardSchema.parse(full).weekday_hour?.total).toBe(14);

    const broken = structuredClone(full);
    broken.weekday_hour?.rows[0].hours.pop();
    expect(() => simpleNurseDashboardSchema.parse(broken)).toThrow();
  });
});
