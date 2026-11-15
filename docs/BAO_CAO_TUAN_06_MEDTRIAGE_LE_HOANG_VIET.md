# BÁO CÁO TIẾN ĐỘ DỰ ÁN KHOA HỌC VÀ CÔNG NGHỆ

## TUẦN 6 — DỰNG BACKEND NỀN TẢNG VÀ HỢP ĐỒNG DỮ LIỆU

**Tên đề tài:** MedTriage AI — Hệ thống hỗ trợ tiếp nhận và phân luồng ưu tiên y tế  
**Người thực hiện:** Lê Hoàng Việt  
**Tuần thực hiện:** Tuần 6/15  
**Thời gian:** 31/08/2026 – 06/09/2026  
**Báo cáo liên kết:** Báo cáo Tuần 5 — Thiết kế trải nghiệm người dùng, wireframe và hệ thống thiết kế lâm sàng  
**Trạng thái:** Đã hoàn thành khung FastAPI, mô hình dữ liệu, hợp đồng API, schema Zod và gói migration PostgreSQL/pgvector. Các tiêu chí tạo phiên, lưu tin nhắn, đọc lại state và gọi endpoint chính đều có test tự động. Ba việc còn mở: hợp nhất namespace API lâm sàng, viết test API cho `/profiles`, và trả tiến trình phiên trong luồng simple agent.

> **Lưu ý phạm vi:** Đây là báo cáo cá nhân của Lê Hoàng Việt. Backend phục vụ nghiên cứu và nguyên mẫu, không phải thiết bị y tế đã được cấp phép; mọi kết quả phân luồng chỉ có giá trị sau khi nhân viên y tế xác nhận. Khung backend đã có từ giai đoạn nguyên mẫu (commit đầu tiên của `src/main.py` ngày 24/07/2026). Trong tuần 6, tôi rà soát khung này theo các yêu cầu phát sinh từ tuần 5, chốt hợp đồng dữ liệu, làm mới gói migration và kiểm chứng theo tiêu chí hoàn thành. Số route, số bảng và số test được đếm lại trên commit `ab4ffec` ngày 03/11/2026; các hạng mục bổ sung sau tuần 6 được ghi rõ. Tuần này không đo hiệu năng hay tải, nên báo cáo không có số liệu độ trễ. Docker không chạy được vào ngày đếm lại, nên kết quả test trích từ lần kiểm chứng gần nhất có ghi ngày (mục 10).

---

## 1. MỤC TIÊU TUẦN 6

Tuần 5 đã chốt giao diện cho hai vai trò. Tuần 6 làm phần bên dưới: backend phải cung cấp đúng dữ liệu mà các màn hình đó cần, và mỗi trạng thái hiển thị phải có một trường dữ liệu thật đứng sau.

Các mục tiêu chính:

1. Chốt cấu trúc FastAPI, DTO Pydantic v2 và health check.
2. Chốt endpoint cho hội thoại, hồ sơ, hàng đợi, nhận/trả ca và quyết định phân luồng.
3. Tách trạng thái phiên AI khỏi trạng thái công việc điều dưỡng trong mô hình dữ liệu.
4. Bổ sung độ đầy đủ dữ liệu, số phiên bản chống ghi đè, và nguồn cùng thời điểm cho từng sinh hiệu.
5. Chốt xác thực, phân quyền và việc che token trong log.
6. Xây dựng schema Zod phía frontend khớp với DTO backend.
7. Đóng gói migration, seed và tài liệu chạy local.
8. Kiểm chứng theo tiêu chí hoàn thành của kế hoạch 15 tuần.

---

## 2. KẾ THỪA YÊU CẦU TỪ TUẦN 5

Mỗi quyết định thiết kế ở tuần 5 kéo theo một yêu cầu cụ thể với backend:

| Quyết định ở tuần 5 | Mục | Yêu cầu với backend |
|---|---|---|
| Người bệnh không thấy ESI trước khi điều dưỡng duyệt | 8.4, 9 | ESI do AI đề xuất và ESI cuối cùng là hai trường riêng; API người bệnh chỉ trả kết quả đã thẩm định |
| `review_status` tách khỏi trạng thái phiên AI | 7.3 | Hai trường nằm ở hai bảng khác nhau, mỗi trường có tập giá trị riêng |
| Nhận ca có khóa chống xử lý trùng | 7.2 | Optimistic concurrency bằng số phiên bản; xung đột trả 409 có mã lỗi máy đọc được |
| Ca thiếu dữ liệu có nhãn riêng trên hàng đợi | 8.5 | Hàng đợi trả danh sách trường còn thiếu và lọc được theo tiêu chí này |
| Mỗi sinh hiệu có đơn vị, nguồn, thời điểm | 9 | Sinh hiệu là bản ghi riêng có `source`, `measured_at`, `recorded_by` và trạng thái “chưa đo” |
| Thanh tiến trình gắn với `workflow_phase` thật | 7.3 | Mỗi lượt trả lời phải mang theo giai đoạn hiện tại của phiên |
| Server lỗi thì giữ ca, không giả lập thành công | 7.2 | Ghi quyết định trong một giao dịch; giao diện chỉ đổi trạng thái khi nhận phản hồi thành công |

