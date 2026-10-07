# Deep Triage Agent — mô tả kiến trúc để tích hợp

Tài liệu này mô tả agent triage cấp cứu (mock, không phải chẩn đoán thật) đang
nằm ở project này, dùng để một agent/dev khác đọc và quyết định cách ghép vào
một backend đã có sẵn. Mọi đường dẫn dưới đây là tương đối so với gốc project
này.

## Agent này làm gì

Một trợ lý hội thoại tiếng Việt mô phỏng quy trình phân loại độ khẩn cấp cấp
cứu ESI (Emergency Severity Index, mức 1-5). Người dùng mô tả triệu chứng qua
nhiều lượt chat; agent hỏi thêm thông tin còn thiếu, rồi khớp câu trả lời với
một tập luật lâm sàng (protocol atoms) để kết luận mức ESI phù hợp — hoặc báo
chưa đủ dữ liệu để kết luận. Đây là mô phỏng, luôn kèm khuyến cáo "không phải
chẩn đoán, cần bác sĩ khám trực tiếp".

## Nguyên tắc kiến trúc cốt lõi (bắt buộc giữ khi tích hợp)

1. **Khớp ESI luôn deterministic, không bao giờ do LLM tự quyết định.** Toàn
   bộ logic "atom nào thỏa mãn, mức ESI nào được chọn" nằm ở `decision.py`,
   thuần Python, không gọi LLM. LLM chỉ trích xuất dữ kiện và diễn đạt câu
   chữ — không bao giờ tự phán mức độ nghiêm trọng.
2. **Model không thể tự bịa ID.** Mọi `concept_id`/`fact_target_id` mà LLM
   dùng đều phải đến từ một lời gọi tool đã thực sự trả về ID đó trong lượt
   này, hoặc đã có sẵn trong session — được validate ở code (`tools.py`), không
   tin tưởng mù quáng đầu ra của model.
3. Mỗi lượt chat chạy đúng 3 pha tuần tự (xem bên dưới), luôn theo thứ tự
   A → B → C.

## 3 pha xử lý một lượt chat

- **Phase A — hiểu tin nhắn** (`understanding.py` + `tools.py`): một vòng
  lặp gọi LLM có tool-calling (tối đa 6 lần gọi/lượt, model mặc định
  `gpt-4.1-mini`), đọc tin nhắn bệnh nhân và gọi tool để cập nhật state:
  concept nào đang được nói tới (của chính bệnh nhân hay của người khác họ
  hỏi hộ), giá trị cụ thể cho các fact, mô tả định tính, "không biết", v.v.
- **Phase B — quyết định** (`decision.py`): Python thuần, khớp các protocol
  atom đã truy xuất với facts hiện có, xếp hạng câu hỏi tiếp theo nên hỏi.
  Không gọi LLM ở bước này.
- **Phase C — diễn đạt** (`phrasing.py`): một lời gọi LLM ngắn, biến quyết
  định của Phase B (hỏi fact nào, hay kết luận ESI nào) thành câu tiếng Việt
  tự nhiên, dễ hiểu. Không được tự thêm dữ kiện lâm sàng nào ở bước này.

## Bản đồ file (`src/simple_agent/`)

| File | Vai trò |
|---|---|
| `agent.py` | Orchestrator — class `SimpleTriageAgent`, entry point duy nhất là `process_turn(session_id, message)`. |
| `session.py` | `Session` dataclass — state một cuộc hội thoại. Hỗ trợ hỏi hộ người khác (self/other-person) với cơ chế switch/park/resume theo từng chủ thể. |
| `tools.py` | `AgentToolbox` — cách duy nhất Phase A đọc/ghi state; validate mọi input ở đây. |
| `understanding.py` | Vòng lặp tool-calling của Phase A. |
| `decision.py` | Khớp atom/ESI + xếp hạng câu hỏi tiếp theo — thuần deterministic. |
| `phrasing.py` | Phase C — soạn câu hỏi/tóm tắt xác nhận/kết luận cuối bằng tiếng Việt. |
| `resource_estimate.py` | Một lời gọi LLM ước lượng riêng cho `fact_target:resource_count` (trường CLINICIAN_ONLY, không hỏi bệnh nhân trực tiếp được, nhưng gần như mọi atom ESI 3/4/5 cần nó) — chỉ chạy một lần/phiên, khi phần còn lại của cuộc phỏng vấn đã xong. |
| `prompts.py` | Toàn bộ system prompt cho LLM + tool schema, tập trung một chỗ. |
| `corpus.py` | Load 4 file JSONL dữ liệu lâm sàng + index embedding; hàm cosine similarity. |
| `skills.py` | Guardrail deterministic chặn prompt-injection/dò system prompt — chạy trước cả Phase A, không tốn lời gọi LLM nào. |

## API bề mặt thực tế

```python
from src.simple_agent.agent import SimpleTriageAgent

agent = SimpleTriageAgent()  # mặc định corpus_dir=data/siu, index_dir=data/indexes_siu
result = agent.process_turn(session_id="user-123", message="tôi bị đau bụng")
# result = {
#     "message": "<câu trả lời tiếng Việt cho người dùng>",
#     "decision": {
#         "route": "TRIAGE" | "CLARIFY" | "NON_CLINICAL" | "GUARDRAIL",
#         "action": "ASK_NEXT" | "ASK_CONFIRMATION" | "RETURN_MATCH" | "RETURN_INCOMPLETE" | ...,
#         "subject_type": "SELF" | "OTHER_PERSON",
#         "subject_label": "con của bạn" | None,
#         "question_target_id": "fact_target:..." | None,
#         ... (concepts, facts đã ghi lượt này, lý do quyết định, v.v.)
#     }
# }
```

