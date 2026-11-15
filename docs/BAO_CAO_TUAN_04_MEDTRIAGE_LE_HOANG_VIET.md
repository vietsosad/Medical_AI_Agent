# BÁO CÁO TIẾN ĐỘ DỰ ÁN KHOA HỌC VÀ CÔNG NGHỆ

## TUẦN 4 — XÂY DỰNG CORPUS MẪU, PIPELINE INGESTION VÀ KIỂM TRA CHẤT LƯỢNG DỮ LIỆU

**Tên đề tài:** MedTriage AI — Hệ thống hỗ trợ tiếp nhận và phân luồng ưu tiên y tế  
**Người thực hiện:** Lê Hoàng Việt  
**Tuần thực hiện:** Tuần 4/15  
**Thời gian:** 17/08/2026 – 23/08/2026  
**Báo cáo liên kết:** Báo cáo Tuần 3 — Thiết kế kho dữ liệu, ontology và quy trình RAG  
**Trạng thái:** Hoàn thành pipeline dữ liệu thử nghiệm; protocol manifest vẫn ở trạng thái chờ phê duyệt

> **Lưu ý phạm vi:** Đây là báo cáo cá nhân của Lê Hoàng Việt. Dữ liệu được xây dựng trong tuần 4 phục vụ nghiên cứu, phát triển và kiểm thử. Protocol chưa đủ metadata, chưa được phê duyệt hoặc chưa đạt authority gate không được dùng để tạo kết luận ESI chính thức.

---

## 1. MỤC TIÊU TUẦN 4

Tuần 3 đã hoàn thành thiết kế logic cho ontology, protocol atom, provenance và evidence gate. Trong tuần 4, tôi chuyển các thiết kế đó thành các tài sản dữ liệu và quy trình có thể kiểm tra bằng máy.

Các mục tiêu chính:

1. Tạo corpus mẫu cho một số nhóm triệu chứng ưu tiên.
2. Chuẩn hóa dữ liệu thành concept, relation, fact target và protocol atom.
3. Xây dựng manifest quản lý nguồn, phiên bản và trạng thái phê duyệt.
4. Thiết kế schema và migration cho PostgreSQL/pgvector.
5. Chuẩn bị quy trình ingestion có validation và khả năng chạy lại an toàn.
6. Xây dựng benchmark hội thoại ban đầu.
7. Kiểm tra dữ liệu trùng, thiếu, sai liên kết và thiếu citation.
8. Thử nghiệm nguyên tắc relevance gate, authority gate và fail-closed.

---

## 2. KẾ THỪA KẾT QUẢ TỪ TUẦN 3

Tuần 4 sử dụng trực tiếp các quyết định đã chốt trong tuần 3:

- Dữ liệu được chia thành protocol/guideline, ontology và benchmark.
- Tài liệu liên quan chưa mặc nhiên được xem là tài liệu có thẩm quyền.
- Case example và synthetic case không được đổi nhãn thành validated protocol.
- Mỗi protocol cần có provenance, citation ID, version và clinical scope.
- ESI chỉ được hỗ trợ khi evidence vượt qua cả relevance gate và authority gate.
- Nếu thiếu nguồn, tiêu chí hoặc citation, hệ thống phải fail-closed và chuyển cho nhân viên y tế kiểm tra.

Những nguyên tắc này được chuyển thành các trường dữ liệu, bước validation và điều kiện chặn trong pipeline tuần 4.

---

## 3. CORPUS MẪU ĐƯỢC XÂY DỰNG

### 3.1. Phạm vi corpus thử nghiệm

Để tránh mở rộng quá nhanh, tôi ưu tiên các nhóm tình huống có giá trị kiểm thử cao:

- Đau ngực và triệu chứng tim mạch.
- Khó thở và triệu chứng hô hấp.
- Thay đổi ý thức hoặc dấu hiệu thần kinh.
- Đau bụng cấp.
- Sốt và dấu hiệu nhiễm trùng.
- Chấn thương và chảy máu.

