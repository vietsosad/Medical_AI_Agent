# Vấn đề mở — Đường tới ESI 1 của người bệnh tự khai

> **Trạng thái: CHỜ Ý KIẾN CHUYÊN MÔN LÂM SÀNG.** Tài liệu này chỉ ghi lại một
> số đo và đặt câu hỏi. **Không có bất kỳ thay đổi nào đã được thực hiện** đối
> với kho phác đồ, các trường dữ kiện (fact target) hay logic phân loại. Không
> đề xuất nào ở đây được thi hành cho tới khi có người đủ chuyên môn quyết định.
>
> Ngày đo: 16/09/2026 · Nguồn: 5 bảng corpus trong PostgreSQL · Người ghi: nhóm kỹ thuật

## 1. Tóm tắt

Hệ thống có **216 tiêu chí phác đồ dẫn tới ESI 1** (mức tối khẩn). Nhưng một
người bệnh tự khai qua giao diện chat chỉ chạm được tới **20** trong số đó.
188/208 tiêu chí ESI 1 hạng `CLINICAL_AUTHORITY` bị khoá sau các trường dữ kiện
chỉ nhân viên y tế mới được điền (`CLINICIAN_ONLY`).

Trong 20 cánh cửa còn mở, **25 trên 35 điều kiện là chỉ số phải đo bằng thiết
bị** (SpO2, nhịp thở, nhịp tim, huyết áp tâm thu). Đúng **một** cánh cửa không
đòi hỏi thiết bị nào: dấu hiệu **tím tái**.

Hệ quả cần được cân nhắc: một người bệnh không sở hữu máy đo SpO2 và máy đo
huyết áp, về mặt cấu trúc dữ liệu, gần như chỉ còn một con đường duy nhất để hệ
thống kết luận ESI 1.

## 2. Cách đo (tái lập được)

Số liệu lấy bằng đúng hai bộ lọc mà bộ sinh ca đánh giá đang dùng, tại
[`eval/simple_runtime/golden_builder.py`](../eval/simple_runtime/golden_builder.py):

- `_eligible()` — giữ lại tiêu chí có `authority_scope = CLINICAL_AUTHORITY`,
  `atom_type = DECISION_CRITERION`, `impact = ASSIGN_ESI`, mọi điều kiện dùng
  toán tử so sánh được, và **không có điều kiện bắt buộc nào trỏ vào một fact
  target `CLINICIAN_ONLY`**.
- `_isolated_for_level()` — loại tiếp những tiêu chí mà chính dữ kiện sinh ra
  cho nó lại thoả một tiêu chí ở mức khẩn hơn.

Chạy trên corpus thật: 1.768 tiêu chí · 1.132 khái niệm · 243 fact target ·
4.260 quan hệ.

## 3. Các trường khoá đường tới ESI 1

Hệ thống có 10 fact target `CLINICIAN_ONLY`. Bảy trong số đó xuất hiện trong
tiêu chí ESI 1:

| Fact target | Tên | Xuất hiện ở … tiêu chí ESI 1 | Là rào chặn **duy nhất** ở … |
|---|---|---:|---:|
| `life_saving_intervention_required` | Cần can thiệp cứu sống ngay | 128 | **112** |
| `circulation_status` | Tình trạng tuần hoàn | 26 | 21 |
| `breathing_status` | Tình trạng hô hấp | 22 | 16 |
| `mental_status` | Tình trạng ý thức | 17 | 10 |
| `airway_status` | Tình trạng đường thở | 15 | 10 |
| `communication_coherence` | Mức độ mạch lạc khi giao tiếp | 1 | 0 |
| `behavioral_control` | Khả năng kiểm soát hành vi | 1 | 0 |

Cột cuối đọc là: "nếu trường này được coi là người bệnh khai được, thì có bao
nhiêu tiêu chí ESI 1 mở ra, trong khi mọi điều kiện còn lại của nó vốn đã khai
được". Đây là **số liệu mô tả, không phải đề xuất**.

Ba fact `CLINICIAN_ONLY` còn lại không tham gia vào tiêu chí ESI 1 nào:
`high_risk_situation`, `resource_count`, `pupil_asymmetry`.

## 4. Mười ba cánh cửa còn mở

