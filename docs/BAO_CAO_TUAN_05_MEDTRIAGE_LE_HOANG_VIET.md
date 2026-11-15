# BÁO CÁO TIẾN ĐỘ DỰ ÁN KHOA HỌC VÀ CÔNG NGHỆ

## TUẦN 5 — THIẾT KẾ TRẢI NGHIỆM NGƯỜI DÙNG, WIREFRAME VÀ HỆ THỐNG THIẾT KẾ LÂM SÀNG

**Tên đề tài:** MedTriage AI — Hệ thống hỗ trợ tiếp nhận và phân luồng ưu tiên y tế  
**Người thực hiện:** Lê Hoàng Việt  
**Tuần thực hiện:** Tuần 5/15  
**Thời gian:** 24/08/2026 – 30/08/2026  
**Báo cáo liên kết:** Báo cáo Tuần 4 — Xây dựng corpus mẫu, pipeline ingestion và kiểm tra chất lượng dữ liệu  
**Trạng thái:** Hoàn thành screen map, user flow, wireframe v2 và design token; kịch bản usability test đã sẵn sàng, chưa thực hiện với người dùng ngoài nhóm

> **Lưu ý phạm vi:** Đây là báo cáo cá nhân của Lê Hoàng Việt. Các thiết kế trong tuần 5 phục vụ nghiên cứu và xây dựng nguyên mẫu. Giao diện không được trình bày như thiết bị chẩn đoán; mọi kết quả phân luồng chỉ có giá trị sau khi nhân viên y tế xác nhận. Tuần này chưa thu thập dữ liệu người dùng thật, vì vậy báo cáo không đưa ra số liệu usability định lượng.

---

## 1. MỤC TIÊU TUẦN 5

Bốn tuần đầu đã chốt bài toán, yêu cầu, kho dữ liệu và các cổng kiểm soát bằng chứng. Trong tuần 5, tôi chuyển các ràng buộc đó thành trải nghiệm sử dụng cụ thể cho hai vai trò chính: người bệnh/người nhà và nhân viên lâm sàng.

Các mục tiêu chính:

1. Rà soát bản wireframe v1 (01/08/2026) dựa trên các nguyên tắc an toàn đã chốt từ tuần 2 đến tuần 4.
2. Xây dựng screen map v2 cho cổng người bệnh và cổng điều dưỡng.
3. Vẽ user flow chi tiết và ánh xạ từng trạng thái phiên triage sang thành phần giao diện.
4. Thiết kế wireframe các màn hình: hội thoại, cảnh báo khẩn, xác nhận thông tin, chờ thẩm định, hàng đợi và chi tiết ca.
5. Xác định quy tắc hiển thị ESI, citation, trạng thái thiếu bằng chứng và SBAR theo từng vai trò.
6. Xây dựng design token và quy tắc accessibility ban đầu.
7. Chuẩn bị kịch bản usability test cho ba tình huống chính.

---

## 2. KẾ THỪA KẾT QUẢ TỪ CÁC TUẦN TRƯỚC

Tuần 5 không thiết kế giao diện từ đầu. Mỗi quyết định UX đều xuất phát từ một ràng buộc đã chốt trước đó:

| Ràng buộc đã chốt | Nguồn | Hệ quả bắt buộc với giao diện |
|---|---|---|
| Không chẩn đoán, không kê đơn | Tuần 1–2 | Không hiển thị tên bệnh nghi ngờ, thuốc hoặc chỉ định chuyên khoa |
| Red flag được kiểm tra trước LLM | Tuần 2, UC-02 | Cảnh báo khẩn phải xuất hiện ngay, không chờ câu trả lời của mô hình |
| Người dùng không cần hiểu thuật ngữ ESI | Tuần 2, mục 4.3 | Người bệnh nhìn thấy trạng thái và hướng dẫn, không thấy mã ESI thô |
| Người dùng luôn biết hệ thống đang ở bước nào | Tuần 2, mục 4.3 | Cần thanh tiến trình gắn với trạng thái phiên thật |
| Chỉ evidence `AUTHORIZED` được hỗ trợ ESI | Tuần 3–4 | Tách nguồn có thẩm quyền và nguồn chỉ tham khảo trên giao diện |
| Thiếu bằng chứng thì fail-closed | Tuần 4, mục 9.2 | Cần trạng thái `INSUFFICIENT_EVIDENCE` rõ ràng, không giả lập kết luận |
| Mọi kết luận phải qua HITL | Tuần 2, FR-16/FR-17 | Cổng điều dưỡng có xác nhận, điều chỉnh kèm lý do và audit |

---

## 3. PHƯƠNG PHÁP THIẾT KẾ

Tôi áp dụng quy trình gồm năm bước, ưu tiên audit trước khi vẽ lại:

```text
Audit wireframe v1 theo ràng buộc an toàn
        │
        ▼
Chốt nguyên tắc thiết kế và quy tắc 3 giây
        │
        ▼
Screen map v2 + user flow + ánh xạ trạng thái → UI
        │
        ▼
Wireframe v2 + design token + quy tắc accessibility
        │
        ▼
Cognitive walkthrough nội bộ → chỉnh sửa → kịch bản usability test
```

Tiêu chí đánh giá mỗi màn hình được rút gọn thành bốn câu hỏi mà người dùng phải trả lời được trong khoảng 3 giây:

1. **Ai?** — ca nào, người bệnh hay người thân.
2. **Cái gì?** — triệu chứng chính hoặc thông tin đang được hỏi.
3. **Mức độ khẩn?** — có dấu hiệu nguy cấp hay không.
4. **Làm gì tiếp theo?** — một hành động chính duy nhất.

---

## 4. AUDIT WIREFRAME V1

### 4.1. Phạm vi audit

Bản wireframe v1 trong `docs/Wireframe_UI_Flow.md` được tạo ngày 01/08/2026, trước khi các quyết định về evidence gate, HITL bắt buộc và fail-closed được chốt. Tôi rà soát 5 màn hình (S0, S1, S1a, S2, S3), bảng token và các luồng tương tác.