---

## 3. PHƯƠNG PHÁP

Vì khung backend đã có từ trước, tôi không viết lại mà làm theo bốn bước:

```text
Đối chiếu khung hiện có với 7 yêu cầu ở mục 2
        │
        ▼
Chốt mô hình dữ liệu và hợp đồng API (DTO backend ↔ schema Zod frontend)
        │
        ▼
Đóng gói migration + seed + tài liệu chạy local
        │
        ▼
Kiểm chứng theo tiêu chí hoàn thành bằng test tự động và CI
```

Tiêu chí hoàn thành lấy từ kế hoạch 15 tuần: **tạo được phiên, lưu được tin nhắn, đọc lại được state, gọi được các endpoint chính với dữ liệu mẫu.**

---

## 4. KIẾN TRÚC BACKEND

```text
Next.js — cổng người bệnh / cổng điều dưỡng
   │  REST /api/v1/*  (axios + kiểm tra phản hồi bằng Zod)
   │  WebSocket /api/v1/ws/*  (cập nhật hàng đợi và tin nhắn theo thời gian thực)
   ▼
FastAPI  src/main.py
   ├── lifespan: init_db_schema()  → tạo extension, bảng và cột còn thiếu
   ├── GET /health                 → liveness
   ├── router tổng src/api/routes.py, gắn prefix /api/v1
   │     └── 11 router nghiệp vụ src/api/routes_*.py
   ├── DTO Pydantic v2             src/models/*_schemas.py
   ├── dependencies                src/api/dependencies.py (JWT, vai trò, phiên DB)
   ├── services                    src/services/* (security, db, log_redaction, ...)
   └── agent runtime               src/simple_agent (pilot) │ src/agents (luồng DeepAgent cũ)
   ▼
SQLModel + SQLAlchemy async
   ├── SQLite      sqlite+aiosqlite:///./data/app.db   (dev, test)
   └── PostgreSQL 16 + pgvector  (Docker, cổng host 5433)
```

Hai quyết định kiến trúc:

1. **Schema được bổ sung khi khởi động, không xóa.** `init_db_schema()` chạy trong lifespan, thực hiện `CREATE EXTENSION IF NOT EXISTS vector`, tạo bảng và thêm cột còn thiếu. Hàm này không xóa hay đổi kiểu cột, nên khởi động lại không làm mất dữ liệu.
2. **Bảng vector chỉ có trên PostgreSQL.** `POSTGRES_ONLY_TABLES` (`src/services/db.py:76`) liệt kê 5 bảng dùng pgvector. Trên SQLite, các bảng này được bỏ qua, nên test API chạy được mà không cần Docker.

---

## 5. MÔ HÌNH DỮ LIỆU

### 5.1. Nhóm bảng

`src/models/db_models.py` có 22 bảng trên commit `ab4ffec`. Tại thời điểm kết thúc tuần 6 có 21 bảng; `MedicalFacility` được thêm ngày 16/09/2026.

| Nhóm | Bảng | Ghi chú |
|---|---|---|
| Danh tính và phiên đăng nhập | `User`, `OtpCode`, `RefreshTokenSession`, `AuditLog` | OTP có `expires_at` (UTC); refresh token xoay vòng, token cũ bị đánh dấu `is_revoked` |
| Hồ sơ | `EHRProfile` | Một tài khoản có nhiều hồ sơ (bản thân, người thân) |
| Luồng triage DeepAgent | `TriageCase`, `NurseReviewState`, `ClinicalObservation`, `ChatMessage` | Luồng cũ, cổng `/nurse` |
| Luồng simple agent (runtime) | `SimpleAgentSessionRecord`, `SimpleAgentChatSession`, `SimpleAgentChatMessage`, `SimpleAgentNurseReview` | Luồng pilot, cổng `/nurse-simple` |
| Kho tri thức simple agent | `SimpleAgentClinicalConcept`, `SimpleAgentConceptRelation`, `SimpleAgentProtocolAtom`, `SimpleAgentFactTarget`, `SimpleAgentFactTargetEmbedding` | Dữ liệu tham chiếu; embedding `Vector(1536)` |
| Kho bằng chứng ESI và ca tham khảo | `ESIKnowledgeDocument`, `MieticCase` | Embedding `Vector(1024)` |
| Nội dung | `HealthTopic` | Bài giáo dục sức khỏe |
| Cơ sở y tế | `MedicalFacility` | Bổ sung sau tuần 6 (16/09/2026) |

### 5.2. Tách trạng thái phiên AI và trạng thái thẩm định

Kế hoạch tuần 5 gọi trường này là `triage_status`. Khi đối chiếu, tôi giữ tên `status` đã có trong code, vì việc tách hai khái niệm đã được thực hiện bằng hai bảng riêng:

| Luồng | Trạng thái phiên AI | Trạng thái công việc điều dưỡng |
|---|---|---|
| DeepAgent (`/nurse`) | `TriageCase.status`: `IN_PROGRESS`, `RED_FLAG_LOCKED`, `HITL_REVIEWING`, `COMPLETED`, `CANCELLED` | `NurseReviewState.review_status`: `WAITING_REVIEW`, `ASSIGNED`, `IN_REVIEW`, `NEEDS_MORE_INFO`, `SPECIALIST_REVIEW_REQUIRED`, `TRIAGE_DECIDED`, `HANDED_OFF` |
| Simple agent (`/nurse-simple`) | `SimpleAgentChatSession.status`: `ACTIVE`, `COMPLETED`, `ABANDONED` | `SimpleAgentNurseReview.review_status`: `WAITING_REVIEW`, `ASSIGNED`, `TRIAGE_DECIDED`, `HANDED_OFF`, `PARKED` |

`TriageCase` cũng tách `ai_proposed_esi` khỏi `final_clinical_esi`, có cờ `is_overridden`. Vì vậy, ESI do AI đề xuất không bao giờ ghi đè lên ESI đã được điều dưỡng xác nhận.

Luồng simple agent gộp hai bước “quyết định” và “bàn giao”. Quyết định của điều dưỡng đưa ca thẳng sang `HANDED_OFF`, và luồng này không có bước đánh giá chuyên sâu. Docstring của `SimpleAgentNurseReview` ghi rõ đây là phạm vi pilot, không phải thiếu sót bị bỏ quên.

### 5.3. Chống ghi đè bằng `case_version`

Cả hai cổng lâm sàng dùng optimistic concurrency. Mỗi thao tác nhận ca hoặc quyết định phải gửi kèm số phiên bản đang xem. Nếu số này không khớp, server trả về:

```json
{
  "detail": {
    "code": "CASE_VERSION_CONFLICT",
    "message": "Ca đã được cập nhật bởi người khác. Vui lòng tải lại dữ liệu.",
    "current_version": 4
  }
}
```

với mã HTTP 409 (`src/api/routes_nurse.py:254`, `src/api/routes_nurse_simple.py:225`). Ngoài kiểm tra phiên bản, server còn kiểm tra người phụ trách: ca đang do điều dưỡng khác nhận thì cũng trả 409. Mỗi lần ghi thành công tăng `version` thêm 1.

Khi đối chiếu, tôi thấy hai cổng chưa thống nhất chi tiết. `/nurse` nhận trường `case_version` và bắt đầu từ 1. `/nurse-simple` nhận trường `version` và bắt đầu từ 0, dù phản hồi vẫn đặt tên là `case_version`. Hành vi giống nhau, nhưng tên trường khác nhau khiến frontend phải viết hai bộ ánh xạ. Việc này được đưa vào kế hoạch tuần 7.

### 5.4. Độ đầy đủ dữ liệu

`DataCompletenessDTO(is_complete, missing_fields)` (`src/models/nurse_schemas.py:37`) được trả trong từng thẻ hàng đợi của `/nurse`. Tham số `needs_info_only=true` lọc ra các ca còn thiếu dữ liệu nền tảng, tương ứng với tab “Thiếu dữ liệu” của wireframe N1. Cổng `/nurse-simple` chưa có trường này.

### 5.5. Sinh hiệu có nguồn và thời điểm

Mỗi sinh hiệu là một bản ghi `ClinicalObservation`, không phải một cột trong bảng ca:

| Trường | Giá trị |
|---|---|
| `kind` | `HEART_RATE`, `BLOOD_PRESSURE`, `RESPIRATORY_RATE`, `SPO2`, `TEMPERATURE`, `CONSCIOUSNESS` |
| `availability` | `MEASURED`, `UNKNOWN`, `NOT_MEASURED`, `NOT_APPLICABLE` |
| `source` | `PATIENT_REPORTED`, `NURSE_MEASURED`, `DEVICE`, `UNKNOWN` |
| `value`, `unit` | Giá trị và đơn vị |
| `measured_at`, `recorded_by`, `created_at` | Thời điểm đo, người ghi, thời điểm lưu |

Trường `availability` cho phép phân biệt “chưa đo” với “đo được giá trị bình thường”. Giao diện vì vậy hiển thị được “Chưa có dữ liệu” thay vì để trống hoặc tự điền giá trị mặc định, đúng quy tắc ở mục 9 tuần 5. Trường `source` tách lời người bệnh khai khỏi số đo của điều dưỡng hoặc thiết bị.

---

## 6. HỢP ĐỒNG API

### 6.1. Các nhóm endpoint

Tất cả router được gắn dưới `/api/v1` qua `src/api/routes.py`. Trên commit `ab4ffec` có 73 route (67 HTTP, 6 WebSocket), cộng thêm `GET /health` nằm ngoài prefix.

