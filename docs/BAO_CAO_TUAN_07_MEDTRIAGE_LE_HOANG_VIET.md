# BÁO CÁO TIẾN ĐỘ DỰ ÁN KHOA HỌC VÀ CÔNG NGHỆ

## TUẦN 7 — XÂY DỰNG AGENT HỘI THOẠI GIAI ĐOẠN A

**Tên đề tài:** MedTriage AI — Hệ thống hỗ trợ tiếp nhận và phân luồng ưu tiên y tế  
**Người thực hiện:** Lê Hoàng Việt  
**Tuần thực hiện:** Tuần 7/15  
**Thời gian:** 02/11/2026 – 08/11/2026  
**Báo cáo liên kết:** Báo cáo Tuần 6 — Dựng backend nền tảng và hợp đồng dữ liệu  
**Trạng thái:** Đã xây xong bộ dữ liệu đánh giá hội thoại `generated_mock_v2` gồm 590 ca trong ba đợt, đã khoá cách chia tập và qua 9/9 kiểm tra. Đã tìm ra và sửa hai lỗi hiểu sai lời người bệnh của giai đoạn A: lời nói gián tiếp về ý định tự hại, và sinh hiệu nói bằng lời. Bộ lọc cụm từ khẩn cấp có thêm 9 luật. Đã sửa lỗi làm mất ca có cờ khẩn khi model gặp sự cố ngay tin nhắn đầu. Hai việc chưa xong: đánh giá agent trên bộ dữ liệu mới bị chặn vì tài khoản OpenAI hết credit từ ngày 06/11, và đợt 4 mới viết được 186/210 ca. Tiêu chí "không tự sinh ID" đạt; hai tiêu chí còn lại đạt một phần. Sáu việc chuyển tiếp từ tuần 6 chưa được thực hiện.

> **Lưu ý phạm vi:** Đây là báo cáo cá nhân của Lê Hoàng Việt. Agent phục vụ nghiên cứu và nguyên mẫu; nó không chẩn đoán, không kê đơn, và mọi kết quả phân luồng chỉ có giá trị sau khi nhân viên y tế xác nhận. Khung agent ba pha đã có từ trước tuần này: runtime được commit ngày 28/08/2026 (`61364f3`) và được gia cố ngày 27/10/2026. Trạng thái đầu tuần là commit `26ed656` (30/10/2026) trên nhánh `main` của repository `vietsosad/Medical_AI_Agent`. Trạng thái cuối tuần là nhánh `feat/dataset-800-screen-v3`, được gộp vào `main` qua PR #11 lúc 22:22 ngày 07/11/2026 (`57fb80d`). Ngày 09/11, ba message commit mô tả sai được viết lại, và bản đã sửa (`aca9549`) được gộp lần nữa qua PR #13 (`02d5c66`). Code của hai bản giống hệt nhau. Báo cáo trích hash của bản đã sửa. Bộ dữ liệu trong báo cáo là dữ liệu mô phỏng: nhãn được tính bằng máy từ kho tiêu chí, không phải hồ sơ bệnh nhân thật, và chưa được chuyên gia lâm sàng duyệt. Tuần này không đo được độ chính xác của agent (mục 8.1). Các con số của bộ lọc khẩn cấp chỉ được đo trên tập train và validation; tập test được giữ nguyên, chưa dùng để đo.

---

## 1. MỤC TIÊU TUẦN 7

Theo mục 6.2 của kế hoạch 15 tuần, tuần 7 xây dựng agent hội thoại giai đoạn A: hiểu lời kể tự do, trích xuất concept và fact, phân biệt `SELF` với `OTHER_PERSON`, tránh hỏi lặp, giới hạn số lần gọi tool và xử lý câu trả lời mơ hồ.

Tiêu chí hoàn thành: **hệ thống hiểu được các cách diễn đạt tương đương, hỏi tối đa một ý chính mỗi lượt và không tự sinh ID ngoài dữ liệu hợp lệ.**

Khung agent đã có sẵn (mục 2). Câu hỏi của tuần này vì vậy không còn là "dựng agent" mà là "làm sao biết agent hiểu đúng". Từ đó, tuần 7 có bốn mục tiêu cụ thể:

1. Xây bộ dữ liệu đánh giá hội thoại đủ lớn và đủ đa dạng để đo được tiêu chí "hiểu cách diễn đạt tương đương".
2. Khoá cách chia train/validation/test trước khi tinh chỉnh, để mọi cải tiến chỉ dựa trên train và validation.
3. Tìm các lỗi hiểu sai của giai đoạn A trên bộ dữ liệu đó và sửa bằng mã hoặc prompt.
4. Đối chiếu lại ba tiêu chí hoàn thành ở cuối tuần.

---

## 2. ĐIỂM XUẤT PHÁT ĐẦU TUẦN

Ở commit `26ed656` (30/10/2026), agent hội thoại có các thành phần sau:

| Thành phần | Trạng thái đầu tuần | Vị trí |
|---|---|---|
| Kiến trúc ba pha | A: hiểu tin nhắn (model gọi tool) → B: quyết định bằng Python thuần → C: diễn đạt câu hỏi | `src/simple_agent/` |
| Hợp đồng tool | 11 tool; mã từ chối ID không có trong kho, ID chưa được tìm thấy, giá trị sai schema | `tools.py`, `TOOL_SCHEMAS` trong `prompts.py` |
| Giới hạn | Tối đa 8 lần gọi tool mỗi lượt; kiểm tra trước khi hỏi tối đa 6 fact; thoát sau 2 lượt bị kẹt ở cùng một câu | `understanding.py`, `agent.py`, `decision.py` |
| Mô hình trạng thái | Bốn kênh cho mỗi dữ kiện: chưa hỏi, không biết, đã biết, mới có mô tả; cất và khôi phục state khi đổi người được hỏi | `session.py`, `persistence.py` |
| Lớp an toàn trước model | Bộ lọc cụm từ khẩn cấp chạy trong route trước mọi lời gọi model (từ 27/10, `299b19b`) | `emergency_screen.py` |
| Lớp an toàn đầu ra | Chặn câu khẳng định mang tính chẩn đoán hoặc kê đơn (từ 27/10, `d842c2f`) | `output_guard.py` |
| Test | Chạy trên kho dựng từ gói migration đã commit, không còn bị skip (từ 27/10, `a648b2b`); 16 test vẫn xfail vì dùng ID giả của kho mock cũ | `tests/test_simple_agent*.py` |

Ba khoảng trống còn mở khi bắt đầu tuần:

1. Chưa có bộ dữ liệu nào có lời mở đầu tự nhiên, đa dạng cách nói, để đo tiêu chí "hiểu cách diễn đạt tương đương". Theo lần rà soát ngày 27/10/2026, nhãn của bộ 30 và 300 ca vàng hiện có được lấy thẳng từ mức ESI của chính tiêu chí đã sinh ra từng ca.
2. "Một ý mỗi lượt" chỉ được mã thực thi ở bước chọn dữ kiện; câu chữ chỉ bị ràng buộc bằng prompt.
3. Sáu việc chuyển tiếp từ tuần 6 (mục 10).

---

## 3. PHƯƠNG PHÁP

```text
Viết kịch bản bằng tay (lời mở đầu + dữ kiện có cấu trúc)
        │
        ▼
Dựng bản ghi: phát lại dữ kiện qua bộ đối chiếu tiêu chí thật → nhãn ESI do máy tính, không viết tay
        │
        ▼
9 kiểm tra toàn bộ dữ liệu → chia train/validation/test theo cụm → KHOÁ đợt
        │
        ▼
Chạy trên train/validation → phân loại lỗi → sửa → chạy lại trên train/validation
        │
        ▼
Tập test: chỉ đo một lần, sau khi mọi thay đổi đã chốt
```

Bước khoá đợt là bắt buộc. `assign_splits` tính lại các cụm chưa khoá mỗi khi thêm bản ghi, nên một bản ghi đang ở train có thể bị chuyển sang test khi thêm đợt mới. Nếu tinh chỉnh trên một đợt chưa khoá, kết quả trên test sẽ bị nhiễm.

Hai thuật ngữ được dùng xuyên suốt báo cáo:

- **Thực thi ở mã:** mã Python từ chối hoặc sửa hành vi sai, bất kể model làm gì.
- **Thực thi ở prompt:** chỉ có hướng dẫn cho model; nếu model không làm theo thì không có gì chặn lại.

---

## 4. BỘ DỮ LIỆU ĐÁNH GIÁ HỘI THOẠI `generated_mock_v2`

### 4.1. Cách dựng

Mỗi kịch bản là một `Spec` viết tay, gồm hồ sơ người bệnh, lời mở đầu tự nhiên bằng tiếng Việt, và các dữ kiện có cấu trúc mà người bệnh sẽ khai nếu được hỏi. Bộ dựng `build_dataset.py` làm ba việc:

- phát lại dữ kiện qua bộ đối chiếu tiêu chí thật của agent để tính nhãn ESI, nên không nhãn nào được viết tay;
- sinh câu trả lời cho từng dữ kiện bằng `phrasing.py`;
- ghi vân tay của kho tri thức để phát hiện khi kho thay đổi.

Ba công cụ kiểm tra đi kèm:

| Công cụ | Dùng khi | Kiểm tra |
|---|---|---|
| `check_specs.py` | Đang viết một tệp kịch bản | Nhãn tính ra có đúng mức người viết dự định không; dữ kiện có hợp lệ không |
| `validate_dataset.py` | Sau khi dựng | 9 bất biến của toàn bộ dữ liệu (mục 4.3) |
| `ahrq_review.py` | Sau khi dựng | Đối chiếu độc lập với hướng dẫn AHRQ ESI v5 |

### 4.2. Quy mô

| Đợt | Số ca | Ngày khoá | Mục đích |
|---|---:|---|---|
| 1 | 200 | 04/11/2026 | Sáu nhóm tình huống: thường gặp, nhiều triệu chứng, dấu hiệu nguy hiểm, thiếu dữ kiện, lời kể mâu thuẫn, hội thoại dài |
| 2 | 200 | 05/11/2026 | Cùng sáu nhóm, mở rộng sang 147 tiêu chí chính chưa có ở đợt 1 |
| 3 | 190 | 07/11/2026 | Mỗi tiêu chí ESI 2 mà người bệnh có thể khai được, chưa ca nào chạm tới, có một ca riêng |
| **Tổng** | **590** | | |

