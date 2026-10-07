# ⚙️ BACKEND ENGINEERING RULES & TECH STACK (AI PROMPT INCLUSION FILE)
*(File đặc tả luật kỹ thuật & Tech stack cho Backend - Đính kèm tài liệu này @[.agents/rules/backend-rules.md] mỗi khi yêu cầu AI viết hay sửa chữa code Backend)*

Tài liệu này xác định **quy chuẩn công nghệ bắt buộc (Mandatory Tech Stack)**, **cấu trúc thư mục mô-đun (Folder Structure)** và **quy ước kỹ thuật bất khả xâm phạm (Engineering Commandments)** cho toàn bộ khối Backend (FastAPI + tool-gated DeepAgent + Hybrid RAG) dựa theo `TRIAGE_AGENT_SOLUTION_DESIGN.md` và `ARCHITECTURE.md`.

---

## 1. MỘT SỐ BẮT BUỘC (MANDATORY TECH STACK & LIBRARIES)

| Nhóm Công Nghệ | Thư Viện / Framework Chuẩn | Phạm Vi & Mục Đích Sử Dụng |
| :--- | :--- | :--- |
| **HTTP & Realtime Server** | **FastAPI** (v0.115+) & **Uvicorn** | Cổng giao tiếp REST API bất đồng bộ và hệ thống quản lý WebSocket Real-time, cấu hình Lifespan Factory. |
| **Database ORM** | **SQLModel** (Ưu tiên hơn SQLAlchemy) | Khai báo mô hình dữ liệu (Database Models), bảng thông số bệnh nhân và nhật ký kiểm toán (Audit Logs) trên PostgreSQL. |
| **Async Concurrency** | **Asyncer** & **Psycopg 3** | Quản lý kết nối non-blocking tới DB, điều phối mượt mà giữa mã bất đồng bộ (`async`) và mã blocking I/O. |
| **AI Multi-Agent Engine** | **Deep Agents** + **LangChain Core** | Supervisor, specialist subagents, skills và prerequisite-gated clinical tools. Deep Agents dùng LangGraph nội bộ; repo không tự compile StateGraph. |
| **LLM Provider** | **LangChain Google GenAI** (+ OpenAI Fallback) | Cung cấp nguồn năng lượng suy luận AI (Ưu tiên **Gemini 1.5 Pro**; thiết lập cấu hình Fallback sang GPT-4o khi gặp sự cố timeout). |
| **Vector & Hybrid RAG** | **PostgreSQL pgvector** + controlled sparse retrieval | Kết hợp VI/EN dense retrieval và sparse terms, trộn hạng RRF rồi áp authority/calibration gate. |
| **Data Validation DTOs** | **Pydantic v2 Strict Mode** | Định danh DTOs (Data Transfer Objects), ép buộc kiểm duyệt hợp lệ tại runtime cho mọi payload từ Frontend và phản hồi từ LLM. |

---

## 2. CẤU TRÚC THƯ MỰC BẮT BUỘC (`src/` ARCHITECTURE)

Mọi mã nguồn Backend phải nằm gọn bên trong thư mục `src/`, tuân theo nguyên tắc phân tách trách nhiệm tuyệt đối giữa Lớp API Giao Tiếp, Lớp Não Bộ AI, và Lớp Dữ Liệu:

