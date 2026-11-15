# BÁO CÁO TIẾN ĐỘ DỰ ÁN KHOA HỌC VÀ CÔNG NGHỆ

## TUẦN 2 — ĐẶC TẢ YÊU CẦU, LUỒNG NGHIỆP VỤ VÀ TIÊU CHÍ AN TOÀN

**Tên đề tài:** MedTriage AI — Hệ thống hỗ trợ tiếp nhận và phân luồng ưu tiên y tế  
**Người thực hiện:** Lê Hoàng Việt  
**Tuần thực hiện:** Tuần 2/15  
**Thời gian:** 03/08/2026 – 09/08/2026  
**Báo cáo liên kết:** Báo cáo Tuần 1 — Xác định bài toán, pain point và định hướng giải pháp  
**Trạng thái:** Hoàn thành giai đoạn đặc tả ban đầu

> **Lưu ý phạm vi:** Đây là báo cáo cá nhân của Lê Hoàng Việt. Tuần 2 tập trung chuyển kết quả khảo sát của tuần 1 thành yêu cầu, luồng xử lý và tiêu chí kiểm thử. Hệ thống vẫn chỉ là nguyên mẫu phục vụ học tập và nghiên cứu, không phải công cụ chẩn đoán hoặc điều trị.

---

## 1. MỤC TIÊU TUẦN 2

Sau khi đã xác định bài toán và hướng giải pháp trong tuần 1, mục tiêu của tuần 2 là làm rõ sản phẩm cần làm gì, không làm gì và phải hoạt động như thế nào.

Các mục tiêu cụ thể:

1. Chuyển problem statement thành yêu cầu sản phẩm có thể kiểm thử.
2. Xác định các đối tượng sử dụng và use case chính.
3. Mô tả luồng nghiệp vụ từ lúc người dùng nhập triệu chứng đến khi nhân viên y tế kiểm tra.
4. Xác định input, output và trạng thái của một phiên triage.
5. Đặt ra các yêu cầu an toàn bắt buộc cho hệ thống.
6. Thiết kế schema dữ liệu ban đầu cho concept, fact, protocol và session.
7. Xây dựng tiêu chí nghiệm thu và nhóm test case đầu tiên.

---

## 2. CÔNG VIỆC ĐÃ THỰC HIỆN

### 2.1. Hoàn thiện đặc tả bài toán

Tôi cụ thể hóa bài toán của MedTriage AI thành ba nhu cầu chính:

- Người dùng cần mô tả triệu chứng bằng ngôn ngữ tự nhiên mà không phải hiểu thuật ngữ y khoa.
- Hệ thống cần xác định các dữ kiện còn thiếu và hỏi bổ sung theo thứ tự hợp lý.
- Nhân viên y tế cần nhận được một đề xuất có cấu trúc, có lý do và có thể kiểm tra lại.

Từ đó, mục tiêu của sản phẩm được giới hạn ở **hỗ trợ tiếp nhận và phân luồng ưu tiên ban đầu**. Sản phẩm không có mục tiêu xác định tên bệnh, kê đơn hoặc thay thế việc thăm khám.

### 2.2. Xác định yêu cầu theo vai trò người dùng

#### Người bệnh/người nhà

- Bắt đầu một phiên tiếp nhận.
- Nhập triệu chứng bằng văn bản tự do.
- Trả lời câu hỏi bổ sung.
- Khai báo đang nói cho bản thân hay cho người khác.
- Xem cảnh báo khẩn cấp và hướng dẫn bước tiếp theo.
- Xác nhận lại thông tin trước khi chuyển ca.

#### Điều dưỡng/nhân viên tiếp nhận

- Xem danh sách ca đang chờ.
- Nhận một ca để xử lý.
- Xem thông tin người dùng, transcript, facts và nguồn đối chiếu.
- Bổ sung thông tin cần thiết.
- Xác nhận hoặc điều chỉnh đề xuất ESI.
- Ghi rõ lý do nếu điều chỉnh kết quả.

#### Người quản lý hệ thống

Trong phạm vi thiết kế ban đầu, người quản lý chỉ được xem xét ở mức yêu cầu tương lai: theo dõi số lượng ca, thời gian xử lý, trạng thái hệ thống và chất lượng dữ liệu. Chưa mở rộng thành một module quản trị hoàn chỉnh trong tuần 2.

