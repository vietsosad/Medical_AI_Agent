"""Nhóm MISSING_INFO, đợt 3 lượt 2 (tệp c): số đo và mốc thời gian không biết được (lớp lỗi F3).

Vẫn hai kiểu ca như ``missing.py``, ``b2_missing.py`` và ``b3_missing.py``:

- thiếu đúng dữ kiện quyết định -> kỳ vọng RETURN_INCOMPLETE (chuyển nhân viên y tế). Câu "không biết"
  nằm trong ``unknown``; không bao giờ được hiểu thành "không có", cũng không được tự hiểu thành "có".
- dữ kiện đã nêu đủ quyết định dù thiếu phần khác -> agent phải kết luận ngay, không đòi thêm số đo
  (tag ``decisive_despite_missing``).

Ngoài ra có ca ESI 3: dữ kiện đã nêu khớp tiêu chí ESI 3, phần còn thiếu không được làm agent chuyển thành
"không đủ thông tin" hay tự nâng mức.

Tệp này chỉ đổi nguồn của chữ "không biết" sang SỐ ĐO và MỐC THỜI GIAN: máy đo không vừa người bệnh (máy kẹp
ngón người lớn trên ngón trẻ nhỏ, băng quấn người lớn trên tay trẻ), máy cho số không tin được (nhiệt kế đo
trán mỗi lần một số, đồng hồ thông minh lúc 38 lúc 70, ứng dụng đo mạch bằng camera điện thoại), người kể
không đọc được nhiệt kế thủy ngân, nhiệt độ đo ngay sau tắm nước nóng, mạch yếu không đếm ra, không ai đếm số
lần nôn, không ai biết lần cuối đi ngoài, đang ngủ nên không biết khởi phát, người kể về sau mới thấy, người
bệnh không chấm được điểm đau (trẻ nhũ nhi, sa sút trí tuệ, đau vết mổ lẫn tức bàng quang, không nói được).

Quy ước riêng của tệp này:

- Lời mở đầu có thể nhắc con số máy hiện ra mà người kể không tin (nhiệt kế đo trán, đồng hồ thông minh,
  nhiệt độ đo ngay sau tắm nước nóng); dữ kiện đó vẫn nằm trong ``unknown`` vì giá trị thật sự không biết.
  Câu trả lời trong ``unknown`` không nhắc lại con số.
- Một cặp tối thiểu có chủ đích: x90/x91 (đang hoá trị: không biết có sốt, so với người nóng hầm hập mà không
  có con số).
"""

from __future__ import annotations

from eval.generated_mock_v2.spec import INCOMPLETE, MISSING, P, SCREEN_HIT as HIT, SCREEN_QUIET as QUIET, Spec


def S(key: str, family: str, title: str, profile: dict, opening: str, facts: dict, intended, **kw) -> Spec:
    return Spec(case_id=key, family=family, group=MISSING, title=title, profile=profile,
                opening=opening, facts=facts, intended=intended, **kw)


