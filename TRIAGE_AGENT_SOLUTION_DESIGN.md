# MedTriage AI Solution Design

Tài liệu tương thích này tồn tại vì workspace rules yêu cầu đọc
`TRIAGE_AGENT_SOLUTION_DESIGN.md` trước khi sửa backend.

Thiết kế runtime AI hiện hành nằm tại `ARCHITECTURE.md`. Thiết kế đó
thay custom LangGraph `StateGraph` bằng tool-gated DeepAgent supervisor, nhưng
giữ nguyên các yêu cầu an toàn lâm sàng sau:

- deterministic emergency reflex trước mọi LLM;
- structured DeepAgent semantic emergency assessment bắt buộc sau reflex âm tính,
  chỉ được nâng cảnh báo và không được tự chọn ESI;
- diagnosis/prescribing output firewall;
- patient confirmation và evidence authority gate;
- 100% citation provenance cho proposal không khẩn cấp;
- ESI/SBAR chỉ từ tool output đã verify;
- nurse Human-in-the-Loop và audit;
- fail-closed khi model, retrieval hoặc validation lỗi.

Đọc đầy đủ `ARCHITECTURE.md` và các skill
`medtriage-deepagent-system`, `medtriage-deepagent-router`,
`medtriage-rag-evidence`, `medtriage-clinical-safety` trước khi thay đổi runtime
AI hoặc patient-facing clinical output.
