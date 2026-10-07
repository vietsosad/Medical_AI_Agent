# MedTriage AI — Trợ lý phân loại mức độ cấp cứu có điều dưỡng thẩm định

Hệ thống web sàng lọc mức độ khẩn cấp theo **thang ESI 5 cấp**, hỏi từng dữ kiện lâm sàng còn
thiếu bằng tiếng Việt tự nhiên, đối chiếu với phác đồ đã số hoá, và **chỉ trở thành kết quả chính
thức sau khi nhân viên y tế thẩm định**.

> **Đây là hệ thống mô phỏng phục vụ học tập và nghiên cứu kỹ thuật.** Nó không chẩn đoán bệnh,
> không kê đơn, không thay thế thăm khám trực tiếp. Trong tình huống nguy kịch, gọi cấp cứu 115.

Cài đặt và chạy thử: xem **[SETUP.md](SETUP.md)**. Bạn cần tự chuẩn bị khoá API của riêng mình —
repo này không chứa và sẽ không bao giờ chứa khoá trả phí của bất kỳ ai.

---

## Vấn đề

Người bệnh mô tả triệu chứng rời rạc, qua nhiều lượt, bằng lời đời thường. Một chatbot y tế thông
thường hỏng ở ba chỗ:

- hỏi theo checklist cứng nhắc, hỏi lại điều người bệnh vừa nói;
- bỏ lỡ dấu hiệu nguy kịch trong lúc chờ mô hình ngôn ngữ trả lời;
- đưa ra kết luận không có nguồn, nhân viên y tế không kiểm tra lại được.

## Cách tiếp cận

Mức độ khẩn cấp **không do mô hình ngôn ngữ quyết định**. Hệ thống tách bạch bốn lớp:

| Lớp | Vai trò | Dùng LLM? |
|---|---|---|
| Guardrail | Chặn prompt-injection và các tín hiệu cần xử lý an toàn trước khi vào hội thoại | Không |
| Hiểu tin nhắn | Đọc câu tiếng Việt tự do, truy xuất concept/fact, cập nhật state phiên | Có |
| Quyết định | Khớp dữ kiện với tiêu chí phác đồ, chọn câu hỏi tiếp theo hoặc chốt mức ESI | **Không** |
| Thẩm định | Điều dưỡng xem toàn bộ hồ sơ rồi giữ nguyên hoặc điều chỉnh mức ESI | Người |

### Ba nguyên tắc bất biến

1. **Mức ESI do code quyết định.** Logic "tiêu chí nào đã thoả, chọn mức nào" nằm ở
   `src/simple_agent/decision.py` — thuần Python, không gọi LLM. Mô hình chỉ trích xuất dữ kiện và
   diễn đạt câu chữ.
2. **Mô hình không thể tự bịa ID.** Mọi `concept_id` / `fact_target_id` phải đến từ một lời gọi
   tool đã thực sự trả về ID đó, hoặc đã có sẵn trong phiên — kiểm tra ở `tools.py`.
3. **Fail-closed.** Không truy xuất được phác đồ làm căn cứ thì **không kết luận** — hệ thống nói
   thẳng là chưa đủ dữ liệu thay vì đoán một mức ESI.

### Ba pha mỗi lượt chat

| Pha | File | Việc | LLM |
|---|---|---|---|
| A — Hiểu | `understanding.py`, `tools.py` | Vòng tool-calling đọc tin nhắn, cập nhật dữ kiện, phân biệt "tự hỏi" với "hỏi hộ người khác" | ≤ 8 lời gọi tool/lượt |
| B — Quyết định | `decision.py` | Đối chiếu tất định từng tiêu chí, xếp hạng câu hỏi kế tiếp | Không |
| C — Diễn đạt | `phrasing.py` | Biến quyết định của pha B thành câu tiếng Việt, không thêm dữ kiện lâm sàng | 1 lời gọi ngắn |

Ràng buộc tài nguyên cứng: `MAX_ASKED_FACTS_PER_SESSION = 17` · `MAX_TOOL_CALLS = 8` mỗi lượt ·
`STALE_QUESTION_LIMIT = 2` lần hỏi lại tối đa cho cùng một dữ kiện.

### Tri thức lâm sàng