| Router | Prefix | Số route | Nội dung chính |
|---|---|---:|---|
| Xác thực | `/auth` | 12 | Đăng ký, xác minh OTP, đăng nhập, khách khẩn cấp, refresh, quên/đặt lại mật khẩu, `GET /me`, cập nhật số điện thoại, đăng xuất, OAuth Google/GitHub |
| Hồ sơ | `/profiles` | 9 | CRUD hồ sơ, `ehr-lite`, liên hệ khẩn cấp |
| Triage simple agent | `/simple-triage` | 8 | Bắt đầu phiên, gửi tin, danh sách và chi tiết phiên, PDF, nhắn nhân viên, đánh dấu đã đọc, kênh care team |
| Điều dưỡng simple agent | `/nurse-simple` | 8 | Hàng đợi, chi tiết ca, nhận/trả/tạm gác/khôi phục ca, quyết định, tin nhắn, care team; `GET /dashboard` bổ sung ngày 16/09/2026 |
| Triage DeepAgent | `/triage` | 8 + 1 | Bắt đầu phiên, gửi tin, đọc lại tin nhắn, lịch sử, nhắn nhân viên, care team; thêm 1 route xuất PDF |
| Điều dưỡng DeepAgent | `/nurse` | 16 | Hàng đợi, chi tiết ca, nhận/trả ca, cập nhật sinh hiệu và thông tin tiếp nhận, quyết định, đánh giá chuyên sâu, bàn giao, xác nhận cảnh báo, truy cập PII có lý do, tin nhắn, inbox, liên hệ khẩn cấp |
| Giáo dục sức khỏe | `/health-topics` | 2 | Danh sách và chi tiết bài viết |
| Cơ sở y tế gần | `/facilities` | 1 | Bổ sung ngày 16/09/2026 |
| Realtime | `/ws` | 3 + 3 | `/ws/clinical`, `/ws/case/{case_id}`, `/ws/patient` và ba kênh tương ứng của simple agent |
| Router tổng | — | 2 | `POST /chat` và `GET /status` gọi thẳng DeepAgent runtime |

Endpoint `POST /auth/resend-registration-otp` có trong bản làm việc hiện tại nhưng chưa nằm trong commit `ab4ffec`, nên không được tính vào bảng trên.

### 6.2. Luồng chính qua API

```text
Người bệnh                                     Điều dưỡng
POST /simple-triage/start  → session_id
POST /simple-triage/chat/{id}  (mỗi lượt)
        │  lưu tin nhắn + state vào DB
        │  phát sự kiện qua /ws/simple-clinical ─────▶ GET /nurse-simple/queue
        │                                              POST /cases/{id}/claim  {version, action: CLAIM}
        │                                              GET  /cases/{id}
        │                                              POST /cases/{id}/decision {version, final_esi, reason_code}
        │  ◀──── sự kiện qua /ws/simple-patient ───── review_status = HANDED_OFF
GET /simple-triage/sessions/{id}  → kết quả đã thẩm định
```

Luồng DeepAgent đi qua `/triage` và `/nurse` theo cùng thứ tự, có thêm bước cập nhật sinh hiệu, đánh giá chuyên sâu và bàn giao tách riêng.

### 6.3. Quy ước lỗi

| Mã | Khi nào | Xử lý phía frontend |
|---|---|---|
| 401 | Thiếu hoặc hết hạn access token | Interceptor trong `frontend/src/lib/api/axios.client.ts` gọi `/auth/refresh` một lần rồi gửi lại; vẫn 401 thì đăng xuất. Các request 401 đồng thời xếp hàng chờ một lần refresh |
| 403 | Sai vai trò, ví dụ tài khoản người bệnh gọi `/nurse` | Chuyển cho service hoặc TanStack Query xử lý |
| 404 | Phiên không tồn tại hoặc không thuộc về người gọi; server không phân biệt hai trường hợp này | Như trên |
| 409 | `CASE_VERSION_CONFLICT` hoặc ca đã có người khác nhận | Như trên; giao diện phải tải lại ca, không ghi đè |
| 422 | Dữ liệu đầu vào sai, ví dụ tạm gác ca mà không ghi lý do | Như trên |

Việc không phân biệt “không tồn tại” với “không thuộc về bạn” là có chủ ý: người gọi không dò được mã phiên của người khác bằng cách thử từng giá trị.

### 6.4. Hai namespace lâm sàng cùng tồn tại

Kế hoạch tuần 5 đặt mục tiêu một namespace API duy nhất cho cổng lâm sàng. Mục tiêu này **chưa đạt**. Ngày 28/08/2026, luồng simple agent được thêm như một runtime pilot tách biệt (commit `61364f3`), có bảng, router và kênh WebSocket riêng, để thử nghiệm không ảnh hưởng luồng DeepAgent đang chạy. Frontend chọn namespace theo cờ chế độ agent.

Cách tách này giúp hai luồng không ghi chéo dữ liệu của nhau. Đổi lại, hợp đồng bị lặp: hai bộ DTO, hai cách đặt tên trường phiên bản (mục 5.3), hai tập `review_status`. Tôi ghi nhận đây là nợ kỹ thuật. Việc gộp chỉ nên làm sau khi chọn được luồng sẽ giữ lại, vì gộp sớm buộc phải thống nhất cả hai mô hình quyết định.

Cũng trong lúc đối chiếu, tôi thấy DTO của `/nurse-simple` khai báo `action` và `decision_type` là `str` rồi tự kiểm tra trong thân hàm. Giá trị sai vẫn bị chặn bằng 422, nhưng tài liệu OpenAPI không liệt kê được tập giá trị hợp lệ. `/nurse` dùng `Literal` nên không gặp vấn đề này.

