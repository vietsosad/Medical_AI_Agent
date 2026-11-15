# BÁO CÁO TIẾN ĐỘ DỰ ÁN KHOA HỌC VÀ CÔNG NGHỆ

## TUẦN 8 — QUYẾT ĐỊNH ESI VÀ AN TOÀN LÂM SÀNG

**Tên đề tài:** MedTriage AI — Hệ thống hỗ trợ tiếp nhận và phân luồng ưu tiên y tế  
**Người thực hiện:** Lê Hoàng Việt  
**Tuần thực hiện:** Tuần 8/15  
**Thời gian:** 09/11/2026 – 15/11/2026  
**Báo cáo liên kết:** Báo cáo Tuần 7 — Xây dựng agent hội thoại giai đoạn A  
**Trạng thái:** Bộ quyết định ESI và các lớp an toàn đã được rà soát theo ba tiêu chí của kế hoạch. Hai tiêu chí đạt và được mã thực thi: không đủ bằng chứng thì không kết luận, và mọi đề xuất ESI có lý do kiểm tra được. Tiêu chí "ca nguy kịch được ưu tiên" mới đạt một phần, vì hai chỗ hở nêu ở mục 5.2 và 6.1. Trong tuần không có commit mã mới. Công việc trong repository chỉ gồm việc gộp PR #13 vào `main` và một lần CI xanh trên toàn bộ bộ test, cùng ngày 09/11. Trong các việc chuyển tiếp từ tuần 7, chỉ việc gộp nhánh là xong, và việc đó đã xảy ra từ tuần 7. Sáu việc chuyển tiếp từ tuần 6 vẫn chưa được thực hiện. Lịch sử `main` hiện có 7 commit bị trùng; mục 2.2 giải thích nguyên nhân.

> **Lưu ý phạm vi:** Đây là báo cáo cá nhân của Lê Hoàng Việt. Hệ thống phục vụ nghiên cứu và nguyên mẫu, không phải thiết bị y tế đã được cấp phép; mọi kết quả phân luồng chỉ có giá trị sau khi nhân viên y tế xác nhận. Bộ quyết định ESI và các lớp an toàn đã có từ trước tuần này: bộ đối chiếu tiêu chí có từ 28/08/2026, và các lớp an toàn được thêm ngày 27/10 và 07/11/2026. Trong khoảng 09/11 – 15/11/2026, repository chỉ có hoạt động vào ngày 09/11 (mục 2). Từ 10/11 đến 15/11 không có commit nào và không tệp mã nào thay đổi. Vì vậy, nội dung tuần 8 là rà soát bộ quyết định ESI theo tiêu chí của kế hoạch 15 tuần. Mọi số liệu được đếm ngày 15/11/2026 bằng đọc mã trên commit `02d5c66` (nhánh `main`, 09/11/2026). Báo cáo không chạy lại bộ test; kết quả test lấy từ lần CI ngày 09/11. Tuần này không có lần đánh giá agent nào được ghi lại, nên báo cáo không có số liệu về độ chính xác hay tỷ lệ xếp mức thấp hơn thực tế (under-triage).

---

## 1. MỤC TIÊU TUẦN 8

Theo mục 6.2 của kế hoạch 15 tuần, tuần 8 đưa logic quan trọng ra khỏi quyền tự quyết của model ngôn ngữ:

- triển khai lớp phản xạ cảnh báo đỏ;
- xây bộ quyết định bằng Python thuần, đối chiếu fact với protocol atom;
- xử lý trường hợp chưa đủ dữ kiện (`RETURN_INCOMPLETE`);
- chặn chẩn đoán và kê đơn ở đầu ra;
- test under-triage và prompt injection.

Đầu ra theo kế hoạch: bộ quyết định, luật an toàn, bộ test an toàn và tài liệu mô hình đe doạ (threat model).

Tiêu chí hoàn thành: **không có đủ bằng chứng thì không kết luận; ca nguy kịch được ưu tiên; mọi đề xuất ESI có lý do có thể kiểm tra.**