### 4.2. Kết quả audit

| # | Mức độ | Vấn đề trong v1 | Vị trí | Hướng xử lý trong v2 |
|---:|---|---|---|---|
| 1 | Nghiêm trọng | Cảnh báo khẩn ghi “Nghi ngờ: Nhồi máu cơ tim / Thuyên tắc phổi” | S1a | Chỉ mô tả dấu hiệu và hành động: “Phát hiện dấu hiệu cần đánh giá khẩn cấp” |
| 2 | Nghiêm trọng | Phần lý do ghi “gợi ý migraine nặng” và khuyến cáo “đặt lịch khám chuyên khoa Thần kinh” | S2 | Loại bỏ tên bệnh và chỉ định chuyên khoa khỏi giao diện người bệnh |
| 3 | Cao | Người bệnh nhìn thấy ESI ngay khi AI xử lý xong, trước khi điều dưỡng duyệt | S2 | Thay bằng màn hình chờ thẩm định; chỉ hiển thị kết quả đã được xác nhận |
| 4 | Cao | “Thời gian chờ khuyến cáo ≤ 30 phút” được gắn cứng theo ESI | S2 | Không hiển thị SLA cho người bệnh; SLA phía điều dưỡng lấy từ cấu hình cơ sở |
| 5 | Cao | Nguồn tham khảo được liệt kê mà không có trạng thái thẩm quyền | S2 | Tách nguồn `AUTHORIZED` và nguồn chỉ tham khảo, ghi rõ nhãn |
| 6 | Cao | Không có trạng thái xác nhận thông tin, thiếu bằng chứng hoặc chuyển nhân viên | Toàn luồng | Bổ sung bước “Bạn xác nhận” và trạng thái `INSUFFICIENT_EVIDENCE`/`HANDOFF` |
| 7 | Trung bình | Overlay được kích hoạt khi “phát hiện triệu chứng ESI 1 hoặc 2”, trộn red flag với mức ESI | S1a | Red flag là cờ nguy cơ độc lập, không phải mức ESI |
| 8 | Trung bình | Dùng emoji làm icon trong nút, nhãn và tiêu đề | Toàn bộ | Dùng icon vector `lucide-react` có `aria-hidden` |
| 9 | Trung bình | Disclaimer 12px, caption 13px, body 15px | Bảng typography | Body tối thiểu 14–16px; dữ liệu quan trọng 16–20px |
| 10 | Trung bình | Badge ESI 2, 3, 4 dùng chữ trắng trên nền màu không đạt WCAG AA | Bảng màu ESI | Đổi sang nền nhạt + chữ đậm; màu đậm chỉ dùng cho viền và icon |
| 11 | Thấp | Chưa có thiết kế cho cổng điều dưỡng | Screen map | Bổ sung hàng đợi, chi tiết ca và form quyết định |

### 4.3. Kiểm tra độ tương phản màu ESI trong v1

Tôi tính tỷ lệ tương phản giữa chữ trắng `#FFFFFF` và nền badge theo công thức relative luminance của WCAG 2.1. Badge ESI dùng chữ 14px đậm, chưa đạt ngưỡng “chữ lớn”, nên yêu cầu tối thiểu là 4,5:1.

| Mức ESI | Nền v1 | Tỷ lệ tương phản | Kết quả AA (4,5:1) |
|---:|---|---:|---|
| 1 | `#DC2626` | ≈ 4,83:1 | Đạt |
| 2 | `#EA580C` | ≈ 3,56:1 | Không đạt |
| 3 | `#CA8A04` | ≈ 2,94:1 | Không đạt, kể cả ngưỡng chữ lớn 3:1 |
| 4 | `#16A34A` | ≈ 3,30:1 | Không đạt |
| 5 | `#2563EB` | ≈ 5,17:1 | Đạt |

Kết luận: ba trên năm badge ESI của v1 không đọc tốt được với người có thị lực kém hoặc khi màn hình bị chói. Đây là lý do v2 chuyển sang mẫu “nền nhạt + chữ đậm cùng tông”.

---

## 5. NGUYÊN TẮC THIẾT KẾ ĐƯỢC CHỐT

| Nguyên tắc | Diễn giải trong MedTriage |
|---|---|
| Rõ ràng hơn đẹp mắt | Mỗi màn hình phục vụ một nhiệm vụ; không thêm trang trí không mang thông tin |
| Màu sắc chỉ mang chức năng | Màu chỉ báo trạng thái, mức nguy cơ hoặc hành động |
| Một hành động chính | Mỗi thẻ hoặc màn hình chỉ có một CTA chính |
| Không bao giờ chỉ dùng màu | Mức nguy cơ luôn đi kèm chữ, số và icon |
| Ngôn ngữ phân luồng, không chẩn đoán | Mô tả dấu hiệu và bước tiếp theo, không gọi tên bệnh |
| Trạng thái trung thực | Giao diện không hiển thị kết quả chưa được server lưu thành công |
| Hiện dần thông tin | Transcript, nguồn đầy đủ và PII đóng mặc định, chỉ mở khi cần |

---

## 6. SCREEN MAP V2

### 6.1. Cổng người bệnh/người nhà