---

## 7. XÁC THỰC VÀ PHÂN QUYỀN

| Thành phần | Cách làm | Vị trí |
|---|---|---|
| Access token | JWT HS256, mặc định 1.440 phút | `src/config.py:117-118` |
| Refresh token | Mặc định 10.080 phút, xoay vòng mỗi lần dùng; token cũ bị thu hồi | `RefreshTokenSession`, `src/services/security.py` |
| OTP | Gắn với email, có hạn dùng | `OtpCode`, `routes_auth.py` |
| OAuth | Google và GitHub, kiểm tra URL chuyển hướng | `routes_auth.py`, `tests/test_api/test_oauth_redirect.py` |
| Vai trò | `GUEST_EMERGENCY`, `PATIENT`, `CLINICAL_NURSE`, `SYSTEM_ADMIN`; `DOCTOR` chỉ còn là bí danh cũ | `src/api/dependencies.py` |
| Phạm vi dữ liệu | Truy vấn phiên luôn lọc theo `patient_id` của người gọi | `routes_simple_triage.py`, `test_persisted_memory_cannot_be_read_by_another_patients_scope`; phạm vi hồ sơ chưa có test (mục 10.3) |
| Che token trong log | Token trong query string của WebSocket được che trước khi ghi log truy cập | `src/services/log_redaction.py` (commit `e3af5fe`, 30/08/2026) |

Có hai điểm cần lưu ý khi triển khai:

1. Access token mặc định sống 1 ngày, quá dài với một ứng dụng lâm sàng dùng chung máy trạm. Giá trị này đặt được qua biến môi trường, và phải đặt ngắn hơn khi chạy ngoài môi trường dev.
2. Ngày 31/08/2026, lối vào “Dùng thử không cần tài khoản” được gỡ khỏi màn hình đăng nhập (commit `51900f3`). Endpoint `POST /auth/guest` và trang `/triage/guest-session` vẫn còn và vẫn gọi được. Cần quyết định giữ lối vào này cho tình huống khẩn cấp, kèm giới hạn rõ ràng, hay gỡ hẳn.

---

## 8. HỢP ĐỒNG DỮ LIỆU FRONTEND–BACKEND

Mục tiêu là frontend không tin phản hồi một cách mù quáng. Mỗi phản hồi quan trọng được kiểm tra bằng Zod trước khi đưa vào giao diện. Nếu backend đổi tên hoặc kiểu một trường, lỗi xuất hiện ngay tại tầng service, thay vì hiển thị sai một trạng thái lâm sàng.

| Nhóm | Tệp | Đối ứng phía backend |
|---|---|---|
| Phản hồi API | `frontend/src/schemas/simple-triage.schema.ts`, `simple-nurse.schema.ts`, `simple-care-team.schema.ts`, `triage-stream.schema.ts`, `clinical-profile.schema.ts`, `facilities.schema.ts` | DTO trong `src/models/*_schemas.py` và các model khai báo trong `routes_*_simple.py` |
| Form nhập liệu | `frontend/src/lib/validations/clinical-hitl.schema.ts`, `clinical-profile.schema.ts`, `clinical-history.schema.ts`, `account-contact.schema.ts` | DTO request tương ứng |

Năm service gọi Zod để kiểm tra phản hồi: `clinical-hitl`, `facilities`, `simple-nurse`, `simple-triage`, `triage`. Ví dụ, `simple-triage.schema.ts` khai báo `status` là `ACTIVE | COMPLETED | ABANDONED` và `review_status` là một trường riêng có thể `null`, khớp với cách tách ở mục 5.2.

Về `workflow_phase`: hợp đồng này chỉ có trong luồng DeepAgent. `triage-stream.schema.ts` khai báo các giai đoạn `SAFETY_CHECK`, `INTENT_CLASSIFICATION`, `INTAKE_EXTRACTION`, `CLARIFICATION`, …, và thanh tiến trình dựa vào đó. Phản hồi của simple agent chưa có trường tiến trình tương đương. Với luồng pilot, thanh tiến trình vì vậy chưa phản ánh được trạng thái thật, trái với quy tắc ở mục 7.3 tuần 5.

---

## 9. MIGRATION, SEED VÀ CHẠY LOCAL

### 9.1. Gói migration

Gói migration nằm trong `database/migrations/` và được làm mới ngày 01/09/2026 (commit `826dd82`):

| Tệp | Nội dung |
|---|---|
| `20260901_simple_agent_schema.sql` (~20 KB) | 9 bảng `simple_agent_*`, index btree và HNSW cho cột vector, khóa ngoại tới `users` |
| `20260901_simple_agent_corpus_data.sql` (~60 MB) | Dữ liệu 5 bảng tham chiếu, xuất từ PostgreSQL 16 + pgvector dev ngày 01/09/2026 |
| `README.md` | Cách áp dụng, kiểm tra số dòng sau khi áp dụng, cách xuất lại |

Số dòng dữ liệu tham chiếu đi kèm:

| Bảng | Số dòng |
|---|---:|
| `simple_agent_clinical_concepts` | 1.132 |
| `simple_agent_concept_relations` | 4.247 |
| `simple_agent_protocol_atoms` | 1.768 |
| `simple_agent_fact_targets` | 238 |
| `simple_agent_fact_target_embeddings` | 238 |

Bốn bảng runtime (phiên, tin nhắn, bản ghi phiên, thẩm định) **không được xuất**, vì đó là dữ liệu phát sinh khi người dùng sử dụng hệ thống. Script `scripts/migrate_simple_agent_corpus_to_pg.py` upsert theo khóa tự nhiên, nên chạy lại nhiều lần không sinh bản ghi trùng.

### 9.2. Seed và tài liệu chạy

| Hạng mục | Tệp |
|---|---|
| Khởi tạo schema độc lập | `scripts/init_db_schema_standalone.py` |
| Tài khoản demo theo vai trò | `scripts/seed_demo_accounts.py` |
| Bài giáo dục sức khỏe | `scripts/seed_health_topics.py` |
| Cơ sở y tế (bổ sung sau tuần 6) | `scripts/seed_medical_facilities.py` |
| Hướng dẫn cài đặt và chạy | `SETUP.md` (`docker compose up -d postgres` ở dòng 123, seed tài khoản ở dòng 210) |
| Vận hành và di chuyển dữ liệu | `RUNBOOK.md`, `README_DB_MIGRATION.md`, `LOCAL_DATA_MIGRATION.md` |
| Hạ tầng local | `docker-compose.yml`, `Makefile` |

Tài khoản demo dùng mật khẩu cố định khai báo trong `scripts/seed_demo_accounts.py`, chỉ phục vụ dev và demo. Không được chạy script này trên môi trường triển khai thật. Khóa API và chuỗi kết nối nằm trong `.env`; file này không được commit lên repository.

---

## 10. KIỂM THỬ THEO TIÊU CHÍ HOÀN THÀNH

### 10.1. Ánh xạ tiêu chí sang test

`tests/test_api/` có 17 tệp với 140 hàm test, chạy trên SQLite:

| Tiêu chí | Test chứng minh | Số test |
|---|---|---:|
| Tạo phiên | `test_patient_adaptive_contract`, `test_simple_triage_emergency_flow`, `test_routes` | 10 + 4 + 5 |
| Lưu tin nhắn và đọc lại state | `test_state_persistence`: state chuẩn và bộ nhớ hội thoại còn nguyên sau khi đọc lại từ DB; người bệnh khác không đọc được; câu lệnh migration chạy lại an toàn | 18 |
| Hàng đợi, nhận ca, quyết định | `test_nurse_core`: phiên bản cũ → 409, ca của người khác → 409; `test_simple_triage_review_contract` | 10 + 1 |
| Thời gian thực | `test_clinical_realtime` | 21 |
| Cảnh báo khẩn và SBAR | `test_red_flag_timestamps`, `test_sbar_publication_order`, `test_sbar_pdf` | 7 + 7 + 3 |
| Xác thực | `test_auth_otp`, `test_auth_tokens`, `test_oauth_redirect`, `test_account_phone` | 8 + 4 + 10 + 5 |
| Nội dung và tiện ích | `test_health_topics`, `test_patient_session_title`, `test_facilities` (sau tuần 6) | 15 + 3 + 9 |
| **Hồ sơ `/profiles`** | **Chưa có test API** | **0** |

### 10.2. Kết quả chạy

| Lần chạy | Kết quả |
|---|---|
| CI Backend trên GitHub, run `40919127933`, commit `4c78aaf` (30/10/2026) | Xanh |
| Bộ test backend trong môi trường Python 3.12 cài mới, cùng tập dependency với CI | 1.272 passed, 10 skipped, 16 xfailed |

16 xfailed là các test được đánh dấu lỗi đã biết, không được tính là đạt. Hai lần chạy trên là lần kiểm chứng gần nhất có ghi lại. Ngày 03/11/2026, Docker không khởi động được trên máy làm việc, nên tôi không chạy lại; số liệu trên không được trình bày như kết quả của ngày viết báo cáo.

### 10.3. Khoảng trống còn lại

1. **`/profiles` không có test API.** Đây là router chứa thông tin dị ứng, thuốc và liên hệ khẩn cấp, những dữ liệu ảnh hưởng trực tiếp tới quyết định của điều dưỡng. Thiếu test ở đây là khoảng trống đáng kể nhất của tuần.
2. **`/health` chỉ là liveness.** Endpoint trả `{"status": "ok", "env": ...}` mà không kiểm tra kết nối DB. Bước smoke test trong CD chờ `/health` trả lời, nên gián tiếp xác nhận lifespan đã chạy xong `init_db_schema()`. Tuy vậy, nếu DB mất kết nối sau khi khởi động, `/health` vẫn trả `ok`.
3. **Phần vector chỉ kiểm được trên PostgreSQL.** Test API chạy SQLite, nên truy vấn HNSW và dữ liệu tham chiếu không được bộ test này kiểm. Hiện chỉ có bước kiểm tra số dòng trong `database/migrations/README.md`.

