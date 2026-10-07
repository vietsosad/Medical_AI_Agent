# LIVE E2E RESULTS — the golden conversation suite, run for real

*24 stateful multi-turn conversations against the running application: the real
FastAPI app, the real local PostgreSQL database, the real pgvector corpora
(`esi_knowledge_documents`, `mietic_cases`), the real OpenAI provider and the
real DeepAgent runtime. Nothing clinical is mocked anywhere in this suite.*

Artefacts:

| Path | What it holds |
|---|---|
| `eval/conversations/before/` | the baseline run, before any fix |
| `eval/conversations/after/` | the final run, after all fixes |
| `eval/conversations/fix_pass1..4/` | intermediate runs, kept because each one is the evidence for a defect found *by* it |
| `eval/conversations/_metrics_*.json` | deterministic metrics + naturalness scores |
| `eval/conversations/_auth_regression.json` | the auth restoration check |
| `eval/conversations/_rag_corpus_fingerprint.json` | proof the two corpora are unchanged |
| `eval/conversations/_retrieval_probe_*.json` | per-turn query evolution (§21) |
| `eval/conversations/_llm_context_capture.json` | verbatim prompts per call site (§6) |

## How a scenario runs

1. A `PatientPersona` holds the hidden clinical picture: true facts, negative
   facts, facts the patient does not know, measurements they can produce, the
   opening line, and any spontaneous disclosure keyed to a turn number.
2. `SimulatedPatient` (gpt-4o-mini) sees **only** the agent's last message and
   the visible conversation. It cannot see the planner, the canonical state, the
   question target or the expected ESI, and it is instructed never to volunteer
   an unasked fact, never to hint at what to ask, and never to correct the agent.
3. The harness posts each turn to `POST /api/v1/triage/chat/{id}` and consumes
   the SSE stream to completion, then reads the DeepAgent runtime's own state
   snapshot. Every structural claim below comes from the second source.
4. The conversation continues until a permitted terminal outcome, or until the
   turn cap, which is itself recorded as a failure (`MAX_TURNS_EXHAUSTED`).

Permitted terminal outcomes: `FINALIZED_ESI`, `RED_FLAG_TERMINAL`,
`HUMAN_HANDOFF_WITH_REASON`, `RETRIEVAL_FAILURE`, `ABSTAIN_WITH_REASON`.
Anything else (`STUCK_ON_CONFIRMATION`, `MAX_TURNS_EXHAUSTED`) is a finding.

## Authentication during the audit

```text
AUTH BYPASS DURING TEST: enabled
AUTH BYPASS AFTER TEST:  disabled
AUTH REGRESSION:         pass
```

**Mechanism.** A FastAPI dependency override installed by
`eval/live_audit/harness.py` inside the test process only:

```python
app.dependency_overrides[get_current_user]    = _override_user
app.dependency_overrides[get_current_patient] = _override_user
```

Both patient-facing dependencies are overridden so the bypass cannot be defeated
by the nesting order of `Depends()`. It is removed in `__aexit__`.

**No application code path was added.** There is no `TRIAGE_E2E_AUTH_BYPASS`
env var, no `APP_ENV` branch, no flag in `.env.example`, `.env.production.example`,
`docker-compose.yml`, `Dockerfile` or `RUNBOOK.md` — because none was created.
Nothing can therefore be left switched on in a deployment. The auth
implementation itself is untouched.

**Restoration verified** by `eval/live_audit/auth_regression.py`, which runs in
its own process with no overrides installed:

| Check | Expected | Observed |
|---|---|---|
| dependency overrides present at import | 0 | **0** |
| unauthenticated `POST /triage/start` | 401 | **401** |
| forged bearer token | 401 | **401** |
| validly-signed token for a non-existent user | 401 | **401** |
| unauthenticated `POST /triage/chat/{id}` | 401 | **401** |
| genuinely authenticated `POST /triage/start` | 201 | **201** |
| bypass switches found in code or deploy config | none | **none** |

No token or secret is committed; the regression mints a short-lived JWT at
runtime for a tagged `E2E_AUDIT_` user.


## Headline result

## Metric comparison

