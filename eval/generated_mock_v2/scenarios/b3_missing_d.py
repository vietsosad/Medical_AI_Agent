"""Nhóm MISSING_INFO, đợt 3 (lượt 2): không biết tiền sử và phơi nhiễm, không phải không đo được.

Vẫn hai kiểu ca như ``missing.py``, ``b2_missing.py`` và ``b3_missing.py``:

- thiếu đúng dữ kiện quyết định -> kỳ vọng RETURN_INCOMPLETE (chuyển nhân viên y tế). Câu "không biết"
  nằm trong ``unknown``; không bao giờ được hiểu thành "không có", cũng không được tự hiểu thành "có".
- dữ kiện đã nêu đủ quyết định dù thiếu phần khác -> agent phải kết luận ngay, không đòi thêm tiền sử
  (tag ``decisive_despite_missing``).
- thêm kiểu thứ ba: điều không biết không đổi được mức, dữ kiện đã nêu khớp ESI 3 -> agent không được
  chuyển "không đủ thông tin" chỉ vì một câu "không biết".

Tệp này (lượt 2 của đợt 3) chỉ xét chữ "không biết" về tiền sử và phơi nhiễm: uống, ăn, hít phải gì, bao
nhiêu, lúc nào, với ý gì; có thai hay không khi kinh nguyệt không cho biết; bệnh nền, thuốc đang dùng, dị
ứng; sự việc người kể không chứng kiến; người kể ở thành phố khác; người kể phải dịch cho người bệnh nói
tiếng dân tộc hoặc tiếng nước ngoài. Không biết số đo, không biết giờ khởi phát là phần của
``b3_missing_c.py``.

Quy ước riêng của tệp này:

- Như ``b2_missing.py``: người kể nói rõ "không biết bao nhiêu" / "không biết chất gì" thì giá trị
  ``UNKNOWN`` của ``estimated_exposure_amount`` / ``toxic_substance_category`` nằm trong ``facts``; các dữ
  kiện phơi nhiễm khác chưa biết (dùng kèm chất khác, ý định, có ai cùng bị) nằm trong ``unknown``.
- "Không biết có thai không" vì kinh không đều hoặc đang cho con bú mà chưa có kinh lại được ghi là chưa
  biết như x25 của đợt 1, không phải "có thể có thai".
- ``test`` của mỗi ca INCOMPLETE nêu dữ kiện còn thiếu và mức corpus sẽ cho nếu biết được dữ kiện đó.
"""

from __future__ import annotations

from eval.generated_mock_v2.spec import INCOMPLETE, MISSING, P, SCREEN_HIT as HIT, SCREEN_QUIET as QUIET, Spec


def S(key: str, family: str, title: str, profile: dict, opening: str, facts: dict, intended, **kw) -> Spec:
    return Spec(case_id=key, family=family, group=MISSING, title=title, profile=profile,
                opening=opening, facts=facts, intended=intended, **kw)