| Mã | Màn hình/thành phần | Route hoặc vị trí | Vai trò |
|---|---|---|---|
| P0 | Trang giới thiệu + cam kết sử dụng | `/` + modal đồng ý | Nêu rõ phạm vi, không chẩn đoán, số 115 |
| P1 | Hội thoại triage + thanh tiến trình 5 bước | `/triage` | Thu thập triệu chứng |
| P1a | Thẻ cảnh báo khẩn trong hội thoại | Trong P1 | Hướng dẫn gọi 115 ngay |
| P1b | Nút SOS 115 cố định | Góc màn hình | Lối tắt người dùng chủ động chọn |
| P1c | Thẻ lựa chọn có cấu trúc | Trong P1 | Giảm gõ phím với câu hỏi đóng |
| P1d | Thẻ xác nhận thông tin đã thu thập | Trong P1 | Người bệnh kiểm tra, sửa hoặc bổ sung |
| P1e | Màn hình chờ thẩm định | Trong P1 | Thông báo hồ sơ đã chuyển nhân viên y tế |
| P1f | Kết quả đã được thẩm định | Trong P1 | Chỉ xuất hiện sau quyết định HITL |
| P2 | Lịch sử phiên và chi tiết | `/history`, `/history/[id]` | Xem lại phiên trước |
| P3 | Hồ sơ cá nhân và người thân | `/profile` | Bối cảnh người khai và liên hệ khẩn |

### 6.2. Cổng nhân viên lâm sàng

| Mã | Màn hình/thành phần | Route hoặc vị trí | Vai trò |
|---|---|---|---|
| N1 | Hàng đợi ưu tiên | `/clinical/queue` | Biết ngay ca nào cần nhận trước |
| N2 | Chi tiết ca phân luồng | `/clinical/cases/[caseId]` | Rà soát, bổ sung, quyết định và bàn giao |
| N2a | Nguồn trích dẫn của ca | `/clinical/cases/[caseId]/sources/[citationId]` | Đối chiếu căn cứ ngay trong ngữ cảnh ca |
| N3 | Cảnh báo nguy cấp toàn cục | Lớp thông báo | Báo ca red flag mới, ghim đầu hàng đợi |
| N4 | Hộp thoại truy cập PII | Trong N2 | Yêu cầu lý do và ghi audit |
| N5 | Hộp thoại trả ca | Trong N2 | Trả ca về hàng đợi kèm lý do |

### 6.3. Hạng mục loại khỏi MVP

| Hạng mục | Lý do loại |
|---|---|
| Luồng EMS 115, ETA xe, chuẩn bị giường | Chưa có tích hợp ngoại viện thật; dễ tạo dữ liệu giả trông như thật |
| Biểu đồ KPI và Concordance Rate trong cổng điều dưỡng | Là dữ liệu quản trị, không hỗ trợ xử lý ca ngay |
| Menu thư viện phác đồ riêng | Làm nhân viên rời khỏi ca; căn cứ ngắn đã hiển thị trong ca |
| Công tắc đổi vai trò Nurse/Doctor | Chỉ dùng trong môi trường demo/dev |
| Xuất PDF cho người bệnh | Hoãn đến sau khi luồng HITL ổn định |

---

## 7. USER FLOW CHI TIẾT

### 7.1. Luồng người bệnh/người nhà

```text
Mở trang → Đọc phạm vi + đồng ý sử dụng
        │
        ▼
Chọn người cần khai: bản thân / người thân
        │
        ▼
Nhập triệu chứng tự do hoặc bằng giọng nói
        │
        ▼
Kiểm tra an toàn (trước LLM)
        │
        ├── Có red flag → Thẻ cảnh báo khẩn + nút gọi 115
        │                 + cảnh báo song song tới điều dưỡng
        │
        └── Không → Hỏi bổ sung từng ý (chữ hoặc thẻ lựa chọn)
                        │
                        ▼
                Thẻ xác nhận thông tin (sửa/bổ sung được)
                        │
                        ▼
                AI đối chiếu phác đồ có nguồn
                        │
                        ▼
                Màn hình chờ nhân viên y tế thẩm định
                (kể cả khi AI không đủ bằng chứng)
                        │
                        ▼
                Kết quả đã thẩm định + hướng dẫn tiếp theo
```

Điểm thiết kế quan trọng: khi evidence gate trả về `INSUFFICIENT_EVIDENCE`, người bệnh vẫn đi vào cùng màn hình chờ thẩm định. Người bệnh không cần biết lỗi nằm ở tầng dữ liệu, nhưng điều dưỡng sẽ thấy rõ ca này không có đề xuất ESI từ AI.

### 7.2. Luồng nhân viên lâm sàng

```text
Ca mới vào hàng đợi
        │
        ├── Red flag → cảnh báo toàn cục + ghim đầu hàng đợi
        │              "Xác nhận đã thấy" chỉ tắt âm thanh
        ▼
Nhận ca (khóa chống xử lý trùng)
        │
        ▼
Rà soát 4 khối: Tóm tắt → Cảnh báo/sinh hiệu → Yếu tố nguy cơ → Đề xuất AI
        │
        ▼
Bổ sung sinh hiệu thực đo (có nguồn, người đo, thời điểm)
        │
        ▼
Quyết định: Xác nhận ESI │ Điều chỉnh ESI + lý do │ Yêu cầu đánh giá chuyên sâu
        │
        ▼
Server lưu thành công → Bàn giao → Hoàn tất
(Server lỗi → giữ ca, cho phép thử lại, không giả lập thành công)
```

Thứ tự sắp xếp hàng đợi: **Red flag → ESI có số nhỏ nhất → thời gian chờ lâu nhất**.

### 7.3. Ánh xạ trạng thái phiên sang giao diện

Thanh tiến trình của người bệnh không phải hình minh họa tĩnh. Mỗi bước được gắn với `workflow_phase` thật mà backend trả về:

| Bước hiển thị | `workflow_phase` tương ứng | Thành phần giao diện |
|---|---|---|
| 1. Kiểm tra an toàn | `SAFETY_CHECK` | Chỉ báo đang xử lý; thẻ cảnh báo nếu có red flag |
| 2. Thu thập thông tin | `INTENT_CLASSIFICATION`, `INTAKE_EXTRACTION`, `CLARIFICATION`, `REASSESSMENT` | Câu hỏi hội thoại, thẻ lựa chọn |
| 3. Bạn xác nhận | `PATIENT_CONFIRMATION` | Thẻ xác nhận thông tin |
| 4. AI phân loại | `RETRIEVAL`, `REASONING` | Chỉ báo đối chiếu phác đồ |
| 5. Nhân viên y tế duyệt | `HANDOFF`, `COMPLETE` | Màn hình chờ thẩm định hoặc kết quả đã thẩm định |

