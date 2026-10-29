import * as z from "zod";
import { optionalVietnamPhoneSchema } from "@/lib/validations/account-contact.schema";
import type { EhrLiteDTO, EmergencyContactDTO } from "@/types/clinical-profile";

/**
 * ============================================================================
 * ZOD RUNTIME VALIDATION SCHEMAS FOR CLINICAL PROFILE (STRICT ZERO `any`)
 * ============================================================================
 * Đảm bảo tính toàn diện dữ liệu lâm sàng, chống xâm phạm cấu trúc hoặc lỗi
 * kiểu dữ liệu tại runtime khi giao tiếp giữa Next.js 15 & FastAPI Backend.
 */

export const AllergySchema = z.object({
  id: z.string().min(1, "ID dị ứng không được để trống"),
  name: z.string().min(2, "Tên tác nhân dị ứng phải có ít nhất 2 ký tự"),
  type: z.enum(["MEDICATION", "FOOD", "ENVIRONMENT", "OTHER"]),
  severity: z.enum(["HIGH", "MEDIUM", "LOW"]),
});

export const MedicationSchema = z.object({
  id: z.string().min(1, "ID thuốc không được để trống"),
  name: z.string().min(2, "Tên thuốc phải có ít nhất 2 ký tự"),
  dosage: z.string().min(1, "Liều lượng không được để trống (Vd: 75mg)"),
  frequency: z.string().min(1, "Tần suất dùng thuốc không được để trống"),
});

export const EhrLiteSchema: z.ZodType<EhrLiteDTO, EhrLiteDTO> = z
  .object({
    patient_id: z.string().optional(),
    age: z
      .number({
        error: "Tuổi phải là dạng số",
      })
      .int("Tuổi phải là số nguyên")
      .min(0, "Tuổi không được nhỏ hơn 0")
      .max(120, "Tuổi không được vượt quá 120")
      .nullable()
      .optional(),
    gender: z.enum(["MALE", "FEMALE", "OTHER"]).nullable().optional(),
    height_cm: z
      .number({
        error: "Chiều cao phải là dạng số",
      })
      .min(50, "Chiều cao tối thiểu là 50 cm")
      .max(250, "Chiều cao tối đa là 250 cm")
      .nullable()
      .optional(),
    weight_kg: z
      .number({
        error: "Cân nặng phải là dạng số",
      })
      .min(3.0, "Cân nặng tối thiểu là 3.0 kg")
      .max(350.0, "Cân nặng tối đa là 350.0 kg")
      .nullable()
      .optional(),
    blood_type: z.enum(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-", "UNKNOWN"]).nullable().optional(),
    chronic_conditions: z.array(z.string()),
    allergies: z.array(AllergySchema),
    current_medications: z.array(MedicationSchema),
    last_updated: z.string().nullable().optional(),
  });

export const EmergencyContactSchema: z.ZodType<EmergencyContactDTO, EmergencyContactDTO> = z
  .object({
    id: z.string().optional(),
    full_name: z.string().min(2, "Họ tên người liên hệ phải có ít nhất 2 ký tự"),
    relationship: z.enum(["SPOUSE", "PARENT", "CHILD", "SIBLING", "FRIEND", "OTHER"]),
    phone_number: z
      .string()
      .regex(
        /^\+?[0-9\s\-]{9,15}$/,
        "Số điện thoại không hợp lệ (hỗ trợ định dạng Việt Nam & Quốc tế 9-15 số)."
      ),
    is_primary: z.boolean(),
    address: z.string().optional(),
  });

/**
 * Dữ liệu tối thiểu để tạo nhanh hồ sơ một thành viên gia đình.
 * Giữ tuổi ở dạng chuỗi cho form để ô trống hợp lệ trước khi chuyển thành DTO.
 */
export const CreateFamilyProfileFormSchema = z.object({
  fullName: z.string().trim().min(2, "Họ và tên cần có ít nhất 2 ký tự."),
  relationship: z.enum(["SELF", "CHILD", "SPOUSE", "PARENT", "OTHER"]),
  age: z
    .string()
    .trim()
    .refine(
      (value) => value === "" || (/^\d+$/.test(value) && Number(value) <= 120),
      "Nhập tuổi từ 0 đến 120 hoặc để trống."
    ),
  gender: z.enum(["Male", "Female", "Other"]),
  bloodType: z.enum(["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-", "Chưa rõ"]),
  // Cùng một luật số điện thoại Việt Nam với số của chủ tài khoản; để trống là hợp lệ.
  phoneNumber: optionalVietnamPhoneSchema,
});

export type EhrLiteFormValues = z.infer<typeof EhrLiteSchema>;
export type EmergencyContactFormValues = z.infer<typeof EmergencyContactSchema>;
/** Giá trị người dùng gõ vào form (ô số điện thoại trống là chuỗi rỗng). */
export type CreateFamilyProfileFormInput = z.input<typeof CreateFamilyProfileFormSchema>;
/** Giá trị sau khi zod chuẩn hóa (ô trống trở thành null, số đã về dạng 0XXXXXXXXX). */
export type CreateFamilyProfileFormValues = z.output<typeof CreateFamilyProfileFormSchema>;