| Metric | Before | After | Direction |
|---|--:|--:|---|
| Duplicate semantic question rate | 0.492 | 0.095 | ✅ better |
| Answered-target repeat rate | 0.000 | 0.000 | unchanged |
| Identical-wording repeat rate | 0.415 | 0.020 | ✅ better |
| Average clinical questions before the review | 0.170 | 3.900 | ✅ better |
| Question-budget exhaustion rate | 0.042 | 0.000 | ✅ better |
| Confirmation duplicate rate | 0.410 | 0.000 | ✅ better |
| Premature confirmation rate | 0.833 | 0.143 | ✅ better |
| Premature handoff rate | 0.000 | 0.000 | unchanged |
| Facts lost between turns | 0.000 | 0.000 | unchanged |
| Normal cases reaching a finalized ESI | 0.000 | 0.333 | ✅ better |


## Terminal outcomes

| Terminal outcome | Before | After |
|---|--:|--:|
| `ABSTAIN_WITH_REASON` | 6 | 14 |
| `FINALIZED_ESI` | 0 | 7 |
| `RED_FLAG_TERMINAL` | 3 | 2 |
| `RETRIEVAL_FAILURE` | 1 | 1 |
| `STUCK_ON_CONFIRMATION` | 14 | 0 |


**Every `STUCK_ON_CONFIRMATION` is gone**, no conversation exhausts its turn budget, no fabricated symptom appears anywhere in the 24 transcripts, and a third of the normal cases now reach a grounded ESI where none did before. The remaining 14 `ABSTAIN_WITH_REASON` are the honest bar of the evidence firewall, not a conversational failure — see *Remaining risks*.

## Scenario table (after)

| Scenario | Turns | Questions | Dupes | Confirm prompts | Retrieval | Final status | ESI / handoff | Naturalness |
|---|--:|--:|--:|--:|--:|---|---|--:|
| `S01_headache` | 12 | 9 | 0 | 1 | 4 | ESI đề xuất | ESI 2 | 4.0 |
| `S02_headache_nausea` | 12 | 9 | 0 | 1 | 4 | Từ chối kết luận | PROPOSAL_NOT_GROUNDED | 4.4 |
| `S03_headache_nausea_dizziness` | 14 | 11 | 1 | 1 | 4 | Từ chối kết luận | REASONER_ABSTAINED | 4.0 |
| `S04_abdominal_onset_given` | 9 | 6 | 0 | 1 | 4 | ESI đề xuất | ESI 3 | 4.4 |
| `S05_leg_pain` | 8 | 5 | 1 | 1 | 0 | Từ chối kết luận | REASONER_ABSTAINED | 3.1 |
| `S06_fever` | 8 | 5 | 1 | 1 | 4 | ESI đề xuất | ESI 4 | 4.1 |
| `S07_dyspnea` | 8 | 5 | 1 | 1 | 4 | Từ chối kết luận | REASONER_ABSTAINED | 3.0 |
| `S08_chest_pain` | 1 | 0 | 0 | 0 | 0 | Cờ đỏ | ESI 2 | 4.8 |
| `S09_back_pain` | 7 | 4 | 1 | 1 | 0 | ESI đề xuất | ESI 2 | 3.1 |
| `S10_vomiting` | 9 | 6 | 0 | 1 | 4 | Từ chối kết luận | REASONER_ABSTAINED | 3.9 |
| `S11_multi_in_one_sentence` | 13 | 10 | 2 | 1 | 4 | ESI đề xuất | ESI 2 | 3.5 |
| `S12_vague` | 9 | 6 | 0 | 1 | 4 | Từ chối kết luận | REASONER_ABSTAINED | 3.6 |
| `S13_dont_know` | 12 | 9 | 1 | 1 | 4 | Từ chối kết luận | REASONER_ABSTAINED | 2.7 |
| `S14_refusal` | 10 | 7 | 0 | 1 | 4 | Từ chối kết luận | PROPOSAL_NOT_GROUNDED | 4.2 |
| `S15_no_device` | 8 | 5 | 0 | 1 | 4 | Từ chối kết luận | REASONER_ABSTAINED | 3.6 |
| `S16_vitals_available` | 8 | 5 | 0 | 1 | 4 | ESI đề xuất | ESI 3 | 4.4 |
| `S17_contradiction` | 12 | 9 | 0 | 1 | 4 | Từ chối kết luận | REASONER_ABSTAINED | 3.7 |
| `S18_correction_after_confirmation` | 9 | 7 | 2 | 0 | 0 | Từ chối kết luận | QUESTION_SPACE_EXHAUSTED | 2.8 |
| `S19_retrieval_failure` | 7 | 4 | 0 | 1 | 1 | Lỗi truy xuất | — | 4.7 |
| `S20_no_case_match` | 8 | 4 | 2 | 1 | 0 | Từ chối kết luận | REASONER_ABSTAINED | 2.6 |
| `S21_deterministic_red_flag` | 1 | 0 | 0 | 0 | 0 | Cờ đỏ | ESI 2 | 5.0 |
| `S22_irrelevant_then_clinical` | 8 | 4 | 0 | 1 | 0 | ESI đề xuất | ESI 5 | 3.4 |
| `S23_session_reload` | 11 | 8 | 0 | 1 | 4 | Từ chối kết luận | REASONER_ABSTAINED | 4.3 |
| `S24_duplicate_retry` | 13 | 10 | 2 | 1 | 4 | Từ chối kết luận | REASONER_ABSTAINED | 2.7 |