Với các ý định ngoài phạm vi như chào hỏi, câu hỏi không rõ hoặc ngoài triage, thanh tiến trình được thay bằng thông báo “Hỗ trợ đúng phạm vi” và không tăng bước khai thác triệu chứng.

Phía điều dưỡng, `review_status` được tách khỏi trạng thái phiên AI để tránh một trường `status` mang hai nghĩa:

| `review_status` | Hiển thị trên hàng đợi |
|---|---|
| `WAITING_REVIEW` | Chưa nhận |
| `ASSIGNED` / `IN_REVIEW` | Đang xử lý + tên người phụ trách |
| `NEEDS_MORE_INFO` | Thiếu dữ liệu |
| `SPECIALIST_REVIEW_REQUIRED` | Cần đánh giá chuyên sâu |
| `TRIAGE_DECIDED` | Đã quyết định |
| `HANDED_OFF` | Đã bàn giao |

---

## 8. WIREFRAME V2 CÁC MÀN HÌNH CHÍNH

### 8.1. P1 — Hội thoại triage

```text
┌──────────────────────────────────────────────────────────┐
│ MedTriage AI                     [Lịch sử] [Hồ sơ] [Sáng/Tối] │
├──────────────────────────────────────────────────────────┤
│ Đang khai cho: Bản thân                     [Đổi người]  │
│ (1) An toàn ─ (2) Thu thập ─ (3) Xác nhận ─ (4) AI ─ (5) Duyệt │
├──────────────────────────────────────────────────────────┤
│ [AI]  Cơn đau ngực bắt đầu từ khi nào?                   │
│                                                          │
│   [ Dưới 1 giờ ] [ 1–6 giờ ] [ Hơn 6 giờ ] [ Không rõ ]  │
│                                                          │
│                         Tôi đau từ khoảng 30 phút trước [Bạn] │
├──────────────────────────────────────────────────────────┤
│ [ Mô tả triệu chứng...                      ] [Mic] [Gửi] │
│ Hỗ trợ phân luồng ban đầu, không thay thế nhân viên y tế  │
└──────────────────────────────────────────────── [SOS 115] ┘
```

Quy tắc: mỗi lượt chỉ hỏi một ý chính; câu hỏi đóng có thẻ lựa chọn để giảm thao tác; luôn có lựa chọn “Không rõ” để tránh ép người dùng đoán.

### 8.2. P1a — Thẻ cảnh báo khẩn

```text
┌──────────────────────────────────────────────────────────┐
│ [!] Phát hiện dấu hiệu cần đánh giá khẩn cấp        [X]  │
│     Một số triệu chứng bạn mô tả có thể cần được nhân    │
│     viên y tế đánh giá trực tiếp ngay.                   │
├──────────────────────────────────────────────────────────┤
│ Khuyến nghị: gọi 115 hoặc nhờ người bên cạnh hỗ trợ ngay. │
│                                                          │
│ [ GỌI 115 ]  [ Gọi người liên hệ khẩn ]  [ Tôi đã biết ]  │
│                                                          │
│ Trong khi chờ hỗ trợ:                                    │
│ 1. Nhờ người ở gần ở lại cùng bạn.                       │
│ 2. Không tự lái xe.                                      │
│ 3. Làm theo hướng dẫn của nhân viên cấp cứu.             │
└──────────────────────────────────────────────────────────┘
```

**So sánh hai phương án trình bày cảnh báo khẩn:**

| Tiêu chí | A. Overlay toàn màn hình, khóa chat | B. Thẻ trong hội thoại + nút SOS cố định |
|---|---|---|
| Mức nổi bật | Rất cao | Cao (màu đỏ, `role="alert"`, `aria-live="assertive"`) |
| Giữ được ngữ cảnh hội thoại | Không | Có |
| Người thân vẫn khai tiếp cho điều dưỡng | Không | Có |
| Nguy cơ gây hoảng loạn | Cao hơn | Thấp hơn |
| Nguy cơ người dùng bỏ qua | Thấp | Trung bình, được giảm bằng chip “xem lại hướng dẫn” không biến mất và cảnh báo song song tới điều dưỡng |

Tôi chọn **phương án B** cho nguyên mẫu, với ba lớp bảo vệ: thẻ không thể biến mất hoàn toàn mà chỉ thu gọn thành chip có thể mở lại; nút SOS 115 luôn hiển thị; cảnh báo được gửi song song tới cổng điều dưỡng mà không chờ HITL. Đây là giả thuyết thiết kế cần được kiểm chứng bằng usability test (kịch bản 1, mục 13). Đồng thời, phương án này cần được thống nhất lại với quy tắc dự án đang mô tả cảnh báo dưới dạng overlay khóa chat.

### 8.3. P1d — Thẻ xác nhận thông tin

```text
┌──────────────────────────────────────────────────────────┐
│ Kiểm tra lại thông tin trước khi gửi nhân viên y tế      │
├──────────────────────────────────────────────────────────┤
│ Triệu chứng chính        Đau ngực                        │
│ Thời điểm bắt đầu        Khoảng 30 phút trước            │
│ Mức độ hiện tại          7/10                            │
│ Dấu hiệu đi kèm          Vã mồ hôi                       │
│ Bạn có nhắc tới nhưng    Khó thở nhẹ?  [Có] [Không]      │
│ chưa chắc chắn                                           │
│ Sinh hiệu hiện có        Chưa có số đo                   │
├──────────────────────────────────────────────────────────┤
│ [ Sửa hoặc bổ sung ]              [ Thông tin đã đúng ]  │
└──────────────────────────────────────────────────────────┘
```

