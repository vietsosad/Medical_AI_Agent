# Audit dữ liệu và dựng bộ ca tổng hợp generated_mock_v2

Đợt 1 (200 ca) dựng ngày 04/11/2026; đợt 2 (thêm 200 ca, mục 11) dựng ngày 05/11/2026, cùng ngày rà lại đợt 1, kiểm
chứng mù trên mẫu ngẫu nhiên và chạy thử đầu cuối qua agent thật (mục 12). Thư mục:
`eval/generated_mock_v2/`. Toàn bộ là **dữ liệu tổng hợp**: kịch bản do mô hình ngôn ngữ soạn theo yêu cầu của chủ dự
án, chưa có chuyên gia y tế nào duyệt; mọi bản ghi mang `clinical_review_status = PENDING_CLINICAL_REVIEW`.

## Tóm tắt

- **400 ca hội thoại phân luồng** tiếng Việt (đợt 1: 200, đợt 2: 200), cùng schema `GoldenCase`
  (`simple-agent-golden-v1`) và cùng bộ khoá với `eval/cases/simple_agent_golden_300.jsonl`. Mỗi tệp chạy được ngay bằng
  `python -m eval.run --cases <tệp>`; trình nạp và bước preflight của `eval/run.py` đã chạy qua cả bốn tệp (checksum, vân
  tay tiêu chí và dữ kiện, ca smoke, không cảnh báo corpus lệch).
- **Nhãn không do người viết gán.** Người viết chỉ soạn kịch bản (hồ sơ, lời kể, câu trả lời, điều người bệnh không
  biết). Nhãn được tính bằng bộ đánh giá độc lập sẵn có của dự án, `golden_validator.satisfied_esi`, trên 1.711 tiêu
  chí `CLINICAL_AUTHORITY` của corpus PostgreSQL; sau đó được đối chiếu với một tài liệu khác là bản trích AHRQ ESI v5
  trong repo. Kịch bản nào cho ra nhãn khác dự định thì bước dựng dừng lại, không sửa nhãn cho khớp.
- **315 ca có nhãn kiểm chứng được bằng văn bản hướng dẫn**, chia train 218 / validation 48 / test 49 (69,2 / 15,2 /
  15,6%). **85 ca chưa kiểm chứng được** nằm riêng trong `needs_medical_review.jsonl`, mỗi ca ghi lý do.
- **Đợt 2 mở rộng phạm vi, không lặp lại đợt 1.** 147/158 tiêu chí đại diện của đợt 2 chưa từng xuất hiện ở đợt 1. Số
  tiêu chí corpus được ít nhất một ca chạm tới (trong số tiêu chí khớp được chỉ từ lời người bệnh): ESI 1 từ 9 lên 20/20,
  ESI 2 từ 126 lên 293/474, ESI 3 từ 10 lên 17/19. Số tiêu chí đại diện khác nhau của cả bộ: 117 lên 264.
- **Cả hai đợt được khoá** (`split_lock.json`): 400 bản ghi giữ nguyên tập, cờ smoke và từng byte khi bộ ca mở rộng tiếp.
  Năm lần sửa có chủ đích lên bản ghi đã khoá (tổng 222 lượt bản ghi) đều được ghi nhật ký, mỗi lần chỉ ở các trường được
  nêu tên; không lần nào đổi mức ESI, trạng thái duyệt hay tập (mục 11.3, 12.2).
- `validate_dataset.py` tính lại mọi thứ từ chính các tệp JSONL và từ PostgreSQL: 9/9 nhóm kiểm tra đạt
  (chi tiết ở `validation_report.md`). Mỗi đợt có một lượt đọc mù độc lập đối chiếu lời kể với dữ kiện: đợt 1 có 57 phát
  hiện (mục 5.1), đợt 2 có 150 phát hiện (mục 11.4); mọi phát hiện được sửa hoặc bác bỏ có lý do.
- **Đợt 1 được rà lại theo đúng kiểu lỗi mà đợt 2 lộ ra** (lời kể đã nói nhưng dữ kiện chưa ghi, mục 12.1): 167/200 bản ghi
  được bổ sung, số ca có thời gian bị của cả bộ tăng từ 206 lên 327/400, tổng dữ kiện từ 3.453 lên 3.809.
- **Kiểm chứng mù trên mẫu ngẫu nhiên 60 ca** của cả hai đợt (mục 12.3): 5/60 ca (8%) còn một lỗi mức ERROR, tất cả là
  dữ kiện phụ lời kể đã nêu nhưng chưa ghi; không ca nào sai nhãn. Mọi lỗi được sửa, và mỗi kiểu lỗi được quét lại trên cả
  400 ca.
- **Chạy thử đầu cuối qua agent thật** (mục 12.4): ca smoke của validation, test và hàng chờ đạt; ca smoke cũ của train (r19,
  ý nghĩ tự hại nói gián tiếp) trượt cả hai lần vì agent hiểu thành buồn ngủ/mất ngủ. Đây là lỗi an toàn của agent; ca smoke
  của train được chuyển sang r15 để cổng smoke không chặn 217 ca còn lại, r19 vẫn nằm trong train như một ca thường.
- Bộ ca làm lộ các vấn đề của hệ thống hiện tại, nêu ở mục 9 và 11.6: corpus khoá một nửa số tiêu chí ESI 1-2
  (507/1.001) sau dữ kiện chỉ người khám mới biết; 40 tiêu chí gán mức ESI chỉ theo điểm đau hoặc sinh hiệu dù mô tả của
  chúng nói về một than phiền cụ thể (một vết bỏng gối được xếp theo tiêu chí "đau bụng"); một số tình huống nguy hiểm
  chưa có tiêu chí nào (rắn lục cắn, nôn dịch xanh ở trẻ sơ sinh, bỏ lọc máu, ngộ độc thuốc trừ sâu qua da); theo mã nguồn,
  agent sống tự ước lượng số nguồn lực bằng LLM nên ca thiếu thông tin nhiều khả năng không được chuyển người (suy ra từ
  mã, chưa chạy agent để xác nhận); bộ lọc khẩn cấp bỏ sót 27 cách nói dấu hiệu đỏ và báo động giả ở 8 câu (đã chạy thật).

## 1. Audit dữ liệu hiện có (Phase 1)

### 1.1 Đã đọc những gì

| Nguồn | Vai trò |
|---|---|
| `eval/cases/simple_agent_golden_30.jsonl`, `simple_agent_golden_300.jsonl` và hai manifest | Dữ liệu hiện có (chỉ đọc, không sửa) |
| `eval/simple_runtime/schemas.py` | Schema `GoldenCase` (`extra="forbid"` ở cấp ngoài) |
| `eval/simple_runtime/golden_builder.py`, `expanded_builder.py` | Cách bộ 30 và 300 ca được sinh |
| `eval/simple_runtime/golden_validator.py` | Bộ đánh giá nhãn độc lập (`satisfied_esi`) |
| `eval/run.py`, `backend_client.py`, `extractor.py`, `deterministic_metrics.py` | Trường nào được runner và metric thực sự dùng |
| PostgreSQL: `simple_agent_protocol_atoms`, `_fact_targets`, `_clinical_concepts`, `_concept_relations`, `_fact_target_embeddings` | Corpus 1.768 tiêu chí, 243 dữ kiện, 1.132 concept |
| `data/protocols/ahrq_esi_v5.draft-manifest.json` | Bản trích AHRQ ESI v5, dùng làm tài liệu đối chiếu thứ hai |
| `src/simple_agent/agent.py`, `emergency_screen.py`, `src/api/routes_simple_triage.py` | Hành vi thật của agent mà bộ ca sẽ đo |

Số liệu ở mục 1.3 được tính bằng `audit_existing.py` và lưu ở `existing_dataset_audit.json`.

### 1.2 Schema hiện tại và cách runner dùng nó

| Mục | Khoá | Runner/metric dùng để làm gì |
|---|---|---|
| cấp ngoài | `schema_version, case_id, category, kind, smoke, clinical_review_status` + 8 mục dưới | `kind`/`category` chỉ phân biệt `guardrail`; `smoke` là cổng chạy thử bắt buộc |
| `profile` | `age_years, age_band, sex, relationship_type, chronic_conditions, allergies, daily_medications` | `auth.create_eval_profile` tạo hồ sơ EHR thật (danh sách là `list[str]`) |
| `presentation` | `initial_message, language, style, contains_temporal_context` | Tin nhắn đầu tiên gửi tới `/simple-triage/start` |
| `expected_state` | `concept_ids, negated_concept_ids, facts, qualitative_observations, unknown_fact_ids, clinician_only_facts, resource_count` | F1 concept và F1 dữ kiện (so theo khoá) |
| `adaptive_dialogue` | `answers_by_fact_target, acceptable_answer_variants, confirmation_reply, clarification_reply, allowed_question_target_ids, forbidden_question_target_ids, max_turns` | Mỗi `ASK_NEXT` phải có câu trả lời cho đúng dữ kiện được hỏi, thiếu là lỗi `missing_answer_mapping`; `ASK_CONFIRMATION` và `ASK_CLARIFICATION` dùng hai câu trả lời riêng |
| `expected_retrieval` | `primary_atom_id, relevant_atom_ids, acceptable_atom_ids, forbidden_atom_ids, decision_points, minimum_recall_at_5` | Recall@5, precision@5, MRR, nDCG@5 |
| `expected_decision` | `esi, terminal_route, terminal_action, acceptable_matched_atom_ids, resource_count` | Đạt khi `terminal_action` khớp và, nếu có `esi`, mức ESI khớp |
| `expected_safety` | 7 cờ an toàn | Ghi kèm quan sát |
| `postgres_provenance` | atom, concept, fact, relation và embedding fingerprint | Preflight từ chối chạy nếu corpus đã đổi |

### 1.3 Thống kê bộ hiện có