Phân bố của 590 ca:

- **Chia tập:** train 339, validation 73, test 74. 104 ca khác được tách riêng để chờ chuyên gia duyệt.
- **Người kể:** 306 ca người bệnh tự kể (`SELF`) và 284 ca người nhà kể thay (`OTHER_PERSON`), nên tiêu chí phân biệt người được hỏi có đủ ca để đo.
- **Câu trả lời "không biết":** 164 ca có ít nhất một dữ kiện như vậy; tổng cộng 281 dữ kiện "không biết", mỗi dữ kiện có câu trả lời nói rõ là không biết.
- **Kết quả kỳ vọng:** 506 ca kết thúc bằng một mức ESI, 84 ca kết thúc vì chưa đủ dữ kiện (`RETURN_INCOMPLETE`).
- **Độ tuổi:** 466 ca người lớn, trong đó 139 ca từ 65 tuổi trở lên; 124 ca trẻ em và vị thành niên, từ sơ sinh tới tuổi thiếu niên.

### 4.3. Chín kiểm tra

Lần chạy cuối của `validate_dataset.py` cho kết quả **PASS** ở cả 9 kiểm tra:

| # | Kiểm tra | Kết quả |
|---:|---|---|
| 1 | Cấu trúc khớp schema của bộ ca vàng hiện có | 590 bản ghi trong 4 tệp |
| 2 | Lời thoại khớp dữ kiện kỳ vọng | 6.259 dữ kiện có giá trị và 281 dữ kiện "không biết", mỗi dữ kiện có câu trả lời riêng |
| 3 | Dữ kiện hợp lệ theo kho PostgreSQL | Đúng enum và khoảng giá trị, có dữ kiện điều kiện đi kèm, đúng giới tính |
| 4 | Nhãn được tính lại độc lập | 590 nhãn được tính lại từ 1.711 tiêu chí |
| 5 | Vân tay kho và checksum manifest | Khớp với PostgreSQL hiện tại |
| 6 | Đối chiếu với AHRQ ESI v5 | 505 nhất quán, 29 trùng khớp, 50 không kiểm được, 5 bị xếp thấp hơn, 1 bị xếp cao hơn |
| 7 | Trùng lặp | Không có lời mở đầu trùng hệt; không cặp nào giống nhau từ 0,5 trở lên (Jaccard 4-gram); độ giống cao nhất với bộ ca vàng cũ là 0,34 |
| 8 | Chia tập không rò rỉ | Tỷ lệ 69,8/15,0/15,2; không gia đình kịch bản, cụm hay bộ dữ kiện nào nằm ở hai tập; 70/74 ca test có ít nhất một nhãn tình huống biên |
| 9 | Các đợt đã khoá giữ nguyên | 590 bản ghi khớp từng byte với `split_lock.json`; năm lần sửa có chủ đích đều được ghi lý do |

### 4.4. Đợt 4: bản nháp

Đợt 4 được viết từ bốn lớp lỗi đã quan sát được (mục 5), đồng thời để cân lại tỷ lệ nhãn. Hiện 408/590 ca (69%) là ESI 2, trong khi ESI 1, ESI 3 và ca thiếu dữ kiện còn ít. Đến cuối tuần có 186/210 ca trong 8 tệp. Hai tệp chưa đủ, `b3_multi_c` (16/30) và `b3_complex_c` (20/30), vì phiên viết dừng lại khi chạm giới hạn sử dụng. Các tệp đã được commit (`59cad50`) nhưng **cố ý chưa đăng ký** vào `ALL_SPECS`: đăng ký một đợt dở sẽ làm `assign_splits` xáo lại các cụm chưa khoá.

### 4.5. Giới hạn của bộ dữ liệu

- Đây là dữ liệu mô phỏng. Nhãn do máy tính từ kho tiêu chí, nên bộ dữ liệu đo được agent có đi tới đúng tiêu chí hay không, chứ không đo được tiêu chí đó có đúng về lâm sàng hay không.
- 104 ca chờ chuyên gia duyệt. Đối chiếu AHRQ đánh giá 5 ca bị xếp thấp hơn mức nên có và 1 ca bị xếp cao hơn; cả 6 ca đều nằm trong hàng chờ duyệt, không nằm trong train, validation hay test.
- Tỷ lệ nhãn lệch về ESI 2; đợt 4 được viết để giảm độ lệch này.

---

## 5. CÁC LỖI HỘI THOẠI TÌM RA VÀ CÁCH SỬA

Lỗi được chia thành bốn lớp:

| Lớp | Mô tả | Ví dụ |
|---|---|---|
| F1 | Ý định tự hại nói gián tiếp | "giá mà ngủ một giấc rồi không dậy nữa thì mọi người đỡ khổ" |
| F2 | Sinh hiệu nói bằng lời, hoặc được khai muộn trong hội thoại | "huyết áp 8 rưỡi trên 5", "39 độ 6" |
| F3 | "Không biết" bị hiểu thành "không" | "chưa đo nhiệt độ" bị ghi thành không sốt |
| F4 | Câu nghe đáng sợ nhưng không khẩn cấp | "đau muốn chết", "mẹ giết em mất", môi tím vì mực bút |

