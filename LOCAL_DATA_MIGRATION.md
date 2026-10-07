# Hướng Dẫn Migrate Local Data Đồng Bộ Với Production

## Bối cảnh cập nhật
Chúng ta vừa hoàn tất quá trình **Deployment Cleanup** chuẩn bị cho Production. Các cập nhật chính bao gồm:
1. **Loại bỏ Local Embedding Model (BGE-M3):** Code không còn bake/download thư viện model vector nặng nề, giảm tải cho môi trường và bỏ qua mô hình fallback cũ.
2. **Loại bỏ Legacy RAG Tables:** Các bảng dữ liệu cũ là `triageknowledgebase`, `triage_case_examples`, và `triage_protocol_documents` đã bị xoá khỏi kiến trúc hệ thống (`db_models.py`).
3. **Tiêu chuẩn hoá RAG:** Hệ thống RAG hiện tại chỉ truy vấn vào 2 bảng có cấu trúc chuẩn 1024-dimension: 
   - `esi_knowledge_documents` (Cho Clinical Authority)
   - `mietic_cases` (Cho Case Support)

Vì các model legacy đã bị xoá, nếu bạn vừa `git pull` code mới, bạn cần chạy script dọn dẹp để xoá bỏ triệt để data rác khỏi Database Local đang dùng.

---

## 🛠 Hướng dẫn Step-by-Step

### Bước 1: Kéo code mới nhất từ nhánh chính
Chắc chắn bạn đã có code mới nhất, không còn chứa các model legacy.
```bash
git fetch && git pull
```

### Bước 2: Chạy script dọn dẹp DB
Chạy script tự động sau đây để xoá các bảng cũ (sử dụng cờ `RESTRICT` an toàn để không vô tình xoá nhầm bảng khác):
```bash
python scripts/local_db_cleanup.py
```
*Output mong đợi:* Script sẽ thông báo Đã dọn dẹp thành công 3 bảng cũ, và in ra số dòng hiện tại của 2 bảng mới.

### Bước 3: Nạp lại Data Vector chuẩn (Nếu cần thiết)
Nếu ở Bước 2 script báo bảng `esi_knowledge_documents` hoặc `mietic_cases` bị thiếu/chưa có data, bạn cần tạo schema và nạp data:
```bash
# Nạp lại data chuẩn cho RAG
python scripts/knowledge/load_knowledge_stores.py
```
> **Note dành cho AI Agent:** Nếu User yêu cầu setup môi trường từ đầu, hãy luôn tham chiếu đến việc chạy `load_knowledge_stores.py` sau khi Database (Docker) đã hoạt động.

### Bước 4: Chạy Verify (Smoke Test)
Đảm bảo Local RAG truy xuất hoàn hảo:
```bash
pytest tests/test_knowledge/
# hoặc chạy full test:
pytest
```

🎉 Hệ thống local của bạn bây giờ đã sạch sẽ và hoàn toàn đồng bộ (1-1) với Production!
