# BÁO CÁO TIẾN ĐỘ DỰ ÁN KHOA HỌC VÀ CÔNG NGHỆ

## TUẦN 3 — THIẾT KẾ KHO DỮ LIỆU, ONTOLOGY VÀ QUY TRÌNH RAG

**Tên đề tài:** MedTriage AI — Hệ thống hỗ trợ tiếp nhận và phân luồng ưu tiên y tế  
**Người thực hiện:** Lê Hoàng Việt  
**Tuần thực hiện:** Tuần 3/15  
**Thời gian:** 10/08/2026 – 16/08/2026  
**Báo cáo liên kết:** Báo cáo Tuần 2 — Đặc tả yêu cầu, luồng nghiệp vụ và tiêu chí an toàn  
**Trạng thái:** Hoàn thành thiết kế dữ liệu và hướng dẫn chuẩn hóa ban đầu

> **Lưu ý phạm vi:** Đây là báo cáo cá nhân của Lê Hoàng Việt. Tuần 3 tập trung vào việc thiết kế dữ liệu và kho tri thức phục vụ nghiên cứu. Các nguồn dữ liệu chưa được xem là căn cứ lâm sàng chính thức nếu chưa qua kiểm tra thẩm quyền, phạm vi và trạng thái phê duyệt.

---

## 1. MỤC TIÊU TUẦN 3

Theo kế hoạch đã đặt ra ở tuần 2, tôi tập trung hoàn thiện nền tảng dữ liệu cho MedTriage AI. Các mục tiêu chính gồm:

1. Xác định các loại dữ liệu cần có trong hệ thống.
2. Thiết kế cấu trúc metadata cho tài liệu và protocol.
3. Xây dựng ontology ban đầu gồm concept, alias, quan hệ và fact target.
4. Thiết kế protocol atom để máy có thể đối chiếu theo điều kiện rõ ràng.
5. Định nghĩa quy tắc provenance, citation và versioning.
6. Thiết kế pipeline từ tài liệu gốc đến dữ liệu có thể truy xuất.
7. Xác định cách tách dữ liệu tham khảo, dữ liệu demo và dữ liệu đủ điều kiện hỗ trợ đề xuất ESI.

---

## 2. VẤN ĐỀ DỮ LIỆU CỦA ĐỀ TÀI

Bài toán của MedTriage AI không chỉ là đưa một tài liệu y khoa vào vector database. Hệ thống cần biết tài liệu nào được phép làm căn cứ, tài liệu nào chỉ dùng để tham khảo, dữ kiện nào đã được người dùng xác nhận và tiêu chí nào thực sự được thỏa mãn.

Nếu không thiết kế dữ liệu ngay từ đầu, hệ thống có thể gặp các lỗi sau:

- Truy xuất được tài liệu có nội dung gần giống nhưng không có thẩm quyền.
- Dùng case mô phỏng làm căn cứ thay cho protocol đã được phê duyệt.
- Không truy ngược được một đề xuất ESI đến nguồn và tiêu chí cụ thể.
- Nhầm giữa triệu chứng người dùng đã nói và triệu chứng hệ thống tự suy đoán.
- Trộn dữ liệu demo với dữ liệu dùng cho luồng production.
- Khi nguồn bị thiếu hoặc chưa được phê duyệt, hệ thống vẫn cố tạo kết luận.

Vì vậy, trong tuần 3 tôi xác định rằng **độ liên quan của kết quả truy xuất và thẩm quyền của nguồn là hai điều kiện độc lập**. Một tài liệu giống câu hỏi chưa chắc đủ điều kiện để hỗ trợ quyết định.

---

## 3. KIẾN TRÚC DỮ LIỆU ĐƯỢC ĐỀ XUẤT

### 3.1. Ba khối dữ liệu cốt lõi

| Khối dữ liệu | Vai trò | Trạng thái sử dụng |
|---|---|---|
| Kho protocol/guideline | Cung cấp tiêu chí phân luồng và bằng chứng | Chỉ được hỗ trợ ESI khi qua authority gate |
| Ontology lâm sàng | Chuẩn hóa concept, alias, quan hệ và dữ kiện cần hỏi | Dùng để hiểu ngôn ngữ và lập kế hoạch hỏi |
| Benchmark/evaluation set | Đo chất lượng hội thoại và quyết định | Dùng cho kiểm thử, không làm nguồn protocol |