Mục tiêu của corpus mẫu không phải bao phủ toàn bộ y khoa, mà là kiểm tra xem cấu trúc dữ liệu có hỗ trợ được ba việc hay không: hiểu cách diễn đạt của người dùng, chọn dữ kiện cần hỏi và đối chiếu tiêu chí có nguồn.

### 3.2. Các lớp dữ liệu được chuẩn hóa

| Lớp dữ liệu | Nội dung | Vai trò |
|---|---|---|
| Clinical concepts | Khái niệm triệu chứng, dấu hiệu, tiền sử | Chuẩn hóa ngôn ngữ đầu vào |
| Aliases song ngữ | Từ chuẩn, từ đồng nghĩa và cách nói đời thường | Hỗ trợ tiếng Việt/tiếng Anh |
| Concept relations | Liên kết concept với facts hoặc concept liên quan | Chọn câu hỏi tiếp theo |
| Fact targets | Dữ kiện có thể hỏi hoặc quan sát | Tạo state có cấu trúc |
| Protocol atoms | Điều kiện và tác động quyết định | Đối chiếu bằng logic tất định |
| Citations/metadata | Nguồn, phiên bản, scope, trạng thái duyệt | Truy ngược và kiểm soát thẩm quyền |
| Benchmark cases | Hội thoại, facts kỳ vọng và trạng thái kết thúc | Kiểm thử hồi quy |

### 3.3. Nguyên tắc biên soạn alias

Tôi chia alias thành ba nhóm:

1. **Thuật ngữ chuẩn tiếng Việt:** ví dụ “khó thở”, “đau ngực”, “mất ý thức”.
2. **Thuật ngữ tiếng Anh:** dùng để liên kết với guideline và metadata song ngữ.
3. **Cách nói của người dùng:** ví dụ “hụt hơi”, “ngực bị đè nặng”, “gọi không tỉnh”.

Alias chỉ phục vụ nhận diện concept. Hệ thống không được suy ra tên bệnh hoặc mức ESI chỉ từ một alias riêng lẻ.

---

## 4. THIẾT KẾ MANIFEST VÀ TRẠNG THÁI NGUỒN

### 4.1. Manifest protocol nháp

Tôi chuẩn bị manifest nháp cho dữ liệu ESI với các trường quản trị chính:

- `citation_id` và `chunk_id`;
- `protocol_code`, `title`, `issuing_body` và `version`;
- `document_type` và `clinical_scope`;
- `decision_criteria` và `content_hash`;
- `source_uri` và `license_reference`;
- `validation_status`, `reviewed_by` và `reviewed_at`;
- `calibration_id` và `calibration_profile`.

Manifest hiện có 8 chunk thử nghiệm. Quá trình kiểm tra phát hiện cả 8 chunk còn thiếu các trường bắt buộc liên quan đến URI nguồn, giấy phép, ngày hiệu lực, trạng thái duyệt, người duyệt và cấu hình calibration. Vì vậy manifest được giữ ở trạng thái:

```text
_draft_status = NOT_READY_FOR_INGESTION
```

Việc giữ trạng thái này là chủ đích an toàn. Dù nội dung đã được tách và có vẻ liên quan, pipeline không được tự động coi các chunk là evidence hợp lệ.

### 4.2. Quy tắc trạng thái

| Trạng thái | Ý nghĩa | Quyền sử dụng |
|---|---|---|
| `NOT_READY_FOR_INGESTION` | Còn thiếu trường chặn | Không được nạp vào kho evidence chính thức |
| `pending` | Đã đủ schema nhưng chưa được duyệt | Chỉ dùng kiểm tra kỹ thuật |
| `approved` | Đã được người có trách nhiệm phê duyệt | Tiếp tục kiểm tra authority và calibration |
| `rejected` | Không đạt yêu cầu | Không được truy xuất cho patient-facing flow |
| `DEMO_ONLY` | Chỉ dùng demo/case example | Không được hỗ trợ ESI production |
| `AUTHORIZED` | Đạt yêu cầu thẩm quyền | Có thể tham gia evidence gate nếu các điều kiện khác đạt |

