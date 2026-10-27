# Kế hoạch hoàn thiện MedTriage AI — Tuần 14 và 15

**Ngày lập:** 27/10/2026 · **Nhánh khảo sát:** `feat/nearby-facilities-and-theme` (13 commit chưa có trên `origin`, cộng WIP chưa commit)
**Phạm vi:** toàn bộ backend `src/`, frontend `frontend/`, dữ liệu, đánh giá, CI/CD, triển khai và tài liệu.
**Cách lập:** mọi phát hiện dưới đây được kiểm chứng bằng cách đọc mã hoặc chạy thử; chỗ nào chưa kiểm chứng được thì ghi rõ. Không có lời gọi API trả phí nào được thực hiện.

Theo lộ trình 15 tuần, tuần này (26/10–01/11) là **tuần 14 — hardening, triển khai, tài liệu**; tuần 15 là nghiệm thu. Tiêu chí nghiệm thu của chính dự án đòi hỏi: red flag được xử lý trước LLM và có hướng dẫn 115; mọi số liệu trong báo cáo truy được về script/dataset; thành viên khác dựng được môi trường theo tài liệu.

---

## 1. Tóm tắt

Phần lõi đáng giữ: quyết định ESI tất định trong `decision.py`, chống bịa ID ở `tools.py`, fail-closed khi lỗi, HITL điều dưỡng có lý do bắt buộc. Frontend sạch về kiểu (0 `any`, `tsc` và ESLint sạch, 238/238 test).

Nhưng có bốn nhóm vấn đề chặn nghiệm thu:

1. **An toàn lâm sàng trên luồng đang chạy thật yếu hơn tài liệu mô tả.** Luồng `simple_agent` không có phản xạ cấp cứu nào trước LLM, không có output firewall, và một ca ESI 1 đã khớp tiêu chí vẫn bị giữ lại chờ người bệnh xác nhận (đã sửa hôm nay).
2. **Bảo mật xác thực có lỗ hổng chiếm tài khoản** qua OTP (đã sửa hôm nay), và khoá API Groq/Google đã bị commit lên `origin/main`.
3. **Số liệu đánh giá đang công bố không truy được về lần chạy nào** — vi phạm trực tiếp tiêu chí nghiệm thu "mọi số liệu truy được về script/dataset".
4. **Lõi quyết định ESI gần như không có test chạy được** trên máy nào ngoài máy gốc (đã sửa hôm nay: 0 → 42 test chạy).

---

## 2. Hiện trạng đã kiểm chứng

| Hạng mục | Kết quả | Cách kiểm chứng |
|---|---|---|
| Frontend | Vitest 238/238 qua (31 file), `tsc` sạch, ESLint sạch | Chạy trên working tree, kể cả WIP |
| Backend trước khi sửa | 1.151 qua, 0 lỗi, 59 bỏ qua | `pytest tests/ eval/tests` (75 lỗi ban đầu là do thư mục tạm của Windows, không phải mã) |
| Test lõi `decision.py` | **0/59 chạy được** — bỏ qua vì thiếu `data/siu` | `tests/test_simple_agent.py:48-56` |
| Test chạm luồng sống | ~25/1.151; phần còn lại kiểm thử runtime DeepAgent cũ | Đối chiếu import |
| Corpus trong git | 1.132 khái niệm · 4.247 quan hệ · 1.768 tiêu chí · 238 fact target | `database/migrations/20260901_simple_agent_corpus_data.sql` |
| Corpus mà tài liệu/eval dùng | 243 fact target · 4.260 quan hệ | `docs/OPEN_ISSUE_ESI1_REACHABILITY.md`, manifest golden — **lệch với bundle** |
| Runtime cũ | Vẫn khởi động mỗi lần boot (~5,7 s), shell frontend vẫn gọi API cũ | `src/main.py:39`, layout frontend |
| Mã chưa đồng bộ | 13 commit (16/09) chưa push, chưa merge `main`; WIP health-topics chưa commit | `git log main..HEAD` |

---

## 3. Phát hiện theo mức độ

Ký hiệu trạng thái: **ĐÃ SỬA** (27/10, có test hồi quy) · **CHƯA** · **CẦN QUYẾT ĐỊNH** (thuộc quyền chủ dự án).