Ngoài ba khối trên, tôi bổ sung một lớp metadata chung để quản lý nguồn, phiên bản, phạm vi, trạng thái phê duyệt và đường dẫn citation.

### 3.2. Luồng dữ liệu tổng quát

```text
Tài liệu gốc có nguồn
        │
        ▼
Trích xuất và chia nhỏ nội dung
        │
        ▼
Chuẩn hóa metadata + protocol atom
        │
        ▼
Kiểm tra schema, citation và quyền sử dụng
        │
        ├── Chưa đạt → giữ ở trạng thái pending/rejected
        │
        └── Đạt → nạp vào kho được phép truy xuất
                         │
                         ▼
             Hybrid retrieval theo facts đã xác nhận
                         │
                         ▼
                  Authority/evidence gate
                         │
             ┌───────────┴───────────┐
             │                       │
       Đủ điều kiện              Chưa đủ điều kiện
             │                       │
     Tạo evidence/citation       Fail-closed, chuyển HITL
```

### 3.3. Hướng lưu trữ

Định hướng lưu trữ là PostgreSQL kết hợp pgvector để giữ dữ liệu quan hệ, metadata và embedding trong cùng một hệ thống. Cách này giúp liên kết được:

- session với facts người dùng đã cung cấp;
- fact target với concept và câu hỏi tương ứng;
- protocol atom với tài liệu, phiên bản và citation;
- proposal với evidence đã được authority gate chấp nhận;
- quyết định điều dưỡng với toàn bộ lịch sử trước đó.

Trong giai đoạn nghiên cứu, dữ liệu văn bản có thể được chuẩn bị ở dạng Markdown/JSON có metadata trước khi nạp vào database. File nguồn không được xem là nguồn runtime nếu chưa qua bước ingestion và validation.

---

## 4. ĐỊNH HƯỚNG NGUỒN DỮ LIỆU

### 4.1. Nguồn làm hạt nhân tri thức

Tôi xác định nguồn hạt nhân cần đáp ứng ba điều kiện: có tổ chức hoặc đơn vị phát hành rõ ràng, có phạm vi sử dụng phù hợp với phân luồng và có thể ghi lại phiên bản/citation.

Các nhóm nguồn được xem xét:

- Tài liệu hướng dẫn Emergency Severity Index (ESI) và tài liệu đào tạo phân luồng có thẩm quyền.
- Hướng dẫn hoặc phác đồ liên quan đến cấp cứu, phân loại ban đầu và dấu hiệu nguy hiểm.
- Tài liệu thuật ngữ y khoa tiếng Việt để bổ sung cách diễn đạt, không tự động dùng làm quy tắc quyết định.
- Bộ ca mô phỏng hoặc case study có nhãn rõ ràng để phục vụ kiểm thử.

### 4.2. Phân loại nguồn theo quyền sử dụng

| Loại tài liệu | Có thể dùng để | Không được dùng để |
|---|---|---|
| `validated_protocol` | Hỗ trợ đối chiếu ESI khi đã approved và authorized | Không được bỏ qua scope hoặc citation |
| `reference_material` | Tham khảo thuật ngữ, bối cảnh và thiết kế câu hỏi | Không được tự cấp quyền hỗ trợ ESI |
| `case_example` | Demo hoặc benchmark có kiểm soát | Không được gắn nhãn thành protocol |
| `synthetic_case` | Kiểm thử hội thoại và edge case | Không được xem là ground truth nếu chưa được rà soát |
| `rejected/pending` | Theo dõi chất lượng dữ liệu | Không được đưa vào evidence của người dùng |

Một case example dù có nội dung gần với tình huống người dùng cũng chỉ được xem là dữ liệu minh họa hoặc demo. Nó không được đổi tên thành validated protocol để làm căn cứ quyết định.

### 4.3. Nguyên tắc không sử dụng dữ liệu sai phạm vi

