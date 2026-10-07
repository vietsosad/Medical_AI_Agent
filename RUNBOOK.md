# RUNBOOK — Chạy MedTriage trên máy local

Tài liệu này là **đường chạy nhanh** và **sổ tay xử lý sự cố**. Mọi lỗi liệt kê
ở đây đều đã thực sự xảy ra và đã được kiểm chứng cách khắc phục, không phải
suy đoán.

Cần cài đặt chi tiết hơn (yêu cầu máy, tạo `.env` từ đầu, restore database
backup)? Xem [SETUP.md](SETUP.md).

---

## 0. Tóm tắt 60 giây

```bash
docker compose up -d postgres backend     # backend :8000 + postgres :5433
cd frontend && npm run dev -- --hostname localhost --port 3000
```

Mở **http://localhost:3000**

> ⚠️ Dùng đúng **`localhost`**, đừng dùng `127.0.0.1`. Lý do ở [mục 4](#4-lỗi-thường-gặp).

Kiểm tra nhanh:

```bash
curl http://127.0.0.1:8000/health        # {"status":"ok","env":"development"}
docker compose ps                        # cả 2 container phải "healthy"
```

---

## 1. Kiến trúc khi chạy local

| Thành phần | Chạy ở đâu | Cổng | Ghi chú |
|---|---|---|---|
| PostgreSQL + pgvector | Docker | 5433 | `restart: unless-stopped` |
| FastAPI backend | Docker | 8000 | mount `./src` + `--reload` |
| Next.js frontend | Máy host | 3000 | `npm run dev` |

**Quan trọng:** `docker-compose.yml` mount `./src:/app/src`, nên **code Python
sửa là có hiệu lực ngay**, không cần rebuild image.

Nhưng `.env` chỉ được nạp **lúc container khởi động**. Sửa `.env` thì phải:

```bash
docker compose up -d backend      # recreate để nạp lại env
```

`docker compose restart backend` **không** nạp lại `.env` — chỉ dùng khi bạn
đổi code Python và muốn reload sạch.

---

## 2. Biến môi trường dễ sai nhất

### `CORS_ORIGINS` phải chứa **đúng** origin bạn mở trên trình duyệt

```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173
```

Với trình duyệt, `localhost:3000` và `127.0.0.1:3000` là **hai origin khác
nhau**. Thiếu một cái thì preflight trả 400 và frontend báo *"Không thể kết nối
tới máy chủ FastAPI (Port 8000)"* — dù backend hoàn toàn khỏe mạnh.

`curl` không gửi header `Origin`, nên **test bằng curl sẽ pass** trong khi
trình duyệt vẫn lỗi. Muốn kiểm tra đúng:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X OPTIONS \
  http://127.0.0.1:8000/api/v1/triage/history \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET"
# 200 = OK   |   400 = origin chưa có trong CORS_ORIGINS
```

### `NEXT_PUBLIC_API_URL`

`frontend/.env.local` hiện là `http://127.0.0.1:8000`. Dùng được, miễn là
`CORS_ORIGINS` có origin của frontend. Đổi giá trị này thì **phải restart
`npm run dev`** — Next.js chỉ đọc `NEXT_PUBLIC_*` lúc khởi động.

---

## 3. Chạy backend ngoài Docker (khi Docker hỏng)

```bash
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
DATABASE_URL="sqlite+aiosqlite:///./data/local_dev.db" \
SYNC_DATABASE_URL="sqlite:///./data/local_dev.db" \
RAG_DEMO_LEGACY_MIETIC_ENABLED=false \
.venv312/Scripts/python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Ứng dụng có sẵn nhánh SQLite, tự bỏ qua các bảng pgvector.

**`PYTHONIOENCODING=utf-8` là bắt buộc trên Windows.** Không có nó, khi stdout
bị redirect ra file, `/api/v1/auth/guest` **crash 500** với `UnicodeEncodeError`
trên emoji trong dòng log (`security.py`), vì console codepage là cp1258.

**Đánh đổi:** chế độ này **không có RAG/MIETIC** (các bảng đó cần pgvector).
Chỉ dùng để xem giao diện và luồng hội thoại.

---

## 4. Lỗi thường gặp

### `Không thể kết nối tới máy chủ AI Triage FastAPI (Port 8000)`

Thông báo này gây hiểu nhầm — backend thường **vẫn sống**. Kiểm tra:

```bash
curl http://127.0.0.1:8000/health          # còn sống?
docker logs triage_backend --tail 30 | grep OPTIONS
```

Thấy `OPTIONS ... 400 Bad Request` → là lỗi CORS, xem [mục 2](#2-biến-môi-trường-dễ-sai-nhất).

Cũng cần kiểm tra **ai đang giữ cổng 8000**:

```bash
netstat -ano | grep ":8000" | grep LISTENING
tasklist //FI "PID eq <PID>"
```

Nếu là `com.docker.backend.exe` thì cổng đang do **container** giữ, không phải
uvicorn local của bạn. Hai tiến trình cùng nghe một cổng sẽ khiến bạn test một
đằng, trình duyệt gọi một nẻo.

### `Jest worker encountered N child process exceptions` (Next.js)

Đây là **worker của dev server chết**, không phải lỗi code. Thường sau khi dev
server chạy nhiều giờ (tiến trình node phình >1 GB), Next.js gắn nhãn *"(stale)"*.

```bash
# Ctrl+C dừng dev server
rm -rf frontend/.next
cd frontend && npm run dev -- --hostname localhost --port 3000
```

Muốn chắc chắn không phải lỗi code, chạy build — nếu build sạch thì đúng là
worker:

```bash
cd frontend && npx next build
```

Làm việc lâu mà cứ tái diễn thì chạy production mode, ổn định hơn hẳn:

```bash
cd frontend && npm run build && npm run start -- --hostname localhost --port 3000
```

### Đăng nhập Google không vào được

Trình duyệt quay về **đúng origin đã bấm nút** — token lưu trong localStorage
theo từng origin, nên về sai origin thì tab bạn đang mở vẫn "chưa đăng nhập"
dù Google đã xác thực thành công.

Backend đã tự lấy `redirect_uri` theo origin của request (có kiểm tra
allowlist). Nhưng **Google Cloud Console phải đăng ký sẵn URI đó**:

> Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client ID
> → **Authorized redirect URIs**
> ```
> http://localhost:3000/auth/callback/google
> http://127.0.0.1:3000/auth/callback/google
> ```

Cách nhanh nhất: **mở app bằng `localhost:3000`**, vì `.env` đã trỏ sẵn origin đó.

Kiểm tra backend đang sinh URI nào:

```bash
curl -s "http://127.0.0.1:8000/api/v1/auth/oauth/google/url" \
  -H "Origin: http://localhost:3000" | grep -o "redirect_uri=[^&]*"
```

### Chat trả về `HTTP 400 — Phiên đã bị khóa an toàn`

**Đúng thiết kế**, không phải bug. Phiên đã leo thang cấp cứu và bị khoá. Mở
phiên mới để tiếp tục test.

### Không có citation RAG / hệ thống luôn "không đủ bằng chứng"

**Đúng thiết kế.** Bảng `triage_protocol_documents` đang **rỗng** — xem
[mục 7](#7-tầng-tri-thức-lâm-sàng). Hệ thống chọn ABSTAIN thay vì đoán bừa.

---

## 5. Kiểm thử

```bash
.venv312/Scripts/python.exe -m pytest tests/ -q          # 762 passed
.venv312/Scripts/python.exe -m ruff check src/ tests/    # All checks passed
```

Test chạy trên SQLite, **không** cần Docker.

> ⚠️ SQLite dễ tính hơn PostgreSQL. Đã có lỗi lọt qua toàn bộ test rồi hỏng ở
> sản phẩm: một `datetime` có timezone ghi vào cột `TIMESTAMP WITHOUT TIME ZONE`
> — SQLite chấp nhận, asyncpg từ chối và làm hỏng cả transaction giữa lượt.
> Đụng vào cột thời gian thì hãy test luôn trên Postgres thật.

Đánh giá chất lượng (không cần LLM):

```bash
PYTHONPATH=. .venv312/Scripts/python.exe eval/run_evaluation.py
```

In ra 6 chỉ số kỹ thuật đo được thật, và 7 chỉ số lâm sàng đánh dấu
`NO_LABELLED_BENCHMARK` kèm lý do — cố ý không ước lượng bừa.

---

## 6. AI log (Phoenix)

Hook `pre-push` thu prompt từ **cả hai** IDE:

```bash
scripts/log_antigravity.py --auto     # Antigravity IDE
scripts/log_claude_code.py --auto     # Claude Code
scripts/submit_log.py                 # nộp lên server
```

> ⚠️ `.git/hooks/` **không được version control**. Người mới clone repo phải tự
> tạo lại `.git/hooks/pre-push` với đủ 3 dòng trên, nếu không log sẽ không được
> ghi nhận.

Chạy tay và xem trước:

```bash
python scripts/log_claude_code.py --all --dry-run   # xem sẽ ghi gì
python scripts/log_claude_code.py --all             # ghi toàn bộ lịch sử
python scripts/submit_log.py                        # nộp (mong đợi: 202)
```

Chống trùng đọc cả `.ai-log/session.jsonl` lẫn `.ai-log/archive/`, nên chạy lại
nhiều lần không gửi trùng.

Cần `AI_LOG_SERVER` và `AI_LOG_API_KEY` trong `.env`.

---

## 7. Tầng tri thức lâm sàng

`triage_protocol_documents` (corpus phác đồ chính thức) đang **rỗng**. Đây là
trạng thái đã biết, không phải lỗi cấu hình.

```bash
python scripts/build_protocol_manifest.py    # dựng manifest nháp từ AHRQ ESI v5
```

Manifest sinh ra **cố ý không qua được** khâu kiểm định:

```
BLOCKING METADATA (must be supplied by a clinical owner):
  - validation_status, reviewed_by, reviewed_at
  - calibration_profile, calibration_id
  - source_uri, license_reference, effective_date
STATUS: NOT_READY_FOR_INGESTION
```

Những trường này cần **bác sĩ có tên thật ký duyệt**. Điền bừa sẽ tạo ra một
corpus nói dối về chính nguồn gốc của nó — tệ hơn là để trống.

Corpus MIETIC (9.629 ca) **chỉ dùng cho demo**, đã được cách ly: nó không có ca
ESI 4/5 nào, có 1.122 nhóm nhãn ESI mâu thuẫn, và không dùng để đánh giá lâm
sàng được.

---

## 8. Trạng thái hiện tại — nói thẳng

| | |
|---|---|
| Test | 762 passed, 0 skipped, 0 xfail |
| Lint | ruff sạch |
| Corpus phác đồ | **rỗng** — chờ bác sĩ duyệt |
| Artifact chờ duyệt lâm sàng | **9** (`PENDING_CLINICAL_REVIEW`) |

**Hệ thống chưa được thẩm định lâm sàng.** Test kỹ thuật pass chỉ chứng minh bộ
máy an toàn hoạt động đúng như đặc tả — không chứng minh đặc tả đó đúng về mặt
y khoa.

---

## 9. Tài liệu liên quan

- [SETUP.md](SETUP.md) — cài đặt chi tiết, restore database backup
- [ARCHITECTURE.md](ARCHITECTURE.md) — kiến trúc hệ thống
- [eval/results/report.md](eval/results/report.md) — báo cáo đánh giá
- `docs/Gate_2/` — hồ sơ demo Gate 2