### 3.1. P0 — an toàn lâm sàng

| # | Vấn đề | Bằng chứng | Hướng sửa | Trạng thái |
|---|---|---|---|---|
| S1 | Ca đã khớp tiêu chí ESI 1/2 vẫn bị hỏi "còn gì bổ sung không?". Phiên vẫn `ACTIVE`, mà hàng đợi điều dưỡng chỉ lấy phiên `COMPLETED` — người nhà bỏ đi gọi cấp cứu thì ca biến mất. Câu kết luận do LLM viết không hề bảo gọi 115. | `agent.py` (cổng xác nhận sau `decisive_match`), `routes_nurse_simple.py:335`, `prompts.py:333-347` | Chốt ngay khi khớp tất định ESI 1/2; bỏ lời gọi ước lượng tài nguyên; câu kết luận cố định có 115, không qua LLM | **ĐÃ SỬA** |
| S2 | Không có phản xạ cấp cứu tất định nào trước LLM trên luồng sống. "ngất", "xỉu", "co giật", "nôn ra máu", "chảy máu nhiều" chỉ được nhận ra nếu LLM trích xuất đúng. OpenAI lỗi thì người bệnh chỉ nhận "thử lại", không có 115. | `agent.py:712-760`; `_TURN_FAILED_DETAIL` ở `routes_simple_triage.py:63-65` | Lớp sàng lọc trước Phase A: phát hiện → **đưa vào hàng đợi "cần xem ngay" + hiện 115**, không tự gán ESI (giữ đúng hợp đồng: red flag không phải `keyword → ESI`). Thêm 115 vào mọi màn lỗi. | **ĐÃ SỬA** theo khuyến nghị Q3 |
| S3 | Kết quả ESI phụ thuộc thứ hạng ngữ nghĩa: chỉ top 8 tiêu chí theo cosine được xét. Ca SpO2 78 / nhịp thở 42 thoả 3 tiêu chí ESI 1 nhưng trả ESI 2. | `decision.py:20,29,84-98`, `agent.py:879-890` | 38 tiêu chí ESI 1/2 chỉ dựa trên sinh hiệu/tím tái luôn được xét, không phụ thuộc truy xuất, không quyết định câu hỏi. (Không mở rộng cho mọi tiêu chí ESI 1/2: nhiều tiêu chí viết theo chủ đề nhưng điều kiện không chứa chủ đề, ví dụ "đau bụng dữ dội" chỉ cần đau ≥ 8.) | **ĐÃ SỬA** |
| S4 | Không có output firewall: văn bản Phase C và câu trả lời tự do của Phase A đến thẳng người bệnh. Bộ lọc cũ còn để lọt "Bạn bị nhồi máu cơ tim". | `phrasing.py:35-37`, `agent.py:771,783-787` | Bộ lọc tất định chẩn đoán/kê đơn cho mọi chuỗi gửi người bệnh, rơi về câu mẫu khi bị chặn hoặc rỗng | **ĐÃ SỬA** |
| S5 | Bộ bỏ mệnh đề phủ định xoá "not breathing, no pulse" khỏi truy vấn truy xuất — đúng loại tiêu chí ESI 1. | `agent.py:103-127` | Giữ lại mệnh đề mô tả mất chức năng sống; câu chối triệu chứng thường vẫn bị bỏ | **ĐÃ SỬA** |
| S6 | Màn kết quả ESI 1: trang cuộn qua mất kết quả; nút ghim là "Bắt đầu phiên mới", không phải 115; không `role="alert"`. Màn 503 hiện tên biến môi trường cho người bệnh. Không có `error.tsx` nào. | `triage-pilot/page.tsx:206-216,312-324,469-480`, `SimpleEsiResultCard.tsx:38-51` | Ghim `tel:115` cho ESI 1–2, cuộn tới kết quả, màn lỗi chung tiếng Việt có 115 | **ĐÃ SỬA** |
| S7 | Điều dưỡng không có cảnh báo toàn cục cho ca pilot ESI 1/2 (cảnh báo hiện tại đọc hàng đợi cũ). | `GlobalRedFlagAlert.tsx:11,29`, `ClinicalRealtimeProvider.tsx:45` | Lái cảnh báo từ hàng đợi pilot (ESI ≤ 2 hoặc có cờ "cần xem ngay", chưa nhận) | **ĐÃ SỬA** |

