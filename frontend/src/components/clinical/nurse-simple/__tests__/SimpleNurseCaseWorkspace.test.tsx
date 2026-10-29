import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  SimpleClaimPayload,
  SimpleDecisionPayload,
  SimpleNurseActionResponseDTO,
  SimpleNurseCaseDetailDTO,
} from "@/types/simple-nurse";

type MutateOptions = {
  onSuccess?: (result: SimpleNurseActionResponseDTO) => void;
  onError?: (error: Error) => void;
};

const hooks = vi.hoisted(() => ({
  useSimpleNurseCase: vi.fn(),
  useClaimSimpleCase: vi.fn(),
  useSubmitSimpleDecision: vi.fn(),
  useSimpleCaseCareTeamThread: vi.fn(),
  useSendSimpleCaseMessage: vi.fn(),
  useMarkSimpleCaseMessagesRead: vi.fn(),
  useSimpleCaseRealtime: vi.fn(),
}));
const nav = vi.hoisted(() => ({ push: vi.fn() }));
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
const auth = vi.hoisted(() => ({ userId: "nurse-1" }));

vi.mock("@/queries/useSimpleNurseQueries", () => hooks);
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: nav.push }) }));
vi.mock("sonner", () => ({ toast }));
vi.mock("@/store/useAuthStore", () => ({
  useAuthStore: <T,>(selector: (state: { user: { id: string } }) => T) => selector({ user: { id: auth.userId } }),
}));
vi.mock("@/lib/realtime/useClinicalSocket", () => ({ useClinicalSocket: () => ({ status: "open" }) }));

const { SimpleNurseCaseWorkspace } = await import("@/components/clinical/nurse-simple/SimpleNurseCaseWorkspace");

function caseDetail(overrides: Partial<SimpleNurseCaseDetailDTO> = {}): SimpleNurseCaseDetailDTO {
  return {
    session_id: "session-1",
    patient: {
      account: { full_name: "Nguyễn Thị Mai", email: "mai@example.com", phone: "0912 000 111" },
      profile: {
        full_name: "Nguyễn An",
        relationship_type: "CHILD",
        is_primary: false,
        age: 4,
        gender: "FEMALE",
        phone_number: null,
        blood_type: "A+",
        chronic_conditions: [],
        allergies: ["Ibuprofen"],
        emergency_contact_name: null,
        emergency_contact_phone: null,
      },
    },
    initial_message: "Con tôi sốt 39 độ, li bì từ sáng.",
    final_action: "RETURN_MATCH",
    final_message: "Bạn nên đưa bé đi khám ngay.",
    ai_proposed_esi: 2,
    matched_esi_levels: [2],
    final_concepts: [],
    session_status: "COMPLETED",
    attention_required: false,
    attention_reason: null,
    attention_raised_at: null,
    review_status: "ASSIGNED",
    assigned_nurse_id: "nurse-1",
    case_version: 5,
    final_esi: null,
    decision_type: null,
    decision_reason_code: null,
    decision_note: null,
    sbar: {
      situation: "Triệu chứng của bé: sốt, li bì.",
      background: "Thông tin đã ghi nhận: Nhiệt độ: 39.",
      assessment: "AI đề xuất mức ESI: 2.",
      recommendation: "Đề nghị điều dưỡng xác nhận hoặc điều chỉnh mức ESI trước khi đóng ca.",
      citations: [
        {
          atom_id: "ATOM-FEVER-LETHARGY",
          decision_point: "DP-B",
          criteria_text: "Sốt cao kèm thay đổi ý thức",
          status: "SATISFIED",
          satisfied_requirements: [
            { fact_target_id: "temp", name: "Nhiệt độ", operator: "GTE", expected_value: 39, actual_value: 39 },
            { fact_target_id: "lethargy", name: "Li bì", operator: "EQ", expected_value: true, actual_value: true },
          ],
        },
        {
          atom_id: "ATOM-NECK",
          decision_point: null,
          criteria_text: "Cổ cứng",
          status: "MISSING_INFO",
          satisfied_requirements: [],
        },
        {
          atom_id: "ATOM-RASH",
          decision_point: null,
          criteria_text: "Ban xuất huyết",
          status: "CONTRADICTED",
          satisfied_requirements: [],
        },
      ],
    },
    messages: [
      { turn_index: 0, sender: "PATIENT", content: "Con tôi sốt 39 độ, li bì từ sáng.", created_at: "2026-10-29T08:12:00Z" },
      { turn_index: 0, sender: "AGENT", content: "Bé có còn **tỉnh táo** không?", created_at: "2026-10-29T08:12:30Z" },
    ],
    ...overrides,
  };
}