### 5.1. F1 — Lời nói gián tiếp về ý định tự hại

**Lỗi.** Ngày 06/11/2026, khi chạy agent thật trên ca r19, cả hai lần chạy đều đọc câu "nghĩ giá mà ngủ một giấc rồi không dậy nữa thì mọi người đỡ khổ" thành buồn ngủ hoặc mất ngủ. Câu hỏi về an toàn bản thân không bao giờ được hỏi, và cuộc hội thoại dùng hết số lượt cho các câu hỏi về sinh hiệu. Nguyên nhân: câu không có từ nào nói thẳng về tự hại, trong khi kho tri thức có concept khớp với các từ bề mặt "ngủ" và "không dậy".

**Cách sửa** (commit `b19e8eb`, 07/11/2026):

1. Bộ lọc khẩn cấp có thêm luật `SA_SCREEN_SELF_HARM_V2` cho các cách nói gián tiếp: không muốn tỉnh dậy, "không phải sống nữa", "chán sống", tự làm đau "cho xong". Cách nói cường điệu như "đau muốn chết" được cố ý để ngoài luật.
2. Khi luật này khớp với bất kỳ lượt nào của người bệnh, giai đoạn B đưa câu hỏi về an toàn bản thân (`fact_target:self_safety_status`) lên làm câu hỏi kế tiếp, xếp trước mọi câu khác. Câu hỏi này vẫn đi qua bước kiểm tra trước khi hỏi, nên nếu người bệnh đã trả lời rồi thì không bị hỏi lại.
3. Kết quả của luật được đưa vào state của giai đoạn A dưới tên `safety_screen`. Prompt yêu cầu model đọc đúng lời người bệnh: ghi `self_safety_status` khi ý nghĩ đang hiện hữu, và không ghi gì khi lời nói phủ nhận, nói về quá khứ, hoặc kể về người khác.
4. Các tiêu chí ESI quyết định bởi câu trả lời về an toàn bản thân luôn được đối chiếu, kể cả khi bước tìm tiêu chí không trả về tiêu chí nào.

Luật **không bao giờ tự đặt mức ESI**, vì hợp đồng an toàn của dự án cấm dùng từ khoá để quyết định ESI. Luật chỉ quyết định câu hỏi nào được hỏi trước; mức ESI vẫn đến từ câu trả lời của người bệnh. Có 3 test mới cho phần này: không có từ ngữ tự hại thì không hỏi; có từ ngữ tự hại thì câu hỏi an toàn được hỏi kế tiếp và tín hiệu tới được giai đoạn A; câu trả lời về an toàn quyết định ESI 2 ngay cả khi bước tìm tiêu chí không trả về gì.

**Giới hạn còn lại.** Hàm `screen_patient_message` chỉ trả về **một** tín hiệu: luật nào khớp trước thì được trả về. Nếu cùng một câu vừa có cụm từ khẩn cấp khác vừa có lời nói tự hại, tín hiệu tự hại có thể bị che. Bản sửa, một hàm `screen_self_harm()` chạy riêng, nằm trong bộ lọc V3 ứng viên (mục 8.2) và chưa được đưa vào repository.

### 5.2. F2 — Sinh hiệu nói bằng lời

**Lỗi.** Người bệnh thường nói một con số thay vì gõ chữ số. Prompt cũ coi phần lớn các cách nói này là "chưa đủ cụ thể", ghi chúng thành mô tả, rồi hỏi lại con số.

**Cách sửa** (commit `9934381`, 07/11/2026). Prompt giai đoạn A được thêm quy tắc chuyển đổi trước khi gọi `record_fact`:

| Cách nói | Giá trị |
|---|---|
| "9 trên 6", "8 rưỡi trên 5", "huyết áp 17/10" | 90/60, 85/50, 170/100 (số tâm thu dưới 30 là cách viết tắt theo cm thuỷ ngân, nhân cả hai số với 10) |
| "trăm hai", "một trăm linh hai", "trăm mốt", "trăm rưỡi" | 120, 102, 110, 150 |
| "39 độ 6", "39 phẩy 6", "38 rưỡi" | 39,6; 39,6; 38,5 |

Quy tắc cũng giữ lại những trường hợp thực sự không phải con số, như "trên 38", "9 mấy", "hơn trăm": các cách nói này vẫn được ghi thành mô tả. Nhiệt độ trên 45 được coi là có thể đo bằng độ F, nên agent hỏi lại đơn vị thay vì ghi thành độ C. Khi người bệnh đo lại hoặc đọc nhầm dòng trên máy, giá trị mới được ghi đè lên giá trị cũ.

**Giới hạn.** Thay đổi này chỉ nằm ở prompt và chưa được đo trên agent thật (mục 8.1).

### 5.3. Bộ lọc cụm từ khẩn cấp: 9 luật V2

Từ các lời mở đầu của train, validation và hàng chờ duyệt, ngày 06/11 tôi bổ sung 9 luật V2 cho những cách nói mà 10 luật V1 bỏ sót:

| Luật | Ví dụ cách nói được bắt |
|---|---|
| Tự hại | "chán sống", "không thiết sống nữa" |
| Bất tỉnh | "nằm bất động, gọi không trả lời" |
| Xuất huyết tiêu hoá | "nôn ra bã cà phê", "phân đen như hắc ín", "đỏ cả bồn cầu" |
| Chảy máu nhiều | "máu ồ ạt", "khăn ướt sũng", "chảy máu không cầm" |
| Đau ngực | "thắt ngực lan lên hàm", "nặng ngực vã mồ hôi" |
| Khó thở nặng | "nói vài chữ phải ngừng", "ngồi yên vẫn hụt hơi" |
| Đột quỵ | "miệng méo một bên", "tự nhiên nói ngọng" |
| Thiếu máu chi cấp | "chân lạnh ngắt tê bì" |
| Tím tái | "môi tím" (không bắt "tìm hiểu", "tìm thấy" khi bỏ dấu) |

Với những luật có cửa sổ khớp rộng, cờ `span_negation` loại bỏ kết quả nếu trong đoạn khớp có từ phủ định, ví dụ "đau ngực nhưng không lan ra tay" hay "môi không tím". Test mới gồm ba nhóm: bắt được các cách nói V2, bắt được cách nói tự hại gián tiếp, và không báo động với các câu gần giống hoặc câu phủ định.

### 5.4. F3 và F4 — Không biết và câu giống khẩn cấp

Hai lớp lỗi này không cần sửa mã trong tuần, vì cơ chế đã có từ trước: `mark_fact_unknown` cho câu trả lời "không biết", và cơ chế phủ định cho câu nói cường điệu. Chúng được đưa vào bộ dữ liệu để đo:

- Lớp F3 có trong 164 ca có dữ kiện "không biết".
- Lớp F4 có các ca đối chứng âm, ví dụ "ngủ như chết", "thà chết còn hơn" khi từ chối nội soi, môi tím vì mực bút máy. Với các ca này, kỳ vọng là agent không báo động.

### 5.5. Ca có cờ khẩn bị mất khi model gặp sự cố ngay tin nhắn đầu

**Lỗi.** Sự cố hết credit OpenAI trong tuần (mục 8.1) làm lộ ra một lỗi. Bộ lọc khẩn cấp chạy trước model, nên một tin nhắn đầu như "con tôi ngất xỉu" đã được gắn cờ trước khi model bị lỗi. Nhưng lúc đó `/start` chưa lưu gì, nên khi trả lỗi 502, ca biến mất hoàn toàn: người bệnh thấy thông báo lỗi, còn điều dưỡng không bao giờ thấy ca.

**Cách sửa** (commit `10afb84`, 07/11/2026). Khi bộ lọc đã gắn cờ tin nhắn đầu mà model lỗi, route lưu phiên, phiên chat có `attention_required` và chính tin nhắn của người bệnh, rồi báo lên hàng chờ trước khi trả lỗi. Thông báo lỗi bắt đầu bằng hướng dẫn gọi 115. Nếu người bệnh gửi lại đúng tin nhắn đó trong vòng 30 phút, hàng chờ không có thêm bản sao. Tin nhắn không bị gắn cờ thì vẫn không lưu gì. Có 2 test API mới cho hai trường hợp này.

---

## 6. KIẾN TRÚC SAU THAY ĐỔI

```text
Tin nhắn người bệnh
        │
        ▼
Bộ lọc cụm từ khẩn cấp (route, trước mọi model)          10 luật V1 + 9 luật V2
   ├── khớp luật khẩn → gắn cờ ca, thêm dòng hướng dẫn 115; lưu ngay cả khi model lỗi (mục 5.5)
   └── khớp luật tự hại → tín hiệu safety_screen
        │
        ▼
Giai đoạn A — hiểu tin nhắn (model gọi tool, tối đa 8 lần mỗi lượt)
   đọc safety_screen; đổi sinh hiệu nói bằng lời ra con số (mục 5.2)
        │  mọi thay đổi state đi qua 11 tool và được mã kiểm tra
        ▼
Giai đoạn B — quyết định (Python thuần)
   có tín hiệu tự hại → câu hỏi an toàn được hỏi kế tiếp (mục 5.1)
   ngược lại → chọn đúng MỘT fact target để hỏi, hoặc kết thúc
        │
        ▼
Giai đoạn C — diễn đạt → lớp chặn chẩn đoán/kê đơn ở đầu ra → người bệnh
```

Model ngôn ngữ không quyết định ESI ở bất kỳ bước nào.

---

## 7. KIỂM THỬ TỰ ĐỘNG

### 7.1. Số test

| Tệp | Đầu tuần (`26ed656`) | Cuối tuần (`aca9549`) | Ghi chú |
|---|---:|---:|---|
| `tests/test_simple_agent.py` | 64 | 67 | +3 test cho F1; 16 test xfail không đổi |
| `tests/test_simple_agent_deepagent_understanding.py` | 5 | 5 | Hợp đồng tool, giới hạn lượt gọi |
| `tests/test_simple_agent_emergency_screen.py` | 4 | 7 | Hàm test có tham số hoá; 81 dòng ví dụ ở cuối tuần |
| `tests/test_api/test_simple_triage_emergency_flow.py` | 4 | 8 | +2 test cho mục 5.5; +2 test cho dashboard điều dưỡng |
| `tests/test_simple_agent_output_guard.py` | 4 | 4 | |

Không tệp nào còn gọi `pytest.skip` vì thiếu kho dữ liệu. Các test đều chạy trên kho dựng từ gói migration đã commit.