| Chỉ số | Bộ 30 ca | Bộ 300 ca |
|---|---|---|
| Phân bố nhãn | ESI 1: 3, 2: 7, 3: 9, 4: 4, 5: 3, guardrail: 4 | ESI 1: 20, 2: 150, 3: 50, 4: 35, 5: 35, guardrail: 10 |
| Kết cục kỳ vọng | 29 RETURN_MATCH, 1 REFUSE | 299 RETURN_MATCH, 1 REFUSE |
| Ca kỳ vọng RETURN_INCOMPLETE | 0 | 0 |
| Tuổi | 35 ở cả 30 ca | 35 ở cả 300 ca |
| Giới | Other: 30 | Other: 293, Female: 7 |
| Quan hệ với người dùng | SELF: 30 | SELF: 300 |
| Hồ sơ có bệnh nền, thuốc hoặc dị ứng | 0 | 0 |
| Ca có ngữ cảnh thời gian | 12 | 2 |
| Lời mở đầu kiểu nhãn biểu mẫu ("Đặc điểm chất nôn: có máu.") | 0 | 121 |
| Lời mở đầu trùng hệt | 0 | 10 bản ghi (5 cặp) |
| Bản ghi triage trùng khoá dữ kiện với bản ghi khác | 0 | 70 |
| Dữ kiện có giá trị được dùng (trên 243) | 70 | 119 |
| Trường chưa bao giờ dùng | `negated_concept_ids`, `unknown_fact_ids`, `qualitative_observations`, `acceptable_answer_variants`, `forbidden_question_target_ids`, `forbidden_atom_ids` | như bộ 30 ca |
| Trạng thái duyệt lâm sàng | PENDING: 30 | PENDING: 300 |

### 1.4 Những gì bộ hiện có đã làm tốt

- Mọi nhãn ESI truy được về một tiêu chí `CLINICAL_AUTHORITY` cụ thể, có vân tay để phát hiện corpus đổi.
- Bộ 300 ca phủ 290 tiêu chí khác nhau và có bảng dịch tiếng Việt cho giá trị enum.
- Cổng smoke và kiểm tra checksum chặn được việc chạy trên dữ liệu hỏng.

### 1.5 Những gì còn thiếu

1. **Một kiểu người bệnh duy nhất:** 35 tuổi, giới "Other", tự kể, không bệnh nền, không thuốc. Không có trẻ em,
   người cao tuổi, thai phụ, người nhà kể hộ; nên các luật phụ thuộc tuổi (sốt ở trẻ sơ sinh, sinh hiệu theo tuổi) chưa
   bao giờ được đo.
2. **Lời kể được sinh từ enum**, nhiều câu là nhãn biểu mẫu; không có câu mơ hồ, sai chính tả, không dấu, viết tắt,
   phương ngữ, lạc đề, mâu thuẫn hay đính chính.
3. **Không có ca thiếu thông tin:** không ca nào dùng `unknown_fact_ids`, không ca nào kỳ vọng agent chuyển nhân viên y
   tế (RETURN_INCOMPLETE). Vì vậy chưa đo được nguyên tắc UNKNOWN khác NEGATIVE.
4. **Nhãn mang tính vòng tròn:** bộ dựng chọn một tiêu chí, sinh dữ kiện từ chính tiêu chí đó rồi kiểm tra rằng dữ kiện
   khớp tiêu chí. Nhãn đúng với corpus theo định nghĩa, nhưng chưa từng được đối chiếu với một tài liệu hướng dẫn khác.
5. Có trùng lặp ở bộ 300 ca (10 lời mở đầu trùng hệt, 70 bản ghi trùng khoá dữ kiện).
6. Mã ca để lộ nhãn (`exp-esi1-001`), và mã ca được dùng làm tên hồ sơ EHR của lượt đánh giá.

### 1.6 Corpus: những điều quyết định cách gán nhãn

Đếm trên PostgreSQL ngày dựng (vân tay bảng khớp với manifest của bộ 300 ca, tức corpus chưa đổi kể từ đó), theo đúng
cách `satisfied_esi` đánh giá (với tiêu chí điểm D mức 3-5, `resource_count` luôn bị coi là bắt buộc):

| Mức ESI | Tiêu chí CLINICAL_AUTHORITY | Khớp được chỉ bằng dữ kiện người bệnh khai | Cần ít nhất một dữ kiện CLINICIAN_ONLY |
|---|---|---|---|
| 1 | 208 | 20 | 188 (113 cần `life_saving_intervention_required`) |
| 2 | 793 | 474 | 319 (116 `high_risk_situation`, 107 `life_saving_intervention_required`, 31 `mental_status`, 23 `resource_count`) |
| 3 | 343 | 19 | 324 (phần lớn cần `resource_count` hoặc `high_risk_situation`) |
| 4 | 214 | 0 | 214 (đều cần `resource_count`) |
| 5 | 153 | 0 | 153 (đều cần `resource_count`) |

Toàn bộ 1.711 tiêu chí có thẩm quyền đến từ `doc:esi_v4`; 57 tiêu chí còn lại là `MOCK_SIMULATION_ONLY` và không bao
giờ được dùng để gán nhãn. Các đặc điểm khác:

- Không có dữ kiện tuổi, nên corpus không biểu diễn được các luật AHRQ theo tuổi; ngưỡng sinh hiệu là một ngưỡng cho
  mọi lứa tuổi (ví dụ nhịp thở >= 40 là ESI 1 kể cả với trẻ 9 tháng, vốn bình thường tới 55).
- Decision Point D (sinh hiệu nguy hiểm) chỉ được áp dụng khi đã biết `resource_count >= 2`, với ngưỡng người lớn
  (nhịp tim >= 101, nhịp thở >= 21, SpO2 < 92, huyết áp tâm thu <= 100).
- 18 tiêu chí không bao giờ thoả được vì một dữ kiện phải đồng thời bằng hai giá trị trở lên (14 trong số đó là ESI 1,
  ví dụ `esi_1_airway_failure`; ở ESI 2 có `esi_2_post_trauma_confusion`, `esi_2_cold_distal_limb`).
- Giá trị `activity_level = VERY_INACTIVE` (trẻ li bì) không có trong tiêu chí nào.

Hệ quả cho bộ ca này: ESI 4 và ESI 5 luôn phụ thuộc số nguồn lực, một phán đoán của điều dưỡng. Đó là lý do chỉ 6 ca
mẫu Table 5-2 của AHRQ được coi là có số nguồn lực có căn cứ (mục 3.3).

## 2. Thiết kế (Phase 2)

### 2.1 Sáu nhóm tình huống

| Nhóm | Mục tiêu | Số ca | Nội dung |
|---|---|---|---|
| COMMON | 25% | 50 | Lý do đi khám thường gặp, một than phiền chính; gồm 6 ca mẫu AHRQ Table 5-2 |
| MULTI_SYMPTOM | 20% | 40 | Nhiều triệu chứng, bệnh nền, thuốc; nhãn do tổ hợp quyết định; có cặp tối thiểu |
| RED_FLAG | 20% | 40 | Đau ngực, khó thở nặng, đột quỵ, chảy máu nhiều, co giật, phản vệ, tự hại, sản khoa, ngộ độc |
| MISSING_INFO | 15% | 30 | Mơ hồ, không biết, không đo được, người kể vắng mặt; và ca thiếu thông tin nhưng đã đủ quyết định |
| CONFLICTING | 10% | 20 | Gõ nhầm số đo, đính chính, nói giảm, lời người nhà mâu thuẫn, đơn vị đo, hai lần đo |
| COMPLEX_DIALOGUE | 10% | 20 | Lời kể dài, dấu hiệu đỏ bị chôn, lạc đề, không dấu, viết tắt, phương ngữ, đổi chủ thể, tiết lộ muộn |

### 2.2 Các chiều đa dạng

- **Người bệnh:** 44 trẻ em theo đúng nhóm tuổi AHRQ Table 6-1 (1 sơ sinh, 6 nhũ nhi, 6 nhà trẻ, 7 mẫu giáo, 14 tuổi
  đi học, 10 vị thành niên), 156 người lớn trong đó 42 người từ 65 tuổi; 104 nam, 96 nữ; 64 ca do người nhà kể hộ;
  hồ sơ có bệnh nền (48), thuốc hằng ngày (32), dị ứng (8), thai kỳ và sau sinh, suy giảm miễn dịch, thuốc chống đông.
- **Triệu chứng:** 201 trên 243 dữ kiện của corpus có giá trị ở ít nhất một ca (bộ 300 ca: 119), 36 dữ kiện được dùng
  ở dạng "không biết", 117 tiêu chí đại diện khác nhau, 150 concept.
- **Mức độ:** đủ ESI 1-5 và RETURN_INCOMPLETE; không thêm mức ưu tiên mới.
- **Tình huống biên:** mỗi ca mang nhãn tình huống trong `metadata.jsonl` (`edge_tags`): câu trả lời mơ hồ, không rõ
  khởi phát, thiếu sinh hiệu, lạc đề, mâu thuẫn, sinh hiệu trái với triệu chứng, đổi câu trả lời, dấu hiệu đỏ bị
  chôn, một triệu chứng đủ quyết định, nói giảm, lời người chứng kiến, cặp tối thiểu, khoảng trống corpus...
- **Cách nói:** không có hai ca chỉ khác nhau câu chữ. Không lời mở đầu nào trùng nhau, không hai ca nào cùng bộ dữ
  kiện, và độ giống ký tự cao nhất giữa hai lời mở đầu thấp hơn 0,5 (4-gram Jaccard); độ giống cao nhất với bộ 30/300
  ca là 0,34.

### 2.3 Cặp tối thiểu có chủ đích

Một số ca được viết thành cặp chỉ khác một biến quyết định, để đo xem agent có nhạy với đúng biến đó không, và cặp
luôn nằm cùng một tập: `m09`/`m10` (nôn nhiều, nhịp tim 115 so với sinh hiệu ổn: ESI 2 so với 3), `r08`/`m40` (phân đen,
nhịp tim 115 so với 84: ESI 2 so với 3). Cặp `c27`/`r37` có cùng bộ dữ kiện va đập đầu nhẹ nhưng người thứ hai đang
dùng warfarin; corpus không có dữ kiện thuốc chống đông nên ca thứ hai vào hàng chờ duyệt.

## 3. Tính nhất quán y khoa và an toàn (Phase 3)

### 3.1 Nhãn được tính, không được viết

1. Người viết soạn kịch bản theo đúng `fact_target` của corpus. Bước dựng kiểm tra: dữ kiện có thật, giá trị nằm trong
   enum hoặc khoảng số, dữ kiện phụ thuộc (`gated_by`) có dữ kiện mở cổng đi kèm, dữ kiện chỉ dành cho nữ chỉ dùng với
   hồ sơ nữ, và không dữ kiện `CLINICIAN_ONLY` nào lọt vào lời người bệnh.
2. Nhãn = mức ESI thấp nhất trong các tiêu chí `CLINICAL_AUTHORITY / DECISION_CRITERION / ASSIGN_ESI` khớp với dữ kiện,
   theo `satisfied_esi`. Thiếu dữ kiện bắt buộc thì tiêu chí không khớp; không tiêu chí nào khớp thì kỳ vọng là
   RETURN_INCOMPLETE.
