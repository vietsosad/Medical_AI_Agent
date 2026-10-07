# Kế hoạch xử lý 4 nhóm tài liệu thành bộ Triage Protocol mô phỏng

## 1. Quyết định phạm vi

- Mục tiêu: tạo một corpus **mô phỏng, có nguồn và truy vết được** để demo RAG hỗ trợ phân loại ESI và phát hiện dấu hiệu nguy cấp.
- Không dùng LLM để tự viết phác đồ mới. LLM chỉ trích xuất, chuẩn hóa, dịch nháp và kiểm tra chéo nội dung đã có trong PDF.
- ESI v4 có thể dùng cho demo khi chưa có v5, nhưng toàn bộ dữ liệu và giao diện phải ghi rõ `ESI_V4_SIMULATION`; không gọi đây là guideline mới nhất hoặc phác đồ đã được bệnh viện phê duyệt.
- Chưa chạy OCR, LLM, embedding hoặc ghi database trong bước lập kế hoạch này.

Trong thư mục hiện có 5 PDF nhưng được tính là 4 nhóm nguồn:

| Nhóm | Tệp | Vai trò trong corpus |
|---|---|---|
| 1. ESI v4 | `raw/ena/AHRQ_ESI_v4_2012_Implementation_Handbook.pdf` | Nguồn chính duy nhất để mô phỏng kết luận ESI 1–5 và lý do theo các decision point của ESI v4 |
| 2. Bộ Y tế | `raw/vn_byt/BYT_QD79_2026_Huong_dan_cap_cuu.pdf` | Dấu hiệu cấp cứu và bối cảnh Việt Nam; không tự ánh xạ sang ESI |
| 3. WHO IITT theo tuổi | `raw/who_iitt/WHO_IITT_Age_12_Plus.pdf`, `WHO_IITT_Age_Under_12.pdf` | Lớp kiểm tra an toàn theo người lớn/trẻ em và các mức Đỏ/Vàng/Xanh; không đổi trực tiếp thành ESI |
| 4. WHO IITT Reference Card | `raw/who_iitt/WHO_IITT_Reference_Card.pdf` | Giải nghĩa các dấu hiệu như suy hô hấp, chấn thương, bỏng, ngộ độc và chi bị đe dọa |

## 2. Nguyên tắc tạo bộ dữ liệu “sát nhất”

1. **ESI phải dựa trên ESI v4.** BYT và WHO chỉ bổ sung red flag, câu hỏi cần hỏi và bằng chứng an toàn.
2. **Không trộn thang điểm.** IITT Đỏ/Vàng/Xanh không được model tự quy đổi thành ESI 1–5.
3. **Mọi tiêu chí đều có nguồn.** Mỗi record phải giữ PDF, trang, section và đoạn bằng chứng gốc.
4. **Không cho model sáng tác ngưỡng.** Dấu `<`, `>`, `≤`, `≥`, đơn vị, tuổi và nhóm đối tượng phải khớp tài liệu.
5. **Case MIETIC chỉ là ví dụ tương tự.** `metadata_json.esi_level` hỗ trợ tham khảo nhưng không thay thế tiêu chí từ ESI v4.
6. **Bản gốc là chuẩn đối chiếu.** Bản dịch tiếng Việt chỉ được dùng sau khi kiểm tra thuật ngữ và ý nghĩa lâm sàng.

## 3. Pipeline xử lý đề xuất

### Bước 1 — Đóng băng và đăng ký nguồn

- Giữ nguyên PDF trong `data/protocol_corpus/raw/`, không sửa file gốc.
- Lưu SHA-256, tên tài liệu, phiên bản, ngày tải, cơ quan ban hành, giấy phép và phạm vi sử dụng.
- Đánh dấu ESI v4 là `simulation_only`; WHO phải giữ attribution/license; BYT phải giữ số quyết định và trạng thái hiệu lực.

Đầu ra: `data/protocol_corpus/source_registry/protocol_sources.json`.

### Bước 2 — Trích xuất và kiểm tra PDF

- ESI v4: dùng text layer, giữ nguyên chapter, table và decision point.
- BYT: chạy OCR/kiểm tra trực quan các trang có cảnh báo font hoặc ảnh để tránh mất tiêu chí.
- WHO IITT: trích xuất theo vùng trên poster; đối chiếu trực quan vì thứ tự đọc của PDF một trang có thể sai.
- Loại header/footer lặp nhưng không sửa câu lâm sàng.

Đầu ra: `data/protocol_corpus/extracted/<source_id>/*.md` kèm page anchor.

### Bước 3 — Chia chunk theo đơn vị quyết định