---

## 11. ĐỐI CHIẾU VỚI KẾ HOẠCH TUẦN 5

| # | Hạng mục kế hoạch (mục 17 tuần 5) | Kết quả | Ghi chú |
|---:|---|---|---|
| 1 | Cấu trúc FastAPI, DTO Pydantic v2, health check | Đạt | Health check mới là liveness; readiness có kiểm tra DB chuyển sang tuần 7 |
| 2 | Endpoint chat, hồ sơ, hàng đợi, nhận/trả ca, quyết định | Đạt | Có ở cả hai luồng; nhận và trả ca dùng chung một endpoint `claim` với `action` |
| 3 | Tách `triage_status` khỏi `review_status` | Đạt, khác tên | Trường phiên AI tên là `status`, đặt ở bảng khác với `review_status` |
| 4 | `data_completeness`, `case_version`, nguồn/thời điểm sinh hiệu | Đạt ở `/nurse`; một phần ở `/nurse-simple` | `/nurse-simple` có `case_version` nhưng chưa có `data_completeness` và bảng sinh hiệu |
| 5 | Contract `workflow_phase` cho thanh tiến trình | Một phần | Chỉ có ở luồng DeepAgent; simple agent chưa trả tiến trình |
| 6 | Một namespace API duy nhất cho cổng lâm sàng | Chưa đạt | Hai namespace cùng tồn tại do pilot tách biệt (mục 6.4) |
| 7 | Schema Zod khớp DTO backend | Đạt | 6 schema phản hồi, 4 schema form, 5 service kiểm tra phản hồi |

Kết quả: 4/7 hạng mục đạt, 2 đạt một phần, 1 chưa đạt. Các hạng mục chưa xong được chuyển sang kế hoạch tuần 7 (mục 15), kèm lý do.

---

## 12. SẢN PHẨM VÀ MINH CHỨNG TUẦN 6

| Hạng mục | Minh chứng trong repository | Trạng thái |
|---|---|---|
| Khung ứng dụng, lifespan, health check | `src/main.py` | Có |
| Router và hợp đồng API | `src/api/routes.py`, `src/api/routes_*.py` | 73 route + `/health` |
| DTO Pydantic v2 | `src/models/auth_schemas.py`, `nurse_schemas.py`, `patient_schemas.py`, `profile_schemas.py`, `health_schemas.py`, `facility_schemas.py`, `schemas.py` | Có |
| Mô hình dữ liệu | `src/models/db_models.py` | 22 bảng (21 bảng tại thời điểm kết thúc tuần 6) |
| Khởi tạo schema, bảng chỉ dành cho PostgreSQL | `src/services/db.py` | Có |
| Xác thực, xoay vòng token, che token trong log | `src/services/security.py`, `src/api/routes_auth.py`, `src/services/log_redaction.py` | Có |
| Schema Zod | `frontend/src/schemas/`, `frontend/src/lib/validations/` | Có |
| Gói migration và dữ liệu tham chiếu | `database/migrations/` | Làm mới ngày 01/09/2026 |
| Script seed và di chuyển dữ liệu | `scripts/` | Có |
| Tài liệu chạy local | `SETUP.md`, `RUNBOOK.md`, `README_DB_MIGRATION.md`, `LOCAL_DATA_MIGRATION.md` | Có |
| Test API | `tests/test_api/` | 140 test; chưa có test cho `/profiles` |
| CI backend | `.github/workflows/ci-backend.yml` | Xanh ở lần chạy 30/10/2026 |

---

## 13. KẾT QUẢ ĐẠT ĐƯỢC TRONG TUẦN 6

Trong tuần 6, tôi đã hoàn thành các nội dung sau:

- Đối chiếu khung backend hiện có với 7 yêu cầu phát sinh từ thiết kế tuần 5.
- Chốt mô hình dữ liệu gồm 21 bảng ở thời điểm kết thúc tuần. Trạng thái phiên AI và trạng thái thẩm định nằm ở hai bảng riêng trong cả hai luồng.
- Chốt cơ chế chống ghi đè bằng số phiên bản, với lỗi 409 `CASE_VERSION_CONFLICT` máy đọc được ở cả hai cổng lâm sàng.
- Chốt mô hình sinh hiệu có nguồn, thời điểm, người ghi và trạng thái “chưa đo”.
- Lập bảng hợp đồng API cho 11 router nghiệp vụ và quy ước mã lỗi 401/403/404/409/422.
- Rà soát xác thực: JWT, refresh token xoay vòng, OTP có hạn dùng, OAuth, 4 vai trò, che token trong log.
- Chốt các schema Zod phía frontend ứng với DTO backend; 5 service kiểm tra phản hồi trước khi dùng.
- Làm mới gói migration PostgreSQL/pgvector cùng dữ liệu tham chiếu 5 bảng, có hướng dẫn áp dụng, kiểm tra và xuất lại.
- Ánh xạ tiêu chí hoàn thành sang 140 test API và xác định khoảng trống lớn nhất là `/profiles`.
- Ghi nhận trung thực 3 hạng mục kế hoạch chưa đạt trọn vẹn và lý do.

---

