/**
 * DEFINED DTOs & TYPES FOR CLINICAL HISTORY & SBAR ARCHIVE MODULE (GROUP 4)
 * Cam kết tuân thủ 100% TypeScript Strict Mode (Zero `any` tolerance) theo tiêu chuẩn y khoa AI.
 */
import type { ChatMessage } from "@/types/triage-chat";

/**
 * Phân độ Cấp cứu Lâm sàng ESI (Emergency Severity Index)
 * 1: Resuscitation (Tối cấp cứu)
 * 2: Emergent (Khẩn cấp cực cao)
 * 3: Urgent (Khám ngoại trú ưu tiên / Khẩn)
 * 4: Less Urgent (Bất thường nhẹ)
 * 5: Non-urgent (Thăm khám thường quy / Tự theo dõi)
 */
export type EsiLevel = 1 | 2 | 3 | 4 | 5;

/** Authoritative lifecycle persisted on the backend TriageCase. */
export type TriageSessionStatus =
  | "IN_PROGRESS"
  | "HITL_REVIEWING"
  | "COMPLETED"
  | "RED_FLAG_LOCKED"
  | "CANCELLED";

/**
 * Trạng thái thẩm định của Bác sĩ / Điều dưỡng lâm sàng trực chiến (HITL - Human-In-The-Loop)
 */
export type HitlReviewStatus = 
  | "APPROVED"          // Duyệt hợp pháp 100% đề xuất của AI
  | "OVERRIDDEN"        // Chuyên gia can thiệp nâng/hạ phân độ ESI
  | "PENDING_REVIEW"    // Đang chờ hàng đợi bác sĩ trực duyệt
  | "EMERGENCY_REJECTED"; // Từ chối do hồ sơ vi phạm hoặc báo động đỏ chuyển trực tiếp

/**
 * Chữ ký thẩm định từ Bác sĩ hoặc Điều dưỡng trưởng (HITL Signature DTO)
 * Lưu trữ bằng chứng pháp lý lâm sàng khi thẩm định ca khám.
 */
export interface HitlSignatureDTO {
  reviewer_name: string | null;
  review_timestamp: string;      // Định dạng chuẩn ISO 8601 string
  status: HitlReviewStatus;
  original_esi: EsiLevel;        // Chỉ số ESI ban đầu do DeepAgent đề xuất
  final_esi: EsiLevel;           // Chỉ số ESI chính thức sau quyết định thẩm định
  justification_note?: string | null; // Lý do / biện chứng lâm sàng của bác sĩ khi can thiệp override
}

/**
 * Phiếu Báo Cáo SBAR Quá Khứ (Situation - Background - Assessment - Recommendation)
 * Đảm bảo 100% minh bạch nguồn trích dẫn phác đồ RAG Y khoa.
 */
export interface SbarReportDTO {
  situation: string;             // Tóm tắt tình trạng hiện tại và triệu chứng chính
  background: string;            // Nền tảng tiền sử, bệnh mãn tính, thuốc đang dùng từ Hồ sơ Lâm sàng
  assessment: string;            // Nhận định đánh giá và nguy cơ theo phác đồ AI & RAG
  recommendation: string;        // Khuyến nghị hành động tức thì và hướng chỉ định tiếp theo
  citations: string[];           // Mảng mã phác đồ RAG đã sử dụng (vd: ["PRO_CARD_001", "PRO_CP_002"])
}

/**
 * Thẻ thông tin tóm tắt ca bệnh hiển thị trên danh sách tra cứu / Sidebar (List Item DTO)
 */
export interface TriageHistoryListItemDTO {
  session_id: string;            // UUID duy nhất của phiên khám
  profile_name?: string | null;
  relationship_type?: string | null;
  chief_complaint: string;       // Triệu chứng chính / Lý do tiếp nhận lâm sàng
  created_at: string;            // Thời gian tạo (ISO timestamp)
  status: TriageSessionStatus;   // Trạng thái thật của ca, không suy ra từ HITL
  final_esi: EsiLevel | null;    // Chỉ có khi đã có đề xuất đủ căn cứ hoặc HITL chốt
  hitl_status: HitlReviewStatus; // Trạng thái thẩm định con người (HITL)
  sbar_snippet: string;          // Trích đoạn tóm lược SBAR nhanh
  sbar_finalized: boolean;       // Chỉ true sau final verifier và DB commit
  unread_from_staff?: number;    // Số lượng tin nhắn chưa đọc từ nhân viên y tế
}

/**
 * Hồ sơ chi tiết ca bệnh quá khứ hoàn chỉnh (Session Detail DTO)
 * Kế thừa từ thẻ tóm tắt và bổ sung dữ liệu phục vụ Read-Only Replay & Kiểm tra SBAR.
 */
export interface TriageSessionDetailDTO extends TriageHistoryListItemDTO {
  messages: ChatMessage[];       // Lịch sử tin nhắn trắc nghiệm hội thoại AI (từ Nhóm 3 - Read-Only Replay)
  sbar_report: SbarReportDTO | null; // Null cho đến khi backend xác nhận SBAR đã finalized
  hitl_signature?: HitlSignatureDTO | null; // Chữ ký thẩm định (có thể null nếu đang chờ duyệt)
}

/**
 * Khóa phân nhóm chuỗi thời gian khi hiển thị danh sách trên Trung tâm Lịch sử
 */
export type TimeGroupKey = "TODAY" | "LAST_7_DAYS" | "LAST_MONTH" | "OLDER";