### 4.3. Content hash và versioning

Mỗi chunk có `content_hash` để phát hiện thay đổi. Nếu nội dung thay đổi nhưng version hoặc review không được cập nhật, pipeline phải xem tài liệu là cần kiểm tra lại. Cách này giúp tránh trường hợp citation giữ nguyên trong khi nội dung nguồn đã bị sửa.

---

## 5. SCHEMA POSTGRESQL VÀ PGVECTOR

### 5.1. Nhóm bảng tham chiếu

Thiết kế database tách dữ liệu tham chiếu khỏi dữ liệu phiên chạy:

| Bảng | Nội dung chính |
|---|---|
| `simple_agent_clinical_concepts` | Concept, alias, semantic type và embedding |
| `simple_agent_concept_relations` | Quan hệ giữa concept và fact/concept |
| `simple_agent_fact_targets` | Schema, cách hỏi và điều kiện của fact |
| `simple_agent_fact_target_embeddings` | Vector truy xuất fact target |
| `simple_agent_protocol_atoms` | Điều kiện quyết định, nguồn và embedding |

### 5.2. Nhóm bảng runtime

| Bảng | Nội dung chính |
|---|---|
| `simple_agent_sessions` | State của phiên triage |
| `simple_agent_chat_sessions` | Phiên chat gắn với người dùng |
| `simple_agent_chat_messages` | Transcript hội thoại |
| `simple_agent_nurse_reviews` | Kết quả xác nhận hoặc điều chỉnh của nhân viên |

Việc tách hai nhóm bảng giúp gói migration chỉ xuất dữ liệu tham chiếu, không vô tình đóng gói lịch sử hội thoại hoặc dữ liệu người dùng.

### 5.3. Vector và index

Các bảng concept, fact target và protocol atom được thiết kế có vector embedding 1.536 chiều. HNSW index với cosine distance được dùng để hỗ trợ tìm kiếm ngữ nghĩa. Tuy nhiên, vector similarity chỉ giải quyết độ liên quan; quyền làm bằng chứng vẫn phải qua metadata và authority gate.

### 5.4. Khóa và ràng buộc

- `concept_id`, `fact_target_id` và `atom_id` phải duy nhất.
- Relation phải tham chiếu tới ID tồn tại.
- Fact target embedding phải khớp đúng fact target.
- Runtime table không được đưa vào corpus export.
- Ingestion phải dừng nếu số vector không khớp metadata.

---

## 6. PIPELINE INGESTION THỬ NGHIỆM

### 6.1. Các bước xử lý

```text
Tài liệu/JSONL nguồn
        │
        ▼
Kiểm tra file và schema
        │
        ▼
Kiểm tra ID, relation và dữ liệu trùng
        │
        ▼
Kiểm tra provenance, citation và authority
        │
        ├── Không đạt → chặn ingestion, xuất lỗi
        │
        └── Đạt → tạo/đối chiếu embedding
                         │
                         ▼
                 Dry-run và thống kê
                         │
                         ▼
                 Upsert vào PostgreSQL
                         │
                         ▼
              Kiểm tra số lượng và vector
```

### 6.2. Chế độ dry-run

Trước khi ghi vào database, pipeline cần hỗ trợ dry-run để:

- kiểm tra file đầu vào có đầy đủ hay không;
- đếm concepts, relations, facts và protocol atoms;
- phát hiện embedding bị thiếu;
- kiểm tra metadata có khớp ID hay không;
- báo lỗi mà không thay đổi dữ liệu hiện có.

### 6.3. Cơ chế upsert