Toàn bộ phác đồ nằm trong **PostgreSQL**, ở các bảng `simple_agent_*`. Agent không đọc file dữ
liệu cục bộ nào lúc chạy. Bảng trống thì hệ thống chặn khởi động thay vì chạy với kho rỗng —
xem `src/simple_agent/pg_corpus.py`.

---

## Tính năng

### Phía người bệnh

- **Sàng lọc hội thoại** — agent hỏi từng dữ kiện còn thiếu, tối đa một câu mỗi lượt.
- **Kết luận kèm trích dẫn** — nêu rõ tiêu chí phác đồ nào đã thoả và người bệnh đã khai giá trị
  gì cho tiêu chí đó.
- **Hồ sơ EHR nhẹ** — tuổi, giới, nhóm máu, dị ứng, bệnh nền, người liên hệ khẩn cấp; hỗ trợ hồ
  sơ người thân (khám hộ con, cha mẹ).
- **Nhắn tin thời gian thực** với nhân viên y tế sau khi phiên sàng lọc kết thúc.
- **Kiến thức sức khoẻ** — 16 chủ đề biên soạn theo tài liệu WHO, trình bày thành một dòng chảy
  ngang liên tục trên trang chủ.

### Phía điều dưỡng / bác sĩ

- **Hàng đợi điều phối** — 4 nhóm (chờ tiếp nhận, ca của tôi, tạm gác lại, đã xác nhận), lọc theo
  mức ESI, mã ca, email; dải màu mức độ đọc được từ xa, ca ESI 1–2 có tín hiệu động riêng.
- **Màn thẩm định ca** — danh tính và đường liên lạc, phiếu SBAR, từng tiêu chí phác đồ đã tham
  chiếu kèm giá trị người bệnh khai, toàn bộ hội thoại với AI.
- **Bàn quyết định** — giữ nguyên hoặc điều chỉnh mức ESI, bắt buộc ghi lý do khi điều chỉnh.
- **Bảng số liệu tổng quan** — phân bố mức độ, thời gian chờ tiếp nhận, điều dưỡng đã làm gì với
  đề xuất của AI, lý do điều chỉnh, khối lượng 14 ngày. Mọi con số là phép đếm trực tiếp trên dữ
  liệu ca, không có chỉ số ước lượng.

---

## Công nghệ

**Backend** — Python 3.12, FastAPI, SQLModel/SQLAlchemy (async), PostgreSQL + pgvector, WebSocket,
LangChain cho lớp tool-calling, Pydantic cho mọi hợp đồng dữ liệu.

**Frontend** — Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, TanStack Query,
Zustand, Zod kiểm định mọi phản hồi API ở biên mạng, Vitest + Testing Library.

**Hạ tầng** — Docker Compose cho Postgres, GitHub Actions cho CI.

---

## Chạy thử nhanh

Hướng dẫn đầy đủ nằm ở **[SETUP.md](SETUP.md)**. Tóm tắt:

```bash
# 1. Chuẩn bị biến môi trường — TỰ ĐIỀN KHOÁ API CỦA BẠN
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local

# 2. Dựng database
docker compose up -d postgres

# 3. Backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# 4. Nạp tri thức lâm sàng (BẮT BUỘC — thiếu bước này agent không kết luận được)
#    xem database/migrations/README.md

# 5. Nội dung sức khoẻ + tài khoản demo (tuỳ chọn)
python scripts/seed_health_topics.py --no-llm
python scripts/seed_demo_accounts.py

# 6. Frontend
cd frontend && npm install && npm run dev     # http://localhost:3000
```

---

## Cấu trúc dự án

```
src/
  api/              FastAPI routers — auth, patient, nurse, nurse-simple, health, websocket
  simple_agent/     Agent phân loại: understanding · decision · phrasing · tools · sbar · pg_corpus
  agents/           Runtime bao quanh agent
  models/           SQLModel bảng dữ liệu + DTO Pydantic
  services/         DB, bảo mật, LLM provider, nội dung sức khoẻ, số liệu tổng quan
frontend/src/
  app/              App Router: trang chủ, (patient), clinical, auth, admin
  components/       landing · chat · clinical/nurse-simple · profile · history · ui
  queries/ services/ schemas/ types/    Lớp dữ liệu: TanStack Query + Zod + DTO
eval/               Bộ đánh giá agent trên 30 ca vàng
tests/              pytest — API, agent, services, knowledge
database/           Migration và bundle nạp kho phác đồ
data/               Bảng ESI đã trích xuất, ontology, nội dung sức khoẻ (seed)
scripts/            Seed, migrate, dựng manifest phác đồ
docs/               PRD, kiến trúc, các bản thiết kế và audit
```

