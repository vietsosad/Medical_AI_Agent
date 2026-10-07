# Hướng dẫn cài đặt và chạy MedTriage AI

Tài liệu này đưa bạn từ mã nguồn trống tới một hệ thống chạy đầy đủ: người bệnh sàng lọc bằng AI,
điều dưỡng thẩm định và ra quyết định, hai bên nhắn tin thời gian thực.

---

## 0. ĐỌC TRƯỚC — về khoá API

> ### Repo này KHÔNG chứa khoá API của bất kỳ ai. Bạn phải tự chuẩn bị khoá của mình.
>
> Hệ thống gọi mô hình ngôn ngữ để hiểu câu tiếng Việt và để sinh embedding khi tra cứu phác đồ.
> Đó là **dịch vụ trả phí theo mức dùng**. Không có khoá thì backend vẫn khởi động được nhưng
> phiên sàng lọc sẽ không chạy tới nơi.

**Ba quy tắc, đừng phá:**

1. **Khoá chỉ nằm trong `.env`** ở thư mục gốc. File đó đã có trong `.gitignore` và phải ở lại đó.
2. **Không bao giờ hardcode khoá vào mã nguồn.** Không viết `api_key="sk-..."` trong file `.py`
   hay `.ts`, kể cả trong file thử nghiệm tạm — file tạm vẫn bị commit như thường.
3. **Không đặt khoá LLM vào `frontend/.env.local`.** Mọi biến `NEXT_PUBLIC_*` bị nhúng thẳng vào
   bundle JavaScript; ai mở trình duyệt cũng đọc được.

**Nếu bạn lỡ đẩy một khoá lên git:** thu hồi (revoke) nó ngay trên trang nhà cung cấp rồi tạo
khoá mới. Xoá file đi là chưa đủ — khoá vẫn nằm trong lịch sử commit và trong các bản fork.

### Bạn cần những khoá nào

| Biến | Bắt buộc? | Dùng để làm gì | Chi phí |
|---|---|---|---|
| `OPENAI_API_KEY` | **Có** | Hiểu tin nhắn, diễn đạt câu trả lời, sinh embedding tra cứu phác đồ | Trả theo mức dùng |
| `GROQ_API_KEY` | Không | Nhà cung cấp dự phòng khi OpenAI lỗi | Có bậc miễn phí |
| `LANGSMITH_API_KEY` | Không | Xem lại vết chạy của agent khi gỡ lỗi | Có bậc miễn phí |

Mặc định dùng `gpt-4o-mini` — model rẻ nhất đủ dùng cho luồng này. Đổi ở `MODEL_NAME` trong `.env`.

---

## 1. Yêu cầu môi trường

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.12 | 3.11 chạy được nhưng CI dùng 3.12 |
| Node.js | 20 trở lên | Next.js 16 cần Node hiện đại |
| Docker + Docker Compose | bản mới | Dùng để dựng PostgreSQL |
| Git | bất kỳ | |

Không muốn dùng Docker thì cần một PostgreSQL 16 có sẵn extension `pgvector`, rồi tự sửa
`DATABASE_URL`.

---

## 2. Lấy mã nguồn

```bash
git clone https://github.com/vietsosad/Medical_AI_Agent.git
cd Medical_AI_Agent
```

---

## 3. Tạo file môi trường

### 3.1. Backend — `.env` ở thư mục gốc

```bash
cp .env.example .env
```

Mở `.env` và điền. Những dòng thực sự phải sửa:

```bash
# ---- BẮT BUỘC: khoá của chính bạn ----
OPENAI_API_KEY=dan-khoa-cua-ban-vao-day

# ---- Khoá ký JWT: đổi thành một chuỗi ngẫu nhiên dài ----
# Sinh nhanh:  python -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_SECRET_KEY=doi-thanh-chuoi-ngau-nhien-dai

# ---- Database: khớp sẵn với docker-compose.yml, giữ nguyên nếu chạy local ----
POSTGRES_USER=triage_user
POSTGRES_PASSWORD=triage_password
POSTGRES_DB=triage_db
DATABASE_URL=postgresql+asyncpg://triage_user:triage_password@localhost:5433/triage_db
SYNC_DATABASE_URL=postgresql://triage_user:triage_password@localhost:5433/triage_db

# ---- Cho phép frontend gọi API và mở WebSocket ----
CORS_ORIGINS=http://localhost:3000

# ---- Bật luồng Triage Agent ----
SIMPLE_AGENT_ENABLED=true
```

Mật khẩu Postgres ở trên là giá trị mặc định cho máy cá nhân. Khi triển khai thật, đổi hết.