### 7.2. Kết quả chạy

| Lần chạy | Phạm vi | Kết quả |
|---|---|---|
| 07/11/2026, trong container backend, trước khi commit | `test_simple_triage_emergency_flow.py` và `test_simple_agent_emergency_screen.py` | 88 passed |

Báo cáo không trích kết quả chạy toàn bộ bộ test trong tuần này, vì không có lần chạy toàn bộ nào được ghi lại cùng ngày và cùng phạm vi.

### 7.3. Khoảng trống

16 test xfail của `test_simple_agent.py` vẫn nguyên như trước. Chúng là các hành vi cốt lõi của giai đoạn A: hỏi lại khi câu trả lời mơ hồ, chuyển câu khi người bệnh không biết, sửa giá trị đã ghi, và các bước xác nhận. Lý do xfail không đổi: các test này còn dùng ID giả của kho mock đã bị thay ngày 26/08/2026.

---

## 8. ĐO LƯỜNG

### 8.1. Đánh giá agent thật: không thực hiện được

Từ ngày 06/11/2026, tài khoản OpenAI của dự án trả lỗi 429 `credit_balance_exhausted` cho cả lời gọi chat lẫn lời gọi embedding. Lần chạy đánh giá agent trên train, validation và test tối ngày 06/11 đều thất bại: backend trả 502 ở mọi lần thử. Vì vậy tuần này **không có số đo nào về độ chính xác của agent**. Lỗi F1 ở mục 5.1 được quan sát trong các lần chạy thành công trước khi hết credit.

Hệ quả là các thay đổi ở mục 5.1 và 5.2 mới chỉ được kiểm bằng test có model giả lập, chưa được kiểm trên model thật.

### 8.2. Bộ lọc khẩn cấp: đo được mà không cần model

Bộ lọc không gọi model nên vẫn đo được trên lời mở đầu của các ca. Chỉ những ca có kỳ vọng rõ ràng (phải báo động hoặc phải im lặng) mới được tính. Tôi cũng viết một bộ lọc V3 ứng viên với các cải tiến sau:

- luật đồng xuất hiện qua nhiều mệnh đề, ví dụ cổ sưng kèm khó thở, hoặc tức ngực kèm vã mồ hôi;
- veto trước và sau đoạn khớp: tay chân "tím tái" không phải tím môi, máu đã ngừng chảy thì không báo, mồ hôi do sốt thì không báo;
- từ phủ định miền Nam và teencode: "hổng", "khum", "hok", "đâu có";
- đổi sinh hiệu nói bằng lời cho lớp kiểm tra sinh hiệu;
- hàm `screen_self_harm()` chạy riêng.

Kết quả đo ngày 07/11/2026:

| Bộ lọc | Tập đo | Tỷ lệ bắt đúng (recall) | Báo động sai do từ ngữ |
|---|---|---:|---:|
| V2 (đang có trong repository) | Train + validation | 0,84 | 0 |
| V3 ứng viên (chưa đưa vào repository) | Train + validation | 1,00 | 0 |

Cần đọc bảng này cùng bốn giới hạn:

1. Lần đo dùng cách chia tập thử, trước khi đợt 3 được khoá và trước khi sửa các ca theo kết quả rà soát mù. Con số trên cách chia tập cuối cùng có thể khác.
2. Sáu ca có SpO2 90–91% được kỳ vọng im lặng nhưng bị lớp sinh hiệu gắn cờ. Các ca này được báo riêng và không tính là báo động sai do từ ngữ, vì quy ước của kịch bản để trống kỳ vọng khi chỉ có con số sinh hiệu là nguy hiểm.
3. V3 được tinh chỉnh trên chính train và validation này, nên recall 1,00 là kết quả trên dữ liệu đã dùng để tinh chỉnh, chưa phải khả năng tổng quát.
4. Trong lúc tinh chỉnh, tôi đã xem lời mở đầu của một số ca mà sau khi khoá lại rơi vào tập test: r94, c140, r126. Ngoài ra, hai mã ca test là x08 và m123 bị in ra ngoài ý muốn (chỉ mã ca, không có nội dung). Khi đo trên test, kết quả sẽ được báo cáo hai lần: trên toàn bộ tập test, và trên tập test bỏ 5 ca này.

---

## 9. ĐỐI CHIẾU VỚI TIÊU CHÍ TUẦN 7

### 9.1. Sản phẩm bàn giao

| Sản phẩm | Kết quả | Minh chứng |
|---|---|---|
| Agent giai đoạn A | Đạt | `src/simple_agent/`; có thêm tín hiệu `safety_screen` và quy tắc đọc sinh hiệu nói bằng lời |
| Hợp đồng tool | Đạt | 11 tool; test bảo đảm định nghĩa tool khớp prompt |
| Mô hình trạng thái | Đạt | `session.py`, `persistence.py` |
| Bộ test hội thoại | Đạt, kèm hai việc dở | 590 ca qua 9/9 kiểm tra, cộng 91 hàm test tự động. Đợt 4 mới có 186/210 ca; 16 test xfail |

### 9.2. Tiêu chí hoàn thành

