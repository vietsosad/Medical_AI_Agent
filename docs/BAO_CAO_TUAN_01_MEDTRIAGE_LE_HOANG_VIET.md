# BÁO CÁO TIẾN ĐỘ DỰ ÁN KHOA HỌC VÀ CÔNG NGHỆ

## TUẦN 1 — XÁC ĐỊNH BÀI TOÁN, PAIN POINT VÀ ĐỊNH HƯỚNG GIẢI PHÁP

**Tên đề tài:** MedTriage AI — Hệ thống hỗ trợ tiếp nhận và phân luồng ưu tiên y tế  
**Người thực hiện:** Lê Hoàng Việt  
**Tuần thực hiện:** Tuần 1/15  
**Thời gian:** 31/07/2026 – 02/08/2026  
**Trạng thái:** Hoàn thành giai đoạn khảo sát và định hướng

> **Lưu ý phạm vi:** Đây là báo cáo cá nhân của Lê Hoàng Việt trong tuần 1. Nội dung tuần này tập trung vào việc xác định vấn đề, phân tích nhu cầu và lập hướng nghiên cứu; chưa xem hệ thống là một sản phẩm y tế dùng trong thực tế.

---

## 1. MỤC TIÊU TUẦN 1

Trong tuần đầu tiên, tôi tập trung trả lời các câu hỏi nền tảng trước khi phát triển sản phẩm:

1. Vấn đề thực tế nào cần được giải quyết?
2. Người dùng đang gặp khó khăn gì trong quy trình hiện tại?
3. AI có thể hỗ trợ ở khâu nào và không được làm gì?
4. Sản phẩm cần những loại dữ liệu nào?
5. Dữ liệu sẽ được thu thập, chuẩn hóa và kiểm soát ra sao?
6. Làm thế nào để đề tài có thể triển khai trong phạm vi 15 tuần?

---

## 2. GIỚI THIỆU BÀI TOÁN

Trong quá trình tiếp nhận ban đầu, người bệnh thường mô tả triệu chứng bằng ngôn ngữ đời thường, không theo biểu mẫu y khoa cố định. Ví dụ, người bệnh có thể nói “tôi thấy tức ngực, hơi khó thở và mệt” thay vì cung cấp đầy đủ thời điểm khởi phát, mức độ, diễn biến hoặc các triệu chứng đi kèm.

Nhân viên tiếp nhận hoặc điều dưỡng cần nhanh chóng thu thập các dữ kiện quan trọng để xác định mức độ ưu tiên. Khi số lượng người bệnh tăng, quy trình hỏi đáp thủ công có thể gây ra một số vấn đề:

- Thời gian tiếp nhận kéo dài.
- Dữ liệu ban đầu không đồng nhất giữa các ca.
- Một số thông tin quan trọng có thể bị bỏ sót.
- Người bệnh không biết nên cung cấp thông tin nào trước.
- Nhân viên phải lặp lại nhiều câu hỏi cơ bản.

Từ đó, bài toán tôi lựa chọn là:

> **Xây dựng một hệ thống AI hỗ trợ tiếp nhận mô tả triệu chứng, đặt câu hỏi bổ sung có cấu trúc và đề xuất mức độ ưu tiên để nhân viên y tế kiểm tra, thay vì để AI tự chẩn đoán hoặc tự quyết định điều trị.**

Đây là bài toán hỗ trợ phân luồng ban đầu, không phải bài toán chẩn đoán bệnh.

---

## 3. PHÂN TÍCH PAIN POINT

### 3.1. Pain point của người bệnh và người nhà

**Pain point 1 — Không biết phải mô tả triệu chứng như thế nào**  
Người dùng thường không biết thông tin nào là quan trọng, dẫn đến mô tả dài nhưng thiếu dữ kiện cần thiết.

**Pain point 2 — Khó xác định mức độ khẩn cấp**  
Người dùng có thể không biết khi nào cần gọi cấp cứu, đến bệnh viện ngay hoặc đặt lịch khám thông thường.

**Pain point 3 — Phải trả lời các câu hỏi lặp lại**  
Nếu quy trình chỉ dựa trên checklist cứng, hệ thống có thể hỏi lại thông tin mà người dùng đã cung cấp.

**Pain point 4 — Khó hiểu thuật ngữ chuyên môn**  
Các câu hỏi hoặc hướng dẫn quá nhiều thuật ngữ y khoa có thể làm người dùng trả lời sai hoặc bỏ cuộc.