Không chia máy móc theo số token. Mỗi chunk chỉ nên chứa một đơn vị độc lập:

- một decision point ESI;
- một nhóm red flag có cùng kết quả;
- một bảng sinh hiệu kèm tuổi/đơn vị;
- một định nghĩa hoặc ngoại lệ;
- một quy tắc áp dụng cho người lớn hoặc trẻ em.

Mỗi chunk giữ tối thiểu:

```json
{
  "citation_id": "ENA_ESI4__DECISION_B__Pxx",
  "source_family": "ESI_V4",
  "document_type": "protocol_simulation",
  "population": ["adult"],
  "clinical_use": ["ESI_DECISION_SUPPORT"],
  "original_text": "...",
  "vi_text": "...",
  "decision_criteria": [],
  "page": 0,
  "section": "...",
  "validation_status": "candidate",
  "simulation_only": true
}
```

### Bước 4 — Dùng OpenAI theo hai lượt

**Lượt A — trích xuất giá rẻ:** dùng `gpt-4o-mini` với Structured Outputs để tạo candidate JSON, keywords, bản dịch nháp và cờ lỗi OCR.

**Lượt B — kiểm tra phần quan trọng:** dùng `gpt-5-mini` chỉ cho chunk có decision point, ngưỡng sinh hiệu, pediatric rule, mâu thuẫn hoặc cờ OCR. Model phải so sánh từng criterion với evidence span, không dùng kiến thức ngoài nguồn.

Quy tắc reject tự động:

- thiếu trang/section hoặc evidence span;
- model tạo tiêu chí không xuất hiện trong nguồn;
- mất đơn vị, toán tử so sánh hoặc nhóm tuổi;
- trộn ESI với IITT/BYT;
- kết luận ESI chỉ dựa trên case MIETIC.

Đầu ra: `data/protocol_corpus/review/protocol_candidates.jsonl` và `protocol_rejected.jsonl`.

### Bước 5 — Review con người và tạo bản phát hành mô phỏng

- Data QA đối chiếu OCR, trang, hash và cấu trúc.
- Người có chuyên môn kiểm tra criterion, population, bản dịch và lý do ESI.
- Record đạt yêu cầu chuyển thành `simulation_reviewed`; không dùng tên trạng thái `clinically_validated` nếu chưa có phê duyệt chính thức.
- Tạo báo cáo khác biệt, record bị loại và người/thời điểm duyệt.

Đầu ra chính:

```text
data/protocol_corpus/manifests/candidate/triage_protocol_simulation_v1.jsonl
data/protocol_corpus/reports/triage_protocol_simulation_v1_review.md
data/protocol_corpus/eval/triage_protocol_simulation_v1_cases.jsonl
```

### Bước 6 — Embedding và tích hợp demo

- Tiếp tục dùng `BAAI/bge-m3` để tương thích vector 1024 chiều hiện tại; không cần trả phí OpenAI embedding.
- Phải pin đúng `EMBEDDING_MODEL_REVISION` trước khi tạo vector mới. Nếu vector MIETIC cũ không xác định được revision, đo lại retrieval hoặc re-embed một phiên bản corpus thống nhất.
- Chưa cần tạo thêm bảng. Có thể dùng `triageknowledgebase` cho demo **chỉ sau khi** retriever lọc bắt buộc theo `metadata_json.document_type`:
  - `protocol_simulation`: bằng chứng guideline;
  - `case_example`: ca MIETIC tham khảo.
- LLM kết luận sơ bộ ESI từ các chunk `ESI_V4`; BYT/IITT chỉ kích hoạt cảnh báo và bổ sung lý do. Nếu không có đủ bằng chứng ESI, agent phải nêu dữ kiện còn thiếu và chuyển HITL.
- UI hiển thị: **“Kết luận mô phỏng theo ESI v4 — cần điều dưỡng xác nhận”** và citation trang nguồn.

Không ingest protocol trước khi có bộ lọc `document_type`, vì nếu truy hồi lẫn guideline và case thì model có thể coi nhãn MIETIC là quy tắc lâm sàng.

### Bước 7 — Kiểm thử trước demo

Tạo khoảng 40–60 ca kiểm thử, gồm người lớn, trẻ em, red flag, sinh hiệu sát ngưỡng, thiếu dữ kiện và câu hỏi tiếng Việt có lỗi chính tả. Điều kiện đạt đề xuất:

- 100% kết luận có citation đến đúng trang/section;
- 0 tiêu chí hoặc ngưỡng do LLM tự tạo;
- 0 phép quy đổi IITT thành ESI;
- Recall@5 của chunk liên quan tối thiểu 90% trên gold set nội bộ;
- mọi ESI cuối cùng vẫn cần HITL xác nhận.