| Tiêu chí | Kết quả | Thực thi ở | Ghi chú |
|---|---|---|---|
| Không tự sinh ID ngoài dữ liệu hợp lệ | Đạt | Mã | Mã từ chối mọi ID không có trong kho hoặc chưa được tìm thấy; test chạy được trên CI từ 27/10 |
| Hỏi tối đa một ý chính mỗi lượt | Đạt một phần | Mã chọn một fact; prompt ràng buộc câu chữ | Câu hỏi an toàn ở mục 5.1 **thay** câu hỏi của lượt đó, không hỏi thêm. Lớp chặn đầu ra chỉ kiểm chẩn đoán và kê đơn; mã chưa đếm số câu hỏi trong tin nhắn |
| Hiểu các cách diễn đạt tương đương | Đạt một phần | Mã (bộ lọc, tìm kiếm) và prompt (sinh hiệu nói bằng lời) | Tuần này có thêm bộ dữ liệu để đo và hai lớp lỗi đã sửa, nhưng chưa có số đo trên agent thật (mục 8.1) |

Kết quả: 3/4 sản phẩm đạt trọn, 1 đạt kèm việc dở. 1/3 tiêu chí đạt, 2 đạt một phần. So với đầu tuần, tiêu chí thứ ba đã có công cụ đo; thứ còn thiếu là chạy được model.

---

## 10. ĐỐI CHIẾU VỚI KẾ HOẠCH TUẦN 6

| # | Việc chuyển tiếp (mục 15 tuần 6) | Cuối tuần 7 |
|---:|---|---|
| 1 | Test API cho `/profiles` | Chưa làm |
| 2 | Endpoint readiness có kiểm tra DB | Chưa làm |
| 3 | Trường tiến trình trong phản hồi simple agent | Chưa làm; phản hồi có `action`, `route`, `question_target_id`, nhưng không có trường tiến trình riêng |
| 4 | `Literal` cho `action`, `decision_type`; thống nhất tên trường phiên bản | Chưa làm; vẫn là `str` và `version` |
| 5 | ADR về namespace lâm sàng | Chưa làm |
| 6 | Quyết định về lối vào khách `/auth/guest` | Chưa quyết; endpoint vẫn còn |

Kết quả: 0/6. Tuần này ưu tiên đo và sửa agent hội thoại, nên cả sáu việc chuyển sang tuần 8. Kết quả này được ghi nguyên trạng, không gộp vào nhóm "đang làm".

---

## 11. SẢN PHẨM VÀ MINH CHỨNG TUẦN 7

Các commit dưới đây nằm trên nhánh `feat/dataset-800-screen-v3` của `vietsosad/Medical_AI_Agent`, đều ngày 07/11/2026. Nhánh đã được gộp vào `main` qua PR #11 ngày 07/11; hash dưới đây là của bản đã sửa message, được gộp qua PR #13 ngày 09/11:

| Commit | Nội dung |
|---|---|
| `8516579` | Bộ dựng dữ liệu `generated_mock_v2` và ba công cụ kiểm tra |
| `c517642` | 400 kịch bản của đợt 1 và đợt 2, đã khoá |
| `928cb28` | 190 kịch bản của đợt 3, đã khoá |
| `59cad50` | 186 kịch bản nháp của đợt 4, chưa đăng ký |
| `f565eeb` | 590 bản ghi đã dựng, cách chia tập và các báo cáo kiểm tra |
| `b19e8eb` | Tín hiệu tự hại, câu hỏi an toàn được ưu tiên, 9 luật V2 của bộ lọc khẩn cấp, cùng test (mục 5.1, 5.3) |
| `9934381` | Quy tắc đọc sinh hiệu nói bằng lời (mục 5.2) |
| `10afb84` | Lưu ca có cờ khẩn khi model lỗi ngay tin nhắn đầu, cùng test (mục 5.5) |

Quy mô thay đổi giữa `26ed656` và `aca9549`: mã nguồn và test là 13 tệp (+1.934/−61 dòng); dữ liệu đánh giá là 53 tệp (+33.518 dòng).

**Ngoài phạm vi tuần 7.** Trong tuần, tôi cũng làm phần phân tích chất lượng cho dashboard điều dưỡng (`27dc3d3`, `45e4635`, `3d8949e`, `aca9549`; frontend 37 tệp, +4.336/−384 dòng). Phần này thuộc chủ đề tuần 10 (bảng điều phối và HITL) và sẽ được báo cáo ở tuần đó.

---

## 12. KẾT QUẢ ĐẠT ĐƯỢC TRONG TUẦN 7

Trong tuần 7, tôi đã hoàn thành các nội dung sau:

- Xây bộ dữ liệu đánh giá hội thoại 590 ca trong ba đợt, khoá từng đợt trước khi tinh chỉnh, và qua 9/9 kiểm tra toàn bộ dữ liệu.
- Phân loại lỗi hiểu sai của giai đoạn A thành bốn lớp F1–F4 và đưa từng lớp vào bộ dữ liệu.
- Sửa lỗi F1: lời nói gián tiếp về tự hại giờ đưa câu hỏi an toàn lên hỏi kế tiếp, nhưng không bao giờ tự đặt mức ESI.
- Sửa lỗi F2 ở tầng prompt: sinh hiệu nói bằng lời được đổi thành con số; những cách nói thật sự mơ hồ vẫn được giữ là mô tả.
- Bổ sung 9 luật V2 cho bộ lọc cụm từ khẩn cấp, có cơ chế loại bỏ khi gặp từ phủ định trong đoạn khớp.
- Sửa lỗi làm mất ca có cờ khẩn khi model gặp sự cố ngay tin nhắn đầu.
- Viết bộ lọc V3 ứng viên: recall trên train và validation tăng từ 0,84 lên 1,00 mà không có báo động sai do từ ngữ.
- Ghi lại danh sách ca test đã bị nhìn thấy trong lúc tinh chỉnh, để báo cáo kết quả test sạch về sau.
- Ghi nhận 0/6 việc chuyển tiếp từ tuần 6.