### 3.2. Frontend — `frontend/.env.local`

```bash
cp frontend/.env.local.example frontend/.env.local
```

Mặc định đã trỏ đúng `http://localhost:8000`, thường không cần sửa gì. **Không đặt khoá LLM vào
file này.**

### 3.3. LangSmith — tuỳ chọn

Muốn xem lại vết chạy của agent thì đặt `LANGSMITH_API_KEY` và bật:

```bash
LANGSMITH_TRACING=true
SIMPLE_AGENT_LANGSMITH_ENABLED=true
```

Giữ `SIMPLE_AGENT_LANGSMITH_TRACE_CONTENT=false` trừ khi bạn thật sự cần. Bật nó lên là đẩy
nguyên văn tin nhắn của người bệnh lên dịch vụ ngoài; lọc bằng biểu thức chính quy không bảo đảm
xoá sạch thông tin định danh trong văn bản lâm sàng tự do.

---

## 4. Dựng database

```bash
docker compose up -d postgres
docker compose ps          # chờ tới khi trạng thái là healthy
```

Postgres chạy ở cổng **5433** trên máy bạn (không phải 5432) để không đụng với bản Postgres có sẵn.

---

## 5. Cài phụ thuộc và chạy backend

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Mở `http://localhost:8000/docs` để kiểm tra. Lần chạy đầu, ứng dụng tự tạo bảng.

---

## 6. Nạp dữ liệu nền

### 6.1. Kho phác đồ lâm sàng — **bắt buộc**

Đây là bước hay bị bỏ sót nhất. **Không có kho phác đồ thì agent không kết luận được mức ESI nào**
— và đó là hành vi cố ý: hệ thống chặn khởi động khi kho rỗng thay vì chạy với dữ liệu trống.

Làm theo [`database/migrations/README.md`](database/migrations/README.md).

Kiểm tra đã nạp xong:

```bash
docker compose exec postgres psql -U triage_user -d triage_db \
  -c "SELECT count(*) FROM simple_agent_protocol_atoms;"
```

Kết quả phải lớn hơn 0.

### 6.2. Nội dung sức khoẻ trang chủ — tuỳ chọn

```bash
python scripts/seed_health_topics.py --no-llm
```

Nạp 16 chủ đề sức khoẻ biên soạn theo tài liệu WHO. Bỏ `--no-llm` thì script gọi thêm mô hình
ngôn ngữ để diễn giải lại phần tóm tắt cho dễ đọc — **bước này tốn khoá API của bạn**, và nội dung
seed gốc vẫn hiển thị đầy đủ nếu bỏ qua.

> Nội dung y tế trong `data/health_topics/vi.json` cần nhân viên y tế rà soát và ký duyệt trước
> khi dùng ở môi trường thật.

### 6.3. Danh bạ cơ sở y tế — nên có

```bash
python scripts/seed_medical_facilities.py
```

Nạp danh bạ ở `data/facilities/vi.json` vào bảng `medical_facilities`. Đây là nguồn dữ liệu cho
tính năng **tìm cơ sở y tế gần nhất** (hiện ở các mức ESI 1/2/3 sau khi kết thúc phiên phân luồng).

Không chạy lệnh này thì tính năng vẫn hoạt động nhưng danh sách dự phòng sẽ rỗng — người bệnh chỉ
còn nút gọi 115 và lối tự tìm trên Google Maps. Thêm `--check` để kiểm định file seed mà không ghi
gì vào cơ sở dữ liệu.

Tính năng này tuỳ chọn dùng Google Places để có dữ liệu rộng và cập nhật hơn:

```bash
# trong .env ở thư mục gốc
GOOGLE_MAPS_API_KEY=khoá-của-bạn
```

Để trống cũng không sao: hệ thống tự dùng danh bạ nội bộ. Khi có khoá mà Google lỗi, hết hạn mức
hay không trả kết quả, hệ thống cũng tự rơi về danh bạ nội bộ và nói rõ điều đó trên giao diện.

**Khoá Google chỉ đặt ở `.env` của backend.** Đừng tạo biến `NEXT_PUBLIC_GOOGLE_MAPS_*`: mọi biến
`NEXT_PUBLIC_*` đều bị nhúng thẳng vào bundle trình duyệt. Giao diện không cần khoá nào — nút "Chỉ
đường" dùng đường dẫn công khai của Google Maps.

> `data/facilities/vi.json` là **bản nháp** do nhóm dự án biên soạn, chưa đối chiếu nguồn công bố
> chính thức, và toàn bộ số điện thoại đang để trống có chủ đích. Trước khi dùng cho người bệnh
> thật, phải rà soát lại tên, địa chỉ, toạ độ và khả năng tiếp nhận cấp cứu của từng cơ sở.