SPECS = [
    # ------------------------------------------------- uống, ăn, hít phải gì, bao nhiêu, lúc nào
    S("x101", "dementia_mother_extra_gliclazide_unknown_count",
      "Cụ bà hay quên có thể đã uống thêm thuốc tiểu đường, không biết mấy viên, lúc nào",
      P(79, "Female", "PARENT", chronic=("Đái tháo đường type 2", "Tăng huyết áp", "Sa sút trí tuệ giai đoạn nhẹ"),
        meds=("Gliclazid 30 mg mỗi sáng", "Amlodipin 5 mg mỗi sáng")),
      "Mẹ tôi 79 tuổi bị tiểu đường, huyết áp, dạo này hay quên. Trưa nay dọn bàn, tôi thấy vỉ thuốc tiểu đường "
      "tôi mới bóc hôm qua đã trống mất mấy ô, tìm quanh bàn với gầm giường không thấy viên nào rơi, mà mỗi sáng mẹ "
      "chỉ uống một viên. Hỏi thì mẹ không nhớ đã uống mấy viên, uống lúc nào. Giờ mẹ vẫn tỉnh, nói chuyện bình "
      "thường, bữa trưa vẫn ăn như mọi ngày.",
      {"toxic_exposure_present": "YES", "toxic_substance_category": "MEDICATION", "toxic_exposure_route": "INGESTION",
       "estimated_exposure_amount": "UNKNOWN", "exposure_intent": "MEDICATION_ERROR",
       "altered_mental_status_present": "NO", "oral_intake_tolerance": "NORMAL"},
      INCOMPLETE, concepts=("medication_error", "unknown_exposure_amount"), screen=QUIET,
      answers={"toxic_exposure_present": "Có, vỉ thuốc tiểu đường mới bóc hôm qua mà đã trống mất mấy ô, tìm quanh "
                                         "không thấy viên nào rơi.",
               "toxic_substance_category": "Thuốc tiểu đường mẹ vẫn uống mỗi sáng.",
               "toxic_exposure_route": "Chắc là mẹ uống, tôi tìm quanh không thấy viên nào rơi ra.",
               "estimated_exposure_amount": "Mẹ không nhớ uống mấy viên, vỉ trống mấy ô nhưng tôi cũng không chắc mẹ "
                                            "uống hết số đó hay không.",
               "exposure_intent": "Mẹ hay quên nên chắc uống rồi lại tưởng mình chưa uống.",
               "altered_mental_status_present": "Không, mẹ vẫn tỉnh, nói chuyện bình thường.",
               "oral_intake_tolerance": "Bữa trưa mẹ vẫn ăn như mọi ngày."},
      unknown={"coingestion_status": "Vỉ thuốc huyết áp tôi chưa kịp đếm nên không biết mẹ có uống thêm thuốc nào "
                                     "khác không.",
               "symptom_duration_bucket": "Mẹ không nhớ uống lúc nào nên tôi không biết đã được bao lâu."},
      review_concern="Người 79 tuổi có thể đã uống thêm nhiều viên gliclazid, không rõ số lượng và thời điểm: thuốc "
                     "nhóm sulfonylurea có thể gây hạ đường huyết xuất hiện muộn và kéo dài; theo Decision Point B "
                     "đây là tình huống nguy cơ cao, nên xếp ESI 2. Với thuốc nuốt nhầm, corpus chỉ có tiêu chí khi "
                     "lượng là nhiều hoặc có dùng kèm chất khác, và corpus không có dữ kiện đường huyết.",
      tags=("older_adult", "caregiver", "toxic", "comorbidity", "baseline_cognitive_impairment", "null_unknown",
            "unknown_exposure_time"),
      test="Không biết mẹ đã uống mấy viên, lúc nào, có uống thêm thuốc huyết áp không (nếu có thì corpus cho ESI 2): "
           "agent không được coi 'vẫn tỉnh, vẫn ăn được' là đã an toàn hay tự ước một con số, mà phải chuyển nhân "
           "viên y tế."),
    S("x102", "preschool_oleander_leaf_chewing",
      "Cô giáo mầm non thấy bé 5 tuổi nhai lá trúc đào, không biết đã nuốt bao nhiêu",
      P(5, "Male", "OTHER"),
      "Tôi là cô giáo mầm non. Giờ ra chơi sáng nay, cách đây chừng nửa tiếng, tôi thấy một bé trai 5 tuổi lớp tôi "
      "ngồi ở góc sân nhai lá cây trúc đào trồng sát hàng rào, miệng còn dính vụn lá xanh. Tôi móc ra được mấy mẩu "
      "nhưng không biết bé đã nuốt vào bao nhiêu. Bé chưa nôn, vẫn chạy chơi bình thường. Phụ huynh đang trên "
      "đường tới.",
      {"toxic_exposure_present": "YES", "toxic_substance_category": "MUSHROOM_OR_PLANT",
       "toxic_exposure_route": "INGESTION", "estimated_exposure_amount": "UNKNOWN", "exposure_intent": "ACCIDENTAL",
       "vomiting_present": "NO", "activity_level": "NORMAL", "symptom_duration_bucket": "UNDER_1_HOUR"},
      INCOMPLETE, concepts=("plant_ingestion", "accidental_ingestion"), screen=QUIET,
      answers={"toxic_exposure_present": "Có, bé nhai lá cây trúc đào ở góc sân.",
               "toxic_substance_category": "Lá cây trúc đào trồng sát hàng rào trường.",
               "toxic_exposure_route": "Bé nhai trong miệng, tôi móc ra được mấy mẩu, còn nuốt vào bao nhiêu thì "
                                       "không biết.",
               "estimated_exposure_amount": "Tôi không biết bé đã nuốt bao nhiêu, chỉ móc ra được mấy mẩu.",
               "exposure_intent": "Bé nghịch thôi, không ai cho bé ăn.",
               "vomiting_present": "Bé chưa nôn.",
               "activity_level": "Bé vẫn chạy chơi bình thường.",
               "symptom_duration_bucket": "Mới chừng nửa tiếng."},
      unknown={"coingestion_status": "Tôi chỉ thấy lúc bé đang nhai lá, không biết trước đó bé có cho thứ gì khác "
                                     "vào miệng không."},
      review_concern="Trẻ 5 tuổi nhai lá trúc đào (cây chứa glycosid tim), không biết đã nuốt bao nhiêu: ngộ độc có "
                     "thể gây nôn và rối loạn nhịp tim sau vài giờ; theo Decision Point B đây là tình huống nguy cơ "
                     "cao, nên xếp ESI 2. Corpus chỉ có tiêu chí cây, nấm khi lượng là nhiều.",
      tags=("pediatric", "collateral_history", "toxic", "school_setting", "null_unknown"),
      test="Không biết bé đã nuốt bao nhiêu lá trúc đào (nếu biết là nhiều thì corpus cho ESI 2): agent không được "
           "coi 'vẫn chạy chơi, chưa nôn' là vô hại hay tự cho là bé đã nhả ra hết, mà phải chuyển nhân viên y tế."),
    S("x103", "new_tenant_corridor_odor_neighbours_unknown",
      "Mới chuyển tới chung cư, ngửi mùi hắc lạ ở hành lang, nhức đầu, không biết hàng xóm có ai bị",
      P(34, "Female"),
      "Mình mới chuyển tới chung cư này dc 1 tuần. Chừng 40 phút trước mình đi đổ rác ở cuối hành lang thì ngửi "
      "thấy 1 mùi hắc lạ, ko giống mùi gas bếp, đứng đó vài phút rồi về phòng. Giờ mình nhức đầu âm ỉ khoảng 3/10, "
      "hơi buồn nôn nhưng chưa nôn, thở vẫn bình thường. Mình ko biết đó là mùi gì, cũng chưa quen hàng xóm nên ko "
      "biết có ai bị giống mình ko.",
      {"toxic_exposure_present": "YES", "toxic_substance_category": "UNKNOWN", "toxic_exposure_route": "INHALATION",
       "estimated_exposure_amount": "SMALL", "exposure_intent": "ACCIDENTAL", "headache_present": "YES",
       "headache_character": "DULL", "pain_present": "YES", "pain_severity": 3,
       "gastrointestinal_symptom_present": "YES", "vomiting_present": "NO", "dyspnea_present": "NO",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      INCOMPLETE, concepts=("unknown_exposure_substance", "toxic_inhalation", "headache"), screen=QUIET,
      answers={"toxic_exposure_present": "Có, mình ngửi phải 1 mùi hắc lạ ở cuối hành lang.",
               "toxic_substance_category": "Mình ko biết là mùi gì, chỉ biết ko giống mùi gas bếp.",
               "toxic_exposure_route": "Mình hít phải thôi, ko dính hay nuốt gì.",
               "estimated_exposure_amount": "Chắc chỉ hít phải 1 ít, mình đứng đó vài phút rồi về.",
               "exposure_intent": "Vô tình thôi, mình đi đổ rác.",
               "headache_present": "Có, mình nhức đầu âm ỉ.",
               "headache_character": "Nhức âm ỉ thôi.",
               "pain_present": "Có, mình nhức đầu.",
               "pain_severity": "Khoảng 3/10.",
               "gastrointestinal_symptom_present": "Có, mình hơi buồn nôn.",
               "vomiting_present": "Chưa nôn.",
               "dyspnea_present": "Ko, mình thở vẫn bình thường.",
               "symptom_duration_bucket": "Mới chưa tới 1 tiếng, từ lúc đi đổ rác về."},
      unknown={"similar_symptoms_in_others": "Mình mới chuyển tới, chưa quen ai nên ko biết hàng xóm có ai bị ko."},
      tags=("toxic", "environmental", "abbreviation", "null_unknown"),
      test="Không biết mùi lạ là chất gì và có ai khác cùng bị không (nếu có người khác cùng bị thì corpus cho ESI 2): "
           "agent phải hỏi về người xung quanh, không được tự coi là vô hại hay là ngộ độc khí hàng loạt; thiếu dữ kiện "
           "đó thì chuyển nhân viên y tế."),
    S("x104", "scrap_collector_unlabelled_drum_vapour",
      "Người thu mua phế liệu cạy thùng phuy không nhãn, hít phải hơi, ho sặc, không biết chất gì",
      P(47, "Male", allergies=("Dị ứng tôm",)),
      "Tui làm nghề thu mua phế liệu. Chừng 20 phút trước tui cạy nắp một cái thùng phuy cũ không nhãn mác để cắt "
      "bán sắt, hơi trong thùng xộc thẳng vô mũi. Chừ tui ho sặc sụa, rát cổ họng, đầu choáng choáng, chưa "
      "thấy khó thở. Thùng ni mua lại của người ta, không ai biết trước đựng chất chi, tui hít phải nhiều hay ít "
      "cũng không biết.",
      {"toxic_exposure_present": "YES", "toxic_substance_category": "UNKNOWN", "toxic_exposure_route": "INHALATION",
       "estimated_exposure_amount": "UNKNOWN", "exposure_intent": "ACCIDENTAL",
       "smoke_or_fume_exposure": "CHEMICAL_FUMES", "cough_present": "YES", "sore_throat_present": "YES",
       "pain_present": "YES", "dizziness_present": "YES", "dizziness_sensation": "NONSPECIFIC",
       "dyspnea_present": "NO", "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("unknown_exposure_substance", "occupational_inhalation_exposure", "cough"), screen=QUIET,
      answers={"toxic_exposure_present": "Có, tui hít phải hơi trong cái thùng phuy cũ.",
               "toxic_substance_category": "Không ai biết thùng đó trước đựng chất chi, thùng không có nhãn mác.",
               "toxic_exposure_route": "Hơi xộc vô mũi, tui hít phải.",
               "estimated_exposure_amount": "Tui không biết hít phải nhiều hay ít.",
               "exposure_intent": "Không cố ý chi hết, tui cạy nắp để cắt bán sắt.",
               "smoke_or_fume_exposure": "Có, hơi trong thùng xộc ra.",
               "cough_present": "Có, tui ho sặc sụa.",
               "sore_throat_present": "Có, rát cổ họng lắm.",
               "pain_present": "Có, rát ở cổ họng.",
               "dizziness_present": "Có, đầu choáng choáng.",
               "dizziness_sensation": "Choáng choáng, tả không rõ.",
               "dyspnea_present": "Chưa thấy khó thở.",
               "symptom_duration_bucket": "Mới chừng 20 phút."},
      unknown={"pain_severity": "Rát thì rát chứ tui không biết chấm mấy điểm."},
      tags=("toxic", "occupational", "dialect", "unreadable_label", "decisive_despite_missing"),
      test="Không biết thùng từng đựng chất gì và đã hít phải bao nhiêu (khác x35 ở đường hít và nơi làm việc): chất "
           "không rõ với lượng không rõ đã đủ quyết định ESI 2, agent không được đòi tên chất hay chờ tới khi khó thở "
           "mới kết luận."),
    S("x105", "market_pork_roll_lunch_two_turn_blue",
      "Sau bữa trưa có giò mua ở chợ phiên, chồng và mẹ chồng thâm tím môi, máy kẹp ngón báo 84%",
      P(52, "Male", "SPOUSE"),
      "Trưa nay nhà tôi ăn giò lụa với dưa cải muối mua ở chợ phiên. Ăn xong chừng nửa tiếng thì chồng tôi kêu "
      "nhức đầu, choáng, ngồi yên cũng thở mệt, môi với các đầu ngón tay thâm tím lại. Mẹ chồng tôi ngồi cùng mâm giờ cũng thấy "
      "môi thâm đi. Máy kẹp ngón tay ở nhà đo cho chồng tôi báo 84%. Tôi không biết trong món nào có thứ gì lạ, "
      "anh ăn bao nhiêu tôi cũng không để ý.",
      {"toxic_exposure_present": "YES", "toxic_substance_category": "FOOD", "toxic_exposure_route": "INGESTION",
       "estimated_exposure_amount": "UNKNOWN", "exposure_intent": "ACCIDENTAL", "similar_symptoms_in_others": "YES",
       "cyanosis_present": "YES", "spo2": 84, "dyspnea_present": "YES", "dyspnea_context": "AT_REST",
       "respiratory_distress_symptoms": "AT_REST", "cardiorespiratory_symptom_present": "YES",
       "headache_present": "YES", "pain_present": "YES", "dizziness_present": "YES",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      1, concepts=("cyanosis", "contaminated_food_exposure"), screen=HIT,
      answers={"toxic_exposure_present": "Có, chắc là do bữa trưa, hai người ăn xong đều bị.",
               "toxic_substance_category": "Đồ ăn bữa trưa, giò lụa với dưa cải muối mua ở chợ phiên.",
               "toxic_exposure_route": "Ăn vào thôi.",
               "estimated_exposure_amount": "Tôi không biết thứ lạ nằm ở món nào nên không biết anh ăn phải bao "
                                            "nhiêu.",
               "exposure_intent": "Không ai cố ý, nhà ăn bữa trưa bình thường.",
               "similar_symptoms_in_others": "Có, mẹ chồng tôi ăn cùng mâm giờ cũng thấy môi thâm đi.",
               "cyanosis_present": "Có, môi với các đầu ngón tay anh thâm tím lại.",
               "spo2": "Máy kẹp ngón tay báo 84%.",
               "dyspnea_present": "Có, anh kêu thở mệt.",
               "dyspnea_context": "Anh ngồi yên cũng thở mệt.",
               "respiratory_distress_symptoms": "Ngồi yên anh cũng thở mệt.",
               "cardiorespiratory_symptom_present": "Có, anh kêu thở mệt.",
               "headache_present": "Có, anh kêu nhức đầu.",
               "pain_present": "Anh kêu nhức đầu.",
               "dizziness_present": "Có, anh kêu choáng.",
               "symptom_duration_bucket": "Mới bị được một lúc, chưa tới một tiếng."},
      unknown={"pain_severity": "Anh chỉ kêu nhức đầu chứ không chấm điểm được."},
      tags=("toxic", "multiple_victims", "collateral_history", "decisive_despite_missing", "null_unknown"),
      test="Không biết thứ lạ nằm trong món nào và đã ăn phải bao nhiêu: môi, đầu ngón thâm tím kèm SpO2 84% đã đủ "
           "quyết định ESI 1, agent không được hỏi thêm về món ăn hay đợi xem người còn lại thế nào rồi mới kết luận."),
    S("x106", "floodwater_unseen_object_sole_puncture",
      "Lội lũ dọn sân giẫm phải vật nhọn không nhìn thấy, gan bàn chân sưng đỏ, đau tăng dần",
      P(39, "Male"),
      "Ba hôm trước nước lũ tràn vào sân, tôi lội dọn bùn thì giẫm phải vật gì nhọn dưới làn nước đục, không nhìn "
      "thấy là gì, gan bàn chân phải có một lỗ nhỏ. Từ hôm qua quanh chỗ đó sưng đỏ, đau tăng dần, giờ khoảng "
      "6/10, đi lại phải nhón chân nhưng các ngón chân không tê. Sáng nay tôi cặp nhiệt được 37,4 độ. Tôi không biết "
      "trong vết còn mảnh gì không, cũng không nhớ lần cuối tiêm phòng uốn ván là bao giờ.",
      {"trauma_present": "YES", "trauma_mechanism": "PENETRATING_INJURY", "wound_present": "YES",
       "wound_type": "PUNCTURE", "wound_location": "FOOT_TOE", "wound_contamination": "DIRTY_WATER",
       "lower_extremity_problem_present": "YES", "lower_extremity_injury_location": "FOOT",
       "weight_bearing_ability": "PAINFUL_BUT_POSSIBLE", "distal_limb_symptoms": "NONE", "swelling_present": "YES",
       "swelling_location": "OTHER", "pain_present": "YES", "pain_severity": 6, "symptom_trend": "WORSENING",
       "temperature": 37.4, "fever_present": "NO", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, concepts=("wound", "wound_contamination"), screen=QUIET,
      answers={"trauma_present": "Có, ba hôm trước tôi giẫm phải vật nhọn khi lội lũ dọn sân.",
               "trauma_mechanism": "Giẫm phải vật gì nhọn dưới nước, đâm vào gan bàn chân.",
               "wound_present": "Có, gan bàn chân phải có một lỗ nhỏ.",
               "wound_type": "Một lỗ nhỏ do vật nhọn đâm.",
               "wound_location": "Ở gan bàn chân phải.",
               "wound_contamination": "Dính nước lũ đục.",
               "lower_extremity_problem_present": "Có, gan bàn chân phải bị đâm, giờ sưng đỏ.",
               "lower_extremity_injury_location": "Ở gan bàn chân phải.",
               "weight_bearing_ability": "Vẫn đi được nhưng đau, phải nhón chân.",
               "distal_limb_symptoms": "Các ngón chân không tê.",
               "swelling_present": "Có, quanh chỗ bị đâm sưng đỏ.",
               "swelling_location": "Sưng quanh vết ở gan bàn chân.",
               "pain_present": "Có, đau ở gan bàn chân.",
               "pain_severity": "Khoảng 6/10.",
               "symptom_trend": "Đau tăng dần từ hôm qua.",
               "temperature": "Sáng nay cặp nhiệt được 37,4 độ.",
               "fever_present": "Không, sáng nay cặp nhiệt được 37,4 độ thôi.",
               "symptom_duration_bucket": "Bị đâm ba hôm trước, sưng đau từ hôm qua."},
      unknown={"foreign_body_status": "Tôi không nhìn thấy vật đâm là gì nên không biết trong vết còn mảnh nào không.",
               "wound_depth_category": "Lỗ nhỏ nên tôi không biết vật đó đâm vào sâu tới đâu."},
      tags=("environmental", "unknown_mechanism", "null_unknown", "low_acuity_look_alike"),
      test="Không biết vật đâm là gì, còn mảnh trong vết không, đâm sâu bao nhiêu, đã tiêm uốn ván chưa: những điều "
           "đó không đổi được mức ở điểm đau 6; agent không được chuyển 'không đủ thông tin' hay tự nâng mức, vì đau "
           "vừa tăng dần đã đủ xếp ESI 3."),
    S("x107", "teen_took_mothers_sleeping_pills_reason_unclear",
      "Con gái 16 tuổi lấy hai viên thuốc ngủ của mẹ uống, không nói vì sao",
      P(16, "Female", "CHILD"),
      "Sáng nay con gái tôi 16 tuổi dậy muộn hơn mọi khi. Tôi kiểm tra thì vỉ thuốc ngủ bác sĩ kê cho tôi thiếu mất "
      "hai viên so với tối qua, cháu nhận là đêm qua khó ngủ nên lấy uống. Giờ cháu tỉnh táo, nói chuyện rõ ràng, "
      "ăn sáng được. Tôi hỏi sao lại tự lấy thuốc của mẹ thì cháu im lặng rồi quay vào phòng.",
      {"toxic_exposure_present": "YES", "toxic_substance_category": "MEDICATION", "toxic_exposure_route": "INGESTION",
       "estimated_exposure_amount": "SMALL", "altered_mental_status_present": "NO", "oral_intake_tolerance": "NORMAL",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("medication_ingestion", "medication_access"), screen=QUIET,
      answers={"toxic_exposure_present": "Có, đêm qua cháu lấy thuốc ngủ của tôi uống.",
               "toxic_substance_category": "Thuốc ngủ bác sĩ kê cho tôi.",
               "toxic_exposure_route": "Cháu uống.",
               "estimated_exposure_amount": "Hai viên thôi, vỉ thiếu đúng hai viên so với tối qua.",
               "altered_mental_status_present": "Không, giờ cháu tỉnh táo, nói chuyện rõ ràng.",
               "oral_intake_tolerance": "Sáng nay cháu vẫn ăn sáng được.",
               "symptom_duration_bucket": "Cháu uống từ đêm qua, tới giờ mấy tiếng rồi."},
      unknown={"exposure_intent": "Cháu chỉ bảo khó ngủ, ngoài ra không nói gì nên tôi không biết cháu uống với ý gì.",
               "self_safety_status": "Tôi hỏi thì cháu không trả lời, tôi không biết.",
               "coingestion_status": "Tôi không biết đêm qua cháu có uống thêm gì khác không."},
      review_concern="Thiếu niên tự lấy thuốc ngủ của mẹ uống và im lặng khi được hỏi lý do: chưa loại trừ được ý "
                     "định tự hại; theo Decision Point B đây là tình huống nguy cơ cao, nên xếp ESI 2 cho tới khi đánh "
                     "giá được an toàn. Corpus chỉ xếp được khi biết ý định hoặc ý nghĩ tự hại.",
      tags=("adolescent", "caregiver", "toxic", "mental_health", "null_unknown", "intent_unknown"),
      test="Không biết cháu uống thuốc ngủ vì khó ngủ hay vì lý do khác (nếu cố ý hại mình thì corpus cho ESI 2): agent "
           "phải hỏi về an toàn bản thân, không được tự coi là vô tình vì lượng ít; thiếu ý định và tình trạng an toàn "
           "thì phải chuyển nhân viên y tế."),
    # ------------------------------------------------------------- có thai hay không
    S("x108", "breastfeeding_amenorrhea_bleeding_cramps",
      "Đang cho con bú chưa có kinh lại, ra máu khá nhiều, đau quặn bụng dưới, không biết có thai",
      P(29, "Female"),
      "Em sinh bé thứ hai được 5 tháng, vẫn cho bú mẹ hoàn toàn nên từ lúc sinh tới giờ chưa có kinh lại. Từ sáng "
      "nay em tự nhiên ra máu đỏ ở dưới, khá nhiều, phải thay băng mấy lần rồi, bụng dưới đau quặn từng cơn chừng 5 "
      "trên 10. Em không biết mình có thai lại hay không, ở nhà không có que thử.",
      {"vaginal_bleeding_present": "YES", "vaginal_bleeding_amount": "MODERATE", "abdominal_pain_present": "YES",
       "abdominal_pain_location": "LOWER_ABDOMEN", "abdominal_pain_character": "CRAMPING", "pain_present": "YES",
       "pain_severity": 5, "symptom_trend": "INTERMITTENT", "gastrointestinal_symptom_present": "YES",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("vaginal_bleeding", "breastfeeding", "lower_abdominal_pain"), screen=QUIET,
      answers={"vaginal_bleeding_present": "Dạ có, từ sáng em ra máu đỏ ở dưới.",
               "vaginal_bleeding_amount": "Ra khá nhiều, em phải thay băng mấy lần rồi.",
               "abdominal_pain_present": "Dạ có, bụng dưới em đau quặn.",
               "abdominal_pain_location": "Bụng dưới ạ.",
               "abdominal_pain_character": "Quặn từng cơn ạ.",
               "pain_present": "Dạ có, em đau quặn bụng dưới.",
               "pain_severity": "Chừng 5 trên 10 ạ.",
               "symptom_trend": "Đau từng cơn, quặn lên rồi lại đỡ ạ.",
               "gastrointestinal_symptom_present": "Dạ có, em đau quặn bụng dưới.",
               "symptom_duration_bucket": "Từ sáng nay tới giờ ạ."},
      unknown={"pregnancy_present": "Em không biết, từ lúc sinh tới giờ em chưa có kinh lại, cũng chưa thử que.",
               "pregnancy_status": "Em không biết mình có thai lại hay không, nhà không có que thử."},
      tags=("null_unknown", "breastfeeding", "pregnancy_status_unknown"),
      test="Đang cho con bú, chưa có kinh lại, không có que thử nên không biết có thai hay không (nếu có thể có thai "
           "thì ra máu vừa kèm đau 5 điểm đã đủ ESI 2): agent không được tự coi là 'có kinh lại' hay 'không có thai', "
           "phải chuyển nhân viên y tế."),
    S("x109", "pcos_wife_high_fever_productive_cough_no_diacritics",
      "Chồng nhắn không dấu: vợ sốt 39,2, ho đờm vàng, kinh vài tháng mới có, chưa biết có thai",
      P(31, "Female", "SPOUSE", chronic=("Hội chứng buồng trứng đa nang",), allergies=("Dị ứng amoxicillin",)),
      "Vo toi 31 tuoi sot tu toi hom kia, sang nay do nhiet ke dien tu duoc 39,2 do, ho khac dom vang, nguoi met ra "
      "roi. Vo toi khong kho tho. Vo toi bi buong trung da nang nen kinh vai thang moi co mot lan, lan gan nhat ca "
      "hai vo chong deu khong nho, chua thu thai lan nao nen khong biet co thai hay khong.",
      {"fever_present": "YES", "temperature": 39.2, "cough_present": "YES", "cough_character": "PRODUCTIVE",
       "sputum_present": "YES", "sputum_appearance": "YELLOW_OR_GREEN", "infection_source_symptom_group": "RESPIRATORY",
       "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS", "dyspnea_present": "NO",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, concepts=("fever", "cough", "sputum_production"), screen=QUIET,
      answers={"fever_present": "Co, vo toi sot, sang nay do duoc 39,2 do.",
               "temperature": "Nhiet ke dien tu do duoc 39,2 do.",
               "cough_present": "Co, vo toi ho khac dom.",
               "cough_character": "Ho co dom.",
               "sputum_present": "Co, khac ra dom vang.",
               "sputum_appearance": "Dom mau vang.",
               "infection_source_symptom_group": "Ngoai sot thi chu yeu la ho khac dom.",
               "associated_systemic_symptoms": "Vua sot vua met ra roi.",
               "dyspnea_present": "Khong, vo toi khong kho tho.",
               "symptom_duration_bucket": "Tu toi hom kia toi gio."},
      unknown={"pregnancy_present": "Chua thu thai lan nao nen khong biet co hay khong.",
               "pregnancy_status": "Khong biet, kinh vo toi vai thang moi co mot lan, lan gan nhat cung khong nho."},
      tags=("no_diacritics", "collateral_history", "comorbidity", "null_unknown", "pregnancy_status_unknown"),
      test="Kinh thưa vì buồng trứng đa nang, chưa thử thai nên không biết có thai hay không (nếu có thể có thai thì "
           "sốt 39,2 đã đủ ESI 2): agent không được tự ghi 'không có thai', phải chuyển nhân viên y tế."),
    # ------------------------------------------------- bệnh nền, thuốc đang dùng, dị ứng
    S("x110", "new_live_in_helper_fever_unknown_history",
      "Người giúp việc mới đến: bà cụ sốt 38,4, ho khan, không ai nói bà bệnh gì, uống thuốc gì",
      P(72, "Female", "OTHER"),
      "Em là người giúp việc mới tới nhà được bốn hôm, chăm một bà cụ 72 tuổi. Từ chiều bà sốt, em kẹp nhiệt kế được "
      "38,4 độ, bà ho khan, kêu mệt, nhưng tối vẫn ăn hết bát cháo như mọi bữa, thở bình thường. Con cháu bà ở nước "
      "ngoài hết, lúc giao việc chỉ dặn cho bà uống thuốc theo hộp chia sẵn từng ngày, không nói bà bị bệnh gì, thuốc "
      "gì. Em gọi cho cô con gái mà chưa ai nghe máy.",
      {"fever_present": "YES", "temperature": 38.4, "cough_present": "YES", "cough_character": "DRY",
       "infection_source_symptom_group": "RESPIRATORY", "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS",
       "oral_intake_tolerance": "NORMAL", "dyspnea_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("fever", "cough"), screen=QUIET,
      answers={"fever_present": "Dạ có, em kẹp nhiệt kế được 38,4 độ.",
               "temperature": "Nhiệt kế đo được 38,4 độ ạ.",
               "cough_present": "Dạ có, bà ho khan.",
               "cough_character": "Bà ho khan ạ.",
               "infection_source_symptom_group": "Ngoài sốt thì bà chủ yếu ho khan ạ.",
               "associated_systemic_symptoms": "Bà sốt, kêu mệt ạ.",
               "oral_intake_tolerance": "Tối bà vẫn ăn hết bát cháo như mọi bữa ạ.",
               "dyspnea_present": "Dạ không, bà thở bình thường.",
               "symptom_duration_bucket": "Bà sốt từ chiều tới giờ ạ."},
      unknown={"immunocompromised_state_present": "Gia đình không nói bà bị bệnh gì nên em không biết sức đề kháng "
                                                  "của bà thế nào ạ.",
               "chemotherapy_history_present": "Em mới tới, không biết bà có đang điều trị gì như vậy không, con bà "
                                               "chưa nghe máy ạ."},
      tags=("older_adult", "collateral_history", "null_unknown", "unknown_medication_history"),
      test="Người kể mới đến làm, không biết bệnh nền và thuốc trong hộp chia sẵn (nếu bà suy giảm miễn dịch hay đang "
           "hoá trị thì sốt đã đủ ESI 2): agent không được tự coi là không có, phải chuyển nhân viên y tế."),
    S("x111", "son_home_from_abroad_father_black_stool_meds_unknown",
      "Con đi làm nước ngoài mới về: bố 76 tuổi phân đen, sinh hiệu ổn, không rõ thuốc đang dùng",
      P(76, "Male", "PARENT", chronic=("Tăng huyết áp", "Thoái hoá khớp gối"), allergies=("Dị ứng penicilin",)),
      "Tôi đi làm ở nước ngoài, mới về thăm bố được hai hôm. Sáng nay bố tôi 76 tuổi đi ngoài ra phân đen sệt, bố bảo "
      "từ hôm kia đi đã thấy đen như vậy. Tôi đo máy huyết áp ở nhà được 132/80, mạch 84. Bố không đau bụng, không "
      "nôn, không choáng, vẫn ăn uống bình thường. Bố uống mấy loại thuốc huyết áp với thuốc khớp của bệnh viện "
      "huyện, đơn để ở nhà chị gái tôi nên tôi không biết là những thuốc gì.",
      {"gastrointestinal_symptom_present": "YES", "stool_appearance": "BLACK", "systolic_bp": 132, "diastolic_bp": 80,
       "heart_rate": 84, "abdominal_pain_present": "NO", "pain_present": "NO", "vomiting_present": "NO",
       "dizziness_present": "NO", "oral_intake_tolerance": "NORMAL", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, concepts=("black_stool", "current_medication_use"), screen=QUIET,
      answers={"gastrointestinal_symptom_present": "Có, bố đi ngoài ra phân đen.",
               "stool_appearance": "Phân đen sệt.",
               "systolic_bp": "Máy đo được 132/80.",
               "diastolic_bp": "Số dưới là 80.",
               "heart_rate": "Máy báo mạch 84.",
               "abdominal_pain_present": "Không, bố không đau bụng.",
               "pain_present": "Bố không kêu đau ở đâu.",
               "vomiting_present": "Không, bố không nôn.",
               "dizziness_present": "Không, bố không choáng.",
               "oral_intake_tolerance": "Bố vẫn ăn uống bình thường.",
               "symptom_duration_bucket": "Bố bảo từ hôm kia đi ngoài đã đen như vậy."},
      unknown={"toxic_exposure_present": "Đơn thuốc để ở nhà chị gái, tôi không biết ngoài thuốc bệnh viện bố có tự mua "
                                         "thêm thuốc gì uống không."},
      tags=("older_adult", "caregiver", "comorbidity", "null_unknown", "unknown_medication_history",
            "low_acuity_look_alike"),
      test="Không biết bố đang dùng thuốc gì: agent không được tự cho phân đen là do thuốc để hạ mức, cũng không được "
           "chuyển 'không đủ thông tin' vì thiếu đơn thuốc; phân đen với sinh hiệu ổn định đã đủ xếp ESI 3 (khác m40 ở "
           "người kể vừa từ nước ngoài về, không nắm thuốc men; khác c173 ở chỗ thuốc không biết còn sinh hiệu có)."),
    S("x112", "tour_guide_seafood_dinner_hives_lip_swelling",
      "Hướng dẫn viên dịch hộ: bà khách nổi mề đay khắp người, sưng môi, không rõ món nào và tiền sử dị ứng",
      P(63, "Female", "OTHER"),
      "Tôi là hướng dẫn viên, đang dẫn một đoàn khách nước ngoài ăn tối ở nhà hàng hải sản. Một bà khách 63 tuổi chỉ "
      "nói được tiếng nước bà, tôi dịch lại: chừng 20 phút nay bà nổi mẩn đỏ gồ lên khắp người, ngứa lắm, môi sưng "
      "mọng lên. Bà vẫn nói chuyện được, không kêu khó thở. Bàn ăn có cả chục món, bà không để ý nổi mẩn từ lúc ăn "
      "món nào, hồ sơ đoàn cũng không ghi bà có dị ứng gì hay đang dùng thuốc gì.",
      {"rash_or_skin_finding_present": "YES", "skin_finding_appearance": "RAISED_WHEALS",
       "skin_finding_distribution": "GENERALIZED", "itching_present": "YES", "swelling_present": "YES",
       "swelling_location": "LIPS", "dyspnea_present": "NO", "allergic_reaction_features": "MULTIPLE_FEATURES",
       "suspected_trigger_exposure_present": "YES", "suspected_allergy_trigger": "FOOD",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("urticaria", "lip_swelling"), negated=("shortness_of_breath",), screen=QUIET,
      # Hoà điểm với esi_2_generalized_hives_with_face_swelling (thắng theo chữ cái) dù chỉ có môi sưng.
      primary_atom="esi_2_generalized_hives_with_lip_swelling",
      answers={"rash_or_skin_finding_present": "Có, bà nổi mẩn đỏ gồ lên khắp người.",
               "skin_finding_appearance": "Mẩn đỏ gồ lên.",
               "skin_finding_distribution": "Nổi khắp người.",
               "itching_present": "Có, bà kêu ngứa lắm.",
               "swelling_present": "Có, môi bà sưng mọng lên.",
               "swelling_location": "Sưng ở môi.",
               "dyspnea_present": "Bà không kêu khó thở, vẫn nói chuyện được.",
               "allergic_reaction_features": "Vừa nổi mẩn ngứa khắp người vừa sưng môi.",
               "suspected_trigger_exposure_present": "Bà đang ăn tối hải sản thì bị.",
               "suspected_allergy_trigger": "Đồ ăn bữa tối, nhưng bàn có cả chục món nên không biết món nào.",
               "symptom_duration_bucket": "Mới chừng 20 phút nay."},
      unknown={"exposure_to_symptom_interval": "Bà không để ý ăn được bao lâu thì bắt đầu nổi mẩn, lúc đó tôi ngồi "
                                               "bàn khác."},
      tags=("language_barrier", "collateral_history", "travel_setting", "negation", "decisive_despite_missing",
            "unknown_allergy_history"),
      test="Không biết do món nào, ăn bao lâu thì nổi, tiền sử dị ứng và thuốc đang dùng: mề đay khắp người kèm sưng "
           "môi đã đủ quyết định ESI 2; agent không được đòi tên món ăn hay tiền sử rồi mới kết luận (khác x41, x42 ở "
           "chỗ tác nhân và khoảng thời gian đều không rõ)."),
    # ------------------------------------------------------ sự việc người kể không chứng kiến
    S("x113", "teen_shower_floor_after_football_unwitnessed",
      "Con trai 14 tuổi ngồi bệt dưới sàn nhà tắm sau đá bóng, không ai thấy chuyện gì xảy ra",
      P(14, "Male", "CHILD"),
      "Con trai tôi 14 tuổi đá bóng về thì vào tắm. Chừng 15 phút trước tôi nghe trong nhà tắm có tiếng rầm, chạy "
      "vào thì thấy cháu đang ngồi bệt dưới sàn, mặt tái. Cháu bảo đang gội đầu thì tự nhiên hoa mắt, sau đó thì "
      "không nhớ rõ, không biết mình có bị lịm đi hay có đập đầu vào đâu không. Giờ cháu tỉnh táo, nói chuyện bình "
      "thường, không kêu đau ở đâu.",
      {"dizziness_present": "YES", "dizziness_sensation": "LIGHTHEADED", "symptom_onset": "SUDDEN",
       "altered_mental_status_present": "NO", "pain_present": "NO", "symptom_duration_bucket": "UNDER_1_HOUR"},
      INCOMPLETE, concepts=("presyncope", "collapse"),
      answers={"dizziness_present": "Có, lúc đang gội đầu cháu tự nhiên thấy hoa mắt.",
               "dizziness_sensation": "Cháu bảo hoa mắt, choáng váng.",
               "symptom_onset": "Tự nhiên bị, đang gội đầu thì hoa mắt.",
               "altered_mental_status_present": "Không, giờ cháu tỉnh táo, nói chuyện bình thường.",
               "pain_present": "Không, cháu không kêu đau ở đâu.",
               "symptom_duration_bucket": "Mới chừng 15 phút trước."},
      unknown={"syncope_present": "Lúc đó không ai ở trong, cháu cũng không nhớ rõ nên tôi không biết cháu có bị lịm "
                                  "đi không.",
               "seizure_present": "Không ai nhìn thấy chuyện xảy ra trong nhà tắm nên tôi không biết có co giật hay "
                                  "không.",
               "recent_head_trauma": "Cháu không nhớ, lúc đó cũng không ai thấy nên tôi không biết cháu có đập đầu "
                                     "không."},
      review_concern="Thiếu niên có thể đã ngất trong lúc tắm ngay sau khi đá bóng mà không ai chứng kiến: ngất liên "
                     "quan tới gắng sức ở người trẻ là tình huống nguy cơ cao theo Decision Point B, nên xếp ESI 2; "
                     "corpus cần dữ kiện ngất mà người kể không biết.",
      tags=("adolescent", "caregiver", "collateral_history", "null_unknown", "unwitnessed_event"),
      test="Không ai chứng kiến: không biết cháu có ngất, có co giật hay có đập đầu không (biết là có ngất thì corpus "
           "cho ESI 2); agent không được hiểu 'giờ tỉnh, không đau' là không có, phải chuyển nhân viên y tế."),
    S("x114", "daycare_reports_twitching_febrile_toddler_mother_absent",
      "Nhà trẻ báo bé 20 tháng sốt, có lúc giật giật tay chân, mẹ không chứng kiến",
      P(1, "Male", "CHILD"),
      "Cô giáo nhà trẻ gọi bảo bé nhà em 20 tháng ngủ trưa dậy thì sốt, có lúc tay chân giật giật một lúc, cô không "
      "chắc đó có phải là lên cơn không. Em đón bé về, đo nhiệt kế ở nhà được 38,7 độ. Giờ bé tỉnh, nhận ra mẹ, vẫn "
      "chơi đồ chơi, bú như mọi ngày. Ngoài sốt em chưa thấy bé ho hay đi ngoài lỏng gì.",
      {"fever_present": "YES", "temperature": 38.7, "altered_mental_status_present": "NO", "activity_level": "NORMAL",
       "feeding_intake_level": "NORMAL", "infection_source_symptom_group": "NONE_CLEAR", "cough_present": "NO",
       "diarrhea_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("fever",),
      answers={"fever_present": "Dạ có, ở nhà em đo được 38,7 độ.",
               "temperature": "Nhiệt kế ở nhà đo được 38,7 độ ạ.",
               "altered_mental_status_present": "Dạ không, giờ bé tỉnh, nhận ra mẹ.",
               "activity_level": "Bé vẫn chơi đồ chơi ạ.",
               "feeding_intake_level": "Bé vẫn bú như mọi ngày ạ.",
               "infection_source_symptom_group": "Ngoài sốt em chưa thấy gì khác ạ.",
               "cough_present": "Dạ chưa thấy bé ho.",
               "diarrhea_present": "Dạ không thấy bé đi ngoài lỏng ạ.",
               "symptom_duration_bucket": "Bé sốt từ lúc ngủ trưa dậy tới giờ ạ."},
      unknown={"seizure_present": "Em không ở đó, cô chỉ kể tay chân bé giật giật một lúc, em không biết đó có phải là "
                                  "lên cơn không ạ.",
               "seizure_occurrence": "Cô giáo cũng không chắc, em không biết bé có bị một cơn như vậy thật không ạ."},
      review_concern="Trẻ 20 tháng sốt 38,7 có thể vừa có một cơn co giật mà người kể không chứng kiến: theo Decision "
                     "Point B và bảng dấu hiệu nguy cơ ở trẻ (sốt trên 38,5 °C ở trẻ trên 3 tháng), nhiều điều dưỡng sẽ "
                     "xếp ESI 2; corpus chỉ xếp được khi biết chắc có co giật.",
      tags=("pediatric", "caregiver", "collateral_history", "null_unknown", "unwitnessed_event"),
      test="Mẹ không chứng kiến cơn 'giật giật' ở nhà trẻ, cô giáo cũng không chắc (biết là co giật thì corpus cho "
           "ESI 2): agent không được tự kết luận là có hay không co giật, phải chuyển nhân viên y tế."),
    S("x115", "crawling_infant_cough_fit_dusky_lips_grandma",
      "Bà nội xuống bếp một lát, cháu 10 tháng ho sặc, thở gấp khò khè, môi thâm tím, không ai thấy cháu ngậm gì",
      P(0, "Male", "OTHER", months=10),
      "Cháu nội tôi 10 tháng đang bò chơi ở phòng khách, tôi xuống bếp một lát thì nghe cháu ho sặc sụa. Chạy lên thấy "
      "cháu ho từng tràng, khò khè, mặt đỏ gay, môi thâm tím lại, giờ tôi bế ngồi yên mà cháu vẫn thở gấp. Dưới sàn "
      "có mấy hạt lạc với cái nắp chai nhựa, tôi không biết cháu có cho gì vào miệng không. Mới xảy ra chừng năm phút.",
      {"cough_present": "YES", "cyanosis_present": "YES", "noisy_breathing_present": "YES",
       "breathing_sound": "WHEEZING", "dyspnea_present": "YES", "dyspnea_context": "AT_REST",
       "respiratory_distress_symptoms": "AT_REST", "cardiorespiratory_symptom_present": "YES",
       "choking_relation": "UNCERTAIN", "symptom_onset": "SUDDEN", "symptom_duration_bucket": "UNDER_1_HOUR"},
      1, concepts=("cyanosis", "choking"), screen=HIT,
      answers={"cough_present": "Có, cháu ho từng tràng.",
               "cyanosis_present": "Có, môi cháu thâm tím lại.",
               "noisy_breathing_present": "Có, cháu thở khò khè.",
               "breathing_sound": "Thở khò khè.",
               "dyspnea_present": "Có, cháu thở gấp.",
               "dyspnea_context": "Tôi bế ngồi yên mà cháu vẫn thở gấp.",
               "respiratory_distress_symptoms": "Ngồi yên trong lòng tôi cháu vẫn thở gấp.",
               "cardiorespiratory_symptom_present": "Có, cháu thở gấp, khò khè.",
               "choking_relation": "Tôi không chắc, lúc cháu bắt đầu ho tôi đang ở dưới bếp.",
               "symptom_onset": "Đột ngột, cháu đang bò chơi thì ho sặc lên.",
               "symptom_duration_bucket": "Mới chừng năm phút."},
      unknown={"ent_foreign_body_present": "Tôi không thấy lúc đó nên không biết có thứ gì mắc trong họng cháu không."},
      tags=("pediatric", "caregiver", "collateral_history", "decisive_despite_missing", "unknown_mechanism",
            "unwitnessed_event"),
      test="Không ai thấy cháu cho gì vào miệng, không biết có vật mắc trong họng không: môi thâm tím đã đủ quyết định "
           "ESI 1, agent không được hỏi thêm cháu ngậm vật gì rồi mới hướng dẫn gọi cấp cứu."),
    # ------------------------------------------------------------- người kể ở thành phố khác
    S("x116", "landlord_calls_sister_brother_hearing_voices",
      "Chủ trọ báo em trai 26 tuổi nghe tiếng chửi trong tường, chị ở thành phố khác chưa hỏi được về an toàn",
      P(26, "Male", "SIBLING"),
      "Em trai mình 26 tuổi đi làm ở một thành phố khác, cách chỗ mình mấy trăm cây số. Tối nay chủ nhà trọ gọi báo "
      "mấy hôm nay em hay đứng ngoài hành lang nói chuyện một mình, bảo nghe thấy có người trong tường chửi em. Chủ "
      "trọ bảo em vẫn tự đi mua cơm, đi làm về đúng giờ. Mình gọi video thì em vẫn nhận ra mình, nói được vài câu rồi "
      "tắt máy. Mình không biết em có uống thuốc gì, có dùng chất gì không, nhà chưa ai từng đưa em đi khám chuyện "
      "này.",
      {"perceptual_disturbance_present": "YES", "perceptual_disturbance_type": "AUDITORY",
       "basic_self_care_capacity": "INDEPENDENT", "functional_status": "NORMAL",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, concepts=("hallucination",), screen=QUIET,
      answers={"perceptual_disturbance_present": "Có, chủ trọ kể em bảo nghe thấy có người trong tường chửi em.",
               "perceptual_disturbance_type": "Em bảo nghe thấy tiếng người chửi trong tường.",
               "basic_self_care_capacity": "Chủ trọ bảo em vẫn tự đi mua cơm.",
               "functional_status": "Chủ trọ bảo em vẫn đi làm, về đúng giờ.",
               "symptom_duration_bucket": "Chủ trọ bảo mấy hôm nay rồi."},
      unknown={"self_safety_status": "Em tắt máy rồi, mình chưa hỏi được em có ý nghĩ làm hại bản thân không.",
               "other_safety_status": "Mình không biết em có ý định làm hại ai không, chủ trọ cũng không nói gì chuyện "
                                      "đó.",
               "substance_involvement": "Mình ở xa nên không biết dạo này em có uống rượu hay dùng chất gì không."},
      review_concern="Người trẻ mới xuất hiện ảo thanh, chưa từng khám, chưa đánh giá được nguy cơ với bản thân và người "
                     "khác: theo AHRQ, người bệnh tâm thần cấp chưa loại trừ được nguy cơ thường được xếp ESI 2; corpus "
                     "chỉ xếp được khi biết có ý nghĩ tự hại hoặc bạo lực.",
      tags=("caregiver_remote", "mental_health", "collateral_history", "null_unknown"),
      test="Người kể ở thành phố khác, chưa hỏi được về an toàn (có ý nghĩ tự hại hay bạo lực thì corpus cho ESI 2): "
           "agent phải hỏi về ý nghĩ làm hại bản thân và người khác, không được coi 'vẫn nhận ra người nhà, vẫn đi làm' "
           "là đủ an toàn; thiếu các dữ kiện đó thì chuyển nhân viên y tế."),
    S("x117", "remote_son_father_bowl_of_red_vomit",
      "Con đi công tác xa nhận điện bố 68 tuổi ói ra một bát máu đỏ, không rõ rượu, thuốc, không có máy đo",
      P(68, "Male", "PARENT"),
      "Tôi đang đi công tác ở tỉnh khác, bố tôi 68 tuổi ở quê một mình. Bố vừa gọi bảo chừng nửa tiếng trước ói ra một "
      "bát toàn máu đỏ, giờ người lả đi, chóng mặt. Tôi đã nhờ hàng xóm chạy sang. Tôi không biết dạo này bố có uống "
      "rượu nhiều hay tự mua thuốc đau khớp về uống không, nhà bố cũng không có máy đo huyết áp.",
      {"vomiting_present": "YES", "vomit_appearance": "BLOODY", "vomiting_frequency": "ONCE",
       "gastrointestinal_symptom_present": "YES", "dizziness_present": "YES",
       "associated_systemic_symptoms": "GENERAL_WEAKNESS", "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("hematemesis",), screen=HIT,
      answers={"vomiting_present": "Có, bố bảo vừa ói ra máu.",
               "vomit_appearance": "Bố bảo ói ra một bát toàn máu đỏ.",
               "vomiting_frequency": "Bố nói ói một lần.",
               "gastrointestinal_symptom_present": "Có, bố ói ra máu.",
               "dizziness_present": "Có, bố kêu chóng mặt.",
               "associated_systemic_symptoms": "Bố bảo người lả đi.",
               "symptom_duration_bucket": "Bố bảo chừng nửa tiếng trước."},
      unknown={"substance_involvement": "Tôi ở xa nên không biết dạo này bố có uống rượu không.",
               "toxic_exposure_present": "Tôi không biết bố có tự mua thuốc gì về uống không.",
               "systolic_bp": "Nhà bố không có máy đo huyết áp, hàng xóm cũng chưa sang tới."},
      tags=("caregiver_remote", "older_adult", "decisive_despite_missing", "missing_vitals", "null_unknown"),
      test="Người kể ở xa, không biết bố có uống rượu hay thuốc giảm đau, không có huyết áp: ói ra một bát máu đã đủ "
           "quyết định ESI 2; agent không được đòi số đo hay tiền sử rồi mới hướng dẫn gọi cấp cứu."),
    # ------------------------------------------------- người kể dịch cho người bệnh nói tiếng khác
    S("x118", "kinh_daughter_in_law_highland_father_vertigo",
      "Con dâu hiểu ít tiếng dân tộc: bố chồng 70 tuổi chóng mặt quay, nôn, không biết có nói ngọng, yếu tay chân",
      P(70, "Male", "OTHER"),
      "Em là người Kinh, lấy chồng trên bản. Bố chồng em 70 tuổi chỉ nói tiếng dân tộc, em hiểu được dăm câu. Từ "
      "trưa ông tự nhiên chóng mặt, ông ra hiệu là nhà cửa quay tròn, nôn mấy lần, cứ cử động đầu là nôn nên ông nằm "
      "im. Ông vẫn tỉnh, nhìn theo em, gật đầu khi em hỏi. Ông có nói nhưng em không rành tiếng của ông nên không "
      "nghe ra ông nói có khác mọi khi không. Chồng em đi rừng chưa về.",
      {"dizziness_present": "YES", "dizziness_sensation": "SPINNING", "symptom_onset": "SUDDEN",
       "vomiting_present": "YES", "vomiting_frequency": "FEW_TIMES", "gastrointestinal_symptom_present": "YES",
       "altered_mental_status_present": "NO", "functional_status": "MARKEDLY_REDUCED",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("vertigo", "vomiting"), screen=QUIET,
      answers={"dizziness_present": "Dạ có, ông chóng mặt từ trưa.",
               "dizziness_sensation": "Ông ra hiệu là nhà cửa quay tròn ạ.",
               "symptom_onset": "Ông tự nhiên bị chứ không phải từ từ ạ.",
               "vomiting_present": "Dạ có, ông nôn mấy lần.",
               "vomiting_frequency": "Nôn mấy lần rồi ạ.",
               "gastrointestinal_symptom_present": "Dạ có, ông nôn mấy lần.",
               "altered_mental_status_present": "Dạ không, ông vẫn tỉnh, nhìn theo em, gật đầu khi em hỏi.",
               "functional_status": "Ông chỉ nằm im, cử động đầu là nôn ạ.",
               "symptom_duration_bucket": "Từ trưa tới giờ ạ."},
      unknown={"focal_neurologic_symptoms": "Ông có nói nhưng em không rành tiếng của ông nên không biết ông nói có ngọng "
                                            "hơn mọi khi không, ông nằm im nên em cũng không biết tay chân ông có yếu "
                                            "không ạ."},
      review_concern="Người 70 tuổi chóng mặt quay đột ngột kèm nôn, rào cản ngôn ngữ không cho loại trừ dấu thần kinh "
                     "khu trú: tổn thương thân não, tiểu não có thể biểu hiện như vậy; nhiều điều dưỡng sẽ xếp ESI 2 theo "
                     "Decision Point B; corpus chỉ xếp được khi biết có dấu thần kinh khu trú.",
      tags=("older_adult", "language_barrier", "collateral_history", "highland_setting", "null_unknown"),
      test="Rào cản ngôn ngữ chặn câu hỏi về nói ngọng, yếu tay chân (có một dấu khu trú thì corpus cho ESI 2): agent "
           "không được coi 'ông vẫn nói được' là nói bình thường hay tự ghi 'không có dấu khu trú', phải chuyển nhân viên "
           "y tế."),
    S("x119", "boarding_school_teacher_translates_father_child_diarrhoea",
      "Giáo viên bán trú dịch cho bố học sinh: bé 8 tuổi tiêu chảy ba hôm, ăn kém, tiểu ít",
      P(8, "Female", "OTHER"),
      "Tôi là giáo viên ở một điểm trường bán trú trên bản. Bố của một em học sinh nữ 8 tuổi chỉ nói tiếng dân tộc, "
      "nhờ tôi hỏi giúp. Em kể ba hôm nay đi ngoài phân lỏng nhiều lần, ăn ít hẳn so với mọi ngày, từ hôm qua đi tiểu "
      "ít hơn. Nhiệt kế ở trường đo được 37,3 độ, em vẫn tỉnh, trả lời tôi rõ ràng. Tôi hỏi trong nhà có ai cũng bị "
      "như em không thì anh ấy không hiểu câu hỏi.",
      {"diarrhea_present": "YES", "stool_appearance": "LOOSE", "gastrointestinal_symptom_present": "YES",
       "oral_intake_tolerance": "REDUCED", "urination_status": "DECREASED", "urine_output_status": "REDUCED",
       "temperature": 37.3, "fever_present": "NO", "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, concepts=("diarrhea", "dehydration"), screen=QUIET,
      answers={"diarrhea_present": "Có, ba hôm nay em đi ngoài phân lỏng nhiều lần.",
               "stool_appearance": "Phân lỏng.",
               "gastrointestinal_symptom_present": "Có, em đi ngoài phân lỏng nhiều lần.",
               "oral_intake_tolerance": "Em ăn ít hẳn so với mọi ngày.",
               "urination_status": "Từ hôm qua em đi tiểu ít hơn.",
               "urine_output_status": "Từ hôm qua em tiểu ít hơn bình thường.",
               "temperature": "Nhiệt kế ở trường đo được 37,3 độ.",
               "fever_present": "Không, nhiệt kế đo được 37,3 độ thôi.",
               "altered_mental_status_present": "Không, em vẫn tỉnh, trả lời tôi rõ ràng.",
               "symptom_duration_bucket": "Ba hôm nay rồi."},
      unknown={"similar_symptoms_in_others": "Tôi hỏi trong nhà có ai cũng bị không thì anh ấy không hiểu câu hỏi, nên "
                                             "tôi không biết."},
      tags=("pediatric", "language_barrier", "collateral_history", "highland_setting", "school_setting"),
      test="Rào cản ngôn ngữ chặn câu hỏi về người trong nhà, nhưng thông tin đó không đổi được mức: agent không được "
           "chuyển 'không đủ thông tin', ăn kém kèm tiểu ít đã đủ xếp ESI 3."),
    S("x120", "foreign_engineer_canteen_stiffening_jerking",
      "Kỹ sư nước ngoài mới sang hai tuần cứng người, giật tay chân ở nhà ăn, không ai biết tiền sử",
      P(41, "Male", "OTHER"),
      "Tôi là tổ trưởng ở một xưởng cơ khí. Chừng mười lăm phút trước, một anh kỹ sư người nước ngoài 41 tuổi mới sang "
      "làm được hai tuần đang ăn trưa ở nhà ăn thì ngã khỏi ghế, người cứng đờ rồi giật tay chân liên hồi chừng hai "
      "phút. Giờ hết giật nhưng anh còn lơ mơ, gọi to mới mở mắt nhìn. Anh không nói được tiếng Việt, phiên dịch hôm "
      "nay nghỉ, nên không ai biết anh có bệnh gì từ trước hay đang uống thuốc gì.",
      {"seizure_present": "YES", "seizure_occurrence": "YES", "altered_mental_status_present": "YES",
       "trauma_present": "YES", "trauma_mechanism": "FALL", "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("seizure",), screen=HIT,
      answers={"seizure_present": "Có, anh người cứng đờ rồi giật tay chân liên hồi.",
               "seizure_occurrence": "Có, mọi người ở nhà ăn thấy anh giật tay chân chừng hai phút.",
               "altered_mental_status_present": "Có, giờ anh còn lơ mơ, gọi to mới mở mắt nhìn.",
               "trauma_present": "Anh ngã khỏi ghế xuống sàn lúc bắt đầu bị.",
               "trauma_mechanism": "Ngã từ ghế xuống sàn.",
               "symptom_duration_bucket": "Mới chừng mười lăm phút."},
      unknown={"recent_head_trauma": "Lúc anh ngã mọi người hoảng quá nên không ai để ý anh có đập đầu không.",
               "injury_region": "Không ai để ý lúc ngã anh va vào chỗ nào.",
               "substance_involvement": "Anh mới sang, không ai biết anh có uống rượu hay dùng chất gì không."},
      tags=("language_barrier", "collateral_history", "occupational", "foreign_worker", "decisive_despite_missing"),
      test="Không ai biết tiền sử, thuốc men, có đập đầu hay dùng chất gì không: cơn cứng người, giật tay chân kèm lơ mơ "
           "sau cơn đã đủ quyết định ESI 2; agent không được đòi tiền sử động kinh hay chờ phiên dịch rồi mới kết luận."),
]