`agent.sessions: dict[str, Session]` là **in-memory, mất khi restart process,
không chia sẻ được giữa nhiều worker** — đây là điểm bắt buộc phải thay khi
ghép vào backend thật (xem mục "Chưa có, cần bổ sung" bên dưới).

## Dữ liệu cần mang theo

- `data/siu/*.jsonl` (4 file: `fact_targets.jsonl`, `protocol_atoms.jsonl`,
  `clinical_concepts.jsonl`, `concept_relations.jsonl`) — bộ luật lâm sàng
  thật, là nguồn duy nhất quyết định agent hỏi gì và kết luận gì.
- `data/indexes_siu/*` — embedding đã build sẵn khớp với đúng 4 file trên.
  Nếu sửa nội dung `retrieval.text`/alias trong `data/siu`, phải build lại
  index này (`scripts/build_indexes.py` — **có gọi OpenAI thật, tốn phí**,
  không tự chạy nếu không được yêu cầu).
- KHÔNG cần `data/mock_corpus/` + `data/indexes/` — đó chỉ là fixture nhỏ
  riêng cho `tests/test_simple_agent.py`, không dùng khi chạy thật.

## Cấu hình runtime

- Biến môi trường bắt buộc: `OPENAI_API_KEY`.
- Biến môi trường tùy chọn: `DEEP_TRIAGE_MODEL` (mặc định `gpt-4.1-mini` nếu
  không set — **không nên nâng cấp model** khi tích hợp trừ khi được yêu cầu
  rõ, vì mọi prompt/logic đã được tinh chỉnh và verify trên model này).
- Thư viện: `openai`, `python-dotenv`, `numpy` (xem `requirements.txt`).

## Các bất biến hành vi cần giữ khi ghép (để không hồi quy)

- `pain_severity` (và các fact kiểu DESCRIPTIVE_SEVERITY khác) chỉ được ghi
  số khi có mô tả định tính thật về mức độ trong cùng lượt — không được suy
  ra từ câu trả lời về khía cạnh khác (vd tính chất đau).
- Protocol atom đã truy xuất được **cộng dồn suốt phiên**
  (`session.seen_atom_ids`), không chỉ tính theo truy vấn của lượt hiện tại
  — tránh mất kết quả đã khớp trước đó vì một câu trả lời xác nhận cuối
  cùng không mang tín hiệu ngữ nghĩa gì.
- Hỏi hộ người khác (`subject=OTHER_PERSON`) giờ chạy **triage thật đầy đủ**
  cho người đó (không chỉ ghi nhận qua loa), với câu hỏi dùng đúng chủ ngữ,
  và giữ được tiến trình khi bệnh nhân chuyển qua lại giữa các chủ thể.
- Giới hạn tài nguyên cứng, không phải phán đoán ESI:
  `MAX_ASKED_FACTS_PER_SESSION=14` (số fact tối đa được hỏi/phiên),
  `MAX_TOOL_CALLS=6` (số lời gọi tool/lượt), `STALE_QUESTION_LIMIT=2` (số
  lần tối đa hỏi lại đúng một câu chưa được trả lời trước khi bỏ qua).
- Trước khi trả kết quả cuối, agent luôn hỏi xác nhận "còn gì bổ sung
  không" — không kết luận ngay khi vừa đủ dữ kiện.

## Test hồi quy

`tests/test_simple_agent.py` — 43 test, chạy offline (mock toàn bộ lời gọi
LLM/embedding, không tốn phí), dùng fixture `data/mock_corpus`+`data/indexes`
riêng. Chạy `pytest tests/test_simple_agent.py -q` sau bất kỳ thay đổi nào để
xác nhận không hồi quy.

## Chưa có, cần bổ sung khi lên backend thật

- Lớp HTTP/API (hiện chỉ có CLI `scripts/run_agent.py`).
- Lưu trữ session bền vững, dùng chung được giữa nhiều worker (Redis/DB) —
  `Session` có `set`/`dict` lồng nhau, cần viết (de)serialize riêng.
- Khóa/đồng bộ khi có request trùng `session_id` chạy cùng lúc.
- Auth thật gắn `session_id` với user đã xác thực (hiện caller tự truyền ID
  tùy ý).
- Retry/timeout khi gọi OpenAI (hiện chưa có ở `understanding.py`/
  `phrasing.py`/`resource_estimate.py` — lỗi mạng/rate-limit sẽ crash lượt).
- Theo dõi chi phí/rate-limit theo user trong runtime thật.

## Giới hạn đã biết (đừng overclaim khi mô tả lại cho người khác)

- Input mơ hồ, chung chung ("khó chịu trong người quá") đôi khi vẫn bị ép
  thành một concept cụ thể thay vì hỏi lại làm rõ.
- Một số fact định tính mơ hồ về khẩu ngữ (vd tính chất đau) đôi khi chỉ dừng
  ở ghi nhận mô tả, chưa map được sang enum cụ thể để dùng cho khớp atom.
- Tín hiệu `patient_wants_to_stop`/`confirmed_ready` do LLM tự quyết định
  mỗi lượt (không phải rule cứng) — không đảm bảo kích hoạt 100% mọi lần.
- Chỉ theo dõi **một chủ thể active tại một thời điểm** khi hỏi hộ người
  khác (có thể chuyển qua lại, không theo dõi song song nhiều người cùng lúc).

Chi tiết lịch sử các lần sửa lỗi/quyết định thiết kế nằm ở
`data/siu/MULTI_TURN_PROBE_FINDINGS.md` nếu cần tra cứu sâu hơn.