Thiết kế này xử lý trực tiếp quy tắc tuần 2: fact phải có nguồn từ câu trả lời đã được xác nhận. Triệu chứng được nói kèm từ ngữ không chắc chắn không được ghi thành dữ kiện, mà được hỏi lại ở dòng riêng. Trường chưa có giá trị ghi “Chưa ghi nhận”, không tự điền mặc định.

### 8.4. P1e — Màn hình chờ thẩm định

```text
┌──────────────────────────────────────────────────────────┐
│ Hồ sơ đang chờ nhân viên y tế thẩm định         [ 02:14 ] │
│ Bạn không cần khai lại hoặc tải lại trang.               │
├──────────────────────────────────────────────────────────┤
│ [v] Hồ sơ đã được gửi                                    │
│ [~] Đang chờ nhân viên y tế xem xét                      │
│ [ ] Nhận hướng xử trí đã thẩm định                       │
├──────────────────────────────────────────────────────────┤
│ Kết quả chỉ hiển thị sau khi nhân viên y tế xác nhận.    │
│                         [ Gọi 115 nếu triệu chứng xấu đi ] │
└──────────────────────────────────────────────────────────┘
```

### 8.5. N1 — Hàng đợi ưu tiên của điều dưỡng

```text
┌──────────────────────────────────────────────────────────┐
│ Hàng đợi cần xử lý                                       │
│ Đang chờ: 6 │ Nguy cấp: 1 │ Đánh giá chuyên sâu: 1 │ Chờ lâu nhất: 18 phút │
│ [Tất cả] [Nguy cấp] [Ca của tôi] [Thiếu dữ liệu] [Chuyên sâu] │
├──────────────────────────────────────────────────────────┤
│ [RED FLAG] Đề xuất AI: ESI 2 │ BN ***-0412 │ Nam, 58      │
│ Đau ngực kèm vã mồ hôi        Chờ 04:10   Chưa nhận      │
│                                        [ Nhận và xem ca ] │
├──────────────────────────────────────────────────────────┤
│ Đề xuất AI: Chưa đủ căn cứ │ BN ***-0398 │ Nữ, 34          │
│ Đau bụng âm ỉ                 Chờ 12:30   Thiếu dữ liệu  │
│                                        [ Nhận và xem ca ] │
└──────────────────────────────────────────────────────────┘
```

Mỗi thẻ chỉ có dữ liệu cần để quyết định mở ca và đúng một CTA chính. Tên người bệnh được che mặc định. Ô “Nguy cấp” chỉ được tô đỏ khi giá trị lớn hơn 0.

### 8.6. N2 — Chi tiết ca và quyết định phân luồng

```text
┌──────────────────────────────────────────────────────────┐
│ BN ***-0412 │ Đề xuất AI: ESI 2 │ RED FLAG │ Chờ 06:02 │ Phụ trách: Bạn │
├──────────────────────────────────────────────────────────┤
│ 1. Tóm tắt ca: triệu chứng, khởi phát, diễn tiến, mức đau │
│ 2. Cảnh báo và sinh hiệu                                  │
│    Mạch: Chưa có dữ liệu   SpO2: Chưa có dữ liệu   [Nhập] │
│ 3. Yếu tố nguy cơ: bệnh nền, dị ứng, thuốc đang dùng      │
│ 4. Đề xuất AI: ESI 2 – lý do ngắn – độ đầy đủ dữ liệu     │
│    Căn cứ có thẩm quyền (2)      [Mở rộng]                │
│    Ca tương tự – chỉ tham khảo (1) [Mở rộng]              │
│    Transcript đầy đủ               [Mở rộng]              │
├──────────────────────────────────────────────────────────┤
│ (o) Xác nhận ESI đề xuất                                 │
│ ( ) Điều chỉnh ESI  → ESI cuối [__]  Lý do [chọn mã] *    │
│ ( ) Yêu cầu đánh giá chuyên sâu → Lý do [chọn mã] *       │
│ Ghi chú: ngắn, khách quan; không chẩn đoán hoặc kê đơn    │
│                               [ Lưu quyết định phân luồng ] │
└──────────────────────────────────────────────────────────┘
```

Màn hình chi tiết được sắp theo một luồng dọc thay cho bố cục ba cột, để điều dưỡng đọc từ trên xuống theo đúng thứ tự ra quyết định.

---

## 9. QUY TẮC HIỂN THỊ ESI, CITATION, THIẾU BẰNG CHỨNG VÀ SBAR

| Thông tin | Người bệnh/người nhà | Nhân viên lâm sàng |
|---|---|---|
| ESI do AI đề xuất | Không hiển thị | Luôn có nhãn “Đề xuất AI” |
| ESI cuối cùng | Hiển thị kèm “đã được nhân viên y tế xác nhận/điều chỉnh” | Hiển thị cạnh ESI AI để thấy chênh lệch |
| Red flag | Thẻ cảnh báo + hướng dẫn gọi 115 | Cảnh báo toàn cục + ghim đầu hàng đợi |
| Citation `AUTHORIZED` | Không hiển thị chi tiết | Hiển thị ngắn trong ca, mở được nguồn đầy đủ |
| Nguồn chỉ tham khảo/ca tương tự | Không hiển thị | Nhãn riêng “chỉ hỗ trợ tham khảo”, tách khỏi căn cứ |
| Độ tương đồng retrieval | Không hiển thị | Không hiển thị dạng phần trăm; chỉ dùng mức mô tả |
| `INSUFFICIENT_EVIDENCE` | Vẫn vào màn hình chờ thẩm định | Banner “Chưa đủ căn cứ – AI không đề xuất ESI”, liệt kê trường thiếu; form không điền sẵn ESI |
| SBAR | Không hiển thị | Dạng cấu trúc ngắn, mở rộng được |
| Transcript | Xem lại trong lịch sử của chính mình | Đóng mặc định, chỉ mở sau khi đã nhận ca |
| Sinh hiệu | Khai báo nếu có | Mỗi giá trị có đơn vị, nguồn, thời điểm; chưa đo thì ghi “Chưa có dữ liệu” |

