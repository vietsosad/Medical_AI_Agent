"""Nhóm RED_FLAG, đợt 3 (tệp a): dấu hiệu nguy hiểm, mức ưu tiên cao.

Đợt 3 tệp a nhắm vào các tiêu chí ESI 2 mà hai đợt trước chưa ca nào chạm tới: chấn thương cả lưng, thắt lưng
và cổ kèm dấu thần kinh ở chi (tê, châm chích, yếu, liệt, nhiều dấu cùng lúc); chấn thương đầu kèm từng loại dấu
thần kinh (tê hoặc yếu nửa người, liệt, méo mặt, rối loạn lời nói, nhìn mờ, quên đoạn quanh lúc chấn thương); dấu
hiệu nghi vỡ nền sọ (chảy máu tai, bầm sau tai, nhiều dấu hiệu cùng lúc); vật nhọn xuyên vào đầu; chóng mặt quay
hoặc mất thăng bằng kèm dấu thần kinh khu trú; ý định gây thương tích cho người khác.

Quy ước riêng của tệp:
- Chấn thương cột sống (lưng, cổ) chỉ ghi ``limb_neurologic_symptoms`` như r64 của đợt 2. Chấn thương đầu có tê
  hoặc yếu nửa người thì ghi cả ``limb_neurologic_symptoms`` lẫn ``focal_neurologic_symptoms``, vì người kể sẽ trả
  lời "có" cho cả hai câu hỏi; khi đó tiêu chí theo chi thắng theo thứ tự chữ cái và đúng bệnh cảnh.
- Không ca nào có sinh hiệu: mọi ca được quyết định bởi điều người bệnh hoặc người kể tự thấy.
- Bỏ tiêu chí ``esi_2_penetrating_with_neurovascular_symptoms``: ``distal_limb_symptoms`` chỉ được hỏi khi có vấn
  đề ở chân (``lower_extremity_problem_present``), còn cơ chế lại là ``upper_extremity_injury_mechanism`` (tay), nên
  tiêu chí chỉ khớp khi ghép vết đâm ở tay với triệu chứng ở chân, không phải một bệnh cảnh thật. Thay bằng r104:
  tê yếu lan dần từ chân lên tay sau một đợt tiêu chảy, corpus không có tiêu chí nên kỳ vọng RETURN_INCOMPLETE và
  ca vào hàng chờ chuyên gia.
"""

from __future__ import annotations

from eval.generated_mock_v2.spec import INCOMPLETE, P, RED, SCREEN_HIT as HIT, SCREEN_QUIET as QUIET, Spec


def S(key: str, family: str, title: str, profile: dict, opening: str, facts: dict, intended, **kw) -> Spec:
    return Spec(case_id=key, family=family, group=RED, title=title, profile=profile,
                opening=opening, facts=facts, intended=intended, **kw)