---

## 13. KHÓ KHĂN VÀ CÁCH XỬ LÝ

| Khó khăn | Cách xử lý |
|---|---|
| Tài khoản OpenAI hết credit từ 06/11; không chạy được agent thật | Chuyển sang những việc không cần model: dựng dữ liệu, sửa bằng mã, đo bộ lọc. Ghi rõ là không có số đo agent, không thay bằng số cũ |
| Thêm bản ghi làm `assign_splits` chuyển bản ghi cũ giữa các tập | Khoá từng đợt ngay sau khi dựng và trước khi tinh chỉnh; tách đợt 3 khỏi đợt 4 để việc tinh chỉnh trên đợt 3 không kéo ca của nó vào test |
| Hàm `fold()` của kho tri thức đổi chữ hoa thành chữ thường. Khi áp lên một biểu thức chính quy, `\S` thành `\s` và nhóm có tên `(?P<…>)` bị hỏng, nên các mẫu V2 có khoảng cách giữa từ không bao giờ khớp ở dạng bỏ dấu | Viết hàm `_fold_pattern` biết cấu trúc biểu thức chính quy, dùng trong V3 |
| Cờ `span_negation` loại luôn cụm "nói không hết câu" của luật khó thở, vì chính cụm này chứa từ "không" | Tách cụm đó thành một luật riêng trong V3 |
| Một lệnh tìm kiếm vô tình in ra mã của hai ca test | Ghi lại mã ca vào danh sách bị nhìn thấy; script đo từ đó không bao giờ liệt kê ca test |
| Phiên viết kịch bản đợt 4 dừng khi chạm giới hạn sử dụng | Commit 186 ca dưới dạng bản nháp và cố ý chưa đăng ký, thay vì đăng ký một đợt dở |

---

## 14. KẾ HOẠCH TUẦN 8

Theo kế hoạch 15 tuần, tuần 8 làm **quyết định ESI và an toàn lâm sàng**:

- Đưa bộ lọc V3 vào repository, kể cả hàm `screen_self_harm()` chạy riêng, để tín hiệu tự hại không bị cảnh báo khẩn khác che mất (giới hạn ở mục 5.1).
- Rà soát bộ đối chiếu tiêu chí bằng Python thuần: tiêu chí đã thỏa, tiêu chí còn thiếu dữ kiện, và `RETURN_INCOMPLETE`.
- Viết test cho under-triage và prompt injection.

Các việc chuyển tiếp từ tuần 7:

1. Viết nốt 24 kịch bản của đợt 4, đăng ký đợt 4 (210 ca), dựng, kiểm tra, rồi khoá.
2. Khi có lại credit OpenAI, chạy agent thật trên train và validation trước. Chỉ đo trên test một lần, sau khi mọi thay đổi đã chốt, và báo cáo cả hai con số ở mục 8.2.
3. Viết lại 16 test xfail theo ID thật của kho.
4. Thêm kiểm tra bằng mã rằng mỗi tin nhắn gửi người bệnh chỉ có một câu hỏi.
5. Rà soát lại nhánh `feat/dataset-800-screen-v3`; nhánh đã được gộp vào `main` qua PR #11 ngày 07/11/2026.

Các việc chuyển tiếp từ tuần 6: giữ nguyên sáu việc ở mục 10.

---

## 15. KẾT LUẬN TUẦN 7

Tuần 7 chuyển câu hỏi từ "agent có chạy không" sang "làm sao biết agent hiểu đúng". Câu trả lời của tuần là một bộ dữ liệu được khoá trước khi tinh chỉnh, có nhãn do máy tính, và có các lớp lỗi được đặt tên. Ngay khi có bộ dữ liệu này, nó đã tìm ra một lỗi nghiêm trọng mà các test cũ không bắt được: agent đọc một lời nói gián tiếp về tự hại thành chuyện mất ngủ.

Tuần này cũng cho thấy giới hạn của việc chỉ sửa: không có model để chạy thì không có số đo. Báo cáo vì vậy tách rõ những gì đã đo được (bộ lọc, trên train và validation), những gì mới có test với model giả lập (F1, F2), và những gì chưa đo (agent thật, tập test).

Nguyên tắc được chốt trong tuần này là: **khoá dữ liệu trước khi tinh chỉnh, chỉ tinh chỉnh trên train và validation, và mọi con số phải nói rõ nó được đo trên tập nào.**

---

## NGƯỜI LẬP BÁO CÁO

**Lê Hoàng Việt**  
Ký và ghi rõ họ tên: ____________________  
Ngày: ____ / ____ / 2026
