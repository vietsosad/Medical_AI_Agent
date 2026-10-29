/**
 * Dữ liệu thuần cho màn hội thoại `/triage-pilot`: biến các dòng tin nhắn đã
 * lưu thành những gì người bệnh thấy, không chạm tới trạng thái phiên.
 */
import type {
  SimpleRecordedFactDTO,
  SimpleRecordedSymptomDTO,
  SimpleTriageDecisionDTO,
  SimpleTriageMessageRowDTO,
  SimpleTriageSessionDetailDTO,
} from "@/types/simple-triage";

/**
 * Lời chào mở đầu chỉ có ở phía giao diện -- `/start` của simple_agent luôn
 * cần một tin nhắn thật (chính triệu chứng đầu tiên), nên không có lượt "mở
 * phiên rỗng" nào để máy chủ trả câu này về.
 */
export const PILOT_GREETING = "Chào bạn! Bạn có đang gặp vấn đề sức khỏe nào cần hỗ trợ không?";

export type QuickReplyKind = "YES_NO" | "SCALE_0_10" | "CONFIRM";

export interface SafetyNotice {
  kind: "EMERGENCY" | "SELF_HARM";
  /** Câu hướng dẫn cố định của bộ sàng lọc cấp cứu, không qua mô hình nào. */
  text: string;
}

export type TranscriptEntry =
  | { kind: "patient"; key: string; content: string; timestamp: string }
  | {
      kind: "agent";
      key: string;
      /** Rỗng khi cả lượt chỉ là câu hướng dẫn an toàn. */
      content: string;
      timestamp: string;
      guarded: boolean;
      safety: SafetyNotice | null;
    };

/**
 * Khóa theo lượt chứ không theo id phiên: tin nhắn đang gửi dùng đúng khóa của
 * dòng thật mà máy chủ sẽ trả về (cùng `turn_index`), nên khi dòng thật tới,
 * React giữ nguyên phần tử -- bong bóng không nháy hay diễn hoạt lại.
 */
export function patientKey(turnIndex: number): string {
  return `patient-${turnIndex}`;
}

function agentKey(turnIndex: number): string {
  return `agent-${turnIndex}`;
}

/**
 * Bộ sàng lọc cấp cứu đặt câu hướng dẫn cố định trước câu trả lời của trợ lý,
 * cách một dòng trống (`_apply_emergency_signal` trong
 * routes_simple_triage.py) -- trừ khi lượt đó đã là kết quả ESI 1/2, vốn
 * mang sẵn câu 115 của riêng nó.
 */
function hasPrependedGuidance(snapshot: Partial<SimpleTriageDecisionDTO>): boolean {
  if (!snapshot.safety_alert) return false;
  const levels = snapshot.matched_esi_levels ?? [];
  return !(snapshot.action === "RETURN_MATCH" && levels.length > 0 && Math.min(...levels) <= 2);
}

const SAFETY_PREFIX = /^Lưu ý an toàn:\s*/;

function splitAgentContent(row: SimpleTriageMessageRowDTO): { safety: SafetyNotice | null; content: string } {
  const snapshot = row.decision_snapshot;
  if (!snapshot.safety_alert || !hasPrependedGuidance(snapshot)) {
    return { safety: null, content: row.content };
  }
  const gap = row.content.indexOf("\n\n");
  const guidance = (gap === -1 ? row.content : row.content.slice(0, gap)).trim();
  const reply = gap === -1 ? "" : row.content.slice(gap + 2).trim();
  // Thẻ đã có tiêu đề "Lưu ý an toàn", bỏ tiền tố để không lặp lại.
  const body = guidance.replace(SAFETY_PREFIX, "");
  return {
    safety: { kind: snapshot.safety_alert.kind, text: body.charAt(0).toUpperCase() + body.slice(1) },
    content: reply,
  };
}

export function buildTranscript(rows: SimpleTriageMessageRowDTO[]): TranscriptEntry[] {
  return rows.map((row) => {
    if (row.sender === "PATIENT") {
      return { kind: "patient", key: patientKey(row.turn_index), content: row.content, timestamp: row.created_at };
    }
    const { safety, content } = splitAgentContent(row);
    return {
      kind: "agent",
      key: agentKey(row.turn_index),
      content,
      timestamp: row.created_at,
      guarded: row.route === "GUARDRAIL",
      safety,
    };
  });
}

function lastAgentRow(session: SimpleTriageSessionDetailDTO | undefined): SimpleTriageMessageRowDTO | undefined {
  return session?.messages.findLast((row) => row.sender === "AGENT");
}

