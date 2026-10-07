# Adaptive conversation transcript

Live run against the local `mietic_cases` corpus (read-only). Every agent turn below was chosen by the planner; nothing in the script tells it what to ask.

## Conversation

**Người bệnh:** Tôi bị đau đầu và buồn nôn

**AI Triage:** Hiện mình ghi nhận hai triệu chứng chính là đau đầu và buồn nôn. Tình trạng đau đầu bắt đầu từ khi nào?

> `sufficiency=SAFETY_CRITICAL_MISSING` `action=ASK` `target=headache.onset_time` `response_type=TEXT`

**Người bệnh:** Đau từ sáng nay, khoảng 6/10

**AI Triage:** Đây có phải cơn đau đầu dữ dội nhất bạn từng gặp không?

> `sufficiency=SAFETY_CRITICAL_MISSING` `action=ASK` `target=headache.worst_ever` `response_type=TEXT`

**Người bệnh:** Tôi còn hơi chóng mặt nữa

**AI Triage:** Mình đã ghi nhận thêm chóng mặt vào phần triệu chứng đang theo dõi, cùng với những gì bạn kể trước đó. Đây có phải cơn đau đầu dữ dội nhất bạn từng gặp không?

> `sufficiency=SAFETY_CRITICAL_MISSING` `action=ASK` `target=headache.worst_ever` `response_type=TEXT`

**Người bệnh:** Không phải, tôi từng đau nặng hơn

**AI Triage:** Kèm theo đau đầu, bạn có thấy yếu hoặc tê một bên người, nói khó, hay nhìn mờ/nhìn đôi không?

> `sufficiency=SAFETY_CRITICAL_MISSING` `action=ASK` `target=headache.associated_neuro` `response_type=TEXT`

**Người bệnh:** Không yếu tay chân, không nói khó, nhìn vẫn rõ

**AI Triage:** Đau đầu xuất hiện đột ngột hay tăng dần lên? Hiện đang nặng thêm, giữ nguyên hay đỡ hơn?

> `sufficiency=SAFETY_CRITICAL_MISSING` `action=ASK` `target=headache.course` `response_type=TEXT`

**Người bệnh:** Đau tăng dần lên, giờ nặng hơn lúc sáng

**AI Triage:** Bạn có thấy sốt kèm theo không?

> `sufficiency=SAFETY_CRITICAL_MISSING` `action=ASK` `target=symptom.fever` `response_type=STRUCTURED_QUESTION`

**Người bệnh:** Không sốt

**AI Triage:** Bạn có thấy ngất kèm theo không?

> `sufficiency=SAFETY_CRITICAL_MISSING` `action=ASK` `target=symptom.syncope` `response_type=STRUCTURED_QUESTION`

**Người bệnh:** Không, tôi không bị ngất

**AI Triage:** Mình đã thu thập đủ thông tin ban đầu. Vui lòng kiểm tra bản tóm tắt bên dưới, sửa hoặc bổ sung nếu cần, rồi xác nhận để AI mới bắt đầu phân loại mức độ ưu tiên.

> `sufficiency=USEFUL_BUT_OPTIONAL` `action=END` `target=None` `response_type=INTAKE_REVIEW`

## Working state the agent built

```
Active problems
├─ headache (primary)
│  ├─ onset_time: sáng nay
│  ├─ course: tăng dần
│  ├─ severity_score: 6
│  ├─ location: ?
│  ├─ character: ?
│  ├─ radiation: ?
│  ├─ worst_ever: không (Không phải, tôi từng đau nặng hơn)
│  ├─ associated_neuro: không (Không yếu tay chân, không nói khó, nhìn vẫn rõ)
│  └─ fever: không (False)
├─ nausea
│  ├─ onset_time: ?
│  ├─ course: ?
│  ├─ severity_score: ?
│  ├─ vomiting: ?
│  ├─ frequency: ?
│  └─ relation_to_primary: ?
└─ dizziness
   ├─ onset_time: ?
   ├─ course: ?
   ├─ severity_score: ?
   ├─ syncope: không (False)
   └─ relation_to_primary: ?
```