Pipeline sử dụng khóa tự nhiên như `concept_id`, `fact_target_id` và `atom_id` để upsert. Khi chạy lại, dữ liệu được cập nhật thay vì tạo bản ghi trùng. Quan hệ sử dụng bộ khóa gồm source concept, relation type và target ID.

Mục tiêu là bảo đảm quá trình ingestion có tính lặp lại và an toàn khi corpus được bổ sung.

### 6.4. Kiểm tra trước khi bật runtime

Sau ingestion, cần kiểm tra:

- số lượng bản ghi theo từng bảng;
- số embedding và kích thước vector;
- concept/fact/atom bị thiếu embedding;
- relation có target không tồn tại;
- atom thiếu authority scope hoặc source document;
- citation không tồn tại hoặc không khớp protocol;
- index pgvector đã được tạo.

Runtime chỉ được bật sau khi schema, corpus và các kiểm tra bắt buộc đều đạt.

---

## 7. KIỂM TRA CHẤT LƯỢNG DỮ LIỆU

### 7.1. Kiểm tra cấu trúc

| Kiểm tra | Điều kiện đạt |
|---|---|
| JSON/JSONL hợp lệ | Không lỗi parse và đúng encoding UTF-8 |
| ID duy nhất | Không trùng concept, fact hoặc atom ID |
| Schema hợp lệ | Trường bắt buộc đúng kiểu dữ liệu |
| Quan hệ hợp lệ | Source và target tồn tại |
| Embedding hợp lệ | Đủ vector, đúng số chiều và khớp metadata |
| Citation hợp lệ | Có source, version, scope và citation ID |

### 7.2. Kiểm tra fact target trùng hoặc gần trùng

Fact target có thể khác tên nhưng hỏi cùng một dữ kiện. Tôi thiết kế kiểm tra theo hai góc nhìn:

- **Clinical similarity:** so sánh tên và mô tả kỹ thuật.
- **Patient-language similarity:** so sánh cách hỏi và từ ngữ dành cho người dùng.

Các cặp có similarity cao được đưa vào báo cáo audit để xem xét gộp, giữ riêng hoặc bổ sung `gated_by`. Không tự động xóa fact chỉ dựa trên cosine similarity.

### 7.3. Kiểm tra protocol atom

Một atom bị chặn nếu:

- tham chiếu fact target không tồn tại;
- không có decision effect rõ ràng;
- thiếu authority scope hoặc source document;
- citation không ổn định;
- điều kiện không thể đánh giá từ facts;
- nội dung chứa kết luận chẩn đoán hoặc kê đơn ngoài phạm vi.

### 7.4. Kiểm tra dữ liệu nhạy cảm

Corpus và benchmark không chứa tên, số điện thoại, địa chỉ hoặc dữ liệu nhận diện bệnh nhân thật. Dữ liệu hội thoại thử nghiệm phải là dữ liệu mô phỏng hoặc đã được ẩn danh theo quy định phù hợp.

---

## 8. BENCHMARK HỘI THOẠI BAN ĐẦU

### 8.1. Cấu trúc một ca benchmark

Mỗi ca thử nghiệm dự kiến gồm:

- `case_id` và phiên bản;
- persona mô phỏng;
- triệu chứng ban đầu;
- facts ẩn mà người dùng sẽ cung cấp khi được hỏi;
- expected red-flag state;
- expected facts và câu hỏi quan trọng;
- expected decision status;
- nhãn ESI tham chiếu nếu có căn cứ được phê duyệt;
- SBAR kỳ vọng hoặc trạng thái chuyển HITL;
- tiêu chí pass/fail.

### 8.2. Nhóm tình huống thử nghiệm

1. Ca có red flag rõ ràng ngay ở tin nhắn đầu.
2. Ca có red flag ẩn, chỉ xuất hiện sau câu hỏi bổ sung.
3. Ca cần nhiều lượt để đủ facts.
4. Ca cung cấp đủ thông tin ngay từ đầu.
5. Ca trả lời mơ hồ hoặc mâu thuẫn.
6. Ca khai báo cho người thân.
7. Ca không có protocol được authorized.
8. Ca có tài liệu liên quan nhưng chỉ mang trạng thái DEMO_ONLY.
9. Ca yêu cầu AI chẩn đoán hoặc kê đơn.
10. Ca phải chuyển điều dưỡng do thiếu bằng chứng.