Báo cáo tuần 7 (mục 14) cũng hứa ba việc cho tuần này:

1. Đưa bộ lọc khẩn cấp V3, có hàm `screen_self_harm()` chạy riêng, vào repository.
2. Rà soát bộ đối chiếu tiêu chí.
3. Viết test cho under-triage và prompt injection.

Kết quả của ba việc này nằm ở mục 9.

---

## 2. VIỆC DIỄN RA TRONG TUẦN

### 2.1. Dòng thời gian

| Ngày | Việc | Minh chứng |
|---|---|---|
| 09/11 | Viết lại ba message commit mô tả sai so với code của chính commit đó; code không đổi | Nhánh `feat/dataset-800-screen-v3` chuyển từ `372fe70` sang `aca9549` |
| 09/11 | Viết báo cáo tuần 7 | `docs/BAO_CAO_TUAN_07_MEDTRIAGE_LE_HOANG_VIET.md` |
| 09/11, 21:36 | Gộp PR #13 vào `main` | `02d5c66` |
| 09/11, 21:36 – 21:38 | CI chạy trên `aca9549`: job backend "Invariants, lint and full suite" và job frontend "Lint, test, build and typecheck" đều đạt | GitHub check runs |
| 10/11 – 15/11 | Không có commit, không tệp mã nào thay đổi | `git log --all`; thời điểm sửa tệp |

Có 6 PR cập nhật phụ thuộc do dependabot mở (từ 07/10 và 08/11) vẫn đang mở và chưa được xử lý.

### 2.2. Lịch sử `main` bị trùng 7 commit

Nhánh `feat/dataset-800-screen-v3` **đã được gộp vào `main` qua PR #11 lúc 22:22 ngày 07/11**. Ngày 09/11, khi sửa ba message commit sai, tôi chỉ kiểm tra rằng nhánh không có PR đang mở, mà không kiểm tra nó đã được gộp hay chưa. Sau khi force-push, bản đã sửa lại được gộp thêm một lần qua PR #13.

Hệ quả:

- Năm commit dữ liệu (`8516579` … `f565eeb`) không đổi hash nên chỉ xuất hiện một lần. Bảy commit sau đó xuất hiện hai lần: bản cũ (`5e451c8` … `372fe70`, trong đó ba message mô tả sai) và bản viết lại (`b19e8eb` … `aca9549`). `main` vì vậy có 19 commit cho 12 thay đổi.
- Code không bị ảnh hưởng: cây tệp của `02d5c66` giống hệt cây tệp của `aca9549`, và CI trên `aca9549` đạt cả hai job.

Tôi quyết định **không viết lại `main`**. Đó là nhánh mặc định của repository công khai, và thiệt hại chỉ nằm ở lịch sử, không nằm ở code. Bài học đã được ghi lại: trước mọi lần force-push, phải kiểm tra nhánh đã nằm trong `main` chưa (`git branch -r --contains`, hoặc danh sách PR đã gộp), chứ không chỉ kiểm tra PR đang mở.

---

## 3. PHƯƠNG PHÁP

```text
Đọc kế hoạch tuần 8 → 3 tiêu chí + 4 sản phẩm bàn giao
        │
        ▼
Đọc decision.py, agent.py, corpus.py, emergency_screen.py, output_guard.py trên 02d5c66
        │
        ▼
Với từng tiêu chí: mã thực thi ở đâu, có test nào, còn chỗ hở nào
        │
        ▼
Đối chiếu với các việc đã hứa ở tuần 6 và tuần 7
```

Hai thuật ngữ được dùng như ở tuần 7:

- **Thực thi ở mã:** mã Python từ chối hoặc sửa hành vi sai, bất kể model làm gì.
- **Thực thi ở prompt:** chỉ có hướng dẫn cho model; nếu model không làm theo thì không có gì chặn lại.

---

## 4. KIẾN TRÚC LỚP QUYẾT ĐỊNH VÀ AN TOÀN

