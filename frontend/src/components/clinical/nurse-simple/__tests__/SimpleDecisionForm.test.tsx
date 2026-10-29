import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SimpleDecisionPayload, SimpleNurseActionResponseDTO } from "@/types/simple-nurse";

type MutateOptions = {
  onSuccess?: (result: SimpleNurseActionResponseDTO) => void;
  onError?: (error: Error) => void;
};

const hooks = vi.hoisted(() => ({ useSubmitSimpleDecision: vi.fn() }));

vi.mock("@/queries/useSimpleNurseQueries", () => ({
  useSubmitSimpleDecision: hooks.useSubmitSimpleDecision,
}));

const { SimpleDecisionForm } = await import("@/components/clinical/nurse-simple/SimpleDecisionForm");

function setup(aiEsi: 1 | 2 | 3 | 4 | 5 | null, mutate = vi.fn()) {
  hooks.useSubmitSimpleDecision.mockReturnValue({ mutate, isPending: false, error: null });
  const onDecided = vi.fn();
  const onError = vi.fn();
  render(
    <SimpleDecisionForm sessionId="session-1" caseVersion={7} aiEsi={aiEsi} onDecided={onDecided} onError={onError} />,
  );
  return { mutate, onDecided, onError, user: userEvent.setup() };
}

function reasonLabels(): string[] {
  const group = screen.getByRole("group", { name: "Lý do" });
  return within(group)
    .getAllByRole("radio")
    .map((radio) => radio.closest("label")?.textContent ?? "");
}

afterEach(() => hooks.useSubmitSimpleDecision.mockReset());

describe("bàn quyết định của điều dưỡng", () => {
  it("chọn sẵn mức AI đề xuất và gọi đúng tên việc sắp làm", () => {
    setup(2);

    // Mức AI đề xuất được đánh dấu cho cả trình đọc màn hình.
    expect(screen.getByRole("radio", { name: "ESI 2 · Cấp cứu · AI đề xuất" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "ESI 3 · Khẩn trương" })).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Xác nhận ESI 2" })).toBeInTheDocument();
    expect(reasonLabels()).toEqual(["Dữ liệu phù hợp với phác đồ đã tham chiếu"]);
    expect(screen.getByText(/Giữ nguyên mức AI/)).toBeInTheDocument();
  });

  it("xác nhận gửi đúng mức AI đề xuất, kèm phiên bản ca", async () => {
    const { mutate, user } = setup(2);

    await user.click(screen.getByRole("button", { name: "Xác nhận ESI 2" }));

    await waitFor(() => expect(mutate).toHaveBeenCalledTimes(1));
    const payload: SimpleDecisionPayload = mutate.mock.calls[0][0];
    expect(payload).toEqual({
      version: 7,
      decision_type: "CONFIRM_ESI",
      final_esi: 2,
      reason_code: "MATCHES_PROTOCOL",
      note: null,
    });
  });

  it("chọn mức khác thì nút đổi thành điều chỉnh và lý do đổi theo", async () => {
    const { user } = setup(2);

    await user.click(screen.getByRole("radio", { name: "ESI 3 · Khẩn trương" }));

    expect(screen.getByRole("button", { name: "Điều chỉnh thành ESI 3" })).toBeInTheDocument();
    expect(screen.getByText(/Chốt ít khẩn hơn AI/)).toBeInTheDocument();
    expect(reasonLabels()).toEqual([
      "Nhận định lâm sàng bổ sung",
      "Dữ liệu bệnh nhân cung cấp chưa đủ",
      "Lý do khác (ghi rõ trong ghi chú)",
    ]);
    expect(screen.getByRole("radio", { name: "Nhận định lâm sàng bổ sung" })).toBeChecked();

    await user.click(screen.getByRole("radio", { name: "ESI 1 · Hồi sức" }));
    expect(screen.getByText(/Chốt khẩn hơn AI/)).toBeInTheDocument();
  });

  it("điều chỉnh mà thiếu ghi chú 10 ký tự thì chặn lại, đủ thì gửi", async () => {
    const { mutate, user } = setup(2);

    await user.click(screen.getByRole("radio", { name: "ESI 3 · Khẩn trương" }));
    await user.type(screen.getByLabelText(/Ghi chú cho người bệnh/), "ngắn");
    await user.click(screen.getByRole("button", { name: "Điều chỉnh thành ESI 3" }));

    expect(await screen.findByText("Điều chỉnh ESI cần ghi chú lâm sàng ít nhất 10 ký tự.")).toBeInTheDocument();
    expect(mutate).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText(/Ghi chú cho người bệnh/), " quá, cần khám lại");
    await user.click(screen.getByRole("radio", { name: "Dữ liệu bệnh nhân cung cấp chưa đủ" }));
    await user.click(screen.getByRole("button", { name: "Điều chỉnh thành ESI 3" }));

    await waitFor(() => expect(mutate).toHaveBeenCalledTimes(1));
    expect(mutate.mock.calls[0][0]).toEqual({
      version: 7,
      decision_type: "ADJUST_ESI",
      final_esi: 3,
      reason_code: "INSUFFICIENT_PATIENT_DATA",
      note: "ngắn quá, cần khám lại",
    });
  });

  it("ca AI chưa đủ dữ liệu: không chọn sẵn mức nào và bắt chọn trước khi chốt", async () => {
    const { mutate, user } = setup(null);

    for (const radio of screen.getAllByRole("radio", { name: /^ESI \d/ })) {
      expect(radio).not.toBeChecked();
    }
    await user.click(screen.getByRole("button", { name: "Chốt mức ESI" }));

    expect(await screen.findByText("Chọn một mức ESI trước khi chốt.")).toBeInTheDocument();
    expect(mutate).not.toHaveBeenCalled();

    await user.click(screen.getByRole("radio", { name: "ESI 1 · Hồi sức" }));
    expect(screen.getByRole("button", { name: "Chốt ESI 1" })).toBeInTheDocument();
    expect(screen.getByText(/AI chưa đề xuất mức nào/)).toBeInTheDocument();
    expect(screen.getByText(/bắt buộc, tối thiểu 10 ký tự/)).toBeInTheDocument();
  });

  it("báo cho nơi gọi sau khi backend đã lưu, hoặc khi lưu lỗi", async () => {
    const mutate = vi.fn((_payload: SimpleDecisionPayload, options: MutateOptions) =>
      options.onSuccess?.({ session_id: "session-1", review_status: "HANDED_OFF", case_version: 8, final_esi: 2 }),
    );
    const { onDecided, user } = setup(2, mutate);

    await user.click(screen.getByRole("button", { name: "Xác nhận ESI 2" }));
    await waitFor(() => expect(onDecided).toHaveBeenCalledWith({ finalEsi: 2, decisionType: "CONFIRM_ESI" }));
  });

  it("lỗi từ máy chủ được chuyển cho nơi gọi để báo và tải lại ca", async () => {
    const conflict = new Error("Ca đã được cập nhật bởi người khác. Vui lòng tải lại dữ liệu.");
    const mutate = vi.fn((_payload: SimpleDecisionPayload, options: MutateOptions) => options.onError?.(conflict));
    const { onError, user } = setup(4, mutate);

    await user.click(screen.getByRole("button", { name: "Xác nhận ESI 4" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith(conflict));
  });
});