Hai quyết định cần giải thích thêm:

1. **Không hiển thị độ tương đồng dạng phần trăm.** Cosine similarity là khoảng cách trong không gian embedding, không phải độ tin cậy lâm sàng. Hiển thị “58%” dễ khiến người đọc hiểu rằng hệ thống “chắc chắn 58%” về một kết luận, điều mà con số này không chứng minh được.
2. **Không điền sẵn ESI khi thiếu bằng chứng.** Nếu form có sẵn một giá trị mặc định, điều dưỡng dễ xác nhận theo quán tính. Khi AI không đủ căn cứ, điều dưỡng phải chủ động chọn mức ESI.

---

## 10. NGÔN NGỮ GIAO DIỆN (MICROCOPY)

| Không dùng | Thay bằng | Lý do |
|---|---|---|
| “Nghi ngờ nhồi máu cơ tim” | “Phát hiện dấu hiệu cần đánh giá khẩn cấp” | Không chẩn đoán |
| “Kết quả chẩn đoán” | “Kết quả phân luồng đã được thẩm định” | Đúng phạm vi |
| “AI xác định bạn thuộc ESI 3” | “Hồ sơ đang chờ nhân viên y tế thẩm định” | Không công bố kết quả chưa qua HITL |
| “Bàn phán quyết”, “quyền lực tối cao” | “Xác nhận phân luồng” | Ngôn ngữ nghiệp vụ, không gây nhiễu |
| “Độ tin cậy 58%” | “Mức tương đồng: gần/trung bình/xa” | Không ngụy tạo độ tin cậy |
| “Lỗi 500 – Internal Server Error” | “Chưa lưu được quyết định. Ca vẫn giữ trong hàng đợi, vui lòng thử lại.” | Không lộ lỗi kỹ thuật, nêu hành động tiếp theo |

Quy tắc chung: câu ngắn, chủ động, một ý mỗi câu; nút bấm dùng động từ chỉ hành động (“Gọi 115”, “Nhận và xem ca”, “Lưu quyết định phân luồng”).

---

## 11. DESIGN TOKEN VÀ ACCESSIBILITY

### 11.1. Theme màu

| Theme | Ngữ cảnh | Nền (60%) | Cấu trúc (30%) | Điểm nhấn (10%) |
|---|---|---|---|---|
| Pristine Day Medical | Cổng người bệnh ban ngày | Trắng/Slate-50 | Slate-100/Navy | Sky-600/Blue-600 |
| Deep Slate Night ER | Cổng điều dưỡng, ca trực đêm | Slate-950 | Slate-900 | Sky-400 + Rose báo động |
| Pediatric & Family Serenity | Khai cho trẻ em/người thân | Sky-50 | Trắng | Teal-600 |

### 11.2. Màu trạng thái và ESI

| Ý nghĩa | Token (giao diện sáng) | Cách dùng |
|---|---|---|
| ESI 1 / Red flag | `--esi-1: #e11d48` (rose-600) | Viền, icon, nút gọi 115; chữ trên nền `rose-50` dùng `rose-900/950` |
| ESI 2 / Cảnh báo | `--esi-2: #d97706` (amber-600) | Viền và icon; chữ dùng `amber-900/950` |
| ESI 3 / Thông tin | `--esi-3: #2563eb` (blue-600) | Viền và icon |
| ESI 4 | `--esi-4: #059669` (emerald-600) | Viền và icon |
| ESI 5 | `--esi-5: #64748b` (slate-500) | Trung tính, không cạnh tranh sự chú ý |
| SBAR/căn cứ AI | `sky-50` / `sky-900` | Khối thông tin bổ sung |

So với v1, ESI 3 chuyển từ vàng sang xanh dương để màu vàng/cam chỉ dành cho cảnh báo, còn ESI 5 chuyển sang màu trung tính. Khi đối chiếu token đang có trong `frontend/src/app/globals.css`, tôi phát hiện ở giao diện tối `--esi-5` dùng `#34d399` (xanh lá), trùng nhóm màu với ESI 4, trong khi giao diện sáng dùng slate. Đây là điểm cần thống nhất lại ở giai đoạn tích hợp.

### 11.3. Typography và khoảng cách

| Thành phần | Quy định |
|---|---|
| Font | Inter, tối đa 2 họ font |
| Body text | Tối thiểu 14–16px; giao diện người bệnh ưu tiên 16px |
| Dữ liệu quan trọng (mức ESI, triệu chứng chính, thời gian chờ) | 16–20px, đậm |
| Nhãn nhỏ | Không dùng dưới 14px cho thông tin cần đọc |
| Lưới khoảng cách | Bội số 8px: 8, 16, 24, 32, 40, 48 |
| Trong một thẻ | Tối đa 3 cỡ chữ và 2 độ đậm |

### 11.4. Checklist accessibility

- Vùng chạm tối thiểu 44 × 44px cho nút, thẻ lựa chọn và tab.
- Tương phản chữ tối thiểu 4,5:1 theo WCAG AA.
- Mọi điều khiển có trạng thái focus rõ ràng (`focus-visible:ring-2`).
- Cảnh báo khẩn dùng `role="alert"` và `aria-live="assertive"`; trạng thái chờ dùng `role="status"` và `aria-live="polite"`.
- Icon trang trí có `aria-hidden="true"`; nút chỉ có icon phải có `aria-label`.
- Animation tôn trọng `prefers-reduced-motion`.
- Mức nguy cơ không chỉ thể hiện bằng màu, luôn có chữ và icon.
- Nút gọi 115 dùng liên kết `tel:115` để mở trình quay số trên điện thoại.

---

## 12. ĐÁNH GIÁ NỘI BỘ BẰNG COGNITIVE WALKTHROUGH