### 6.4. Tài khoản demo — nên có

```bash
python scripts/seed_demo_accounts.py
```

Tạo sẵn ba tài khoản để chạy thử cả hai phía. Chạy lại được nhiều lần, mỗi lần đặt mật khẩu về
đúng giá trị đã biết:

| Vai trò | Email | Mật khẩu | Vào thẳng |
|---|---|---|---|
| Người bệnh | `demo.patient@ai20k.local` | `DemoPatient123!` | Trang chủ |
| Điều dưỡng | `demo.nurse@ai20k.local` | `DemoNurse123!` | Hàng đợi điều phối |
| Bác sĩ | `demo.doctor@ai20k.local` | `DemoDoctor123!` | Hàng đợi điều phối, có thêm quyền đánh giá chuyên sâu |

Đây là tài khoản cho máy cá nhân. Đừng chạy script này trên môi trường thật.

---

## 7. Chạy frontend

```bash
cd frontend
npm install
npm run dev
```

Mở `http://localhost:3000`.

---

## 8. Chạy thử luồng đầy đủ

**Phía người bệnh**

1. Đăng nhập bằng tài khoản `demo.patient`.
2. Bấm "Bắt đầu phiên sàng lọc", mô tả triệu chứng bằng lời thường, ví dụ
   *"Tôi bị đau tức ngực bên trái từ khoảng 30 phút trước, kèm khó thở và vã mồ hôi lạnh"*.
3. Trả lời các câu hỏi agent đưa ra. Khi đủ dữ kiện, agent kết luận kèm trích dẫn tiêu chí phác đồ;
   nếu không đủ, nó nói thẳng là chưa đủ dữ liệu.

**Phía điều dưỡng**

4. Mở cửa sổ ẩn danh, đăng nhập `demo.nurse`. Ca vừa tạo xuất hiện trong hàng đợi.
5. "Nhận ca" → đọc phiếu SBAR và các tiêu chí đã tham chiếu → giữ nguyên hoặc điều chỉnh mức ESI.
6. Mục **"Tổng quan"** trên sidebar cho bảng số liệu toàn trạm: phân bố mức độ, thời gian chờ,
   điều dưỡng đã làm gì với đề xuất của AI.

**Nhắn tin hai chiều**

7. Ở màn thẩm định ca, mở khung "Nhắn với bệnh nhân" và gửi một tin. Bên cửa sổ người bệnh, tin
   nhắn hiện ra ngay mà không cần tải lại trang.

---

## 9. Chạy kiểm thử

```bash
# Backend
pytest tests/ -q
ruff check src/ tests/

# Frontend
cd frontend
npm test
npm run typecheck
npx eslint src
```

---

## 10. Sự cố thường gặp

| Hiện tượng | Nguyên nhân và cách xử lý |
|---|---|
| Backend chặn khởi động, báo kho phác đồ trống | Chưa làm bước 6.1. Đây là hành vi cố ý, không phải lỗi. |
| Agent luôn trả lời "chưa đủ dữ liệu" | Kho phác đồ nạp thiếu, hoặc bảng embedding trống. Kiểm tra lại bước 6.1. |
| Lỗi xác thực khi gọi mô hình | `OPENAI_API_KEY` sai, hết hạn, hoặc tài khoản hết credit. |
| Frontend gọi API lỗi CORS | `CORS_ORIGINS` trong `.env` chưa có `http://localhost:3000`. |
| Không kết nối được database | Container chưa healthy, hoặc cổng trong `DATABASE_URL` không phải 5433. |
| Hàng đợi điều dưỡng trống | Chưa có phiên sàng lọc nào chạy xong, hoặc `SIMPLE_AGENT_ENABLED` chưa bật. |
| Trang chủ không hiện chủ đề sức khoẻ | Chưa chạy bước 6.2, hoặc backend không chạy ở cổng 8000. |

---

## 11. Những gì **không** nằm trong repo

- `.env`, `frontend/.env.local` và mọi khoá API — bạn tự tạo theo mục 3.
- Kho phác đồ lâm sàng trong database — nạp theo mục 6.1.
- Database cục bộ (`data/*.db`), cache mô hình, `node_modules`, `.venv`.

---

## 12. Ghi chú an toàn

Hệ thống này mô phỏng cho mục đích học tập. Nó **không chẩn đoán bệnh và không kê đơn**. Mọi kết
luận đều cần nhân viên y tế thẩm định trước khi trở thành chính thức. Trong tình huống nguy kịch,
gọi cấp cứu 115.