### 2.3. Xác định luồng nghiệp vụ chính

```text
1. Người dùng mở phiên triage
              │
2. Nhập triệu chứng ban đầu
              │
3. Kiểm tra đầu vào và dấu hiệu nguy hiểm
              │
      ┌───────┴────────┐
      │                │
 Có dấu hiệu khẩn   Chưa thấy dấu hiệu khẩn
      │                │
 Cảnh báo 115      Trích xuất facts đã biết
                     │
              Còn facts bắt buộc?
                     │
          ┌──────────┴──────────┐
          │                     │
        Còn thiếu              Đủ dữ kiện
          │                     │
    Hỏi bổ sung          Đối chiếu protocol
                                │
                      Tạo đề xuất ESI/SBAR
                                │
                         Điều dưỡng kiểm tra
                                │
                    Xác nhận hoặc điều chỉnh
```

### 2.4. Phân tách trách nhiệm của AI và con người

Trong tuần 2, tôi chốt ranh giới trách nhiệm như sau:

| Thành phần | Được phép thực hiện | Không được phép thực hiện |
|---|---|---|
| LLM | Hiểu câu tiếng Việt, trích xuất thông tin, diễn đạt câu hỏi | Tự chọn ESI không có căn cứ |
| Bộ truy xuất | Tìm protocol/fact có liên quan và nguồn trích dẫn | Tự thay đổi nội dung nguồn |
| Logic tất định | Kiểm tra điều kiện, đối chiếu facts và xác định trạng thái | Suy diễn vượt quá dữ liệu đã khai báo |
| Điều dưỡng | Kiểm tra hồ sơ, bổ sung thông tin, xác nhận hoặc điều chỉnh | Bị buộc phải chấp nhận kết quả AI |

---

## 3. ĐẶC TẢ YÊU CẦU CHỨC NĂNG

### 3.1. Nhóm yêu cầu tiếp nhận

| Mã | Yêu cầu | Kết quả mong đợi |
|---|---|---|
| FR-01 | Tạo phiên triage | Hệ thống tạo một `session_id` và trạng thái ban đầu |
| FR-02 | Nhận tin nhắn tự do | Tin nhắn được lưu cùng thời điểm và phiên tương ứng |
| FR-03 | Xác định đối tượng | Ghi nhận người dùng đang khai cho bản thân hay người khác |
| FR-04 | Trích xuất facts | Facts có nguồn từ tin nhắn hoặc câu trả lời đã xác nhận |
| FR-05 | Hỏi bổ sung | Mỗi lượt ưu tiên một câu hỏi chính, tránh hỏi lại dữ kiện đã có |
| FR-06 | Kết thúc phiên | Phiên có trạng thái rõ ràng: đang hỏi, cảnh báo khẩn, chờ xác nhận hoặc hoàn tất |

### 3.2. Nhóm yêu cầu phân luồng

| Mã | Yêu cầu | Kết quả mong đợi |
|---|---|---|
| FR-07 | Phát hiện dấu hiệu nguy hiểm | Nếu khớp điều kiện nguy cấp, hiển thị cảnh báo ưu tiên |
| FR-08 | Đối chiếu tiêu chí | Chỉ sử dụng protocol/fact đã được hệ thống xác thực |
| FR-09 | Trả về trạng thái chưa đủ dữ liệu | Không kết luận khi chưa có bằng chứng phù hợp |
| FR-10 | Tạo đề xuất ESI | Đề xuất kèm lý do, facts liên quan và citation |
| FR-11 | Tạo SBAR | Tóm tắt có cấu trúc để nhân viên y tế xem lại |
| FR-12 | Chuyển ca cho nhân viên | Ca được đưa vào hàng đợi cùng trạng thái chờ xử lý |

### 3.3. Nhóm yêu cầu dành cho điều dưỡng

| Mã | Yêu cầu | Kết quả mong đợi |
|---|---|---|
| FR-13 | Xem hàng đợi | Có thể lọc và xem các ca đang chờ |
| FR-14 | Nhận ca | Một nhân viên có thể claim ca để xử lý |
| FR-15 | Xem bằng chứng | Có transcript, facts, tiêu chí và citation |
| FR-16 | Xác nhận kết quả | Lưu quyết định cuối cùng và người thực hiện |
| FR-17 | Điều chỉnh kết quả | Bắt buộc ghi lý do override |

---