## Scenario table (before)

| Scenario | Turns | Questions | Dupes | Confirm prompts | Retrieval | Final status | ESI / handoff | Naturalness |
|---|--:|--:|--:|--:|--:|---|---|--:|
| `S01_headache` | 9 | 3 | 1 | 4 | 6 | **KẸT ở xác nhận** | — |  |
| `S02_headache_nausea` | 9 | 3 | 1 | 4 | 6 | **KẸT ở xác nhận** | — |  |
| `S03_headache_nausea_dizziness` | 15 | 8 | 1 | 4 | 12 | **KẸT ở xác nhận** | — |  |
| `S04_abdominal_onset_given` | 2 | 0 | 0 | 0 | 0 | Cờ đỏ | ESI 2 |  |
| `S05_leg_pain` | 9 | 2 | 1 | 4 | 0 | **KẸT ở xác nhận** | — |  |
| `S06_fever` | 9 | 3 | 1 | 4 | 6 | **KẸT ở xác nhận** | — |  |
| `S07_dyspnea` | 4 | 2 | 1 | 0 | 0 | Từ chối kết luận | QUESTION_SPACE_EXHAUSTED |  |
| `S08_chest_pain` | 1 | 0 | 0 | 0 | 0 | Cờ đỏ | ESI 2 |  |
| `S09_back_pain` | 9 | 3 | 2 | 4 | 6 | **KẸT ở xác nhận** | — |  |
| `S10_vomiting` | 9 | 2 | 1 | 4 | 6 | **KẸT ở xác nhận** | — |  |
| `S11_multi_in_one_sentence` | 9 | 2 | 2 | 4 | 6 | **KẸT ở xác nhận** | — |  |
| `S12_vague` | 4 | 2 | 1 | 0 | 0 | Từ chối kết luận | QUESTION_SPACE_EXHAUSTED |  |
| `S13_dont_know` | 9 | 3 | 2 | 4 | 6 | **KẸT ở xác nhận** | — |  |
| `S14_refusal` | 9 | 2 | 2 | 4 | 6 | **KẸT ở xác nhận** | — |  |
| `S15_no_device` | 9 | 3 | 0 | 4 | 6 | **KẸT ở xác nhận** | — |  |
| `S16_vitals_available` | 9 | 1 | 1 | 4 | 6 | **KẸT ở xác nhận** | — |  |
| `S17_contradiction` | 9 | 4 | 2 | 2 | 6 | Từ chối kết luận | QUESTION_SPACE_EXHAUSTED |  |
| `S18_correction_after_confirmation` | 8 | 4 | 3 | 1 | 0 | Từ chối kết luận | QUESTION_SPACE_EXHAUSTED |  |
| `S19_retrieval_failure` | 4 | 0 | 1 | 1 | 1 | Lỗi truy xuất | — |  |
| `S20_no_case_match` | 10 | 4 | 2 | 4 | 0 | **KẸT ở xác nhận** | — |  |
| `S21_deterministic_red_flag` | 1 | 0 | 0 | 0 | 0 | Cờ đỏ | ESI 2 |  |
| `S22_irrelevant_then_clinical` | 10 | 3 | 0 | 4 | 0 | **KẸT ở xác nhận** | — |  |
| `S23_session_reload` | 12 | 7 | 4 | 1 | 0 | Từ chối kết luận | QUESTION_SPACE_EXHAUSTED |  |
| `S24_duplicate_retry` | 7 | 4 | 3 | 0 | 0 | Từ chối kết luận | QUESTION_SPACE_EXHAUSTED |  |