Tôi tự thực hiện cognitive walkthrough trên wireframe v2 theo ba kịch bản ở mục 13. Đây là đánh giá chuyên gia nội bộ, không thay thế usability test với người dùng thật.

| Bước kiểm tra | Phát hiện | Điều chỉnh |
|---|---|---|
| Người dùng có biết phải làm gì khi thấy cảnh báo khẩn? | Nút “Tôi đã biết” cùng kích thước với nút gọi 115 có thể gây nhầm | Nút 115 dùng nền đỏ đặc, đặt đầu tiên; hai nút còn lại dạng viền |
| Người dùng có hiểu vì sao phải xác nhận thông tin? | Tiêu đề “Xác nhận” chưa nói rõ mục đích | Đổi thành “Kiểm tra lại thông tin trước khi gửi nhân viên y tế” |
| Người dùng có lo lắng khi phải chờ? | Màn hình chờ không có mốc tiến trình | Thêm 3 bước tiến trình và đồng hồ thời gian chờ |
| Điều dưỡng có nhận ra ca thiếu bằng chứng? | Ca thiếu bằng chứng trông giống ca thường | Thay ESI bằng nhãn “Chưa đủ căn cứ” và trạng thái “Thiếu dữ liệu” |
| Điều dưỡng có xác nhận nhầm khi chưa đọc đủ? | Form quyết định nằm cạnh khối tóm tắt | Đặt form sau 4 khối dữ liệu; điều chỉnh ESI bắt buộc chọn mã lý do |
| “Xác nhận đã thấy” cảnh báo có làm mất ca? | Có thể hiểu là đã xử lý xong | Thêm dòng “Xác nhận không xóa cảnh báo và không hoàn tất ca” |

---

## 13. KỊCH BẢN USABILITY TEST

### 13.1. Thiết kế phiên thử

- **Đối tượng dự kiến:** 5 người đóng vai người bệnh/người nhà và 3 người đóng vai nhân viên lâm sàng.
- **Hình thức:** think-aloud, có người điều phối, mỗi phiên khoảng 20–30 phút.
- **Dữ liệu:** chỉ dùng persona mô phỏng; không dùng triệu chứng hoặc thông tin cá nhân thật của người tham gia.
- **Đồng ý tham gia:** giải thích mục đích và quyền dừng bất cứ lúc nào; không ghi hình khuôn mặt.
- **Thời điểm:** kịch bản đã sẵn sàng trong tuần 5; phiên chính thức gắn với giai đoạn pilot (tuần 13) khi đã có bản alpha nối API thật.

### 13.2. Ba kịch bản chính

| Kịch bản | Persona và nhiệm vụ | Hành vi kỳ vọng |
|---|---|---|
| 1. Ca red flag | Người nhà khai cho bố 58 tuổi đau ngực, vã mồ hôi | Nhận ra cảnh báo và chạm nút gọi 115 mà không cần hướng dẫn |
| 2. Ca cần hỏi thêm | Người bệnh 34 tuổi đau bụng, trả lời mơ hồ | Trả lời từng câu hỏi, sửa một thông tin sai ở thẻ xác nhận |
| 3. Ca chuyển điều dưỡng | Điều dưỡng nhận ca “Chưa đủ căn cứ” | Nhận ca, nhập sinh hiệu, chọn ESI kèm lý do và lưu quyết định |

### 13.3. Chỉ số đo và ngưỡng đạt

| Chỉ số | Cách đo | Ngưỡng đạt đề xuất |
|---|---|---|
| Hoàn thành nhiệm vụ | Tỷ lệ người tự hoàn thành không cần gợi ý | ≥ 80% mỗi kịch bản |
| Nhận biết cảnh báo | Thời gian từ khi cảnh báo xuất hiện đến khi chạm nút 115 | Ghi nhận và phân tích; mọi người tham gia phải tìm thấy nút |
| Hiểu bước tiếp theo | Câu hỏi sau nhiệm vụ: “Bây giờ chuyện gì sẽ xảy ra?” | Trả lời đúng ý “chờ nhân viên y tế” |
| Hiểu sai phạm vi | Người tham gia cho rằng AI đã chẩn đoán | 0 trường hợp; nếu có thì sửa microcopy |
| Quy tắc 3 giây (điều dưỡng) | Xem hàng đợi 3 giây rồi trả lời ca nào cần nhận trước | Chọn đúng ca red flag |
| Mức độ dễ thực hiện | Single Ease Question thang 1–7 | Trung bình ≥ 5 |

Bất kỳ lỗi nào làm người dùng bỏ qua cảnh báo khẩn hoặc hiểu sai rằng AI đã chẩn đoán được xếp mức nghiêm trọng và phải sửa trước khi demo, kể cả khi các chỉ số khác đạt.

---

## 14. SẢN PHẨM VÀ MINH CHỨNG TUẦN 5

| Hạng mục | Minh chứng trong repository | Trạng thái |
|---|---|---|
| Wireframe v1 được audit | `docs/Wireframe_UI_Flow.md` | Tài liệu lịch sử, đã đánh dấu không còn là source of truth |
| Phạm vi và màn hình cổng điều dưỡng | `docs/NURSE_CORE_FUNCTIONAL_SCOPE_PLAN.md` | Baseline 2.0 |
| Quy tắc kỹ thuật và design system frontend | `.agents/rules/frontend-rules.md`, `.agents/skills/frontend-design/SKILL.md` | Đang áp dụng |
| Design token màu ESI, font, radius, theme | `frontend/src/app/globals.css` | Có; cần thống nhất `--esi-5` ở giao diện tối |
| Thanh tiến trình gắn `workflow_phase` | `frontend/src/components/chat/IntakeStepper.tsx` | Có |
| Thẻ cảnh báo khẩn trong hội thoại | `frontend/src/components/chat/RedFlagAlertCard.tsx` | Có |
| Nút SOS 115 cố định | `frontend/src/components/chat/EmergencyFloatingButton.tsx` | Có |
| Thẻ xác nhận thông tin | `frontend/src/components/chat/PatientIntakeReviewCard.tsx` | Có |
| Màn hình chờ thẩm định | `frontend/src/components/chat/HitlWaitingRoom.tsx` | Có |
| Tách nguồn có thẩm quyền và nguồn tham khảo | `frontend/src/components/chat/EvidenceSources.tsx` | Có |
| Hàng đợi và chi tiết ca | `frontend/src/components/clinical/nurse/NurseQueueWorkspace.tsx`, `NurseCaseWorkspace.tsx` | Có |
| Form quyết định 3 lựa chọn + mã lý do | `frontend/src/components/clinical/nurse/DecisionForm.tsx` | Có |
| Cảnh báo nguy cấp toàn cục | `frontend/src/components/clinical/nurse/GlobalRedFlagAlert.tsx` | Có |