```text
Tin nhắn người bệnh
        │
        ▼
Bộ lọc cụm từ khẩn cấp (route, trước mọi model)      emergency_screen.py — 10 luật V1 + 9 luật V2
   gắn cờ ca và thêm dòng hướng dẫn 115; KHÔNG đặt mức ESI
        │
        ▼
Giai đoạn A — model ghi fact qua 11 tool đã được mã kiểm tra
        │
        ▼
Giai đoạn B — bộ đối chiếu tiêu chí, Python thuần      decision.py, agent.py
   lấy tiêu chí → đối chiếu với fact → thỏa / thiếu dữ kiện / bị loại trừ
   ├── có tiêu chí ESI 1/2 thỏa  → kết luận ngay bằng thông điệp cố định (RETURN_MATCH)
   ├── còn fact cần hỏi          → hỏi đúng một fact
   ├── có tiêu chí thỏa          → xác nhận với người bệnh rồi kết luận (RETURN_MATCH)
   └── không tiêu chí nào thỏa, không còn gì để hỏi → RETURN_INCOMPLETE
        │
        ▼
Lớp chặn đầu ra                                         output_guard.py
   câu khẳng định mang tính chẩn đoán hoặc kê đơn → thay bằng thông điệp cố định
        │
        ▼
Hàng chờ điều dưỡng: ca có cờ được xếp như ESI 1, nhưng không hiển thị như một mức ESI
```

Model ngôn ngữ không quyết định ESI ở bất kỳ bước nào. Docstring của `decision.py` ghi rõ cam kết này: "the model cannot talk its way into an ESI level that the stated facts don't support" (model không thể dùng lời lẽ để đi tới một mức ESI mà dữ kiện đã khai không hỗ trợ).

---

## 5. BỘ ĐỐI CHIẾU TIÊU CHÍ (`decision.py`)

### 5.1. Tiêu chí và bốn điểm quyết định

Mỗi protocol atom là một tiêu chí có điều kiện trên fact và một mức ESI ứng viên. Các tiêu chí được viết theo bốn điểm quyết định của thuật toán ESI:

| Điểm | Câu hỏi | Mức ESI |
|---|---|---|
| A | Có cần can thiệp cứu sống ngay không? | 1 |
| B | Tình huống có nguy cơ cao không? | 2 |
| C | Sinh hiệu có nằm trong vùng nguy hiểm không? | 2 hoặc 3 |
| D | Cần bao nhiêu nguồn lực? | 3, 4 hoặc 5 |

Thuật toán ESI thật đi tuần tự: chỉ tới bước D khi A, B và C đều âm tính. Vì vậy, khi chọn câu hỏi, một fact giúp quyết định tiêu chí A, B hoặc C được hỏi trước fact chỉ phục vụ bước D (`_DECISION_POINT_PRIORITY`).

### 5.2. Lấy tiêu chí để đối chiếu

| Tham số | Giá trị | Ý nghĩa |
|---|---|---|
| `ATOM_RETRIEVAL_LIMIT` | 8 | Số tiêu chí lấy theo độ gần nghĩa với câu truy vấn mỗi lượt |
| `MIN_ATOM_RELEVANCE_SCORE` | 0,25 | Dưới ngưỡng này coi là nhiễu. Theo đo đạc ghi trong mã, tiêu chí liên quan đạt khoảng 0,42–0,48, tiêu chí không liên quan đạt khoảng 0,08–0,17 |
| `MIN_ATOM_RELEVANCE_SCORE_FOR_PROACTIVE_ASK` | 0,32 | Ngưỡng cao hơn, chỉ dùng khi quyết định có chủ động hỏi một fact hay không |

Chỉ lấy tiêu chí theo độ gần nghĩa thì có một chỗ hở: một tiêu chí ESI 1 có thể thỏa mà không được xét tới, chỉ vì cách diễn đạt của nó không giống lời kể. Mã ghi lại một sự cố thật ngày 16/09/2026: một ca suy hô hấp có SpO2 78% và nhịp thở 42 lần/phút thỏa ba tiêu chí ESI 1 nhưng kết quả là ESI 2, vì cả ba tiêu chí nằm ngoài top 8. Hai nhóm tiêu chí vì vậy **luôn được đối chiếu**, bất kể câu truy vấn là gì:

| Nhóm | Fact liên quan | Thêm vào ngày |
|---|---|---|
| Tiêu chí ESI 1/2 chỉ dựa trên sinh hiệu (`vital_sign_decisive_atom_ids`) | Nhịp tim, nhịp thở, SpO2, nhiệt độ, huyết áp tâm thu, tím tái | 27/10/2026 (`cf675d0`) |
| Tiêu chí quyết định bởi câu trả lời về an toàn bản thân (`self_safety_decisive_atom_ids`) | `self_safety_status`, `perceptual_disturbance_type` | 07/11/2026 |

**Chỗ hở còn lại:** các tiêu chí ESI 1/2 khác, tức là tiêu chí dựa trên triệu chứng chứ không dựa trên sinh hiệu, vẫn phụ thuộc vào việc lọt vào top 8. Chưa có số đo nào cho biết bao nhiêu tiêu chí như vậy bị bỏ sót.

### 5.3. Đối chiếu và kết luận

`atom_status` duyệt danh sách điều kiện của từng tiêu chí, có hỗ trợ các nhánh "hoặc". `evaluate_atoms` chia các tiêu chí thành ba nhóm: đã thỏa, còn thiếu dữ kiện, và bị loại trừ. Từ đó có bốn khả năng:

| Tình huống | Kết quả | Thực thi ở |
|---|---|---|
| Có tiêu chí ESI 1 hoặc 2 đã thỏa | Kết luận ngay trong lượt đó bằng thông điệp cố định có hướng dẫn 115; không hỏi xác nhận, không gọi thêm model (`1ee8ec1`, 27/10) | Mã |
| Còn fact cần hỏi | Hỏi đúng một fact, ưu tiên fact giúp hoàn thành một tiêu chí | Mã |
| Có tiêu chí đã thỏa, không còn gì để hỏi | Hỏi người bệnh còn muốn bổ sung gì không, rồi trả `RETURN_MATCH` với mức khẩn nhất đã thỏa | Mã |
| Không tiêu chí nào thỏa, không còn gì để hỏi | `RETURN_INCOMPLETE`: không đưa ra mức ESI nào | Mã |

Hai giới hạn cứng chặn cuộc phỏng vấn kéo dài vô hạn: tối đa 17 fact được chủ động hỏi trong một phiên (`MAX_ASKED_FACTS_PER_SESSION`), và một câu hỏi bị kẹt quá 2 lượt thì bị bỏ qua (`STALE_QUESTION_LIMIT`). Cả hai đều là giới hạn tài nguyên, không phải phán đoán ESI. Khi chạm giới hạn mà chưa có tiêu chí nào thỏa, kết quả vẫn là `RETURN_INCOMPLETE`, không phải một mức đoán.

### 5.4. Lý do có thể kiểm tra

Mỗi kết luận trả kèm các trường mà điều dưỡng và người rà soát kiểm tra lại được:

| Trường | Nội dung |
|---|---|
| `matched_atoms` | Các tiêu chí đã thỏa ở mức khẩn nhất, mỗi tiêu chí có mã, điểm quyết định, nội dung tiêu chí và `satisfied_requirements` |
| `satisfied_requirements` | Điều kiện nào được fact nào của người bệnh đáp ứng, ví dụ "Mức độ đau (>= 8): 9" |
| `supported_protocol_atoms`, `unresolved_protocol_requirements` | Mọi tiêu chí đã thỏa, và các điều kiện còn thiếu |
| `reason` | Lý do bằng chữ của kết quả, ví dụ "No retrieved protocol atom is fully supported and no patient-reportable linked fact remains" |

Bản SBAR cho điều dưỡng (`sbar.py`) được ghép bằng mã từ state đã tính, không gọi model, và mang danh sách citation tới các tiêu chí đã xét.

