# Báo cáo kiểm tra bộ ca generated_mock_v2

Sinh tự động bởi `validate_dataset.py`. Mọi con số dưới đây được tính lại từ các tệp JSONL và từ corpus, không chép từ metadata của bước dựng.

**Kết quả chung: PASS**

| Kiểm tra | Kết quả | Tóm tắt |
|---|---|---|
| 1. Cấu trúc và kiểu dữ liệu so với schema hiện có | PASS | 590 bản ghi, 4 tệp; mỗi tệp có ca smoke; khoá từng mục so với simple_agent_golden_300.jsonl. |
| 2. Lời thoại khớp với dữ kiện kỳ vọng | PASS | 6259 dữ kiện có giá trị đều có câu trả lời riêng; 281 dữ kiện 'không biết' đều có câu trả lời nói rõ là không biết. |
| 3. Dữ kiện hợp lệ theo schema của corpus PostgreSQL | PASS | Mọi dữ kiện của 590 bản ghi nằm trong enum/khoảng của corpus, có dữ kiện mở cổng đi kèm, đúng giới tính. |
| 4. Nhãn tính lại độc lập bằng golden_validator.satisfied_esi | PASS | 590 nhãn được tính lại từ 1711 tiêu chí CLINICAL_AUTHORITY. |
| 5. Vân tay corpus và checksum manifest | PASS | Vân tay tiêu chí, dữ kiện, concept và checksum của 4 manifest được đối chiếu với PostgreSQL hiện tại. |
| 6. Đối chiếu độc lập với AHRQ ESI v5 và phân loại hàng chờ duyệt | PASS | Kết luận: AGREE 29, CANNOT_VERIFY 50, CONSISTENT 505, DISAGREE_OVER 1, DISAGREE_UNDER 5. |
| 7. Trùng lặp và gần trùng | PASS | 0 lời mở đầu trùng hệt; 0 cặp có độ giống ký tự (4-gram Jaccard) >= 0.5; 0 bản ghi chia chung một bộ dữ kiện với bản ghi khác (khác hồ sơ); độ giống cao nhất với bộ 30/300 ca hiện có: 0.34. |
| 8. Chia tập 70/15/15, không rò rỉ, test có ca khó | PASS | train 339 (69.8%), validation 73 (15.0%), test 74 (15.2%); 70/74 ca test có ít nhất một nhãn tình huống biên; không gia đình, cụm, bộ dữ kiện hay cặp gần trùng nào vắt qua hai tập. |
| 9. Các đợt đã khoá giữ nguyên so với split_lock.json | PASS | 590 bản ghi đã khoá (đợt 1, 2, 3) khớp từng byte với khoá, đúng tệp và cờ smoke (5 lần sửa có chủ đích, tổng 222 bản ghi, chỉ ở trường ['adaptive_dialogue.allowed_question_target_ids', 'adaptive_dialogue.answers_by_fact_target', 'adaptive_dialogue.clarification_reply', 'expected_decision.acceptable_matched_atom_ids', 'expected_retrieval', 'expected_retrieval.acceptable_atom_ids', 'expected_state.facts', 'expected_state.unknown_fact_ids', 'postgres_provenance', 'postgres_provenance.embedding_fingerprints', 'postgres_provenance.fact_target_fingerprints', 'postgres_provenance.fact_target_ids', 'postgres_provenance.relation_fingerprints', 'presentation.contains_temporal_context', 'presentation.initial_message', 'smoke']); không còn bản ghi chưa khoá. |

## Độ phủ

