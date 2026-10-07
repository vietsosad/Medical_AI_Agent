/**
 * ============================================================================
 * CLINICAL DATA TYPES & DTO CONTRACTS (STRICT TYPED - ZERO `any` TOLERANCE)
 * ============================================================================
 * Định nghĩa chuẩn kiểu dữ liệu lâm sàng cho Hồ sơ Bệnh nhân (EHR Lite)
 * và Danh sách Liên hệ Khẩn cấp (Emergency SOS Contacts) trong AI20K Engine.
 */

export type GenderType = "MALE" | "FEMALE" | "OTHER";

export type BloodType =
  | "A+"
  | "A-"
  | "B+"
  | "B-"
  | "O+"
  | "O-"
  | "AB+"
  | "AB-"
  | "UNKNOWN";

export type AllergyType = "MEDICATION" | "FOOD" | "ENVIRONMENT" | "OTHER";

export type AllergySeverity = "HIGH" | "MEDIUM" | "LOW";

export type RelationshipType =
  | "SPOUSE"
  | "PARENT"
  | "CHILD"
  | "SIBLING"
  | "FRIEND"
  | "OTHER";

export interface AllergyDTO {
  id: string;
  name: string;
  type: AllergyType;
  severity: AllergySeverity;
}

export interface MedicationDTO {
  id: string;
  name: string;
  dosage: string;
  frequency: string;
}

export interface EhrLiteDTO {
  patient_id?: string;
  age?: number | null;
  gender?: GenderType | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  blood_type?: BloodType | null;
  chronic_conditions: string[];
  allergies: AllergyDTO[];
  current_medications: MedicationDTO[];
  last_updated?: string | null;
}

export interface EmergencyContactDTO {
  id?: string;
  full_name: string;
  relationship: RelationshipType;
  phone_number: string;
  is_primary: boolean;
  address?: string;
}

export type BmiCategory = "UNDERWEIGHT" | "NORMAL" | "OVERWEIGHT" | "OBESE";

export interface BmiResultDTO {
  bmi: number;
  category: BmiCategory;
  colorClass: string;
  advice: string;
}