### 3.2. P0 — bảo mật

| # | Vấn đề | Bằng chứng | Hướng sửa | Trạng thái |
|---|---|---|---|---|
| A1 | Chiếm tài khoản qua OTP: bỏ trống email thì mã được dò trên mọi tài khoản; không giới hạn số lần thử; mỗi lần "quên mật khẩu" thêm một mã sống. Áp dụng cả tài khoản điều dưỡng/bác sĩ. Đồng thời luồng quên mật khẩu hỏng hẳn: bước kiểm tra mã đã đăng nhập người dùng và tiêu thụ mã, nên bước đổi mật khẩu luôn báo sai mã. | `routes_auth.py` (verify-otp, reset-password), `auth_schemas.py:78,106` | Email bắt buộc; chỉ mã mới nhất còn sống; tối đa 5 lần sai; so sánh hằng thời gian; bước kiểm tra mã khôi phục không mở phiên | **ĐÃ SỬA** |
| A2 | Khoá API Groq và Google viết cứng, đã lên `origin/main` từ commit `114ac14`. | `frontend/test_groq.py:11`, `list_models.py:4`, `test_langchain.py:8,16` (bản HEAD) | **Thu hồi khoá ngay**, xoá ba file, quyết định có viết lại lịch sử không | **CẦN QUYẾT ĐỊNH** Q1 |
| A3 | JWT secret mặc định được chấp nhận ở production; ai biết nó ký được thẻ cho mọi email. | `config.py:106`, `dependencies.py:56-59` | Từ chối khởi động khi `APP_ENV=production` với secret đã công khai hoặc < 32 ký tự | **ĐÃ SỬA** — cần đặt `JWT_SECRET_KEY` trên môi trường deploy trước lần deploy tới |
| A4 | Refresh token (7 ngày) dùng được như access token ở API và WebSocket. | `dependencies.py:43-47`, `routes_ws.py:51` | Chỉ nhận thẻ `type == "access"` | **ĐÃ SỬA** |

### 3.3. P0 — tính trung thực của số liệu và nội dung

| # | Vấn đề | Bằng chứng | Hướng sửa | Trạng thái |
|---|---|---|---|---|
| T1 | Số liệu đánh giá (Accuracy 86,21%, Macro-F1 87,14%, RAGAS 87,2%…) không truy được về lần chạy nào: file kết quả ghi giờ chạy **sau** giờ commit của chính nó ~5 giờ; trạng thái `COMPLETE` mà mã chỉ sinh `COMPLETED`; 10 khoá chỉ số không có trong mã nào của lịch sử git; độ nhạy ESI 1 = 0,889 là không thể với 4 ca ESI 1; artifact thật gần nhất (sha `9b74151`) ghi 14/30 ca sai, có ESI 1 bị đoán thành ESI 3. Các số này đã lan sang slide demo-day, portfolio, báo cáo thực tập. | `eval/results/current_*`, `eval/run.py:231`, `report.py:56-57,110`, `docs/Presentation/DEMO_DAY_SLIDES.md:343-383` | Gỡ hoặc đánh dấu "chưa kiểm chứng"; chạy lại đánh giá thật và commit kèm quan sát từng ca | **CẦN QUYẾT ĐỊNH** Q2 |
| T2 | Bộ đánh giá là vòng tròn: ca vàng sinh từ chính các tiêu chí trong corpus, nhãn là `candidate_esi` của tiêu chí đó. 330/330 ca `PENDING_CLINICAL_REVIEW`. Nó đo độ trung thành trích xuất, không đo giá trị lâm sàng. | `golden_builder.py:286-347,501,523` | Ghi rõ giới hạn này cạnh mọi con số | **CHƯA** |
| T3 | Tuyên bố sai trên giao diện: modal đồng ý nói hệ thống "kích hoạt lệnh cấp cứu 115"; trang EHR nói "AES-256", "E2E PII/PHI" (không có mã mã hoá nào); trang admin ghi "99.6% Precision", "Hallucination <0.01%". | `DisclaimerConsentModal.tsx:119-121`, `EmergencySosManager.tsx:382,410-415,520`, `app/admin/*` | Gỡ theo quy tắc nội dung trung thực của dự án | **ĐÃ SỬA** (nhãn sidebar admin "Concordance Rate" còn lại) |

