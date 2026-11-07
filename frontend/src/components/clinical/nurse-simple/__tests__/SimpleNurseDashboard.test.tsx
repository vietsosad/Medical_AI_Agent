import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  hourOfDayInLocalTime,
  hourRangeLabel,
  localOffsetMinutes,
} from "@/components/clinical/nurse-simple/dashboard/dashboard-model";
import type {
  SimpleMatrixRowDTO,
  SimpleNurseDashboardDTO,
  SimpleNurseQueueItemDTO,
  SimpleNurseQueueResponseDTO,
} from "@/types/simple-nurse";

const hooks = vi.hoisted(() => ({ useSimpleNurseDashboard: vi.fn(), useSimpleNurseQueue: vi.fn() }));
const motionPrefs = vi.hoisted(() => ({ reduce: true }));

vi.mock("@/queries/useSimpleNurseQueries", () => ({
  useSimpleNurseDashboard: hooks.useSimpleNurseDashboard,
  useSimpleNurseQueue: hooks.useSimpleNurseQueue,
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
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

/** Ma trận khớp với `esi_distribution` và `wait_buckets` của bộ số mặc định. */
function matrix(rows: Partial<Record<SimpleMatrixRowDTO["key"], [number, number, number]>> = {}): SimpleMatrixRowDTO[] {
  const keys: SimpleMatrixRowDTO["key"][] = ["1", "2", "3", "4", "5", "INSUFFICIENT", "IN_PROGRESS"];
  return keys.map((key) => {
    const [under, warning, critical] = rows[key] ?? [0, 0, 0];
    return {
      key,
      counts: [
        { key: "UNDER_WARNING", count: under },
        { key: "WARNING", count: warning },
        { key: "CRITICAL", count: critical },
      ],
    };
  });
}

function recentHours(values: { completed?: number[]; decided?: number[] } = {}) {
  return Array.from({ length: 24 }, (_, index) => ({
    hour_start: `2026-09-${index < 15 ? "13" : "14"}T${String((index + 9) % 24).padStart(2, "0")}:00:00`,
    completed: values.completed?.[index] ?? 0,
    decided: values.decided?.[index] ?? 0,
  }));
}

function dashboard(overrides: Partial<SimpleNurseDashboardDTO> = {}): SimpleNurseDashboardDTO {
  const completed = Array.from({ length: 24 }, (_, index) => (index === 23 ? 2 : index === 20 ? 1 : 0));
  const decided = Array.from({ length: 24 }, (_, index) => (index === 22 ? 1 : 0));
  return {
    generated_at: "2026-09-14T09:30:00",
    window_days: 14,
    waiting: 5,
    assigned_total: 2,
    assigned_to_me: 1,
    parked: 3,
    decided: 4,
    insufficient_live: 1,
    attention_live: 0,
    in_progress_live: 0,
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
    esi_wait_matrix: matrix({ "2": [1, 1, 4], "3": [0, 1, 0] }),
    completed_in_window: 3,
    decided_in_window: 4,
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
    hour_of_day: Array.from({ length: 24 }, (_, hour) => ({ hour_utc: hour, completed: hour === 2 ? 2 : hour === 7 ? 1 : 0 })),
    recent_hours: recentHours({ completed, decided }),
    ...overrides,
  };
}

function queueItem(overrides: Partial<SimpleNurseQueueItemDTO> = {}): SimpleNurseQueueItemDTO {
  return {
    session_id: "ca-1",
    initial_message: "Đau ngực trái lan ra tay",
    final_action: "RETURN_MATCH",
    ai_proposed_esi: 2,
    is_insufficient: false,
    session_status: "COMPLETED",
    attention_required: false,
    attention_reason: null,
    attention_raised_at: null,
    turn_count: 4,
    waiting_since: "2026-09-14T09:00:00",
    review_status: "WAITING_REVIEW",
    assigned_nurse_id: null,
    case_version: 0,
    unread_count: 0,
    patient_email: "nb@test.vn",
    patient_name: "Nguyễn Văn A",
    final_esi: null,
    decision_type: null,
    decision_note: null,
    decided_at: null,
    parked_at: null,
    parked_by_nurse_id: null,
    parked_reason: null,
    ...overrides,
  };
}

function queueResponse(items: SimpleNurseQueueItemDTO[], totalItems = items.length): SimpleNurseQueueResponseDTO {
  return {
    items,
    summary: { total_waiting: totalItems, mine_count: 0, insufficient_count: 0 },
    pagination: { page: 1, page_size: 5, total_items: totalItems, total_pages: 1 },
  };
}

function setup(
  data: SimpleNurseDashboardDTO | undefined,
  flags: { isLoading?: boolean; isError?: boolean; isFetching?: boolean; isPlaceholderData?: boolean } = {},
  queue: SimpleNurseQueueResponseDTO = queueResponse([]),
) {
  const refetch = vi.fn();
  hooks.useSimpleNurseDashboard.mockReturnValue({
    data,
    isLoading: flags.isLoading ?? false,
    isError: flags.isError ?? false,
    error: undefined,
    refetch,
    isFetching: flags.isFetching ?? false,
    isPlaceholderData: flags.isPlaceholderData ?? false,
  });
  hooks.useSimpleNurseQueue.mockReturnValue({
    data: queue,
    isLoading: false,
    isError: false,
    isSuccess: true,
  });
  return { refetch };
}

/** Giá trị mà trình đọc màn hình nhận được (bản sao cố định cạnh số đang chạy). */
function spokenValue(container: HTMLElement, text: string) {
  return within(container).getByText(text, { selector: ".sr-only" });
}

afterEach(() => {
  hooks.useSimpleNurseDashboard.mockReset();
  hooks.useSimpleNurseQueue.mockReset();
  motionPrefs.reduce = true;
});

describe("bảng số liệu tổng quan của trạm điều phối", () => {
  it("hiển thị đúng các con số đếm được từ hàng đợi", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    expect(screen.getByRole("heading", { level: 1, name: "Tổng quan trạm điều phối" })).toBeInTheDocument();
    // Giờ chụp số liệu luôn kèm ngày, dạng "hh:mm ngày dd/mm".
    expect(screen.getByText(/^\d{2}:\d{2} ngày \d{2}\/\d{2}$/)).toBeInTheDocument();
    // Hai khu vực tách ảnh chụp hàng đợi khỏi phần lịch sử.
    expect(screen.getByRole("heading", { level: 2, name: "Ngay lúc này" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Diễn biến 14 ngày qua" })).toBeInTheDocument();

    // Con số chính = ca đang chờ + ca đã có người phụ trách (5 + 2): đúng tập
    // ca mà thanh thời gian chờ và ma trận cùng đếm trên đó.
    const hero = screen.getByRole("region", { name: "Ca đang mở" });
    expect(spokenValue(hero, "7")).toBeInTheDocument();
    expect(within(hero).getByText("1 giờ 35 phút")).toBeInTheDocument();
    // Ai đang giữ ca: phần "chưa ai nhận" là con số thẻ Hàng đợi ở thanh bên đếm.
    const owners = within(hero).getByRole("list", { name: "Ai đang giữ 7 ca đang mở" });
    expect(within(owners).getByRole("listitem", { name: "Chưa ai nhận: 5 ca, 71% trên 7 ca đang mở" })).toBeInTheDocument();
    expect(
      within(owners).getByRole("listitem", { name: "Đã có người phụ trách: 2 ca, 29% trên 7 ca đang mở" }),
    ).toBeInTheDocument();
    expect(within(hero).getByRole("link", { name: /Xem hàng đợi/ })).toHaveAttribute("href", "/clinical/queue-pilot");

    const flow = screen.getByRole("region", { name: "Luồng xử lý ca" });
    // Đường nối giữa các bước là trang trí (aria-hidden): chỉ bốn bước được đọc.
    const stages = within(flow).getAllByRole("listitem");
    const expected = [
      ["Chờ người nhận", "5", "Chưa ai nhận ca"],
      ["Đang xử lý", "2", "Bạn đang giữ 1 ca"],
      // "Đã chốt" là tổng mọi thời điểm; số trong 24 giờ qua là tổng của dải giờ.
      ["Đã chốt", "4", "1 ca trong 24 giờ qua"],
      ["Tạm gác", "3", "Chờ bổ sung thông tin"],
    ];
    expect(stages).toHaveLength(expected.length);
    expected.forEach(([label, value, hint], index) => {
      expect(stages[index]).toHaveTextContent(label);
      expect(spokenValue(stages[index], value)).toBeInTheDocument();
      expect(stages[index]).toHaveTextContent(hint);
    });

    expect(spokenValue(screen.getByRole("region", { name: "Thiếu dữ liệu kết luận" }), "1")).toBeInTheDocument();
    expect(spokenValue(screen.getByRole("region", { name: "Cần xem ngay" }), "0")).toBeInTheDocument();
    expect(spokenValue(screen.getByRole("region", { name: "Phiên kết thúc trong 24 giờ" }), "3")).toBeInTheDocument();
    expect(spokenValue(screen.getByRole("region", { name: "Ca được chốt trong 24 giờ" }), "1")).toBeInTheDocument();
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
        esi_wait_matrix: matrix({ "2": [6, 0, 0], "3": [1, 0, 0] }),
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

  // --------------------------------------------------------------------------
  // Ma trận mức khẩn × thời gian chờ
  // --------------------------------------------------------------------------

  it("ma trận phát đủ sáu hàng mức độ và ba cột mốc chờ, mỗi ô in số ca", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    const grid = screen.getByRole("grid");
    const headers = within(grid).getAllByRole("columnheader").map((header) => header.textContent);
    expect(headers).toEqual(["Mức AI đề xuất", "Dưới 30 phút", "30 – 59 phút", "Từ 60 phút", "Tổng"]);
    const rowHeaders = within(grid).getAllByRole("rowheader").map((header) => header.textContent);
    expect(rowHeaders).toEqual([
      "ESI 1, Hồi sức",
      "ESI 2, Cấp cứu",
      "ESI 3, Khẩn trương",
      "ESI 4, Ít khẩn cấp",
      "ESI 5, Không khẩn cấp",
      "Chưa đủ dữ liệu",
    ]);

    // Hàng ESI 2: 1 · 1 · 4, tổng 6 -- đúng phân bố mức độ của hàng đợi.
    const esi2 = within(grid).getAllByRole("row")[2];
    expect(within(esi2).getAllByRole("gridcell").map((cell) => within(cell).getByText(/\d/, { selector: ".sr-only" }).textContent)).toEqual(
      ["1", "1", "4", "6"],
    );
    // Một mức vắng mặt vẫn có hàng của nó, đọc ra 0.
    const esi1 = within(grid).getAllByRole("row")[1];
    expect(within(esi1).getAllByRole("gridcell").map((cell) => within(cell).getByText(/\d/, { selector: ".sr-only" }).textContent)).toEqual(
      ["0", "0", "0", "0"],
    );
    expect(screen.getByText(/Trên 7 ca đang mở/)).toBeInTheDocument();
    // Không có phiên nào đang sàng lọc thì không có hàng đó.
    expect(within(grid).queryByRole("rowheader", { name: /Đang sàng lọc/ })).not.toBeInTheDocument();
  });

  it("phiên đã gắn cờ mà chưa sàng lọc xong có hàng riêng, không bị gọi là một mức ESI", () => {
    setup(
      dashboard({
        waiting: 6,
        attention_live: 1,
        in_progress_live: 1,
        esi_wait_matrix: matrix({ "2": [1, 1, 4], "3": [0, 1, 0], IN_PROGRESS: [1, 0, 0] }),
      }),
    );
    render(<SimpleNurseDashboard />);

    const grid = screen.getByRole("grid");
    const row = within(grid).getByRole("rowheader", { name: /Đang sàng lọc/ });
    expect(row).not.toHaveTextContent("ESI");
    expect(screen.getByText(/Hàng “Đang sàng lọc” là phiên bộ lọc khẩn cấp đã gắn cờ/)).toBeInTheDocument();

    const hero = screen.getByRole("region", { name: "Ca đang mở" });
    expect(hero).toHaveTextContent("1 ca có dấu hiệu cần xem ngay");
    const attention = screen.getByRole("region", { name: "Cần xem ngay" });
    expect(spokenValue(attention, "1")).toBeInTheDocument();
    expect(attention).toHaveTextContent("1 phiên còn đang sàng lọc");
  });

  it("ô ma trận là một điểm dừng Tab; mũi tên đi theo hàng và theo cột, Esc ẩn chú thích", async () => {
    const user = userEvent.setup();
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    const grid = screen.getByRole("grid");
    const focusable = within(grid)
      .getAllByRole("gridcell")
      .filter((cell) => cell.tabIndex >= 0);
    expect(focusable).toHaveLength(1);

    const esi2Cells = within(within(grid).getAllByRole("row")[2]).getAllByRole("gridcell");
    act(() => esi2Cells[2].focus());
    expect(screen.getByText("ESI 2 · Cấp cứu · chờ từ 60 phút")).toBeInTheDocument();
    expect(screen.getByText("57% trên 7 ca đang mở")).toBeInTheDocument();

    await user.keyboard("{ArrowLeft}");
    expect(esi2Cells[1]).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    const esi3Cells = within(within(grid).getAllByRole("row")[3]).getAllByRole("gridcell");
    expect(esi3Cells[1]).toHaveFocus();
    expect(await screen.findByText("ESI 3 · Khẩn trương · chờ 30 – 59 phút")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByText("ESI 3 · Khẩn trương · chờ 30 – 59 phút")).not.toBeInTheDocument());
  });

  // --------------------------------------------------------------------------
  // Ca cần người nhận trước
  // --------------------------------------------------------------------------

  it("liệt kê đầu hàng đợi chung đúng thứ tự backend trả về, mỗi hàng mở thẳng hồ sơ ca", () => {
    const flagged = queueItem({
      session_id: "co",
      ai_proposed_esi: null,
      attention_required: true,
      attention_reason: "Ngất xỉu",
      session_status: "ACTIVE",
      patient_name: "Trần Thị B",
    });
    const esi2 = queueItem({ session_id: "esi2", patient_name: "Nguyễn Văn A" });
    setup(dashboard(), {}, queueResponse([flagged, esi2], 7));
    render(<SimpleNurseDashboard />);

    expect(hooks.useSimpleNurseQueue).toHaveBeenCalledWith({ bucket: "QUEUE", page: 1, pageSize: 5 });
    const panel = screen.getByRole("region", { name: "Ca cần người nhận trước" });
    const rows = within(panel).getAllByRole("link").filter((link) => link.getAttribute("href")?.startsWith("/clinical/cases-pilot/"));
    expect(rows.map((row) => row.getAttribute("href"))).toEqual(["/clinical/cases-pilot/co", "/clinical/cases-pilot/esi2"]);
    expect(rows[0]).toHaveTextContent("Trần Thị B");
    expect(rows[0]).toHaveTextContent("Cần xem ngay");
    // Cờ không bao giờ ghi thành một mức ESI.
    expect(rows[0]).toHaveTextContent("Chưa có mức ESI");
    expect(rows[1]).toHaveTextContent("ESI 2");
    expect(panel).toHaveTextContent("Còn 5 ca chưa ai nhận khác trong hàng đợi.");
    expect(within(panel).getByRole("link", { name: /Mở hàng đợi/ })).toHaveAttribute("href", "/clinical/queue-pilot");
  });

  it("hàng đợi trống thì nói thẳng, không vẽ danh sách rỗng", () => {
    setup(dashboard(), {}, queueResponse([]));
    render(<SimpleNurseDashboard />);

    const panel = screen.getByRole("region", { name: "Ca cần người nhận trước" });
    expect(panel).toHaveTextContent("Không có ca nào đang chờ người nhận.");
  });

  // --------------------------------------------------------------------------
  // Khoảng thời gian
  // --------------------------------------------------------------------------

  it("một hàng chọn khoảng thời gian đổi phần lịch sử và giữ số cũ mờ đi trong lúc chờ", async () => {
    const user = userEvent.setup();
    setup(dashboard());
    const { rerender } = render(<SimpleNurseDashboard />);

    expect(hooks.useSimpleNurseDashboard).toHaveBeenLastCalledWith({ days: 14 });
    const range = screen.getByRole("group", { name: "Khoảng thời gian" });
    expect(within(range).getAllByRole("button").map((button) => button.textContent)).toEqual([
      "7 ngày",
      "14 ngày",
      "30 ngày",
      "90 ngày",
    ]);
    expect(within(range).getByRole("button", { name: "14 ngày" })).toHaveAttribute("aria-pressed", "true");

    setup(dashboard(), { isPlaceholderData: true });
    await user.click(within(range).getByRole("button", { name: "30 ngày" }));
    expect(hooks.useSimpleNurseDashboard).toHaveBeenLastCalledWith({ days: 30 });
    expect(within(range).getByRole("button", { name: "30 ngày" })).toHaveAttribute("aria-pressed", "true");
    // Số của khoảng cũ vẫn ở đó, được đánh dấu đang tải -- không khung chờ.
    const history = screen.getByRole("region", { name: /^Diễn biến/ });
    expect(history).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("region", { name: "Ca đang mở" })).toBeInTheDocument();

    setup(
      dashboard({
        window_days: 30,
        daily_volume: Array.from({ length: 30 }, (_, index) => ({
          date: `2026-08-${String(index + 1).padStart(2, "0")}`,
          completed: index === 29 ? 2 : 0,
          decided: 0,
        })),
      }),
    );
    rerender(<SimpleNurseDashboard />);
    expect(screen.getByRole("heading", { level: 2, name: "Diễn biến 30 ngày qua" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Khối lượng 30 ngày gần nhất" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /^Diễn biến/ })).toHaveAttribute("aria-busy", "false");
  });

  it("giờ trong ngày xoay sang giờ trên máy và ghi rõ giờ đông nhất", () => {
    const data = dashboard();
    setup(data);
    render(<SimpleNurseDashboard />);

    const panel = screen.getByRole("region", { name: "Giờ có nhiều phiên kết thúc" });
    const local = hourOfDayInLocalTime(data.hour_of_day, localOffsetMinutes());
    const peak = local?.find((point) => point.completed === 2);
    expect(peak).toBeDefined();
    expect(panel).toHaveTextContent(`Đông nhất ${hourRangeLabel(peak?.hour ?? 0)} với 2 trên 3 phiên (67%).`);
    expect(within(panel).getByRole("listitem", { name: `${hourRangeLabel(peak?.hour ?? 0)}: 2 phiên` })).toBeInTheDocument();
  });

  // --------------------------------------------------------------------------
  // Quyết định của điều dưỡng so với đề xuất của AI
  // --------------------------------------------------------------------------

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
        decided_in_window: 0,
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

    expect(screen.getByText("Trên 4 ca đã chốt trong 14 ngày qua")).toBeInTheDocument();
    expect(screen.getByText(/Trên 7 ca đang mở/)).toBeInTheDocument();
    expect(screen.getByText(/Tỉ lệ tính trên 4 ca có mức AI đề xuất/)).toBeInTheDocument();
    expect(screen.getByText(/trên 4 ca đã chốt có ghi lý do trong 14 ngày qua/)).toBeInTheDocument();
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
    expect(within(panel).getByText("Trên 5 ca đã chốt trong 14 ngày qua")).toBeInTheDocument();
    expect(panel).toHaveTextContent("Thêm 1 ca điều dưỡng tự chốt vì AI chưa đề xuất mức");

    const bar = within(panel).getByRole("list", { name: "Quyết định của điều dưỡng trên 4 ca có mức AI đề xuất" });
    expect(within(bar).getAllByRole("listitem")).toHaveLength(3);
    expect(
      within(bar).getByRole("listitem", { name: "Giữ nguyên mức AI: 2 ca, 50% trên 4 ca có mức AI đề xuất" }),
    ).toBeInTheDocument();
  });

  it("chưa có ca nào chốt trong khoảng đang xem thì nói thẳng, không vẽ một biểu đồ rỗng", () => {
    setup(
      dashboard({
        decided: 0,
        decided_in_window: 0,
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

    expect(screen.getByText(/Chưa có ca nào được chốt trong 14 ngày qua, nên chưa có gì để đối chiếu/)).toBeInTheDocument();
    expect(screen.queryByText("Chốt khẩn hơn AI")).not.toBeInTheDocument();
    expect(screen.getByText("Chưa có ca nào được chốt trong 14 ngày qua nên chưa ghi nhận lý do nào.")).toBeInTheDocument();
  });

  it("liệt kê lý do chốt ca bằng đúng chữ của biểu mẫu quyết định", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    const reasons = screen.getByRole("region", { name: "Lý do điều dưỡng ghi lại" });
    expect(within(reasons).getByText("Dữ liệu phù hợp với phác đồ đã tham chiếu")).toBeInTheDocument();
    expect(within(reasons).getByText("Nhận định lâm sàng bổ sung")).toBeInTheDocument();
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

  // --------------------------------------------------------------------------
  // Chuyển động, làm mới, tải, lỗi
  // --------------------------------------------------------------------------

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

  it("luồng ca chỉ chạy chấm khi một bước vừa tăng, không chạy lúc tải trang", () => {
    setup(dashboard());
    const { container, rerender } = render(<SimpleNurseDashboard />);
    expect(container.querySelectorAll(".flow-travel")).toHaveLength(0);

    setup(dashboard({ waiting: 4, assigned_total: 3 }));
    rerender(<SimpleNurseDashboard />);
    expect(container.querySelectorAll(".flow-travel")).toHaveLength(1);
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
    expect(screen.queryByText("Trên 4 ca đã chốt trong 14 ngày qua")).not.toBeInTheDocument();
  });
});