## 4. YÊU CẦU PHI CHỨC NĂNG VÀ AN TOÀN

### 4.1. An toàn lâm sàng

- Kiểm tra red flag trước khi chờ mô hình ngôn ngữ.
- Không dùng LLM làm nguồn duy nhất để quyết định ESI.
- Không tạo output chẩn đoán hoặc kê đơn.
- Nếu thiếu dữ liệu, thiếu nguồn hoặc validation lỗi thì trả về trạng thái an toàn.
- Cảnh báo nguy hiểm phải có hướng dẫn rõ ràng, trong đó tình huống khẩn cấp cần gọi 115.
- Đề xuất không khẩn cấp phải có provenance để nhân viên kiểm tra.
- Kết quả cuối cùng phải có bước xác nhận của điều dưỡng hoặc nhân viên có thẩm quyền.

### 4.2. Bảo mật và quyền riêng tư

- Chỉ thu thập dữ liệu cần thiết cho phiên triage.
- Không đưa thông tin nhận diện cá nhân thật vào benchmark.
- Không ghi thông tin nhạy cảm vào log nếu không cần thiết.
- Phân tách quyền xem dữ liệu người dùng và quyền xử lý ca.
- Có thể xóa hoặc ẩn danh dữ liệu thử nghiệm khi kết thúc đánh giá.

### 4.3. Tính dễ sử dụng

- Câu hỏi hiển thị ngắn, rõ và ưu tiên một ý chính.
- Không yêu cầu người dùng hiểu thuật ngữ ESI.
- Cảnh báo nguy hiểm phải nổi bật và không bị lẫn với nội dung thông thường.
- Người dùng luôn biết hệ thống đang hỏi thêm, đang chờ xác nhận hay đã chuyển ca.
- Giao diện điều dưỡng ưu tiên transcript, facts, citation và thao tác xác nhận.

### 4.4. Tính kiểm thử và quan sát

- Mỗi yêu cầu chức năng phải có ít nhất một test case.
- Các quyết định quan trọng phải lưu được facts, protocol và thời điểm xử lý.
- Số liệu đánh giá phải gắn với dataset, phiên bản code và thời điểm chạy.
- Lỗi của model, retrieval hoặc database không được hiển thị thành stack trace cho người dùng.

---

## 5. THIẾT KẾ TRẠNG THÁI VÀ DỮ LIỆU BAN ĐẦU

### 5.1. Trạng thái một phiên triage

| Trạng thái | Ý nghĩa | Chuyển tiếp có thể có |
|---|---|---|
| `STARTED` | Phiên vừa được tạo | Nhận tin nhắn đầu tiên |
| `COLLECTING` | Đang thu thập hoặc hỏi bổ sung | Hỏi tiếp, cảnh báo hoặc đánh giá |
| `EMERGENCY` | Có tín hiệu nguy hiểm cần xử lý ngay | Hiển thị hướng dẫn khẩn cấp |
| `INCOMPLETE` | Chưa đủ dữ kiện hoặc chưa có bằng chứng phù hợp | Thu thập thêm hoặc chuyển nhân viên |
| `PENDING_REVIEW` | Đã có đề xuất và chờ nhân viên kiểm tra | Claim, xác nhận hoặc override |
| `CONFIRMED` | Nhân viên đã lưu quyết định cuối | Kết thúc phiên hoặc theo dõi |

### 5.2. Các thực thể dữ liệu chính

| Thực thể | Trường dữ liệu dự kiến | Mục đích |
|---|---|---|
| `Session` | ID, người dùng, trạng thái, thời gian tạo/cập nhật | Quản lý vòng đời phiên |
| `Message` | ID, session, vai trò, nội dung, thời gian | Lưu transcript |
| `ClinicalConcept` | ID, tên, alias, ngôn ngữ | Chuẩn hóa cách diễn đạt |
| `FactTarget` | ID, câu hỏi, kiểu dữ liệu, concept liên quan | Xác định dữ kiện cần hỏi |
| `SessionFact` | session, fact target, giá trị, nguồn, độ chắc chắn | Lưu dữ kiện đã khai báo |
| `ProtocolAtom` | ID, điều kiện, mức ESI, citation, phiên bản | Căn cứ đối chiếu |
| `TriageProposal` | session, mức đề xuất, lý do, evidence | Lưu kết quả hỗ trợ |
| `NurseDecision` | người xử lý, kết quả, lý do, thời gian | Lưu xác nhận/override |