### 3.4. P1 — vững vàng, vận hành, kiểm thử

| Nhóm | Vấn đề chính | Hướng sửa |
|---|---|---|
| Agent | Client OpenAI dùng mặc định SDK (timeout 600 s, 2 lần thử lại), không có hạn chót cho một lượt; khoá phiên chỉ phủ một phần request (hai request song song có thể ghi đè nhau); trả toàn bộ log tool và ID nội bộ cho người bệnh. | Timeout ~20 s, `max_retries=1`, hạn chót lượt; khoá phiên phủ cả restore/kiểm tra trạng thái; bỏ trường debug khỏi DTO người bệnh |
| Điều dưỡng | Kiểm tra phiên bản khi chốt quyết định không bao giờ kích hoạt (gửi phiên bản mới nhất lúc submit); lỗi nhận ca bị nuốt im lặng; GET hàng đợi tải mọi phiên + N+1 truy vấn và ghi DB. | Chụp phiên bản lúc mở form, xử lý 409; hiện lỗi; lọc/phân trang bằng SQL |
| Xác thực | Không rate limit (đăng nhập, OTP, guest, chat); chat không giới hạn độ dài; cookie không HttpOnly; OAuth thiếu `state`, liên kết theo email chưa xác minh; `seed_demo_accounts.py` không chặn production; nút "gửi lại OTP" giả (chỉ `alert`). | slowapi + `max_length`; nối nút gửi lại vào API; còn lại sau nghiệm thu |
| CI/CD | Smoke test CD chạy không Postgres, không bật agent nên luôn xanh; CD deploy bản build lại chứ không phải image đã test; bộ lọc `paths` sai (`evaluation/**` thay vì `eval/`), thiếu `Dockerfile`; hai "cổng cứng" trỏ tới thư mục không tồn tại. | Smoke test với Postgres + `SIMPLE_AGENT_ENABLED=true` + endpoint readiness; sửa `paths`; bỏ hoặc hiện thực hai cổng |
| Triển khai | Compose duy nhất là cấu hình dev (`--reload`, bind-mount, mật khẩu mặc định); ~630 MB torch/transformers trong image dù luồng sống không cần; phụ thuộc không khoá phiên bản; không có công cụ migration; không có quy trình backup/restore dữ liệu vận hành; `/health` không kiểm tra DB/corpus; log bằng `print`. | Tách `requirements` runtime/ingest; cấu hình production riêng; tắt runtime cũ bằng `DEEPAGENT_RUNTIME_ENABLED=false`; `/health/ready`; runbook backup |
| Dữ liệu | Bundle corpus trong git (238/4.247) lệch với corpus đã dùng để đánh giá (243/4.260); checkout CRLF trên Windows làm lệch hash dataset. | Chốt một phiên bản corpus, xuất lại bundle, `eval/cases/*.jsonl eol=lf` |
| Kiểm thử | 16 test xfail của agent dùng ID giả; không có test hợp đồng HTTP cho start → chat → quyết định điều dưỡng; không có e2e. | Viết lại theo ID thật; thêm test hợp đồng |
| Tài liệu | `ARCHITECTURE.md`, `AGENT_OVERVIEW.md`, `SYSTEM_DATA_DICTIONARY.md`, `RUNBOOK.md`, `.agents/rules/backend-rules.md` mô tả runtime cũ; `AGENTS.md` bắt đọc 3 tài liệu UI không tồn tại. | Viết lại theo `simple_agent` |
| Mã cũ | ~23.000 dòng backend + ~9.400 dòng frontend chỉ phục vụ runtime cũ; shell frontend vẫn gọi API cũ mỗi 10 s. | **Để sau nghiệm thu** — xoá trước khi demo là rủi ro không cần thiết |

---

## 4. Đã thực hiện ngày 27/10 (chưa commit)

