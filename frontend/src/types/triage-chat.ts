/**
 * DEFINED CONTRACTS & TYPES FOR CLINICAL TRIAGE INTERACTIVE CHAT ENGINE
 * Đảm bảo type safety cho hệ thống hội thoại DeepAgent và RAG.
 */

export type StructuredOptionType =
  | "single"
  | "multiple"
  | "scale"
  | "text_only"
  | "vitals_form";
export type IntentType =
  | "TRIAGE_NEW_SYMPTOM"
  | "TRIAGE_FOLLOW_UP"
  | "GREETING_HELP"
  | "OUT_OF_SCOPE"
  | "UNCLEAR"
  | "EMERGENCY_SIGNAL"
  | "SAFETY_CRISIS_SUPPORT";
export type DecisionStatus =
  | "NOT_APPLICABLE"
  | "COLLECTING"
  | "NEEDS_CLARIFICATION"
  | "READY_FOR_EVIDENCE"
  | "READY_FOR_REASONING"
  | "AWAITING_PATIENT_CONFIRMATION"
  | "INSUFFICIENT_EVIDENCE"
  | "RETRIEVAL_FAILURE"
  | "PROPOSED"
  | "EMERGENCY_ESCALATED";
export type ResponseType =
  | "TEXT"
  | "STRUCTURED_QUESTION"
  | "INTAKE_REVIEW"
  | "EMERGENCY"
  | "TRIAGE_PROPOSAL"
  | "SAFETY_GUIDANCE";
export type WorkflowPhase =
  | "SAFETY_CHECK"
  | "INTENT_CLASSIFICATION"
  | "INTAKE_EXTRACTION"
  | "CLARIFICATION"
  | "PATIENT_CONFIRMATION"
  | "RETRIEVAL"
  | "REASONING"
  | "REASSESSMENT"
  | "HANDOFF"
  | "COMPLETE";
export type EvidenceStatus =
  | "NOT_REQUESTED"
  | "RETRIEVED"
  | "INSUFFICIENT_EVIDENCE"
  | "RETRIEVAL_FAILURE"
  | "CASE_EXAMPLE_SUPPORT"
  | "SUFFICIENT";

/**
 * Một ý trắc nghiệm trong câu hỏi lâm sàng từ AI
 */
export interface OptionItem {
  id: string;
  label: string;
  value: string | number;
  description?: string;
  isRisk?: boolean; // Cờ báo hiệu triệu chứng mang yếu tố nguy cơ khẩn cấp (Red-flag candidate)
  isExclusive?: boolean; // Backend-declared mutually exclusive choice (for example "none")
}

export type VitalFormFieldId =
  | "heart_rate"
  | "blood_pressure"
  | "respiratory_rate"
  | "spo2"
  | "temperature_c"
  | "gcs";

export interface VitalFormField {
  id: VitalFormFieldId;
  label: string;
  unit: string;
  placeholder: string;
  inputMode: "numeric" | "decimal" | "text";
  min?: number;
  max?: number;
  step?: number;
}

export interface EhrConfirmationSnapshot {
  age: number | null;
  gender: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  bmi: number | null;
  blood_type: string | null;
  chronic_conditions: string[];
  allergies: string[];
  daily_medications: string[];
}

/**
 * Payload chứa thông tin cấu trúc biểu mẫu trắc nghiệm đính kèm từ AI Node (IntakeAnalyzer)
 */
export interface StructuredPayload {
  optionsType: StructuredOptionType;
  options?: OptionItem[];       // Bắt buộc nếu là single hoặc multiple
  fields?: VitalFormField[];    // Bắt buộc khi là biểu mẫu sinh hiệu
  ehrSnapshot?: EhrConfirmationSnapshot | null; // Chỉ đọc, dùng khi xác nhận hồ sơ EHR
  minScale?: number;            // Mặc định là 0 nếu là scale
  maxScale?: number;            // Mặc định là 10 nếu là scale
  submitted?: boolean;          // Đánh dấu câu hỏi đã được người dùng chọn hay chưa
  selectedAnswer?: string | string[] | number; // Giá trị câu trả lời chốt của bệnh nhân
}

/**
 * Tham chiếu trích dẫn nguồn RAG chuẩn y khoa
 */