### 5.3. Quy tắc dữ liệu ban đầu

1. Không tạo `concept_id` hoặc `fact_target_id` nếu ID đó không tồn tại trong kho dữ liệu.
2. Một fact phải có nguồn là tin nhắn, câu trả lời đã xác nhận hoặc dữ liệu được nhân viên bổ sung.
3. Protocol atom phải có citation và phiên bản.
4. Không dùng nội dung diễn đạt của LLM làm bằng chứng lâm sàng.
5. Nếu một fact bị mâu thuẫn, hệ thống phải giữ trạng thái cần làm rõ thay vì tự chọn giá trị.

---

## 6. USE CASE CHÍNH

### UC-01 — Người dùng mô tả triệu chứng

**Actor:** Người bệnh/người nhà  
**Tiền điều kiện:** Có phiên triage đang hoạt động  
**Luồng chính:**

1. Người dùng nhập mô tả triệu chứng bằng tiếng Việt.
2. Hệ thống lưu tin nhắn.
3. Hệ thống trích xuất những facts có thể xác định.
4. Hệ thống trả lời xác nhận hoặc hỏi thêm một dữ kiện.

**Ngoại lệ:** Nếu đầu vào chứa tín hiệu nguy hiểm, hệ thống chuyển sang UC-02.

### UC-02 — Xử lý tín hiệu nguy hiểm

**Actor:** Người bệnh/người nhà  
**Luồng chính:**

1. Hệ thống phát hiện cụm từ hoặc điều kiện nguy hiểm.
2. Luồng chat thông thường được ưu tiên dừng.
3. Giao diện hiển thị cảnh báo rõ ràng.
4. Hệ thống hướng dẫn người dùng gọi 115 hoặc tìm trợ giúp khẩn cấp.

**Yêu cầu:** Không chờ câu trả lời dài của LLM trước khi hiển thị cảnh báo.

### UC-03 — Hệ thống hỏi bổ sung dữ kiện

**Actor:** Hệ thống  
**Luồng chính:**

1. Hệ thống xác định protocol/fact còn thiếu.
2. Chọn câu hỏi có mức ưu tiên cao nhất.
3. Hiển thị câu hỏi bằng ngôn ngữ dễ hiểu.
4. Lưu câu trả lời và cập nhật session state.

**Ngoại lệ:** Nếu người dùng không hiểu hoặc trả lời mâu thuẫn, hệ thống chuyển sang trạng thái cần làm rõ.

### UC-04 — Điều dưỡng xác nhận đề xuất

**Actor:** Điều dưỡng/nhân viên tiếp nhận  
**Luồng chính:**

1. Nhân viên mở hàng đợi.
2. Nhận một ca.
3. Xem transcript, facts, protocol và citation.
4. Giữ nguyên hoặc điều chỉnh mức đề xuất.
5. Lưu quyết định cùng người thực hiện và lý do.

---

## 7. TIÊU CHÍ NGHIỆM THU BAN ĐẦU

| Mã | Tiêu chí | Cách kiểm tra |
|---|---|---|
| AC-01 | Người dùng tạo được phiên mới | Gọi API hoặc thao tác trên giao diện |
| AC-02 | Tin nhắn được lưu đúng phiên | Kiểm tra database và lịch sử chat |
| AC-03 | Hệ thống không hỏi lại fact đã xác nhận | Chạy hội thoại có thông tin lặp |
| AC-04 | Cảnh báo nguy hiểm được ưu tiên | Chạy ca có red flag |
| AC-05 | Không kết luận khi thiếu evidence | Chạy ca thiếu dữ kiện hoặc lỗi retrieval |
| AC-06 | Mỗi đề xuất có lý do và nguồn | Kiểm tra proposal/evidence |
| AC-07 | Nhân viên xem được đầy đủ hồ sơ | Chạy luồng queue → claim → detail |
| AC-08 | Override bắt buộc có lý do | Thử lưu decision không có reason |
| AC-09 | Không trả lời chẩn đoán/kê đơn | Chạy bộ câu hỏi adversarial |
| AC-10 | Lỗi kỹ thuật không lộ stack trace | Tắt dependency hoặc gửi payload lỗi |

### Bộ test case khởi đầu