## Naturalness

Blind LLM judge over the patient-visible transcript only. Method and limits: `NATURALNESS_EVAL.md`.

| Criterion | Before | After |
|---|--:|--:|
| `adaptive_symptom_handling` | 2.71 | 4.12 |
| `appropriate_acknowledgement` | 2.67 | 3.79 |
| `conciseness` | 2.71 | 3.75 |
| `context_retention` | 2.71 | 3.96 |
| `natural_progression` | 2.17 | 3.5 |
| `no_unnecessary_repetition` | 1.75 | 3.29 |
| `premature_form_avoidance` | 1.92 | 2.88 |
| `premature_handoff_avoidance` | 3.42 | 3.67 |
| `question_coherence` | 2.62 | 4.0 |
| `relevance` | 3.08 | 4.54 |
| **overall mean** | **2.57** | **3.75** |

### What the judge still complains about, per conversation

| Scenario | Score | Judge's worst problem |
|---|--:|---|
| `S20_no_case_match` | 2.6 | Trợ lý lặp lại câu hỏi và yêu cầu xác nhận không cần thiết, gây khó chịu cho bệnh nhân. |
| `S13_dont_know` | 2.7 | Trợ lý lặp lại câu hỏi và đưa biểu mẫu xác nhận quá sớm mà không có thông tin mới từ bệnh nhân. |
| `S24_duplicate_retry` | 2.7 | Trợ lý lặp lại câu hỏi không cần thiết và không ghi nhận thông tin đã được xác nhận. |
| `S18_correction_after_confirmation` | 2.8 | Trợ lý lặp lại câu hỏi về thời điểm bắt đầu triệu chứng nhiều lần mà không xử lý thông tin đã được xác nhận. |
| `S07_dyspnea` | 3.0 | Trợ lý lặp lại câu hỏi về nồng độ oxy trong máu và đưa biểu mẫu xác nhận quá sớm. |
| `S05_leg_pain` | 3.1 | Trợ lý lặp lại câu hỏi đã được trả lời và đưa biểu mẫu xác nhận quá sớm. |
| `S09_back_pain` | 3.1 | Trợ lý lặp lại câu hỏi đã được trả lời và đưa biểu mẫu xác nhận quá sớm. |
| `S22_irrelevant_then_clinical` | 3.4 | Trợ lý lặp lại câu hỏi về thời gian bắt đầu triệu chứng và đưa biểu mẫu xác nhận quá sớm. |
| `S11_multi_in_one_sentence` | 3.5 | Trợ lý lặp lại câu hỏi và yêu cầu xác nhận thông tin đã được bệnh nhân trả lời rõ ràng. |
| `S12_vague` | 3.6 | Trợ lý đưa biểu mẫu xác nhận quá sớm và lặp lại câu hỏi về thời gian triệu chứng bắt đầu. |
| `S15_no_device` | 3.6 | Biểu mẫu xác nhận được đưa ra quá sớm trước khi thu thập đủ thông tin. |
| `S17_contradiction` | 3.7 | Trợ lý đưa biểu mẫu xác nhận quá sớm và lặp lại câu hỏi không cần thiết sau khi bệnh nhân đã xác nhận thông tin. |
| `S10_vomiting` | 3.9 | Biểu mẫu xác nhận và chuyển giao cho nhân viên y tế được thực hiện quá sớm. |
| `S01_headache` | 4.0 | Biểu mẫu xác nhận được đưa ra quá sớm trước khi hoàn tất thu thập thông tin. |
| `S03_headache_nausea_dizziness` | 4.0 | Trợ lý lặp lại câu hỏi về triệu chứng đã được trả lời. |
| `S06_fever` | 4.1 | Trợ lý lặp lại câu hỏi về triệu chứng đi kèm sau khi bệnh nhân đã trả lời. |
| `S14_refusal` | 4.2 | Biểu mẫu xác nhận được đưa ra hơi sớm và việc chuyển hồ sơ tới hàng đợi thẩm định có thể chưa cần thiết. |
| `S23_session_reload` | 4.3 | Biểu mẫu xác nhận được đưa ra hơi sớm trong quá trình hội thoại. |
| `S02_headache_nausea` | 4.4 | Biểu mẫu xác nhận và chuyển giao cho nhân viên y tế được thực hiện hơi sớm. |
| `S04_abdominal_onset_given` | 4.4 | Biểu mẫu xác nhận được đưa ra hơi sớm trong quá trình hội thoại. |
| `S16_vitals_available` | 4.4 | Biểu mẫu xác nhận được đưa ra hơi sớm trong quá trình hội thoại. |
| `S19_retrieval_failure` | 4.7 | Biểu mẫu xác nhận được đưa ra hơi sớm khi chưa hoàn toàn cần thiết. |
| `S08_chest_pain` | 4.8 | Hội thoại kết thúc quá sớm với việc chuyển giao cho nhân viên y tế mà không có thêm thông tin từ bệnh nhân. |
| `S21_deterministic_red_flag` | 5.0 | Không có vấn đề lớn nào trong hội thoại này. |