```text
src/
├── api/                    # 🌐 LỚP HTTP REST ROUTERS & REAL-TIME WEBSOCKETS
│   ├── routes_patient.py   # APIRouter cho Bệnh nhân (Khởi tạo phiên, chat triệu chứng, trả SBAR)
│   ├── routes_nurse.py     # APIRouter cho Bác sĩ / Điều dưỡng (Lấy hàng đợi Realtime, duyệt HITL)
│   ├── websocket_manager.py # Singleton ClinicalQueueManager phát sóng (broadcast) ca ESI tức thì
│   └── dependencies.py     # Dependency Injection: Auth tokens, SQLModel DB Session (Annotated + Depends)
│
├── agents/                 # 🧠 DEEPAGENT + CLINICAL TOOL ENGINE
│   ├── state.py            # Định nghĩa clinical state dùng chung
│   ├── deepagent_runtime/  # Supervisor, subagents, gated tools, state và SSE events
│   ├── guardrails.py       # Bộ Lọc Bảo Vệ Kép (Reflex Regex <50ms & Output Diagnosis Firewall)
│   ├── nodes/              # Các capability lâm sàng xác định do DeepAgent tools gọi
│   │   ├── redflag_detector.py # Node 0: Quét tín hiệu Đỏ khẩn cấp -> Ngắt luồng Escalate
│   │   ├── intake_analyzer.py  # Node 1: Phân tích mâu thuẫn lời khai & trích xuất tiền sử
│   │   ├── question_engine.py  # Node 2: Sinh câu hỏi làm rõ triệu chứng / Trắc nghiệm ESI
│   │   ├── triage_reasoner.py  # Node 3: Tra cứu Hybrid RAG -> Quyết định thang ESI Level (1 ➔ 5)
│   │   └── summary_creator.py  # Node 4: Chắp bút Phiếu Bàn Giao Y Khoa (Chuẩn SBAR)
│   └── tools/              # Tích hợp retrieval và nurse queue cho clinical nodes
│       ├── rag_retriever.py    # Adapter retrieval pgvector và MIETIC demo có kiểm soát
│       └── queue_pusher.py     # Đẩy ca can thiệp khẩn cấp lên kênh WebSocket Điều Dưỡng
│
├── models/                 # 📋 MÔ HÌNH DỮ LIỆU & TYPE CONTRACTS
│   ├── db_models.py        # Các bảng cơ sở dữ liệu SQLModel (User, TriageCase, Message, AuditLog)
│   └── schemas.py          # Strict Pydantic v2 DTOs (ChatInputDTO, OverridePayload, SBARCardDTO)
│
└── services/               # 🔧 TÍCH HỢP HẠ TẦNG & TRUY XUẤT NGOẠI VI
    ├── db.py               # SQLModel Engine Pool init & Lifespan connection hooks
    └── llm_provider.py     # Factory khởi tạo Gemini 1.5 Pro kèm hệ thống Auto-Fallback
```

---

## 3. QUY ƯỚC KỸ THUẬT & LUẬT BẤT KHẢ XÂM PHẠM (ENGINEERING COMMANDMENTS)

### 3.1. Phân Định Kiến Trúc FastAPI & Non-Monolithic Rules
*   🚫 **CẤM MONOLITHIC ENTRYPOINT:** Không được khai báo các endpoint API hay mô hình ORM trực tiếp tại `src/main.py`. Mọi router phải gom nhóm qua `APIRouter(prefix="/api/v1/...", tags=["..."])`.
*   ✅ **QUẢN LÝ TÀI NGUYÊN LIFESPAN:** Bắt buộc sử dụng `async context manager lifespan` để mở và dán (dispose) connection pool của SQLModel và chỉ mục vector ChromaDB khi máy chủ tắt/mở.
*   ✅ **DEPENDENCY INJECTION CHUẨN MỰC:** Khi tiêm Sessions hay Auth, LUÔN DÙNG cú pháp `Annotated[..., Depends(...)]` từ bộ quy chuẩn mới của FastAPI. Cấm dùng `...` (ellipsis) thừa thãi hay `RootModel`.

### 3.2. Quy Tắc Bất Biến Dữ Liệu Trong DeepAgent Tools
*   **Clinical node là Pure Function:** Trong `src/agents/nodes/`, mỗi hàm nhận state và trả Dict mới chứa **duy nhất** thuộc tính thay đổi.
*   🚫 **CẤM MUTATE TRỰC TIẾP TRONG NODE:** Runtime tool adapter là lớp duy nhất merge partial update và xử lý field tích lũy.
*   **Prerequisite bắt buộc:** Tool gọi sai thứ tự, lặp lại hoặc thiếu patient/evidence gate phải trả `REJECTED` và không mutate clinical state.
*   **Free-form model output không có authority:** Chỉ state từ tool qua `verify_clinical_output` mới được trả cho API.

