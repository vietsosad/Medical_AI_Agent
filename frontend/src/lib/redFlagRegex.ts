/**
 * INSTANT RED-FLAG INTERCEPTOR ENGINE (<50MS REFLEX SHIELD)
 * Lớp bảo vệ phản xạ siêu tốc tại Frontend, can thiệp trước khi gọi AI LLM.
 * Tuân thủ quy định Dual-layer Medical Safety & Reflex Overlay trong AGENTS.md / TRIAGE_AGENT_SOLUTION_DESIGN.md
 */

export interface RedFlagResult {
  isRedFlag: boolean;
  matchedTerm?: string;
  category?: string;
  reason?: string;
}

/**
 * Danh sách các từ khóa rủi ro đe dọa sinh mạng bằng tiếng Việt & tiếng Anh (ESI Level 1 / 2)
 */
export const RED_FLAG_KEYWORDS = [
  // Tiếng Việt - Triệu chứng tim mạch / Mạch vành cấp
  "đau ngực",
  "đau thắt ngực",
  "nghẹn ngực",
  "nặng ngực",
  "đau tức ngực",
  "nhồi máu",
  "stent bị",
  "tê ngực",

  // Tiếng Việt - Hô hấp cấp
  "khó thở",
  "nghẹt thở",
  "hụt hơi trầm trọng",
  "ngạt thở",
  "tím tái",

  // Tiếng Việt - Thần kinh & Đột quỵ
  "mèo miệng",
  "méo miệng",
  "nói ngọ ngọe",
  "nói ngọng",
  "đột quỵ",
  "bất tỉnh",
  "ngất xỉu",
  "tê liệt nứa người",
  "tê nhăn tay chân",

  // Tiếng Việt - Mất máu / Chấn thương cấp
  "chảy máu không cầm",
  "xuất huyết dữ dội",
  "mất máu",
  "vã mồ hôi lạnh ngắt",

  // Tiếng Anh - Emergency Equivalents
  "chest pain",
  "shortness of breath",
  "heart attack",
  "stroke",
  "severe bleeding",
  "unconscious",
  "faint",
  "facial drooping",
  "slurred speech",
  "can not breath",
  "cannot breathe",
  "cold sweats",
];

// Tạo Regex tinh giản cao độ, không phân biệt hoa thường để thực thi <5ms
const RED_FLAG_REGEX = new RegExp(
  `(${RED_FLAG_KEYWORDS.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`,
  "i"
);

/**
 * Kiểm thử lớp lọc tất định: phát hiện sớm rủi ro đe dọa tính mạng
 * @param input Lời văn của người dùng trong ô chat hoặc mô tả option được tick
 */
export function checkIsRedFlag(input?: string): RedFlagResult {
  if (!input || typeof input !== "string") {
    return { isRedFlag: false };
  }

  if (/\b(là gì|nghĩa là gì|có nghĩa gì|giải thích|tìm hiểu|ví dụ)\b/i.test(input)) {
    return { isRedFlag: false };
  }

  const match = input.match(RED_FLAG_REGEX);
  if (match) {
    const matchedTerm = match[0];
    const matchIndex = match.index ?? 0;
    const prefix = input.slice(Math.max(0, matchIndex - 24), matchIndex).trim();
    const isNegated =
      !matchedTerm.toLowerCase().startsWith("không ") &&
      /(?:không|chưa|không bị|không có|không thấy)\s*$/i.test(prefix);
    if (isNegated) return { isRedFlag: false };

    return {
      isRedFlag: true,
      matchedTerm,
      reason: `Phát hiện tín hiệu cần gửi tới bộ kiểm tra an toàn phía máy chủ: "${matchedTerm}".`,
    };
  }

  return { isRedFlag: false };
}