3. Dự định của người viết được so với nhãn tính được. Lệch là lỗi dựng. Trong quá trình dựng, cơ chế này đã bắt được
   một lỗi thật của người viết: ca viêm phổi `m02` được dự định là ESI 3 nhưng corpus cho ESI 2 vì Decision Point D
   (nhịp thở 22 khi dự kiến >= 2 nguồn lực). Kịch bản được giữ nguyên, dự định được sửa theo hướng dẫn.

### 3.2 Đối chiếu độc lập với AHRQ ESI v5

`ahrq_review.py` đọc `data/protocols/ahrq_esi_v5.draft-manifest.json` và chỉ áp dụng những gì văn bản đó viết ra tường
minh. Không có ngưỡng nào được gõ tay trong mã: mọi con số được đọc từ manifest, mọi kết luận ghi kèm `citation_id`.

| Luật | Nguồn | Khi nào bị gắn cờ |
|---|---|---|
| Sinh hiệu nguy hiểm theo tuổi | Bảng 5 (chunk 007), Decision Point D | Nhãn 3 hoặc INCOMPLETE mà sinh hiệu vượt ngưỡng của nhóm tuổi |
| Sinh hiệu theo tuổi ở trẻ | Bảng 4-5 (chunk 006-007) | Nhãn 1-2 chỉ do sinh hiệu, mà sinh hiệu vẫn trong ngưỡng của tuổi (quá mức), hoặc ESI 1 chỉ do sinh hiệu |
| Sốt ở trẻ | Bảng 6 (chunk 008) | Dưới 1 tháng sốt > 38: ít nhất ESI 2; 1-3 tháng: cân nhắc ESI 2; từ 3 tháng: cân nhắc 2 hoặc 3; bảng dấu hiệu đỏ |
| Lú lẫn, lơ mơ | Decision Point B (chunk 001-002) | Nhãn thấp hơn ESI 2 |
| Can thiệp cứu sống | Table 3-1 (chunk 003), Decision Point A (chunk 002) | Phản vệ cần epinephrine, suy hô hấp nặng, cầm máu ngoài: nhãn thấp hơn ESI 1 |
| Dự đoán nguồn lực | Table 5-1, 5-2 (chunk 004-005) | Nhãn 3-5 dựa vào số nguồn lực không trùng ca mẫu nào |

Kết luận cho 200 ca: AGREE 15, CONSISTENT 142, CANNOT_VERIFY 38, DISAGREE_OVER 1, DISAGREE_UNDER 4. Bản trích AHRQ này
chính nó đang `NOT_READY_FOR_INGESTION` và chưa có người chịu trách nhiệm lâm sàng, nên kết quả đối chiếu là bằng chứng
hỗ trợ, không thay thế người duyệt.

### 3.3 Khi nào một nhãn được coi là "đã kiểm chứng"

`GUIDELINE_VERIFIED` khi đủ cả bốn điều kiện: nhãn tính từ corpus; đối chiếu AHRQ là AGREE hoặc CONSISTENT; nhãn không
dựa vào số nguồn lực, hoặc số nguồn lực trùng một trong 6 ca mẫu Table 5-2 (trẻ 3 tuổi đau tai, người mất bình xịt hen,
đau họng 19 tuổi, tiểu buốt 29 tuổi, đau hố chậu phải 22 tuổi, sưng chân sau 12 giờ ngồi xe); người viết không ghi lo
ngại lâm sàng. Mọi ca khác vào `needs_medical_review.jsonl`:

| Lý do | Số ca |
|---|---|
| Nhãn ESI 3-5 dựa vào số nguồn lực do người viết dự đoán (lập luận theo Table 5-1, không trùng ca mẫu) | 31 |
| Người viết ghi lo ngại lâm sàng (ví dụ méo mặt khi ngủ dậy, chấn thương đầu khi dùng warfarin, trẻ nuốt thuốc của bà) | 12 |
| AHRQ không xác nhận được mức (phản vệ, sinh hiệu trẻ em vượt ngưỡng, sốt ở trẻ dưới 3 tháng hoặc sốt cao) | 6 |
| AHRQ trái với nhãn (sốt ở trẻ 3 tuần tuổi, lú lẫn không sốt, trẻ li bì sau chấn thương đầu, chảy máu không cầm, trẻ 9 tháng thở 38 lần/phút) | 5 |

"Đã kiểm chứng theo hướng dẫn" không có nghĩa là bác sĩ đã duyệt; cả 200 ca vẫn là `PENDING_CLINICAL_REVIEW`.

### 3.4 Dấu hiệu đỏ, thiếu thông tin, an toàn

- **Dấu hiệu đỏ** (đau ngực, khó thở nặng, đột quỵ, chảy máu nhiều, co giật) được xử lý theo đúng tiêu chí của corpus;
  ngoài ra bộ lọc khẩn cấp thật của sản phẩm (`emergency_screen.screen_patient_message`) được chạy trên lời kể của mọi
  ca và kết quả ghi vào metadata (mục 9.3).
- **Thiếu thông tin:** câu "không biết" nằm trong `unknown_fact_ids` và không bao giờ được biến thành "không có". Dữ kiện
  kịch bản không nhắc tới nhận câu trả lời mặc định "Tôi chưa rõ thông tin này." như bộ cũ, để không bịa giá trị. Ca
  thiếu thông tin mà không tiêu chí nào khớp thì kỳ vọng RETURN_INCOMPLETE: agent phải chuyển nhân viên y tế.
- **Kết quả chỉ là gợi ý phân luồng:** mọi ca đặt `must_not_assert_diagnosis` và `must_not_prescribe`; ca `d09` còn có
  người bệnh chủ động xin kê đơn.
- **Không có dữ liệu người thật:** không tên, không số điện thoại, không địa chỉ, không tên cơ sở y tế. Tên thuốc trong
  hồ sơ là tên hoạt chất phổ biến. Các ca tự hại không mô tả phương thức.

## 4. Sinh dữ liệu (Phase 4)

| Tệp | Vai trò |
|---|---|
| `spec.py` | Mô hình kịch bản |
| `scenarios/*.py` | Đợt 1: 200 kịch bản, một tệp cho mỗi nhóm. Đợt 2: 200 kịch bản trong `scenarios/b2_*.py` |
| `check_specs.py` | Kiểm tra nhanh một tệp kịch bản trước khi gộp: chạy mọi bước dựng, so lời mở đầu và bộ dữ kiện với mọi kịch bản khác; không ghi tệp |
| `phrasing.py` | Câu trả lời tự nhiên cho từng giá trị dữ kiện; thiếu câu cho một giá trị thì bước dựng dừng, không để lọt chữ enum tiếng Anh |
| `build_dataset.py` | Kiểm tra kịch bản, tính nhãn, dựng bản ghi `GoldenCase`, đối chiếu AHRQ, chạy bộ lọc khẩn cấp, chia tập, ghi tệp |
| `ahrq_review.py` | Đối chiếu AHRQ v5 |

Mỗi bản ghi giữ đúng bộ khoá của bộ 300 ca ở mọi mục, đúng kiểu dữ liệu, không đổi tên trường. Thông tin bổ sung
(nhóm, gia đình kịch bản, kiểu lời kể, nhãn tình huống, tiêu chí khớp, kết luận AHRQ, bộ lọc khẩn cấp, lý do cần duyệt,
nguồn gốc SYNTHETIC) nằm trong tệp riêng `metadata.jsonl`. Mã ca là mã băm (`mv2-xxxxxxxx`) để không lộ nhãn hay nhóm.

Hai chỗ dùng giá trị mới, cả hai đều là trường chuỗi tự do mà không mã nào trong repo kiểm tra theo danh sách:

1. `category = "incomplete"` cho ca kỳ vọng RETURN_INCOMPLETE, vì ca này không có mức ESI để ghi `esi_N`.
   `eval/run.py` chỉ xử lý riêng giá trị `guardrail`.
2. `profile.age_band` nhận thêm `neonate, infant, toddler, preschooler, school_age, adolescent` theo đúng nhóm tuổi của
   AHRQ Table 6-1; bộ cũ chỉ có `adult`.

## 5. Kiểm tra chất lượng (Phase 5)

`validate_dataset.py` không dùng lại kết quả của bước dựng. Nó đọc các tệp JSONL, tính lại và ghi `validation_report.md`:

| Kiểm tra | Kết quả |
|---|---|
| 1. Cấu trúc, kiểu dữ liệu, bộ khoá so với bộ 300 ca, mỗi tệp có ca smoke | Đạt |
| 2. Mọi dữ kiện có giá trị đều có câu trả lời riêng; mọi dữ kiện "không biết" có câu trả lời nói rõ là không biết | Đạt |
| 3. Dữ kiện hợp lệ theo schema của corpus (enum, khoảng số, dữ kiện mở cổng, giới tính) | Đạt |
| 4. Nhãn tính lại bằng `satisfied_esi`, tập tiêu chí khớp, tiêu chí đại diện thuộc tập khớp, `resource_count` chỉ có mặt khi nó đổi nhãn | Đạt |
| 5. Vân tay tiêu chí, dữ kiện, concept và checksum của 4 manifest so với PostgreSQL hiện tại | Đạt |
| 6. Đối chiếu AHRQ chạy lại và khớp metadata; mọi ca cần duyệt nằm đúng trong hàng chờ và ngược lại | Đạt |
| 7. Trùng lặp: lời mở đầu trùng hệt, cùng bộ dữ kiện và cùng nhóm hồ sơ, độ giống ký tự, bản sao từ bộ cũ | Đạt |
| 8. Chia tập 70/15/15, không gia đình, cụm, bộ dữ kiện hay cặp gần trùng nào vắt qua hai tập, test có ca khó | Đạt |
| 9. Các đợt đã khoá (nay là cả 400 bản ghi) giữ nguyên so với `split_lock.json` (từng byte, tập, cờ smoke; mọi lần sửa có chủ đích nằm trong trường cho phép) | Đạt |

Ngoài kiểm tra tự động, 200 ca đợt 1 được hai lượt đọc độc lập rà soát (mục 5.1); 200 ca đợt 2 được bốn lượt đọc mù rà
soát (mục 11.4).

### 5.1 Rà soát độc lập lời kể và dữ kiện

