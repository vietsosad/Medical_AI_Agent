# Xử lý bộ triage protocol khi chưa có chuyên gia lâm sàng

## 1. Kết luận ngắn

Khi chưa có bác sĩ hoặc điều dưỡng đủ thẩm quyền, dự án **không thể tuyên bố bộ dữ liệu đã được phê duyệt lâm sàng**. Tuy nhiên, vẫn có thể tạo một allowlist phục vụ **demo kỹ thuật với dữ liệu/tình huống giả lập**, nếu mọi bản ghi đều vượt qua kiểm tra nguồn, được gắn `simulation_only=true`, và không được dùng để tự động quyết định chăm sóc người bệnh thật.

File đầu vào duy nhất cần xử lý là:

`data/protocol_corpus/work/simulation_v1/protocol_review_package.jsonl`

Kết quả hiện tại:

| Quyết định | Số lượng | Cách xử lý |
|---|---:|---|
| `llm_verified` | 1 | Kiểm tra nguồn cơ học; có thể đưa vào allowlist demo giả lập |
| `manual_review` | 9 | Kiểm tra nguồn thủ công và chạy verifier phản biện; chưa được đưa vào RAG |
| `reject` | 5 | Loại khỏi corpus; chỉ sinh lại khi đã sửa nguyên nhân |

### Kết quả đã tạo ngày 14/08/2026

Pipeline đã thực hiện cổng documentary review không có chuyên gia và xuất:

- `protocol_demo_allowlist.jsonl`: 1 candidate được phép dùng cho demo nội bộ;
- `protocol_demo_review_queue.jsonl`: 9 candidate tiếp tục bị chặn;
- `protocol_demo_excluded.jsonl`: 5 candidate bị loại;
- `protocol_demo_allowlist_summary.json`: báo cáo tổng hợp và phạm vi sử dụng.

Không có database write, embedding call hoặc phê duyệt lâm sàng trong bước này.

## 2. Những việc người không có chuyên môn y tế vẫn có thể kiểm tra

Đây là kiểm tra tài liệu và dữ liệu, không phải đánh giá tính đúng đắn lâm sàng.

Với từng candidate, mở PDF trong `data/protocol_corpus/raw/`, sau đó kiểm tra:

1. `source_id`, `page_start`, `page_end` và `evidence_page` trỏ đúng tài liệu/trang.
2. Mỗi `evidence_quote` xuất hiện nguyên văn trên trang nguồn, không ghép hai đoạn và không dùng dấu `...` để bỏ nội dung.
3. Mọi con số, dấu `<`, `>`, `<=`, `>=`, đơn vị, độ tuổi và khoảng giá trị được giữ nguyên.
4. `triage_system` không trộn ESI, WHO IITT và hướng dẫn của Bộ Y tế.
5. WHO `RED/YELLOW/GREEN` không bị chuyển thành ESI 1–5 và tiêu chí không bị đặt nhầm cột.
6. Bản dịch tiếng Việt không thêm chẩn đoán, thuốc, kết luận hoặc ngưỡng mới.
7. Nội dung không đến từ bài tập, đáp án, ca minh họa hoặc phần lịch sử tài liệu.

Nếu không chắc bất kỳ mục nào, giữ candidate ở trạng thái `blocked`.

## 3. Quy trình tạm thời không cần chuyên gia

### Bước 1 — Giữ nguyên dữ liệu gốc và trạng thái audit

Không sửa trực tiếp các file sau:

- `protocol_review_package.jsonl`
- `protocol_verifications.jsonl`
- `protocol_rejected.jsonl`
- `source_registry.json`

Mọi lần xử lý tiếp theo phải tạo file mới và giữ `candidate_id`, `source_sha256`, trang nguồn cùng trích dẫn.

### Bước 2 — Loại ngay nhóm `reject`

Năm candidate có `llm_verification.decision="reject"` không được embedding, không được import database và không được hiển thị như guideline. Không dùng biểu quyết đa số LLM để cứu một candidate đã có lỗi nguồn hoặc lỗi triage category.

### Bước 3 — Kiểm tra cơ học candidate `llm_verified`

Candidate duy nhất đang là `llm_verified` vẫn cần người phụ trách dự án hoàn thành checklist ở mục 2. Nếu tất cả đều đạt, có thể gắn trạng thái nội bộ:

```json
{
  "demo_status": "demo_eligible_nonclinical",
  "simulation_only": true,
  "clinical_approval": false,
  "review_method": "documentary_source_check_without_clinician"
}
```

Trạng thái này chỉ cho phép dùng trong demo giả lập; nó không đồng nghĩa với `clinically_approved`.

### Bước 4 — Xử lý chín candidate `manual_review`

Thực hiện theo thứ tự:

1. Người phụ trách dự án kiểm tra bảy mục ở phần 2.
2. Chạy một verifier phản biện độc lập, chỉ được đọc candidate và đúng các trang nguồn liên quan.
3. Verifier phải trả structured output cho từng criterion: nguồn hỗ trợ, quote chính xác, số/ngưỡng giữ nguyên, đúng hệ triage và danh sách lỗi.
4. Chỉ candidate có **tất cả criterion đạt ở cả validator cứng và verifier phản biện** mới được chuyển thành `demo_eligible_nonclinical`.
5. Candidate có bất kỳ bất đồng, OCR/layout không rõ hoặc lỗi số phải tiếp tục `blocked`.

LLM thứ hai chỉ giúp phát hiện lỗi; nó không thay thế phê duyệt của chuyên gia.

### Bước 5 — Tạo allowlist riêng cho demo

Không embedding trực tiếp `protocol_candidates.jsonl` hoặc toàn bộ `protocol_review_package.jsonl`. Chỉ xuất các candidate đạt điều kiện sang file mới:

`data/protocol_corpus/work/simulation_v1/protocol_demo_allowlist.jsonl`

Mỗi bản ghi allowlist phải có tối thiểu:

- `candidate_id`, `source_id`, `source_sha256`;
- `page_start`, `page_end`, `evidence_quote`;
- `demo_status="demo_eligible_nonclinical"`;
- `simulation_only=true` và `clinical_approval=false`;
- phiên bản pipeline, prompt và model verifier;
- thời điểm kiểm tra cùng tên/người chịu trách nhiệm kiểm tra tài liệu.

## 4. Phạm vi demo được phép

Allowlist tạm thời chỉ nên dùng cho:

- tình huống giả lập hoặc test case không chứa dữ liệu người bệnh thật;
- trình diễn retrieval, citation, giải thích nguồn và quy trình HITL;
- gợi ý câu hỏi cần thu thập thêm;
- hiển thị “gợi ý sơ bộ, cần điều dưỡng xác nhận”.

Không được dùng để:

- tự động kết luận ESI cho người bệnh thật;
- đưa ra chẩn đoán hoặc chỉ định thuốc;
- thay thế điều dưỡng/bác sĩ;
- quảng bá bộ dữ liệu là guideline đã được thẩm định;
- cho phép agent tự tạo ngưỡng khi retrieval không tìm thấy nguồn.

Red-flag detector dạng luật cứng và nút gọi `115` vẫn phải hoạt động độc lập trước LLM. Khi không tìm thấy candidate đủ nguồn, agent phải trả fallback an toàn và chuyển sang điều dưỡng, không được suy diễn thêm.

## 5. Tiêu chí dừng

Không đưa candidate vào allowlist nếu xảy ra một trong các trường hợp:

- nguồn/trang/quote không xác minh được;
- PDF cần visual review nhưng chưa được đối chiếu;
- số, toán tử, đơn vị hoặc độ tuổi không khớp;
- outcome không có trong nguồn;
- sai population hoặc sai cột WHO;
- hai verifier bất đồng;
- candidate yêu cầu diễn giải chuyên môn để quyết định đúng/sai.

## 6. Khi có chuyên gia sau này

Chuyên gia cần review lại 100% allowlist demo, ưu tiên trước các rule ESI, pediatric, red flag và mọi tiêu chí có ngưỡng số. Chỉ sau khi có bằng chứng phê duyệt, phiên bản nguồn và người duyệt, bản ghi mới được chuyển từ `demo_eligible_nonclinical` sang một trạng thái phê duyệt lâm sàng do dự án định nghĩa.

Cho đến thời điểm đó, phương án an toàn nhất là: **demo được hệ thống tìm nguồn và giải thích, không demo rằng hệ thống đã thay chuyên gia ra quyết định y tế**.