| Chỉ số | Giá trị |
|---|---|
| records | 590 |
| by_batch | {"1": {"records": 200, "verified": 146, "labels": {"esi_1": 9, "esi_2": 111, "esi_3": 16, "esi_4": 14, "esi_5": 18, "incomplete": 32}, "distinct_primary_atoms": 117}, "2": {"records": 200, "verified": 169, "labels": {"esi_1": 17, "esi_2": 128, "esi_3": 13, "esi_4": 2, "esi_5": 4, "incomplete": 36}, "distinct_primary_atoms": 158, "primary_atoms_not_in_batch_1": 147}, "3": {"records": 190, "verified": 171, "labels": {"esi_2": 169, "esi_3": 2, "esi_4": 2, "esi_5": 1, "incomplete": 16}, "distinct_primary_atoms": 174}} |
| groups | {"CONFLICTING": 55, "MISSING_INFO": 80, "COMPLEX_DIALOGUE": 50, "COMMON": 150, "MULTI_SYMPTOM": 130, "RED_FLAG": 125} |
| labels | {"esi_2": 408, "incomplete": 84, "esi_3": 31, "esi_1": 26, "esi_4": 18, "esi_5": 23} |
| labels_by_file | {"train": {"esi_2": 273, "incomplete": 33, "esi_3": 15, "esi_1": 16, "esi_4": 2}, "validation": {"esi_2": 58, "incomplete": 7, "esi_3": 3, "esi_5": 1, "esi_1": 4}, "test": {"esi_2": 58, "incomplete": 7, "esi_3": 4, "esi_1": 4, "esi_5": 1}, "needs_medical_review": {"esi_4": 16, "incomplete": 37, "esi_5": 21, "esi_2": 19, "esi_3": 9, "esi_1": 2}} |
| verified_labels | {"esi_2": 389, "incomplete": 47, "esi_3": 22, "esi_1": 24, "esi_4": 2, "esi_5": 2} |
| age_band | {"adult": 466, "toddler": 10, "adolescent": 41, "school_age": 40, "preschooler": 12, "infant": 18, "neonate": 3} |
| older_adults_65_plus | 139 |
| sex | {"Male": 312, "Female": 278} |
| relationship | {"SELF": 306, "CHILD": 93, "OTHER": 73, "SPOUSE": 42, "PARENT": 67, "SIBLING": 9} |
| narrator | {"SELF": 306, "CAREGIVER": 284} |
| with_chronic_conditions | 208 |
| with_daily_medications | 174 |
| with_allergies | 73 |
| terminal_action | {"RETURN_MATCH": 506, "RETURN_INCOMPLETE": 84} |
| with_unknown_facts | 164 |
| with_resource_count | 47 |
| with_temporal_context | 513 |
| distinct_fact_targets_valued | 232 |
| distinct_fact_targets_unknown | 78 |
| distinct_primary_atoms | 432 |
| decision_points | {"B_HIGH_RISK": 354, "D_RESOURCE_PREDICTION": 72, "A_IMMEDIATE_LIFESAVING": 26, "C_DANGER_ZONE_VITALS": 54} |
| distinct_concepts | 398 |
| edge_tags | {"caregiver": 233, "comorbidity": 157, "older_adult": 138, "negation": 92, "pediatric": 84, "collateral_history": 76, "null_unknown": 55, "contradiction": 52, "occupational": 49, "dialect": 48, "minimization": 44, "pregnancy": 42, "missing_vitals": 41, "adolescent": 40, "abbreviation": 39, "hidden_red_flag": 38, "corpus_gap": 37, "decisive_despite_missing": 34, "environmental": 34, "changed_answer": 32, "anticoagulant": 25, "toxic": 21, "no_diacritics": 19, "requests_prescription": 14, "mental_health": 14, "progressive_disclosure": 13, "unknown_onset": 12, "minimal_pair": 11, "single_decisive_symptom": 11, "post_procedure": 11, "vitals_inconsistent": 10, "vague_answer": 10, "folk_remedy": 10, "long_multi_symptom": 8, "intoxication": 8, "social_pressure": 7, "age_adjusted_vitals": 7, "caregiver_remote": 7, "baseline_cognitive_impairment": 7, "multiple_victims": 6, "postpartum": 6, "polypharmacy": 6, "immunocompromised": 5, "sensitive_topic": 5, "subject_switch": 5, "typo": 5, "medication_nonadherence": 4, "unreadable_label": 4, "late_disclosure": 4, "unknown_mechanism": 4, "units": 3, "multiple_complaints": 3, "indirect_phrasing": 3, "near_miss": 3, "masked_tachycardia": 3, "communication_barrier": 3, "language_barrier": 3, "device_error": 2, "remote_location": 2, "time_corrected": 2, "off_target_answer": 2, "school_setting": 2, "medication_question": 2, "folk_belief": 2, "institutional_care": 2, "atypical_presentation": 2, "slang": 2, "wrong_location": 1, "narrator_switch": 1, "highland_setting": 1, "road_traffic": 1, "concealment": 1, "sports": 1, "cultural_practice": 1, "subacute": 1, "recent_viral_illness": 1, "alcohol_related": 1, "travel_exposure": 1, "scale_misunderstanding": 1, "device_misread": 1, "substance_history": 1, "relayed_answers": 1, "active_cancer": 1, "travel_setting": 1, "wrong_side": 1, "medication_reaction": 1, "single_kidney": 1, "food_related": 1, "ambiguous_wording": 1, "delayed_deficit": 1, "confounded_observation": 1, "postoperative": 1, "assault": 1, "palliative": 1, "masked_fever": 1, "domestic_violence": 1, "antiplatelet": 1, "violence_risk": 1, "regional_convention": 1, "hearing_barrier": 1, "administrative_request": 1, "measurement_artifact": 1, "colloquial_vitals": 1, "disaster_setting": 1, "minor_narrator": 1, "emotional_trigger": 1, "intellectual_disability": 1, "uncertain_history": 1, "camera_observation": 1, "concealed_pregnancy": 1, "decision_point_d": 1} |
| opening_length_chars | {"min": 32, "median": 239, "max": 579} |