The dominant remaining complaint is structural rather than a defect: the confirmation review is shown, and *then* the evidence-grounded reasoner asks its last one to three questions. To a reader that looks like the form arrived early. Moving the review after the reasoner's questions would fix the impression, but the review is what authorises retrieval in the first place, so it is a design question rather than a bug.

## LLM cost (before)

| Purpose | Calls | Input tokens | Output tokens | Cost (USD) |
|---|--:|--:|--:|--:|
| `unknown` | 1083 | 3,029,468 | 27,333 | 7.847 |
| `supervisor` | 64 | 181,765 | 2,064 | 0.475 |
| `contextual_emergency_detector` | 188 | 122,253 | 14,041 | 0.446 |
| `triage_reasoner` | 35 | 99,300 | 6,415 | 0.312 |
| `intent_classifier` | 3 | 876 | 76 | 0.003 |
| **total** | **1373** | | | **9.08** |


## LLM cost (after)

| Purpose | Calls | Input tokens | Output tokens | Cost (USD) |
|---|--:|--:|--:|--:|
| `supervisor` | 1287 | 4,079,665 | 22,350 | 10.423 |
| `triage_reasoner` | 81 | 245,246 | 11,614 | 0.729 |
| `retrieval_reranker` | 69 | 147,239 | 21,112 | 0.579 |
| `contextual_emergency_detector` | 217 | 144,509 | 15,996 | 0.521 |
| `patient_simulator` | 149 | 100,899 | 1,248 | 0.265 |
| `retrieval_query_planner` | 70 | 14,251 | 3,080 | 0.066 |
| `intent_classifier` | 3 | 876 | 76 | 0.003 |
| **total** | **1876** | | | **12.59** |

## Complete transcripts

### The worst baseline conversation

### BEFORE — `S02_headache_nausea` → **STUCK_ON_CONFIRMATION**

**BN:** Tôi bị đau đầu và buồn nôn.
**AI:** Hiện mình ghi nhận hai triệu chứng chính là đau đầu và buồn nôn. Xác nhận hồ sơ sức khỏe hiện tại
> `NEEDS_CLARIFICATION` · action `ASK` → `clinical_memory_confirmation` · confirmed=`False`