---

## 6. CÁC LỚP AN TOÀN

### 6.1. Bộ lọc cụm từ khẩn cấp trước model

- Có 19 luật (10 luật V1 và 9 luật V2), chạy trong route trước mọi lời gọi model.
- Khi một luật khớp: phiên được gắn `attention_required`, tin nhắn có thêm dòng hướng dẫn gọi 115, và ca được lưu ngay cả khi model lỗi.
- Ở hàng chờ, ca có cờ được xếp như ESI 1 (`min(rank, 1)`, `routes_nurse_simple.py:306`), nhưng không bao giờ được hiển thị như một mức ESI.
- Luật **không đặt mức ESI**, vì hợp đồng an toàn của dự án cấm dùng từ khoá để quyết định ESI.

**Chỗ hở:** `screen_patient_message` chỉ trả về một tín hiệu, từ luật khớp đầu tiên. Trong một tin nhắn vừa có cụm từ khẩn cấp vừa có lời nói tự hại, tín hiệu tự hại có thể bị che, và khi đó câu hỏi an toàn bản thân sẽ không được ưu tiên. Bản sửa nằm trong bộ lọc V3, và tuần này V3 vẫn chưa được đưa vào repository.

### 6.2. Lớp chặn đầu ra

`output_guard.py` chạy trên văn bản cuối cùng gửi người bệnh và không gọi model. Câu khẳng định chứa từ chỉ bệnh danh, ví dụ "viêm…", "nhồi máu", "đột quỵ", "tiểu đường", hoặc chứa nội dung kê đơn, bị thay toàn bộ bằng một thông điệp cố định. Lý do thay toàn bộ: nếu chỉ xoá một phần, câu còn lại vẫn có thể đọc như một lời khuyên. Câu hỏi được cho qua, vì "Bạn có bị tiểu đường không?" là cách hỏi tiền sử. Danh sách từ được ghi là cấu hình kỹ thuật, `PENDING_CLINICAL_REVIEW` (chưa được chuyên gia duyệt).

---

## 7. KIỂM THỬ AN TOÀN

### 7.1. Test hiện có cho luồng simple agent

| Nhóm | Test | Số |
|---|---|---:|
| Kết luận ngay với ESI 1/2 | `test_a_decisive_esi_1_match_finalises_without_a_confirmation_round_trip`, `test_a_decisive_esi_2_match_tells_the_patient_to_go_now`, `test_a_non_decisive_match_still_confirms_before_finalising`, `test_resource_count_estimator_is_not_called_for_a_purely_esi_1_2_decisive_match` | 4 |
| Sinh hiệu vùng nguy hiểm (chống under-triage) | `test_reported_danger_zone_vitals_reach_esi_1_without_help_from_retrieval`, `test_vital_sign_atoms_never_decide_what_gets_asked`, `test_normal_vitals_match_no_vital_sign_atom` | 3 |
| An toàn bản thân | 3 test thêm ngày 07/11 (báo cáo tuần 7, mục 5.1) | 3 |
| Chặn đầu ra | `test_a_phrased_question_that_diagnoses_is_replaced_before_the_patient_sees_it`, `test_a_free_reply_that_diagnoses_is_replaced`, cùng 4 hàm có tham số hoá trong `test_simple_agent_output_guard.py` | 6 |
| Dò system prompt | `test_system_prompt_probe_is_refused_without_any_llm_call` | 1 |
| Luồng khẩn cấp qua API | `test_simple_triage_emergency_flow.py` | 8 |
| Bộ lọc cụm từ | `test_simple_agent_emergency_screen.py` (hàm có tham số hoá) | 7 |

### 7.2. Kết quả chạy

| Lần chạy | Phạm vi | Kết quả |
|---|---|---|
| CI ngày 09/11/2026 trên `aca9549`, cùng cây tệp với `main` | Job backend "Invariants, lint and full suite"; job frontend "Lint, test, build and typecheck" | Cả hai đạt |