Một số bộ dữ liệu hỏi đáp y khoa có thể chứa câu trả lời chẩn đoán hoặc kê đơn. Những bộ dữ liệu này không được đưa trực tiếp vào output của MedTriage AI. Nếu được dùng để nghiên cứu cách người Việt diễn đạt triệu chứng, chỉ lấy phần input phù hợp và loại bỏ phần trả lời không nằm trong phạm vi triage.

---

## 5. THIẾT KẾ ONTOLOGY BAN ĐẦU

### 5.1. Clinical concept

`ClinicalConcept` là khái niệm được chuẩn hóa để hệ thống nhận biết nhiều cách diễn đạt khác nhau của người dùng.

Ví dụ minh họa:

| Concept | Alias có thể gặp | Ghi chú |
|---|---|---|
| Đau ngực | tức ngực, nặng ngực, đau vùng ngực | Không tự suy ra nguyên nhân |
| Khó thở | hụt hơi, thở không đủ, nghẹn thở | Cần hỏi thêm mức độ và diễn tiến |
| Mất ý thức | ngất, bất tỉnh, không gọi được | Có thể liên quan nhóm nguy hiểm |
| Sốt | nóng người, nhiệt độ cao, sốt rét | Cần phân biệt cảm giác chủ quan và nhiệt độ đo được |

Alias chỉ giúp chuẩn hóa ngôn ngữ. Alias không tự nó tạo ra nhãn bệnh hoặc mức ESI.

### 5.2. Fact target

`FactTarget` là một dữ kiện mà hệ thống cần thu thập để kiểm tra điều kiện protocol.

Một fact target nên có các trường:

- `fact_target_id`: mã ổn định.
- `concept_id`: concept liên quan.
- `question_text`: câu hỏi thân thiện với người dùng.
- `value_type`: boolean, number, category hoặc free text có kiểm soát.
- `required_for`: nhóm protocol hoặc điều kiện liên quan.
- `source_policy`: dữ kiện được lấy từ người dùng, nhân viên hoặc thiết bị.
- `validation_rule`: cách kiểm tra giá trị hợp lệ.

Ví dụ:

```text
fact_target_id: chest_pain_onset
concept_id: chest_pain
question_text: Cơn đau hoặc tức ngực bắt đầu từ khi nào?
value_type: duration
source_policy: patient_or_nurse
```

### 5.3. Quan hệ giữa các concept

Ontology cần mô tả quan hệ để chọn câu hỏi tiếp theo, nhưng quan hệ không được hiểu là kết luận chẩn đoán. Một số loại quan hệ dự kiến:

- `has_associated_symptom`: triệu chứng liên quan cần hỏi.
- `has_red_flag`: dấu hiệu cần kiểm tra sớm.
- `requires_context`: cần thêm tuổi, thai kỳ, bệnh nền hoặc chấn thương.
- `has_measurement`: cần sinh hiệu hoặc giá trị đo được.
- `is_alias_of`: từ/cụm từ đồng nghĩa hoặc gần nghĩa.
- `contradicts`: hai facts có khả năng mâu thuẫn cần làm rõ.

---

## 6. THIẾT KẾ PROTOCOL ATOM VÀ METADATA

### 6.1. Protocol atom

Thay vì lưu một guideline dài và để mô hình tự đọc toàn bộ, tôi định hướng tách thành các `protocol_atom` nhỏ. Mỗi atom chứa một tiêu chí có thể kiểm tra, ví dụ điều kiện, facts yêu cầu, mức ưu tiên và nguồn.

Mẫu cấu trúc đề xuất:

```yaml
protocol_id: esi_example_001
document_type: validated_protocol
title: Tiêu chí phân luồng mẫu
symptom_category: chest_pain
esi_level: 2
required_facts:
  - chest_pain_onset
  - breathing_difficulty
criterion:
  operator: all
  conditions:
    - fact: breathing_difficulty
      equals: true
source:
  source_id: source_example
  citation_id: citation_example
  version: v1
validation_status: pending
authority_status: UNKNOWN
scope: research_only
```

Đây chỉ là cấu trúc kỹ thuật minh họa. Protocol chưa được phê duyệt không được dùng để tạo kết luận ESI cho người dùng.

### 6.2. Metadata bắt buộc