SPECS = [
    # ------------------------------------------------------------------ ESI 2: chấn thương lưng, ý định bạo lực
    S("r82", "buffalo_throw_whole_back_legs_numb_weak", "Bị trâu húc hất ngã ngửa, đau dọc lưng, hai chân tê và yếu",
      P(52, "Male", "SPOUSE"),
      "Chồng tui 52 tuổi, cách đây chừng hai tiếng đi cày bị con trâu húc hất văng lên rồi rơi ngửa xuống bờ ruộng. "
      "Chừ anh nằm đó kêu đau dọc cả sống lưng, từ giữa hai bả vai xuống tới thắt lưng, hai chân tê rần mà yếu xìu, "
      "nhấc không lên khỏi chiếu. Anh vẫn tỉnh, nói chuyện được. Tui phải làm răng đây?",
      {"trauma_present": "YES", "trauma_mechanism": "OTHER", "injury_region": "ENTIRE_BACK",
       "limb_neurologic_symptoms": "MULTIPLE", "back_or_spinal_problem_present": "YES", "pain_present": "YES",
       "post_trauma_awareness_change": "NONE", "altered_mental_status_present": "NO",
       "functional_status": "UNABLE_TO_AMBULATE", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("back_injury", "lower_extremity_numbness", "lower_extremity_weakness"), screen=QUIET,
      answers={"trauma_present": "Có, anh bị trâu húc hất văng lên rồi rơi ngửa xuống bờ ruộng.",
               "trauma_mechanism": "Bị con trâu húc hất văng lên, rơi ngửa xuống bờ ruộng.",
               "injury_region": "Đau dọc cả sống lưng, từ giữa hai bả vai xuống tới thắt lưng.",
               "limb_neurologic_symptoms": "Hai chân tê rần mà yếu xìu, nhấc không lên khỏi chiếu.",
               "back_or_spinal_problem_present": "Có, anh đau dọc cả sống lưng từ lúc té.",
               "pain_present": "Có, anh kêu đau lưng lắm.",
               "post_trauma_awareness_change": "Anh không ngất lúc mô, nhớ rõ hết.",
               "altered_mental_status_present": "Không, anh vẫn tỉnh, nói chuyện bình thường.",
               "functional_status": "Anh không tự đứng dậy được, hai chân nhấc không lên.",
               "symptom_duration_bucket": "Mới chừng hai tiếng."},
      unknown={"pain_severity": "Anh chỉ rên, tui hỏi đau mấy điểm thì anh nói không biết chấm răng."},
      tags=("caregiver", "dialect", "occupational", "null_unknown"),
      test="Bị trâu húc ngã ngửa, đau dọc cả lưng, hai chân vừa tê vừa yếu, người vợ kể giọng miền Trung: agent phải "
           "nhận ra dấu hiệu tổn thương tuỷ sau chấn thương lưng, không coi là đau lưng do ngã thường."),
    S("r83", "unpaid_wages_intent_to_injure_contractor", "Ý định tối nay đến gây thương tích cho người quỵt lương",
      P(36, "Male"),
      "Tôi 36 tuổi, làm thợ hồ. Ba tháng nay thằng cai thầu quỵt hết lương của cả tổ, vợ con tôi phải đi vay khắp nơi. "
      "Từ trưa tới giờ trong đầu tôi chỉ có một ý: tối nay tôi sẽ đến nhà nó, làm cho nó bị thương thật nặng cho bõ tức, "
      "tôi tính kỹ cả rồi. Nhưng tôi cũng sợ chính mình, sợ làm xong thì vợ con không còn ai lo. Tôi tỉnh táo, chưa uống "
      "giọt rượu nào.",
      {"other_safety_status": "CURRENT_VIOLENT_INTENT", "self_safety_status": "NO_RISK_REPORTED",
       "substance_involvement": "NONE_REPORTED", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("homicidal_ideation", "threat_of_violence"), screen=QUIET,
      answers={"other_safety_status": "Có, tôi đã định tối nay đến nhà nó làm cho nó bị thương thật nặng, ý đó cứ "
                                      "lởn vởn trong đầu từ trưa.",
               "self_safety_status": "Không, tôi không có ý làm hại bản thân, tôi còn vợ con.",
               "substance_involvement": "Không, tôi không uống rượu bia hay dùng chất gì cả.",
               "symptom_duration_bucket": "Ý định đó có từ trưa nay, còn chuyện bị quỵt lương thì ba tháng rồi."},
      tags=("mental_health", "single_decisive_symptom", "negation", "violence_risk"),
      test="Người bệnh tự nhắn, tỉnh táo, không dùng chất, nói rõ ý định tối nay gây thương tích cho người khác: agent "
           "phải xếp ưu tiên cao, giữ an toàn và chuyển người ngay, không hỏi chi tiết kế hoạch."),

    # ------------------------------------------------------------------ ESI 2: chóng mặt quay kèm dấu thần kinh
    S("r84", "market_vendor_vertigo_dysarthria_arm_numb_coin_rubbing",
      "Bà bán rau chóng mặt quay, nói đớ, tê tay phải, người trong chợ đang cạo gió",
      P(66, "Female", "OTHER", chronic=("Tăng huyết áp", "Đái tháo đường type 2")),
      "Bà bán rau sạp kế bên tui 66 tuổi, cách đây khoảng 40 phút đang ngồi lựa rau thì kêu trời đất quay mòng mòng, "
      "ói một bãi. Giờ bà nói đớ lưỡi, nghe hông rõ chữ, tay phải cầm cái rổ cũng rớt, kêu tê rần. Mấy người trong chợ "
      "đang cạo gió cho bà, nói trúng gió thôi. Bà có bệnh huyết áp với tiểu đường, còn uống thuốc gì thì tui hổng biết.",
      {"dizziness_present": "YES", "dizziness_sensation": "SPINNING", "focal_neurologic_symptoms": "MULTIPLE",
       "symptom_onset": "SUDDEN", "vomiting_present": "YES", "vomiting_frequency": "ONCE",
       "gastrointestinal_symptom_present": "YES", "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("vertigo", "slurred_speech", "limb_numbness"), screen=HIT,
      answers={"dizziness_present": "Có, bà kêu chóng mặt quá trời.",
               "dizziness_sensation": "Bà kêu trời đất quay mòng mòng.",
               "focal_neurologic_symptoms": "Bà nói đớ lưỡi, nghe hông rõ chữ, tay phải tê rần, cầm rổ cũng rớt.",
               "symptom_onset": "Đột ngột, đang ngồi lựa rau thì bị liền.",
               "vomiting_present": "Có, bà ói một bãi.",
               "vomiting_frequency": "Ói một lần.",
               "gastrointestinal_symptom_present": "Có, bà ói một bãi.",
               "symptom_duration_bucket": "Mới khoảng 40 phút."},
      tags=("caregiver", "collateral_history", "dialect", "comorbidity", "minimization", "folk_belief"),
      test="Chóng mặt quay kèm nói đớ và tê yếu tay phải ở người bán hàng, người xung quanh cho là trúng gió và đang cạo "
           "gió: agent không được chấp nhận cách giải thích dân gian, phải xếp ưu tiên cao."),
    S("r85", "truck_driver_vertigo_slurred_speech_noticed_by_phone",
      "Tài xế xe tải chóng mặt quay, vợ nghe qua điện thoại thấy nói đớ",
      P(55, "Male", chronic=("Tăng huyết áp",), meds=("Telmisartan 40 mg",)),
      "Tôi 55t, lái xe tải. Khoảng 30p trước đang chạy trên quốc lộ thì tự nhiên chóng mặt quay cuồng, phải tấp vô lề, "
      "ói 2 lần. Gọi đt cho vợ thì vợ bảo tôi nói đớ lưỡi như người say, mà tôi ko uống giọt rượu nào. Tay chân vẫn cử "
      "động bt, gõ chữ vẫn dc.",
      {"dizziness_present": "YES", "dizziness_sensation": "SPINNING",
       "focal_neurologic_symptoms": "SPEECH_OR_LANGUAGE_CHANGE", "symptom_onset": "SUDDEN", "vomiting_present": "YES",
       "vomiting_frequency": "FEW_TIMES", "gastrointestinal_symptom_present": "YES",
       "substance_involvement": "NONE_REPORTED", "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("vertigo", "slurred_speech"), screen=HIT,
      answers={"dizziness_present": "Có, chóng mặt quay cuồng.",
               "dizziness_sensation": "Quay cuồng, mọi thứ xoay vòng vòng.",
               "focal_neurologic_symptoms": "Vợ bảo tôi nói đớ lưỡi như người say. Tay chân thì bt.",
               "symptom_onset": "Tự nhiên bị, đang chạy xe thì quay cuồng luôn.",
               "vomiting_present": "Có, ói 2 lần.",
               "vomiting_frequency": "Ói 2 lần.",
               "gastrointestinal_symptom_present": "Có, ói 2 lần.",
               "substance_involvement": "Ko, tôi ko uống rượu bia, ko dùng gì cả.",
               "symptom_duration_bucket": "Mới khoảng 30p."},
      tags=("abbreviation", "occupational", "collateral_history", "negation"),
      test="Chóng mặt quay kèm nói đớ do vợ nhận ra qua điện thoại, người bệnh vẫn gõ chữ trôi chảy: agent không được "
           "dựa vào tin nhắn mạch lạc để loại trừ rối loạn lời nói."),
    S("r86", "known_vestibular_disorder_new_left_hemisensory",
      "Người hay rối loạn tiền đình, cơn chóng mặt lần này kèm tê yếu tay chân trái",
      P(34, "Female", chronic=("Rối loạn tiền đình", "Đau nửa đầu"), allergies=("Amoxicillin",),
        meds=("Betahistin khi lên cơn chóng mặt", "Viên tránh thai phối hợp hằng ngày")),
      "Em hay bị rối loạn tiền đình, mỗi lần lên cơn uống betahistin nằm nghỉ là đỡ. Trưa nay đang ăn cơm thì tự nhiên "
      "quay cuồng như mọi lần, buồn nôn mà chưa nôn. Nhưng lần này tay trái với chân trái em tê bì, cầm điện thoại cứ "
      "tuột, đi thì lết chân trái. Giờ hơn 3 tiếng rồi vẫn vậy. Chắc đợt này nặng hơn thôi chị nhỉ?",
      {"dizziness_present": "YES", "dizziness_sensation": "SPINNING",
       "focal_neurologic_symptoms": "WEAKNESS_OR_NUMBNESS", "symptom_onset": "SUDDEN",
       "gastrointestinal_symptom_present": "YES", "vomiting_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("vertigo", "limb_numbness", "limb_weakness"), screen=HIT,
      answers={"dizziness_present": "Có, em chóng mặt quay cuồng.",
               "dizziness_sensation": "Quay cuồng như mọi lần em lên cơn tiền đình.",
               "focal_neurologic_symptoms": "Tay trái với chân trái em tê bì, cầm điện thoại cứ tuột, đi thì lết chân "
                                            "trái.",
               "symptom_onset": "Tự nhiên bị, đang ăn cơm trưa thì quay cuồng.",
               "gastrointestinal_symptom_present": "Có, em buồn nôn.",
               "vomiting_present": "Chưa, em buồn nôn thôi chứ chưa nôn.",
               "symptom_duration_bucket": "Hơn 3 tiếng rồi."},
      tags=("comorbidity", "minimization", "hidden_red_flag", "negation"),
      test="Người có bệnh rối loạn tiền đình gặp cơn chóng mặt 'như mọi lần' nhưng kèm tê yếu tay chân trái và tự trấn "
           "an: agent không được để bệnh nền quen thuộc che mất dấu thần kinh khu trú mới."),

    # ------------------------------------------------------------------ ESI 2: chấn thương đầu
    S("r87", "infant_motorbike_fall_ear_bleeding", "Bé 10 tháng ngồi trước xe máy bị ngã, máu rỉ từ tai",
      P(0, "Male", "CHILD", months=10),
      "Bé trai nhà em 10 tháng. Em chở bé ngồi phía trước xe máy, tới khúc cua thì xe trượt ngã, đầu bé đập xuống mặt "
      "đường. Bé khóc thét liền, em xem khắp đầu không thấy u hay rách chỗ nào, mà máu cứ rỉ ra từ lỗ tai phải của bé. "
      "Mới cách đây chừng nửa tiếng, bé chưa ói lần nào.",
      {"trauma_present": "YES", "trauma_mechanism": "MOTORCYCLE_COLLISION", "injury_region": "HEAD",
       "recent_head_trauma": "YES", "visible_head_injury_sign": "EAR_BLEEDING", "ent_bleeding_present": "YES",
       "estimated_ent_bleeding_amount": "SMALL", "post_trauma_awareness_change": "NONE",
       "post_trauma_vomiting_count": 0, "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("head_injury", "ear_bleeding"), screen=QUIET,
      answers={"trauma_present": "Có, em chở bé đi xe máy bị trượt ngã.",
               "trauma_mechanism": "Xe máy trượt ngã ở khúc cua, bé ngồi phía trước.",
               "injury_region": "Đầu bé đập xuống mặt đường.",
               "recent_head_trauma": "Có, đầu bé đập xuống đường lúc ngã xe.",
               "visible_head_injury_sign": "Em không thấy u hay rách gì trên đầu, chỉ thấy máu rỉ ra từ lỗ tai phải.",
               "ent_bleeding_present": "Có, máu rỉ ra từ lỗ tai phải của bé.",
               "estimated_ent_bleeding_amount": "Rỉ ra ít thôi.",
               "post_trauma_awareness_change": "Bé khóc thét ngay lúc ngã, không lịm đi lúc nào.",
               "post_trauma_vomiting_count": "Bé chưa ói lần nào.",
               "symptom_duration_bucket": "Mới chừng nửa tiếng."},
      tags=("pediatric", "caregiver", "negation"),
      test="Trẻ 10 tháng ngồi trước xe máy bị ngã đập đầu, chỉ thấy máu rỉ từ tai, không u không rách, khóc ngay, chưa "
           "nôn: chảy máu tai sau chấn thương đầu là dữ kiện quyết định dù các dấu hiệu khác đều yên."),
    S("r88", "rollerblade_fall_amnesia_friend_reports", "Thiếu niên trượt patin té ngửa đập đầu, không ngất nhưng không nhớ lúc té",
      P(15, "Male", "OTHER"),
      "Bạn em 15 tuổi trượt patin ở công viên bị té ngửa, đập đầu xuống nền xi măng, cách đây khoảng 20 phút. Tụi em thấy "
      "nó không bị ngất, tự ngồi dậy được, mà giờ nó không nhớ mình té lúc nào, hỏi tụi em tới công viên bằng gì nó cũng "
      "không nhớ. Nó vẫn biết tên tụi em, nói chuyện rõ, chưa ói, kêu hơi nhức đầu.",
      {"trauma_present": "YES", "trauma_mechanism": "FALL", "injury_region": "HEAD",
       "recent_head_trauma": "YES", "post_trauma_awareness_change": "MEMORY_GAP", "post_trauma_vomiting_count": 0,
       "altered_mental_status_present": "NO", "headache_present": "YES", "pain_present": "YES",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("head_injury", "memory_loss"), screen=QUIET,
      answers={"trauma_present": "Có, nó trượt patin bị té ngửa.",
               "trauma_mechanism": "Trượt patin té ngửa, đập đầu xuống nền xi măng.",
               "injury_region": "Ở đầu.",
               "recent_head_trauma": "Có, nó đập đầu xuống nền xi măng khoảng 20 phút trước.",
               "post_trauma_awareness_change": "Nó không bị ngất, nhưng không nhớ mình té lúc nào, cũng không nhớ tụi em "
                                               "tới công viên bằng gì.",
               "post_trauma_vomiting_count": "Nó chưa ói lần nào.",
               "altered_mental_status_present": "Không, nó vẫn biết tên tụi em, nói chuyện rõ, chỉ không nhớ đoạn lúc "
                                                "té.",
               "headache_present": "Có, nó kêu hơi nhức đầu.",
               "pain_present": "Có, nó kêu hơi nhức đầu.",
               "symptom_duration_bucket": "Mới khoảng 20 phút."},
      unknown={"pain_severity": "Em chưa hỏi nó đau mấy điểm."},
      tags=("adolescent", "caregiver", "collateral_history", "negation"),
      test="Thiếu niên trượt patin té đập đầu, không ngất, vẫn nhận ra bạn bè nhưng quên cả đoạn trước và lúc té, bạn "
           "cùng tuổi kể: mất trí nhớ sau chấn thương đầu là dữ kiện quyết định dù cậu bé trông bình thường."),
    S("r89", "storm_branch_on_helmeted_rider_left_numbness", "Cành cây gãy rơi trúng đầu khi đi xe máy, tê nửa người trái",
      P(27, "Female"),
      "Chiều nay giông to, em đang chạy xe máy thì một nhánh cây lớn gãy rơi trúng đầu. Em có đội mũ bảo hiểm mà mũ nứt "
      "luôn, em không ngất, tự dắt xe vào lề được. Giờ khoảng 2 tiếng rồi, đầu đau âm ỉ, tay trái với chân trái cứ tê bì "
      "như không phải của mình.",
      {"trauma_present": "YES", "trauma_mechanism": "DIRECT_BLOW", "injury_region": "HEAD", "recent_head_trauma": "YES",
       "limb_neurologic_symptoms": "NUMBNESS", "focal_neurologic_symptoms": "WEAKNESS_OR_NUMBNESS",
       "post_trauma_awareness_change": "NONE", "headache_present": "YES", "headache_character": "DULL",
       "pain_present": "YES", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("head_injury", "limb_numbness"), screen=HIT,
      answers={"trauma_present": "Có, nhánh cây gãy rơi trúng đầu em lúc đang chạy xe.",
               "trauma_mechanism": "Nhánh cây lớn gãy rơi trúng đầu.",
               "injury_region": "Ở đầu.",
               "recent_head_trauma": "Có, chiều nay nhánh cây rơi trúng đầu em.",
               "limb_neurologic_symptoms": "Tay trái với chân trái tê bì, như không phải của mình.",
               "focal_neurologic_symptoms": "Tay chân bên trái tê bì.",
               "post_trauma_awareness_change": "Em không ngất, nhớ rõ hết mọi chuyện.",
               "headache_present": "Có, đầu đau âm ỉ.",
               "headache_character": "Đau âm ỉ.",
               "pain_present": "Có, đầu đau âm ỉ.",
               "symptom_duration_bucket": "Khoảng 2 tiếng rồi."},
      tags=("environmental", "negation", "road_traffic"),
      test="Người đi xe máy có đội mũ bị cành cây gãy rơi trúng đầu, không ngất, tự nhắn tin được nhưng tê nửa người "
           "trái: mũ bảo hiểm và việc tỉnh táo không loại trừ tổn thương nội sọ."),
    S("r90", "valve_anticoagulant_kitchen_fall_next_day_right_paralysis",
      "Người thay van tim dùng thuốc chống đông ngã đập đầu, sáng hôm sau liệt tay chân phải",
      P(41, "Female", "SPOUSE", chronic=("Thay van hai lá cơ học do thấp tim",), meds=("Acenocoumarol 2 mg mỗi tối",)),
      "Vợ tôi 41 tuổi, thay van tim cơ học đã 5 năm, ngày nào cũng uống thuốc chống đông acenocoumarol. Tối qua cô ấy "
      "trượt chân trong bếp, đập đầu vào cạnh bàn đá, chỉ sưng một cục nhỏ nên cả nhà nghĩ không sao. Sáng nay dậy thì "
      "tay chân bên phải cô ấy không nhúc nhích được chút nào, nói vẫn rõ nhưng cứ lơ mơ, ngủ gà ngủ gật.",
      {"trauma_present": "YES", "trauma_mechanism": "FALL", "injury_region": "HEAD", "recent_head_trauma": "YES",
       "visible_head_injury_sign": "SCALP_SWELLING", "swelling_present": "YES", "swelling_location": "OTHER",
       "limb_neurologic_symptoms": "PARALYSIS", "focal_neurologic_symptoms": "WEAKNESS_OR_NUMBNESS",
       "altered_mental_status_present": "YES", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("head_injury", "paralysis"), screen=HIT,
      answers={"trauma_present": "Có, tối qua cô ấy trượt chân ngã trong bếp.",
               "trauma_mechanism": "Trượt chân ngã, đập đầu vào cạnh bàn đá.",
               "injury_region": "Ở đầu, chỗ đập vào cạnh bàn đá.",
               "recent_head_trauma": "Có, tối qua cô ấy đập đầu vào cạnh bàn đá.",
               "visible_head_injury_sign": "Chỉ sưng một cục nhỏ trên đầu.",
               "swelling_present": "Có, trên đầu sưng một cục nhỏ.",
               "swelling_location": "Sưng một cục nhỏ trên đầu.",
               "limb_neurologic_symptoms": "Tay chân bên phải không nhúc nhích được chút nào.",
               "focal_neurologic_symptoms": "Tay chân phải không cử động được; nói thì vẫn rõ.",
               "altered_mental_status_present": "Có, cô ấy cứ lơ mơ, ngủ gà ngủ gật.",
               "symptom_duration_bucket": "Liệt từ sáng nay, mấy tiếng rồi; còn ngã là từ tối qua."},
      tags=("caregiver", "anticoagulant", "comorbidity"),
      test="Ngã đập đầu tưởng nhẹ ở người thay van tim dùng thuốc chống đông, sáng hôm sau liệt tay chân phải và lơ mơ: "
           "khác r37 (va đập nhẹ, chưa có dấu hiệu gì), ở đây dấu thần kinh xuất hiện muộn mới là dữ kiện quyết định."),
    S("r91", "post_crash_facial_droop_blamed_on_fan", "Hai ngày sau té xe đập đầu thì méo miệng, mẹ cho là do nằm quạt",
      P(22, "Female", allergies=("Tôm, cua",)),
      "Em 22 tuổi. Hôm kia em đi xe máy bị té, đập bên đầu trái xuống lề đường, có đội mũ, lúc đó không ngất, chỉ đau đầu "
      "nên về nhà nằm. Sáng nay soi gương thì thấy miệng méo xệch sang phải, mắt trái nhắm không kín, uống nước bị trào ra "
      "mép trái. Mẹ em bảo tại tối qua em nằm quạt phả thẳng vào mặt, bị liệt dây 7 thôi, đi châm cứu là khỏi. Giờ đầu vẫn "
      "còn đau âm ỉ.",
      {"trauma_present": "YES", "trauma_mechanism": "MOTORCYCLE_COLLISION", "injury_region": "HEAD",
       "recent_head_trauma": "YES", "post_trauma_awareness_change": "NONE", "focal_neurologic_symptoms": "FACIAL_ASYMMETRY",
       "headache_present": "YES", "headache_character": "DULL", "pain_present": "YES",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("facial_weakness", "head_injury"), screen=HIT,
      answers={"trauma_present": "Có, hôm kia em đi xe máy bị té.",
               "trauma_mechanism": "Té xe máy, đập bên đầu trái xuống lề đường.",
               "injury_region": "Bên đầu trái.",
               "recent_head_trauma": "Có, hôm kia em té xe đập bên đầu trái xuống lề đường.",
               "post_trauma_awareness_change": "Lúc té em không ngất, nhớ rõ hết.",
               "focal_neurologic_symptoms": "Miệng méo xệch sang phải, mắt trái nhắm không kín, uống nước trào ra mép "
                                            "trái.",
               "headache_present": "Có, đầu vẫn còn đau âm ỉ.",
               "headache_character": "Đau âm ỉ.",
               "pain_present": "Có, đầu vẫn đau âm ỉ.",
               "symptom_duration_bucket": "Méo miệng thì sáng nay mới thấy, còn té xe là từ hôm kia."},
      tags=("minimization", "hidden_red_flag", "folk_belief", "negation"),
      test="Méo miệng, nhắm mắt không kín xuất hiện hai ngày sau té xe đập đầu, gia đình cho là liệt mặt do nằm quạt: "
           "agent phải nối dấu hiệu này với lần chấn thương đầu chứ không coi là liệt mặt đơn thuần."),
    S("r92", "assault_stick_left_head_lucid_then_aphasia", "Bị đánh gậy vào đầu, về phòng bình thường rồi mới nói không thành lời",
      P(24, "Male", "OTHER"),
      "Bạn cùng phòng trọ của em 24 tuổi, tối nay đi làm thêm về bị mấy người lạ chặn đường đánh, bị phang một gậy vào "
      "bên trái đầu, lúc đó bạn ko ngất. Về tới phòng vẫn nói chuyện bình thường, chỗ bị đánh sưng môt cục. Khoảng 40 "
      "phút nay bạn bắt đầu nói ko ra lời, cứ bập bẹ từng chữ, muốn gọi cái chìa khoá mà nói mãi ko ra rồi tự bực mình. "
      "Bạn vẫn tỉnh, hiểu em nói gì, tay chân cử động bình thường.",
      {"trauma_present": "YES", "trauma_mechanism": "ASSAULT", "injury_region": "HEAD", "recent_head_trauma": "YES",
       "visible_head_injury_sign": "SCALP_SWELLING", "swelling_present": "YES", "swelling_location": "OTHER",
       "post_trauma_awareness_change": "NONE", "focal_neurologic_symptoms": "SPEECH_OR_LANGUAGE_CHANGE",
       "limb_neurologic_symptoms": "NONE", "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("head_injury", "speech_difficulty"), screen=HIT,
      answers={"trauma_present": "Có, bạn bị mấy người lạ chặn đường đánh.",
               "trauma_mechanism": "Bị người ta đánh, phang một gậy vào đầu.",
               "injury_region": "Bên trái đầu.",
               "recent_head_trauma": "Có, tối nay bạn bị phang gậy vào bên trái đầu.",
               "visible_head_injury_sign": "Chỗ bị đánh sưng một cục.",
               "swelling_present": "Có, chỗ bị đánh trên đầu sưng một cục.",
               "swelling_location": "Sưng trên đầu, bên trái.",
               "post_trauma_awareness_change": "Lúc bị đánh bạn ko ngất, về phòng vẫn nói chuyện bình thường.",
               "focal_neurologic_symptoms": "Bạn nói ko ra lời, bập bẹ từng chữ, muốn gọi tên đồ vật mà ko nói ra "
                                            "được.",
               "limb_neurologic_symptoms": "Tay chân bạn cử động bình thường.",
               "altered_mental_status_present": "Ko, bạn vẫn tỉnh, hiểu em nói gì.",
               "symptom_duration_bucket": "Nói ko ra lời thì khoảng 40 phút nay, còn bị đánh là đầu buổi tối."},
      tags=("caregiver", "collateral_history", "abbreviation", "typo", "negation", "assault"),
      test="Bị đánh vào đầu, về phòng vẫn nói chuyện bình thường rồi sau đó mới nói không thành lời: khoảng tỉnh sau chấn "
           "thương không phải lý do yên tâm, rối loạn lời nói sau va đập đầu là dữ kiện quyết định."),
    S("r93", "pregnant_backward_fall_occiput_blurred_vision", "Thai 26 tuần ngã ngửa đập phía sau đầu, từ đó nhìn mờ hai mắt",
      P(29, "Female", allergies=("Cefaclor",)),
      "Em có bầu 26 tuần. Sáng nay lau nhà trơn, em trượt ngã ngửa, đập phía sau đầu xuống nền gạch. Em không ngất, ngồi "
      "dậy được ngay, nhưng từ lúc đó hai mắt nhìn mờ hẳn, cái gì cũng như qua một lớp sương, sau đầu đau ê ẩm. Bụng em "
      "không đau, không ra máu, con vẫn đạp bình thường.",
      {"trauma_present": "YES", "trauma_mechanism": "FALL", "injury_region": "HEAD", "recent_head_trauma": "YES",
       "post_trauma_awareness_change": "NONE", "focal_neurologic_symptoms": "VISION_CHANGE",
       "vision_impairment_present": "YES", "vision_impairment_extent": "BLURRED", "headache_present": "YES",
       "headache_location": "OCCIPITAL", "pain_present": "YES", "pregnancy_present": "YES",
       "pregnancy_status": "PREGNANT", "gestational_age_weeks": 26, "abdominal_pain_present": "NO",
       "vaginal_bleeding_present": "NO", "fetal_movement_status": "NORMAL", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("head_injury", "blurred_vision"), screen=QUIET,
      answers={"trauma_present": "Có, sáng nay em trượt ngã ngửa lúc lau nhà.",
               "trauma_mechanism": "Trượt chân trên sàn ướt, ngã ngửa.",
               "injury_region": "Phía sau đầu.",
               "recent_head_trauma": "Có, sáng nay em ngã ngửa đập phía sau đầu xuống nền gạch.",
               "post_trauma_awareness_change": "Em không ngất, ngồi dậy được ngay, nhớ hết.",
               "focal_neurologic_symptoms": "Từ lúc ngã hai mắt em nhìn mờ hẳn.",
               "vision_impairment_present": "Có, từ lúc ngã em nhìn mờ hẳn.",
               "vision_impairment_extent": "Nhìn mờ, cái gì cũng như qua một lớp sương.",
               "headache_present": "Có, sau đầu em đau ê ẩm.",
               "headache_location": "Đau ở phía sau đầu, chỗ bị đập.",
               "pain_present": "Có, sau đầu đau ê ẩm.",
               "pregnancy_present": "Dạ có, em đang bầu 26 tuần.",
               "pregnancy_status": "Em đang mang thai.",
               "gestational_age_weeks": "Thai được 26 tuần.",
               "abdominal_pain_present": "Không, bụng em không đau.",
               "vaginal_bleeding_present": "Không, em không ra máu.",
               "fetal_movement_status": "Con vẫn đạp bình thường.",
               "symptom_duration_bucket": "Từ sáng nay, lúc ngã tới giờ được mấy tiếng rồi."},
      tags=("pregnancy", "negation"),
      test="Thai phụ 26 tuần ngã ngửa đập phía sau đầu, từ đó nhìn mờ hai mắt, thai vẫn ổn: dấu hiệu thị giác mới sau "
           "chấn thương đầu quyết định mức ưu tiên, các câu trả lời sản khoa yên ổn không làm giảm mức."),
    S("r94", "bus_step_fall_head_and_back_delayed_left_weakness",
      "Cụ bà hụt chân khi xuống xe buýt, đập đầu, đau lưng, vài giờ sau yếu dần tay chân trái",
      P(74, "Female", "PARENT", chronic=("Thoái hoá khớp gối", "Tăng huyết áp"), meds=("Losartan 50 mg",)),
      "Mẹ tôi 74 tuổi, trưa nay bước xuống xe buýt bị hụt chân ngã ngửa, đập phía sau đầu xuống vỉa hè, đau cả vùng lưng. "
      "Lúc đó mẹ vẫn tự đứng dậy được, nói chuyện bình thường, không ngất. Nhưng khoảng 2 tiếng nay tay trái mẹ yếu dần, "
      "cầm cốc nước run rồi đánh rơi, chân trái bước đi cứ kéo lê. Nhà tôi đang định cho mẹ nằm nghỉ xem sao.",
      {"trauma_present": "YES", "trauma_mechanism": "FALL", "injury_region": "MULTIPLE_REGIONS",
       "recent_head_trauma": "YES", "back_or_spinal_problem_present": "YES", "pain_present": "YES",
       "post_trauma_awareness_change": "NONE", "focal_neurologic_symptoms": "WEAKNESS_OR_NUMBNESS",
       "limb_neurologic_symptoms": "WEAKNESS", "symptom_onset": "GRADUAL", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("head_injury", "limb_weakness", "back_injury"), screen=HIT,
      answers={"trauma_present": "Có, trưa nay mẹ bước xuống xe buýt bị hụt chân ngã ngửa.",
               "trauma_mechanism": "Hụt chân lúc bước xuống xe buýt, ngã ngửa.",
               "injury_region": "Cả đầu lẫn lưng: phía sau đầu đập xuống vỉa hè, lưng thì đau cả vùng.",
               "recent_head_trauma": "Có, mẹ đập phía sau đầu xuống vỉa hè lúc ngã.",
               "back_or_spinal_problem_present": "Có, mẹ kêu đau cả vùng lưng từ lúc ngã.",
               "pain_present": "Có, mẹ kêu đau lưng.",
               "post_trauma_awareness_change": "Lúc ngã mẹ không ngất, tự đứng dậy, nói chuyện bình thường.",
               "focal_neurologic_symptoms": "Tay trái mẹ yếu dần, cầm cốc run rồi đánh rơi, chân trái bước kéo lê.",
               "limb_neurologic_symptoms": "Tay trái yếu dần, chân trái bước đi kéo lê.",
               "symptom_onset": "Yếu từ từ, tăng dần trong khoảng 2 tiếng nay.",
               "symptom_duration_bucket": "Ngã từ trưa, còn yếu tay chân là khoảng 2 tiếng nay."},
      tags=("older_adult", "caregiver", "comorbidity", "minimization", "negation"),
      test="Cụ bà ngã ngửa khi xuống xe buýt, chấn thương cả đầu lẫn lưng, vài giờ sau yếu dần tay chân trái mà gia đình "
           "định để nằm nghỉ: dấu thần kinh khu trú mới sau va đập đầu quyết định mức, không phải vùng chấn thương."),

    # ------------------------------------------------------------------ ESI 2: mất thăng bằng kèm dấu thần kinh
    S("r95", "child_progressive_unsteady_gait_facial_droop", "Trẻ 7 tuổi hơn hai tuần đi loạng choạng, nôn buổi sáng, cười miệng lệch",
      P(7, "Female", "CHILD"),
      "Con gái tôi 7 tuổi, hơn hai tuần nay đi đứng cứ loạng choạng như người say, phải vịn tường, ngày càng rõ hơn. Bé hay "
      "kêu đau đầu lúc mới ngủ dậy, tuần này có ba buổi sáng bé nôn. Mấy hôm nay tôi để ý bé cười thì miệng lệch hẳn sang "
      "một bên. Bé không sốt, trước đó cũng không bị ngã hay va đập gì. Cô giáo bảo chắc bé thiếu ngủ.",
      {"dizziness_present": "YES", "dizziness_sensation": "IMBALANCE", "focal_neurologic_symptoms": "FACIAL_ASYMMETRY",
       "headache_present": "YES", "pain_present": "YES", "vomiting_present": "YES", "vomiting_frequency": "FEW_TIMES",
       "gastrointestinal_symptom_present": "YES", "fever_present": "NO", "trauma_present": "NO",
       "symptom_onset": "GRADUAL", "symptom_trend": "WORSENING", "symptom_duration_bucket": "OVER_7_DAYS"},
      2, concepts=("ataxia", "facial_weakness", "headache"), screen=HIT,
      answers={"dizziness_present": "Có, bé đi đứng mất thăng bằng, loạng choạng như người say.",
               "dizziness_sensation": "Chủ yếu là đi đứng không vững, phải vịn tường.",
               "focal_neurologic_symptoms": "Mấy hôm nay bé cười thì miệng lệch hẳn sang một bên.",
               "headache_present": "Có, bé hay kêu đau đầu lúc mới ngủ dậy.",
               "pain_present": "Có, bé kêu đau đầu buổi sáng.",
               "vomiting_present": "Có, tuần này bé nôn ba buổi sáng.",
               "vomiting_frequency": "Tuần này nôn ba lần, đều vào buổi sáng.",
               "gastrointestinal_symptom_present": "Có, bé nôn mấy buổi sáng.",
               "fever_present": "Không, bé không sốt.",
               "trauma_present": "Không, trước đó bé không bị ngã hay va đập gì.",
               "symptom_onset": "Từ từ, không phải tự nhiên một lúc mà bị.",
               "symptom_trend": "Ngày càng rõ hơn.",
               "symptom_duration_bucket": "Đi loạng choạng hơn hai tuần nay rồi, còn miệng lệch thì mấy hôm nay."},
      unknown={"pain_severity": "Tôi hỏi đau mấy điểm thì bé không biết nói."},
      tags=("pediatric", "caregiver", "negation", "minimization", "subacute"),
      test="Trẻ 7 tuổi hơn hai tuần đi loạng choạng, đau đầu và nôn buổi sáng, mới đây cười miệng lệch: diễn tiến từ từ "
           "nên không tiêu chí 'đột ngột' nào khớp, agent vẫn phải xếp ưu tiên cao vì mất thăng bằng kèm dấu thần kinh "
           "khu trú."),
    S("r96", "wedding_two_beers_ataxia_slurred_wife_doubts",
      "Ăn cưới uống hai lon bia, đi loạng choạng, nói líu lưỡi, vợ thấy khác hẳn mọi khi",
      P(48, "Male", "SPOUSE", chronic=("Tăng huyết áp",), meds=("Lisinopril 10 mg",)),
      "Chồng tôi 48 tuổi, trưa nay đi ăn cưới mới uống có hai lon bia, vậy mà từ lúc về, khoảng một tiếng rưỡi nay, anh "
      "đi đứng loạng choạng, phải vịn tường, nói thì lè nhè líu lưỡi. Mọi người bảo anh say, cứ để ngủ một giấc là hết, "
      "nhưng bình thường anh uống cả chục lon cũng không đến mức này. Anh vẫn tỉnh, nhận ra tôi, tay chân cử động được.",
      {"dizziness_present": "YES", "dizziness_sensation": "IMBALANCE",
       "focal_neurologic_symptoms": "SPEECH_OR_LANGUAGE_CHANGE", "substance_involvement": "RECENT_USE_REPORTED",
       "altered_mental_status_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("gait_disturbance", "slurred_speech"), screen=HIT,
      answers={"dizziness_present": "Có, anh đi đứng mất thăng bằng.",
               "dizziness_sensation": "Đi đứng loạng choạng, phải vịn tường.",
               "focal_neurologic_symptoms": "Anh nói lè nhè, líu lưỡi; tay chân vẫn cử động được.",
               "substance_involvement": "Trưa nay đi ăn cưới anh uống hai lon bia, ngoài ra không dùng gì.",
               "altered_mental_status_present": "Không, anh vẫn tỉnh, nhận ra tôi.",
               "symptom_duration_bucket": "Khoảng một tiếng rưỡi nay, từ lúc đi ăn cưới về."},
      tags=("caregiver", "intoxication", "hidden_red_flag", "minimization"),
      test="Đi loạng choạng, nói líu lưỡi sau hai lon bia, mọi người cho là say: agent không được quy cho rượu khi lượng "
           "uống không tương xứng và người vợ thấy khác hẳn mọi khi."),

    # ------------------------------------------------------------------ ESI 2: chấn thương thắt lưng, dấu hiệu nền sọ
    S("r97", "shoulder_pole_vendor_fell_on_step_lower_back_leg_tingling",
      "Người bán hàng gánh té ngửa đập thắt lưng vào bậc đá, châm chích hai chân, gõ không dấu",
      P(45, "Female"),
      "Toi 45 tuoi, ban hang ganh o cho. Khoang 3 tieng truoc dang ganh hai thung hang xuong bac da o ben cho thi truot "
      "chan te ngua, that lung dap vao canh bac. Gio that lung dau nhoi, toi cham chung 8/10, hai chan cu cham chich nhu "
      "kien bo tu mong xuong ban chan. Van di duoc nhung toi so lam. Di tieu van binh thuong.",
      {"trauma_present": "YES", "trauma_mechanism": "FALL", "injury_region": "LOWER_BACK",
       "limb_neurologic_symptoms": "TINGLING", "back_or_spinal_problem_present": "YES",
       "bowel_bladder_control_change": "NONE", "pain_present": "YES", "pain_severity": 8,
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("lower_back_pain", "back_injury", "tingling"), screen=QUIET,
      answers={"trauma_present": "Co, toi truot chan te ngua luc dang ganh hang.",
               "trauma_mechanism": "Truot chan te ngua tren bac da, that lung dap vao canh bac.",
               "injury_region": "O that lung.",
               "limb_neurologic_symptoms": "Hai chan cham chich nhu kien bo tu mong xuong ban chan, van nhac len duoc.",
               "back_or_spinal_problem_present": "Co, that lung dau nhoi tu luc te.",
               "bowel_bladder_control_change": "Di tieu van binh thuong, khong bi gi.",
               "pain_present": "Co, that lung dau nhoi.",
               "pain_severity": "Toi cham chung 8/10.",
               "symptom_duration_bucket": "Khoang 3 tieng roi."},
      clarification="Noi lai cho ro: khoang 3 tieng truoc toi dang ganh hang xuong bac da thi te ngua, that lung dap vao "
                    "canh bac, gio dau nhoi chung 8/10, hai chan cham chich tu mong xuong ban chan.",
      confirmation="Dung roi, vay la du.",
      tags=("no_diacritics", "occupational", "negation"),
      test="Người bán hàng gánh té ngửa đập thắt lưng, đau 8/10 kèm châm chích hai chân nhưng vẫn đi được, gõ không dấu: "
           "dấu thần kinh nhẹ ở chân sau chấn thương thắt lưng đã đủ quyết định."),
    S("r98", "ladder_gutter_fall_delayed_bruise_behind_ear", "Ngã thang hai hôm trước, sáng nay mới thấy bầm tím sau tai",
      P(68, "Male", "SPOUSE", chronic=("Đái tháo đường type 2",), meds=("Metformin 850 mg",)),
      "Ông nhà tui 68 tuổi, hôm kia trèo thang sửa máng xối bị trượt, ngã nghiêng đập bên đầu phải xuống sân. Ông nói không "
      "răng, vẫn ăn uống, đi lại bình thường, không ói, không ngất. Sáng ni tui thấy sau tai phải ông có một mảng bầm tím "
      "to bằng quả trứng gà, hôm qua chưa có. Ông chỉ hơi nhức đầu, chấm chừng 3 điểm.",
      {"trauma_present": "YES", "trauma_mechanism": "FALL", "injury_region": "HEAD", "recent_head_trauma": "YES",
       "visible_head_injury_sign": "MASTOID_BRUISING", "post_trauma_awareness_change": "NONE",
       "post_trauma_vomiting_count": 0, "functional_status": "NORMAL", "headache_present": "YES", "pain_present": "YES",
       "pain_severity": 3, "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      2, concepts=("mastoid_bruising", "head_injury"), screen=QUIET,
      answers={"trauma_present": "Có, hôm kia ông trèo thang bị trượt ngã.",
               "trauma_mechanism": "Trèo thang sửa máng xối bị trượt, ngã nghiêng xuống sân.",
               "injury_region": "Bên đầu phải.",
               "recent_head_trauma": "Có, hôm kia ông ngã đập bên đầu phải xuống sân.",
               "visible_head_injury_sign": "Sau tai phải có mảng bầm tím to bằng quả trứng gà, sáng ni mới thấy.",
               "post_trauma_awareness_change": "Ông không ngất, nhớ rõ hết.",
               "post_trauma_vomiting_count": "Ông không ói lần mô.",
               "functional_status": "Ông vẫn ăn uống, đi lại bình thường.",
               "headache_present": "Có, ông hơi nhức đầu.",
               "pain_present": "Có, ông hơi nhức đầu.",
               "pain_severity": "Ông chấm chừng 3 điểm.",
               "symptom_duration_bucket": "Ông ngã từ hôm kia, nhức đầu từ bữa đó; còn vết bầm sau tai thì sáng ni mới "
                                          "thấy."},
      tags=("older_adult", "caregiver", "dialect", "minimization", "hidden_red_flag", "negation"),
      test="Bầm tím sau tai xuất hiện muộn hai ngày sau ngã đập đầu, ông vẫn sinh hoạt bình thường và chỉ nhức đầu 3/10: "
           "một dấu hiệu nghi vỡ nền sọ đơn lẻ đã đủ quyết định, agent không được trấn an vì 'đã hai ngày không sao'."),
    S("r99", "neighbor_shelters_beaten_woman_raccoon_eyes_ear_blood",
      "Hàng xóm kể: chị bị chồng đánh đêm qua, bầm quanh hai mắt, máu khô trong tai",
      P(38, "Female", "OTHER"),
      "Sáng nay chị hàng xóm 38 tuổi chạy sang nhà tôi trốn, kể đêm qua bị chồng say rượu đánh, đập đầu chị vào thành "
      "giường mấy cái. Giờ quanh hai mắt chị bầm tím đen như đeo kính râm, trong lỗ tai phải có máu khô. Chị vẫn tỉnh, "
      "nói chuyện được, kêu đau đầu, nhưng không dám về nhà và xin tôi đừng cho ai biết.",
      {"trauma_present": "YES", "trauma_mechanism": "ASSAULT", "injury_region": "HEAD", "recent_head_trauma": "YES",
       "visible_head_injury_sign": "MULTIPLE", "ent_bleeding_present": "YES", "estimated_ent_bleeding_amount": "TRACE",
       "headache_present": "YES", "pain_present": "YES", "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("head_injury", "periorbital_bruising", "ear_bleeding"), screen=QUIET,
      answers={"trauma_present": "Có, đêm qua chị bị chồng đánh.",
               "trauma_mechanism": "Bị chồng đánh, đập đầu vào thành giường.",
               "injury_region": "Ở đầu.",
               "recent_head_trauma": "Có, đêm qua chị bị đập đầu vào thành giường mấy cái.",
               "visible_head_injury_sign": "Quanh hai mắt bầm tím đen như đeo kính râm, trong lỗ tai phải có máu khô.",
               "ent_bleeding_present": "Có, trong lỗ tai phải có máu khô.",
               "estimated_ent_bleeding_amount": "Chỉ có chút máu khô trong lỗ tai.",
               "headache_present": "Có, chị kêu đau đầu.",
               "pain_present": "Có, chị kêu đau đầu.",
               "altered_mental_status_present": "Không, chị vẫn tỉnh, nói chuyện được.",
               "symptom_duration_bucket": "Chị bị đánh đêm qua, tới giờ chừng mười tiếng."},
      unknown={"post_trauma_awareness_change": "Chị không kể lúc bị đánh có ngất hay không, tôi cũng chưa dám hỏi kỹ."},
      tags=("caregiver", "collateral_history", "domestic_violence", "sensitive_topic", "null_unknown"),
      test="Nạn nhân bạo lực gia đình bị đập đầu, bầm quanh hai mắt và có máu khô trong tai, hàng xóm kể hộ: agent phải "
           "xếp ưu tiên cao theo dấu hiệu chấn thương đầu, không phán xét và không khuyên chị quay về nhà."),

    # ------------------------------------------------------------------ ESI 2: chấn thương cổ, vết thương xuyên đầu
    S("r100", "teen_trampoline_flip_neck_arms_numb_weak", "Thiếu nữ lộn ngược trên đệm nhún tiếp đất bằng gáy, hai tay tê và yếu",
      P(14, "Female"),
      "E 14 tuổi, chiều nay tập lộn ngược trên đệm nhún ở nhà bạn thì tiếp đất bằng gáy, nghe cổ kêu rắc 1 cái. Giờ khoảng "
      "2 tiếng rồi, cổ đau cứng ko dám quay, 2 tay tê rần rần mà còn yếu nữa, cầm cái ly ko chặt, rớt luôn. Chân thì vẫn "
      "đi dc bt, e ko bị ngất. E chưa dám nói mẹ vì sợ bị la.",
      {"trauma_present": "YES", "trauma_mechanism": "SPORTS_INJURY", "injury_region": "NECK",
       "limb_neurologic_symptoms": "MULTIPLE", "back_or_spinal_problem_present": "YES", "neck_stiffness_present": "YES",
       "pain_present": "YES", "post_trauma_awareness_change": "NONE", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("neck_injury", "upper_extremity_numbness", "upper_extremity_weakness"), screen=QUIET,
      answers={"trauma_present": "Có, e tập lộn ngược trên đệm nhún bị tiếp đất bằng gáy.",
               "trauma_mechanism": "Tập lộn ngược trên đệm nhún, tiếp đất bằng gáy.",
               "injury_region": "Ở cổ, chỗ gáy.",
               "limb_neurologic_symptoms": "2 tay tê rần rần mà còn yếu, cầm ly ko chặt. Chân thì bt.",
               "back_or_spinal_problem_present": "Có, cổ e đau cứng ko dám quay.",
               "neck_stiffness_present": "Cổ đau cứng, ko dám quay.",
               "pain_present": "Có, cổ e đau.",
               "post_trauma_awareness_change": "E ko bị ngất, nhớ hết.",
               "symptom_duration_bucket": "Khoảng 2 tiếng rồi."},
      tags=("adolescent", "abbreviation", "concealment", "sports"),
      test="Thiếu nữ tự nhắn, lộn ngược trên đệm nhún tiếp đất bằng gáy, hai tay vừa tê vừa yếu, chân vẫn đi được và muốn "
           "giấu mẹ: agent phải xếp ưu tiên cao và khuyến khích em báo người lớn ngay."),
    S("r101", "roofer_fall_neck_strike_quadriplegia", "Thợ lợp mái rơi từ mái nhà, gáy đập xuống, tỉnh nhưng không cử động được tay chân",
      P(41, "Male", "OTHER"),
      "Anh thợ lợp tôn làm chung với tôi, 41 tuổi, khoảng 15 phút trước trượt chân rơi từ mái nhà cao chừng 4 mét, té ngửa, "
      "gáy đập vào mép bồn nước. Giờ anh nằm dưới đất, tỉnh, nói chuyện được, thở đều, kêu đau cổ dữ dội, nhưng cả hai tay "
      "hai chân không cử động được chút nào. Lúc rơi xuống anh không ngất, kêu la liền. Tụi tôi chưa dám đỡ anh dậy.",
      {"trauma_present": "YES", "trauma_mechanism": "FALL", "injury_region": "NECK", "limb_neurologic_symptoms": "PARALYSIS",
       "back_or_spinal_problem_present": "YES", "pain_present": "YES", "post_trauma_awareness_change": "NONE",
       "dyspnea_present": "NO", "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("neck_injury", "paralysis"), screen=QUIET,
      answers={"trauma_present": "Có, anh rơi từ mái nhà xuống.",
               "trauma_mechanism": "Trượt chân rơi từ mái nhà cao chừng 4 mét, té ngửa.",
               "injury_region": "Ở cổ, gáy đập vào mép bồn nước.",
               "limb_neurologic_symptoms": "Cả hai tay hai chân không cử động được chút nào.",
               "back_or_spinal_problem_present": "Có, anh kêu đau cổ dữ dội.",
               "pain_present": "Có, anh kêu đau cổ dữ dội.",
               "post_trauma_awareness_change": "Anh không ngất, rơi xuống là kêu la liền, giờ vẫn tỉnh.",
               "dyspnea_present": "Không, anh vẫn thở đều.",
               "symptom_duration_bucket": "Mới khoảng 15 phút."},
      tags=("caregiver", "collateral_history", "occupational", "negation"),
      test="Thợ lợp mái rơi từ trên cao, gáy đập xuống, tỉnh táo và thở đều nhưng liệt cả tứ chi, đồng nghiệp kể: liệt sau "
           "chấn thương cổ là dữ kiện quyết định dù người bệnh nói chuyện bình thường."),
    S("r102", "elderly_taxi_rear_end_whiplash_arms_weak", "Cụ ông ngồi taxi bị tông đuôi, cổ bật ngửa, sáng hôm sau hai tay yếu",
      P(77, "Male", "PARENT", chronic=("Thoái hoá cột sống cổ", "Tăng huyết áp"), allergies=("Aspirin",),
        meds=("Amlodipin 5 mg",)),
      "Ba tui 77 tuổi, tối qua đi taxi bị xe phía sau tông vô đuôi, cổ ổng bị giật bật ngửa ra sau. Tối qua ổng chỉ kêu "
      "mỏi cổ, mà sáng nay ổng kêu đau cổ, hai tay yếu xìu, cầm đũa hông nổi, cài nút áo cũng hông được, còn hai chân thì "
      "vẫn đi lại được. Ổng hông đập đầu, hông bị ngất, đầu óc vẫn tỉnh táo.",
      {"trauma_present": "YES", "trauma_mechanism": "MOTOR_VEHICLE_COLLISION", "injury_region": "NECK",
       "limb_neurologic_symptoms": "WEAKNESS", "back_or_spinal_problem_present": "YES", "pain_present": "YES",
       "recent_head_trauma": "NO", "post_trauma_awareness_change": "NONE", "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("neck_injury", "upper_extremity_weakness"), screen=QUIET,
      answers={"trauma_present": "Có, tối qua ổng đi taxi bị xe phía sau tông vô đuôi.",
               "trauma_mechanism": "Ngồi taxi bị xe phía sau tông vô đuôi, cổ bị giật bật ngửa ra sau.",
               "injury_region": "Ở cổ.",
               "limb_neurologic_symptoms": "Hai tay yếu xìu, cầm đũa hông nổi, cài nút áo hông được; hai chân vẫn đi "
                                           "được.",
               "back_or_spinal_problem_present": "Có, sáng nay ổng kêu đau cổ.",
               "pain_present": "Có, ổng kêu đau cổ.",
               "recent_head_trauma": "Hông, ổng hông bị đập đầu, chỉ bị giật cổ thôi.",
               "post_trauma_awareness_change": "Ổng hông bị ngất, nhớ rõ hết.",
               "altered_mental_status_present": "Hông, đầu óc ổng vẫn tỉnh táo.",
               "symptom_duration_bucket": "Bị tông từ tối qua, còn yếu tay là sáng nay mới thấy."},
      tags=("older_adult", "caregiver", "dialect", "comorbidity", "negation", "delayed_deficit"),
      test="Cụ ông thoái hoá cột sống cổ bị giật cổ khi taxi bị tông đuôi, không đập đầu, sáng hôm sau hai tay yếu mà chân "
           "vẫn đi được: kiểu yếu tay nhiều hơn chân dễ bị bỏ qua, agent vẫn phải xếp ưu tiên cao."),
    S("r103", "air_gun_pellet_lodged_in_teen_scalp", "Thiếu niên bị bạn bắn súng hơi trúng đầu, viên đạn chắc còn nằm trong",
      P(13, "Male", "CHILD"),
      "Con trai tôi 13 tuổi, khoảng 30 phút trước đi chơi với mấy đứa bạn, tụi nó lấy súng hơi bắn chim rồi bắn nhầm trúng "
      "đầu cháu, phía trên tai phải. Có một lỗ nhỏ rỉ máu, không thấy viên đạn rơi ra, chắc còn nằm bên trong. Cháu vẫn "
      "tỉnh, nói chuyện bình thường, không ngất, chỉ kêu đau chỗ đó.",
      {"trauma_present": "YES", "trauma_mechanism": "PENETRATING_INJURY", "injury_region": "HEAD",
       "recent_head_trauma": "YES", "visible_head_injury_sign": "SCALP_WOUND", "wound_present": "YES",
       "wound_type": "PENETRATING", "wound_location": "HEAD_FACE", "foreign_body_status": "POSSIBLE",
       "bleeding_present": "YES", "bleeding_control_status": "SLOW_CONTINUOUS", "pain_present": "YES",
       "post_trauma_awareness_change": "NONE", "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("penetrating_trauma", "foreign_body_in_head_neck_or_back", "head_injury"), screen=QUIET,
      answers={"trauma_present": "Có, cháu bị bạn bắn súng hơi trúng đầu.",
               "trauma_mechanism": "Bị bắn súng hơi, viên đạn xuyên vào đầu.",
               "injury_region": "Ở đầu, phía trên tai phải.",
               "recent_head_trauma": "Có, khoảng 30 phút trước cháu bị bắn trúng đầu.",
               "visible_head_injury_sign": "Có một lỗ nhỏ trên da đầu, phía trên tai phải, rỉ máu.",
               "wound_present": "Có, một lỗ nhỏ trên da đầu.",
               "wound_type": "Vết đạn súng hơi xuyên vào.",
               "wound_location": "Ở đầu, phía trên tai phải.",
               "foreign_body_status": "Không thấy viên đạn rơi ra, chắc còn nằm bên trong.",
               "bleeding_present": "Có, chỗ lỗ nhỏ rỉ máu.",
               "bleeding_control_status": "Máu vẫn rỉ ra chậm.",
               "pain_present": "Có, cháu kêu đau chỗ bị bắn.",
               "post_trauma_awareness_change": "Cháu không ngất, tỉnh táo từ lúc bị bắn tới giờ.",
               "altered_mental_status_present": "Không, cháu vẫn tỉnh, nói chuyện bình thường.",
               "symptom_duration_bucket": "Mới khoảng 30 phút."},
      unknown={"wound_depth_category": "Lỗ nhỏ lắm, tôi không biết viên đạn vào sâu tới đâu."},
      tags=("adolescent", "caregiver", "negation", "null_unknown"),
      test="Đạn súng hơi xuyên vào da đầu trẻ 13 tuổi, chỉ thấy lỗ nhỏ rỉ máu, cháu tỉnh táo: cơ chế xuyên thấu vùng đầu đã "
           "đủ quyết định dù vết thương nhỏ, độ sâu chưa rõ và không có dấu hiệu thần kinh."),

    # ------------------------------------------------------------------ RETURN_INCOMPLETE: dấu hiệu đỏ ngoài corpus
    S("r104", "post_diarrhea_ascending_weakness", "Sau đợt tiêu chảy, tê yếu lan dần từ chân lên tay, không tự đi được",
      P(31, "Female", "SIBLING"),
      "Em gái tôi 31 tuổi, hai tuần trước bị tiêu chảy mấy ngày rồi khỏi. Từ hôm kia hai bàn chân em tê rần như kiến bò, "
      "rồi yếu dần lên bắp chân, đầu gối; hôm nay hai bàn tay cũng tê, cầm đũa không chặt, đứng dậy khỏi ghế phải có người "
      "đỡ, tự đi không nổi. Em không sốt, không đau đầu, không ngã hay va đập gì. Em vẫn thở bình thường, nói chuyện rõ.",
      {"focal_neurologic_symptoms": "WEAKNESS_OR_NUMBNESS", "symptom_onset": "GRADUAL", "symptom_trend": "WORSENING",
       "functional_status": "UNABLE_TO_AMBULATE", "fever_present": "NO", "headache_present": "NO", "trauma_present": "NO",
       "dyspnea_present": "NO", "gastrointestinal_symptom_present": "NO", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, concepts=("limb_weakness", "paresthesia", "gait_difficulty"), screen=QUIET,
      answers={"focal_neurologic_symptoms": "Hai chân em tê và yếu dần từ bàn chân lên tới đầu gối, hôm nay hai bàn tay "
                                            "cũng tê, cầm đũa không chặt.",
               "symptom_onset": "Từ từ, mỗi ngày yếu thêm một chút.",
               "symptom_trend": "Ngày càng nặng hơn, lan dần từ chân lên tay.",
               "functional_status": "Đứng dậy khỏi ghế phải có người đỡ, tự đi không nổi.",
               "fever_present": "Không, em không sốt.",
               "headache_present": "Không, em không đau đầu.",
               "trauma_present": "Không, em không ngã hay va đập gì.",
               "dyspnea_present": "Không, em vẫn thở bình thường.",
               "gastrointestinal_symptom_present": "Giờ em hết tiêu chảy rồi.",
               "symptom_duration_bucket": "Tê chân từ hôm kia, hôm nay thì lan lên tay."},
      review_concern=("Tê và yếu tăng dần đối xứng từ chân lên tay trong hai ngày, sau một đợt tiêu chảy, đã không tự đi "
                      "được: bệnh cảnh gợi ý tổn thương rễ thần kinh cấp, có thể lan tới cơ hô hấp, là tình huống nguy cơ "
                      "cao theo Decision Point B nên AHRQ sẽ xếp ESI 2. Corpus chỉ có tiêu chí tê yếu khi khởi phát đột "
                      "ngột hoặc đi kèm chóng mặt, chấn thương đầu, co giật; yếu hai bên tăng dần không khớp tiêu chí nào, "
                      "nên từ lời người nhà chỉ tính được RETURN_INCOMPLETE."),
      tags=("caregiver", "corpus_gap", "negation"),
      test="Tê yếu lan dần từ chân lên tay sau đợt tiêu chảy, không tự đi được nhưng chưa khó thở: corpus không có tiêu chí "
           "cho yếu hai bên tăng dần, agent phải chuyển nhân viên y tế ngay chứ không chờ tới khi khó thở."),
]