### 3.3. Lá Chắn Sinh Tử Kép (Dual-Layer Medical Safety Shield)
Đây là luật nghiêm ngặt nhất định đoạt sự an toàn tính mạng bệnh nhân:
*   **Lớp 1: Bọc Bảo Vệ Phản Xạ Ngắt Luồng Dưới 50ms (Reflex Interception):**
    *   Bất kỳ chuỗi văn bản nào gửi đến cổng triage ĐỂU PHẢI lướt qua Regex & Ontology (trong `guardrails.py` / `ontology_vi_en.json`) **trước khi nạp vào DeepAgent hay gọi LLM**.
    *   *Từ Khóa Đuôi Tim:* Nếu chạm phải tín hiệu đe dọa (vd: "đau thắt ngực", "nghe nhói buốt tim", "thở hụt hơi như đứt hơi", "méo miệng FAST", "GCS < 9", "chảy máu không cầm"), hệ thống phải **lập tức ngắt toàn bộ luồng suy luận (<50ms)**, ấn định ngay mức **ESI Level 1 (Tối Khẩn) hoặc ESI Level 2**, kích hoạt còi báo động qua WebSocket cho Điều Dưỡng và phát thẻ Gọi Hotline Cấp cứu 115 cho Bệnh nhân.
*   **Lớp 2: Tường Lửa Ngăn Chặn Tự Xưng Chẩn Đoan (Output Diagnosis Firewall):**
    *   Trước khi phát trả văn bản của AI về Frontend, một dải lọc xuất ra (Output interceptor) sẽ loại bỏ toàn bộ các khẳng định mang tính phán xét bệnh hay toa thuốc chối bỏ trách nhiệm y khoa (vd: cấm nói "Bạn đã mắc ung thư/nhồi máu cơ tim"). Buộc phải dịch chuyển thành: *"Dựa trên các dấu hiệu lâm sàng bạn phác họa, đây là tình trạng cần được chuyên môn y khoa khảo sát gấp..."*.

### 3.4. Chuẩn Tra Cứu Lai & Minh Chứng RAG (Hybrid RAG Provenance)
*   **Thực thi Tìm Kiếm Lai (Dense + Sparse):** Đơn thuần Embeddings vector dễ làm trượt mất các mác viết tắt huyết áp hay thông số y tế chính xác. Luôn thi thoảng chạy song song **ChromaDB Vector** (bắt ngữ nghĩa bệnh) và **Rank-BM25 / Postgres FTS** (bắt trúng thông số như "SpO2 < 90%", "GCS 8"), trộn danh mục kết quả bằng RRF.
*   **Bắt buộc Gắn Nguồn (Citation Accountability):** Mọi kết luận ESI (1 ➔ 5) và nội dung của Thẻ Bàn Giao Y Khoa (SBAR) PHẢI kèm theo minh chứng mã tài liệu gốc RAG thu hoạch được (vd: `[Ref: PRO_CP_001 - Hội chứng Vành cấp]`). Nếu độ tương đồng hạ dưới ngưỡng chuẩn, CẤM hallucinate (chém gió), hãy giữ thái độ bảo thủ: Nâng thang rủi ro hoặc đề xuất nhân sự thật can Thiệp.

### 3.5. Kiểm Duyệt Con Người Trong Nhịp Khám (HITL - Human-in-the-Loop)
*   **Proposal không phải quyết định cuối:** DeepAgent chỉ được ghi proposal vào `triage_cases` và `nurse_review_states`; Điều dưỡng/Bác sĩ quyết định **Approve** hoặc **Override** qua `routes_nurse.py`.
*   **Durable state:** `chat_messages`, case, review state và audit log là nguồn bền vững. Hot agent state có thể rebuild bảo thủ và không được tự suy ra ESI.
*   Mọi hành động can thiệp lâm sàng phải ghi `AuditLog` và giữ optimistic concurrency/version checks.

### 3.6. Xử lý Dữ liệu Chuẩn & An toàn Bất Đồng Bộ (Pydantic v2 & Asyncer)
*   **100% DTOs rõ ràng:** Mọi cổng giao tiếp `@router.post(...)` và đầu ra đều phải được bọc trong các lớp Pydantic v2 `BaseModel` định nghĩa tại `src/models/schemas.py`.
*   **An toàn Non-Blocking Loop:** Không thực hiện các lệnh truy vấn CSDL đồng bộ trực tiếp trong các hàm `async def` của router vì sẽ bóp nghẹt Event Loop của FastAPI. Khuyến khích sử dụng tiện ích **Asyncer** hoặc tài nguyên `async` gốc của SQLModel (`AsyncSession`) để tối ưu hóa hiệu năng nghìn luồng.

---
*Hết Bộ Quy Chuẩn Kỹ Thuật Backend Rules.*  
**Mọi mã nguồn Backend từ Trợ lý AI hay Kỹ sư Lập trình đều phải được kiểm định chặt chẽ bởi tài liệu này trước khi được Commit.**
