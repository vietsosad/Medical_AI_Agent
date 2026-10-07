export type EsiLevel = 1 | 2 | 3 | 4 | 5;

export type ReviewStatus =
  | "WAITING_REVIEW"
  | "ASSIGNED"
  | "IN_REVIEW"
  | "NEEDS_MORE_INFO"
  | "SPECIALIST_REVIEW_REQUIRED"
  | "TRIAGE_DECIDED"
  | "HANDED_OFF";

export type ObservationKind =
  | "HEART_RATE"
  | "BLOOD_PRESSURE"
  | "RESPIRATORY_RATE"
  | "SPO2"
  | "TEMPERATURE"
  | "CONSCIOUSNESS";

export type ObservationAvailability =
  | "MEASURED"
  | "UNKNOWN"
  | "NOT_MEASURED"
  | "NOT_APPLICABLE";

export type ObservationSource =
  | "PATIENT_REPORTED"
  | "NURSE_MEASURED"
  | "DEVICE"
  | "UNKNOWN";

export interface NurseIdentityDTO {
  id: string;
  name: string;
}

export interface DataCompletenessDTO {
  is_complete: boolean;
  missing_fields: string[];
}

export interface NurseQueueItemDTO {
  case_id: string;
  patient_name: string;
  masked_patient_label: string;
  age: number | null;
  sex: string | null;
  chief_complaint: string;
  ai_recommended_esi: EsiLevel | null;
  red_flags: string[];
  is_red_flag: boolean;
  waiting_since: string;
  wait_time_seconds: number;
  review_status: ReviewStatus;
  assignee: NurseIdentityDTO | null;
  data_completeness: DataCompletenessDTO;
  case_version: number;
  alert_acknowledged: boolean;
  unread_count: number;
  last_message_at: string | null;
}

export type TranscriptSender = "PATIENT" | "AI_AGENT" | "SYSTEM_SHIELD" | "NURSE";

export interface ClinicalTranscriptMessageDTO {
  id: string;
  sender: TranscriptSender;
  content: string;
  created_at: string;
  sender_name: string | null;
  read_at: string | null;
}

export type MessagePriority = "RED_FLAG" | "URGENT" | "NORMAL";

export interface InboxItemDTO {
  case_id: string;
  patient_name: string;
  age: number | null;
  sex: string | null;
  chief_complaint: string;
  ai_recommended_esi: EsiLevel | null;
  is_red_flag: boolean;
  priority: MessagePriority;
  /** Trích ngắn tin gần nhất; hồ sơ đầy đủ vẫn sau lớp kiểm quyền. */
  preview: string;
  unread_count: number;
  last_message_at: string | null;
  assignee: NurseIdentityDTO | null;
  case_version: number;
}

export interface InboxResponseDTO {
  items: InboxItemDTO[];
  total_unread: number;
  urgent_unread: number;
}

export interface CaseMessagesResponseDTO {
  case_id: string;
  messages: ClinicalTranscriptMessageDTO[];
  unread_count: number;
}

export interface EmergencyContactPersonDTO {
  label: string;
  full_name: string | null;
  relationship: string | null;
  /** null nghĩa là chưa khai báo — hiển thị "Chưa cập nhật", không bịa số. */
  phone: string | null;
}

export interface EmergencyContactResponseDTO {
  case_id: string;
  contacts: EmergencyContactPersonDTO[];
  expires_at: string;
}

export interface NurseQueueResponseDTO {
  items: NurseQueueItemDTO[];
  summary: {
    total_waiting: number;
    urgent_count: number;
    mine_count: number;
    specialist_count?: number;
    longest_wait_seconds: number;
  };
  sla_target_minutes: number | null;
}

export interface ClinicalObservationInputDTO {
  kind: ObservationKind;
  value: string | null;
  unit: string | null;
  availability: ObservationAvailability;
  source: ObservationSource;
  measured_at: string | null;
}

export interface ClinicalObservationDTO extends ClinicalObservationInputDTO {
  id: string;
  recorded_by: NurseIdentityDTO;
  recorded_at: string;
}

export interface NurseCaseDetailDTO extends NurseQueueItemDTO {
  triage_status: string;
  final_esi: EsiLevel | null;
  observations: ClinicalObservationDTO[];
  risk_context: {
    age: number | null;
    gender: string | null;
    height_cm: number | null;
    weight_kg: number | null;
    bmi: number | null;
    blood_type: string | null;
    chronic_conditions: string[];
    allergies: string[];
    active_medications: string[];
    pregnancy_status: string | null;
    patient_reported_vitals: Record<string, string | number>;
    patient_reported_vitals_source: string | null;
    patient_reported_vitals_measured_at: string | null;
    vital_signs_status: string;
    ehr_confirmation_status: string;
    ehr_profile_updated_at: string | null;
    patient_context_note: string | null;
  };
  sbar: {
    situation: string | null;
    background: string | null;
    assessment: string | null;
    recommendation: string | null;
  };
  citations: Array<{
    code: string;
    title: string | null;
    excerpt: string | null;
    source_uri: string | null;
    section: string | null;
    version: string | null;
    content_hash: string | null;
  }>;
  ai_rationale: string | null;
  transcript: ClinicalTranscriptMessageDTO[];
  specialist_review: {
    required: boolean;
    reason_code: string | null;
    note: string | null;
    requested_at: string | null;
  };
}

export interface NurseActionResponseDTO {
  success: boolean;
  case_id: string;
  review_status: ReviewStatus;
  case_version: number;
  message: string;
}

export interface ClaimCasePayload {
  case_version: number;
  action: "CLAIM" | "RELEASE";
  reason?: string;
}

export interface ObservationUpdatePayload {
  case_version: number;
  observations: ClinicalObservationInputDTO[];
}

export interface IntakeUpdatePayload {
  case_version: number;
  chief_complaint: string;
}

export interface TriageDecisionPayload {
  case_version: number;
  decision_type: "CONFIRM_ESI" | "ADJUST_ESI";
  final_esi: EsiLevel;
  reason_code: string;
  note: string | null;
}

export interface EscalateCasePayload {
  case_version: number;
  reason_code: string;
  note: string;
}

export interface HandoffCasePayload {
  case_version: number;
  destination:
    | "IMMEDIATE_CARE"
    | "PRIORITY_IN_PERSON"
    | "ROUTINE_QUEUE";
  note: string;
}

export interface PiiAccessResponseDTO {
  case_id: string;
  full_name: string;
  phone: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  expires_at: string;
}