Các thành phần trên là minh chứng cho việc thiết kế đã được chuyển thành cấu trúc giao diện có thể kiểm tra. Việc thành phần tồn tại không đồng nghĩa luồng end-to-end đã được nghiệm thu; tích hợp API thật thuộc kế hoạch tuần 6 và tuần 11.

---

## 15. KẾT QUẢ ĐẠT ĐƯỢC TRONG TUẦN 5

Trong tuần 5, tôi đã hoàn thành các nội dung sau:

- Audit wireframe v1 và phát hiện 11 vấn đề, trong đó 2 vấn đề nghiêm trọng liên quan đến nội dung mang tính chẩn đoán.
- Tính tương phản màu ESI của v1 và xác định 3/5 badge không đạt WCAG AA.
- Chốt 7 nguyên tắc thiết kế và quy tắc 3 giây cho cả hai vai trò.
- Xây dựng screen map v2 gồm 10 màn hình/thành phần phía người bệnh và 6 phía điều dưỡng; loại 5 hạng mục ra khỏi MVP.
- Vẽ user flow cho người bệnh và điều dưỡng, ánh xạ 10 giá trị `workflow_phase` vào 5 bước hiển thị.
- Thiết kế wireframe v2 cho 6 màn hình chính và so sánh hai phương án trình bày cảnh báo khẩn.
- Xây dựng ma trận hiển thị ESI, citation, `INSUFFICIENT_EVIDENCE`, SBAR, transcript và sinh hiệu theo vai trò.
- Chuẩn hóa microcopy theo nguyên tắc phân luồng, không chẩn đoán.
- Chốt design token, typography, lưới 8px và checklist accessibility.
- Thực hiện cognitive walkthrough nội bộ và điều chỉnh 6 điểm.
- Chuẩn bị kịch bản usability test với 3 kịch bản và 6 chỉ số đo.

---

## 16. KHÓ KHĂN VÀ CÁCH XỬ LÝ

| Khó khăn | Cách xử lý |
|---|---|
| Wireframe v1 được làm trước khi chốt evidence gate và HITL | Audit theo ràng buộc an toàn trước, không vẽ lại trực tiếp |
| Người bệnh muốn biết kết quả nhưng ESI chưa được duyệt | Hiển thị tiến trình và thời gian chờ thay cho ESI thô |
| Cảnh báo khẩn cần nổi bật nhưng không nên làm mất ngữ cảnh | Thẻ trong hội thoại + chip mở lại + nút SOS + cảnh báo song song cho điều dưỡng |
| Ca thiếu bằng chứng dễ bị xử lý như ca thường | Nhãn “Chưa đủ căn cứ”, không điền sẵn ESI, bắt buộc chọn lý do |
| Màn hình điều dưỡng ba cột quá tải thông tin | Chuyển sang luồng dọc 4 khối, thông tin dài đóng mặc định |
| Điểm tương đồng retrieval dễ bị hiểu là độ tin cậy | Không hiển thị phần trăm, chỉ dùng mức mô tả |
| Chưa có người dùng thật để kiểm tra | Dùng cognitive walkthrough nội bộ; chuẩn bị kịch bản cho pilot |

---

## 17. KẾ HOẠCH TUẦN 6

Trong tuần 6, tôi sẽ chuyển sang dựng backend nền tảng và hợp đồng dữ liệu, sử dụng trực tiếp các yêu cầu phát sinh từ thiết kế tuần 5:

- Khởi tạo cấu trúc FastAPI, DTO Pydantic v2 và health check.
- Thiết kế endpoint chat, hồ sơ, hàng đợi, nhận/trả ca và quyết định phân luồng.
- Tách `triage_status` (phiên AI) khỏi `review_status` (công việc điều dưỡng) trong data model.
- Bổ sung trường `data_completeness`, `case_version` chống ghi đè và nguồn/thời điểm cho từng sinh hiệu.
- Định nghĩa contract trả về `workflow_phase` để thanh tiến trình phản ánh trạng thái thật.
- Chuẩn hóa một namespace API duy nhất cho cổng lâm sàng.
- Xây dựng schema Zod phía frontend khớp với DTO backend.

---

## 18. KẾT LUẬN TUẦN 5

Tuần 5 cho thấy giao diện trong một hệ thống AI y tế không chỉ là lớp trình bày. Một wireframe tưởng như hợp lý vẫn có thể phá vỡ các nguyên tắc an toàn nếu nó gọi tên bệnh, công bố kết quả trước khi được duyệt hoặc hiển thị nguồn chưa qua kiểm tra thẩm quyền.

Nguyên tắc được chốt trong tuần này là: **giao diện phải nói đúng những gì hệ thống thực sự biết — không nhiều hơn bằng chứng, không sớm hơn quyết định của nhân viên y tế, và không chậm hơn khi có dấu hiệu nguy hiểm.**

---

## NGƯỜI LẬP BÁO CÁO

**Lê Hoàng Việt**  
Ký và ghi rõ họ tên: ____________________  
Ngày: ____ / ____ / 2026