| Tổ hợp dữ kiện | Cần thiết bị đo? | Số tiêu chí |
|---|---|---:|
| Nhịp thở | Có | 3 |
| Độ bão hoà oxy (SpO2) | Có | 2 |
| Huyết áp tâm thu | Có | 2 |
| Nhịp thở + SpO2 | Có | 2 |
| Huyết áp tâm thu + Đặc điểm chất nôn | Có | 2 |
| Nhịp tim + Đặc điểm phân + Huyết áp tâm thu | Có | 2 |
| **Có tím tái** | **Không** | **1** |
| Nhịp tim + Huyết áp tâm thu | Có | 1 |
| Lượng máu khi đại tiện + Huyết áp tâm thu | Có | 1 |
| Lượng máu khi đại tiện + Nhịp tim | Có | 1 |
| Khả năng ăn uống + Nhịp thở | Có | 1 |
| Khả năng cầm máu + Huyết áp tâm thu | Có | 1 |
| SpO2 + Huyết áp tâm thu + Đặc điểm chất nôn | Có | 1 |
| | | **20** |

## 5. Vì sao điều này đáng đưa ra hội chẩn

Trong bối cảnh sử dụng thực tế ở Việt Nam, máy đo SpO2 kẹp ngón tay đã phổ biến
hơn nhiều sau dịch, nhưng vẫn không phải hộ gia đình nào cũng có, và máy đo
huyết áp lại càng ít phổ biến hơn ở nhóm trẻ tuổi. Nếu đa số đường tới ESI 1
đều đi qua một con số đo được, thì với người bệnh không có thiết bị, hệ thống
gần như không còn cách nào kết luận mức tối khẩn — kể cả khi tình trạng thực sự
là tối khẩn.

Đây là rủi ro **under-triage**, loại sai sót nguy hiểm nhất trong phân loại cấp
cứu, nên nó cần được một người có chuyên môn nhìn qua chứ không nên để mặc như
một chi tiết kỹ thuật.

## 6. Tài liệu này KHÔNG khẳng định điều gì

- **Không nói rằng việc đánh dấu `CLINICIAN_ONLY` là sai.** Với
  `life_saving_intervention_required` — trường chặn 112 tiêu chí, nhiều nhất —
  việc hỏi người bệnh "anh/chị có cần can thiệp cứu sống ngay không" là một câu
  hỏi vô nghĩa về mặt lâm sàng. Ở đây ranh giới hiện tại nhiều khả năng là đúng.
- **Không đề xuất chuyển bất kỳ trường nào sang người bệnh tự khai.**
- **Không khẳng định hệ thống đang bỏ sót ca thật.** Số liệu trên nói về cấu
  trúc dữ liệu, không phải về kết quả lâm sàng đã quan sát được. Muốn biết có bỏ
  sót thật hay không thì phải đo trên ca thật, việc đó chưa làm.

## 7. Câu hỏi cần người có chuyên môn trả lời

1. Với người bệnh **không có thiết bị đo**, một dấu hiệu tím tái duy nhất có đủ
   làm đường vào mức ESI 1 hay không? Nếu không đủ, hiện chưa có đường nào khác.
2. Bốn trường `breathing_status`, `mental_status`, `circulation_status`,
   `airway_status` (cộng lại là rào chặn duy nhất của **57** tiêu chí ESI 1) có
   dấu hiệu nào mà người nhà quan sát được và mô tả đủ tin cậy không — ví dụ
   "thở hổn hển không nói hết được một câu", "gọi mãi không tỉnh", "tay chân
   lạnh và tím"? Nếu có, chúng nên là **fact target riêng dành cho người bệnh
   khai**, tách hẳn khỏi trường dành cho nhân viên y tế — chứ không phải nới
   lỏng trường hiện có.
3. Khi hệ thống không đủ căn cứ cho ESI 1 nhưng lời kể có dấu hiệu nguy kịch,
   hành vi đúng là gì: giữ nguyên `RETURN_INCOMPLETE`, hay chủ động đẩy lên
   hàng đợi điều dưỡng?

## 8. Liên quan

- Bộ lọc dùng để đo: [`eval/simple_runtime/golden_builder.py`](../eval/simple_runtime/golden_builder.py)
- Hợp đồng kỹ thuật, mục "ESI là chính sách lâm sàng có ràng buộc, không phải
  lựa chọn tự do của LLM" và nguyên tắc `UNKNOWN ≠ NEGATIVE`
- Quan sát thực tế ngày 16/09/2026: một ca suy hô hấp (SpO2 78, nhịp thở 42)
  thoả đúng điều kiện của 3 tiêu chí ESI 1 đang có trong kho, nhưng hệ thống
  trả về ESI 2 vì tầng truy xuất không đưa được các tiêu chí đó vào nhóm đầu.
  Đó là một vấn đề **khác** với tài liệu này — vấn đề xếp hạng truy xuất, không
  phải vấn đề phạm vi dữ liệu — và đang được theo dõi riêng.