## Cặp lời mở đầu gần giống nhau (4-gram Jaccard >= 0.5)

Các cặp này không phải bản sao: chúng khác dữ kiện (thường là cặp tối thiểu có chủ đích) nhưng câu chữ gần nhau, nên luôn được xếp cùng một tập để không rò rỉ.

Không có.

## Phát hiện về bộ lọc khẩn cấp của sản phẩm

`src/simple_agent/emergency_screen.screen_patient_message` được chạy thật trên lời mở đầu của từng ca. Đây là phát hiện về sản phẩm, không ảnh hưởng nhãn: bộ lọc không gán ESI.

| Kịch bản | case_id | Tình huống | Kỳ vọng | Thực tế | Luật | Cụm khớp |
|---|---|---|---|---|---|---|
| r85 | mv2-04dd7327 | Tài xế xe tải chóng mặt quay, vợ nghe qua điện thoại thấy nói đớ | HIT | QUIET |  |  |
| c76 | mv2-177f81c2 | Máu mũi chảy ngược xuống họng ở cụ bà tăng huyết áp | HIT | QUIET |  |  |
| r96 | mv2-1f89d5e4 | Ăn cưới uống hai lon bia, đi loạng choạng, nói líu lưỡi, vợ thấy khác hẳn mọi khi | HIT | QUIET |  |  |
| c101 | mv2-2dfe1c9d | Chảy máu liên tục sau cắt amidan 7 ngày, huyết áp 94/60 | HIT | QUIET |  |  |
| r119 | mv2-34933a8a | Người đái tháo đường đột ngột nóng rát giữa ngực, tưởng trào ngược, huyết áp 86/54 | HIT | QUIET |  |  |
| r86 | mv2-38a8392d | Người hay rối loạn tiền đình, cơn chóng mặt lần này kèm tê yếu tay chân trái | HIT | QUIET |  |  |
| r89 | mv2-42c90ac6 | Cành cây gãy rơi trúng đầu khi đi xe máy, tê nửa người trái | HIT | QUIET |  |  |
| x79 | mv2-50ad2cd7 | Cụ bà sa sút trí tuệ ôm ngực, vã mồ hôi, không tả được đau | HIT | QUIET |  |  |
| r126 | mv2-5136c638 | Đá bóng cụng đầu với đối thủ, bất tỉnh chừng một phút, giờ tỉnh táo | HIT | QUIET |  |  |
| m84 | mv2-515f0083 | Cụ bà hàng xóm đau quặn bụng trái rồi đi ngoài ra nhiều máu đỏ sẫm | HIT | QUIET |  |  |
| m93 | mv2-532b998e | Bướu giáp nhân phồng to nhanh sau cơn ho, nuốt vướng, khàn tiếng, thở 32 lần/phút | HIT | QUIET |  |  |
| r91 | mv2-5b59afb1 | Hai ngày sau té xe đập đầu thì méo miệng, mẹ cho là do nằm quạt | HIT | QUIET |  |  |
| m108 | mv2-5d9c4900 | Gai cá đuối đâm rách sâu mu bàn chân, đau 9/10, mạch 126 | QUIET | HIT | SA_SCREEN_HEAVY_BLEEDING_V1 | máu chảy nhiều |
| m123 | mv2-631ab95b | Thai 9 tuần trong tử cung ra máu ướt đẫm băng mỗi giờ, có máu cục, đau quặn 8/10 | HIT | QUIET |  |  |
| r123 | mv2-6634546a | Cụ ông có hẹn đặt máy tạo nhịp lịm đi khi đang nằm nghỉ trưa, mạch 36 | HIT | QUIET |  |  |
| c116 | mv2-69117fbf | Bạn kể hộ: tông dải phân cách, gối biến dạng, bàn chân lạnh ngắt | QUIET | HIT | SA_SCREEN_STROKE_V2 | lệch hẳn sang 1 bên |
| r90 | mv2-704ec565 | Người thay van tim dùng thuốc chống đông ngã đập đầu, sáng hôm sau liệt tay chân phải | HIT | QUIET |  |  |
| m128 | mv2-72146b92 | Ung thư vú đang hoá trị, khó thở tăng dần phải ngồi dậy, thở 28, huyết áp 94/72 | QUIET | HIT | SA_SCREEN_RESPIRATORY_V2 | ngồi yên cũng hụt hơi |
| c117 | mv2-745f75de | Cụ bà trượt ngã ở chợ, cổ chân vẹo lệch, bàn chân tím tái | QUIET | HIT | SA_SCREEN_CYANOSIS_V1 | tím tái |
| c102 | mv2-860918f6 | Người xơ gan chảy máu cam không cầm, huyết áp 92/58, mạch không nhanh | HIT | QUIET |  |  |
| m87 | mv2-8b6c57c6 | Chỗ kim chọc cầu nối chạy thận rỉ máu không cầm, huyết áp 84/50 | HIT | QUIET |  |  |
| d37 | mv2-980621cb | Người cứu hàng xóm khỏi đám cháy chỉ xin thuốc ho, bước xác nhận mới báo SpO2 83 | QUIET | HIT | SA_SCREEN_RESPIRATORY_V2 | ngồi yên cũng thấy hụt hơi |
| x08 | mv2-991f7b85 | Nói ngọng, méo miệng, yếu tay, không biết từ lúc nào | HIT | QUIET |  |  |
| r94 | mv2-a0494e7e | Cụ bà hụt chân khi xuống xe buýt, đập đầu, đau lưng, vài giờ sau yếu dần tay chân trái | HIT | QUIET |  |  |
| m111 | mv2-af40aec2 | Bé 9 tuổi ngậm đũa vấp ngã, đũa đâm vòm miệng, máu rỉ liên tục dù cắn khăn ép, mạch 118 | HIT | QUIET |  |  |
| r84 | mv2-b3d55ada | Bà bán rau chóng mặt quay, nói đớ, tê tay phải, người trong chợ đang cạo gió | HIT | QUIET |  |  |
| r92 | mv2-c05b3e97 | Bị đánh gậy vào đầu, về phòng bình thường rồi mới nói không thành lời | HIT | QUIET |  |  |
| c113 | mv2-e393dc09 | Trẻ 11 tuổi ngã cây, cẳng tay cong được bó lá ở ông lang, đầu ngón tím tái | QUIET | HIT | SA_SCREEN_CYANOSIS_V1 | tím tái |
| c122 | mv2-e7338063 | Đứng ghế thay bóng đèn bị ngã đập gáy, lịm đi rồi hỏi đi hỏi lại | HIT | QUIET |  |  |