## 14. KHÓ KHĂN VÀ CÁCH XỬ LÝ

| Khó khăn | Cách xử lý |
|---|---|
| CI của repository tổ chức đỏ vì runner do GitHub cung cấp bị chặn theo hạn mức thanh toán, không phải do code | Chuyển các job sang self-hosted runner (commit `bedb35c`, 31/08/2026); kiểm tra `runner_id` trước khi sửa YAML |
| Pipeline CI mới (27/08/2026) không còn lệnh bỏ qua lỗi ở từng bước như bản cũ, và làm lộ hai vấn đề. Thứ nhất, CI cài dependency không kèm bộ ML (torch, transformers), còn `numpy` chưa được khai báo, nên `pytest` dừng ngay khi thu thập test. Thứ hai, một số test vốn đỏ từ trước | Khai báo `numpy` (commit `5e655b2`, 01/09/2026). Một test đang gọi OpenAI thật: đã stub lại. Bảy hồi quy của agent DeepAgent: đánh dấu xfail không nghiêm ngặt và theo dõi riêng. Các lỗi này vẫn hiện trong kết quả test dưới dạng xfailed và sẽ chuyển sang XPASS khi được sửa |
| Backend không khởi động khi bảng embedding fact target trống (30/08/2026) | Backfill từ PostgreSQL; gói migration ngày 01/09 mang theo dữ liệu tham chiếu để máy mới không gặp lại lỗi này |
| pgvector không chạy trên SQLite | Đánh dấu 5 bảng vector là `POSTGRES_ONLY_TABLES`; test API chạy SQLite, phần vector kiểm trên PostgreSQL |
| Pilot simple agent cần thử nghiệm mà không ảnh hưởng luồng đang chạy | Tách bảng, router và kênh WebSocket; chấp nhận hai namespace và ghi rõ là nợ kỹ thuật |
| Token WebSocket truyền qua query string bị ghi vào log truy cập | Thêm bộ lọc che token trước khi ghi log (commit `e3af5fe`, 30/08/2026) |
| Tên trường trong kế hoạch (`triage_status`) khác tên trong code (`status`) | Giữ tên trong code vì việc tách đã đúng về bản chất; ghi rõ trong bảng đối chiếu để người đọc không tìm sai trường |

---

## 15. KẾ HOẠCH TUẦN 7

Theo kế hoạch 15 tuần, tuần 7 xây dựng **agent hội thoại giai đoạn A**:

- Trích xuất concept và fact từ câu trả lời của người dùng.
- Phân biệt người khai cho bản thân (`SELF`) và khai cho người khác (`OTHER_PERSON`).
- Kiểm tra fact đã khai trước khi hỏi, tránh hỏi lặp.
- Giới hạn số lần gọi tool trong một lượt.
- Xử lý câu trả lời mơ hồ bằng câu hỏi làm rõ, không tự suy diễn thành fact.

Các việc chuyển tiếp từ tuần 6:

- Viết test API cho `/profiles`: CRUD, `ehr-lite`, liên hệ khẩn cấp, và chặn truy cập hồ sơ của người khác.
- Thêm endpoint readiness có kiểm tra kết nối DB, tách khỏi `/health` (liveness).
- Bổ sung trường tiến trình cho phản hồi của simple agent để thanh tiến trình phản ánh trạng thái thật.
- Chuẩn hóa DTO `/nurse-simple`: dùng `Literal` cho `action` và `decision_type`, thống nhất tên trường phiên bản với `/nurse`.
- Ghi quyết định kiến trúc (ADR) về việc giữ luồng nào làm namespace lâm sàng chính và lộ trình gộp.
- Quyết định số phận lối vào khách `/auth/guest`: giữ cho tình huống khẩn cấp kèm giới hạn, hoặc gỡ hẳn.

---

## 16. KẾT LUẬN TUẦN 6

Tuần 6 cho thấy hợp đồng dữ liệu là nơi các nguyên tắc an toàn ở tuần 5 trở thành ràng buộc kiểm tra được. Nếu ESI của AI và ESI đã thẩm định là hai trường riêng, giao diện không thể vô tình công bố kết quả chưa duyệt. Nếu mỗi sinh hiệu có trạng thái “chưa đo”, giao diện không cần đoán giá trị. Nếu mỗi lần ghi phải mang số phiên bản, hai điều dưỡng không thể âm thầm ghi đè quyết định của nhau.

Tuần này cũng cho thấy những chỗ hợp đồng chưa chặt: hai namespace lâm sàng, luồng pilot chưa trả tiến trình, router hồ sơ chưa có test. Những điểm này được ghi lại cùng lý do, thay vì báo cáo là đã xong.

Nguyên tắc được chốt trong tuần này là: **mỗi trạng thái hiển thị trên giao diện phải có một trường dữ liệu thật đứng sau, và mỗi trường dữ liệu quan trọng phải có một test chứng minh nó được lưu và đọc lại đúng.**

---

## NGƯỜI LẬP BÁO CÁO

**Lê Hoàng Việt**  
Ký và ghi rõ họ tên: ____________________  
Ngày: ____ / ____ / 2026
