/**
 * Cách đọc dữ liệu của một hồ sơ ca thành chữ cho điều dưỡng.
 *
 * Mọi chuỗi ở đây chỉ diễn đạt lại dữ liệu backend đã trả về
 * (`GET /nurse-simple/cases/{id}`), không suy ra thêm thông tin lâm sàng nào.
 */
import type {
  SimpleNursePatientContactDTO,
  SimpleSatisfiedRequirementDTO,
} from "@/types/simple-nurse";

/** Hồ sơ ca Triage Agent luôn quay về đúng hàng đợi pilot, không đổi theo chế độ. */
export const QUEUE_HREF = "/clinical/queue-pilot";

export function formatClock(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

// EQ/NEQ/GT/GTE/LT/LTE -> ký hiệu toán học dễ đọc, giống hệt helper của phía
// người bệnh (SimplePilotSbarAccordion.tsx) để hai bên đọc cùng một tiêu chí
// bằng cùng một cách viết.
const OPERATOR_SYMBOLS: Record<SimpleSatisfiedRequirementDTO["operator"], string> = {
  EQ: "=",
  NEQ: "≠",
  GT: ">",
  GTE: "≥",
  LT: "<",
  LTE: "≤",
};

function requirementValue(value: SimpleSatisfiedRequirementDTO["actual_value"]): string {
  if (value === null) return "chưa rõ";
  if (typeof value === "boolean") return value ? "Có" : "Không";
  return String(value);
}

/** "Nhiệt độ ≥ 39: 39" -- điều kiện của phác đồ, rồi giá trị người bệnh đã khai. */
export function describeRequirement(requirement: SimpleSatisfiedRequirementDTO): string {
  const symbol = OPERATOR_SYMBOLS[requirement.operator] ?? requirement.operator;
  return `${requirement.name} ${symbol} ${requirementValue(requirement.expected_value)}: ${requirementValue(requirement.actual_value)}`;
}

type PatientProfile = NonNullable<SimpleNursePatientContactDTO["profile"]>;

/** Quan hệ của thẻ hồ sơ được khám so với chủ tài khoản. */
const PROFILE_RELATIONSHIP: Record<string, string> = {
  SELF: "Chính chủ tài khoản",
  CHILD: "Con của chủ tài khoản",
  SPOUSE: "Vợ / chồng của chủ tài khoản",
  PARENT: "Cha / mẹ của chủ tài khoản",
  SIBLING: "Anh / chị / em của chủ tài khoản",
  OTHER: "Người thân của chủ tài khoản",
};

/**
 * Chiều ngược lại: chủ tài khoản (người cầm máy) là ai của người bệnh. Thẻ
 * CHILD nghĩa là người bệnh là con của chủ tài khoản, nên chủ tài khoản là
 * cha hoặc mẹ của người bệnh.
 */
const ACCOUNT_HOLDER_RELATION: Record<string, string> = {
  SELF: "chính người bệnh",
  CHILD: "cha/mẹ của người bệnh",
  SPOUSE: "vợ/chồng của người bệnh",
  PARENT: "con của người bệnh",
  SIBLING: "anh/chị/em của người bệnh",
  OTHER: "người thân của người bệnh",
};

const SUBMITTER_PHRASE: Record<string, string> = {
  SELF: "tự khai báo",
  CHILD: "cha/mẹ khai báo giúp",
  SPOUSE: "vợ/chồng khai báo giúp",
  PARENT: "con khai báo giúp",
  SIBLING: "anh/chị/em khai báo giúp",
  OTHER: "người thân khai báo giúp",
};

export function profileRelationshipLabel(profile: PatientProfile): string {
  return PROFILE_RELATIONSHIP[profile.relationship_type] ?? profile.relationship_type;
}

export function genderLabel(value: string | null): string | null {
  if (!value) return null;
  const normalized = value.trim().toUpperCase();
  if (normalized === "MALE") return "Nam";
  if (normalized === "FEMALE") return "Nữ";
  if (normalized === "OTHER") return "Khác";
  return value;
}

export function patientDisplayName(patient: SimpleNursePatientContactDTO): string {
  return patient.profile?.full_name?.trim() || patient.account.full_name?.trim() || "Chưa rõ danh tính";
}

/** "4 tuổi", "Nữ", "cha/mẹ khai báo giúp" -- chỉ những gì hồ sơ thật sự có. */
export function patientContextParts(patient: SimpleNursePatientContactDTO): string[] {
  const { profile } = patient;
  if (!profile) return ["Phiên ẩn danh"];
  const parts: string[] = [];
  if (profile.age !== null) parts.push(`${profile.age} tuổi`);
  const gender = genderLabel(profile.gender);
  if (gender) parts.push(gender);
  const submitter = SUBMITTER_PHRASE[profile.relationship_type];
  if (submitter) parts.push(submitter);
  return parts;
}

export interface ContactLine {
  key: "account" | "patient" | "emergency";
  name: string;
  /** Người này là ai so với người bệnh. */
  relation: string;
  phone: string;
  callLabel: string;
}

function phoneDigits(phone: string): string {
  return phone.replace(/[^\d+]/g, "");
}

export function telHref(phone: string): string {
  return `tel:${phoneDigits(phone)}`;
}

/**
 * Các số gọi được, theo thứ tự nên gọi trước: người đang cầm máy và gửi phiên
 * này, rồi số riêng của người được khám, rồi người liên hệ khẩn cấp. Số trùng
 * nhau chỉ hiện một lần.
 */
export function contactLines(patient: SimpleNursePatientContactDTO): ContactLine[] {
  const { account, profile } = patient;
  const lines: ContactLine[] = [];
  const seen = new Set<string>();
  const push = (line: ContactLine) => {
    const digits = phoneDigits(line.phone);
    if (!digits || seen.has(digits)) return;
    seen.add(digits);
    lines.push(line);
  };

  if (account.phone) {
    const isSelf = profile?.relationship_type === "SELF";
    push({
      key: "account",
      name: account.full_name?.trim() || "Chủ tài khoản",
      relation: profile ? (ACCOUNT_HOLDER_RELATION[profile.relationship_type] ?? "người thân của người bệnh") : "người gửi phiên",
      phone: account.phone,
      callLabel: profile === null ? "Gọi người gửi phiên" : isSelf ? "Gọi người bệnh" : "Gọi người nhà",
    });
  }
  if (profile?.phone_number) {
    push({
      key: "patient",
      name: profile.full_name,
      relation: "người bệnh",
      phone: profile.phone_number,
      callLabel: "Gọi người bệnh",
    });
  }
  if (profile?.emergency_contact_phone) {
    push({
      key: "emergency",
      name: profile.emergency_contact_name?.trim() || "Người liên hệ khẩn cấp",
      relation: "liên hệ khẩn cấp",
      phone: profile.emergency_contact_phone,
      callLabel: "Gọi liên hệ khẩn cấp",
    });
  }
  return lines;
}
