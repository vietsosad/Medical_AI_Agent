# 📊 Cấu Trúc Dữ Liệu Hiện Tại Của Hệ Thống AI Triage
*(Dự án AI Agent Phân Loại Triệu Chứng & Triage Thông Minh - VinUni AI20K)*

Tài liệu này mô tả chi tiết nguồn dữ liệu, các bảng trong cơ sở dữ liệu và cách hệ thống lưu trữ/sử dụng dữ liệu cho phiên bản hiện tại.

## 1. Nguồn Dữ Liệu Cốt Lõi (Core Datasets & Knowledge Base)
Dựa trên chiến lược RAG hiện tại, hệ thống sử dụng các bộ dữ liệu chuẩn y khoa:
* **Giao thức phân độ cấp cứu (Triage Protocols):** Được trích xuất từ **AHRQ Emergency Severity Index (ESI) Handbook v4/v5** và phác đồ Bộ Y Tế. Các dữ liệu này được làm sạch, chuyển sang dạng Markdown và lưu trong thư mục `data/extracted_tables/` (ví dụ: `ahrq_esi_v5_cleaned.md`, `master_esi_clinical_tables.md`).
* **Bộ Từ Khóa Phản Xạ Nhanh (Red-Flag Reflex Dictionary):** Chứa các cụm từ khẩn cấp nguy hiểm được lưu trữ tại `data/guard_rules/ontology_vi_en.json` nhằm ngắt luồng dưới 50ms khi phát hiện dấu hiệu nguy kịch.

## 2. Cơ Sở Dữ Liệu (PostgreSQL + pgvector)
Hệ thống sử dụng **PostgreSQL** kết hợp với extension **pgvector** làm cơ sở dữ liệu chính (lưu trữ cả dữ liệu quan hệ và vector embeddings cho RAG). Các thực thể được quản lý bởi SQLModel theo kiến trúc sau:

### 2.1. Nhóm Danh Tính, Xác Thực & Hồ Sơ Y Khoa
* **`users`:** Lưu thông tin định danh bệnh nhân, điều dưỡng, quản trị viên (có hỗ trợ tài khoản Guest khẩn cấp và OAuth). Phân quyền bằng RBAC (Role-Based Access Control).
* **`ehr_profiles`:** Hồ sơ y khoa (Electronic Health Record) nhẹ của bệnh nhân và người thân. Chứa thông tin về tuổi, nhóm máu, bệnh nền (`chronic_conditions`), thuốc đang dùng (`daily_medications`), và người liên hệ khẩn cấp.
* **`otp_codes` & `refresh_token_sessions`:** Quản lý phiên đăng nhập, xoay vòng token và xác thực OTP bảo mật y tế.

### 2.2. Nhóm Triage Engine & Hội Thoại
* **`triage_cases`:** Bảng trung tâm lưu trữ các phiên khám (Triage session). Chứa thông tin đề xuất phân độ ESI của AI (`ai_proposed_esi`), quyết định cuối cùng của nhân viên y tế (`final_clinical_esi`), trạng thái báo động đỏ (`is_red_flag_triggered`) và phiếu tóm tắt SBAR (`sbar_summary`).
* **`chat_messages`:** Lưu chi tiết lịch sử hội thoại giữa Patient, AI Agent, Nurse và System Alert. Có hỗ trợ các câu hỏi trắc nghiệm có cấu trúc (`structured_options`).
* **`clinical_observations`:** Bản ghi lâm sàng ghi nhận các chỉ số sinh tồn thực tế (Nhịp tim, Huyết áp, SPO2...) chưa qua suy diễn.

### 2.3. Nhóm Điều Phối Lâm Sàng HITL & Kiểm Toán
* **`nurse_review_states`:** Lưu trạng thái làm việc, phê duyệt và bàn giao ca của các Điều dưỡng (Human-in-the-loop - HITL). Sử dụng optimistic concurrency (phiên bản hóa) để tránh xung đột ghi đè.
* **`audit_logs`:** Sổ cái kiểm toán (ACID Ledger) không thể thay đổi. Ghi nhận 100% các sự kiện quan trọng như: Điều dưỡng ghi đè quyết định của AI, thời gian trễ RAG (latency), sự kiện ngắt luồng 50ms (Reflex). Phục vụ trực tiếp để tính KPI đồng thuận (Concordance Rate).

### 2.4. Nhóm RAG Knowledge Base (Vector Storage)
Các bảng lưu trữ tri thức RAG đều sử dụng thuật toán HNSW (`postgresql_using="hnsw"`) và GIN index để tìm kiếm vector kết hợp từ khóa (Hybrid Search):
* **`triage_protocol_documents`:** Kho lưu trữ các phân đoạn phác đồ ESI đã được nhân viên lâm sàng phê duyệt (có cấu trúc metadata, vector embedding, keywords). Đây là tài liệu cốt lõi cho RAG grounding.
* **`triage_case_examples`:** Kho lưu trữ các ca bệnh mẫu (case studies) mô phỏng từ MIETIC. 
* **`triageknowledgebase`:** Bảng kiến thức dự phòng (Legacy) để duy trì khả năng tương thích khi tra cứu chéo.