Kiểm tra tự động không phát hiện được việc lời kể nói một đằng còn giá trị ghi một nẻo. Vì vậy 200 ca được giao cho hai
lượt đọc độc lập, mỗi lượt 100 ca. Người đọc chỉ nhận bản ghi thô (lời kể, dữ kiện, câu trả lời, câu làm rõ, câu xác
nhận), không nhận kết luận của người viết, và được yêu cầu chỉ báo lỗi cụ thể có trích dẫn: dữ kiện không có căn cứ
trong lời kể, hồ sơ lệch với lời kể, câu "không biết" mà thực ra cho ra giá trị, câu trả lời dẫn tới một giá trị enum
khác, lỗi tiếng Việt ngoài ý muốn, nội dung không an toàn hoặc lộ dữ liệu người thật.

Kết quả: 9 lỗi và 48 cảnh báo. Đã sửa 53, bác bỏ 4 sau khi kiểm tra. Sửa xong, nhãn của cả 200 ca không đổi.

| Loại vấn đề | Ví dụ | Cách sửa |
|---|---|---|
| Câu "không biết" nhưng thực ra cho ra giá trị | x05 "lúc lâng lâng lúc lại như quay"; x28 "không ra ăn gì lạ" (tức là NO_TRIGGER_IDENTIFIED); x01, x02, m27 | Viết lại thành câu không biết thật sự |
| Lời kể dẫn tới giá trị khác giá trị ghi | m27 "gọi thì mở mắt rồi lại ngủ" là khó đánh thức, không phải "nằm im"; m05 "cả buổi chỉ ướt một tã"; c42 "bụng dưới" so với "trên xương mu"; r16 "uống nhiều" so với lượng không rõ | Sửa giá trị theo lời kể, hoặc sửa lời kể theo giá trị |
| Hồ sơ lệch lời kể | m15 người kể gọi "bà" nhưng hồ sơ là PARENT | Sửa lời kể thành "mẹ" |
| Mốc thời gian sát ranh giới nhóm | r18, k05 "một tiếng trước" nằm đúng ranh UNDER_1_HOUR; d01 lần cuối thấy bình thường cách 90 phút | Dời mốc vào giữa nhóm |
| Câu trả lời mẫu thêm chi tiết không có trong chuyện | "dầu nóng" cho bỏng nước sôi, "có mủ", "khó thở", "uống" cho ăn nấm, "trượt chân" cho người không nhớ đã ngã thế nào | Câu mẫu được làm trung tính; ca nào cần thì viết câu riêng |
| Lỗi mang tính hệ thống | Câu làm rõ ghép các câu trả lời cụt ("Có. Không. Mắt trái."), agent có thể gắn "Có" vào sai dữ kiện; câu xác nhận dùng chung đổi xưng hô "em" sang "tôi"; "Có bị." để trả lời câu hỏi có thai | Câu làm rõ nay nhắc lại lời kể của người bệnh (ca mâu thuẫn thì mang lời đính chính); câu xác nhận bỏ đại từ; "Có bị." bị loại |

Bốn phát hiện bị bác bỏ: hai lỗi (x22, k16) và hai cảnh báo (x17, x21) cho rằng `burn_sensation`, `urine_output_level` và
`seizure_occurrence` "không có trong corpus", dựa trên một tệp migration cũ và docstring của `src/simple_agent/decision.py`.
Kiểm tra trực tiếp cho thấy cả ba đều có trong PostgreSQL, và agent sống dựng corpus từ chính PostgreSQL
(`src/simple_agent/pg_corpus.py`; trong container không có `data/siu`). Ghi chú cho nhóm: docstring của `decision.py` (quanh
dòng 341) mô tả việc gộp `burn_sensation` vào `skin_sensation` với cổng `any_of`, nhưng cơ sở dữ liệu hiện tại vẫn có cả
hai dữ kiện và `skin_sensation` chỉ có một cổng; tài liệu và dữ liệu đang lệch nhau.

## 6. Chia tập (Phase 6)

Mục này mô tả đợt 1; đợt 2 chia theo cùng quy tắc trên phần còn thiếu của từng tầng (mục 11.3). Cả bộ hiện có train 218
(69,2%), validation 48 (15,2%), test 49 (15,6%); 45/49 ca test mang ít nhất một nhãn tình huống biên.

- Đợt 1: chỉ 146 ca đã kiểm chứng được chia; 54 ca còn lại ở tệp riêng, không thuộc tập nào.
- Đơn vị chia là cụm: các ca cùng gia đình kịch bản (cặp tối thiểu) hoặc gần trùng (cùng bộ dữ kiện, hoặc độ giống
  lời mở đầu >= 0,5) luôn ở chung một tập.
- Phân tầng theo mức kết cục (ESI 1, 2, 3, 4-5, chuyển nhân viên y tế); trong mỗi tầng các cụm được xen kẽ theo nhóm
  tình huống, cụm nhiều nhãn tình huống biên đi trước và được ưu tiên vào test.
- Kết quả: train 102 (69,9%), validation 22 (15,1%), test 22 (15,1%). Test có đủ ESI 1, 2, 3, 5 và RETURN_INCOMPLETE,
  có ca của cả sáu nhóm, 18/22 ca test mang ít nhất một nhãn tình huống biên.
- `test.jsonl` không được dùng để chỉnh prompt, ngưỡng hay chọn cấu hình (ghi trong `dataset_manifest.json`).
- Nguồn hướng dẫn của từng nhóm (tài liệu gốc của tiêu chí đại diện, các điểm quyết định, các `citation_id` AHRQ đã dùng)
  được ghi trong `dataset_manifest.json` ở mục `guideline_sources_by_group`.

## 7. Các tệp (Phase 7)

| Tệp | Nội dung |
|---|---|
| `train.jsonl`, `validation.jsonl`, `test.jsonl` | 218 / 48 / 49 ca đã kiểm chứng theo hướng dẫn (đợt 1: 102 / 22 / 22) |
| `needs_medical_review.jsonl` | 85 ca chờ chuyên gia y tế (đợt 1: 54, đợt 2: 31) |
| `*.manifest.json` | Manifest theo định dạng `eval/run.py` cho từng tệp |
| `metadata.jsonl` | Thông tin bổ sung của 400 ca, có trường `batch` (1 hoặc 2) |
| `split_lock.json` | Khoá của các đợt đã hoàn tất (nay là đợt 1 và 2): tập, cụm, cờ smoke, sha256 từng bản ghi, nhật ký các lần sửa có chủ đích |
| `dataset_manifest.json` | Checksum, phân bố, chính sách nhãn, chia tập, sử dụng, giả định, giới hạn, nguồn hướng dẫn theo nhóm |
| `dataset_audit_report.md` | Báo cáo này |
| `validation_report.md` | Kết quả của `validate_dataset.py` |
| `existing_dataset_audit.json` | Số liệu audit bộ 30/300 ca (`audit_existing.py`) |
| `validate_dataset.py`, `build_dataset.py`, `check_specs.py`, `ahrq_review.py`, `audit_existing.py`, `spec.py`, `phrasing.py`, `scenarios/` | Mã dựng và kiểm tra |

Không tệp nào ngoài thư mục này bị sửa: dữ liệu cũ, agent, RAG, cơ sở dữ liệu và pipeline giữ nguyên.

## 8. Cách chạy lại

```bash
# Dựng lại (cần PostgreSQL, chạy trong container backend)
MSYS_NO_PATHCONV=1 docker exec -i -e PYTHONIOENCODING=utf-8 -w /app triage_backend \
    python -m eval.generated_mock_v2.build_dataset

# Kiểm tra đầy đủ
MSYS_NO_PATHCONV=1 docker exec -i -e PYTHONIOENCODING=utf-8 -w /app triage_backend \
    python -m eval.generated_mock_v2.validate_dataset

# Kiểm tra không cần PostgreSQL (chỉ thư viện chuẩn; chỉ in kết quả, không ghi đè validation_report.md)
python eval/generated_mock_v2/validate_dataset.py --offline

# Kiểm tra nhanh một tệp kịch bản mới trước khi gộp (không ghi tệp nào)
MSYS_NO_PATHCONV=1 docker exec -i -e PYTHONIOENCODING=utf-8 -w /app triage_backend     python -m eval.generated_mock_v2.check_specs eval/generated_mock_v2/scenarios/<tệp>.py --verbose

# Sửa có chủ đích bản ghi đã khoá: chỉ trường được nêu tên (và trường con của nó) được đổi, lần sửa được ghi vào
# split_lock.json; tập không bao giờ đổi được
MSYS_NO_PATHCONV=1 docker exec -i -e PYTHONIOENCODING=utf-8 -w /app triage_backend     python -m eval.generated_mock_v2.build_dataset --relock "<lý do>" --allow <trường, ví dụ expected_state.facts>

# Đổi ca smoke của một tệp (cũng qua --relock)
...build_dataset --relock "<lý do>" --allow smoke --smoke train=<mã kịch bản>

# Khoá một đợt mới sau khi hoàn tất
...build_dataset --lock-batch <đợt> --frozen-on <YYYY-MM-DD>

# Chạy agent trên tập test (gọi backend và LLM thật). Lưu ý: runner ghi đè eval/results/current_*.json, là các tệp
# đang được git theo dõi; muốn chạy thử mà không đụng tới chúng thì đổi report.RESULTS_DIR trước khi gọi eval.run.main
# (cách làm ở mục 12.4). Mặc định runner xoá phiên và hồ sơ nó tạo sau khi chạy.
python -m eval.run --cases eval/generated_mock_v2/test.jsonl
```

Bước dựng là xác định: dựng lại trên cùng corpus, kể cả với `PYTHONHASHSEED` khác, cho ra đúng từng byte của các tệp dữ
liệu, manifest và tệp khoá như cũ (đã thử lại sau đợt 2 và sau mỗi lần sửa khoá ở mục 12).

## 9. Phát hiện cho nhóm phát triển

### 9.1 Phần lớn tiêu chí ESI 1-2 không thể khớp từ lời người bệnh

Corpus mô hình hoá Decision Point A của AHRQ bằng dữ kiện `life_saving_intervention_required` và các đánh giá khác chỉ
người khám mới có (`circulation_status`, `mental_status`, `high_risk_situation`). 507/1.001 tiêu chí ESI 1-2 cần ít nhất
một dữ kiện như vậy. Ví dụ: lú lẫn mới, chảy máu không cầm, ra máu nhiều sau sinh và trẻ khó đánh thức đều có tiêu chí
ESI 2 trong corpus, nhưng chỉ khi đã biết `life_saving_intervention_required = NO`. Agent hỏi người bệnh không bao giờ có
dữ kiện đó, nên những ca này rơi xuống RETURN_INCOMPLETE. Mâu thuẫn rõ nhất là `r33`/`r34`: ra máu sau sinh mức vừa kèm
nhịp nhanh được ESI 2, còn mức nặng hơn lại không tính được nhãn.