Đây là tiêu chí chất lượng kỹ thuật cho demo, không phải chứng nhận an toàn lâm sàng.

## 4. Ước lượng chi phí OpenAI

Corpus hiện có khoảng 75.000 từ; sau chunking, prompt lặp, dịch và kiểm tra, nên dự trù khoảng 0,8–1,5 triệu input tokens và 0,2–0,4 triệu output tokens cho toàn bộ các lượt.

Giá tham chiếu tại ngày 2026-08-14:

- [`gpt-4o-mini`](https://developers.openai.com/api/docs/models/gpt-4o-mini): $0,15/1M input tokens và $0,60/1M output tokens.
- [`gpt-5-mini`](https://developers.openai.com/api/docs/models/gpt-5-mini): $0,25/1M input tokens và $2,00/1M output tokens.
- [Batch API](https://developers.openai.com/api/docs/guides/batch): giảm khoảng 50% chi phí nếu chấp nhận xử lý bất đồng bộ trong 24 giờ.
- BGE-M3 chạy local: $0 chi phí API, không tính máy/điện.

| Hạng mục | Model | Chi phí dự kiến |
|---|---|---:|
| Trích xuất, dịch nháp, keywords | GPT-4o mini | $0,15–$0,35 |
| Kiểm tra chunk rủi ro cao | GPT-5 mini | $0,30–$0,90 |
| Sinh bộ query/eval và retry | GPT-4o mini | $0,10–$0,30 |
| **Tổng dự kiến, API thường** |  | **$0,55–$1,55** |
| **Tổng dự kiến nếu dùng Batch** |  | **$0,28–$0,78** |

Nên duyệt ngân sách tối đa **$2** cho lần chạy đầu để có dư địa retry. Chi phí chưa gồm OCR cloud, nhân sự review y khoa/pháp lý và hạ tầng local. Phần tốn kém thực tế sẽ là review chuyên môn, không phải token.

## 5. Thứ tự thực hiện sau khi duyệt

1. Tạo source registry và xác minh quyền sử dụng.
2. Extract/OCR và QA trực quan cả 5 PDF.
3. Chunk theo decision point và chạy GPT-4o mini bằng Batch.
4. Chỉ gửi chunk rủi ro cao qua GPT-5 mini.
5. Review con người, đóng băng manifest `simulation_v1`.
6. Embed bằng đúng revision của BGE-M3.
7. Chạy gold-set retrieval và kiểm tra lý do/citation.
8. Chỉ sau khi đạt điều kiện mới ingest vào luồng demo có cờ `simulation_only`.

## 6. Code đã chuẩn bị và cách chạy sau này

Pipeline nằm tại `scripts/build_triage_protocol_simulation.py`. Key chỉ được đọc từ `.env`:

```dotenv
OPENAI_API_KEY=sk-...key-của-bạn...
PROTOCOL_OPENAI_EXTRACTION_MODEL=gpt-4o-mini
PROTOCOL_OPENAI_VERIFICATION_MODEL=gpt-5-mini
```

Khi duyệt chạy, thực hiện tuần tự và kiểm tra đầu ra sau từng lệnh:

```bash
python scripts/build_triage_protocol_simulation.py extract
python scripts/build_triage_protocol_simulation.py prepare-extraction
python scripts/build_triage_protocol_simulation.py submit-extraction
python scripts/build_triage_protocol_simulation.py download-extraction
python scripts/build_triage_protocol_simulation.py parse-extraction
python scripts/build_triage_protocol_simulation.py prepare-verification
python scripts/build_triage_protocol_simulation.py submit-verification
python scripts/build_triage_protocol_simulation.py download-verification
python scripts/build_triage_protocol_simulation.py parse-verification
python scripts/build_triage_protocol_simulation.py build-review-package
```

Các lệnh `submit-*` và `download-*` mới truy cập OpenAI. Pipeline dừng tại
`pending_human_review`, không embedding và không ghi database.

## 7. Kết luận

ESI v4 **đủ để làm bản demo mô phỏng sát nguồn** nếu được đặt đúng phiên bản và không bị trộn với BYT/IITT. Phương án phù hợp nhất hiện tại là dùng ESI v4 làm logic ESI, WHO/BYT làm lớp an toàn, BGE-M3 cho retrieval và OpenAI hai lượt cho trích xuất + kiểm tra. Không cần tìm thêm tài liệu trước khi hoàn thành và đánh giá corpus `simulation_v1`; chỉ cân nhắc ESI v5 hoặc protocol bệnh viện khi chuyển sang thử nghiệm lâm sàng/production.