### 3.2. Pain point của nhân viên tiếp nhận và điều dưỡng

**Pain point 1 — Khối lượng tiếp nhận lớn**  
Nhân viên phải xử lý nhiều ca trong thời gian ngắn, đặc biệt ở các thời điểm đông người bệnh.

**Pain point 2 — Thông tin đầu vào thiếu cấu trúc**  
Một cuộc hội thoại tự do nếu không được chuẩn hóa sẽ khó chuyển thành hồ sơ để kiểm tra.

**Pain point 3 — Khó truy lại lý do phân luồng**  
Nếu kết quả không có bằng chứng hoặc tiêu chí đi kèm, nhân viên khó biết hệ thống đã dựa vào thông tin nào.

**Pain point 4 — Rủi ro khi dùng chatbot tổng quát**  
Chatbot có thể tạo ra câu trả lời nghe hợp lý nhưng không có nguồn, tự chẩn đoán hoặc đưa ra hướng dẫn không phù hợp.

---

## 4. ĐỐI TƯỢNG SỬ DỤNG DỰ KIẾN

### 4.1. Người bệnh hoặc người nhà

Người nhập triệu chứng cho bản thân hoặc cho người thân. Họ cần một giao diện dễ hiểu, câu hỏi ngắn gọn và hướng dẫn rõ ràng về bước tiếp theo.

### 4.2. Điều dưỡng hoặc nhân viên tiếp nhận

Người xem lại thông tin do hệ thống thu thập, kiểm tra các dữ kiện, bổ sung thông tin cần thiết và xác nhận mức độ ưu tiên.

### 4.3. Người quản lý hoặc người đánh giá hệ thống

Người theo dõi số lượng ca, kết quả phân luồng, thời gian xử lý, lỗi và chất lượng dữ liệu. Trong phạm vi tuần 1, nhóm đối tượng này chỉ được ghi nhận ở mức nhu cầu tương lai.

---

## 5. GIẢI PHÁP ĐỀ XUẤT

### 5.1. Ý tưởng sản phẩm

MedTriage AI là một ứng dụng web hỗ trợ người dùng mô tả triệu chứng bằng tiếng Việt tự nhiên. Hệ thống sẽ phân tích thông tin đã nhập, xác định dữ kiện còn thiếu, hỏi bổ sung từng ý và đối chiếu các dữ kiện với kho tiêu chí phân luồng.

Kết quả của AI chỉ là **đề xuất hỗ trợ**. Điều dưỡng hoặc nhân viên y tế vẫn là người kiểm tra và đưa ra quyết định chính thức.

### 5.2. Luồng hoạt động dự kiến

```text
Người dùng nhập triệu chứng
            │
            ▼
Kiểm tra dấu hiệu nguy hiểm ban đầu
            │
            ├── Có dấu hiệu nguy kịch → cảnh báo khẩn cấp, hướng dẫn gọi 115
            │
            └── Chưa phát hiện dấu hiệu nguy kịch
                         │
                         ▼
              Trích xuất dữ kiện triệu chứng
                         │
                         ▼
               Hỏi bổ sung dữ kiện còn thiếu
                         │
                         ▼
             Đối chiếu tiêu chí ESI có nguồn
                         │
                         ▼
          Tạo đề xuất và chuyển nhân viên kiểm tra
```

### 5.3. Định hướng nguyên tắc kỹ thuật

Trong tuần 1, tôi xác định bốn nguyên tắc nền tảng cho giải pháp:

1. **LLM dùng để hiểu và diễn đạt:** mô hình có thể đọc câu tiếng Việt tự nhiên và tạo câu hỏi dễ hiểu.
2. **Logic quyết định phải kiểm soát được:** không để mô hình ngôn ngữ tự ý chọn mức độ ưu tiên mà không có căn cứ.
3. **Có bằng chứng mới được đề xuất:** mỗi đề xuất cần truy lại được dữ kiện và tiêu chí nguồn.
4. **Thiếu căn cứ thì dừng an toàn:** nếu không đủ dữ liệu hoặc không truy xuất được nguồn, hệ thống phải thông báo chưa đủ dữ kiện thay vì suy đoán.

---

## 6. HƯỚNG ĐI VÀ CÁCH LẤY DỮ LIỆU