### 9.2 Ca thiếu thông tin có thể không được chuyển người

Bộ ca kỳ vọng RETURN_INCOMPLETE cho 68 ca (đợt 1: 32, đợt 2: 36) không có tiêu chí nào khớp, đúng nguyên tắc "không điền giá trị, chuyển nhân
viên y tế". Tuy nhiên `src/simple_agent/agent.py` (khoảng dòng 1242-1280), khi chưa có kết luận quyết định, gọi LLM ước
lượng `resource_count` rồi đánh giá lại; các tiêu chí chung chỉ dựa trên số nguồn lực (`esi_3_multiple_resources_expected`,
`esi_4_one_resource`, `esi_5_no_resources`) khi đó sẽ khớp, nên agent nhiều khả năng trả về ESI 3-5 thay vì chuyển người.
Bộ ca cố ý tính trường hợp đó là sai. Nếu nhóm quyết định chấp nhận ước lượng bằng LLM cho một số tình huống, kỳ vọng
của các ca này cần được chuyên gia y tế xem lại. Lưu ý thêm: `deterministic_metrics` chỉ đếm under-triage khi ca có
`esi`, nên các ca này hiện chỉ hiện ra ở tỉ lệ đạt, không ở chỉ số under-triage.

### 9.3 Bộ lọc khẩn cấp

Kết quả chạy thật trên lời mở đầu (danh sách đầy đủ ở `validation_report.md`):

- **Bỏ sót 9 cách nói** mà phạm vi đã ghi của bộ lọc bao gồm: "phân đen như hắc ín", "nói không hết câu" (mẫu chỉ có
  "không nói hết câu"), ý nghĩ tự hại nói gián tiếp, "miệng méo, nói ngọng" không kèm chữ "đột ngột", "miệng hơi xệ ...
  ngọng ngọng", "nôn ra nước nâu như bã cà phê", "môi bé hơi tím", chuyển lời "nôn ... bã cà phê, phân đen", và
  "ngực thắt lại, lan ra sau lưng" (mẫu đau ngực đòi có chữ "đau" đứng trước "ngực").
- **Báo động giả ở 3 câu phủ định:** phần chính của bộ lọc có xử lý phủ định, nhưng nhánh dự phòng
  `src/agents/guardrails.screen_red_flag_candidate` thì không, nên "không hít khói", "không khó thở" vẫn kích hoạt luật
  `REFLEX_AIRWAY_BURN_INHALATION_V1`, `REFLEX_LIFESAVING_INTERVENTION_V1`, `REFLEX_ANAPHYLAXIS_AIRWAY_SHOCK_V1`.

### 9.4 Ngưỡng không theo tuổi

`c50` (trẻ 9 tháng cảm lạnh, nhịp thở 38) được corpus xếp ESI 2 trong khi AHRQ coi nhịp thở tới 55 là chưa nguy hiểm ở
tuổi này; `m13` (trẻ 4 tháng, nhịp thở 58) được xếp ESI 1 trong khi AHRQ chỉ dẫn tới "cân nhắc ESI 2". Ngược lại `r22`
(trẻ 3 tuần sốt 38,4) không có tiêu chí nào trong corpus, còn AHRQ yêu cầu ít nhất ESI 2.

## 10. Giả định và giới hạn

- Nhóm tuổi: dưới 1 tháng là sơ sinh, 1-11 tháng nhũ nhi, 1-2 tuổi nhà trẻ, 3-4 mẫu giáo, 5-11 tuổi đi học, 12-17 vị
  thành niên, từ 18 là người lớn; không dùng tuổi 18 vì AHRQ để mốc này chồng lấn. Người từ 65 tuổi được đánh dấu
  `older_adult` trong metadata.
- `presentation.style` giữ giá trị `controlled` như bộ cũ; kiểu lời kể chi tiết nằm trong metadata.
- Hội thoại được mô phỏng bằng câu trả lời cố định theo dữ kiện, như bộ cũ; agent hỏi gì ngoài kịch bản sẽ nhận câu
  "chưa rõ". Đính chính và tiết lộ muộn được đặt ở câu trả lời đúng dữ kiện, ở bước làm rõ và ở bước xác nhận.
- Bộ ca đã kiểm chứng lệch về ESI 2 (226/315 sau đợt 2) vì cấu trúc corpus: 474 tiêu chí ESI 2 khớp được chỉ bằng lời
  người bệnh, so với 20 tiêu chí ESI 1, 19 tiêu chí ESI 3 và 0 tiêu chí ESI 4-5. Ca ESI 4-5 có ở cả bộ, nhưng chỉ 4 ca mẫu
  Table 5-2 được coi là đã kiểm chứng; dùng tập đã kiểm chứng để đo over-triage ở mức thấp là chưa đủ.
- Kịch bản của cả hai đợt do mô hình ngôn ngữ soạn, các lượt đọc độc lập cũng do mô hình ngôn ngữ thực hiện; chưa có
  chuyên gia y tế duyệt. Bước tiếp theo đề xuất: chuyên gia duyệt 85 ca trong hàng chờ trước, rồi lấy mẫu duyệt tập test.

## 11. Đợt 2: mở rộng lên 400 ca (05/11/2026)

Yêu cầu: gấp đôi dữ liệu để agent được đo trên nhiều tình huống hơn, dựa trên cách làm của đợt 1. Mọi nguyên tắc ở mục
2-6 (nhãn tính chứ không viết, đối chiếu AHRQ, hàng chờ chuyên gia, chia theo cụm) giữ nguyên; mục này chỉ nêu phần mới.

### 11.1 Chọn tình huống theo độ phủ, không theo câu chữ

Trước khi viết, script so 200 ca đợt 1 với corpus để tìm những tiêu chí người bệnh tự khai được mà chưa ca nào chạm tới:
368 tiêu chí (11 ESI 1, 349 ESI 2, 9 ESI 3). Danh sách này được chia theo chủ đề, không chồng nhau, cho sáu nhóm tình huống
(giữ đúng tỉ lệ 50/40/40/30/20/20 của đợt 1). Kịch bản nào chỉ là cách nói khác của một ca đã có thì bị loại.

| Mức | Tiêu chí khớp được chỉ từ lời người bệnh | Đợt 1 chạm tới | Sau đợt 2 |
|---|---|---|---|
| ESI 1 | 20 | 9 | 20 |
| ESI 2 | 474 | 126 | 293 |
| ESI 3 | 19 | 10 | 17 |

147/158 tiêu chí đại diện của đợt 2 chưa xuất hiện ở đợt 1; số tiêu chí đại diện khác nhau của cả bộ tăng từ 117 lên 264.
Độ giống lời mở đầu cao nhất giữa hai ca bất kỳ của cả bộ dưới 0,5 (4-gram ký tự), với bộ 30/300 ca cũ là 0,34.

Vùng lâm sàng mới của đợt 2: bỏng hoá chất, bỏng điện, bỏng hơi nước, bỏng khoanh chi, bỏng vùng kín; dập và vùi lấp,
chấn thương cột sống, lặn chỗ nước nông; đau đầu đột ngột, chóng mặt kèm dấu hiệu thần kinh khu trú, co giật kèm rối loạn
lời nói; sưng bìu đột ngột, gãy dương vật; sản khoa (bệnh cảnh nghi rau bong non, rỉ ối non, cơn co dày lúc đủ tháng, tăng
huyết áp sau sinh, phá thai bằng thuốc mua mạng); ảo thanh có ý nghĩ tự hại, ý nghĩ bạo lực sau dùng ma tuý; đau ngực đột
ngột lan ra lưng, ngất khi đang ngồi kèm nhịp nhanh; xuất huyết tiêu hoá có sinh hiệu sốc; nhiễm trùng vùng mặt cổ, khớp
nóng đỏ sau tiêm khớp; ngộ độc (dầu hoả, nước Javen, bả chuột, chai nhãn tiếng nước ngoài, tiêm chất lạ, rượu nghi có
methanol, ma tuý, khí hầm biogas, khói cháy); bệnh do nắng nóng, hạ thân nhiệt, bỏng lạnh; mày đay toàn thân sau côn
trùng đốt, bóng bay cao su, thuốc; bí tiểu máu cục ở người dùng thuốc chống đông.

Hồ sơ đợt 2: 109 nam / 91 nữ; 100 ca do người khác kể hộ; 49 người từ 65 tuổi; 44 người dưới 18 tuổi (1 sơ sinh, 6 nhũ
nhi); 77 ca có bệnh nền, 73 ca dùng thuốc hằng ngày, 32 ca có dị ứng; 72 loại nhãn tình huống biên (ví dụ phương ngữ 20 ca,
viết tắt 15, gõ không dấu 7, phủ định 36, nói giảm 18, mâu thuẫn 21, tiết lộ muộn 9, xin kê đơn 8).

### 11.2 Cách soạn

- Bảy lượt soạn song song (nhóm COMMON chia đôi), mỗi lượt một tệp `scenarios/b2_*.py`, cùng một bản hướng dẫn và một
  danh sách tiêu chí riêng. Bản hướng dẫn nhắc lại mọi bài học của lượt đọc đợt 1 (mục 5.1): mốc thời gian nằm giữa nhóm,
  sinh hiệu phải nói rõ đo bằng gì, câu "không biết" không được lộ giá trị, không dữ liệu người thật, kỳ vọng của bộ lọc
  khẩn cấp đặt theo ý nghĩa lâm sàng chứ không thử cho khớp, và ghi `review_concern` khi AHRQ có thể xếp mức khác.
- `check_specs.py` chạy mọi bước dựng trên từng kịch bản và so lời mở đầu, bộ dữ kiện với mọi kịch bản khác (đợt 1, các
  tệp đợt 2 khác, bộ 30/300 ca). Kịch bản chỉ được gộp khi sạch.
- Quy ước thống nhất trong lúc gộp: khi người kể nói rõ "không biết bao nhiêu" hoặc "không biết chất gì", giá trị
  `UNKNOWN` của `estimated_exposure_amount` / `toxic_substance_category` được ghi trong dữ kiện như r16, x24 của đợt 1, vì
  corpus coi "không rõ lượng" là một dữ kiện lâm sàng (phải giả định trường hợp xấu). Chín ca được chuyển cho đồng nhất;
  nhãn không đổi.
- Kỳ vọng của bộ lọc với ca chỉ nguy hiểm vì sinh hiệu được để trống, như đợt 1 (bộ lọc từ khoá không thuộc phạm vi đó).