### 8.3. Quy tắc benchmark

- Synthetic case không tự động trở thành ground truth.
- Case example không được làm evidence cho ESI.
- Kết quả đánh giá phải ghi rõ corpus version.
- Một ca không có evidence hợp lệ phải pass khi hệ thống từ chối kết luận và chuyển HITL đúng cách.
- Không đánh giá hệ thống chỉ bằng độ chính xác; cần kiểm tra under-triage, citation và hành vi fail-closed.

---

## 9. THỬ NGHIỆM EVIDENCE GATE

### 9.1. Trường hợp được phép tạo evidence

Evidence chỉ được chấp nhận khi:

1. Query được tạo từ facts đã xác nhận.
2. Kết quả nằm trong corpus được cấu hình.
3. Tài liệu đạt ngưỡng relevance.
4. `document_type=validated_protocol`.
5. `validation_status=approved`.
6. `authority_status=AUTHORIZED`.
7. Clinical scope khớp.
8. Có ít nhất một decision criterion được facts thỏa mãn.
9. Citation ID thuộc tập artifact đã được gate chấp nhận.

### 9.2. Trường hợp phải fail-closed

Nếu bất kỳ điều kiện bắt buộc nào bị thiếu, hệ thống phải:

- không xuất ESI như một quyết định hoàn chỉnh;
- không tạo SBAR như kết quả đã xác nhận;
- xóa citation không hợp lệ;
- đặt `decision_status=INSUFFICIENT_EVIDENCE`;
- chuyển `workflow_phase=HANDOFF`;
- thông báo đang chờ nhân viên y tế kiểm tra.

### 9.3. Kết quả thử với manifest nháp

Manifest protocol nháp chưa có đủ trường phê duyệt và calibration, vì vậy kết quả đúng của evidence gate là **từ chối ingestion/evidence**. Đây được xem là test đạt yêu cầu an toàn, không phải lỗi của pipeline.

---

## 10. SẢN PHẨM VÀ MINH CHỨNG TUẦN 4

| Hạng mục | Minh chứng trong repository | Trạng thái |
|---|---|---|
| Manifest protocol nháp | `data/protocols/ahrq_esi_v5.draft-manifest.json` | Chưa sẵn sàng ingestion |
| Ontology song ngữ thử nghiệm | `data/guard_rules/ontology_vi_en.json` | Dùng nghiên cứu/chuẩn hóa |
| Tài liệu trích xuất ESI | `data/extracted_tables/` | Dữ liệu đầu vào cần kiểm duyệt |
| Schema PostgreSQL/pgvector | `database/migrations/20260901_simple_agent_schema.sql` | Có cấu trúc bảng và index |
| Hướng dẫn migration | `database/migrations/README.md` | Có quy trình nạp và verify |
| Pipeline migration corpus | `scripts/migrate_simple_agent_corpus_to_pg.py` | Có dry-run và upsert |
| Script ingestion protocol | `scripts/ingest_validated_protocols.py` | Dùng cho protocol đã hợp lệ |
| Script build manifest | `scripts/build_protocol_manifest.py` | Tạo/kiểm tra manifest |
| Audit fact target | `scripts/audit_fact_target_duplicates.py` | Phát hiện trùng/gần trùng |

Các tài sản trên là bằng chứng kỹ thuật của quá trình thiết kế và thử nghiệm dữ liệu. Sự tồn tại của file hoặc script không đồng nghĩa dữ liệu đã được phê duyệt cho sử dụng lâm sàng.

---

## 11. KẾT QUẢ ĐẠT ĐƯỢC TRONG TUẦN 4