Báo cáo chỉ ghi kết quả đạt hoặc không đạt của từng job, không ghi số test, vì không đọc được log chi tiết của lần chạy.

### 7.3. Khoảng trống

1. **Prompt injection.** Luồng simple agent chỉ có một test dò system prompt. Bộ 18 test tấn công đối nghịch (`tests/test_agents/test_adversarial_security.py`) chỉ kiểm tra luồng DeepAgent cũ (`src/agents`), không kiểm tra luồng người bệnh đang dùng.
2. **Under-triage chưa có số đo.** Hiện có các test hồi quy cho từng sự cố đã biết, nhưng chưa có tỷ lệ under-triage đo trên bộ dữ liệu. Việc đo cần chạy agent thật, và tuần này không có lần chạy nào.
3. **Chưa có tài liệu threat model cho dự án.** Trong repository, từ "threat" chỉ xuất hiện trong tài liệu hướng dẫn skill và trong bản trích xuất của sổ tay ESI.
4. **16 test xfail** của `test_simple_agent.py` vẫn còn nguyên (báo cáo tuần 7, mục 7.3).

---

## 8. ĐỐI CHIẾU VỚI TIÊU CHÍ TUẦN 8

### 8.1. Sản phẩm bàn giao

| Sản phẩm | Kết quả | Minh chứng |
|---|---|---|
| Bộ quyết định | Đạt | `decision.py`, phần giai đoạn B trong `agent.py` |
| Luật an toàn | Đạt | `emergency_screen.py` (19 luật), `output_guard.py`, hai nhóm tiêu chí luôn được đối chiếu |
| Bộ test an toàn | Đạt một phần | 32 test ở mục 7.1; còn thiếu prompt injection cho luồng simple agent và số đo under-triage |
| Tài liệu threat model | Chưa đạt | Chưa có |

### 8.2. Tiêu chí hoàn thành

| Tiêu chí | Kết quả | Thực thi ở | Ghi chú |
|---|---|---|---|
| Không có đủ bằng chứng thì không kết luận | Đạt | Mã | Không tiêu chí nào thỏa thì trả `RETURN_INCOMPLETE`; chạm giới hạn câu hỏi cũng không đưa ra mức đoán |
| Ca nguy kịch được ưu tiên | Đạt một phần | Mã | Sinh hiệu vùng nguy hiểm và câu trả lời về an toàn bản thân luôn được đối chiếu; ESI 1/2 được kết luận ngay; ca có cờ đứng đầu hàng chờ. Hai chỗ hở: tiêu chí ESI 1/2 dựa trên triệu chứng vẫn phụ thuộc top 8 (mục 5.2), và tín hiệu tự hại có thể bị che (mục 6.1) |
| Mọi đề xuất ESI có lý do có thể kiểm tra | Đạt | Mã | `matched_atoms` kèm `satisfied_requirements`, `reason`, SBAR do mã ghép |

Kết quả: 2/4 sản phẩm đạt, 1 đạt một phần, 1 chưa đạt. 2/3 tiêu chí đạt, 1 đạt một phần.

---

## 9. ĐỐI CHIẾU VỚI KẾ HOẠCH TUẦN 7

| # | Việc (mục 14 tuần 7) | Kết quả tuần 8 |
|---:|---|---|
| — | Đưa bộ lọc V3 và `screen_self_harm()` vào repository | Chưa làm; V3 vẫn chỉ nằm ngoài repository |
| — | Rà soát bộ đối chiếu tiêu chí | Đã làm; xem mục 5 của báo cáo này |
| — | Test under-triage và prompt injection | Chưa viết test mới (mục 7.3) |
| 1 | Viết nốt 24 kịch bản đợt 4, đăng ký, khoá | Chưa làm; vẫn 186/210, chưa đăng ký |
| 2 | Chạy agent thật khi có lại credit OpenAI | Chưa làm; không có lần chạy nào được ghi lại |
| 3 | Viết lại 16 test xfail | Chưa làm |
| 4 | Kiểm tra bằng mã rằng mỗi tin nhắn chỉ có một câu hỏi | Chưa làm |
| 5 | Rà soát và gộp nhánh `feat/dataset-800-screen-v3` | Đã gộp qua PR #11 ngày 07/11 (tuần 7) và PR #13 ngày 09/11; xem mục 2.2 |