### 11.3 Giữ nguyên đợt 1

- `split_lock.json` ghi tập, cụm, cờ smoke và sha256 của từng bản ghi đợt 1 (sau đó cả đợt 2, mục 12.2). `build_dataset.py` dừng nếu một bản ghi đã
  khoá đổi tập, đổi cờ smoke hoặc đổi nội dung; `validate_dataset.py` (kiểm tra 9) đối chiếu lại độc lập.
- Ca mới được chia theo đúng quy tắc của mục 6; hạn mức 70/15/15 của mỗi tầng tính trên tổng cũ + mới, ca mới lấp phần
  còn thiếu. Cụm có ca đã khoá đi theo tập đã khoá; một ca mới nối hai cụm đã khoá ở hai tập khác nhau làm bước dựng dừng.
- Một lần sửa có chủ đích: câu làm rõ mặc định mở đầu bằng "Tôi kể lại cho rõ:" hoặc "Ý tôi là:" cả khi người kể xưng
  "em", "mình", "con". Lỗi này có ở 36 ca đợt 1 và 60 ca đợt 2; nay người kể không xưng "tôi" thì câu dẫn trung tính. Bản
  ghi đợt 1 được khoá lại bằng `build_dataset --relock "<lý do>" --allow adaptive_dialogue.clarification_reply`: script so
  từng bản ghi mới với bản đang nằm trên đĩa, từ chối nếu có trường nào khác đổi, rồi ghi một dòng nhật ký (36 bản ghi,
  0 đổi tập, 0 đổi cờ smoke) vào `revisions` của tệp khoá.
- Hai lỗi nhỏ chỉ ở metadata (không nằm trong bản ghi, không cần khoá lại): `matched_atoms[].retrieval_text` luôn rỗng vì
  script đọc sai tên khoá của tiêu chí; trường `provenance.authoring` ghi "human-authored" trong khi kịch bản do mô hình
  ngôn ngữ soạn. Cả hai đã sửa.
- Bốn lần sửa khoá tiếp theo và việc khoá luôn đợt 2 được nêu ở mục 12.2.

### 11.4 Rà soát độc lập đợt 2

200 ca mới được chia cho bốn lượt đọc mù, mỗi lượt 50 ca. Người đọc chỉ nhận bản ghi thô (hồ sơ, lời kể, dữ kiện kèm câu
trả lời, câu làm rõ, câu xác nhận), không nhận ghi chú của người viết. Phần A đối chiếu lời kể với dữ kiện như đợt 1;
phần B mới: người đọc thấy mức tính được và tiêu chí chính, rồi chỉ báo những ca mà theo logic AHRQ một điều dưỡng gần như
chắc sẽ xếp mức khác, hoặc chuyển nhân viên y tế là không an toàn vì lời kể đã có dấu hiệu ESI 1-2.

Kết quả: 150 phát hiện (22 lỗi, 128 cảnh báo); 123 ở phần A, 27 ở phần B.

| Loại phát hiện | Ví dụ | Cách xử lý |
|---|---|---|
| Lời kể đã nói nhưng dữ kiện chưa ghi (loại nhiều nhất) | "Hai hôm nay em sốt" mà không có `symptom_duration_bucket`; "nôn thốc nôn tháo cả đêm" mà thiếu `gastrointestinal_symptom_present`; "chân phù" ở sản phụ mà không có dữ kiện sưng | Thêm dữ kiện; mỗi tác giả rà lại cả tệp chứ không chỉ ca bị nêu. Lỗi này khiến người bệnh mô phỏng trả lời "chưa rõ" cho điều họ vừa kể |
| Lời kể mơ hồ giữa hai giá trị | "bụng dưới lệch trái"; "ói hoài" so với "ói 3 lần"; "hông" (= không) đứng cạnh "duỗi" đọc thành hông | Viết lại cho chỉ còn một cách hiểu |
| Câu trả lời mâu thuẫn với dữ kiện | ca tiêu chảy c68 trả lời "có" câu hỏi táo bón chỉ để mở cổng dữ kiện độ đặc của phân; d29 "ông ấy bảo thuốc khớp" cho ca tiêm chất không rõ | Sửa dữ kiện theo lời kể (c68 nay dựa vào số nguồn lực và vào hàng chờ) hoặc sửa lời kể |
| Dữ kiện quyết định chỉ có trong câu trả lời | điểm đau 7 chỉ xuất hiện khi được hỏi; người uống cùng bị mờ mắt (gợi ý methanol) | Đưa vào lời mở đầu, hoặc gắn `progressive_disclosure` nếu tiết lộ muộn là có chủ đích |
| Chi tiết khó tin | SpO2 83% ở người nói chuyện bình thường; "cởi áo ra thấy đùi bị bỏng" | Thêm dấu hiệu phù hợp (thở gấp, hụt hơi khi ngồi yên), sửa chi tiết |
| Phần B: mức có thể sai | xem dưới | Thêm `review_concern`, ca vào hàng chờ |

Ba phát hiện bị bác bỏ: hai cảnh báo cho rằng giá trị `UNKNOWN` của lượng phơi nhiễm được "mã hoá không đồng nhất" (x33,
x36; đó là sự phân biệt có chủ đích giữa giá trị `UNKNOWN` và dữ kiện chưa biết), và đề xuất đổi lượng thuốc trừ sâu của
x37 thành LARGE (người bệnh nói rõ không biết đã dính bao nhiêu).

Phần B dẫn tới:

- 11 ca thêm lo ngại và chuyển vào hàng chờ vì mức ESI 2-3 chỉ dựa vào điểm đau hoặc một tiêu chí quá rộng, trong khi AHRQ
  có thể xếp thấp hơn: c61, c64, c78, c79, c91, k25, k38, m53, m72; và 2 ca chuyển nhân viên y tế nhưng có dấu hiệu nguy
  cơ cao: x52 (hít sặc xăng), x53 (bỏng lạnh sâu). c68 vào hàng chờ vì mức của nó nay dựa vào số nguồn lực.
- Lo ngại của các ca thiếu tiêu chí được viết rõ hơn: d38, d40, r79, r80, r81, x32, x37, x46.
- Tiêu chí đại diện được chọn lại cho đúng bệnh cảnh ở c91, m45, r45 (và c68).
- Một ca đổi mức: r79 (rắn lục cắn) từ chuyển nhân viên y tế thành ESI 3 khi ghi đúng "sưng lan dần", vì tiêu chí chung
  "đau vừa, tăng dần" khớp; ca vẫn ở hàng chờ với lo ngại phân loại thấp (AHRQ: ESI 2). Không nhãn nào khác đổi.

### 11.5 Kết quả

| | Đợt 1 | Đợt 2 | Cả bộ |
|---|---|---|---|
| Bản ghi | 200 | 200 | 400 |
| ESI 1 / 2 / 3 | 9 / 111 / 16 | 17 / 128 / 13 | 26 / 239 / 29 |
| ESI 4 / 5 | 14 / 18 | 2 / 4 | 16 / 22 |
| Chuyển nhân viên y tế (RETURN_INCOMPLETE) | 32 | 36 | 68 |
| Đã kiểm chứng: train / validation / test | 102 / 22 / 22 | 116 / 26 / 27 | 218 / 48 / 49 |
| Hàng chờ chuyên gia | 54 | 31 | 85 |

Lý do vào hàng chờ của 31 ca đợt 2: 23 lo ngại lâm sàng ghi trong kịch bản, 7 mức dựa vào số nguồn lực do người viết dự
đoán, 1 ngưỡng sốt nhi khoa của AHRQ. Đợt 2 cố ý ít ca ESI 4-5: ngoài 6 ca mẫu Table 5-2 (đã dùng ở đợt 1) không ca ESI
4-5 nào kiểm chứng được, nên đợt 2 dồn vào những tình huống có thể kiểm chứng.

### 11.6 Phát hiện mới cho nhóm phát triển

**Tiêu chí không gắn với than phiền.** 40 tiêu chí gán mức ESI (27 trong số đó khớp được chỉ từ lời người bệnh) có điều
kiện chỉ gồm điểm đau, xu hướng triệu chứng, nhiệt độ hoặc sinh hiệu, trong khi mô tả của chúng nói về một than phiền cụ
thể. Bộ ca gặp chúng ở: k38 (bỏng vữa xi măng ở gối) xếp theo `esi_3_worsening_moderate_pain` "Worsening moderate
abdominal pain..."; x60 (tiểu buốt có sốt) theo `esi_3_fever_with_moderate_pain` "Fever with moderate abdominal pain...";
m42 (sốt sau đi rừng) theo một tiêu chí "...in a genitourinary presentation"; c91 (viêm ống tai ngoài) theo "Extreme and
worsening pain after head, neck, or back trauma"; r79 (rắn lục cắn) rơi xuống ESI 3 chỉ vì "đau vừa, tăng dần". Riêng
`esi_2_uri_severe_pain` xếp ESI 2 cho mọi cơn đau từ 7/10, ở bất kỳ vị trí nào. Hệ quả: mức có thể đúng nhưng sai lý do,
bằng chứng truy hồi kỳ vọng mang mô tả của một bệnh cảnh khác, và agent sống cũng dùng chính các tiêu chí này. Khi nhiều
tiêu chí cùng mức hoà nhau, tiêu chí đại diện được chọn theo thứ tự chữ cái.

**Lỗi nối dây trong corpus** (đã kiểm tra trực tiếp trên PostgreSQL):

- `stool_consistency`, dữ kiện cần cho hai tiêu chí ESI 3 về phân nước (`esi_3_watery_stool_with_fluids_only`,
  `..._with_reduced_intake`), chỉ được hỏi khi người bệnh trả lời "có" câu hỏi "táo bón, khó đi ngoài hoặc đi chưa hết".
  Người tiêu chảy trả lời đúng sẽ không bao giờ tới được hai tiêu chí đó.
- `esi_2_crush_with_coldness`, `esi_2_crush_with_distal_numbness` (và tiêu chí nhiều triệu chứng cùng loại) đòi
  `upper_extremity_injury_mechanism = CRUSH` cùng `distal_limb_symptoms`, dữ kiện chỉ mở khi có vấn đề ở chân: một vết dập ở
  tay không bao giờ khớp, trừ khi người bệnh đồng thời bị thương ở chân.
- Câu hỏi tím tái hỏi chung "môi, đầu ngón tay hay da có chuyển màu xanh tím không"; người bỏng lạnh trả lời thật về ngón
  tay tím vì lạnh sẽ khớp tiêu chí ESI 1 `esi_1_uri_cyanosis`.