### 6.1. Các nhóm dữ liệu cần chuẩn bị

| Nhóm dữ liệu | Mục đích sử dụng | Định hướng thu thập |
|---|---|---|
| Tài liệu/phác đồ phân luồng | Làm căn cứ cho các tiêu chí ESI | Chọn tài liệu y khoa có nguồn, ghi rõ tên, phiên bản và phạm vi sử dụng |
| Khái niệm và từ đồng nghĩa | Hiểu các cách diễn đạt khác nhau của người dùng | Biên soạn các thuật ngữ tiếng Việt, tiếng Anh và cách nói đời thường |
| Dữ kiện cần hỏi | Xác định hệ thống cần hỏi thêm điều gì | Thiết kế theo từng nhóm triệu chứng và tiêu chí phân luồng |
| Ca mô phỏng đánh giá | Kiểm thử hội thoại và kết quả | Tạo các ca có nhãn chuẩn, dữ kiện đầu vào, expected output và lý do |
| Dữ liệu phản hồi người dùng | Đánh giá tính dễ dùng | Thu thập sau khi có prototype, không dùng để tự động thay đổi tiêu chí y khoa |

### 6.2. Quy trình lấy và chuẩn hóa dữ liệu dự kiến

**Bước 1 — Xác định phạm vi triệu chứng**  
Trong giai đoạn đầu, lựa chọn một số nhóm triệu chứng tiêu biểu như đau ngực, khó thở, đau bụng, đau đầu và sốt cao. Chưa mở rộng quá nhiều nhóm khi chưa kiểm soát được chất lượng.

**Bước 2 — Tìm nguồn có thẩm quyền**  
Ưu tiên các tài liệu hướng dẫn phân luồng, tài liệu đào tạo hoặc phác đồ có thông tin xuất bản rõ ràng. Mỗi nội dung đưa vào hệ thống phải lưu nguồn, phiên bản và ngày cập nhật.

**Bước 3 — Chuyển tài liệu thành cấu trúc dữ liệu**  
Tách tài liệu thành các tiêu chí nhỏ, ví dụ: điều kiện, dữ kiện cần hỏi, mức độ ưu tiên, nguồn trích dẫn và ghi chú giới hạn.

**Bước 4 — Xây dựng dữ liệu ngôn ngữ**  
Bổ sung cách người dùng có thể diễn đạt cùng một triệu chứng. Ví dụ, các cách nói như “tức ngực”, “nặng ngực”, “đè ở ngực” cần được xem xét như các alias để hệ thống có thể tìm đúng khái niệm.

**Bước 5 — Tạo benchmark mô phỏng**  
Tạo các tình huống hội thoại đại diện cho ca khẩn cấp, ca cần hỏi thêm, ca ít khẩn cấp và ca không đủ thông tin. Mỗi tình huống phải có đáp án tham chiếu và lý do.

**Bước 6 — Kiểm tra và version hóa**  
Kiểm tra trùng lặp, thiếu trường, sai liên kết và khả năng truy ngược nguồn. Dữ liệu cần được lưu theo phiên bản để biết thay đổi nào đã được thực hiện.

### 6.3. Nguyên tắc sử dụng dữ liệu

- Không dùng dữ liệu bệnh nhân thật nếu chưa được ẩn danh và cho phép phù hợp.
- Không coi dữ liệu do AI sinh ra là nguồn y khoa gốc.
- Dữ liệu mô phỏng chỉ dùng cho phát triển và đánh giá kỹ thuật.
- Không dùng kết quả benchmark nhỏ để tuyên bố hiệu quả lâm sàng.
- Mọi nội dung y khoa cần được rà soát chuyên môn trước khi sử dụng ngoài mục đích nghiên cứu.

---

## 7. PHƯƠNG PHÁP THỰC HIỆN DỰ KIẾN

Trong 15 tuần, tôi dự kiến triển khai đề tài theo các giai đoạn:

1. **Tuần 1–2:** xác định bài toán, yêu cầu, đối tượng và giới hạn.
2. **Tuần 3–4:** chuẩn bị nguồn dữ liệu, ontology và benchmark ban đầu.
3. **Tuần 5–6:** thiết kế giao diện và dựng nền tảng backend.
4. **Tuần 7–10:** phát triển agent hội thoại, logic phân luồng, RAG và luồng kiểm tra của điều dưỡng.
5. **Tuần 11–13:** tích hợp, kiểm thử và đánh giá với các ca mô phỏng.
6. **Tuần 14–15:** hoàn thiện tài liệu, đóng gói demo và viết báo cáo tổng kết.