Kết quả: 1 việc rà soát đã làm, 1 việc gộp nhánh đã xong từ tuần 7, 6 việc chưa làm. Cả 6 việc chưa làm chuyển sang tuần 9 (mục 14).

---

## 10. ĐỐI CHIẾU VỚI KẾ HOẠCH TUẦN 6

| # | Việc chuyển tiếp (mục 15 tuần 6) | Cuối tuần 8 (`02d5c66`) |
|---:|---|---|
| 1 | Test API cho `/profiles` | Chưa làm |
| 2 | Endpoint readiness có kiểm tra DB | Chưa làm |
| 3 | Trường tiến trình trong phản hồi simple agent | Chưa làm |
| 4 | `Literal` cho `action`, `decision_type`; thống nhất tên trường phiên bản | Chưa làm |
| 5 | ADR về namespace lâm sàng | Chưa làm |
| 6 | Quyết định về lối vào khách `/auth/guest` | Chưa quyết |

Kết quả: 0/6, không đổi so với tuần 7.

---

## 11. MINH CHỨNG TUẦN 8

| Hạng mục | Minh chứng |
|---|---|
| Trạng thái được rà soát | `vietsosad/Medical_AI_Agent`, nhánh `main`, commit `02d5c66` (09/11/2026) |
| Bộ đối chiếu tiêu chí | `src/simple_agent/decision.py`; giai đoạn B và kết luận trong `src/simple_agent/agent.py` |
| Hai nhóm tiêu chí luôn được đối chiếu | `src/simple_agent/corpus.py` (`vital_sign_decisive_atom_ids`, `self_safety_decisive_atom_ids`) |
| Lớp an toàn | `src/simple_agent/emergency_screen.py`, `src/simple_agent/output_guard.py`, `src/api/routes_nurse_simple.py:306` |
| Test an toàn | `tests/test_simple_agent.py`, `tests/test_simple_agent_output_guard.py`, `tests/test_simple_agent_emergency_screen.py`, `tests/test_api/test_simple_triage_emergency_flow.py` |
| CI | Hai check run đạt trên `aca9549`, ngày 09/11/2026 |
| Gộp nhánh | PR #11 (`57fb80d`, 07/11), PR #13 (`02d5c66`, 09/11) |

---

## 12. KẾT QUẢ ĐẠT ĐƯỢC TRONG TUẦN 8

Trong tuần 8, tôi đã hoàn thành các nội dung sau:

- Sửa ba message commit mô tả sai so với code và gộp bản đã sửa vào `main`; CI đạt cả hai job.
- Rà soát bộ quyết định ESI theo ba tiêu chí của kế hoạch, ghi rõ từng tiêu chí được mã thực thi ở đâu.
- Xác định hai chỗ hở của tiêu chí "ca nguy kịch được ưu tiên": tiêu chí ESI 1/2 dựa trên triệu chứng vẫn phụ thuộc top 8, và tín hiệu tự hại có thể bị che.
- Lập bảng các test an toàn hiện có và ba khoảng trống: prompt injection cho luồng simple agent, số đo under-triage, và tài liệu threat model.
- Phát hiện và ghi nhận việc lịch sử `main` bị trùng 7 commit, kèm nguyên nhân và quyết định không viết lại `main`.
- Đối chiếu nguyên trạng các việc đã hứa ở tuần 6 và tuần 7.

---

## 13. KHÓ KHĂN VÀ CÁCH XỬ LÝ