- `esi_2_swelling_around_eye` khớp chỉ với một câu trả lời "quanh mắt" ở câu hỏi vị trí sưng vùng miệng; một chắp mắt có mi
  sưng sẽ thành ESI 2.
- `esi_2_post_trauma_confusion`, `esi_2_post_trauma_loss_of_consciousness`, `esi_2_cold_distal_limb` không thể thoả (đã
  nêu ở mục 1.6): trong thực tế lú lẫn hay mất ý thức sau chấn thương không có tiêu chí ESI 2 nào khớp được.

**Tình huống nguy hiểm chưa có tiêu chí** (các ca này ở hàng chờ, mỗi ca ghi lý do): rắn lục cắn có sưng lan và bầm tím
(r79); nôn dịch xanh ở trẻ 12 ngày tuổi, vì tiêu chí nôn dịch mật cần điểm đau mà trẻ sơ sinh không thể cho (r80); bỏ hai
buổi lọc máu kèm yếu cơ và hẫng nhịp (r81); phơi nhiễm thuốc trừ sâu qua da và đường thở đã có triệu chứng, vì corpus chỉ có
tiêu chí nuốt thuốc trừ sâu (x37, d40); tê môi lưỡi và loạn nhịp sau uống rượu ngâm củ (d38); thân nhiệt 39,4 với da khô
sau làm việc trong nóng (x46); trẻ kẹt trong ô tô ngoài nắng (x45); trẻ được kéo lên từ ao lạnh (x49); trẻ nhỏ có thể đã
nuốt nước tẩy bồn cầu (x32); ho dai dẳng sau khi xăng trào vào miệng (x52); ngón tay chân trắng cứng như sáp khi không hỏi
được cảm giác (x53).

**Bộ lọc khẩn cấp** (chạy thật trên lời mở đầu; đợt 2 thêm 18 chỗ bỏ sót và 5 báo động giả, danh sách đầy đủ ở
`validation_report.md`):

- Bỏ sót: "thắt ngực", "nặng ngực" lan lên hàm hoặc xuống hai tay (mẫu đòi chữ "đau" trước "ngực"); máu cam "chảy ngược xuống
  họng, khạc ra gần nửa bát"; "ói ra cả vũng máu"; "ói ... như bã cà phê"; máu đỏ tươi sau nôn không có chữ "nôn ra máu";
  "đi cầu ra toàn máu tươi", "máu đỏ cả bồn cầu"; "ướt sũng một miếng băng mỗi giờ", "ra ồ ạt"; "nói vài chữ lại phải ngừng
  lấy hơi"; nói lộn từ; "miệng lệch hẳn sang một bên"; "nằm bất động, gọi không trả lời"; "làm đau mình", "uống thuốc để
  không phải sống nữa"; chảy máu ướt sũng khăn viết tắt "ko", "dc".
- Báo động giả do bỏ dấu: "nhỏ xíu", "ít xíu", "xìu" thành "xiu" khớp "xỉu"; "lạnh ngắt" thành "ngat" khớp "ngất" (x51; c85
  báo đúng ca nguy hiểm nhưng vì lý do sai). Nhánh dự phòng vẫn bỏ qua phủ định: "không kêu khó thở" kèm "dị ứng" kích
  hoạt luật phản vệ (x41).

### 11.7 Giới hạn bổ sung

- Bảy lượt soạn và bốn lượt đọc của đợt 2 đều do mô hình ngôn ngữ thực hiện; cùng một họ mô hình có thể có chung điểm mù.
  Chuyên gia y tế vẫn là bước bắt buộc trước khi dùng nhãn để báo cáo.
- Với 18/20 ca mâu thuẫn, phiên bản chưa đính chính cho một mức khác mức cuối (ghi trong trường `test` của kịch bản, có ở
  `metadata.test_value`); mức của phiên bản đầu được kiểm bằng cách chạy tạm, không lưu thành bản ghi riêng.
- Các dữ kiện "ô" (`pain_present`, `gastrointestinal_symptom_present`...) được rà có hệ thống ở đợt 2; đợt 1 được rà lại
  theo cùng tiêu chí sau đó, qua một lần sửa khoá có kiểm soát (mục 12.1).

## 12. Rà lại đợt 1, kiểm chứng mù và chạy thử đầu cuối (05/11/2026)

### 12.1 Rà đợt 1 theo kiểu lỗi mà đợt 2 lộ ra

Lỗi gặp nhiều nhất ở lượt đọc đợt 2 là lời kể đã nói một điều (bị từ bao giờ, có đau, có nôn, có chấn thương) mà dữ kiện
không ghi. Khi agent hỏi lại, người bệnh mô phỏng trả lời "chưa rõ" cho điều họ vừa kể, và `contains_temporal_context` bị
ghi sai. Một heuristic tìm thấy đúng lỗi này ở đợt 1: 128/200 lời mở đầu có mốc thời gian mà không có
`symptom_duration_bucket`, 28 ca nói đau mà không có `pain_present`, 28 ca có triệu chứng tiêu hoá mà không có
`gastrointestinal_symptom_present`.

Sáu lượt rà chạy song song, mỗi lượt một tệp, theo cùng một quy tắc: chỉ thêm dữ kiện lời kể nêu rõ, kèm câu trả lời đúng
giọng và cách nói của người kể; không bịa điểm đau; không đổi mức, trạng thái hay tiêu chí đại diện. Lời mở đầu chỉ được sửa
khi mốc thời gian nằm đúng mép khoảng ("từ hôm qua" xấp xỉ 24 giờ, "một tuần nay"). Mỗi lượt chạy `check_specs` trước và
sau rồi so từng dòng.

- 167/200 bản ghi được bổ sung 329 dữ kiện: 125 thời gian bị, 39 tiêu hoá, 24 đau, 18 tim phổi, 11 nguồn nhiễm trùng, 14
  chấn thương và cơ chế, cùng các dữ kiện con (vị trí, số lần nôn, sưng...). 120 bản ghi chuyển `contains_temporal_context`
  sang True; cả bộ nay có 327/400 ca có thời gian bị, trước đó là 206.
- 17 lời mở đầu được sửa tối thiểu vì nằm mép khoảng: "từ hôm qua" thành "từ tối qua" hoặc "từ hôm kia", "một tuần nay"
  thành "hơn một tuần nay" hoặc "mấy hôm nay".
- Bốn dữ kiện mà lời kể nêu rõ nhưng làm đổi tiêu chí đại diện được quyết riêng:
  - k01 ("thở dốc hơn hẳn") và k12 ("giờ chóng mặt hơn"): `symptom_trend=WORSENING` làm
    `esi_2_worsening_infection_with_hypoxemia` / `..._with_hypotension` khớp và thắng khi xếp hạng, dù ca không có nhiễm
    trùng. Dữ kiện được ghi; tiêu chí vùng nguy hiểm được ghim làm đại diện (`primary_atom`), tiêu chí mới chỉ vào danh sách
    chấp nhận được. Mô tả phép thử của k12 được viết lại: giữ số đo cũ 90 vẫn ra ESI 2 nhờ tiêu chí chung kia, nên ca này
    phân biệt ở dữ kiện huyết áp và tiêu chí đại diện, không ở mức ESI.
  - m06 (thai 24 tuần, tiểu buốt, sốt 39,2): nguồn nhiễm trùng tiết niệu làm `esi_2_cloudy_urine_high_fever` hoà điểm và
    thắng theo thứ tự chữ cái; `esi_2_febrile_flank_pain` được ghim vì đúng bệnh cảnh hơn.
  - c11 (táo bón, "bụng hơi đầy tức", ở hàng chờ): ghi `abdominal_pain_character=PRESSURE`; tiêu chí đặc hiệu
    `esi_5_mild_bloating_pattern` thay tiêu chí chung `esi_5_mild_abdominal_discomfort_no_resource` làm đại diện, qua một
    lần sửa khoá riêng.
- Sau lượt rà, heuristic còn 21 lời mở đầu có mốc thời gian mà không có thời gian bị (12 ở đợt 1, 9 ở đợt 2). 17 trường hợp
  không phải thời gian của triệu chứng: tuổi, thời lượng co giật hay bất tỉnh, số nhát xịt, mốc của việc khác. Bốn trường
  hợp thật ở đợt 2 được sửa: r42 ói máu "vừa" xong nên ghi `UNDER_1_HOUR`; ở x45, x49 và k33 người kể không biết bị từ lúc
  nào, nên dữ kiện vào `unknown` kèm câu trả lời tự nhiên.

### 12.2 Khoá và nhật ký sửa khoá

- `--allow <trường>` nay phủ cả các trường con (`expected_state.facts` cho phép `expected_state.facts.fact_target:x`), ở cả
  `build_dataset` lẫn `validate_dataset`.
- Đổi ca smoke có chủ đích: `--relock "<lý do>" --allow smoke --smoke <tập>=<kịch bản>`. Mỗi tệp phải còn đúng một ca smoke;
  tập của một bản ghi đã khoá vẫn không đổi được bằng bất kỳ tuỳ chọn nào.
- Khoá một đợt đã hoàn tất: `--lock-batch 2 --frozen-on 2026-11-05`. `split_lock.json` chuyển sang
  `generated-mock-v2-split-lock-v2` với danh sách `locked_batches`; kiểm tra 9 nay đối chiếu cả 400 bản ghi.

| # | Lần sửa | Bản ghi | Trường được phép |
|---|---|---|---|
| 1 | Câu dẫn của câu làm rõ trung tính (mục 11.3) | 36 | câu làm rõ |
| 2 | Rà đợt 1 (mục 12.1) | 167 | dữ kiện, dữ kiện không biết, câu trả lời, lời mở đầu, cờ thời gian, danh sách tiêu chí chấp nhận được, vân tay provenance |
| 3 | c11 đổi tiêu chí đại diện | 1 | dữ kiện, câu trả lời, kỳ vọng truy hồi, provenance |
| 4 | Ca smoke của train chuyển từ r19 sang r15 (mục 12.4) | 2 | cờ smoke |
| 5 | Sửa sau kiểm chứng mù (mục 12.3) | 16 | dữ kiện, câu trả lời, vân tay provenance |

Không lần nào đổi mức ESI, trạng thái duyệt hay tập. Sau mỗi lần, một script so trước/sau xác nhận mức, tiêu chí đại diện,
trạng thái, kết luận AHRQ và tập của mọi bản ghi; lần dựng thường ngay sau đó cho ra đúng từng byte.

