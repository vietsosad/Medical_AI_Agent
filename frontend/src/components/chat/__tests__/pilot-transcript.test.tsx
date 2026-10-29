import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { QuickReplies } from "@/components/chat/pilot/QuickReplies";
import {
  buildTranscript,
  currentStep,
  formatRecordedValue,
  pendingQuickReply,
  recordedSnapshot,
} from "@/components/chat/pilot/pilot-transcript";
import type { SimpleTriageMessageRowDTO, SimpleTriageSessionDetailDTO } from "@/types/simple-triage";

/**
 * Màn hội thoại chỉ được hiển thị những gì máy chủ thật sự nói: câu 115 cố
 * định tách khỏi lời trợ lý, nút trả lời nhanh chỉ khi máy chủ báo dạng câu
 * hỏi, và giá trị đã ghi không bao giờ bị đoán nghĩa.
 */

function row(overrides: Partial<SimpleTriageMessageRowDTO>): SimpleTriageMessageRowDTO {
  return {
    turn_index: 0,
    sender: "AGENT",
    content: "",
    route: "TRIAGE",
    action: "ASK_NEXT",
    question_target_id: null,
    decision_snapshot: {},
    created_at: "2026-10-29T08:00:00Z",
    ...overrides,
  };
}

function session(messages: SimpleTriageMessageRowDTO[], status: "ACTIVE" | "COMPLETED" = "ACTIVE") {
  return { status, messages } as SimpleTriageSessionDetailDTO;
}

const alert = { rule_id: "SA_SCREEN_SYNCOPE_V1", kind: "EMERGENCY" as const, label: "ngất", trigger: "ngất" };

describe("dựng hội thoại", () => {
  it("tách câu hướng dẫn an toàn cố định khỏi câu hỏi của trợ lý", () => {
    const [entry] = buildTranscript([
      row({
        content: "Lưu ý an toàn: bạn có nhắc tới ngất.\n\nHiện giờ mẹ bạn có trả lời được khi gọi không?",
        decision_snapshot: { safety_alert: alert, action: "ASK_NEXT" },
      }),
    ]);

    expect(entry).toMatchObject({
      kind: "agent",
      content: "Hiện giờ mẹ bạn có trả lời được khi gọi không?",
      safety: { kind: "EMERGENCY", text: "Bạn có nhắc tới ngất." },
    });
  });

  it("không tách kết quả ESI 1/2, vốn đã mang câu 115 của riêng nó", () => {
    const content = "Hãy gọi 115 ngay.\n\nĐây không phải chẩn đoán.";
    const [entry] = buildTranscript([
      row({
        content,
        decision_snapshot: { safety_alert: alert, action: "RETURN_MATCH", matched_esi_levels: [1] },
      }),
    ]);

    expect(entry).toMatchObject({ kind: "agent", content, safety: null });
  });

  it("dòng của người bệnh và của trợ lý cùng lượt có khóa khác nhau, ổn định theo lượt", () => {
    const entries = buildTranscript([
      row({ sender: "PATIENT", turn_index: 2, content: "Có" }),
      row({ sender: "AGENT", turn_index: 2, content: "Cảm ơn bạn." }),
    ]);
    expect(entries.map((entry) => entry.key)).toEqual(["patient-2", "agent-2"]);
  });
});

describe("trả lời nhanh", () => {
  it("chỉ hiện cho câu hỏi cuối cùng còn chờ của phiên đang mở", () => {
    const asking = row({ decision_snapshot: { question_input: { kind: "YES_NO" }, question_target_id: "fact_target:x" } });

    expect(pendingQuickReply(session([asking]))).toEqual({ kind: "YES_NO", questionTargetId: "fact_target:x" });
    expect(pendingQuickReply(session([asking], "COMPLETED"))).toBeNull();
    expect(pendingQuickReply(session([asking, row({ sender: "PATIENT" })]))).toBeNull();
    expect(pendingQuickReply(session([row({ decision_snapshot: { question_input: { kind: "NEW_KIND" } } })]))).toBeNull();
  });

  it("gửi đúng câu người bệnh có thể tự gõ", () => {
    const onReply = vi.fn();
    render(
      <QuickReplies kind="YES_NO" questionTargetId={null} disabled={false} onReply={onReply} onWantToAdd={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Không rõ" }));
    expect(onReply).toHaveBeenCalledWith("Không rõ");
  });

  it("thang 0-10 gửi kèm mốc để trợ lý không hiểu nhầm con số", () => {
    const onReply = vi.fn();
    render(
      <QuickReplies
        kind="SCALE_0_10"
        questionTargetId="fact_target:pain_severity"
        disabled={false}
        onReply={onReply}
        onWantToAdd={vi.fn()}
      />,
    );

    expect(screen.getByText("0 · Không đau")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Mức 7 trên 10" }));
    expect(onReply).toHaveBeenCalledWith("7/10");
  });

  it("'Tôi muốn bổ sung' không gửi lượt rỗng mà đưa con trỏ về ô nhập", () => {
    const onReply = vi.fn();
    const onWantToAdd = vi.fn();
    render(
      <QuickReplies kind="CONFIRM" questionTargetId={null} disabled={false} onReply={onReply} onWantToAdd={onWantToAdd} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Tôi muốn bổ sung" }));
    expect(onWantToAdd).toHaveBeenCalledOnce();
    expect(onReply).not.toHaveBeenCalled();
  });
});

describe("khung 'Mình đã ghi nhận'", () => {
  it("đọc từ lượt trả lời mới nhất của trợ lý", () => {
    const recorded = recordedSnapshot(
      session([
        row({ decision_snapshot: { recorded_facts: [], recorded_symptoms: [] } }),
        row({ sender: "PATIENT", turn_index: 1 }),
        row({
          turn_index: 1,
          decision_snapshot: {
            recorded_facts: [{ fact_target_id: "fact_target:temperature", name: "Nhiệt độ cơ thể", value: 38.2 }],
            recorded_symptoms: [{ concept_id: "concept:fever", label: "Sốt" }],
          },
        }),
      ]),
    );

    expect(recorded.available).toBe(true);
    expect(recorded.symptoms).toHaveLength(1);
    expect(formatRecordedValue(recorded.facts[0])).toBe("38,2 °C");
  });

  it("phiên ghi trước khi có tính năng này thì không giả vờ là rỗng", () => {
    expect(recordedSnapshot(session([row({})])).available).toBe(false);
  });

  it("mã không có cách nói chắc chắn thì không đoán nghĩa", () => {
    const fact = { fact_target_id: "fact_target:x", name: "X" };
    expect(formatRecordedValue({ ...fact, value: "YES" })).toBe("Có");
    expect(formatRecordedValue({ ...fact, value: "UNKNOWN" })).toBe("Không rõ");
    expect(formatRecordedValue({ ...fact, value: "SEVERE_DISTRESS" })).toBe("Đã ghi nhận");
    expect(formatRecordedValue({ fact_target_id: "fact_target:pain_severity", name: "Mức độ đau", value: 7 })).toBe("7/10");
  });
});

describe("các bước", () => {
  it("suy từ trạng thái thật của phiên", () => {
    expect(currentStep(undefined)).toBe(1);
    expect(currentStep(session([row({ action: "ASK_NEXT" })]))).toBe(2);
    expect(currentStep(session([row({ action: "ASK_CONFIRMATION" })]))).toBe(3);
    expect(currentStep(session([row({ action: "RETURN_MATCH" })], "COMPLETED"))).toBe(4);
  });
});