| Thay đổi | File | Kiểm chứng |
|---|---|---|
| Test lõi agent chạy trên đúng corpus production, đọc từ SQL bundle đã có trong git, không cần Postgres hay `data/siu` | `src/simple_agent/sql_bundle_corpus.py` (mới), `pg_corpus.py` (tách `corpus_from_rows` dùng chung), 2 file test | 0 → 42 test lõi chạy, 16 xfail còn lại cần viết lại |
| S1: ESI 1/2 chốt ngay, câu kết luận cố định có 115, không gọi LLM | `agent.py`, `phrasing.py` | 4 test mới; 2 test ESI 1/2 **thất bại trên mã cũ** |
| A1: OTP gắn email, tối đa 5 lần sai, chỉ mã mới nhất sống, sửa luồng quên mật khẩu | `routes_auth.py`, `auth_schemas.py`, `db_models.py`, `db.py` (cột `failed_attempts`, thêm tự động khi khởi động) | 6 test API mới; 5/6 **thất bại trên mã cũ** |
| A3, A4: chặn JWT secret công khai ở production; API/WebSocket chỉ nhận access token | `config.py`, `security.py`, `dependencies.py`, `routes_ws.py` | 7 test mới |

Frontend không phải sửa: kiểu trả về của `verifyOtp` vốn đã cho phép phản hồi dạng thông báo.

### Đợt dọn dẹp và đợt 1 (cùng ngày, sau khi chủ dự án duyệt)

| Thay đổi | File | Kiểm chứng |
|---|---|---|
| Dọn repo: gỡ `scratch/` (script một lần chạy thẳng vào DB production) và 3 file Python chứa khoá trong `frontend/` bằng `git rm`; 67 MB ảnh chụp `.tmp-vietnam-ecom-pages/` vào Thùng rác; xoá cache tự sinh (`frontend/.next` 1,1 GB, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `node_modules` gốc, thư mục test rỗng); `.dockerignore`/`.gitignore` chặn chúng quay lại | — | — |
| S2: sàng lọc cấp cứu tất định trước LLM, hướng dẫn 115 cố định, cờ "cần xem ngay" lưu DB **trước** lượt LLM, ca còn `ACTIVE` vẫn lên đầu hàng đợi; không gán ESI, không khoá chat | `simple_agent/emergency_screen.py` (mới), `routes_simple_triage.py`, `routes_nurse_simple.py`, `db_models.py`, `db.py` | 45 test sàng lọc (22 câu nguy kịch phải bắt, 19 câu phủ định/hỏi kiến thức/chuyện cũ/từ dễ nhầm khi bỏ dấu phải im lặng); 4 test HTTP gồm cả khi OpenAI lỗi |
| S3: 38 tiêu chí ESI 1/2 theo sinh hiệu luôn được xét | `corpus.py`, `agent.py` | Ca SpO2 78 / nhịp thở 42: trước sửa ra `ASK_NEXT` không khớp mức nào, sau sửa ra ESI 1 |
| S4: lớp chặn đầu ra cho Phase C và câu trả lời tự do của Phase A | `simple_agent/output_guard.py` (mới), `agent.py` | 23 test module + 2 test mức agent |
| S5: giữ mệnh đề mất chức năng sống trong truy vấn | `agent.py` | 5 test |
| Timeout 30 s / thử lại 1 lần cho mọi lời gọi OpenAI ngoài Phase A (trước là mặc định SDK 600 s) | `agent.py`, `deepagent_understanding.py` | — |
| S6, S7, T3 phía frontend; thanh 115 trên ô nhập khi lượt có cờ; huy hiệu "Cần xem ngay" ở hàng đợi và hồ sơ ca | `frontend/src/...` | Vitest 238 → 261, `tsc` và ESLint sạch |

Kết quả cuối ngày: backend **1.284 qua, 0 lỗi** (16 xfail cũ); frontend **261/261**.

---

## 5. Kế hoạch theo đợt

Gợi ý người phụ trách theo vai trò trong báo cáo dự án: **Việt** (Lead/Agent), **Tuấn Việt** (Full-stack), **Đại** (Evaluation/Tester), **Phong** (CI/CD/Support). Ước lượng là giờ làm của một người.

### Đợt 0 — Ngay hôm nay và ngày mai (27–28/10)