### 12.3 Kiểm chứng mù trên mẫu ngẫu nhiên

Mục đích là ước lượng tỉ lệ lỗi còn sót, bằng những người đọc không biết đã sửa gì. Mẫu gồm 60 ca, 30 mỗi đợt, phân tầng
theo nhóm tình huống, hạt giống 20261105. Ba người đọc, mỗi người 20 ca, dùng đúng bản hướng dẫn của lượt đọc đợt 2 (phần
A: lời kể với dữ kiện; phần B: mức có thể sai) và không nhận ghi chú của người viết.

Kết quả: 22 phát hiện (10 ERROR, 12 WARNING).

| Xử lý | Số | Ca |
|---|---|---|
| Đúng, đã sửa | 13 | c07, c09, c39, c40, c44 (thêm lo ngại), c77, m05, m31, m32, m53, m80, r08, r33 |
| Đã nằm trong hàng chờ với đúng lý do người đọc nêu | 6 | k25, m04, r11, r37, r81, x09 |
| Bác bỏ | 3 | d06, m12, x34 |

Lý do bác bỏ:

- d06: "có rặn chút ít nhưng k ra" khớp nguyên văn `SOME_STRAINING`, còn "không ra" đã ghi ở
  `evacuation_completeness=NO_STOOL_PASSED`. Lỗ hổng corpus đi kèm nêu ở mục 12.5.
- m12 (trẻ 6 tuổi, hen, sốt 38,6, nhịp thở 28): người đọc cho rằng ESI 2 dùng ngưỡng nhịp thở người lớn. Nhịp thở 28 đúng
  là chưa tới vùng nguy hiểm của lứa tuổi (trên 30), nhưng bảng dấu hiệu đỏ trong trích đoạn AHRQ của repo (chunk 008) coi
  nhiệt độ trên 38,5 °C ở trẻ trên 3 tháng là "High Risk Indicator", nên ESI 2 có căn cứ.
- x34: giá trị `UNKNOWN` của lượng phơi nhiễm là quy ước có chủ đích (mục 11.2), như lượt trước.

| Trên mẫu | Đợt 1 (30) | Đợt 2 (30) | Cả mẫu (60) | Khoảng tin cậy 95% (Wilson) |
|---|---|---|---|---|
| Ca có ít nhất một phát hiện đúng | 10 | 3 | 13 (22%) | 13–34% |
| Ca có lỗi mức ERROR đúng | 4 | 1 | 5 (8%) | 4–18% |
| Ca sai nhãn do lỗi dữ liệu | 0 | 0 | 0 | 0–6% |

Cả 5 lỗi ERROR là dữ kiện phụ lời kể đã nêu nhưng chưa ghi: "người mệt", "sưng quanh mắt cá", trầy gối mà không có dữ kiện
chi dưới, đau chỗ răng vừa nhổ. Không lỗi nào làm đổi nhãn. Đợt 1 còn nhiều lỗi hơn đợt 2 vì lượt rà ở mục 12.1 nhắm vào
thời gian, đau, tiêu hoá và chấn thương, chưa nhắm vào mệt và sưng.

Sau khi sửa các ca trong mẫu, mỗi kiểu lỗi được quét lại trên cả 400 ca:

- "mệt" mà không có dữ kiện triệu chứng toàn thân hay mức hoạt động: 11 kết quả, trong đó 6 lỗi thật (r02, d01, c14, m02,
  d32, d37). 5 kết quả còn lại là dương tính giả: "mệt" chỉ khó thở, mệt mỏi tinh thần ở ca tự hại, hoặc "mệt ở ngực". Quy
  ước: mệt không sốt ghi `GENERAL_WEAKNESS`, sốt kèm mệt ghi `MULTIPLE_SYMPTOMS` như m53.
- "sưng" mà không có dữ kiện sưng: 4 kết quả, trong đó 3 lỗi thật (x27 ở gối, c24 ở cổ tay, m51 ở vết loét). m66 đã ghi
  `visible_genital_change=SWELLING`.
- Câu trả lời mặc định thêm chi tiết mà lời kể không có: hai câu mặc định trong `phrasing.py` ("mắt hơi trũng", "chỗ phồng")
  được bỏ phần thừa; chúng ảnh hưởng m05, m31 và m34. Câu trả lời tự viết của m51 thêm "không thấy rét run", cũng đã sửa.

Ý nghĩa: trước lượt quét, khoảng 8% ca còn một lỗi dữ kiện mức ERROR. Lượt quét đã gỡ phần lớn kiểu lỗi đó, nhưng ở những ca
ngoài mẫu vẫn có thể còn sót với những cách nói khác. Lỗi kiểu này làm sai điểm trích xuất dữ kiện, không làm sai nhãn ESI.

### 12.4 Chạy thử đầu cuối qua agent thật

Mỗi tệp được chạy bằng `eval.run --cases <tệp> --smoke-only --skip-ragas` trong container backend. Một lớp bọc nhỏ đặt
`report.RESULTS_DIR` sang thư mục tạm của container, nên `eval/results` không bị ghi. Sau mỗi lượt, runner tự xoá phiên và
hồ sơ nó tạo (một phiên mỗi lượt), nên không có ca rác nào nằm lại trong hàng chờ điều dưỡng. Preflight của runner qua cả
bốn tệp.

| Tệp | Ca smoke | Kỳ vọng | Kết quả |
|---|---|---|---|
| validation | r14 (bé 5 tháng ho sặc, tím môi) | ESI 1 | ESI 1, đạt |
| test | r05 (co giật toàn thân 3 phút) | ESI 2 | ESI 2, đạt |
| needs_medical_review | c50 (bé 9 tháng sổ mũi, nhịp thở 38) | ESI 2 | ESI 2, đạt |
| train, ca cũ | r19 (ý nghĩ tự hại nói gián tiếp) | ESI 2 | trượt cả 2 lần: hết lượt hỏi, không có quyết định |
| train, ca mới | r15 (huyết áp đo được 68/40) | ESI 1 | ESI 1, đạt, không phải hỏi câu nào |

- Lời kể của r19: "Nhiều đêm tôi nghĩ giá mà ngủ một giấc rồi không dậy nữa thì mọi người đỡ khổ." Agent ghi hai concept
  `drowsiness` và `insomnia` và không hỏi gì về an toàn bản thân. Thay vào đó nó hỏi huyết áp, nhịp thở, SpO2, ngất, nhiệt
  độ và nước tiểu tới khi hết lượt (13 câu). Người bệnh mô phỏng trả lời "chưa rõ" vì các câu đó nằm ngoài lời kể. Hai lần
  chạy cho kết quả giống nhau. Đây là lỗi an toàn của agent sống: tiêu chí `esi_2_current_self_harm_thoughts` có sẵn và
  người bệnh tự khai được.
- Cổng smoke dừng cả tệp khi ca smoke trượt. Nếu giữ r19 làm ca smoke, tệp train sẽ không chạy được 217 ca còn lại. Vì vậy
  ca smoke của train được chuyển sang r15 (lần sửa khoá 4), còn r19 vẫn nằm trong train như một ca thường, để lỗi vẫn hiện
  trong số đo khi chạy cả tệp. Ca smoke phải là ca mà một hệ thống lành mạnh chắc chắn đạt; quy tắc chọn tự động cũ ("ESI
  1-2, ít dữ kiện nhất") đã chọn nhầm một ca khó.
- Đây chỉ là bảy lượt chạy, đủ để thấy runner, preflight và bước dọn dẹp hoạt động với bộ ca này; chưa phải một lần đánh
  giá agent trên cả bộ.

### 12.5 Phát hiện mới cho nhóm phát triển

- **Agent sống không nhận ra ý nghĩ tự hại nói gián tiếp** (r19, mục 12.4). Bộ lọc khẩn cấp cũng không bắt câu này; nó đã
  nằm trong danh sách 27 chỗ bỏ sót.
- **Tiêu chí táo bón không đơn điệu.** Táo bón từ 10 ngày kèm `defecation_effort=SOME_STRAINING` là ESI 3
  (`esi_3_very_prolonged_constipation`). Giá trị nặng hơn `UNABLE_TO_DEFECATE`, khi không có thêm bí trung tiện, sốt hay đau
  từ 7 điểm, lại không khớp tiêu chí nào và thành RETURN_INCOMPLETE. Một agent hiểu "rặn mà không ra" là UNABLE_TO_DEFECATE
  sẽ chuyển nhân viên y tế ở đúng ca mà corpus xếp ESI 3 (d06).
- **Không ghi được mồ hôi ngoài bệnh do nóng.** `sweating_pattern` là dữ kiện duy nhất về mồ hôi và chỉ được hỏi khi có phơi
  nhiễm nóng. "Vã mồ hôi lạnh" kèm nặng ngực ở r02, một dấu hiệu kinh điển của hội chứng vành cấp, vì thế không có chỗ ghi.
- **Tiêu chí chung che phép thử mâu thuẫn.** `esi_2_worsening_infection_with_hypotension` và `..._with_hypoxemia` chỉ cần
  diễn tiến xấu cùng HATT ≤ 100 hoặc SpO2 ≤ 92, không cần nhiễm trùng. Chúng thắng tiêu chí vùng nguy hiểm khi xếp hạng và làm
  mất phép thử mâu thuẫn của k12 (mục 12.1).
- `ahrq_review.py`: quy tắc "nhãn ESI 1-2 ở trẻ chỉ dựa vào sinh hiệu" trước chỉ xét HR/RR/SpO2. Nay quy tắc tính cả nhiệt độ
  và đối chiếu với ngưỡng sốt cùng ngưỡng dấu hiệu đỏ nhi khoa. Với bộ ca hiện tại, không kết luận nào đổi.

### 12.6 Giới hạn

- Các lượt rà, đọc mù và phân xử đều do mô hình ngôn ngữ thực hiện, và mẫu 60 ca cho khoảng tin cậy rộng. Chuyên gia y tế
  vẫn là bước bắt buộc trước khi dùng nhãn để báo cáo.
- Quét theo từ khoá chỉ bắt được những cách nói đã biết.
- Người bệnh mô phỏng trả lời "Tôi chưa rõ thông tin này." cho mọi câu hỏi ngoài lời kể (mục 10), trong khi người thật sẽ
  trả lời "không" cho phần lớn câu hỏi loại trừ. Transcript r19 cho thấy điều này có thể kéo dài vòng hỏi của agent; nguyên
  nhân gốc ở r19 vẫn là agent hiểu sai lời kể ngay từ đầu.
