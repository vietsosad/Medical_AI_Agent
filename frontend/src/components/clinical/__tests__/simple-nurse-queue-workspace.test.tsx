import { fireEvent, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  SimpleNurseQueueItemDTO,
  SimpleNurseQueueParams,
  SimpleNurseQueueResponseDTO,
} from "@/types/simple-nurse";

const hooks = vi.hoisted(() => ({
  useSimpleNurseQueue: vi.fn(),
  useSimpleNurseQueueRealtime: vi.fn(),
  useClaimSimpleCase: vi.fn(),
  push: vi.fn(),
  replace: vi.fn(),
  search: { value: "" },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: hooks.push, replace: hooks.replace }),
  usePathname: () => "/clinical/queue-pilot",
  useSearchParams: () => new URLSearchParams(hooks.search.value),
}));

vi.mock("@/queries/useSimpleNurseQueries", () => ({
  useSimpleNurseQueue: hooks.useSimpleNurseQueue,
  useSimpleNurseQueueRealtime: hooks.useSimpleNurseQueueRealtime,
  useClaimSimpleCase: hooks.useClaimSimpleCase,
}));

vi.mock("@/store/useAuthStore", () => ({
  useAuthStore: (selector: (state: { user: { id: string; name: string } }) => unknown) =>
    selector({ user: { id: "nurse-1", name: "Nguyễn Minh Anh" } }),
}));

const { SimpleNurseQueueWorkspace } = await import(
  "@/components/clinical/nurse-simple/SimpleNurseQueueWorkspace"
);

/**
 * Bảng điều phối sau khi thiết kế lại: giữ đúng hợp đồng `?tab=` mà thanh điều
 * phối trỏ vào, giữ cờ "Cần xem ngay" trên ca người bệnh còn đang trò chuyện,
 * và khi hàng đợi tự làm mới thì chỉ ca vừa tới mới diễn hoạt.
 */