SPECS = [
    # ------------------------------------------------------------------ trẻ em
    S("x81", "infant_7wk_forehead_thermometer_jumping", "Bé 7 tuần sờ âm ấm, nhiệt kế đo trán mỗi lần một số",
      P(0, "Female", "CHILD", months=1),
      "Bé gái nhà em được 7 tuần. Từ chiều em sờ người bé thấy âm ấm, lấy cái nhiệt kế bắn trán ra đo ba lần thì "
      "ra ba số khác nhau, lúc 36 mấy, lúc lại 38 mấy, em không biết tin số nào. Nhà em chỉ có mỗi cái nhiệt kế đó. "
      "Bé vẫn bú nhưng mỗi cữ ít hơn mọi hôm một chút, không trớ, vẫn cựa quậy, khóc to.",
      {"feeding_intake_level": "MILDLY_REDUCED", "oral_intake_tolerance": "REDUCED",
       "vomiting_or_feeding_problem_present": "YES", "fluid_retention": "ABLE_TO_KEEP_FLUIDS", "vomiting_present": "NO",
       "activity_level": "NORMAL", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("fever", "young_infant_age"), screen=QUIET,
      answers={"feeding_intake_level": "Bé vẫn bú nhưng mỗi cữ ít hơn mọi hôm một chút ạ.",
               "oral_intake_tolerance": "Bé vẫn bú được, chỉ là mỗi cữ ít hơn một chút, không trớ ra ạ.",
               "vomiting_or_feeding_problem_present": "Dạ có, bé bú ít hơn mọi hôm một chút ạ.",
               "fluid_retention": "Bú vào bé giữ được, không trớ ạ.",
               "vomiting_present": "Dạ không, bé không trớ ạ.",
               "activity_level": "Bé vẫn cựa quậy, khóc to như mọi khi ạ.",
               "symptom_duration_bucket": "Em sờ thấy âm ấm từ chiều tới giờ ạ."},
      unknown={"temperature": "Cái nhiệt kế bắn trán mỗi lần đo ra một số khác nhau, em không biết số nào là đúng ạ.",
               "fever_present": "Em không chắc bé có sốt thật hay không vì chưa đo được con số nào tin được ạ."},
      tags=("pediatric", "caregiver", "missing_vitals", "device_unreliable", "age_adjusted_vitals"),
      test="Nhiệt kế đo trán cho ba số khác nhau ở trẻ 7 tuần: agent không được chọn một số (36 mấy hay 38 mấy) làm "
           "nhiệt độ, cũng không được ghi là không sốt; chưa có nhiệt độ tin được thì phải chuyển nhân viên y tế (sốt "
           "ở trẻ 1-3 tháng là nguy cơ AHRQ Table 6-2 yêu cầu cân nhắc ESI 2)."),
    S("x82", "tof_toddler_crying_spell_adult_oximeter", "Bé 14 tháng tứ chứng Fallot khóc lả, môi lưỡi tím sẫm, máy kẹp ngón người lớn không lên số",
      P(1, "Male", "CHILD", chronic=("Tứ chứng Fallot đang chờ mổ",), meds=("Propranolol uống sáng và tối",)),
      "Con trai em 14 tháng bị tứ chứng Fallot, đang chờ tới lịch mổ. Chừng mười phút nay bé khóc thét không dỗ "
      "được, rồi môi với lưỡi tím sẫm hơn hẳn mọi khi, thở gấp, sau đó lả dần, người mềm oặt. Em kẹp thử máy đo "
      "oxy của bà mà ngón tay bé nhỏ quá, máy không lên số. Em cũng không đếm được bé thở bao nhiêu.",
      {"cyanosis_present": "YES", "dyspnea_present": "YES", "dyspnea_context": "AT_REST",
       "respiratory_distress_symptoms": "AT_REST",
       "cardiorespiratory_symptom_present": "YES", "activity_level": "VERY_INACTIVE",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      1, concepts=("cyanosis", "history_of_congenital_heart_disease"), screen=HIT,
      answers={"cyanosis_present": "Có, môi với lưỡi bé tím sẫm hơn hẳn mọi khi.",
               "dyspnea_present": "Có, bé thở gấp lắm.",
               "dyspnea_context": "Em bế bé ngồi yên trong lòng mà bé vẫn thở gấp.",
               "respiratory_distress_symptoms": "Em bế bé ngồi yên mà bé vẫn thở gấp.",
               "cardiorespiratory_symptom_present": "Có, bé thở gấp, môi tím sẫm lại.",
               "activity_level": "Khóc một hồi xong bé lả dần, người mềm oặt ra.",
               "symptom_duration_bucket": "Mới chừng mười phút nay."},
      unknown={"spo2": "Máy đo oxy của bà là loại cho người lớn, kẹp vào ngón bé không lên số nào.",
               "respiratory_rate": "Em không đếm được bé thở bao nhiêu."},
      tags=("pediatric", "caregiver", "comorbidity", "missing_vitals", "device_unreliable", "decisive_despite_missing",
            "single_decisive_symptom"),
      test="Máy đo oxy người lớn không đọc được trên ngón tay trẻ 14 tháng, không đếm được nhịp thở: môi lưỡi tím sẫm "
           "hơn hẳn mọi khi trong cơn khóc ở trẻ tim bẩm sinh tím đã đủ quyết định ESI 1; agent không được chờ số SpO2 "
           "hay coi tím là chuyện 'vốn vẫn tím'."),
    S("x83", "toddler_booster_shot_evening_fever", "Bé 18 tháng sốt 38,4 tối sau mũi tiêm nhắc, ăn uống kém, bà không đếm được mạch",
      P(1, "Female", "OTHER"),
      "Cháu nội tôi 18 tháng, sáng nay bố mẹ cháu đưa đi tiêm mũi nhắc ở trạm y tế phường. Từ chập tối cháu sốt, "
      "tôi kẹp nhiệt kế điện tử ở nách được 38,4 độ. Cháu quấy, chỉ ăn được vài thìa cháo, bú sữa cũng ít hơn hẳn, "
      "nhưng không nôn, không ho, không đi ngoài lỏng. Tôi sợ cháu bị phản ứng thuốc tiêm. Tôi đặt tay lên ngực cháu "
      "mà không đếm được tim đập bao nhiêu.",
      {"fever_present": "YES", "temperature": 38.4, "oral_intake_tolerance": "REDUCED",
       "feeding_intake_level": "MARKEDLY_REDUCED", "vomiting_or_feeding_problem_present": "YES",
       "fluid_retention": "ABLE_TO_KEEP_FLUIDS", "vomiting_present": "NO", "cough_present": "NO", "diarrhea_present": "NO",
       "infection_source_symptom_group": "NONE_CLEAR", "suspected_trigger_exposure_present": "YES",
       "suspected_allergy_trigger": "VACCINE", "exposure_to_symptom_interval": "WITHIN_HOURS",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      3, concepts=("fever", "recent_vaccination"), screen=QUIET,
      answers={"fever_present": "Có, cháu sốt từ chập tối.",
               "temperature": "Tôi kẹp nhiệt kế điện tử ở nách được 38,4 độ.",
               "oral_intake_tolerance": "Cháu chỉ ăn được vài thìa cháo, sữa cũng bú ít hơn hẳn, nhưng không nôn.",
               "feeding_intake_level": "Ăn được vài thìa cháo, bú sữa ít hơn hẳn mọi ngày.",
               "vomiting_or_feeding_problem_present": "Có, cháu ăn uống kém hơn hẳn.",
               "fluid_retention": "Cháu uống vào thì giữ được, không nôn.",
               "vomiting_present": "Không, cháu không nôn.",
               "cough_present": "Không, cháu không ho.",
               "diarrhea_present": "Không, cháu không đi ngoài lỏng.",
               "infection_source_symptom_group": "Ngoài sốt thì cháu không ho, không đi ngoài lỏng, chỉ quấy thôi.",
               "suspected_trigger_exposure_present": "Có, sáng nay cháu vừa đi tiêm mũi nhắc.",
               "suspected_allergy_trigger": "Tôi sợ là do mũi tiêm nhắc sáng nay.",
               "exposure_to_symptom_interval": "Tiêm từ sáng, tới chập tối thì cháu sốt.",
               "symptom_duration_bucket": "Cháu sốt từ chập tối tới giờ."},
      unknown={"heart_rate": "Tôi đặt tay lên ngực cháu mà không đếm được tim đập bao nhiêu."},
      tags=("pediatric", "caregiver", "missing_vitals", "vaccine_concern"),
      test="Sốt 38,4 đo được kèm ăn uống kém sau mũi tiêm nhắc đã khớp tiêu chí ESI 3: thiếu mạch không được làm agent "
           "chuyển thành 'không đủ thông tin', và nỗi lo 'phản ứng thuốc tiêm' không được đẩy lên ESI 2 khi không có dấu "
           "hiệu nguy hiểm nào được kể."),
    S("x84", "kindergarten_slide_fall_vomit_uncounted", "Cô giáo mầm non: bé 3 tuổi ngã cầu trượt đập trán, có nôn nhưng không ai nhớ mấy lần",
      P(3, "Male", "OTHER"),
      "Em là cô giáo mầm non. Chừng một tiếng rưỡi trước, một bé trai 3 tuổi lớp em trượt chân từ bậc thang cầu "
      "trượt, đập trán xuống nền sân, khóc ngay, trán sưng một cục, bé kêu đau. Lúc em chạy đi lấy đá chườm thì cô "
      "bảo mẫu báo bé có nôn, cô ấy dọn luôn rồi, giờ hỏi lại thì cô ấy không nhớ bé nôn một lần hay mấy lần. Hiện "
      "bé ngồi trong lòng em, hỏi gì vẫn trả lời.",
      {"trauma_present": "YES", "trauma_mechanism": "FALL", "injury_region": "HEAD", "recent_head_trauma": "YES",
       "visible_head_injury_sign": "SCALP_SWELLING", "post_trauma_awareness_change": "NONE",
       "altered_mental_status_present": "NO", "vomiting_present": "YES", "gastrointestinal_symptom_present": "YES",
       "pain_present": "YES", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("head_injury", "vomiting"), screen=QUIET,
      answers={"trauma_present": "Có, bé trượt chân ngã từ bậc thang cầu trượt, đập trán xuống nền sân ạ.",
               "trauma_mechanism": "Bé trượt chân ngã từ bậc thang cầu trượt ạ.",
               "injury_region": "Bé đập trán, ở đầu ạ.",
               "recent_head_trauma": "Có, bé đập trán xuống nền sân ạ.",
               "visible_head_injury_sign": "Trán bé sưng một cục ạ.",
               "post_trauma_awareness_change": "Bé khóc ngay lúc ngã, giờ hỏi gì vẫn trả lời ạ.",
               "altered_mental_status_present": "Không, bé vẫn tỉnh, hỏi gì vẫn trả lời ạ.",
               "vomiting_present": "Có, cô bảo mẫu báo bé có nôn ạ.",
               "gastrointestinal_symptom_present": "Có, cô bảo mẫu báo bé có nôn ạ.",
               "pain_present": "Có, bé kêu đau trán ạ.",
               "symptom_duration_bucket": "Bé ngã chừng một tiếng rưỡi trước ạ."},
      unknown={"post_trauma_vomiting_count": "Em không thấy lúc bé nôn, cô bảo mẫu dọn rồi mà không nhớ là mấy lần ạ.",
               "vomiting_frequency": "Em không biết bé nôn mấy lần ạ.",
               "pain_severity": "Bé mới 3 tuổi, hỏi đau nhiều hay ít thì bé chỉ khóc ạ."},
      tags=("pediatric", "collateral_history", "null_unknown", "school_setting"),
      test="Không ai đếm số lần nôn sau va đập đầu: tiêu chí chấn thương đầu nôn nhiều lần cần biết từ hai lần trở lên, "
           "agent không được tự coi là nôn một lần (hay nhiều lần) mà phải chuyển nhân viên y tế."),
    S("x85", "bike_handlebar_belly_child_adult_cuff_too_big", "Bé 6 tuổi bị ghi đông xe đạp thúc vào bụng trái, tối đau bụng, xanh, ói, máy đo huyết áp người lớn báo lỗi",
      P(6, "Male", "CHILD"),
      "Con trai tui 6 tuổi, chiều nay chạy xe đạp tông vô gốc cây, cái ghi đông thúc mạnh vô bụng bên trái. Lúc đó "
      "bé khóc chút rồi chơi tiếp, tới tối thì kêu đau bụng bên trái, mặt xanh, nằm một chỗ hổng chịu chơi, ói một lần. "
      "Bé vẫn tỉnh, hỏi vẫn trả lời. Máy đo huyết áp nhà tui là của ông ngoại, băng quấn to quá, quấn vô tay bé cứ lỏng, "
      "đo hai lần máy đều báo lỗi, tui cũng hổng biết bắt mạch. Hỏi đau mấy điểm thì bé chỉ khóc.",
      {"trauma_present": "YES", "trauma_mechanism": "BICYCLE_COLLISION", "post_trauma_awareness_change": "NONE",
       "abdominal_pain_present": "YES", "abdominal_pain_location": "LEFT_SIDE", "pain_present": "YES",
       "vomiting_present": "YES", "vomiting_frequency": "ONCE", "gastrointestinal_symptom_present": "YES",
       "activity_level": "LESS_ACTIVE", "altered_mental_status_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("abdominal_pain", "direct_blunt_trauma"), screen=QUIET,
      answers={"trauma_present": "Có, bé chạy xe đạp tông vô gốc cây, ghi đông thúc vô bụng bên trái.",
               "trauma_mechanism": "Chạy xe đạp tông vô gốc cây, ghi đông thúc vô bụng.",
               "post_trauma_awareness_change": "Lúc đó bé khóc chút rồi chơi tiếp, giờ vẫn tỉnh.",
               "abdominal_pain_present": "Có, tới tối bé kêu đau bụng bên trái.",
               "abdominal_pain_location": "Bên trái, chỗ ghi đông thúc vô.",
               "pain_present": "Có, bé kêu đau bụng bên trái.",
               "vomiting_present": "Có, bé ói một lần.",
               "vomiting_frequency": "Ói một lần.",
               "gastrointestinal_symptom_present": "Có, bé đau bụng, ói một lần.",
               "activity_level": "Bé nằm một chỗ, hổng chịu chơi.",
               "altered_mental_status_present": "Hông, bé vẫn tỉnh, hỏi vẫn trả lời.",
               "symptom_duration_bucket": "Té hồi chiều, tới tối mới kêu đau bụng."},
      unknown={"systolic_bp": "Băng quấn của máy to quá so với tay bé, đo hai lần máy đều báo lỗi.",
               "heart_rate": "Tui hổng biết bắt mạch, máy thì báo lỗi nên cũng hổng ra số mạch.",
               "pain_severity": "Hỏi đau mấy điểm thì bé chỉ khóc."},
      review_concern="Trẻ 6 tuổi bị ghi đông xe đạp thúc vào bụng trái, vài giờ sau đau bụng, xanh, nằm im, nôn: cơ chế có "
                     "nguy cơ tổn thương lách hoặc tạng đặc chảy máu trong; theo AHRQ Decision Point B đây là tình huống nguy "
                     "cơ cao, nên xếp ESI 2; corpus chỉ xếp được khi có huyết áp, mạch hoặc điểm đau, mà máy đo người lớn "
                     "không đo được trên tay trẻ.",
      tags=("pediatric", "caregiver", "missing_vitals", "device_unreliable", "dialect", "hidden_red_flag", "null_unknown"),
      test="Máy đo huyết áp người lớn không đo được trên tay trẻ 6 tuổi, không ai bắt mạch, trẻ không chấm được điểm đau: "
           "'lúc đó vẫn chơi tiếp' không được hiểu là va chạm nhẹ; agent phải chuyển nhân viên y tế ngay chứ không được hẹn "
           "theo dõi ở nhà."),
    S("x86", "teen_left_testis_pain_woke_night_refuses_exam", "Thiếu niên 14 tuổi đau tinh hoàn trái từ nửa đêm, không rõ khởi phát, không chịu chấm điểm đau",
      P(14, "Male", "CHILD"),
      "Thằng con tôi 14 tuổi, sáng nay mãi mới chịu nói là từ nửa đêm nó bị đau ở tinh hoàn bên trái, đau lan lên "
      "bụng dưới, sáng ra còn nôn một lần. Tôi hỏi đau tự nhiên ập tới hay đau tăng dần thì nó bảo lúc đó đang ngủ nên "
      "không biết. Hỏi đau mấy điểm nó cũng không chịu nói, ngại không cho tôi xem.",
      {"genitourinary_pain_present": "YES", "genitourinary_pain_location": "TESTICULAR",
       "genitourinary_pain_laterality": "LEFT", "genitourinary_pain_radiation": "TO_LOWER_ABDOMEN", "pain_present": "YES",
       "genital_symptom_present": "YES", "abdominal_pain_present": "YES", "abdominal_pain_location": "LOWER_ABDOMEN",
       "vomiting_present": "YES", "vomiting_frequency": "ONCE", "gastrointestinal_symptom_present": "YES",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("testicular_pain",), screen=QUIET,
      answers={"genitourinary_pain_present": "Có, nó bị đau ở tinh hoàn bên trái.",
               "genitourinary_pain_location": "Đau ở tinh hoàn.",
               "genitourinary_pain_laterality": "Bên trái.",
               "genitourinary_pain_radiation": "Nó bảo đau lan lên bụng dưới.",
               "pain_present": "Có, nó đau ở tinh hoàn bên trái.",
               "genital_symptom_present": "Có, nó kêu đau ở tinh hoàn bên trái.",
               "abdominal_pain_present": "Có, nó bảo đau lan lên bụng dưới.",
               "abdominal_pain_location": "Bụng dưới, lan từ tinh hoàn lên.",
               "vomiting_present": "Có, sáng ra nó nôn một lần.",
               "vomiting_frequency": "Nôn một lần.",
               "gastrointestinal_symptom_present": "Có, sáng ra nó nôn một lần.",
               "symptom_duration_bucket": "Nó bảo đau từ nửa đêm tới giờ."},
      unknown={"symptom_onset": "Nó bảo lúc đó đang ngủ nên không biết đau ập tới hay tăng dần.",
               "pain_severity": "Nó không chịu nói đau mấy điểm.",
               "visible_genital_change": "Nó ngại, không cho tôi xem nên tôi không biết có sưng hay đổi màu không."},
      review_concern="Thiếu niên đau tinh hoàn một bên từ nửa đêm kèm nôn: phải loại trừ xoắn tinh hoàn (cứu được tinh hoàn hay "
                     "không tính bằng giờ); theo AHRQ Decision Point B đây là tình huống nguy cơ cao, nên xếp ESI 2; corpus cần "
                     "biết khởi phát đột ngột hoặc điểm đau từ 7, mà người bệnh không trả lời được.",
      tags=("adolescent", "caregiver", "unknown_onset", "null_unknown", "reluctant_patient"),
      test="Không biết khởi phát đột ngột hay từ từ, không có điểm đau, không ai được xem: agent không được coi 'không biết' "
           "là 'từ từ' hay là đau nhẹ để hẹn khám sau, phải chuyển nhân viên y tế ngay."),
    # ------------------------------------------------- người lớn, người cao tuổi, nhũ nhi (x87-x100)
    S("x87", "diabetic_numb_foot_ulcer_hot_bath_reading", "Ông 63 tuổi tiểu đường tê chân, vợ mới thấy vết loét sưng đỏ gan bàn chân, đo nhiệt ngay sau tắm nước nóng",
      P(63, "Male", "SPOUSE", chronic=("Đái tháo đường type 2", "Tê bì hai bàn chân do biến chứng tiểu đường"),
        meds=("Insulin tiêm sáng và tối",)),
      "Chồng tôi 63 tuổi bị tiểu đường lâu năm, hai bàn chân tê bì sẵn rồi. Tối nay tôi rửa chân cho ông mới thấy "
      "dưới gan bàn chân phải có một vết loét, quanh đó sưng đỏ, sờ vào nóng. Ông bảo không thấy đau gì vì chân tê, "
      "cũng không biết vết loét có từ bao giờ, vẫn đi lại bình thường. Tôi kẹp nhiệt kế cho ông thì ra 37,9 nhưng ông "
      "vừa tắm nước nóng xong nên tôi không tin số đó. Nhà không có máy đo huyết áp, tôi cũng không biết bắt mạch.",
      {"lower_extremity_problem_present": "YES", "lower_extremity_injury_location": "FOOT",
       "weight_bearing_ability": "NORMAL", "distal_limb_symptoms": "NUMBNESS", "wound_status": "OPEN_WOUND",
       "wound_present": "YES", "wound_location": "FOOT_TOE", "wound_type": "OTHER", "swelling_present": "YES",
       "swelling_location": "OTHER", "rash_or_skin_finding_present": "YES",
       "skin_finding_appearance": "ULCER_OR_OPEN_SKIN", "skin_finding_distribution": "LOCALIZED", "pain_present": "NO"},
      INCOMPLETE, concepts=("skin_ulcer", "lower_extremity_wound"), screen=QUIET,
      answers={"lower_extremity_problem_present": "Có, dưới gan bàn chân phải có một vết loét, quanh đó sưng đỏ.",
               "lower_extremity_injury_location": "Ở gan bàn chân phải.",
               "weight_bearing_ability": "Ông vẫn đi lại bình thường.",
               "distal_limb_symptoms": "Hai bàn chân ông tê bì sẵn từ lâu rồi.",
               "wound_status": "Là vết loét hở dưới gan bàn chân.",
               "wound_present": "Có, một vết loét dưới gan bàn chân phải.",
               "wound_location": "Dưới gan bàn chân phải.",
               "wound_type": "Là một vết loét.",
               "swelling_present": "Có, quanh vết loét sưng đỏ.",
               "swelling_location": "Sưng ở quanh vết loét dưới gan bàn chân phải.",
               "rash_or_skin_finding_present": "Có, quanh vết loét da đỏ, sờ vào nóng.",
               "skin_finding_appearance": "Một vết loét hở, quanh đó đỏ.",
               "skin_finding_distribution": "Chỉ ở một chỗ dưới gan bàn chân phải.",
               "pain_present": "Ông bảo không thấy đau gì vì chân tê."},
      unknown={"temperature": "Ông vừa tắm nước nóng xong tôi mới đo nên tôi không tin con số đó, chưa đo lại.",
               "fever_present": "Tôi không biết ông có sốt hay không.",
               "heart_rate": "Tôi không biết bắt mạch.",
               "systolic_bp": "Nhà không có máy đo huyết áp.",
               "symptom_duration_bucket": "Ông bảo không biết vết loét có từ bao giờ, chân tê nên không thấy gì.",
               "symptom_trend": "Tối nay tôi mới thấy nên không biết chỗ đỏ có đang lan ra hay không."},
      tags=("comorbidity", "caregiver", "missing_vitals", "unknown_onset", "masked_pain", "unreliable_measurement"),
      test="Số 37,9 đo ngay sau tắm nước nóng không đáng tin, không có mạch, huyết áp, không biết vết loét có từ bao giờ "
           "và chỗ đỏ có lan không: agent không được ghi 37,9 làm nhiệt độ hay coi 'không đau' là nhẹ, phải chuyển nhân "
           "viên y tế."),
    S("x88", "rul_pain_measured_fever_no_pulse_or_bp", "Đau âm ỉ dưới sườn phải 6/10, nhiệt kế 38,4, tự bắt mạch không đếm được, nhà không có máy đo huyết áp",
      P(46, "Female", allergies=("Dị ứng amoxicillin",)),
      "Tôi 46 tuổi. Từ nửa đêm qua tôi đau âm ỉ ở dưới sườn bên phải, giờ khoảng 6 trên 10, buồn nôn nhưng chưa nôn, "
      "vẫn ăn được cháo như mọi khi. Sáng nay đo nhiệt kế điện tử ở nách được 38,4 độ. Nhà chỉ có mỗi cái nhiệt kế, "
      "không có máy đo huyết áp, tôi tự bắt mạch ở cổ tay mà đếm không được.",
      {"abdominal_pain_present": "YES", "abdominal_pain_location": "RIGHT_SIDE", "abdominal_pain_character": "DULL",
       "pain_present": "YES", "pain_severity": 6, "gastrointestinal_symptom_present": "YES", "vomiting_present": "NO",
       "oral_intake_tolerance": "NORMAL", "fever_present": "YES", "temperature": 38.4,
       "infection_source_symptom_group": "GASTROINTESTINAL", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      3, concepts=("abdominal_pain", "fever"), screen=QUIET,
      answers={"abdominal_pain_present": "Có, tôi đau âm ỉ dưới sườn bên phải.",
               "abdominal_pain_location": "Ở dưới sườn bên phải.",
               "abdominal_pain_character": "Đau âm ỉ.",
               "pain_present": "Có, đau âm ỉ dưới sườn phải.",
               "pain_severity": "Khoảng 6 trên 10.",
               "gastrointestinal_symptom_present": "Có, tôi đau bụng dưới sườn phải, buồn nôn.",
               "vomiting_present": "Chưa, tôi chỉ buồn nôn chứ chưa nôn.",
               "oral_intake_tolerance": "Tôi vẫn ăn được cháo như mọi khi.",
               "fever_present": "Có, sáng nay đo được 38,4 độ.",
               "temperature": "Nhiệt kế điện tử đo ở nách được 38,4 độ.",
               "infection_source_symptom_group": "Ngoài sốt thì chủ yếu là đau dưới sườn phải với buồn nôn.",
               "symptom_duration_bucket": "Từ nửa đêm qua tới giờ."},
      unknown={"heart_rate": "Tôi tự bắt mạch ở cổ tay mà đếm không được.",
               "systolic_bp": "Nhà không có máy đo huyết áp."},
      tags=("missing_vitals",),
      test="Sốt 38,4 đo được kèm đau 6/10 đã khớp tiêu chí ESI 3: thiếu mạch và huyết áp không được làm agent chuyển thành "
           "'không đủ thông tin', và agent không được tự nâng mức khi chưa có số đo nào ở vùng nguy hiểm."),
    S("x89", "office_sudden_occipital_headache_cannot_score", "Đồng nghiệp đột ngột ôm gáy kêu đau đầu, nôn, không chấm được điểm đau",
      P(41, "Female", "OTHER"),
      "Chị đồng nghiệp ngồi cạnh tôi 41 tuổi, chừng hai mươi phút trước đang gõ máy tính thì tự nhiên kêu lên một "
      "tiếng rồi ôm gáy, nói đau đầu quá, ngay sau đó nôn một lần ra thùng rác. Chị vẫn tỉnh, trả lời được, tay chân "
      "cử động bình thường, nói năng rõ ràng. Tôi hỏi đau mấy điểm thì chị chỉ nhắm mắt lắc đầu, không nói được. Văn "
      "phòng không có máy đo huyết áp.",
      {"headache_present": "YES", "headache_location": "OCCIPITAL", "symptom_onset": "SUDDEN", "pain_present": "YES",
       "vomiting_present": "YES", "vomiting_frequency": "ONCE", "gastrointestinal_symptom_present": "YES",
       "altered_mental_status_present": "NO", "focal_neurologic_symptoms": "NONE",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      INCOMPLETE, concepts=("headache", "vomiting"), screen=QUIET,
      answers={"headache_present": "Có, chị ấy kêu đau đầu quá.",
               "headache_location": "Chị ấy ôm phía sau gáy.",
               "symptom_onset": "Đột ngột, đang gõ máy tính thì tự nhiên kêu lên rồi ôm gáy.",
               "pain_present": "Có, chị ấy kêu đau đầu.",
               "vomiting_present": "Có, chị ấy nôn một lần ra thùng rác.",
               "vomiting_frequency": "Nôn một lần.",
               "gastrointestinal_symptom_present": "Có, chị ấy nôn một lần.",
               "altered_mental_status_present": "Không, chị ấy vẫn tỉnh, trả lời được.",
               "focal_neurologic_symptoms": "Không, tay chân chị ấy cử động bình thường, nói năng rõ ràng.",
               "symptom_duration_bucket": "Mới chừng hai mươi phút trước."},
      unknown={"pain_severity": "Chị ấy chỉ nhắm mắt lắc đầu, không nói được mấy điểm.",
               "systolic_bp": "Văn phòng không có máy đo huyết áp."},
      review_concern="Đau đầu khởi phát đột ngột vùng gáy kèm nôn ngay sau đó: theo AHRQ Decision Point B đây là tình huống "
                     "nguy cơ cao (cần loại trừ xuất huyết dưới nhện), nên xếp ESI 2 dù chưa có điểm đau; corpus chỉ xếp được "
                     "khi điểm đau từ 8 hoặc có dấu thần kinh khu trú.",
      tags=("collateral_history", "null_unknown", "workplace_setting", "pain_unscored"),
      test="Người bệnh không chấm được điểm đau, không có huyết áp: đau đầu đột ngột kèm nôn không được hiểu là đau vừa để "
           "chờ; agent không được đòi một con số mới kết luận mà phải chuyển nhân viên y tế ngay."),
    S("x90", "chemo_day10_fever_unmeasured_pair", "Đang hoá trị ngày thứ mười ớn lạnh, không có nhiệt kế, không biết có sốt",
      P(57, "Male", "SPOUSE", chronic=("Ung thư đại tràng đang hoá trị",), allergies=("Dị ứng penicilin",),
        meds=("Ondansetron 8 mg khi buồn nôn",)),
      "Chồng tôi 57 tuổi đang truyền hoá chất điều trị ung thư đại tràng, đợt này truyền xong được mười hôm. Từ trưa "
      "ông kêu ớn lạnh, nổi da gà, phải đắp chăn, người mệt, chỉ ăn được nửa bát cơm. Tôi sờ trán ông lúc thấy ấm lúc "
      "không. Nhiệt kế để quên ở phòng trọ gần viện, nhà dưới quê không có cái nào, nên tôi không biết ông có sốt không, "
      "tôi cũng không biết bắt mạch.",
      {"chemotherapy_history_present": "YES", "immunocompromised_state_present": "YES", "chills_present": "YES",
       "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS", "oral_intake_tolerance": "REDUCED",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("chemotherapy", "chills"), screen=QUIET,
      answers={"chemotherapy_history_present": "Có, ông đang truyền hoá chất, đợt này truyền xong được mười hôm.",
               "immunocompromised_state_present": "Có, bác sĩ dặn đang truyền hoá chất thì sức đề kháng yếu.",
               "chills_present": "Có, ông kêu ớn lạnh, nổi da gà, phải đắp chăn.",
               "associated_systemic_symptoms": "Ông ớn lạnh, người mệt.",
               "oral_intake_tolerance": "Ông chỉ ăn được nửa bát cơm.",
               "symptom_duration_bucket": "Từ trưa tới giờ."},
      unknown={"fever_present": "Không có nhiệt kế nên tôi không biết ông có sốt hay không.",
               "temperature": "Nhiệt kế để quên ở phòng trọ gần viện, nhà dưới quê không có cái nào.",
               "heart_rate": "Tôi không biết bắt mạch."},
      review_concern="Người đang hoá trị ngày thứ mười (thời điểm bạch cầu thường xuống thấp nhất) có ớn lạnh, mệt: AHRQ coi "
                     "người suy giảm miễn dịch nghi sốt là tình huống nguy cơ cao, nên xếp ESI 2 và đo nhiệt độ ngay khi tới; "
                     "corpus chỉ xếp được khi biết có sốt.",
      tags=("immunocompromised", "caregiver", "comorbidity", "missing_vitals", "minimal_pair", "null_unknown"),
      test="Cặp tối thiểu với x91 (người hoá trị nóng hầm hập dù không có con số): ở đây không ai biết có sốt hay không; "
           "agent không được ghi 'không sốt' vì sờ trán lúc không thấy ấm, phải chuyển nhân viên y tế ngay."),
    S("x91", "chemo_day10_fever_unmeasured_pair", "Em gái hoá trị ngày thứ chín nóng hầm hập, rét run, nhà trọ không có nhiệt kế",
      P(46, "Female", "SIBLING", chronic=("U lympho đang hoá trị",)),
      "Em gái tui 46 tuổi đang hoá trị u lympho, nay là ngày thứ chín sau đợt truyền. Từ đầu "
      "giờ chiều tới giờ người nó nóng hầm hập, rét run cầm cập phải trùm mền, nằm suốt không dậy nổi. Nó hông ho, "
      "hông tiểu buốt, hông tiêu chảy. Hai chị em ở nhà trọ gần viện, hông có nhiệt kế, tui cũng hông biết bắt mạch.",
      {"chemotherapy_history_present": "YES", "immunocompromised_state_present": "YES", "fever_present": "YES",
       "chills_present": "YES", "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS", "functional_status": "MARKEDLY_REDUCED",
       "infection_source_symptom_group": "NONE_CLEAR", "cough_present": "NO", "diarrhea_present": "NO",
       "urinary_symptom_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("chemotherapy", "fever", "chills"), screen=QUIET,
      answers={"chemotherapy_history_present": "Có, nó đang hoá trị u lympho, nay là ngày thứ chín sau đợt truyền.",
               "immunocompromised_state_present": "Có, bác sĩ dặn đang hoá trị thì sức đề kháng yếu lắm.",
               "fever_present": "Có, từ đầu giờ chiều người nó nóng hầm hập.",
               "chills_present": "Có, nó rét run cầm cập phải trùm mền.",
               "associated_systemic_symptoms": "Nó nóng hầm hập, rét run, mệt nằm suốt.",
               "functional_status": "Nó nằm suốt, hông dậy nổi.",
               "infection_source_symptom_group": "Ngoài nóng với rét run thì nó hông ho, hông tiểu buốt, hông tiêu chảy.",
               "cough_present": "Hông, nó hông ho.",
               "diarrhea_present": "Hông, nó hông tiêu chảy.",
               "urinary_symptom_present": "Hông, nó hông tiểu buốt.",
               "symptom_duration_bucket": "Từ đầu giờ chiều tới giờ."},
      unknown={"temperature": "Nhà trọ hông có nhiệt kế nên tui hông đo được.",
               "heart_rate": "Tui hông biết bắt mạch."},
      tags=("immunocompromised", "caregiver", "comorbidity", "missing_vitals", "minimal_pair", "decisive_despite_missing",
            "dialect"),
      test="Cặp tối thiểu với x90: ở đây người bệnh nóng hầm hập, rét run dù không có con số nào; agent không được đòi nhiệt "
           "độ hay mạch mới kết luận, người đang hoá trị có sốt (dù chỉ sờ thấy nóng) đã đủ ESI 2."),
    S("x92", "post_hemorrhoidectomy_cannot_void_pain_unscored", "Chiều vừa mổ cắt trĩ về, buồn tiểu căng mà không ra giọt nào, không chấm được điểm đau",
      P(44, "Male", chronic=("Vừa mổ cắt trĩ sáng nay",), meds=("Paracetamol 500 mg khi đau",)),
      "Tôi 44 tuổi, sáng nay vừa mổ cắt trĩ, gây tê tủy sống, chiều được về nhà. Từ lúc về tới giờ tôi buồn tiểu, căng "
      "tức ngay trên xương mu mà rặn mãi không ra được giọt nào. Lần cuối tiểu được là lúc nào thì tôi chịu, không nhớ. Đau "
      "ở vết mổ với tức bụng dưới lẫn vào nhau nên tôi không chấm được mấy điểm. Nhà không có máy đo huyết áp.",
      {"urinary_symptom_present": "YES", "voiding_ability": "UNABLE_DESPITE_URGE", "urine_output_status": "NONE",
       "urination_status": "VERY_LITTLE_OR_NONE", "genitourinary_pain_present": "YES",
       "genitourinary_pain_location": "SUPRAPUBIC", "pain_present": "YES", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("urinary_retention", "recent_surgery"), screen=QUIET,
      answers={"urinary_symptom_present": "Có, tôi buồn tiểu căng mà không tiểu ra được.",
               "voiding_ability": "Buồn tiểu căng tức mà rặn mãi không ra được giọt nào.",
               "urine_output_status": "Từ lúc về nhà tới giờ không ra được giọt nước tiểu nào.",
               "urination_status": "Từ lúc về tới giờ tôi chưa tiểu được lần nào.",
               "genitourinary_pain_present": "Có, tức căng ở bụng dưới.",
               "genitourinary_pain_location": "Tức ở bụng dưới, ngay trên xương mu.",
               "pain_present": "Có, đau ở vết mổ với tức bụng dưới.",
               "symptom_duration_bucket": "Từ chiều lúc được về nhà tới giờ."},
      unknown={"pain_severity": "Đau vết mổ với tức bụng dưới lẫn vào nhau, tôi không chấm được mấy điểm.",
               "systolic_bp": "Nhà không có máy đo huyết áp."},
      tags=("missing_vitals", "decisive_despite_missing", "post_procedure", "pain_unscored"),
      test="Không chấm được điểm đau vì đau vết mổ lẫn với tức bàng quang, không có huyết áp, không nhớ lần cuối tiểu được: "
           "buồn tiểu mà không ra giọt nào đã đủ ESI 2; agent không được chờ điểm đau hay coi là chuyện thường sau gây tê "
           "để hẹn tới sáng."),
    S("x93", "smartwatch_low_heart_rate_alert_unreliable", "Đồng hồ thông minh báo nhịp tim thấp lúc 38 lúc 70, mới dùng thuốc chẹn beta, choáng nhẹ",
      P(56, "Male", chronic=("Tăng huyết áp",), meds=("Bisoprolol 5 mg mỗi sáng",)),
      "Tôi 56 tuổi, bác sĩ mới cho tôi uống thuốc huyết áp loại chẹn beta được mười ngày. Sáng nay đi bộ tập thể dục "
      "thì đồng hồ thông minh rung báo nhịp tim thấp, tôi nhìn thì lúc nó hiện 38, lúc lại 70, chẳng biết số nào đúng. "
      "Từ lúc đó tới giờ tôi thấy hơi choáng, người mệt hơn mọi ngày, chưa ngất lần nào, không đau ngực, không khó thở, "
      "không thấy tim đập gì lạ. Tôi không biết tự bắt mạch, nhà cũng không có máy đo huyết áp.",
      {"dizziness_present": "YES", "dizziness_sensation": "LIGHTHEADED", "associated_systemic_symptoms": "GENERAL_WEAKNESS",
       "syncope_present": "NO", "chest_pain_present": "NO", "dyspnea_present": "NO",
       "cardiorespiratory_symptom_present": "NO", "palpitation_present": "NO",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("lightheadedness", "fatigue"),
      answers={"dizziness_present": "Có, tôi thấy hơi choáng.",
               "dizziness_sensation": "Choáng nhẹ, lâng lâng, không thấy nhà cửa quay.",
               "associated_systemic_symptoms": "Người tôi mệt hơn mọi ngày.",
               "syncope_present": "Chưa, tôi chưa ngất lần nào.",
               "chest_pain_present": "Không, tôi không đau ngực.",
               "dyspnea_present": "Không, tôi không khó thở.",
               "cardiorespiratory_symptom_present": "Không đau ngực, không khó thở, tôi cũng không thấy tim đập gì lạ.",
               "palpitation_present": "Không, tôi không thấy tim đập gì lạ.",
               "symptom_duration_bucket": "Từ lúc đi bộ sáng nay tới giờ."},
      unknown={"heart_rate": "Đồng hồ lúc hiện số này lúc hiện số khác, tôi không biết số nào đúng, tôi cũng không biết tự "
                             "bắt mạch.",
               "systolic_bp": "Nhà không có máy đo huyết áp."},
      tags=("comorbidity", "missing_vitals", "device_unreliable", "negation", "lay_device_reading"),
      test="Đồng hồ thông minh cho hai số mâu thuẫn: agent không được chọn một số làm nhịp tim (38 thành ESI 2, 70 thành yên "
           "tâm), phải coi nhịp tim là chưa biết và chuyển nhân viên y tế vì cũng chưa có huyết áp."),
    S("x94", "heavy_menses_iud_phone_camera_pulse_app", "Kinh ra nhiều thấm đẫm băng chưa tới một tiếng, choáng khi đứng, ứng dụng đo mạch điện thoại ra ba số",
      P(38, "Female"),
      "Em 38 tuổi, đặt vòng tránh thai được 5 năm. Kỳ kinh này ra nhiều bất thường, hôm nay là ngày thứ ba, cứ chưa "
      "tới một tiếng là thấm đẫm một miếng băng loại ban đêm, có cả cục máu đông. Đứng dậy là choáng, phải bám tường. "
      "Bụng không đau. Sáng nay em thử que thì một vạch. Em đo mạch bằng ứng dụng đặt ngón tay lên camera điện thoại, ba "
      "lần ra ba số khác nhau nên em không tin, nhà cũng không có máy đo huyết áp.",
      {"vaginal_bleeding_present": "YES", "vaginal_bleeding_amount": "HEAVY", "pregnancy_present": "NO",
       "pregnancy_status": "NOT_PREGNANT", "dizziness_present": "YES", "dizziness_sensation": "LIGHTHEADED",
       "pain_present": "NO", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, concepts=("vaginal_bleeding", "lightheadedness"), screen=HIT,
      answers={"vaginal_bleeding_present": "Dạ có, kỳ kinh này em ra nhiều bất thường.",
               "vaginal_bleeding_amount": "Chưa tới một tiếng là thấm đẫm một miếng băng loại ban đêm, có cả cục máu đông.",
               "pregnancy_present": "Không, sáng nay em thử que một vạch.",
               "pregnancy_status": "Em không có thai, que thử sáng nay một vạch.",
               "dizziness_present": "Dạ có, đứng dậy là em choáng.",
               "dizziness_sensation": "Đứng dậy là choáng, phải bám tường.",
               "pain_present": "Không, bụng em không đau.",
               "symptom_duration_bucket": "Hôm nay là ngày thứ ba của kỳ kinh."},
      unknown={"heart_rate": "Ứng dụng điện thoại mỗi lần ra một số khác nhau nên em không biết mạch thật là bao nhiêu.",
               "systolic_bp": "Nhà em không có máy đo huyết áp."},
      tags=("missing_vitals", "device_unreliable", "lay_device_reading", "negation"),
      test="Ứng dụng đo mạch bằng camera điện thoại cho ba số khác nhau, không có máy đo huyết áp: agent không được lấy một "
           "số trong đó làm mạch; ra máu kinh rất nhiều kèm choáng khi đứng mà chưa có sinh hiệu thì phải chuyển nhân viên "
           "y tế, không được khuyên chờ hết kỳ kinh."),
    S("x95", "sudden_painless_curtain_vision_loss_cuff_broken", "Cụ bà đang nhặt rau thì nửa dưới mắt phải tối đi như có tấm màn, máy đo huyết áp hỏng",
      P(72, "Female", chronic=("Tăng huyết áp", "Đái tháo đường type 2"), allergies=("Dị ứng sulfamid",),
        meds=("Losartan 50 mg mỗi sáng", "Metformin 500 mg sáng và tối")),
      "Tôi 72 tuổi, bị huyết áp với tiểu đường. Chừng bốn mươi phút trước đang ngồi nhặt rau thì tự nhiên nửa dưới mắt "
      "phải tối đi như có tấm màn kéo lên, nhắm mắt trái lại thì mắt phải chỉ còn thấy lờ mờ phía trên. Mắt không đau, "
      "không đỏ, không va chạm gì, đầu không đau, tay chân vẫn cử động bình thường, nói năng bình thường. Máy đo huyết "
      "áp nhà tôi hỏng từ tuần trước chưa mua cái mới nên không biết huyết áp bao nhiêu.",
      {"eye_problem_present": "YES", "eye_laterality": "RIGHT", "eye_injury_present": "NO",
       "vision_impairment_present": "YES", "vision_impairment_extent": "PARTIAL_LOSS",
       "visual_disturbance_present": "YES", "visual_disturbance_pattern": "FIELD_DEFECT",
       "focal_neurologic_symptoms": "VISION_CHANGE", "symptom_onset": "SUDDEN", "pain_present": "NO",
       "headache_present": "NO", "contact_lens_status": "NO_USE", "eye_movement_difficulty": "ABSENT",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("vision_loss", "visual_field_defect"), screen=QUIET,
      answers={"eye_problem_present": "Có, nửa dưới mắt phải tôi tự nhiên tối đi.",
               "eye_laterality": "Mắt phải.",
               "eye_injury_present": "Không, mắt tôi không va chạm gì.",
               "vision_impairment_present": "Có, mắt phải chỉ còn thấy lờ mờ phía trên.",
               "vision_impairment_extent": "Nửa dưới mắt phải tối hẳn, phía trên còn thấy lờ mờ.",
               "visual_disturbance_present": "Có, như có tấm màn kéo lên che nửa dưới mắt phải.",
               "visual_disturbance_pattern": "Mất hẳn nửa dưới tầm nhìn của mắt phải, như bị tấm màn che.",
               "focal_neurologic_symptoms": "Chỉ mắt phải nhìn không thấy nửa dưới, tay chân vẫn cử động bình thường, nói năng "
                                            "bình thường.",
               "symptom_onset": "Đột ngột, đang ngồi nhặt rau thì tự nhiên tối đi.",
               "pain_present": "Không, mắt không đau, đầu cũng không đau.",
               "headache_present": "Không, đầu tôi không đau.",
               "contact_lens_status": "Tôi không đeo kính áp tròng.",
               "eye_movement_difficulty": "Liếc mắt các phía vẫn được bình thường.",
               "symptom_duration_bucket": "Chừng bốn mươi phút trước."},
      unknown={"systolic_bp": "Máy đo huyết áp nhà tôi hỏng từ tuần trước, chưa mua cái mới.",
               "diastolic_bp": "Tôi không đo được nên không biết."},
      tags=("older_adult", "comorbidity", "missing_vitals", "decisive_despite_missing", "negation"),
      test="Máy đo huyết áp hỏng: mất một phần thị trường mắt phải khởi phát đột ngột, không đau đã đủ quyết định ESI 2 "
           "(corpus không có tiêu chí riêng cho mất thị lực đột ngột không đau, tiêu chí khớp mang tên đau đầu kèm thay đổi "
           "thị lực); agent không được coi 'mắt không đau, không đỏ' là nhẹ, không được hẹn khám mắt sau hay chờ số huyết áp."),
    S("x96", "sudden_belly_to_back_pain_manual_cuff_pulse_faint", "Cụ ông hút thuốc lào đột ngột đau bụng xuyên lưng 9/10, máy bơm tay đo 68/40, mạch yếu không đếm được",
      P(74, "Male", "PARENT", chronic=("Tăng huyết áp",), meds=("Amlodipin 5 mg mỗi sáng",)),
      "Bố em 74 tuổi, hút thuốc lào mấy chục năm, bị cao huyết áp. Chừng nửa tiếng trước bố đang ngồi xem ti vi thì "
      "đột ngột kêu đau dữ dội ở quanh rốn xuyên ra sau lưng, bố bảo đau 9 trên 10, rồi vã mồ hôi, mặt tái, suýt gục "
      "nhưng chưa ngất. Em đang học điều dưỡng nên lấy máy đo huyết áp bơm tay với ống nghe ra đo được 68 trên 40, còn "
      "mạch cổ tay thì yếu quá em bắt không ra để đếm. Nhà không có máy kẹp ngón đo oxy.",
      {"abdominal_pain_present": "YES", "abdominal_pain_location": "AROUND_UMBILICUS", "abdominal_pain_radiation": "BACK",
       "pain_present": "YES", "pain_severity": 9, "gastrointestinal_symptom_present": "YES", "symptom_onset": "SUDDEN",
       "dizziness_present": "YES", "dizziness_sensation": "LIGHTHEADED", "syncope_present": "NO", "systolic_bp": 68,
       "diastolic_bp": 40, "symptom_duration_bucket": "UNDER_1_HOUR"},
      1, concepts=("abdominal_pain", "back_pain"),
      answers={"abdominal_pain_present": "Có, bố kêu đau dữ dội ở quanh rốn.",
               "abdominal_pain_location": "Quanh rốn.",
               "abdominal_pain_radiation": "Đau xuyên ra sau lưng.",
               "pain_present": "Có, bố đau dữ dội ở bụng xuyên ra sau lưng.",
               "pain_severity": "Bố bảo đau 9 trên 10.",
               "gastrointestinal_symptom_present": "Có, bố đau bụng dữ dội.",
               "symptom_onset": "Đột ngột, đang ngồi xem ti vi thì kêu đau.",
               "dizziness_present": "Có, bố vã mồ hôi, mặt tái, suýt gục.",
               "dizziness_sensation": "Bố choáng, suýt gục xuống.",
               "syncope_present": "Chưa, bố suýt gục nhưng chưa ngất.",
               "systolic_bp": "Em đo bằng máy bơm tay với ống nghe được 68 trên 40.",
               "diastolic_bp": "Số dưới là 40.",
               "symptom_duration_bucket": "Chừng nửa tiếng trước."},
      unknown={"heart_rate": "Mạch cổ tay của bố yếu quá, em bắt không ra để đếm.",
               "spo2": "Nhà không có máy kẹp ngón đo oxy.",
               "abdominal_pain_character": "Bố chỉ kêu đau dữ dội, không tả được kiểu đau."},
      tags=("older_adult", "caregiver", "comorbidity", "missing_vitals", "decisive_despite_missing"),
      test="Mạch quá yếu không đếm được, không có SpO2: huyết áp 68/40 đo bằng máy bơm tay kèm đau bụng xuyên lưng đột ngột "
           "9/10 đã đủ ESI 1; agent không được chờ số mạch, cũng không được coi mạch 'bắt không ra' là chưa có dữ kiện nguy "
           "hiểm."),
    S("x97", "dementia_mil_hot_knee_mercury_thermometer_unread", "Mẹ chồng sa sút trí tuệ sáng ra gối phải sưng đỏ nóng, không chấm được đau, con dâu không đọc được nhiệt kế thủy ngân",
      P(86, "Female", "OTHER", chronic=("Sa sút trí tuệ", "Bệnh gút"),
        meds=("Allopurinol 100 mg mỗi sáng", "Donepezil 5 mg mỗi tối")),
      "Mẹ chồng em 86 tuổi bị sa sút trí tuệ, ở với vợ chồng em. Tối qua em thay đồ cho mẹ chưa thấy gì, sáng nay gối "
      "phải của mẹ sưng to, đỏ, sờ vào nóng hơn hẳn bên kia, em đụng nhẹ là mẹ nhăn mặt kêu oai oái, không chịu đứng "
      "dậy đi như mọi ngày. Hỏi mẹ đau mấy điểm thì mẹ không hiểu. Nhà có cái nhiệt kế thủy ngân, em kẹp cho mẹ rồi mà "
      "không biết đọc vạch. Cả hôm qua mẹ ở nhà với em, không ngã gì.",
      {"joint_pain_present": "YES", "joint_pain_location": "KNEE", "joint_involvement_count": "ONE_JOINT",
       "joint_swelling_status": "PRESENT", "joint_redness_warmth_status": "REDNESS_AND_WARMTH",
       "limb_function_status": "UNABLE_TO_USE", "pain_present": "YES", "swelling_present": "YES",
       "swelling_location": "OTHER", "lower_extremity_problem_present": "YES", "lower_extremity_injury_location": "KNEE",
       "weight_bearing_ability": "UNABLE", "visible_deformity_present": "NO", "trauma_present": "NO",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("knee_pain", "joint_swelling", "joint_redness"), screen=QUIET,
      answers={"joint_pain_present": "Có, em đụng nhẹ vào gối phải là mẹ nhăn mặt kêu oai oái.",
               "joint_pain_location": "Gối phải.",
               "joint_involvement_count": "Chỉ có gối phải thôi, các khớp khác em không thấy gì.",
               "joint_swelling_status": "Có, gối phải sưng to.",
               "joint_redness_warmth_status": "Gối phải đỏ, sờ vào nóng hơn hẳn bên kia.",
               "limb_function_status": "Mẹ không chịu đứng dậy đi như mọi ngày.",
               "pain_present": "Có, em đụng vào gối phải là mẹ nhăn mặt kêu.",
               "swelling_present": "Có, gối phải của mẹ sưng to.",
               "swelling_location": "Sưng ở gối phải.",
               "lower_extremity_problem_present": "Có, gối phải sưng đỏ nóng, mẹ không chịu đứng.",
               "lower_extremity_injury_location": "Ở gối phải.",
               "weight_bearing_ability": "Mẹ không chịu đứng lên chân đó.",
               "visible_deformity_present": "Không, gối chỉ sưng to chứ không cong vẹo gì.",
               "trauma_present": "Không, cả hôm qua mẹ ở nhà với em, không ngã gì.",
               "symptom_duration_bucket": "Tối qua chưa thấy gì, sáng nay mới thấy sưng."},
      unknown={"temperature": "Em kẹp nhiệt kế thủy ngân cho mẹ rồi mà không biết đọc vạch.",
               "fever_present": "Em không đọc được nhiệt kế nên không biết mẹ có sốt không.",
               "associated_systemic_symptoms": "Mẹ không nói được có mệt hay ớn lạnh không.",
               "pain_severity": "Mẹ không hiểu khi em hỏi đau mấy điểm.",
               "symptom_onset": "Tối qua còn bình thường, sáng ra đã sưng, em không biết bắt đầu đột ngột hay từ từ."},
      tags=("older_adult", "caregiver", "baseline_cognitive_impairment", "comorbidity", "missing_vitals", "unknown_onset",
            "null_unknown"),
      test="Người bệnh sa sút trí tuệ không chấm được đau, người kể không đọc được nhiệt kế, không biết khởi phát đột ngột "
           "hay từ từ: các tiêu chí khớp sưng nóng đỏ đều cần một trong ba dữ kiện đó; agent không được tự coi là cơn gút "
           "quen hay là không sốt mà phải chuyển nhân viên y tế."),
    S("x98", "elder_brought_from_village_last_stool_unknown", "Con trai đón mẹ từ quê lên, bụng căng, rặn không ra, không ai biết lần cuối đi ngoài",
      P(81, "Female", "PARENT", chronic=("Tăng huyết áp", "Hay quên do tuổi già"), meds=("Amlodipin 5 mg mỗi sáng",)),
      "Mẹ tôi 81 tuổi ở quê một mình, hôm kia tôi mới đón lên ở cùng. Sáng nay mẹ ngồi trong nhà vệ sinh rất lâu, ra "
      "bảo rặn mãi không đi được, bụng căng tức khắp bụng, không nôn, vẫn ăn được bát cơm như mọi khi. Hỏi lần cuối đi "
      "ngoài được là hôm nào thì mẹ không nhớ, hai hôm ở đây mẹ tự đi vệ sinh nên tôi cũng không để ý. Hỏi còn xì hơi "
      "được không thì mẹ bảo không để ý, đau nhiều hay ít mẹ cũng không nói được mấy điểm.",
      {"constipation_or_defecation_problem_present": "YES", "defecation_effort": "UNABLE_TO_DEFECATE",
       "evacuation_completeness": "NO_STOOL_PASSED", "abdominal_pain_present": "YES",
       "abdominal_pain_character": "PRESSURE", "abdominal_pain_location": "GENERALIZED", "pain_present": "YES",
       "gastrointestinal_symptom_present": "YES", "vomiting_present": "NO", "oral_intake_tolerance": "NORMAL"},
      INCOMPLETE, concepts=("constipation", "inability_to_pass_stool", "abdominal_distension"), screen=QUIET,
      answers={"constipation_or_defecation_problem_present": "Có, mẹ rặn mãi không đi ngoài được.",
               "defecation_effort": "Mẹ ngồi rất lâu, rặn mãi mà không đi được.",
               "evacuation_completeness": "Không ra được tí nào.",
               "abdominal_pain_present": "Có, mẹ kêu bụng căng tức.",
               "abdominal_pain_character": "Căng tức.",
               "abdominal_pain_location": "Căng tức khắp bụng.",
               "pain_present": "Có, mẹ kêu căng tức khắp bụng.",
               "gastrointestinal_symptom_present": "Có, mẹ không đi ngoài được, bụng căng tức.",
               "vomiting_present": "Không, mẹ không nôn.",
               "oral_intake_tolerance": "Mẹ vẫn ăn được bát cơm như mọi khi."},
      unknown={"days_since_last_bowel_movement": "Mẹ không nhớ lần cuối đi được là hôm nào, mấy hôm ở đây tôi cũng không để ý.",
               "gas_passage_status": "Mẹ bảo không để ý có xì hơi hay không.",
               "pain_severity": "Mẹ không nói được đau mấy điểm.",
               "symptom_duration_bucket": "Mẹ không nhớ bị như vậy từ hôm nào.",
               "stool_consistency": "Mẹ chưa đi ra được nên tôi không biết phân thế nào."},
      tags=("older_adult", "caregiver", "null_unknown", "unknown_onset", "recent_caregiver"),
      test="Không ai biết lần cuối đi ngoài và người bệnh không để ý còn xì hơi được không: các tiêu chí táo bón cần số ngày "
           "hoặc tình trạng trung tiện; agent không được tự đoán số ngày hay coi 'vẫn ăn được' là yên tâm mà phải chuyển "
           "nhân viên y tế."),
    S("x99", "infant_episodic_screaming_legs_drawn_mother_home_late", "Bé 9 tháng khóc thét từng cơn co chân lên bụng, nôn, lả giữa cơn, mẹ đi làm về mới biết",
      P(0, "Male", "CHILD", months=9),
      "Em đi làm về thì bà bảo bé trai 9 tháng nhà em từ sau bữa trưa cứ từng cơn khóc thét, co hai chân lên bụng, mỗi "
      "cơn một lúc rồi thôi, đã nôn hai lần, bú ít hơn hẳn. Bà không để ý các cơn cách nhau bao lâu. Em về thấy giữa các "
      "cơn bé nằm lả, mềm người, ít cựa quậy. Bé chưa nói được nên không biết đau mức nào, bé quấy quá em cũng không đếm "
      "được tim đập.",
      {"symptom_trend": "INTERMITTENT", "abdominal_pain_present": "YES", "pain_present": "YES", "vomiting_present": "YES",
       "vomiting_frequency": "FEW_TIMES", "gastrointestinal_symptom_present": "YES",
       "vomiting_or_feeding_problem_present": "YES", "feeding_intake_level": "MARKEDLY_REDUCED",
       "activity_level": "VERY_INACTIVE", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("inconsolable_crying", "vomiting"), screen=QUIET,
      answers={"symptom_trend": "Từng cơn ạ, mỗi cơn khóc thét một lúc rồi thôi, lát sau lại khóc.",
               "abdominal_pain_present": "Bé co hai chân lên bụng khóc thét nên em nghĩ là đau bụng ạ.",
               "pain_present": "Có ạ, bé khóc thét từng cơn, co chân lên bụng.",
               "vomiting_present": "Có ạ, bé nôn hai lần.",
               "vomiting_frequency": "Nôn hai lần ạ.",
               "gastrointestinal_symptom_present": "Có ạ, bé nôn hai lần, co chân lên bụng khóc.",
               "vomiting_or_feeding_problem_present": "Có ạ, bé nôn hai lần, bú ít hơn hẳn.",
               "feeding_intake_level": "Bé bú ít hơn hẳn mọi ngày ạ.",
               "activity_level": "Giữa các cơn bé nằm lả, mềm người, ít cựa quậy ạ.",
               "symptom_duration_bucket": "Bà bảo từ sau bữa trưa tới giờ ạ."},
      unknown={"pain_severity": "Bé chưa nói được nên em không biết bé đau mức nào ạ.",
               "heart_rate": "Bé quấy quá em không đếm được tim đập ạ.",
               "fluid_retention": "Bà không để ý bé bú vào giữ được bao nhiêu, em về thì chưa cho bú lại ạ."},
      review_concern="Trẻ 9 tháng khóc thét từng cơn co chân lên bụng, nôn, lả mềm người giữa các cơn: cần loại trừ lồng ruột "
                     "(xử trí muộn có thể hoại tử ruột); theo AHRQ Decision Point B đây là tình huống nguy cơ cao, nên xếp ESI 2; "
                     "corpus cần điểm đau hoặc sinh hiệu, mà trẻ nhũ nhi không chấm đau được và không ai đếm được mạch.",
      tags=("pediatric", "caregiver", "collateral_history", "null_unknown", "hidden_red_flag"),
      test="Trẻ nhũ nhi không chấm được đau, không ai đếm được mạch, người kể chỉ về sau mới thấy: khóc từng cơn rồi lả giữa "
           "các cơn không được coi là quấy khóc thường hay đau bụng nhẹ; agent phải chuyển nhân viên y tế ngay."),
    S("x100", "site_foreman_new_worker_fever_40_onset_unknown", "Cai thợ kể hộ thợ hồ mới lên công trình sốt 40,3, rét run, không nhớ sốt từ bao giờ",
      P(35, "Male", "OTHER"),
      "Tôi là cai thợ ở một công trình. Sáng nay có anh thợ hồ 35 tuổi dưới quê mới lên làm, tới trưa thì kêu mệt, "
      "nằm co ro trong lán, rét run, không dậy làm được. Tôi lấy nhiệt kế điện tử trong hộp sơ cứu kẹp nách cho anh ấy "
      "được 40,3 độ. Hỏi sốt từ bao giờ thì anh ấy bảo không nhớ là mới hôm nay hay từ mấy hôm trước ở quê. Anh vẫn "
      "tỉnh, trả lời được, không ho, không tiểu buốt, không đi ngoài lỏng. Ở công trình không có máy đo huyết áp, tôi "
      "cũng không biết bắt mạch.",
      {"fever_present": "YES", "temperature": 40.3, "chills_present": "YES",
       "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS", "functional_status": "MARKEDLY_REDUCED",
       "altered_mental_status_present": "NO", "infection_source_symptom_group": "NONE_CLEAR", "cough_present": "NO",
       "diarrhea_present": "NO", "urinary_symptom_present": "NO"},
      2, concepts=("fever", "chills"),
      answers={"fever_present": "Có, kẹp nách được 40,3 độ.",
               "temperature": "Nhiệt kế điện tử trong hộp sơ cứu kẹp nách được 40,3 độ.",
               "chills_present": "Có, anh ấy rét run.",
               "associated_systemic_symptoms": "Anh ấy sốt, rét run, kêu mệt.",
               "functional_status": "Anh ấy nằm co ro trong lán, không dậy làm được.",
               "altered_mental_status_present": "Không, anh ấy vẫn tỉnh, trả lời được.",
               "infection_source_symptom_group": "Ngoài sốt thì không ho, không tiểu buốt, không đi ngoài lỏng.",
               "cough_present": "Không, anh ấy không ho.",
               "diarrhea_present": "Không, anh ấy không đi ngoài lỏng.",
               "urinary_symptom_present": "Không, anh ấy không tiểu buốt."},
      unknown={"symptom_duration_bucket": "Anh ấy không nhớ sốt từ hôm nay hay từ mấy hôm trước, tôi thì sáng nay mới gặp.",
               "heart_rate": "Tôi không biết bắt mạch.",
               "systolic_bp": "Ở công trình không có máy đo huyết áp."},
      tags=("occupational", "collateral_history", "missing_vitals", "unknown_onset", "decisive_despite_missing"),
      test="Người kể mới gặp người bệnh sáng nay, không biết sốt từ bao giờ, không có mạch và huyết áp: thân nhiệt 40,3 đo "
           "được kèm mệt nằm không dậy nổi đã đủ ESI 2; agent không được đòi biết sốt mấy ngày hay chờ sinh hiệu."),
]
