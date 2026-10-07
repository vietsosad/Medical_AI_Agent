import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SimpleNurseDashboardDTO } from "@/types/simple-nurse";

const hooks = vi.hoisted(() => ({ useSimpleNurseDashboard: vi.fn() }));

vi.mock("@/queries/useSimpleNurseQueries", () => ({
  useSimpleNurseDashboard: hooks.useSimpleNurseDashboard,
}));

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

function setup(data: SimpleNurseDashboardDTO | undefined, flags: { isLoading?: boolean; isError?: boolean } = {}) {
  hooks.useSimpleNurseDashboard.mockReturnValue({
    data,
    isLoading: flags.isLoading ?? false,
    isError: flags.isError ?? false,
    error: undefined,
    refetch: vi.fn(),
    isFetching: false,
  });
}

afterEach(() => hooks.useSimpleNurseDashboard.mockReset());

describe("bảng số liệu tổng quan của trạm điều phối", () => {
  it("hiển thị đúng các con số đếm được từ hàng đợi", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    expect(screen.getByRole("heading", { name: "Tổng quan trạm điều phối" })).toBeInTheDocument();
    // Ca chưa ai nhận, ca của chính mình, và thời gian chờ dài nhất.
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("1 giờ 35 phút")).toBeInTheDocument();
    expect(screen.getByText(/Cả kíp đang giữ 2 ca/)).toBeInTheDocument();
  });

  it("phát đủ sáu vạch mức độ, kể cả mức đang bằng không", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    for (const level of [1, 2, 3, 4, 5]) {
      expect(screen.getByText(`ESI ${level}`)).toBeInTheDocument();
    }
    expect(screen.getByText("Chưa có")).toBeInTheDocument();
  });

  /**
   * Ràng buộc nội dung quan trọng nhất của màn này: khối đối chiếu chỉ được
   * gọi là quyết định của điều dưỡng. Hệ thống không có kết luận chuẩn nào để
   * so, nên mọi cách gọi kiểu "độ chính xác của AI" đều là tuyên bố sai.
   */
  it("không bao giờ gọi phần đối chiếu là độ chính xác của AI", () => {
    setup(dashboard());
    const { container } = render(<SimpleNurseDashboard />);
    const text = container.textContent ?? "";

    // Cụm "độ chính xác" chỉ được phép xuất hiện trong đúng câu phủ định.
    // Đếm hai bên phải bằng nhau: một lần dùng nó như một nhãn khẳng định là
    // đã tuyên bố sai về năng lực của hệ thống.
    const mentions = text.match(/độ chính xác/gi) ?? [];
    const denials = text.match(/không phải độ chính xác/gi) ?? [];
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
  });

  it("nói rõ chiều của thang ESI trong nhãn, không để người đọc tự đoán", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    expect(screen.getByText("Chốt khẩn hơn AI")).toBeInTheDocument();
    expect(screen.getByText("Chốt ít khẩn hơn AI")).toBeInTheDocument();
    expect(screen.getByText("Giữ nguyên mức AI")).toBeInTheDocument();
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
  });

  it("liệt kê lý do chốt ca bằng đúng chữ của biểu mẫu quyết định", () => {
    setup(dashboard());
    render(<SimpleNurseDashboard />);

    const table = screen.getByRole("table");
    expect(within(table).getByText("Dữ liệu phù hợp với phác đồ đã tham chiếu")).toBeInTheDocument();
    expect(within(table).getByText("Nhận định lâm sàng bổ sung")).toBeInTheDocument();
  });

  it("hỏng đường truyền thì báo lỗi kèm lối thử lại, không hiện số cũ", () => {
    setup(undefined, { isError: true });
    render(<SimpleNurseDashboard />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Thử tải lại/ })).toBeInTheDocument();
  });
});