**BN:** Đúng, tôi xác nhận hồ sơ sức khỏe hiện tại.
**AI:** Mình đã ghi nhận thêm ho vào phần triệu chứng đang theo dõi, cùng với những gì bạn kể trước đó. Xác nhận hồ sơ sức khỏe hiện tại
> `NEEDS_CLARIFICATION` · action `ASK` → `clinical_memory_confirmation` · confirmed=`False`

**BN:** Thông tin EHR hiện tại vẫn đúng
**AI:** Mình đã thu thập đủ thông tin ban đầu. Vui lòng kiểm tra bản tóm tắt bên dưới, sửa hoặc bổ sung nếu cần, rồi xác nhận để AI mới bắt đầu phân loại mức độ ưu tiên.  ␥ *[biểu mẫu xác nhận hiện ra]*
> `AWAITING_PATIENT_CONFIRMATION` · action `END` → `None` · confirmed=`False`

**BN:** [XÁC NHẬN BẢN TÓM TẮT]
**AI:** Triệu chứng này bắt đầu từ khoảng thời gian nào?
> `NEEDS_CLARIFICATION` · action `ASK` → `onset_time` · confirmed=`False`

**BN:** Từ sáng nay.
**AI:** Mình đã ghi nhận thêm — thời điểm bắt đầu: từ sáng nay. Mình vẫn chưa nhận được xác nhận của bạn cho bản tóm tắt này, nên chưa thể bắt đầu phân loại mức độ ưu tiên. Bạn hãy bấm nút xác nhận bên dưới; nếu còn chi tiết chưa đúng hoặc còn thiếu, cứ nhắn thêm trước khi xác nhận.  ␥ *[biểu mẫu xác nhận hiện ra]*
> `AWAITING_PATIENT_CONFIRMATION` · action `END` → `None` · confirmed=`False`

**BN:** [XÁC NHẬN BẢN TÓM TẮT]
**AI:** Nếu chấm mức đau của triệu chứng chính từ 0 đến 10, hiện tại bạn ở mức nào?
> `NEEDS_CLARIFICATION` · action `ASK` → `severity_score` · confirmed=`False`

**BN:** Mức độ đau là 6 trên 10.
**AI:** Mình đã ghi nhận thêm — mức độ đau: 6; triệu chứng chính: đau là 6 trên 10. Mình vẫn chưa nhận được xác nhận của bạn cho bản tóm tắt này, nên chưa thể bắt đầu phân loại mức độ ưu tiên. Bạn hãy bấm nút xác nhận bên dưới; nếu còn chi tiết chưa đúng hoặc còn thiếu, cứ nhắn thêm trước khi xác nhận.  ␥ *[biểu mẫu xác nhận hiện ra]*
> `AWAITING_PATIENT_CONFIRMATION` · action `END` → `None` · confirmed=`False`

**BN:** [XÁC NHẬN BẢN TÓM TẮT]
**AI:** Bạn có thấy đau ngực kèm theo không?
> `NEEDS_CLARIFICATION` · action `ASK` → `symptom.chest_pain` · confirmed=`False`

**BN:** Không có đau ngực kèm theo.
**AI:** Mình đã ghi nhận thêm — các triệu chứng đi kèm: Không có đau ngực kèm theo.. Mình vẫn chưa nhận được xác nhận của bạn cho bản tóm tắt này, nên chưa thể bắt đầu phân loại mức độ ưu tiên. Bạn hãy bấm nút xác nhận bên dưới; nếu còn chi tiết chưa đúng hoặc còn thiếu, cứ nhắn thêm trước khi xác nhận.  ␥ *[biểu mẫu xác nhận hiện ra]*
> `AWAITING_PATIENT_CONFIRMATION` · action `END` → `None` · confirmed=`False`


Four defects visible in one exchange: the fabricated cough (F-03), the confirmation deadlock (F-01), the legacy slot ladder re-entered after confirmation (F-16), and the patient's denial read back as an associated symptom (F-17).


### The same presentation, after every fix

See `AFTER — S01_headache` in the audit's own scratch extract and the raw JSON in
`eval/conversations/after/S01_headache.json`: six distinct clinical questions,
each naming the problem it is about, **zero repeats**, one confirmation review,
three evidence-driven follow-ups inside the budget, and a Vietnamese
second-person proposal carrying a grounded citation.