export interface RagCitation {
  id: string;
  title: string;
  protocolId: string;
  excerpt: string;
  relevanceScore?: number;
  issuingBody?: string;
  sourceUri?: string;
  version?: string;
  section?: string;
  effectiveDate?: string;
  validationStatus?: "approved";
  contentHash?: string;
  reviewedBy?: string;
  reviewedAt?: string;
  calibrationId?: string;
  sourceType?: "validated_protocol" | "case_example";
  retrievalChannels?: Array<{
    channel: "vi_dense" | "en_dense" | "sparse" | "demo_dense" | "hybrid";
    rank: number;
    score?: number | null;
  }>;
}

/**
 * Ca tương đồng chỉ dùng để tham khảo cách trình bày, không phải phác đồ
 * và tuyệt đối không có quyền xác lập ESI.
 */
export interface CaseSupport {
  caseId: string;
  excerpt: string;
  /** Raw cosine similarity from the dense channel. Not a confidence. */
  similarityScore?: number;
  /** Post-rerank retrieval relevance in [0, 1]. Not a probability. */
  retrievalRelevance?: number;
  relevanceBand: "HIGH" | "MODERATE" | "LOW" | "UNKNOWN";
  /**
   * The retrieved case's own recorded ESI, where the corpus has one. Display
   * context only: this can never be, set, or influence the patient's ESI.
   */
  validatedEsiLevel?: number;
  candidateEsiLevels: number[];
  labelStatus: "CONSISTENT" | "CONFLICTING" | "UNKNOWN";
  ageBand?: string;
  sex?: string;
  symptomConcepts: string[];
  retrievalScope: "CASE_SUPPORT";
  authorityStatus: "NOT_PROTOCOL";
  sourceType: "case_example";
}

/**
 * Kiểu định nghĩa một tin nhắn trong phiên hỏi bệnh
 */
export interface ChatMessage {
  id: string;
  // 'nurse' là tin do một nhân viên lâm sàng thật gõ, không phải mô hình sinh ra.
  sender: "user" | "bot" | "system_shield" | "nurse";
  senderName?: string | null;
  timestamp: string;
  content: string;
  step: number;                 // Display metadata from the backend; never drives workflow.
  structured?: StructuredPayload | null;
  ragCitations?: RagCitation[] | null;
  caseSupport?: CaseSupport[] | null;
  intent?: IntentType | null;
  responseType?: ResponseType | null;
  decisionStatus?: DecisionStatus | null;
  workflowPhase?: WorkflowPhase | null;
  esiLevel?: 1 | 2 | 3 | 4 | 5 | null;
  evidenceStatus?: EvidenceStatus | null;
  retrievalDegradedModes?: string[];
  intakeSummary?: IntakeSummary | null;
  requiresPatientConfirmation?: boolean;
  sbarFinalized?: boolean;
}

export interface IntakeSummary {
  chief_complaint: string[];
  /** Mentioned but hedged, so recorded as uncertain rather than as a finding. */
  uncertain_symptoms: string[];
  onset_time: string | null;
  severity_score: number | null;
  radiation: string | null;
  associated_symptoms: string[];
  current_medication: string[];
  recent_procedure?: string | null;
  vital_signs?: Record<string, string | number>;
  vital_signs_status?:
    | "NOT_REVIEWED"
    | "PATIENT_REPORTED"
    | "UNAVAILABLE_CONFIRMED"
    | "UNCERTAIN";
  vital_signs_source?: string | null;
  vital_signs_measured_at?: string | null;
  ehr_snapshot?: {
    age: number | null;
    gender: string | null;
    height_cm: number | null;
    weight_kg: number | null;
    bmi: number | null;
    blood_type: string | null;
    chronic_conditions: string[];
    allergies: string[];
    daily_medications: string[];
    updated_at: string | null;
    confirmation_status:
      | "NOT_REVIEWED"
      | "CONFIRMED"
      | "UPDATED_BY_PATIENT"
      | "UNCERTAIN";
    patient_context_note: string | null;
  };
}

export type IntakeConfirmationStatus =
  | "NOT_READY"
  | "AWAITING_CONFIRMATION"
  | "CONFIRMED";

export interface AgentStreamEvent {
  type: "accepted" | "progress" | "intent" | "heartbeat" | "result" | "error";
  message: string;
  sequence: number;
  elapsedMs: number;
  phase?: WorkflowPhase | null;
  intent?: IntentType | null;
  label?: string | null;
  detail?: string | null;
  progress?: number | null;
  timestamp: string;
  retryable?: boolean | null;
  errorCode?: string | null;
  result?: ChatMessage | null;
}