| Việc | Phụ trách | Ước lượng | Xong khi |
|---|---|---:|---|
| Thu hồi khoá Groq/Google, xoá 3 file Python trong `frontend/` | Việt | 0,5 | Khoá cũ bị vô hiệu ở trang quản trị nhà cung cấp |
| Đặt `JWT_SECRET_KEY` thật trên môi trường deploy | Phong | 0,5 | Backend production khởi động được với bản vá mới |
| Review và commit các thay đổi ngày 27/10, push nhánh, mở PR vào `main` | Việt, Tuấn Việt | 1 | CI xanh trên self-hosted runner |
| Gỡ tuyên bố sai trên UI (T3) | Tuấn Việt | 2 | Không còn chuỗi nào trong danh sách cấm ở giao diện |
| Gỡ hoặc đánh dấu số liệu chưa kiểm chứng (T1) trong `docs/evaluation.md`, `eval/results/`, slide, portfolio | Đại, Việt | 1,5 | Theo quyết định Q2 |

### Đợt 1 — An toàn lâm sàng còn lại (28–30/10) — **đã hoàn thành sớm ngày 27/10, xem mục 4**

| Việc | Phụ trách | Ước lượng | Xong khi |
|---|---|---:|---|
| S3: tập tiêu chí ESI 1/2 luôn được xét | Việt | 4 | Ca SpO2 78 / nhịp thở 42 trả ESI 1 trong test dùng corpus thật |
| S2: sàng lọc trước LLM → hàng đợi "cần xem ngay" + 115; 115 ở mọi đường lỗi | Việt | 6 | "con tôi ngất xỉu", "nôn ra máu" hiện 115 ngay cả khi OpenAI bị tắt |
| S4: output firewall cho mọi chuỗi gửi người bệnh | Việt | 3 | "Bạn bị nhồi máu cơ tim" và kê liều thuốc đều bị chặn, có câu mẫu thay thế |
| S5: sửa bộ bỏ mệnh đề phủ định | Việt | 1 | "not breathing, no pulse" còn trong truy vấn |
| S6: màn kết quả ESI 1/2 và màn lỗi phía người bệnh, `error.tsx` | Tuấn Việt | 4 | Nút `tel:115` luôn trong tầm mắt ở mobile; không còn chữ kỹ thuật |
| S7: cảnh báo toàn cục cho điều dưỡng từ hàng đợi pilot | Tuấn Việt | 2 | Ca ESI ≤ 2 chưa nhận hiện cảnh báo ở mọi trang lâm sàng |
| Timeout OpenAI ~20 s và hạn chót cho một lượt | Việt | 1 | Lượt chậm kết thúc bằng lỗi có 115 thay vì treo |

### Đợt 2 — Bằng chứng đánh giá thật (29–31/10)

| Việc | Phụ trách | Ước lượng | Xong khi |
|---|---|---:|---|
| Chốt một phiên bản corpus; xuất lại bundle hoặc dựng lại manifest; `.gitattributes` cho dataset | Đại, Việt | 2 | Preflight của `eval/run.py` qua trên DB dựng từ repo |
| Chạy tầng tất định trên 30 ca (và 300 ca nếu kịp), commit quan sát từng ca + metadata thật | Đại | 3 + thời gian chạy | Mọi con số trong báo cáo trỏ được tới một `run_id` có trong repo |
| Viết rõ giới hạn: đánh giá vòng tròn, nhãn chưa qua chuyên gia | Đại | 1 | Có ngay cạnh mọi bảng số |
| Viết lại 16 test xfail theo ID thật; test hợp đồng HTTP start → chat → quyết định điều dưỡng | Đại | 4 | 0 xfail ở `test_simple_agent.py` |

Lưu ý chi phí: theo commit `1c4ff5c`, một ca mất khoảng 5 phút; 300 ca chạy tuần tự gần một ngày, có `--concurrency` để rút ngắn. Chi phí OpenAI chưa được đo — cần duyệt (Q2).

### Đợt 3 — Hardening và triển khai (30/10–01/11)