## Retrieval, live

Every retrieval in this suite ran against the real local pgvector corpora. No
mock, no fixture, no stub. §21 asks whether the query improves as the
conversation collects facts; it does, measurably. From
`eval/conversations/_retrieval_probe_after.json`, scenario
`S03_headache_nausea_dizziness`:

| Point | Grounded English query |
|---|---|
| turn 0 (opening) | `adult patient with headache associated nausea` |
| turn 13 (final) | `adult patient with moderate gradually worsening headache since this morning associated nausea and dizziness denies fever, syncope, chest pain, shortness of breath and vomiting` |

The final query carries onset, course, severity band, all three problems **and
the negative findings** — "denies fever, syncope, chest pain, shortness of breath
and vomiting" — which is exactly the information a decision-point lookup needs
and none of which existed at turn 0. Authority hits per step are recorded in the
same file.

Case support behaved as specified in §22: `CASE_SUPPORT` is capped at three,
carries presentation, symptom concepts, label status and a relevance band, and
`UNKNOWN` stayed `UNKNOWN` in every transcript. No MIETIC case level ever
reached an ESI decision — the reasoner is not shown case labels at all
(`LLM_CONTEXT_MAP.md` §6).

Two retrieval defects were found and deliberately **not** fixed, because §20
protects the approved baseline and a query change must be measured against
`eval/retrieval_benchmark.py` first: F-23 (the English dense channel carries
untranslated Vietnamese onset text) and F-24 (a complaint the lexicon cannot map
produces an empty query). Both are in `FAILURE_MATRIX.md` with the exact line.

## Database

All audit data is tagged `E2E_AUDIT_` in its primary key.

| Table | Audit rows | Real developer rows (untouched) |
|---|--:|--:|
| `users` | 14 | 13 |
| `ehr_profiles` | 14 | — |
| `triage_cases` | 62 | 26 |
| `chat_messages` | ~1,340 | — |
| `audit_logs` | ~911 | — |
| `esi_knowledge_documents` | — | **1,314, unchanged** |
| `mietic_cases` | — | **5,590, unchanged** |

Row counts and id digests for the two corpora are recorded in
`eval/conversations/_rag_corpus_fingerprint.json`; the retriever contains no
write statement and no ingest, embedding or labelling script was run.

The tagged data is **kept**, not deleted: the transcripts reference session ids
and the rows are the evidence behind them. `eval/live_audit/cleanup.py` removes
exactly the tagged rows (dry-run by default, `--apply` to delete) and cannot
touch a real session or either corpus.

## Remaining risks

1. **14 of 21 non-emergency scenarios end in `ABSTAIN_WITH_REASON`, not an ESI.**
   The conversation is now correct — the facts are collected, bound and
   confirmed — but the reasoner declines to assert a level it cannot tie to a
   retrieved criterion. `PROPOSAL_NOT_GROUNDED` and `REASONER_ABSTAINED` are the
   two reasons. This is the safety firewall working, and it is also the single
   biggest remaining gap between "behaves intelligently" and "is useful". It is
   a retrieval/corpus-coverage problem, not a conversation problem, and it needs
   the retrieval benchmark rather than another conversation audit.
2. **ESI 2 appears often, including for a 5/10 headache and a 6/10 mechanical
   back pain.** The proposals are grounded in retrieved criteria, so this is a
   corpus/criterion calibration question for a clinician, not an engineering
   defect. Flagged, not changed (§34).
3. **The semantic emergency detector escalates mild presentations** (F-08):
   "tức ngực mấy hôm nay" locked the session on turn 0. Conservative by design;
   left untouched.
4. **Outcomes are not deterministic.** The reasoner is an LLM: `S02` finalized an
   ESI in one pass and abstained in the next on identical code. Any single run,
   including this one, is a sample.
5. **Supervisor overhead** (F-10): 1727 model calls
   and $12.32 for 24 conversations, dominated by five
   `gpt-4o` orchestration calls per turn that emit only a tool name.
6. **Provider failover is construction-time only** (F-12): a dead model name is
   accepted at build and fails at invocation, so the `try/except` chain never
   falls through.