- **TC-01:** Ca có dấu hiệu nguy hiểm rõ ràng.
- **TC-02:** Ca mô tả triệu chứng ngắn, cần hỏi thêm.
- **TC-03:** Ca đã cung cấp đủ dữ kiện ngay ở tin nhắn đầu.
- **TC-04:** Người dùng khai báo cho người thân.
- **TC-05:** Người dùng trả lời mâu thuẫn.
- **TC-06:** Người dùng hỏi “tôi bị bệnh gì?”
- **TC-07:** Người dùng yêu cầu kê thuốc.
- **TC-08:** Kho dữ liệu không có protocol phù hợp.
- **TC-09:** Nhân viên điều dưỡng điều chỉnh đề xuất.
- **TC-10:** Phiên bị gián đoạn và cần khôi phục trạng thái.

---

## 8. KẾT QUẢ ĐẠT ĐƯỢC TRONG TUẦN 2

Trong tuần 2, tôi đã hoàn thành các đầu ra sau:

- Chuyển problem statement của tuần 1 thành đặc tả yêu cầu ban đầu.
- Xác định rõ ba nhóm người dùng và trách nhiệm của từng nhóm.
- Mô tả luồng nghiệp vụ từ tiếp nhận triệu chứng đến điều dưỡng xác nhận.
- Phân tách trách nhiệm giữa LLM, bộ truy xuất, logic tất định và con người.
- Xác định các yêu cầu chức năng chính cho phiên triage, phân luồng và hàng đợi điều dưỡng.
- Xác định các yêu cầu phi chức năng về an toàn, bảo mật, khả năng sử dụng và kiểm thử.
- Thiết kế trạng thái phiên và các thực thể dữ liệu ban đầu.
- Viết bốn use case chính.
- Xây dựng tiêu chí nghiệm thu và mười test case khởi đầu.

Kết quả tuần 2 tạo thành cơ sở để sang tuần 3 thiết kế chi tiết kho dữ liệu, ontology và pipeline truy xuất.

---

## 9. KHÓ KHĂN VÀ CÁCH XỬ LÝ

| Khó khăn | Cách xử lý |
|---|---|
| Dễ mở rộng phạm vi sang chẩn đoán hoặc điều trị | Ghi rõ out-of-scope trong yêu cầu và acceptance criteria |
| Khó mô tả hội thoại tự nhiên bằng các trạng thái cố định | Dùng state machine tối thiểu, cho phép trạng thái `INCOMPLETE` và `PENDING_REVIEW` |
| AI có thể tạo câu trả lời trôi chảy nhưng thiếu căn cứ | Tách LLM khỏi quyết định, bắt buộc evidence/citation |
| Dữ liệu người dùng có thể mâu thuẫn | Không tự ghi đè; chuyển sang trạng thái cần làm rõ |
| Cảnh báo nguy hiểm bị trộn với hội thoại thông thường | Thiết kế red-flag reflex là luồng ưu tiên riêng |

---

## 10. KẾ HOẠCH TUẦN 3

Trong tuần 3, tôi sẽ tập trung vào cơ sở dữ liệu và kho tri thức:

- Chốt cấu trúc metadata cho guideline và protocol atom.
- Xác định taxonomy nhóm triệu chứng.
- Xây dựng danh sách concept, alias và fact target ban đầu.
- Thiết kế quy tắc citation và versioning của corpus.
- Chuẩn bị dữ liệu mẫu cho một số nhóm triệu chứng ưu tiên.
- Kiểm tra khả năng truy xuất dữ liệu theo từ khóa và ngữ nghĩa.

---

## 11. KẾT LUẬN TUẦN 2

Tuần 2 đã chuyển đề tài từ một ý tưởng tổng quát thành một sản phẩm có phạm vi, vai trò, luồng nghiệp vụ và tiêu chí kiểm thử cụ thể. Việc đặc tả sớm giúp kiểm soát rủi ro của bài toán y tế và tránh phát triển một chatbot có phạm vi quá rộng.

Kết luận quan trọng của tuần này là: **một phiên triage phải luôn có trạng thái rõ ràng, một đề xuất phải có bằng chứng, và quyết định cuối cùng phải thuộc về con người có trách nhiệm chuyên môn.**

---

## NGƯỜI LẬP BÁO CÁO

**Lê Hoàng Việt**  
Ký và ghi rõ họ tên: ____________________  
Ngày: ____ / ____ / 2026