| Việc | Phụ trách | Ước lượng |
|---|---|---:|
| Rate limit đăng nhập/OTP/guest/chat, `max_length` cho tin nhắn, nối nút "gửi lại OTP" | Tuấn Việt | 3 |
| Tách `requirements` runtime/ingest, khoá phiên bản; tắt runtime cũ ở production bằng cờ | Phong | 2 |
| CD: smoke test với Postgres + agent bật + `/health/ready`; deploy đúng image đã test; sửa `paths` CI | Phong | 4 |
| Cấu hình production (không `--reload`, không mật khẩu mặc định); runbook backup/restore dữ liệu vận hành; chặn `seed_demo_accounts.py` ở production | Phong | 3 |
| Điều dưỡng: chụp phiên bản khi mở form quyết định, hiện lỗi nhận ca, khoá idempotency cho lượt chat | Tuấn Việt | 3 |

### Đợt 4 — Tài liệu, chạy thử, đóng băng mã (02–05/11)

| Việc | Phụ trách | Ước lượng |
|---|---|---:|
| Viết lại `ARCHITECTURE.md`, `AGENT_OVERVIEW.md`, `SYSTEM_DATA_DICTIONARY.md`, `RUNBOOK.md`, `backend-rules.md`; sửa tham chiếu hỏng trong `AGENTS.md` | Việt | 4 |
| Dry-run ba kịch bản (red flag, cần hỏi thêm, chuyển điều dưỡng) trên máy sạch, chỉ theo `SETUP.md` | Cả nhóm | 2 |
| Đóng băng mã ít nhất 48 giờ trước nghiệm thu | Cả nhóm | — |

### Sau nghiệm thu

Xoá runtime cũ và mã chỉ phục vụ nó (sau khi tách 5 điểm shell frontend còn gọi API cũ), cookie HttpOnly, OAuth `state`, chạy nhiều worker (session/event bus dùng chung), log có cấu trúc, rà soát accessibility (chữ 10–11 px, nút < 44 px).

---

## 6. Quyết định cần chủ dự án

| # | Câu hỏi | Khuyến nghị |
|---|---|---|
| Q1 | Thu hồi khoá đã lộ là bắt buộc. Có viết lại lịch sử git để xoá khoá khỏi `origin` không? | Thu hồi ngay; viết lại lịch sử là tuỳ chọn vì khoá đã thu hồi thì vô hại, mà viết lại sẽ buộc cả nhóm clone lại |
| Q2 | Với số liệu đánh giá hiện có: gỡ ngay, hay giữ nhưng đánh dấu "chưa kiểm chứng" cho tới khi chạy lại? Có duyệt chi phí OpenAI cho lần chạy thật không? | Gỡ khỏi slide/portfolio ngay; chạy lại tầng tất định trên 30 ca rồi mới công bố số mới |
| Q3 | Khi lời kể có dấu hiệu nguy kịch nhưng chưa đủ căn cứ cho ESI 1 (câu hỏi số 3 trong `docs/OPEN_ISSUE_ESI1_REACHABILITY.md`): giữ `RETURN_INCOMPLETE` hay chủ động đẩy lên hàng đợi điều dưỡng? | Đẩy lên hàng đợi với cờ "cần xem ngay", không gán ESI, và hiện 115 — **đã triển khai theo khuyến nghị này ngày 27/10**; từ vựng sàng lọc vẫn là `PENDING_CLINICAL_REVIEW` |
| Q4 | Nhánh hiện tại (13 commit + WIP health-topics) đi vào `main` thế nào? | Tách WIP health-topics thành PR riêng; các bản vá an toàn/bảo mật đi PR riêng, ưu tiên merge trước |
| Q5 | Xoá runtime cũ trước hay sau nghiệm thu? | Sau — đổi lại được demo ổn định; trước nghiệm thu chỉ tắt nó ở production bằng cờ |

---

## 7. Không làm trong hai tuần này, và lý do

- **Không nới lỏng trường `CLINICIAN_ONLY`** để mở thêm đường tới ESI 1 — đó là quyết định lâm sàng (xem `docs/OPEN_ISSUE_ESI1_REACHABILITY.md`).
- **Không điền tên người duyệt hay trạng thái phê duyệt** vào corpus hoặc ca vàng để qua cổng kiểm tra.
- **Không đổi model mặc định** (`gpt-4.1-mini`) — toàn bộ prompt đã được tinh chỉnh trên model này.
- **Không viết lại kiến trúc agent** — lõi tất định đúng hướng; việc còn lại là lấp các lớp an toàn quanh nó.