function queueItem(overrides: Partial<SimpleNurseQueueItemDTO>): SimpleNurseQueueItemDTO {
  return {
    session_id: "session-1",
    initial_message: "Đau họng, sốt nhẹ hai ngày nay",
    final_action: "RETURN_MATCH",
    ai_proposed_esi: 4,
    is_insufficient: false,
    session_status: "COMPLETED",
    attention_required: false,
    attention_reason: null,
    turn_count: 6,
    waiting_since: new Date().toISOString(),
    review_status: "WAITING_REVIEW",
    assigned_nurse_id: null,
    case_version: 3,
    unread_count: 0,
    patient_email: "nguoi.benh@example.com",
    patient_name: "Đỗ Minh Quân",
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

function response(items: SimpleNurseQueueItemDTO[], mineCount = 0): SimpleNurseQueueResponseDTO {
  return {
    items,
    summary: { total_waiting: items.length + mineCount, mine_count: mineCount, insufficient_count: 0 },
    pagination: { page: 1, page_size: 20, total_items: items.length, total_pages: 1 },
  };
}

const queueData = { current: response([]) };
const parkedData = { current: response([]) };
const mineData = { current: response([]) };

function serveQueue() {
  hooks.useSimpleNurseQueue.mockImplementation((params: SimpleNurseQueueParams) => {
    const data =
      params.bucket === "PARKED" ? parkedData.current : params.mineOnly ? mineData.current : queueData.current;
    return { data, isError: false, error: null, dataUpdatedAt: Date.now() };
  });
}

const claim = { mutate: vi.fn(), isPending: false, isError: false, error: null, variables: undefined };

function renderWorkspace() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const ui = () => (
    <QueryClientProvider client={client}>
      <SimpleNurseQueueWorkspace />
    </QueryClientProvider>
  );
  const view = render(ui());
  return { ...view, rerenderWorkspace: () => view.rerender(ui()) };
}

function rowOf(patientName: string): HTMLElement {
  const row = screen.getByText(patientName).closest("li");
  if (!row) throw new Error(`Không tìm thấy hàng của ${patientName}`);
  return row;
}

describe("bảng điều phối Triage Agent", () => {
  beforeEach(() => {
    hooks.search.value = "";
    hooks.useSimpleNurseQueueRealtime.mockReturnValue({ status: "open" });
    hooks.useClaimSimpleCase.mockReturnValue(claim);
    queueData.current = response([]);
    parkedData.current = response([]);
    mineData.current = response([]);
    serveQueue();
  });

  afterEach(() => {
    Object.values(hooks).forEach((hook) => {
      if (typeof hook === "function") hook.mockReset();
    });
    claim.mutate.mockReset();
  });

  it("giữ cờ \"Cần xem ngay\" trên ca người bệnh còn đang trò chuyện, không tự gán ESI cho nó", () => {
    queueData.current = response([
      queueItem({
        session_id: "co-co",
        patient_name: "Lê Văn Bình",
        ai_proposed_esi: null,
        final_action: null,
        session_status: "ACTIVE",
        attention_required: true,
        attention_reason: "khó thở dữ dội",
      }),
    ]);

    renderWorkspace();

    const row = rowOf("Lê Văn Bình");
    expect(within(row).getByText("Cần xem ngay")).toBeInTheDocument();
    expect(within(row).getByText("khó thở dữ dội")).toBeInTheDocument();
    expect(within(row).getByText("Người bệnh vẫn đang trò chuyện")).toBeInTheDocument();
    expect(within(row).getByText("Chưa có mức ESI")).toBeInTheDocument();
    expect(row).not.toHaveTextContent("ESI 1");
    // Hạng 1: viền đỏ và vòng sáng một lần khi xuất hiện.
    expect(row).toHaveAttribute("data-critical", "true");
  });

  it("nhận ca bằng đúng phiên bản ca rồi mở hồ sơ", () => {
    queueData.current = response([queueItem({ session_id: "ca-7", case_version: 7 })]);

    renderWorkspace();
    fireEvent.click(within(rowOf("Đỗ Minh Quân")).getByRole("button", { name: "Nhận ca" }));

    expect(claim.mutate).toHaveBeenCalledWith(
      { version: 7, action: "CLAIM" },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    const [, options] = claim.mutate.mock.calls[0] as [unknown, { onSuccess: () => void }];
    options.onSuccess();
    expect(hooks.push).toHaveBeenCalledWith("/clinical/cases-pilot/ca-7");
  });

  it("đếm ca chưa ai nhận và ca tạm gác trên thanh nhóm, đổi nhóm qua ?tab=", () => {
    queueData.current = response([queueItem({ session_id: "a" }), queueItem({ session_id: "b", patient_name: "Hoàng Lan" })], 2);
    parkedData.current = response([queueItem({ session_id: "p", review_status: "PARKED" })]);

    renderWorkspace();

    expect(screen.getByRole("tab", { name: /Đang chờ\s*2/ })).toHaveAttribute("aria-selected", "true");
    const parkedTab = screen.getByRole("tab", { name: /Tạm gác\s*1/ });
    expect(parkedTab).toHaveAttribute("aria-selected", "false");

    fireEvent.click(parkedTab);
    expect(hooks.replace).toHaveBeenCalledWith("/clinical/queue-pilot?tab=parked", { scroll: false });
  });

  it("\"Chỉ ca của tôi\" là công tắc của nhóm Đang chờ, gắn với ?tab=mine", () => {
    queueData.current = response([queueItem({ session_id: "a" })], 2);
    renderWorkspace();

    const toggle = screen.getByRole("switch", { name: /Chỉ ca của tôi/ });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    fireEvent.click(toggle);
    expect(hooks.replace).toHaveBeenCalledWith("/clinical/queue-pilot?tab=mine", { scroll: false });
  });

  it("ở ?tab=mine chỉ đọc ca của mình và mở ca mà không nhận lại", () => {
    hooks.search.value = "tab=mine";
    mineData.current = response([queueItem({ session_id: "cua-toi", assigned_nurse_id: "nurse-1" })], 1);

    renderWorkspace();

    expect(screen.getByRole("switch", { name: /Chỉ ca của tôi/ })).toHaveAttribute("aria-checked", "true");
    expect(hooks.useSimpleNurseQueue).toHaveBeenCalledWith(expect.objectContaining({ bucket: "QUEUE", mineOnly: true }));

    fireEvent.click(within(rowOf("Đỗ Minh Quân")).getByRole("button", { name: /Mở ca/ }));
    expect(claim.mutate).not.toHaveBeenCalled();
    expect(hooks.push).toHaveBeenCalledWith("/clinical/cases-pilot/cua-toi");
  });

  it("khi hàng đợi tự làm mới, chỉ ca vừa tới được đánh dấu diễn hoạt", () => {
    const first = queueItem({ session_id: "a", patient_name: "Phạm Thu Trang", ai_proposed_esi: 3 });
    const second = queueItem({ session_id: "b", patient_name: "Hoàng Lan", ai_proposed_esi: 4 });
    queueData.current = response([first, second]);

    const { rerenderWorkspace } = renderWorkspace();
    // Lần tải đầu: cả danh sách nổi lên lần lượt, không ca nào là "vừa tới".
    expect(rowOf("Phạm Thu Trang")).not.toHaveAttribute("data-arrived");
    expect(rowOf("Hoàng Lan")).not.toHaveAttribute("data-arrived");

    const arriving = queueItem({ session_id: "c", patient_name: "Bé Nguyễn An", ai_proposed_esi: 2 });
    queueData.current = response([arriving, first, second]);
    rerenderWorkspace();

    expect(rowOf("Bé Nguyễn An")).toHaveAttribute("data-arrived", "true");
    expect(rowOf("Phạm Thu Trang")).not.toHaveAttribute("data-arrived");
    expect(rowOf("Hoàng Lan")).not.toHaveAttribute("data-arrived");

    // Một nhịp làm mới nữa với cùng dữ liệu: không hàng nào diễn hoạt lại.
    queueData.current = response([arriving, first, second]);
    rerenderWorkspace();
    expect(rowOf("Phạm Thu Trang")).not.toHaveAttribute("data-arrived");
  });

  it("hàng đợi trống vẫn nói rõ ca mới sẽ tự tới", () => {
    renderWorkspace();
    expect(screen.getByRole("heading", { name: "Hàng đợi đang trống" })).toBeInTheDocument();
    expect(screen.getByText(/Ca mới sẽ tự hiện lên ngay khi bệnh nhân hoàn tất sàng lọc/)).toBeInTheDocument();
  });
});