| Trường | Ý nghĩa |
|---|---|
| `document_id` | Mã tài liệu ổn định |
| `document_type` | Phân biệt protocol, reference, case example, synthetic case |
| `source_id` | Mã nguồn phát hành |
| `title` | Tên tài liệu |
| `version` | Phiên bản tài liệu |
| `publication_date` | Ngày phát hành nếu có |
| `retrieved_at` | Ngày lấy dữ liệu |
| `validation_status` | pending, approved hoặc rejected |
| `authority_status` | AUTHORIZED, DEMO_ONLY hoặc UNKNOWN |
| `clinical_scope` | Phạm vi hội chứng/đối tượng được hỗ trợ |
| `citation_id` | Mã trích dẫn ổn định |
| `content_hash` | Phát hiện thay đổi nội dung |

### 6.3. Evidence gate

Một tài liệu chỉ đủ điều kiện hỗ trợ đề xuất ESI khi đồng thời thỏa mãn:

1. `document_type = validated_protocol`.
2. `validation_status = approved`.
3. `authority_status = AUTHORIZED`.
4. Có provenance và citation ID ổn định.
5. Phạm vi lâm sàng khớp với tình huống.
6. Có ít nhất một tiêu chí quyết định được khớp với facts đã xác nhận.
7. Kết quả retrieval đạt ngưỡng của kênh tìm kiếm được cấu hình.

Nếu thiếu một điều kiện bắt buộc, hệ thống phải xóa hoặc không tạo ESI/SBAR/citation như một kết luận hoàn tất; thay vào đó, chuyển sang trạng thái thiếu bằng chứng và chờ nhân viên kiểm tra.

---

## 7. QUY TRÌNH CHUẨN HÓA VÀ NẠP DỮ LIỆU

### Bước 1 — Tiếp nhận tài liệu gốc

Ghi lại nguồn, phiên bản, ngày lấy, phạm vi sử dụng và quyền sử dụng. Không đưa tài liệu chưa rõ nguồn vào kho production evidence.

### Bước 2 — Trích xuất nội dung

Chuyển PDF/text sang nội dung có cấu trúc; giữ lại tiêu đề, mục, trang hoặc vị trí trích dẫn để có thể kiểm tra ngược.

### Bước 3 — Tách và gắn metadata

Chia nội dung thành protocol atom, reference chunk hoặc case example. Gán `document_type`, scope, validation status và citation.

### Bước 4 — Chuẩn hóa ontology

Liên kết concept, alias, fact target và quan hệ. Mọi ID phải được kiểm tra chống trùng và chống tham chiếu đến bản ghi không tồn tại.

### Bước 5 — Kiểm tra nội dung bị cấm

Quét các nội dung chẩn đoán, kê đơn hoặc hướng dẫn vượt quá phạm vi. Nội dung không phù hợp phải được loại bỏ, đánh dấu hoặc chuyển sang tập dữ liệu không dùng cho patient-facing output.

### Bước 6 — Kiểm tra authority và citation

Chỉ bản ghi đạt authority gate mới được đánh dấu có thể hỗ trợ evidence. Citation trong output phải là tập con của citation đã được gate chấp nhận.

### Bước 7 — Nạp và kiểm tra database

Nạp dữ liệu vào PostgreSQL/pgvector; kiểm tra số lượng bản ghi, khóa, embedding, index, metadata và khả năng truy xuất theo query tiếng Việt/tiếng Anh.

### Bước 8 — Version hóa

Lưu manifest, content hash, phiên bản corpus và kết quả kiểm tra. Khi dữ liệu thay đổi, phải biết bản thay đổi nào đã ảnh hưởng đến evaluation.

---

## 8. HƯỚNG TRUY XUẤT DỮ LIỆU

Từ các facts đã xác nhận, hệ thống sẽ tạo ba dạng query:

1. **Query tiếng Việt:** giữ cách diễn đạt tự nhiên của người dùng.
2. **Query tiếng Anh hoặc thuật ngữ chuẩn:** dùng cho nguồn song ngữ hoặc metadata chuẩn hóa.
3. **Query sparse có kiểm soát:** sử dụng concept, alias, fact và từ khóa quan trọng.

Kết quả truy xuất cần được kiểm tra qua hai lớp:

- **Relevance gate:** tài liệu có liên quan đến facts và phạm vi tình huống hay không.
- **Authority gate:** tài liệu có đủ trạng thái approved/authorized để hỗ trợ ESI hay không.

Tài liệu chỉ đạt relevance nhưng không đạt authority được giữ lại để tham khảo hoặc debug, không được đưa vào evidence của kết quả patient-facing.

---

## 9. KẾT QUẢ ĐẠT ĐƯỢC TRONG TUẦN 3

Trong tuần 3, tôi đã hoàn thành các đầu ra thiết kế sau:

- Xác định ba khối dữ liệu chính: protocol/guideline, ontology và benchmark.
- Thiết kế luồng dữ liệu từ tài liệu gốc đến kho truy xuất.
- Xác định cách phân loại tài liệu theo quyền sử dụng.
- Thiết kế concept, alias, fact target và các quan hệ ontology ban đầu.
- Đề xuất cấu trúc protocol atom và metadata kèm provenance.
- Định nghĩa evidence gate dựa trên document type, validation status, authority, scope và citation.
- Xác định quy trình chuẩn hóa, kiểm tra nội dung, nạp database và version hóa.
- Phân biệt rõ dữ liệu có thể hỗ trợ ESI với case example hoặc synthetic case chỉ dùng cho demo/đánh giá.
- Đề xuất hướng truy xuất đa ngôn ngữ và kiểm tra relevance/authority độc lập.

Kết quả tuần 3 tạo nền tảng để sang tuần 4 xây dựng dữ liệu mẫu, migration/seed và pipeline ingestion có thể chạy thử.

---

## 10. KHÓ KHĂN VÀ CÁCH XỬ LÝ

| Khó khăn | Cách xử lý |
|---|---|
| Tài liệu liên quan chưa chắc đủ thẩm quyền | Tách relevance gate khỏi authority gate |
| Case example dễ bị dùng nhầm làm protocol | Gắn `document_type=case_example` và `authority_status=DEMO_ONLY` |
| LLM có thể tự tạo citation hoặc ID | Chỉ cho phép citation/ID là tập con của artifact đã được gate |
| Guideline dài và khó truy xuất chính xác | Tách thành protocol atom có metadata, scope và content hash |
| Dữ liệu mô phỏng không phải ground truth lâm sàng | Chỉ dùng cho benchmark; ghi rõ trạng thái và giới hạn |
| Không đủ bằng chứng để ra đề xuất | Fail-closed, xóa ESI/SBAR/citation hoàn tất và chuyển HITL |

---

## 11. KẾ HOẠCH TUẦN 4

Trong tuần 4, tôi sẽ chuyển thiết kế dữ liệu thành bộ dữ liệu và pipeline thử nghiệm:

- Tạo một corpus mẫu cho các nhóm triệu chứng ưu tiên.
- Viết schema/migration/seed cho concept, fact, protocol và citation.
- Tạo các protocol atom mẫu có metadata đầy đủ.
- Xây dựng một số benchmark conversation nhiều lượt.
- Kiểm tra dữ liệu trùng, thiếu, sai kiểu và thiếu citation.
- Nạp thử dữ liệu vào PostgreSQL/pgvector.
- Chạy truy xuất mẫu và kiểm tra evidence gate.

---

## 12. KẾT LUẬN TUẦN 3

Tuần 3 giúp tôi xác định rằng chất lượng của MedTriage AI phụ thuộc không chỉ vào mô hình ngôn ngữ mà còn vào cách tổ chức, kiểm soát và cấp quyền cho dữ liệu. Kho tri thức phải trả lời được ba câu hỏi: thông tin này đến từ đâu, có được phép sử dụng cho mục đích nào và tiêu chí nào của tình huống đã được chứng minh.

Nguyên tắc quan trọng nhất được chốt trong tuần này là: **tài liệu liên quan chưa đủ để làm bằng chứng; chỉ dữ liệu đã được xác thực thẩm quyền, đúng phạm vi và có provenance mới được hỗ trợ đề xuất phân luồng.**

---

## NGƯỜI LẬP BÁO CÁO

**Lê Hoàng Việt**  
Ký và ghi rõ họ tên: ____________________  
Ngày: ____ / ____ / 2026