function setup(
  data: SimpleNurseCaseDetailDTO | undefined,
  options: {
    userId?: string;
    claimMutate?: ReturnType<typeof vi.fn>;
    decisionMutate?: ReturnType<typeof vi.fn>;
    isError?: boolean;
    error?: Error | null;
  } = {},
) {
  auth.userId = options.userId ?? "nurse-1";
  const refetch = vi.fn();
  const claimMutate = options.claimMutate ?? vi.fn();
  hooks.useSimpleNurseCase.mockReturnValue({
    data,
    isLoading: data === undefined && !options.isError,
    isError: options.isError ?? false,
    error: options.error ?? null,
    refetch,
  });
  hooks.useClaimSimpleCase.mockReturnValue({ mutate: claimMutate, isPending: false, variables: undefined });
  hooks.useSubmitSimpleDecision.mockReturnValue({
    mutate: options.decisionMutate ?? vi.fn(),
    isPending: false,
    error: null,
  });
  hooks.useSimpleCaseCareTeamThread.mockReturnValue({
    data: { session_id: "session-1", unread_count: 0, messages: [] },
    isLoading: false,
    isError: false,
  });
  hooks.useSendSimpleCaseMessage.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });
  hooks.useMarkSimpleCaseMessagesRead.mockReturnValue({ mutate: vi.fn() });

  render(<SimpleNurseCaseWorkspace sessionId="session-1" />);
  return { refetch, claimMutate, user: userEvent.setup() };
}

afterEach(() => {
  Object.values(hooks).forEach((hook) => hook.mockReset());
  nav.push.mockReset();
  toast.success.mockReset();
  toast.error.mockReset();
});

describe("hồ sơ ca: danh tính và đường liên lạc", () => {
  it("nói rõ ai là người bệnh, ai đang cầm máy, và gọi được ngay", () => {
    setup(caseDetail());

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Nguyễn An · 4 tuổi · Nữ · cha/mẹ khai báo giúp");
    expect(screen.getByText("· cha/mẹ của người bệnh", { exact: false })).toBeInTheDocument();
    const call = screen.getByRole("link", { name: /Gọi người nhà: Nguyễn Thị Mai/ });
    expect(call).toHaveAttribute("href", "tel:0912000111");
    // Dị ứng là thông tin phải thấy được ngay, không nằm lẫn trong một câu dài.
    expect(within(screen.getByRole("region", { name: "Hồ sơ sức khỏe" })).getByText("Ibuprofen")).toBeInTheDocument();
  });
});