## Hàng chờ chuyên gia y tế (needs_medical_review.jsonl)

| case_id | Kịch bản | Nhãn hiện tại | Lý do chính |
|---|---|---|---|
| mv2-6b30c6c9 | c07 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-34eac7a3 | c08 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-778538aa | c09 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-48c7489a | c10 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-c5504453 | c100 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-9e8adf58 | c11 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-2e5f2917 | c12 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-dd104648 | c124 | esi_2 | AUTHOR_CONCERN: Decision Point B: cháy nắng nông, phồng rộp nhiều vùng ở người trẻ, không sốt, ăn uống được, không chóng mặt. Corpus cho ESI 2 qua hai tiêu chí: |
| mv2-372708c9 | c125 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-9041a948 | c126 | esi_2 | AUTHOR_CONCERN: Decision Point A: sưng cổ lan nhanh sau ong đốt kèm thở 34 lần/phút là nguy cơ tắc đường thở; nếu điều dưỡng thấy cần tiêm adrenalin hoặc kiểm s |
| mv2-4330d15f | c130 | esi_2 | AUTHOR_CONCERN: Decision Point B: sưng dưới hàm tái diễn theo bữa ăn, nay không xẹp và to dần nhưng không sốt, há miệng và nuốt bình thường, đau 6/10; ESI 2 chỉ |
| mv2-2960cda0 | c133 | esi_2 | AUTHOR_CONCERN: Decision Point B: còn trung tiện, không nôn, ăn uống bình thường, không sốt; ESI 2 chỉ đến từ đau 8/10 cộng việc rặn không ra phân. Theo AHRQ đi |
| mv2-5c18f490 | c141 | esi_2 | AUTHOR_CONCERN: Decision Point B: vai biến dạng sau ngã khi chơi thể thao ở người trẻ, đầu chi ấm hồng, không tê, tỉnh táo; ESI 2 chỉ đến từ đau 9/10 cộng biến  |
| mv2-df465ae6 | c147 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-f4b5fb27 | c149 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-80db3577 | c17 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-3b8d4b98 | c18 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-011c0967 | c19 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-50859d55 | c20 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-08ea3f2e | c21 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-43461cbe | c22 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-5e99541d | c23 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-4f2e99c1 | c24 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-b4b0a96c | c25 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-b088b559 | c27 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-2fdcfacf | c28 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-1282d069 | c29 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-f3eb639a | c30 | esi_3 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 3 dựa vào dự đoán 2 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-5c87bb30 | c32 | esi_3 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 3 dựa vào dự đoán 2 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-c38660e0 | c33 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-863b83b8 | c34 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-be6f0877 | c37 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-4280c26c | c38 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-7dc177ec | c43 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-c3c36558 | c44 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-d262be7a | c45 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-f19f87ec | c46 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-f8218bcd | c48 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-19b9fc71 | c49 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-b462c798 | c50 | esi_2 | AHRQ_AGE_ADJUSTED_VITALS (DISAGREE_OVER): Nhãn ESI 2 chỉ đến từ ngưỡng sinh hiệu/nhiệt độ dùng chung cho mọi tuổi, nhưng các chỉ số trẻ khai không vượt ngưỡng n |
| mv2-1be9c181 | c61 | esi_2 | AUTHOR_CONCERN: Decision Point B: bệnh cảnh giống viêm bàng quang có tiểu máu, không sốt, không đau hông lưng, vẫn đi tiểu được; ESI 2 chỉ dựa vào điểm đau từ 7 |
| mv2-f36c1a69 | c63 | esi_2 | AUTHOR_CONCERN: Decision Point B: người bệnh vẫn ăn uống được, không nôn, còn xì hơi (chỉ ít đi), đau 3/10; nếu không có dấu hiệu tắc ruột thì AHRQ nhiều khả nă |
| mv2-b865271a | c64 | esi_3 | AUTHOR_CONCERN: Decision Point C: người trẻ có hội chứng ruột kích thích, vẫn xì hơi bình thường, hôm qua còn đi ngoài được, đau 6/10; điều dưỡng thường dự kiến |
| mv2-a7a6d7a8 | c68 | esi_3 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 3 dựa vào dự đoán 2 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-02d01652 | c73 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-30ee0749 | c74 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-7fa95d69 | c75 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-a6db2c09 | c78 | esi_2 | AUTHOR_CONCERN: Chấn thương hàm đơn thuần: đường thở thông, vẫn nói chuyện được, tỉnh táo, không nôn, đau 6/10. Ở điểm quyết định B không thấy dấu hiệu nguy cơ  |
| mv2-6533c7d4 | c79 | esi_2 | AUTHOR_CONCERN: Viêm lợi trùm răng khôn khu trú, chưa lan ra má, nuốt bình thường, nhiệt độ 37,6: ESI 2 chỉ đến từ đau nặng 8/10, mà ở điểm quyết định B AHRQ để |
| mv2-654a87b0 | c91 | esi_2 | AUTHOR_CONCERN: Đau tai kiểu viêm ống tai ngoài sau bơi và ngoáy tai, không sốt, không chóng mặt: ESI 2 chỉ dựa vào điểm đau 9/10, mà ở điểm quyết định B AHRQ đ |
| mv2-0b4efba4 | c98 | esi_5 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 5 dựa vào dự đoán 0 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-779974f9 | c99 | esi_4 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 4 dựa vào dự đoán 1 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-5b12c408 | d09 | incomplete | AUTHOR_CONCERN: Huyết áp 190/120 kèm đau đầu và nhìn mờ: ngoài thai kỳ, corpus chỉ có một tiêu chí tăng huyết áp (tâm thu >= 200 kèm kích động, cần dữ kiện CLIN |
| mv2-ed76ad9d | d38 | incomplete | AUTHOR_CONCERN: Tê môi lưỡi, tê hai tay và hồi hộp loạn nhịp ngay sau uống rượu ngâm củ không rõ loại ở người 68 tuổi là tình huống nguy cơ cao theo AHRQ Decisi |
| mv2-3d06276e | d40 | incomplete | AUTHOR_CONCERN: Phơi nhiễm thuốc trừ sâu qua da và đường hô hấp đã có triệu chứng toàn thân kiểu cường cholin (nôn, vã mồ hôi, chảy nhiều nước dãi, nhìn mờ) có  |
| mv2-01765453 | d50 | incomplete | AUTHOR_CONCERN: Trẻ 6 tuổi có thể đã nuốt pin cúc áo chừng 40 phút trước: theo AHRQ Decision Point B đây là tình huống nguy cơ cao, vì pin cúc áo nằm lại ở thực |
| mv2-fe655fc2 | k13 | esi_2 | AUTHOR_CONCERN: AHRQ (chunk 002) ghi đau nặng 'determined by patient report, corroborated with clinical observation'; ở đây lời khai và hành vi tự kể mâu thuẫn, |
| mv2-b0c93e4d | k19 | esi_1 | AUTHOR_CONCERN: Tím môi do người nhà quan sát mâu thuẫn với SpO2 97% đo bằng máy người lớn trên trẻ 1 tuổi; corpus cho ESI 1 theo dấu tím, cần người khám xác nh |
| mv2-22859da6 | k25 | esi_2 | AUTHOR_CONCERN: Ba ngón tay bị dập, bầm, không có dấu hiệu mạch máu (không lạnh, không tím tái), đau 6/10: tiêu chí 'đè dập kèm không cử động được' của corpus v |
| mv2-6b8abeac | k37 | esi_3 | AHRQ_PEDS_FEVER_RED_FLAG (CANNOT_VERIFY): 38.7 °C là 'High Risk Indicator' theo bảng dấu hiệu đỏ (> 3 months (Red Flag Table)/ T > 38.5°C (101.3°F) or < 36.0°C  |
| mv2-aaf629d9 | k38 | esi_3 | AUTHOR_CONCERN: Bỏng do vữa xi măng ướt ở một đầu gối, đau 6/10, chỉ cần chăm sóc vết thương: ở Decision Point C điều dưỡng dự đoán một nguồn lực nên thường xếp |
| mv2-634ff991 | m02 | esi_2 | AHRQ_C_RESOURCE_PREDICTION (CANNOT_VERIFY): ESI 2 dựa vào dự đoán 2 nguồn lực (dữ kiện CLINICIAN_ONLY), không trùng ca mẫu nào của Table 5-2; căn cứ người viết: |
| mv2-6b6eb101 | m04 | esi_3 | AHRQ_D_DANGER_ZONE (CANNOT_VERIFY): Sinh hiệu ngoài ngưỡng nguy hiểm của nhóm tuổi adult (HR 112 > 100); AHRQ yêu cầu điều dưỡng cân nhắc nâng lên ESI 2. Corpus |
| mv2-b254e964 | m13 | esi_1 | AHRQ_AGE_ADJUSTED_VITALS (CANNOT_VERIFY): Sinh hiệu vượt ngưỡng nguy hiểm của nhóm tuổi infant, mà theo Decision Point D thì chỉ dẫn tới 'cân nhắc ESI 2'; ESI 1 |
| mv2-24b50a90 | m27 | incomplete | AHRQ_B_ALTERED_MENTAL_STATUS (DISAGREE_UNDER): Decision Point B: activity_level=DIFFICULT_TO_AROUSE tương ứng 'Confused/lethargic/disoriented' -> ESI 2, nhưng c |
| mv2-fdf004c6 | m53 | esi_2 | AUTHOR_CONCERN: Trẻ 11 tuổi ổn định: sốt 38,6, đi cà nhắc, không đau ngực, không khó thở, chưa ghi nhận sinh hiệu vùng nguy hiểm; ở Decision Point B không thấy  |
| mv2-6377f3a8 | m72 | esi_2 | AUTHOR_CONCERN: Trẻ không li bì và chưa đo được sinh hiệu nào ngoài nhiệt độ; corpus xếp ESI 2 cho mất nước mà không có li bì hay sinh hiệu vùng nguy hiểm, tron |
| mv2-353c73db | m77 | esi_3 | AUTHOR_CONCERN: Táo bón khi dùng clozapin có thể tiến triển thành liệt ruột, tắc ruột, hoại tử ruột; người duyệt có thể coi đây là tình huống nguy cơ cao ở Deci |
| mv2-6a7628bb | r10 | esi_2 | AHRQ_A_EPINEPHRINE_ANAPHYLAXIS (CANNOT_VERIFY): Sưng môi/lưỡi/họng kèm khó thở: Table 3-1 liệt kê 'Epinephrine (including IM for anaphylaxis)' là can thiệp cứu  |
| mv2-ca6befae | r104 | incomplete | AUTHOR_CONCERN: Tê và yếu tăng dần đối xứng từ chân lên tay trong hai ngày, sau một đợt tiêu chảy, đã không tự đi được: bệnh cảnh gợi ý tổn thương rễ thần kinh  |
| mv2-ad950a96 | r11 | esi_2 | AHRQ_A_EPINEPHRINE_ANAPHYLAXIS (CANNOT_VERIFY): Sưng môi/lưỡi/họng kèm khó thở: Table 3-1 liệt kê 'Epinephrine (including IM for anaphylaxis)' là can thiệp cứu  |
| mv2-6634546a | r123 | esi_2 | AUTHOR_CONCERN: Mạch 36 ngay sau một cơn ngất lúc đang nằm nghỉ, người còn mệt, ở cụ ông 81 tuổi: chương 3 của AHRQ ESI nêu 'yếu, chóng mặt, nhịp tim 30' và 'nh |
| mv2-f7142d34 | r125 | incomplete | AHRQ_B_ALTERED_MENTAL_STATUS (DISAGREE_UNDER): Decision Point B: altered_mental_status_present=YES, post_trauma_awareness_change=CONFUSION tương ứng 'Confused/l |
| mv2-18876281 | r22 | incomplete | AHRQ_PEDS_FEVER_NEONATE (DISAGREE_UNDER): Trẻ dưới 1 tháng tuổi, 38.4 °C: 1 - 28 days (< 1 month) / T > 38.0°C (100.4°F) / Assign at least ESI 2 |
| mv2-1cf2ac70 | r23 | incomplete | AHRQ_PEDS_FEVER_1_3_MONTHS (CANNOT_VERIFY): Trẻ 1-3 tháng, 38.3 °C: 1 - 3 months / T > 38.0°C (100.4°F) / Consider assigning ESI 2 |
| mv2-53125064 | r26 | incomplete | AHRQ_B_ALTERED_MENTAL_STATUS (DISAGREE_UNDER): Decision Point B: altered_mental_status_present=YES tương ứng 'Confused/lethargic/disoriented' -> ESI 2, nhưng co |
| mv2-74b41546 | r34 | incomplete | AHRQ_D_DANGER_ZONE (CANNOT_VERIFY): Sinh hiệu ngoài ngưỡng nguy hiểm của nhóm tuổi adult (HR 104 > 100); AHRQ yêu cầu điều dưỡng cân nhắc nâng lên ESI 2. Corpus |
| mv2-c6a2ab3c | r37 | incomplete | AUTHOR_CONCERN: Chấn thương đầu khi đang dùng thuốc chống đông là tình huống nguy cơ cao trong thực hành; corpus không có dữ kiện về thuốc chống đông nên không  |
| mv2-3f20ed87 | r79 | esi_3 | AUTHOR_CONCERN: Rắn lục cắn, sưng lan dần và bầm tím quanh vết cắn là dấu hiệu nhiễm độc nọc tại chỗ: có nguy cơ rối loạn đông máu, cần xét nghiệm đông máu và q |
| mv2-48af56eb | r80 | incomplete | AUTHOR_CONCERN: Nôn dịch xanh ở trẻ sơ sinh phải được coi là cấp cứu ngoại khoa cho tới khi chứng minh được điều ngược lại (tắc ruột, xoắn ruột): tình huống ngu |
| mv2-30297cca | r81 | incomplete | AUTHOR_CONCERN: Người chạy thận bỏ hai buổi lọc kèm yếu cơ, tê quanh môi và hồi hộp hẫng nhịp là tình huống nguy cơ cao (Decision Point B: nguy cơ tăng kali máu |
| mv2-63ef2215 | x05 | incomplete | AUTHOR_CONCERN: Chóng mặt ở người 60 tuổi mà chưa loại trừ được dấu hiệu thần kinh khu trú (người bệnh không biết); corpus không có tiêu chí cho tình huống thiế |
| mv2-d8fe58d6 | x07 | incomplete | AUTHOR_CONCERN: Méo mặt mới phát hiện khi ngủ dậy, không rõ giờ khởi phát: corpus chỉ có tiêu chí cho méo mặt khi khởi phát đột ngột; trong thực hành đây vẫn là |
| mv2-1989ee51 | x09 | incomplete | AHRQ_A_EXTERNAL_HEMORRHAGE (DISAGREE_UNDER): Máu chảy nhiều, ép không cầm: Table 3-1 liệt kê 'Control of external hemorrhage' là can thiệp cứu sống (ESI 1); cor |
| mv2-8bffc94d | x14 | incomplete | AUTHOR_CONCERN: Ra máu khi mang thai mà không rõ tuổi thai: không dùng được mốc 20 tuần của corpus; cần chuyên gia xác định mức. |
| mv2-9b5261f3 | x15 | incomplete | AUTHOR_CONCERN: Choáng, tái, vã mồ hôi lạnh đột ngột ở người 65 tuổi gợi ý tụt huyết áp hoặc bệnh tim; không có sinh hiệu nên corpus không quyết được. |
| mv2-bdec788d | x21 | incomplete | AUTHOR_CONCERN: Cử động giật khu trú ở người cao tuổi có thể là cơn co giật cục bộ hoặc bệnh mạch máu não; người kể không chắc nên corpus không có dữ kiện để tí |
| mv2-1deee745 | x23 | incomplete | AUTHOR_CONCERN: Người cao tuổi ngã không ai chứng kiến và quên diễn biến là nguy cơ cao; corpus chỉ tính được khi biết chắc có chấn thương đầu. |
| mv2-1587c10a | x24 | incomplete | AUTHOR_CONCERN: Trẻ nhỏ nuốt thuốc huyết áp của người lớn không rõ số lượng là tình huống nguy cơ cao (vài viên đã có thể nguy hiểm). Với thuốc nuốt nhầm, tiêu  |
| mv2-33f2f2fa | x26 | incomplete | AHRQ_PEDS_FEVER_3_MONTHS_PLUS (CANNOT_VERIFY): Trẻ từ 3 tháng, 39.6 °C: 3 months and older / 1. T > 39.0°C (102.2°F) or < 36.0°C (96.8°F)<br>2. OR Incomplete im |
| mv2-cb4a8a44 | x32 | incomplete | AUTHOR_CONCERN: Trẻ 20 tháng có thể đã nuốt nước tẩy bồn cầu (thường là chất ăn mòn): nghi nuốt chất ăn mòn ở trẻ nhỏ là tình huống nguy cơ cao theo Decision Po |
| mv2-a510844e | x37 | incomplete | AUTHOR_CONCERN: Phơi nhiễm thuốc trừ sâu không rõ loại qua da và đường hô hấp kéo dài, đã có triệu chứng (vã mồ hôi, buồn nôn, chóng mặt) gợi ý ngộ độc kiểu cườ |
| mv2-5ed1b85c | x45 | incomplete | AUTHOR_CONCERN: Trẻ 3 tuổi kẹt trong ô tô đỗ ngoài nắng không rõ bao lâu có nguy cơ tăng thân nhiệt nặng; theo Decision Point B đây là tình huống nguy cơ cao cầ |
| mv2-26f17492 | x46 | incomplete | AUTHOR_CONCERN: Thân nhiệt 39,4 độ sau nhiều giờ làm trong nhà màng, da khô không ra mồ hôi: có thể là say nóng; theo Decision Point B đây là tình huống nguy cơ |
| mv2-308c33dc | x49 | incomplete | AUTHOR_CONCERN: Trẻ được kéo lên từ ao nước lạnh, không ai thấy lúc ngã và không rõ thời gian ngâm nước: có thể được xem là tình huống nguy cơ cao theo Decision |
| mv2-14821df7 | x52 | incomplete | AUTHOR_CONCERN: Ho dai dẳng sau khi xăng trào vào miệng lúc hút xăng là dấu hiệu kinh điển của hít sặc hydrocarbon (nguy cơ viêm phổi hoá chất): theo Decision P |
| mv2-b1793056 | x53 | incomplete | AUTHOR_CONCERN: Các đầu ngón tay, ngón chân cứng, trắng như sáp sau phơi lạnh cả đêm là dấu hiệu tổn thương lạnh sâu (mô có nguy cơ hoại tử, cần làm ấm lại sớm) |
| mv2-59dc5415 | x71 | incomplete | AUTHOR_CONCERN: Người 79 tuổi suy tim đang dùng thuốc lợi tiểu, nằm dưới sàn không tự dậy được trong phòng nóng nhiều giờ, không rõ có ngất, có ngã hay có lơ mơ |
| mv2-b8f07c02 | x73 | incomplete | AUTHOR_CONCERN: Vết cắn khi ngủ dưới nền nhà ban đêm, không thấy con vật, hai dấu chấm nhỏ ít đau, chưa sưng: rắn độc thần kinh (như rắn cạp nia) cắn có thể gần |
| mv2-35d74227 | x74 | incomplete | AUTHOR_CONCERN: Thai 34 tuần nhức đầu kèm nhìn thấy đom đóm và phù chân tăng: theo Decision Point B đây là tình huống nguy cơ cao (cần loại trừ tiền sản giật nặ |
| mv2-5288d57d | x75 | incomplete | AUTHOR_CONCERN: Người 69 tuổi rung nhĩ, hồi hộp loạn nhịp khởi phát đột ngột kèm choáng phải ngồi xuống, máy đo không ra số: có thể đang nhịp rất nhanh hoặc tụt |
| mv2-c3b30cd2 | x76 | incomplete | AHRQ_D_DANGER_ZONE (CANNOT_VERIFY): Sinh hiệu ngoài ngưỡng nguy hiểm của nhóm tuổi adult (HR 112 > 100); AHRQ yêu cầu điều dưỡng cân nhắc nâng lên ESI 2. Corpus |
| mv2-5f6007c8 | x77 | incomplete | AUTHOR_CONCERN: Thiếu niên 16 tuổi giấu thai, chưa khám thai lần nào, đang có cơn gò từng cơn: chưa rõ tuổi thai và khoảng cách cơn gò nên corpus không xếp được |
| mv2-50ad2cd7 | x79 | incomplete | AUTHOR_CONCERN: Cụ bà 81 tuổi đái tháo đường, khó chịu ngực khi đang nghỉ kèm vã mồ hôi: theo Decision Point B đây là tình huống nguy cơ cao (cần loại trừ hội c |