/** Nút trả lời nhanh cho câu hỏi đang chờ -- chỉ khi phiên còn mở. */
export function pendingQuickReply(session: SimpleTriageSessionDetailDTO | undefined): {
  kind: QuickReplyKind;
  questionTargetId: string | null;
} | null {
  if (!session || session.status !== "ACTIVE") return null;
  const lastRow = session.messages.at(-1);
  if (!lastRow || lastRow.sender !== "AGENT") return null;
  const kind = lastRow.decision_snapshot.question_input?.kind;
  if (kind !== "YES_NO" && kind !== "SCALE_0_10" && kind !== "CONFIRM") return null;
  return { kind, questionTargetId: lastRow.decision_snapshot.question_target_id ?? null };
}

export interface RecordedSnapshot {
  symptoms: SimpleRecordedSymptomDTO[];
  facts: SimpleRecordedFactDTO[];
  /** Phiên được ghi trước khi máy chủ có các trường này -- không có gì để hiện. */
  available: boolean;
}

export function recordedSnapshot(session: SimpleTriageSessionDetailDTO | undefined): RecordedSnapshot {
  const snapshot = lastAgentRow(session)?.decision_snapshot;
  if (!snapshot || (snapshot.recorded_facts === undefined && snapshot.recorded_symptoms === undefined)) {
    return { symptoms: [], facts: [], available: false };
  }
  return { symptoms: snapshot.recorded_symptoms ?? [], facts: snapshot.recorded_facts ?? [], available: true };
}

// Chỉ những mã có một cách nói tiếng Việt không thể hiểu sai. Mã khác hiện là
// "Đã ghi nhận" thay vì đoán nghĩa -- nhầm một dữ kiện lâm sàng tệ hơn là không
// nói giá trị.
const CODE_LABELS: Record<string, string> = {
  YES: "Có",
  NO: "Không",
  PRESENT: "Có",
  ABSENT: "Không",
  NONE: "Không có",
  UNKNOWN: "Không rõ",
  NORMAL: "Bình thường",
  SUDDEN: "Đột ngột",
  GRADUAL: "Từ từ",
  UNDER_1_HOUR: "Dưới 1 giờ",
  ONE_TO_24_HOURS: "Từ 1 đến 24 giờ",
  ONE_TO_7_DAYS: "Từ 1 đến 7 ngày",
  OVER_7_DAYS: "Hơn 7 ngày",
  CONSTANT: "Liên tục",
  INTERMITTENT: "Từng cơn",
  WORSENING: "Nặng dần",
  IMPROVING: "Đỡ dần",
  LEFT: "Bên trái",
  RIGHT: "Bên phải",
  BILATERAL: "Cả hai bên",
};

const UNITS: Record<string, string> = {
  "fact_target:temperature": " °C",
  "fact_target:heart_rate": " lần/phút",
  "fact_target:respiratory_rate": " lần/phút",
  "fact_target:spo2": "%",
  "fact_target:systolic_bp": " mmHg",
  "fact_target:diastolic_bp": " mmHg",
  "fact_target:pain_severity": "/10",
  "fact_target:itching_severity": "/10",
  "fact_target:gestational_age_weeks": " tuần",
  "fact_target:contraction_interval_minutes": " phút",
  "fact_target:days_since_last_bowel_movement": " ngày",
  "fact_target:post_trauma_vomiting_count": " lần",
};

export function formatRecordedValue(fact: SimpleRecordedFactDTO): string {
  const { value } = fact;
  if (typeof value === "number" && Number.isFinite(value)) {
    return `${value.toLocaleString("vi-VN")}${UNITS[fact.fact_target_id] ?? ""}`;
  }
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (typeof value === "string") return CODE_LABELS[value.toUpperCase()] ?? "Đã ghi nhận";
  return "Đã ghi nhận";
}

/**
 * Giá trị trong một tiêu chí phác đồ đã khớp. Mã quen thuộc đọc thành tiếng
 * Việt; mã khác giữ nguyên -- ở đây người đọc đang kiểm tra điều kiện thật, giấu
 * mã đi còn tệ hơn một mã khó đọc.
 */
export function formatCriterionValue(value: unknown): string {
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (typeof value === "number") return value.toLocaleString("vi-VN");
  if (typeof value === "string") return CODE_LABELS[value.toUpperCase()] ?? value;
  return String(value);
}

export type TriageStep = 1 | 2 | 3 | 4;

export const TRIAGE_STEPS: ReadonlyArray<{ step: TriageStep; label: string }> = [
  { step: 1, label: "Kể triệu chứng" },
  { step: 2, label: "Trả lời câu hỏi còn thiếu" },
  { step: 3, label: "Xác nhận lại thông tin" },
  { step: 4, label: "Điều dưỡng xem kết quả" },
];

/** Bước hiện tại, suy từ trạng thái thật của phiên -- không phải đồng hồ. */
export function currentStep(session: SimpleTriageSessionDetailDTO | undefined): TriageStep {
  if (!session || session.messages.length === 0) return 1;
  if (session.status === "COMPLETED") return 4;
  const action = lastAgentRow(session)?.action;
  return action === "ASK_CONFIRMATION" ? 3 : 2;
}