describe("hồ sơ ca: giữ ca, tạm gác, trả lại", () => {
  it("ca của mình: hiện trạng thái và hai việc tạm gác, trả lại", () => {
    setup(caseDetail());

    expect(screen.getByText("Bạn đang xử lý ca này")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Tạm gác/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Trả lại hàng đợi/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Xác nhận ESI 2" })).toBeInTheDocument();
  });

  it("trả lại hàng đợi gửi kèm phiên bản ca rồi quay về hàng đợi", async () => {
    const claimMutate = vi.fn((_payload: SimpleClaimPayload, options: MutateOptions) =>
      options.onSuccess?.({ session_id: "session-1", review_status: "WAITING_REVIEW", case_version: 6 }),
    );
    const { user } = setup(caseDetail(), { claimMutate });

    await user.click(screen.getByRole("button", { name: /Trả lại hàng đợi/ }));

    expect(claimMutate.mock.calls[0][0]).toEqual({ version: 5, action: "RELEASE" });
    expect(toast.success).toHaveBeenCalledWith("Đã trả ca về hàng đợi");
    expect(nav.push).toHaveBeenCalledWith("/clinical/queue-pilot");
  });

  it("tạm gác bắt buộc ghi lý do ít nhất 10 ký tự", async () => {
    const { claimMutate, user } = setup(caseDetail());

    await user.click(screen.getByRole("button", { name: /Tạm gác/ }));
    const reason = screen.getByLabelText(/Lý do tạm gác lại/);
    await user.type(reason, "thiếu");
    await user.click(screen.getByRole("button", { name: /Xác nhận tạm gác/ }));

    expect(await screen.findByText("Lý do tạm gác cần ít nhất 10 ký tự.")).toBeInTheDocument();
    expect(claimMutate).not.toHaveBeenCalled();

    await user.type(reason, " số đo nhiệt độ, cần gọi lại");
    await user.click(screen.getByRole("button", { name: /Xác nhận tạm gác/ }));

    await waitFor(() => expect(claimMutate).toHaveBeenCalledTimes(1));
    expect(claimMutate.mock.calls[0][0]).toEqual({
      version: 5,
      action: "PARK",
      reason: "thiếu số đo nhiệt độ, cần gọi lại",
    });
  });

  it("ca chưa ai nhận: khoá bàn quyết định cho tới khi nhận ca", async () => {
    const { claimMutate, user } = setup(caseDetail({ assigned_nurse_id: null, review_status: "WAITING_REVIEW" }));

    expect(screen.getByText("Chưa ai nhận ca")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Xác nhận ESI/ })).not.toBeInTheDocument();
    expect(screen.getByText(/để mở bàn quyết định/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Nhận ca này/ }));
    expect(claimMutate.mock.calls[0][0]).toEqual({ version: 5, action: "CLAIM" });
  });

  it("ca y tá khác đang giữ: đọc được hồ sơ nhưng không ra quyết định, không nhắn tin", () => {
    setup(caseDetail({ assigned_nurse_id: "nurse-2" }));

    expect(screen.getByText("Y tá khác đang phụ trách")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Trả lại hàng đợi/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Xác nhận ESI/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Mở khung nhắn tin/ })).not.toBeInTheDocument();
  });

  it("ca đang tạm gác: ai cũng đưa lại được hàng đợi", async () => {
    const { claimMutate, user } = setup(caseDetail({ review_status: "PARKED", assigned_nurse_id: "nurse-2" }));

    expect(screen.getByText("Ca đang được tạm gác")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Đẩy lại hàng đợi/ }));
    expect(claimMutate.mock.calls[0][0]).toEqual({ version: 5, action: "RESTORE" });
  });

  it("xung đột phiên bản: báo rõ và tải lại ca thay vì giữ dữ liệu cũ", async () => {
    const claimMutate = vi.fn((_payload: SimpleClaimPayload, options: MutateOptions) =>
      options.onError?.(new Error("Ca đã được cập nhật bởi người khác. Vui lòng tải lại dữ liệu.")),
    );
    const { refetch, user } = setup(caseDetail(), { claimMutate });

    await user.click(screen.getByRole("button", { name: /Trả lại hàng đợi/ }));

    expect(toast.error).toHaveBeenCalledWith("Ca vừa được cập nhật ở nơi khác", expect.anything());
    expect(refetch).toHaveBeenCalled();
    expect(nav.push).not.toHaveBeenCalled();
  });

  it("lỗi khác: báo đúng việc nào không làm được, kèm lời của máy chủ", async () => {
    const claimMutate = vi.fn((_payload: SimpleClaimPayload, options: MutateOptions) =>
      options.onError?.(new Error("Ca này đã có người khác nhận.")),
    );
    const { user } = setup(caseDetail({ assigned_nurse_id: null, review_status: "WAITING_REVIEW" }), { claimMutate });

    await user.click(screen.getByRole("button", { name: /Nhận ca này/ }));

    expect(toast.error).toHaveBeenCalledWith("Chưa nhận được ca", { description: "Ca này đã có người khác nhận." });
  });
});

describe("hồ sơ ca: cảnh báo và tài liệu đối chiếu", () => {
  it("cờ cần xem ngay là cảnh báo khẩn, không phải mức ESI, và có nút gọi", () => {
    setup(
      caseDetail({
        attention_required: true,
        attention_reason: "khó thở dữ dội",
        attention_raised_at: "2026-10-29T08:15:00Z",
        session_status: "ACTIVE",
      }),
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Cần xem ngay");
    expect(alert).toHaveTextContent("khó thở dữ dội");
    expect(alert).toHaveTextContent("Đây không phải mức ESI.");
    expect(alert).toHaveTextContent("Người bệnh vẫn đang trò chuyện với trợ lý.");
    const call = within(alert).getByRole("link", { name: /Gọi người nhà/ });
    expect(call).toHaveAttribute("href", "tel:0912000111");
    expect(call).toHaveClass("ring-pulse");
  });

  it("ca đã chốt thì cờ chỉ còn là một dòng lịch sử, không còn là cảnh báo", () => {
    setup(
      caseDetail({
        attention_required: true,
        attention_reason: "khó thở dữ dội",
        review_status: "HANDED_OFF",
        final_esi: 2,
        decision_type: "CONFIRM_ESI",
      }),
    );

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText(/Ca này từng được gắn cờ/)).toBeInTheDocument();
  });

  it("SBAR được trình bày là tài liệu cần đối chiếu, không phải chẩn đoán", () => {
    setup(caseDetail());

    const sbar = screen.getByRole("region", { name: "Tóm tắt SBAR" });
    expect(sbar).toHaveTextContent("Tạo tự động từ cuộc hội thoại · cần đối chiếu");
    expect(sbar).toHaveTextContent("chưa phải chẩn đoán");
    expect(within(sbar).getByText("S · Tình huống")).toBeInTheDocument();
    expect(within(sbar).getByText("R · Khuyến nghị")).toBeInTheDocument();
  });

  it("tiêu chí phác đồ ghi trạng thái bằng chữ và giá trị người bệnh đã khai", () => {
    setup(caseDetail());

    const criteria = screen.getByRole("region", { name: "Tiêu chí phác đồ đã xét" });
    expect(within(criteria).getByText("Khớp:")).toBeInTheDocument();
    expect(within(criteria).getByText("Thiếu thông tin:")).toBeInTheDocument();
    expect(within(criteria).getByText("Không khớp:")).toBeInTheDocument();
    expect(within(criteria).getByText("Nhiệt độ ≥ 39: 39")).toBeInTheDocument();
    expect(within(criteria).getByText("Li bì = Có: Có")).toBeInTheDocument();
    expect(criteria).toHaveTextContent("ATOM-FEVER-LETHARGY");
  });

  it("hội thoại gốc giữ nguyên lời người bệnh và định dạng lời trợ lý", () => {
    setup(caseDetail());

    const transcript = screen.getByRole("region", { name: "Hội thoại gốc" });
    expect(within(transcript).getByText("Con tôi sốt 39 độ, li bì từ sáng.")).toBeInTheDocument();
    expect(within(transcript).getByText("tỉnh táo").tagName).toBe("STRONG");
  });
});