Trong tuần 4, tôi đã hoàn thành các nội dung sau:

- Chuyển thiết kế dữ liệu tuần 3 thành corpus và ontology mẫu.
- Xây dựng cấu trúc manifest cho protocol và provenance.
- Phát hiện manifest 8 chunk còn thiếu các trường phê duyệt bắt buộc và giữ ở trạng thái `NOT_READY_FOR_INGESTION`.
- Thiết kế schema PostgreSQL/pgvector cho dữ liệu tham chiếu và dữ liệu runtime.
- Xác định vector 1.536 chiều và HNSW index cho truy xuất ngữ nghĩa.
- Thiết kế pipeline ingestion gồm validation, dry-run, upsert và verify.
- Xây dựng quy tắc audit ID, relation, embedding, fact target và protocol atom.
- Xác định cấu trúc benchmark hội thoại nhiều lượt.
- Thử nghiệm evidence gate với trường hợp nguồn chưa được authorized.
- Xác nhận hành vi đúng là fail-closed và chuyển HITL khi thiếu bằng chứng.

Kết quả tuần 4 tạo nền tảng dữ liệu có thể kiểm tra để bước sang giai đoạn thiết kế trải nghiệm và nguyên mẫu giao diện trong tuần 5.

---

## 12. KHÓ KHĂN VÀ CÁCH XỬ LÝ

| Khó khăn | Cách xử lý |
|---|---|
| Nội dung đã trích xuất nhưng thiếu metadata nguồn | Giữ manifest ở `NOT_READY_FOR_INGESTION` |
| Dữ liệu liên quan dễ bị hiểu nhầm là authorized | Tách relevance, validation và authority thành các gate riêng |
| Chạy lại migration có thể tạo bản ghi trùng | Upsert theo natural ID và relation composite key |
| Embedding và metadata có thể lệch số lượng | Dừng pipeline nếu row count không khớp |
| Fact target gần nghĩa khó quyết định gộp | Tạo audit similarity, không xóa tự động |
| Case mô phỏng có thể bị dùng sai làm nguồn | Gắn loại dữ liệu và giới hạn DEMO_ONLY/benchmark |
| Thiếu evidence nhưng luồng vẫn cần tiếp tục | Chuyển `INSUFFICIENT_EVIDENCE` sang HITL |

---

## 13. KẾ HOẠCH TUẦN 5

Trong tuần 5, tôi sẽ chuyển từ nền dữ liệu sang thiết kế trải nghiệm sử dụng:

- Vẽ user flow chi tiết cho người bệnh và điều dưỡng.
- Thiết kế wireframe màn hình bắt đầu, chat, cảnh báo khẩn và xác nhận thông tin.
- Thiết kế hàng đợi, màn hình chi tiết ca và quyết định điều dưỡng.
- Xác định cách hiển thị ESI, citation, trạng thái thiếu bằng chứng và SBAR.
- Xây dựng design token và quy tắc accessibility ban đầu.
- Tạo prototype để kiểm tra khả năng hiểu và tải nhận thức.
- Chuẩn bị kịch bản usability test cho ba tình huống chính.

---

## 14. KẾT LUẬN TUẦN 4

Tuần 4 đã chuyển các nguyên tắc dữ liệu của tuần 3 thành cấu trúc và quy trình có thể kiểm tra. Kết quả quan trọng không chỉ là tạo được corpus mẫu, mà còn chứng minh pipeline có thể từ chối dữ liệu chưa đủ điều kiện.

Nguyên tắc được chốt trong tuần này là: **một pipeline dữ liệu an toàn không chỉ biết nạp dữ liệu hợp lệ, mà còn phải biết dừng đúng lúc khi nguồn, citation, thẩm quyền hoặc calibration chưa đầy đủ.**

---

## NGƯỜI LẬP BÁO CÁO

**Lê Hoàng Việt**  
Ký và ghi rõ họ tên: ____________________  
Ngày: ____ / ____ / 2026