## Confirmation checkpoint (auto-filled from canonical state)

- Triệu chứng: đau đầu, buồn nôn
- Khởi phát: sáng nay
- Mức độ: 6
- Triệu chứng kèm theo: buồn nôn
- Bạn có nhắc tới nhưng chưa chắc chắn: chóng mặt
- Sinh hiệu: chưa có số đo

## Retrieval query

**BEFORE** — one mixed-language string, embedded once:

```
đau đầu; buồn nôn; khởi phát sáng nay; mức độ 6/10. headache; nausea; vomiting; patient-reported onset: sáng nay; severity 6/10. headache nausea vomiting
```

**AFTER** — grounded clinical English, several scoped queries:

```
primary         moderate gradually worsening headache since this morning
associated      headache with nausea and dizziness
overall         adult patient with moderate gradually worsening headache since this morning associated nausea and dizziness denies fever and syncope
```

## Case support retrieved

**BEFORE** — dense top-5, all rendered as `% tương đồng`:

- `mietic_c_d7b122432011f67a786d` cosine=0.580 concepts=['headache', 'nausea', 'vomiting']
  - Patient: 19 years, female Vitals: dbp 63, hr 81, rr 13, sbp 103, spo2 100, temp_c 37.1 Presentation: 19-year-old whi...
- `mietic_c_4b3c2c996b36169950d2` cosine=0.543 concepts=[]
  - Patient: 30 years, male Vitals: dbp 86, hr 100, rr 20, sbp 135, spo2 95 Presentation: A 30-year-old white male prese...
- `mietic_c_f5bf652515616075a1a1` cosine=0.535 concepts=['headache', 'nausea']
  - Patient: 52 years, female Vitals: dbp 80, hr 72, rr 18, sbp 140, spo2 100 Presentation: 52-year-old Black/African Am...
- `mietic_c_aebdc497c8eaebb2625b` cosine=0.530 concepts=['headache', 'nausea', 'vomiting']
  - Patient: 45 years, female Vitals: dbp 97, hr 90, rr 16, sbp 133, spo2 96, temp_c 36.4 Presentation: The patient is a...
- `mietic_c_2789203eba6497ad711f` cosine=0.517 concepts=['nausea', 'vomiting']
  - Patient: 65 years, female Vitals: dbp 91, hr 94, rr 16, sbp 151, spo2 100, temp_c 36.1 Presentation: The patient is ...

**AFTER** — fused, reranked, filtered to what is worth showing (floor 0.3, cap 3):

- `mietic_c_145db48942f91a008b63` relevance=0.89 channels=['dense:associated', 'lexical:associated'] concepts=['dizziness', 'headache', 'nausea'] esi=3 label=CONSISTENT
  - Patient: 33 years, male Vitals: dbp 63, hr 81, rr 16, sbp 133, spo2 100, temp_c 37.1 Presentation: A 33-year-old whi...
- `mietic_c_be91be078aef8c0d8b2a` relevance=0.89 channels=['dense:associated', 'lexical:associated'] concepts=['dizziness', 'headache', 'nausea', 'syncpore', 'vomiting'] esi=1 label=CONSISTENT
  - Patient: 36 years, female Presentation: A 36-year-old female with a history of hypertension and anxiety/depression p...
- `mietic_c_ab78314275f24945f2ad` relevance=0.89 channels=['dense:associated', 'lexical:associated'] concepts=['dizziness'] esi=None label=UNKNOWN
  - Patient: 54 years, female Vitals: dbp 58, hr 78, rr 17, sbp 110, spo2 99, temp_c 37.0 Presentation: A 54-year-old Hi...

## Summary

- Patient concepts: `['dizziness', 'headache', 'nausea']`
- BEFORE: 4/5 shown cases share a presenting concept
- AFTER:  3/3 shown cases share a presenting concept