describe("hồ sơ ca: chốt quyết định", () => {
  it("ca đã đóng chỉ còn đọc lại quyết định", () => {
    setup(
      caseDetail({
        review_status: "HANDED_OFF",
        final_esi: 3,
        decision_type: "ADJUST_ESI",
        decision_reason_code: "ADDITIONAL_CLINICAL_JUDGMENT",
        decision_note: "Đưa bé đến khoa cấp cứu nhi ngay.",
      }),
    );

    const desk = screen.getByRole("complementary", { name: "Quyết định của điều dưỡng" });
    expect(within(desk).getByText("ESI 3 · Khẩn trương")).toBeInTheDocument();
    expect(within(desk).getByText("Nhận định lâm sàng bổ sung")).toBeInTheDocument();
    expect(within(desk).getByText("Đưa bé đến khoa cấp cứu nhi ngay.")).toBeInTheDocument();
    expect(within(desk).queryByRole("radio")).not.toBeInTheDocument();
    expect(screen.getByText("Đã chốt ESI 3 · Khẩn trương")).toBeInTheDocument();
  });

  it("chốt xong thì xác nhận rõ ràng trước, rồi mới quay về hàng đợi", async () => {
    const decisionMutate = vi.fn((payload: SimpleDecisionPayload, options: MutateOptions) =>
      options.onSuccess?.({
        session_id: "session-1",
        review_status: "HANDED_OFF",
        case_version: 6,
        final_esi: payload.final_esi,
      }),
    );
    const { user } = setup(caseDetail(), { decisionMutate });

    await user.click(screen.getByRole("button", { name: "Xác nhận ESI 2" }));

    expect(await screen.findByText("Đã lưu quyết định, ca đã đóng")).toBeInTheDocument();
    expect(toast.success).toHaveBeenCalledWith("Đã chốt ESI 2 · Cấp cứu", expect.anything());
    expect(nav.push).not.toHaveBeenCalled();
    await waitFor(() => expect(nav.push).toHaveBeenCalledWith("/clinical/queue-pilot"), { timeout: 3000 });
  });

  it("ca AI chưa đủ dữ liệu vẫn chốt được, nhưng không có mức nào chọn sẵn", () => {
    setup(caseDetail({ ai_proposed_esi: null, matched_esi_levels: [], final_action: "RETURN_INCOMPLETE" }));

    const desk = screen.getByRole("complementary", { name: "Quyết định của điều dưỡng" });
    expect(within(desk).getByText("Chưa đủ dữ liệu để đề xuất")).toBeInTheDocument();
    expect(within(desk).getByRole("button", { name: "Chốt mức ESI" })).toBeInTheDocument();
    for (const radio of within(desk).getAllByRole("radio", { name: /^ESI \d/ })) {
      expect(radio).not.toBeChecked();
    }
  });
});

describe("hồ sơ ca: tải dữ liệu", () => {
  it("lần tải đầu hỏng thì báo lỗi kèm lối thử lại", async () => {
    const { refetch, user } = setup(undefined, {
      isError: true,
      error: new Error("Không tìm thấy ca simple_agent đã hoàn tất để thẩm định."),
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Không thể tải ca này.");
    await user.click(screen.getByRole("button", { name: /Thử tải lại/ }));
    expect(refetch).toHaveBeenCalled();
  });

  it("một nhịp làm mới hỏng không xoá hồ sơ đang đọc", () => {
    setup(caseDetail(), { isError: true, error: new Error("Không thể kết nối tới máy chủ.") });

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Nguyễn An");
    expect(screen.getByText(/Không tải được dữ liệu mới nhất của ca/)).toBeInTheDocument();
  });
});