### Công nghệ định hướng

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS.
- **Backend:** FastAPI, Python, Pydantic.
- **Cơ sở dữ liệu:** PostgreSQL và pgvector.
- **AI/RAG:** mô hình ngôn ngữ, embedding, truy xuất theo metadata và vector.
- **Đánh giá:** unit test, integration test, benchmark hội thoại và các chỉ số phân loại/RAG.

---

## 8. KẾT QUẢ ĐẠT ĐƯỢC TRONG TUẦN 1

Sau tuần đầu tiên, tôi đã hoàn thành các nội dung định hướng sau:

- Xác định tên và phạm vi đề tài MedTriage AI.
- Mô tả được bài toán tiếp nhận và phân luồng ưu tiên ban đầu.
- Phân tích pain point của người bệnh và nhân viên tiếp nhận.
- Xác định nhóm người dùng dự kiến.
- Đề xuất giải pháp AI hỗ trợ hỏi đáp và phân luồng có kiểm soát.
- Chốt giới hạn: không chẩn đoán, không kê đơn, không thay thế nhân viên y tế.
- Xác định bốn nhóm dữ liệu cần chuẩn bị: guideline, ontology/alias, fact targets và benchmark.
- Đề xuất quy trình lấy, chuẩn hóa, kiểm tra và version hóa dữ liệu.
- Xây dựng định hướng triển khai cho 15 tuần tiếp theo.

Ở tuần 1, tôi chưa đánh giá độ chính xác của mô hình và chưa đưa ra kết luận về hiệu quả lâm sàng. Các chỉ số kỹ thuật chỉ được xem xét sau khi có prototype, dataset và quy trình đánh giá rõ ràng.

---

## 9. KHÓ KHĂN VÀ CÁCH XỬ LÝ

| Khó khăn | Cách xử lý trong tuần 1 |
|---|---|
| Bài toán y tế có rủi ro cao nếu mô tả quá rộng | Thu hẹp thành hỗ trợ phân luồng, không chẩn đoán |
| Dữ liệu y tế khó thu thập và khó xác minh | Xác định nguồn có thẩm quyền, lưu metadata và không dùng dữ liệu AI sinh làm nguồn gốc |
| Khó cân bằng giữa hội thoại tự nhiên và tính kiểm soát | Phân tách vai trò: LLM hiểu/diễn đạt, code và dữ liệu kiểm soát quyết định |
| Có thể nhầm đề xuất AI với kết luận y khoa | Đưa HITL, disclaimer và cơ chế fail-closed vào yêu cầu ngay từ đầu |

---

## 10. KẾ HOẠCH TUẦN 2

Trong tuần 2, tôi sẽ chuyển kết quả khảo sát của tuần 1 thành đặc tả cụ thể:

- Hoàn thiện PRD và các use case chính.
- Xác định input/output cho từng bước trong luồng người dùng.
- Thiết kế schema ban đầu cho concept, fact, protocol và session.
- Lập danh sách nguồn dữ liệu ưu tiên.
- Viết các tiêu chí nghiệm thu và nhóm test case đầu tiên.
- Phác thảo wireframe cho màn hình người dùng và màn hình nhân viên tiếp nhận.

---

## 11. KẾT LUẬN TUẦN 1

Tuần 1 đã giúp tôi xác định rõ MedTriage AI không phải là chatbot chẩn đoán, mà là một hệ thống hỗ trợ thu thập thông tin và phân luồng ưu tiên ban đầu. Giá trị cốt lõi của đề tài nằm ở việc kết hợp hội thoại tự nhiên với dữ liệu có nguồn, logic có thể kiểm tra và sự xác nhận của nhân viên y tế.

Định hướng quan trọng nhất được chốt trong tuần này là: **AI chỉ hỗ trợ hiểu và hỏi; quyết định phải dựa trên bằng chứng, có giới hạn an toàn và được con người kiểm tra.**

---

## NGƯỜI LẬP BÁO CÁO

**Lê Hoàng Việt**  
Ký và ghi rõ họ tên: ____________________  
Ngày: ____ / ____ / 2026
