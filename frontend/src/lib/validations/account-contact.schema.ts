import { z } from "zod";

/**
 * ============================================================================
 * KIỂM ĐỊNH SỐ ĐIỆN THOẠI VIỆT NAM (ĐỒNG BỘ VỚI BACKEND)
 * ============================================================================
 * Giữ đúng cùng luật với `normalize_vietnam_phone` trong
 * `src/models/auth_schemas.py`, để người dùng thấy lỗi ngay trên form thay vì
 * phải chờ một vòng gọi API. Máy chủ vẫn là nơi kiểm định sau cùng.
 */

/** Di động 10 số (03/05/07/08/09) hoặc cố định 11 số (02). */
const VN_PHONE_PATTERN = /^(0[35789]\d{8}|02\d{9})$/;

/** Chặn payload rác trước khi chuẩn hóa: "+84 (024) 3936-1414" vẫn nằm dưới ngưỡng này. */
export const MAX_RAW_PHONE_LENGTH = 24;

/**
 * Quy các cách viết thông dụng (khoảng trắng, dấu chấm, gạch nối, dấu ngoặc,
 * tiền tố +84 / 84) về một dạng nội địa duy nhất bắt đầu bằng số 0.
 */
export function normalizeVietnamPhone(rawValue: string): string {
  const digitsOnly = rawValue.trim().replace(/[\s.\-()]/g, "");
  if (digitsOnly.startsWith("+84")) return `0${digitsOnly.slice(3)}`;
  if (digitsOnly.startsWith("84") && digitsOnly.length >= 11) return `0${digitsOnly.slice(2)}`;
  return digitsOnly;
}

export const vietnamPhoneSchema = z
  .string()
  .trim()
  .max(MAX_RAW_PHONE_LENGTH, "Số điện thoại quá dài. Vui lòng nhập số điện thoại Việt Nam hợp lệ.")
  .refine((value) => /^\+?[\d\s.\-()]+$/.test(value), {
    message: "Số điện thoại chỉ được chứa chữ số và các ký tự phân cách thông dụng.",
  })
  .transform(normalizeVietnamPhone)
  .refine((value) => VN_PHONE_PATTERN.test(value), {
    message:
      "Số điện thoại không đúng định dạng Việt Nam (ví dụ 0912345678 hoặc +84912345678).",
  });

/** Ô nhập để trống nghĩa là gỡ bỏ số điện thoại đang lưu. */
export const optionalVietnamPhoneSchema = z
  .string()
  .trim()
  .transform((value) => (value.length === 0 ? null : value))
  .pipe(vietnamPhoneSchema.nullable());

/** Hiển thị 0912 345 678 cho dễ đọc, dữ liệu lưu vẫn là dạng liền. */
export function formatVietnamPhoneForDisplay(phoneNumber: string): string {
  const normalized = normalizeVietnamPhone(phoneNumber);
  if (!VN_PHONE_PATTERN.test(normalized)) return phoneNumber;
  if (normalized.length === 10) {
    return `${normalized.slice(0, 4)} ${normalized.slice(4, 7)} ${normalized.slice(7)}`;
  }
  return `${normalized.slice(0, 3)} ${normalized.slice(3, 7)} ${normalized.slice(7)}`;
}