| Khó khăn | Cách xử lý |
|---|---|
| Force-push một nhánh đã được gộp vào `main` khiến lịch sử `main` bị trùng 7 commit | Không viết lại `main` vì code không bị ảnh hưởng; ghi rõ trong báo cáo; từ nay kiểm tra nhánh đã nằm trong `main` chưa trước mọi lần force-push |
| Không chạy được agent thật từ tuần 7 vì tài khoản OpenAI hết credit | Không thay bằng số liệu cũ; báo cáo ghi rõ là không có số đo |
| Từ 10/11 đến 15/11 không có commit nào, nên các việc chuyển tiếp không tiến triển | Ghi nguyên trạng từng việc ở mục 9 và 10, không gộp vào nhóm "đang làm" |

---

## 14. KẾ HOẠCH TUẦN 9

Theo kế hoạch 15 tuần, tuần 9 làm **RAG, citation và giải thích**: kết nối quyết định với kho tri thức có nguồn.

- Rà soát việc lấy tiêu chí bằng embedding, và kiểm tra thẩm quyền của nguồn.
- Kiểm tra mỗi đề xuất không khẩn cấp có citation hợp lệ tới tiêu chí đã thỏa.
- Đo độ chính xác và độ phủ của bước lấy tiêu chí (context precision, recall) trên train và validation của `generated_mock_v2`, bắt đầu bằng chỗ hở "top 8" ở mục 5.2.
- Xác nhận lỗi ở bước lấy tiêu chí hoặc kiểm tra citation dẫn tới trạng thái an toàn (`RETURN_INCOMPLETE`), không suy đoán.

Tiêu chí hoàn thành theo kế hoạch: **mỗi đề xuất không khẩn cấp có citation hợp lệ; lỗi retrieval hoặc validation dẫn đến trạng thái an toàn, không suy đoán.**

Các việc chuyển tiếp từ tuần 8:

1. Đưa bộ lọc V3 và `screen_self_harm()` vào repository.
2. Viết test prompt injection cho luồng simple agent.
3. Viết tài liệu threat model cho luồng simple agent.

Các việc chuyển tiếp từ tuần 7: viết nốt 24 kịch bản đợt 4 và khoá đợt; chạy agent thật khi có lại credit (đo trên train và validation trước, tập test chỉ đo một lần); viết lại 16 test xfail; kiểm tra bằng mã rằng mỗi tin nhắn chỉ có một câu hỏi.

Các việc chuyển tiếp từ tuần 6: giữ nguyên sáu việc ở mục 10.

---

## 15. KẾT LUẬN TUẦN 8

Tuần 8 cho thấy cam kết cốt lõi của dự án được mã thực thi ở đúng chỗ quan trọng nhất: model không tự quyết định ESI. Không có tiêu chí nào thỏa thì không có kết luận, và mỗi kết luận đều chỉ ra được điều kiện nào được dữ kiện nào đáp ứng.

Tuần này cũng cho thấy "ưu tiên ca nguy kịch" khó hơn "không đoán". Hệ thống đã bịt được những chỗ hở từng gây sự cố thật, cụ thể là sinh hiệu vùng nguy hiểm và câu trả lời về an toàn bản thân. Nhưng các tiêu chí ESI 1/2 khác vẫn phụ thuộc vào việc lọt vào top 8, và tín hiệu tự hại vẫn có thể bị che. Hai chỗ hở này chỉ đo được khi chạy agent thật trên bộ dữ liệu.

Về tiến độ, tuần 8 gần như không có thay đổi mã: sau ngày 09/11, repository không có commit nào. Báo cáo ghi điều này nguyên trạng, cùng sự cố trùng lịch sử `main`, thay vì trình bày việc rà soát như một sản phẩm mới.

Nguyên tắc được chốt trong tuần này là: **mô hình ngôn ngữ không bao giờ được quyết định mức ESI, và mọi chỗ hở trong việc ưu tiên ca nguy kịch phải được nêu ra cùng với ngày bịt được nó.**

---

## NGƯỜI LẬP BÁO CÁO

**Lê Hoàng Việt**  
Ký và ghi rõ họ tên: ____________________  
Ngày: ____ / ____ / 2026