---

## API chính

| Nhóm | Endpoint tiêu biểu |
|---|---|
| Xác thực | `POST /api/v1/auth/register` · `/login` · `/verify-otp` · `/refresh` |
| Sàng lọc | `POST /api/v1/simple-triage/start` · `/chat/{session_id}` |
| Hồ sơ | `GET/POST /api/v1/profiles` · `GET /api/v1/patient/history` |
| Điều dưỡng | `GET /api/v1/nurse-simple/queue` · `/dashboard` · `/cases/{id}` · `POST /cases/{id}/decision` |
| Sức khoẻ | `GET /api/v1/health-topics` · `/health-topics/{slug}` |
| Realtime | `WS /ws/simple-clinical` · `/ws/simple-case/{id}` |

Tài liệu tương tác: `http://localhost:8000/docs`

---

## Kiểm thử

```bash
pytest tests/ -q                    # backend
cd frontend && npm test             # frontend (Vitest)
cd frontend && npm run typecheck    # TypeScript
cd frontend && npx eslint src       # lint
ruff check src/ tests/              # lint Python
```

Bộ đánh giá agent trên 30 ca vàng nằm ở `eval/`; báo cáo lần chạy gần nhất ở
[`docs/evaluation.md`](docs/evaluation.md) — các con số ở đó là kết quả của một lần chạy cục bộ,
không phải chỉ số đã được kiểm định độc lập.

---

## Ghi chú an toàn lâm sàng

Những hành vi dưới đây là **chủ ý**, không phải lỗi:

- **Không đủ căn cứ thì không kết luận.** Hệ thống trả lời thẳng là chưa đủ dữ liệu.
- **Không có kết quả nào tự động thành chính thức.** Đề xuất của AI luôn phải qua điều dưỡng.
- **Không tự xếp hạng mức độ nguy hiểm của bệnh** ở lớp nội dung giáo dục sức khoẻ — dữ liệu chủ
  đề không mang trường mức độ, nên giao diện không được phép tự nghĩ ra một thứ tự.
- **Bảng số liệu không nói về độ chính xác của AI.** Hệ thống không có nhãn chuẩn để đối chiếu;
  con số ở đó ghi lại quyết định của điều dưỡng, luôn kèm mẫu số.
- **Thông tin định danh được che trong nhật ký hệ thống** — xem `src/services/log_redaction.py`.

Nội dung giáo dục sức khoẻ trong `data/health_topics/vi.json` được biên soạn theo tài liệu của
WHO và đã qua bộ lọc chặn tuyên bố dịch tễ, nhưng **cần nhân viên y tế rà soát và ký duyệt trước
khi dùng ở môi trường thật** — đúng như ghi chú trong chính file seed.

---

## Tài liệu liên quan

| File | Nội dung |
|---|---|
| [SETUP.md](SETUP.md) | Cài đặt, cấu hình khoá API, nạp dữ liệu, chạy thử |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Kiến trúc hệ thống |
| [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) | Chi tiết agent phân loại |
| [docs/PRD.md](docs/PRD.md) | Yêu cầu sản phẩm |
| [DATASET_AND_RAG_STRATEGY.md](DATASET_AND_RAG_STRATEGY.md) | Chiến lược dữ liệu và truy xuất |
| [SYSTEM_DATA_DICTIONARY.md](SYSTEM_DATA_DICTIONARY.md) | Từ điển dữ liệu |
| [RUNBOOK.md](RUNBOOK.md) | Vận hành |
| [database/migrations/README.md](database/migrations/README.md) | Nạp kho phác đồ |

---

## Giấy phép

Dự án phục vụ mục đích học tập và nghiên cứu. Không dùng cho chẩn đoán hoặc điều trị thật.
