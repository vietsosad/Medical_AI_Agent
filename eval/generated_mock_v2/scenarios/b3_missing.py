"""Nhóm MISSING_INFO, đợt 3: người kể không thể biết dữ kiện quyết định, hoặc đã nói đủ dù thiếu phần còn lại.

Vẫn hai kiểu ca như ``missing.py`` và ``b2_missing.py``:

- thiếu đúng dữ kiện quyết định -> kỳ vọng RETURN_INCOMPLETE (chuyển nhân viên y tế). Câu "không biết"
  nằm trong ``unknown``; không bao giờ được hiểu thành "không có", cũng không được tự hiểu thành "có".
- dữ kiện đã nêu đủ quyết định dù thiếu phần khác -> agent phải kết luận ngay, không đòi thêm số đo
  (tag ``decisive_despite_missing``).

Đợt 3 đổi nguồn của chữ "không biết": người kể là trẻ em, người cứu hộ, nhân viên ca đêm mới vào làm,
giáo viên, chủ lò gạch, chủ ghe đang ngoài biển, bạn cùng phòng trọ, nhân viên trung tâm bảo trợ; người
bệnh mù, sa sút trí tuệ, không nói được; máy đo báo lỗi hoặc không lên số; người kể chỉ nhìn qua camera;
không ai thấy con vật cắn, không ai nhìn thấy phân.

Quy ước riêng của tệp này:

- Như ``b2_missing.py``: run rét đang diễn ra ghi ở cả ``shivering_status`` lẫn ``chills_present``; ngón
  đổi màu do lạnh ghi bằng ``skin_appearance``, không ghi ``cyanosis_present`` là có vì đó không phải tím
  tái trung tâm.
- Tổn thương do lạnh ở ngón tay, ngón chân là than phiền ở chi, nên có thêm dữ kiện chi trên, chi dưới
  (vị trí, cảm giác, màu sắc) đúng như người kể tả.
"""

from __future__ import annotations

from eval.generated_mock_v2.spec import INCOMPLETE, MISSING, P, SCREEN_HIT as HIT, SCREEN_QUIET as QUIET, Spec


def S(key: str, family: str, title: str, profile: dict, opening: str, facts: dict, intended, **kw) -> Spec:
    return Spec(case_id=key, family=family, group=MISSING, title=title, profile=profile,
                opening=opening, facts=facts, intended=intended, **kw)


SPECS = [
    # ------------------------------------------------------------------ tiết niệu
    S("x61", "blind_grandfather_clots_child_reporter", "Cháu lớp 7 kể hộ ông nội mù: tiểu ra cục máu, tia nhỏ",
      P(78, "Male", "OTHER", chronic=("Mù hai mắt do tăng nhãn áp", "Phì đại tiền liệt tuyến")),
      "Cháu chào ạ, cháu học lớp 7, bố mẹ cháu đi làm xa nên cháu ở với ông nội. Ông cháu bị mù hai mắt. Lúc nãy "
      "ông đi tiểu vào bô, cháu thấy nước tiểu đỏ, có mấy cục máu đông. Ông bảo tiểu khó, tia nhỏ, ra ít hơn hẳn mọi "
      "khi, tức ở bụng dưới ngay trên chỗ đi tiểu. Nhà có máy đo huyết áp nhưng cháu không biết đo ạ.",
      {"urinary_symptom_present": "YES", "urine_appearance": "BLOOD_CLOTS", "voiding_ability": "REDUCED",
       "genitourinary_pain_present": "YES", "genitourinary_pain_location": "SUPRAPUBIC", "pain_present": "YES"},
      2, concepts=("blood_clots_in_urine", "weak_urine_stream"), screen=QUIET,
      answers={"urinary_symptom_present": "Dạ có, nước tiểu của ông đỏ, có cục máu, ông tiểu khó ạ.",
               "urine_appearance": "Nước tiểu đỏ, có mấy cục máu đông ạ.",
               "voiding_ability": "Ông bảo tia nhỏ, ra ít hơn hẳn mọi khi ạ.",
               "genitourinary_pain_present": "Dạ có, ông kêu tức ở bụng dưới ạ.",
               "genitourinary_pain_location": "Ông kêu tức ở bụng dưới, ngay trên chỗ đi tiểu ạ.",
               "pain_present": "Dạ có, ông kêu tức ở bụng dưới ạ."},
      unknown={"symptom_duration_bucket": "Cháu hỏi thì ông bảo không nhớ bắt đầu từ lúc nào ạ.",
               "pain_severity": "Cháu hỏi ông đau mấy điểm thì ông bảo không biết chấm thế nào ạ.",
               "systolic_bp": "Nhà có máy đo huyết áp nhưng cháu không biết đo ạ."},
      confirmation="Dạ đúng rồi ạ.",
      tags=("older_adult", "collateral_history", "minor_narrator", "comorbidity", "missing_vitals",
            "decisive_despite_missing"),
      test="Người kể là trẻ em, không đo được huyết áp, không biết thời điểm bắt đầu và điểm đau: tiểu ra cục máu kèm "
           "tiểu ít, tia nhỏ đã đủ quyết định; agent không được đòi thêm số đo hay chờ người lớn về."),
    S("x62", "night_coach_motion_pill_retention", "Bí tiểu trên xe khách đêm: chỉ ra vài giọt, đau 8/10, không có máy đo",
      P(69, "Male", "PARENT", chronic=("Phì đại tiền liệt tuyến",), meds=("Tamsulosin 0,4 mg mỗi tối",)),
      "Tôi đang đi xe khách giường nằm chuyến đêm cùng bố, bố tôi 69 tuổi bị phì đại tiền liệt tuyến. Lúc lên xe bố "
      "có uống một viên thuốc chống say xe mua ở bến, tôi không nhớ tên. Từ nửa đêm tới giờ, chừng bốn tiếng, bố buồn "
      "tiểu căng mà xe dừng ở trạm thì rặn mãi cũng chỉ ra được vài giọt, căng đau ngay trên xương mu, bố bảo đau 8 "
      "trên 10. Trên xe không có máy đo gì, trời tối nên tôi không nhìn được mấy giọt đó màu gì.",
      {"urinary_symptom_present": "YES", "voiding_ability": "DROPS_ONLY", "genitourinary_pain_present": "YES",
       "genitourinary_pain_location": "SUPRAPUBIC", "pain_present": "YES", "pain_severity": 8,
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("urinary_retention",), screen=QUIET,
      answers={"urinary_symptom_present": "Có, bố buồn tiểu căng mà chỉ ra được vài giọt.",
               "voiding_ability": "Rặn mãi cũng chỉ ra được vài giọt.",
               "genitourinary_pain_present": "Có, bố kêu căng đau ngay trên xương mu.",
               "genitourinary_pain_location": "Căng đau ngay trên xương mu.",
               "pain_present": "Có, bố kêu căng đau ngay trên xương mu.",
               "pain_severity": "Bố bảo đau 8 trên 10.",
               "symptom_duration_bucket": "Từ nửa đêm tới giờ, chừng bốn tiếng."},
      unknown={"urine_appearance": "Trời tối, mấy giọt đó lại nhỏ xuống rãnh nên tôi không nhìn được màu.",
               "systolic_bp": "Trên xe không có máy đo huyết áp."},
      tags=("older_adult", "caregiver", "comorbidity", "missing_vitals", "decisive_despite_missing", "travel_setting"),
      test="Đang trên xe khách, không có máy đo, không nhìn được màu nước tiểu: chỉ tiểu được vài giọt kèm đau 8/10 đã "
           "đủ quyết định; agent không được chờ tới bến hay đòi thêm số đo."),
    S("x63", "kidney_donor_flank_no_urine", "Người đã hiến một quả thận đau hông lưng, từ tối qua không có nước tiểu",
      P(54, "Female", chronic=("Chỉ còn một thận do đã hiến thận cho em trai",), allergies=("Dị ứng ibuprofen",)),
      "Tôi 54 tuổi, chỉ còn một quả thận vì đã hiến cho em trai cách đây tám năm. Từ 4 giờ sáng tôi đau quặn hông lưng "
      "bên phải, chừng 6 trên 10, nôn hai lần. Từ tối qua tới giờ tôi không đi tiểu được giọt nào mà cũng không thấy "
      "buồn tiểu. Nhiệt kế nhà hết pin nên tôi chưa đo được có sốt không, nhà cũng không có máy đo huyết áp.",
      {"genitourinary_pain_present": "YES", "genitourinary_pain_location": "FLANK",
       "genitourinary_pain_laterality": "RIGHT", "pain_present": "YES", "pain_severity": 6,
       "urinary_symptom_present": "YES", "voiding_ability": "NO_URINE_WITHOUT_URGE", "urine_output_status": "NONE",
       "urination_status": "VERY_LITTLE_OR_NONE", "vomiting_present": "YES", "vomiting_frequency": "FEW_TIMES",
       "gastrointestinal_symptom_present": "YES", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("flank_pain", "anuria"), screen=QUIET,
      answers={"genitourinary_pain_present": "Có, tôi đau quặn hông lưng bên phải.",
               "genitourinary_pain_location": "Đau ở hông lưng.",
               "genitourinary_pain_laterality": "Bên phải.",
               "pain_present": "Có, tôi đau quặn hông lưng bên phải.",
               "pain_severity": "Chừng 6 trên 10.",
               "urinary_symptom_present": "Có, từ tối qua tới giờ tôi không đi tiểu được giọt nào.",
               "voiding_ability": "Không tiểu được giọt nào, mà cũng không thấy buồn tiểu.",
               "urine_output_status": "Từ tối qua tới giờ không có giọt nước tiểu nào.",
               "urination_status": "Từ tối qua tới giờ tôi không đi tiểu lần nào.",
               "vomiting_present": "Có, tôi nôn hai lần.",
               "vomiting_frequency": "Nôn hai lần.",
               "gastrointestinal_symptom_present": "Có, tôi nôn hai lần.",
               "symptom_duration_bucket": "Tôi đau từ 4 giờ sáng tới giờ."},
      unknown={"temperature": "Nhiệt kế nhà hết pin nên tôi chưa đo được.",
               "fever_present": "Tôi chưa đo được nên không biết có sốt hay không.",
               "systolic_bp": "Nhà tôi không có máy đo huyết áp."},
      tags=("comorbidity", "single_kidney", "missing_vitals", "decisive_despite_missing"),
      test="Không đo được nhiệt độ và huyết áp: đau hông lưng kèm không có nước tiểu mà không buồn tiểu đã đủ quyết "
           "định; agent không được chờ biết có sốt hay không rồi mới kết luận."),
    # ------------------------------------------------------------- lạnh, hạ thân nhiệt
    S("x64", "flood_rooftop_night_elder_rescue", "Cụ bà bám mái nhà cả đêm lũ: 34,4 độ, mạch 116, không có máy đo huyết áp",
      P(72, "Female", "OTHER"),
      "Tui ở đội cứu hộ tình nguyện, vừa đưa được một bà cụ 72 tuổi từ mái nhà xuống thuyền. Bà bám trên mái tôn cả "
      "đêm qua giữa mưa lũ, áo quần ướt hết, chừ vẫn run cầm cập. Nhiệt kế điện tử trong túi sơ cứu đo nách được 34,4 "
      "độ, máy kẹp ngón tay báo mạch 116, SpO2 95%. Bà vẫn tỉnh, hỏi chi trả lời nấy nhưng giọng run. Người nhà bà đi "
      "sơ tán từ trước nên tui không biết bà có bệnh chi, uống thuốc chi. Túi sơ cứu không có máy đo huyết áp.",
      {"cold_exposure_present": "YES", "thermal_exposure_present": "YES", "thermal_exposure_type": "WET_COLD_ENVIRONMENT",
       "thermal_exposure_duration": "MORE_THAN_SIX_HOURS", "shivering_status": "PRESENT", "chills_present": "YES", "associated_systemic_symptoms": "CHILLS",
       "temperature": 34.4, "heart_rate": 116, "spo2": 95, "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("hypothermia", "wet_clothing"),
      answers={"cold_exposure_present": "Có, bà bám mái nhà cả đêm trong mưa lũ, áo quần ướt hết.",
               "thermal_exposure_present": "Có, bà ở ngoài mưa lạnh cả đêm.",
               "thermal_exposure_type": "Mưa lũ, gió lạnh, áo quần ướt hết.",
               "thermal_exposure_duration": "Cả đêm qua.",
               "shivering_status": "Chừ bà vẫn run cầm cập.",
               "associated_systemic_symptoms": "Bà run cầm cập vì lạnh, còn sốt hay không thì tui chưa thấy.",
               "chills_present": "Có, chừ bà vẫn run cầm cập.",
               "temperature": "Nhiệt kế điện tử đo nách được 34,4 độ.",
               "heart_rate": "Máy kẹp ngón tay báo mạch 116.",
               "spo2": "Máy kẹp ngón tay báo SpO2 95%.",
               "altered_mental_status_present": "Không, bà vẫn tỉnh, hỏi chi trả lời nấy, chỉ có giọng run.",
               "symptom_duration_bucket": "Từ đêm qua tới chừ."},
      unknown={"systolic_bp": "Túi sơ cứu không có máy đo huyết áp.",
               "trauma_present": "Bà không kể có bị va đập chi không, tui cũng chưa xem kỹ được vì đang ở trên thuyền."},
      tags=("older_adult", "collateral_history", "environmental", "missing_vitals", "decisive_despite_missing",
            "dialect", "disaster_setting"),
      test="Người kể là người cứu hộ, không biết tiền sử, không có máy đo huyết áp: thân nhiệt 34,4 độ kèm mạch 116 đã "
           "đủ quyết định; agent không được chờ huyết áp hay tiền sử."),
    S("x65", "nursing_home_night_shift_cold_low_bp", "Nhân viên ca đêm nhà dưỡng lão: cụ ông 35,4 độ, huyết áp 84/50",
      P(84, "Male", "OTHER", chronic=("Bệnh Parkinson", "Nhồi máu não cũ"),
        meds=("Levodopa/benserazid 125 mg ba lần mỗi ngày", "Atorvastatin 20 mg mỗi tối")),
      "Em làm ca đêm ở một nhà dưỡng lão tư nhân, mới vào làm được năm hôm. Lúc 2 giờ sáng em đi phòng thì thấy một cụ "
      "ông 84 tuổi người lạnh toát, da tái. Em đo nhiệt kế điện tử được 35,4 độ, máy đo huyết áp báo 84/50, mạch 98. "
      "Cụ bị Parkinson, nói nhỏ và chậm, em hỏi gì cụ cũng chỉ ậm ừ. Ca ngày không bàn giao gì nên em không biết cụ như "
      "thế từ bao giờ, cũng không biết bình thường cụ tỉnh táo cỡ nào.",
      {"temperature": 35.4, "systolic_bp": 84, "diastolic_bp": 50, "heart_rate": 98, "fever_present": "NO"},
      2, concepts=("hypothermia", "hypotension"),
      answers={"temperature": "Nhiệt kế điện tử đo được 35,4 độ ạ.",
               "systolic_bp": "Máy đo huyết áp báo 84/50 ạ.",
               "diastolic_bp": "Số dưới là 50 ạ.",
               "heart_rate": "Máy báo mạch 98 ạ.",
               "fever_present": "Dạ không, người cụ lạnh toát."},
      unknown={"altered_mental_status_present": "Em mới vào làm nên không biết bình thường cụ thế nào, không so được ạ.",
               "symptom_duration_bucket": "Ca ngày không bàn giao gì nên em không biết cụ bị từ lúc nào ạ.",
               "urine_output_status": "Em chưa kịp xem bỉm của cụ ạ."},
      tags=("older_adult", "collateral_history", "communication_barrier", "comorbidity", "unknown_onset",
            "decisive_despite_missing", "institutional_care"),
      test="Người kể mới vào làm, không biết nền ý thức và thời điểm khởi phát: thân nhiệt 35,4 độ kèm huyết áp 84 đã "
           "đủ quyết định; agent không được coi 'không sốt' là đáng yên tâm."),
    S("x66", "highland_frost_herder_purple_digits", "Cụ ông vùng cao kẹt trên núi đêm băng giá: ngón tay, ngón chân tím bầm, tê cứng",
      P(64, "Male", "PARENT"),
      "Bố tôi 64 tuổi, chiều qua lên núi tìm trâu bị lạc rồi kẹt lại trên đó cả đêm, đêm qua trên bản có băng giá. Sáng "
      "nay mọi người mới tìm thấy, đưa về nhà sưởi lửa. Các đầu ngón tay hai bàn tay và mấy ngón chân của bố tím bầm, bố "
      "bảo tê cứng, không thấy đau. Bố vẫn tỉnh, nói chuyện được, người còn run, môi không tím. Nhà không có nhiệt kế.",
      {"cold_exposure_present": "YES", "thermal_exposure_present": "YES", "thermal_exposure_type": "COLD_AIR",
       "thermal_exposure_duration": "MORE_THAN_SIX_HOURS", "thermal_injury_body_area": "MULTIPLE_AREAS",
       "skin_appearance": "BLUE_PURPLE", "skin_sensation": "NUMB", "shivering_status": "PRESENT", "chills_present": "YES", "associated_systemic_symptoms": "CHILLS",
       "cyanosis_present": "NO", "altered_mental_status_present": "NO", "pain_present": "NO",
       "upper_extremity_problem_present": "YES", "upper_extremity_injury_location": "FINGER",
       "upper_extremity_injury_mechanism": "OTHER", "upper_extremity_sensory_change": "NUMBNESS",
       "distal_color_temperature_change": "CYANOTIC", "lower_extremity_problem_present": "YES",
       "lower_extremity_injury_location": "TOE", "distal_limb_symptoms": "MULTIPLE",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("cold_exposure", "skin_discoloration", "skin_numbness"), screen=QUIET,
      answers={"cold_exposure_present": "Có, bố kẹt trên núi cả đêm, đêm qua có băng giá.",
               "thermal_exposure_present": "Có, bố ở ngoài trời rét cả đêm.",
               "thermal_exposure_type": "Ngoài trời trên núi, đêm có băng giá.",
               "thermal_exposure_duration": "Từ chiều qua tới sáng nay.",
               "thermal_injury_body_area": "Các đầu ngón của hai bàn tay và mấy ngón chân.",
               "skin_appearance": "Tím bầm.",
               "skin_sensation": "Bố bảo tê cứng.",
               "shivering_status": "Bố vẫn còn run.",
               "associated_systemic_symptoms": "Bố vẫn còn run vì lạnh.",
               "chills_present": "Có, bố vẫn còn run.",
               "cyanosis_present": "Môi bố không tím.",
               "altered_mental_status_present": "Không, bố vẫn tỉnh, nói chuyện được.",
               "pain_present": "Bố bảo không thấy đau, chỉ tê cứng.",
               "upper_extremity_problem_present": "Có, các đầu ngón tay hai bàn tay tím bầm, tê cứng.",
               "upper_extremity_injury_location": "Ở các đầu ngón tay.",
               "upper_extremity_injury_mechanism": "Không bị thương gì, là do rét cả đêm.",
               "upper_extremity_sensory_change": "Bố bảo các đầu ngón tê cứng.",
               "distal_color_temperature_change": "Các đầu ngón tay tím bầm.",
               "lower_extremity_problem_present": "Có, mấy ngón chân cũng tím bầm, tê cứng.",
               "lower_extremity_injury_location": "Ở mấy ngón chân.",
               "distal_limb_symptoms": "Mấy ngón chân vừa tê cứng vừa tím bầm.",
               "symptom_duration_bucket": "Từ đêm qua tới giờ."},
      unknown={"temperature": "Nhà không có nhiệt kế.",
               "systolic_bp": "Trong bản không nhà nào có máy đo huyết áp."},
      tags=("older_adult", "caregiver", "environmental", "missing_vitals", "decisive_despite_missing", "negation",
            "highland_setting"),
      test="Không có nhiệt kế, không có máy đo: ngón tay, ngón chân tím bầm và tê cứng sau một đêm băng giá đã đủ quyết "
           "định; agent không được đòi đo nhiệt, cũng không được ghi màu tím ở ngón thành tím tái trung tâm."),
    S("x67", "boarding_student_frost_walk_waxy_digits", "Học sinh vùng cao đi bộ tới trường giữa sương muối: ngón trắng như sáp, kém cảm giác",
      P(13, "Female", "OTHER"),
      "Tôi là giáo viên ở một điểm trường vùng cao. Sáng nay trời có sương muối, một em học sinh nữ 13 tuổi đi bộ gần "
      "ba tiếng tới trường, chỉ đi dép nhựa, không có găng tay. Tới lớp thì mấy ngón chân và các đầu ngón tay của em "
      "trắng bệch, cứng như sáp, em bảo sờ vào chỉ thấy lờ mờ. Em vẫn tỉnh, nói chuyện được, người hơi run. Điểm trường "
      "không có nhiệt kế, bố mẹ em lên nương nên chưa gọi được.",
      {"cold_exposure_present": "YES", "thermal_exposure_present": "YES", "thermal_exposure_type": "COLD_AIR",
       "thermal_exposure_duration": "TWO_TO_SIX_HOURS", "thermal_injury_body_area": "MULTIPLE_AREAS",
       "skin_appearance": "WAXY", "skin_sensation": "REDUCED", "shivering_status": "PRESENT", "chills_present": "YES", "associated_systemic_symptoms": "CHILLS",
       "altered_mental_status_present": "NO", "upper_extremity_problem_present": "YES",
       "upper_extremity_injury_location": "FINGER", "upper_extremity_injury_mechanism": "OTHER",
       "upper_extremity_sensory_change": "NUMBNESS", "distal_color_temperature_change": "PALE",
       "lower_extremity_problem_present": "YES", "lower_extremity_injury_location": "TOE",
       "distal_limb_symptoms": "MULTIPLE", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("cold_exposure", "upper_extremity_pallor", "lower_extremity_numbness"), screen=QUIET,
      answers={"cold_exposure_present": "Có, em đi bộ gần ba tiếng giữa sương muối.",
               "thermal_exposure_present": "Có, em đi ngoài trời rét gần ba tiếng.",
               "thermal_exposure_type": "Ngoài trời rét, có sương muối.",
               "thermal_exposure_duration": "Gần ba tiếng.",
               "thermal_injury_body_area": "Mấy ngón chân và các đầu ngón tay.",
               "skin_appearance": "Trắng bệch, cứng như sáp.",
               "skin_sensation": "Em bảo sờ vào chỉ thấy lờ mờ.",
               "shivering_status": "Em vẫn hơi run.",
               "associated_systemic_symptoms": "Em vẫn hơi run vì lạnh.",
               "chills_present": "Có, em vẫn hơi run.",
               "altered_mental_status_present": "Không, em vẫn tỉnh, nói chuyện được.",
               "upper_extremity_problem_present": "Có, các đầu ngón tay của em trắng bệch, sờ vào chỉ thấy lờ mờ.",
               "upper_extremity_injury_location": "Ở các đầu ngón tay.",
               "upper_extremity_injury_mechanism": "Không bị thương gì, là do đi ngoài trời rét.",
               "upper_extremity_sensory_change": "Em bảo sờ vào chỉ thấy lờ mờ.",
               "distal_color_temperature_change": "Các đầu ngón tay trắng bệch.",
               "lower_extremity_problem_present": "Có, mấy ngón chân của em trắng bệch, cứng như sáp.",
               "lower_extremity_injury_location": "Ở mấy ngón chân.",
               "distal_limb_symptoms": "Mấy ngón chân vừa trắng bệch vừa chỉ thấy lờ mờ khi sờ vào.",
               "symptom_duration_bucket": "Từ sáng sớm lúc em đi học tới giờ."},
      unknown={"temperature": "Điểm trường không có nhiệt kế.",
               "systolic_bp": "Ở đây không có máy đo huyết áp."},
      tags=("adolescent", "collateral_history", "environmental", "missing_vitals", "decisive_despite_missing",
            "school_setting"),
      test="Người kể là giáo viên, không có nhiệt kế, chưa gọi được bố mẹ: ngón trắng như sáp, kém cảm giác ở nhiều vùng "
           "sau gần ba tiếng đi ngoài trời rét đã đủ quyết định; agent không được coi em còn tỉnh, còn nói chuyện là đủ "
           "yên tâm."),
    # ------------------------------------------------------------------ bệnh do nóng
    S("x68", "brick_kiln_unloader_low_bp", "Thợ ra gạch trong lò nóng hơn bốn tiếng: ói, choáng, huyết áp 82/50, mạch 132",
      P(32, "Male", "OTHER"),
      "Tui là chủ lò gạch ở miền Tây. Thằng nhỏ làm công cho tui 32 tuổi, từ một giờ trưa vô lò ra gạch tới giờ hơn bốn "
      "tiếng, trong lò nóng hầm hập. Chừng nửa tiếng nay nó nằm vật ra, áo ướt đẫm mồ hôi, ói hai lần, kêu choáng, đứng "
      "lên là xây xẩm. Tui lấy máy đo huyết áp của tui đo cho nó được 82 trên 50, mạch 132. Nó vẫn tỉnh, hỏi gì trả lời "
      "đó. Ở lò hổng có nhiệt kế, nó mới lên làm mùa này nên tui hổng biết nó có bệnh gì.",
      {"thermal_exposure_present": "YES", "thermal_exposure_type": "ENCLOSED_HOT_SPACE",
       "thermal_exposure_duration": "TWO_TO_SIX_HOURS", "heat_exposure_present": "YES", "sweating_pattern": "INCREASED",
       "vomiting_present": "YES", "vomiting_frequency": "FEW_TIMES", "gastrointestinal_symptom_present": "YES",
       "dizziness_present": "YES", "dizziness_sensation": "LIGHTHEADED", "functional_status": "MARKEDLY_REDUCED",
       "systolic_bp": 82, "diastolic_bp": 50, "heart_rate": 132, "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("heat_exposure", "hypotension"),
      answers={"thermal_exposure_present": "Có, nó ở trong lò gạch nóng hầm hập.",
               "thermal_exposure_type": "Trong lò gạch, nóng hầm hập.",
               "thermal_exposure_duration": "Từ một giờ trưa tới giờ, hơn bốn tiếng.",
               "heat_exposure_present": "Có, trong lò nóng lắm.",
               "sweating_pattern": "Áo nó ướt đẫm mồ hôi.",
               "vomiting_present": "Có, nó ói hai lần.",
               "vomiting_frequency": "Ói hai lần.",
               "gastrointestinal_symptom_present": "Có, nó ói hai lần.",
               "dizziness_present": "Có, nó kêu choáng.",
               "dizziness_sensation": "Nó kêu choáng, đứng lên là xây xẩm.",
               "functional_status": "Nó nằm vật ra, hổng gượng dậy nổi.",
               "systolic_bp": "Máy đo được 82 trên 50.",
               "diastolic_bp": "Số dưới là 50.",
               "heart_rate": "Máy báo mạch 132.",
               "altered_mental_status_present": "Hổng, nó vẫn tỉnh, hỏi gì trả lời đó.",
               "symptom_duration_bucket": "Mới chừng nửa tiếng nay."},
      unknown={"temperature": "Ở lò hổng có nhiệt kế.",
               "urine_output_status": "Tui hổng theo dõi chuyện nó đi tiểu."},
      tags=("occupational", "environmental", "dialect", "collateral_history", "missing_vitals",
            "decisive_despite_missing"),
      test="Người kể là chủ lò, không có nhiệt kế, không biết tiền sử người làm công: huyết áp 82, mạch 132 sau nhiều giờ "
           "trong lò nóng đã đủ quyết định; agent không được đòi đo nhiệt rồi mới kết luận."),
    S("x69", "rooftop_bonsai_beta_blocker_heat", "Cụ ông dùng thuốc chẹn beta tỉa cây giữa nắng: 39,6 độ, huyết áp 86, mạch 96",
      P(76, "Male", "PARENT", chronic=("Tăng huyết áp", "Đau thắt ngực ổn định"), allergies=("Dị ứng penicilin",),
        meds=("Bisoprolol 5 mg mỗi sáng", "Amlodipin 5 mg mỗi sáng")),
      "Bố tôi 76 tuổi, trưa nay lên sân thượng tỉa cây cảnh giữa nắng gắt. Tôi đi chợ về thấy bố ngồi gục ở chân cầu "
      "thang, người nóng hầm hập, áo ướt mồ hôi, kêu mệt lả. Nhiệt kế đo tai được 39,6 độ, máy đo huyết áp điện tử báo "
      "86/52, mạch 96. Bố vẫn trả lời đúng, nói chuyện bình thường. Tôi đi vắng từ sáng nên không biết bố ở trên đó bao "
      "lâu, hỏi thì bố bảo không nhớ.",
      {"thermal_exposure_present": "YES", "thermal_exposure_type": "DIRECT_SUN", "heat_exposure_present": "YES",
       "sweating_pattern": "INCREASED", "temperature": 39.6, "fever_present": "YES",
       "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS", "systolic_bp": 86, "diastolic_bp": 52, "heart_rate": 96,
       "altered_mental_status_present": "NO"},
      2, concepts=("heat_exposure", "fatigue"),
      answers={"thermal_exposure_present": "Có, bố ở trên sân thượng giữa nắng gắt.",
               "thermal_exposure_type": "Tỉa cây ngoài sân thượng dưới nắng gắt.",
               "heat_exposure_present": "Có, bố ở ngoài nắng gắt giữa trưa.",
               "sweating_pattern": "Áo bố ướt mồ hôi.",
               "temperature": "Nhiệt kế đo tai được 39,6 độ.",
               "fever_present": "Có, người bố nóng hầm hập, đo được 39,6 độ.",
               "associated_systemic_symptoms": "Người bố nóng hầm hập, bố kêu mệt lả.",
               "systolic_bp": "Máy báo 86/52.",
               "diastolic_bp": "Số dưới là 52.",
               "heart_rate": "Máy báo mạch 96.",
               "altered_mental_status_present": "Không, bố vẫn trả lời đúng, nói chuyện bình thường."},
      unknown={"thermal_exposure_duration": "Tôi đi vắng từ sáng, hỏi thì bố bảo không nhớ đã ở trên sân thượng bao lâu.",
               "symptom_duration_bucket": "Tôi về mới thấy bố như vậy, không biết bố mệt từ lúc nào."},
      tags=("older_adult", "caregiver", "comorbidity", "environmental", "unknown_onset", "decisive_despite_missing",
            "masked_tachycardia"),
      test="Không biết đã ở ngoài nắng bao lâu, mạch không nhanh ở người đang dùng thuốc chẹn beta: thân nhiệt 39,6 kèm "
           "huyết áp 86 sau phơi nắng đã đủ quyết định; agent không được lấy mạch 96 để hạ mức."),
    S("x70", "pe_class_1500m_noon_runner", "Học sinh 16 tuổi chạy 1.500 mét giữa trưa nắng: 39,7 độ, thở 34 lần/phút",
      P(16, "Male", "OTHER"),
      "Tôi là giáo viên thể dục. Trưa nay lớp 10 kiểm tra chạy 1.500 mét ngoài sân nắng chang chang, cả lớp đứng ngoài "
      "sân hơn một tiếng. Chừng hai mươi phút trước, một em nam 16 tuổi chạy xong thì ngồi bệt xuống gốc cây, người nóng "
      "ran, mặt đỏ, thở rất nhanh, kêu mệt, hụt hơi, buồn nôn nhưng chưa nôn. Tôi đếm được 34 lần thở một phút, nhiệt kế "
      "ở phòng y tế đo được 39,7 độ. Em vẫn trả lời được. Phòng y tế không có máy đo huyết áp, tôi cũng không quen bắt "
      "mạch.",
      {"thermal_exposure_present": "YES", "thermal_exposure_type": "DIRECT_SUN",
       "thermal_exposure_duration": "THIRTY_MINUTES_TO_TWO_HOURS", "heat_exposure_present": "YES",
       "skin_appearance": "RED", "temperature": 39.7, "fever_present": "YES", "respiratory_rate": 34,
       "dyspnea_present": "YES", "dyspnea_context": "AT_REST", "respiratory_distress_symptoms": "AT_REST",
       "cardiorespiratory_symptom_present": "YES", "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS",
       "gastrointestinal_symptom_present": "YES", "vomiting_present": "NO", "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("feeling_overheated", "tachypnea"),
      answers={"thermal_exposure_present": "Có, em chạy giữa trưa nắng chang chang.",
               "thermal_exposure_type": "Chạy ngoài sân dưới nắng chang chang.",
               "thermal_exposure_duration": "Cả lớp đứng ngoài sân nắng hơn một tiếng.",
               "heat_exposure_present": "Có, ngoài sân nắng chang chang.",
               "skin_appearance": "Mặt em đỏ.",
               "temperature": "Nhiệt kế phòng y tế đo được 39,7 độ.",
               "fever_present": "Có, người em nóng ran, đo được 39,7 độ.",
               "respiratory_rate": "Tôi đếm được 34 lần thở một phút.",
               "dyspnea_present": "Có, em kêu hụt hơi.",
               "dyspnea_context": "Em ngồi nghỉ rồi mà vẫn hụt hơi.",
               "respiratory_distress_symptoms": "Ngồi nghỉ rồi mà em vẫn thở rất nhanh, kêu hụt hơi.",
               "cardiorespiratory_symptom_present": "Có, em thở rất nhanh, kêu hụt hơi.",
               "associated_systemic_symptoms": "Người em nóng ran, em kêu mệt.",
               "gastrointestinal_symptom_present": "Có, em buồn nôn.",
               "vomiting_present": "Em chưa nôn.",
               "altered_mental_status_present": "Không, em vẫn trả lời được.",
               "symptom_duration_bucket": "Mới chừng hai mươi phút."},
      unknown={"heart_rate": "Tôi không quen bắt mạch nên không đếm được.",
               "systolic_bp": "Phòng y tế không có máy đo huyết áp."},
      tags=("adolescent", "collateral_history", "environmental", "missing_vitals", "decisive_despite_missing",
            "school_setting"),
      test="Người kể là giáo viên, không đo được mạch và huyết áp: thân nhiệt 39,7 kèm thở 34 lần/phút sau chạy dưới nắng "
           "đã đủ quyết định; agent không được đòi mạch hay huyết áp rồi mới kết luận."),
    S("x71", "home_camera_power_cut_mother_on_floor", "Con ở cơ quan xem camera thấy mẹ 79 tuổi nằm dưới sàn phòng mái tôn khi mất điện",
      P(79, "Female", "PARENT", chronic=("Suy tim", "Tăng huyết áp"),
        meds=("Furosemid 40 mg mỗi sáng", "Amlodipin 5 mg mỗi sáng")),
      "Tôi đang ở cơ quan, mở camera trong nhà thì thấy mẹ tôi 79 tuổi nằm nghiêng dưới sàn cạnh giường. Khu nhà tôi mất "
      "điện từ 11 giờ trưa, giờ gần 3 giờ chiều, phòng mái tôn nóng như lò, quạt không chạy. Tôi gọi qua loa camera thì "
      "mẹ có giơ tay vẫy nhưng không ngồi dậy được, tôi không nghe rõ mẹ nói gì. Tôi không biết mẹ ngã hay tự nằm xuống, "
      "nằm đó từ lúc nào. Tôi đã nhờ hàng xóm sang, đang chờ.",
      {"thermal_exposure_present": "YES", "thermal_exposure_type": "ENCLOSED_HOT_SPACE",
       "thermal_exposure_duration": "TWO_TO_SIX_HOURS", "heat_exposure_present": "YES",
       "functional_status": "UNABLE_TO_AMBULATE"},
      INCOMPLETE, concepts=("heat_exposure", "generalized_weakness"),
      answers={"thermal_exposure_present": "Có, mất điện từ trưa, phòng mái tôn nóng như lò.",
               "thermal_exposure_type": "Trong phòng mái tôn, mất điện, quạt không chạy.",
               "thermal_exposure_duration": "Mất điện từ 11 giờ trưa, giờ gần 3 giờ chiều rồi.",
               "heat_exposure_present": "Có, phòng nóng như lò vì mất điện.",
               "functional_status": "Mẹ không tự ngồi dậy được."},
      unknown={"syncope_present": "Tôi chỉ nhìn qua camera nên không biết mẹ có ngất hay không.",
               "trauma_present": "Tôi không thấy lúc mẹ nằm xuống nên không biết mẹ có bị ngã không.",
               "altered_mental_status_present": "Qua loa camera tôi không nghe rõ mẹ nói gì nên không biết mẹ có tỉnh táo như "
                                                "mọi khi không.",
               "symptom_duration_bucket": "Tôi mở camera ra thì đã thấy mẹ nằm đó rồi, không biết từ lúc nào.",
               "temperature": "Ở nhà không có ai đo cho mẹ.",
               "sweating_pattern": "Camera nhìn không rõ nên tôi không biết mẹ có ra mồ hôi không."},
      review_concern="Người 79 tuổi suy tim đang dùng thuốc lợi tiểu, nằm dưới sàn không tự dậy được trong phòng nóng nhiều "
                     "giờ, không rõ có ngất, có ngã hay có lơ mơ: theo Decision Point B đây là tình huống nguy cơ cao, nên xếp "
                     "ít nhất ESI 2; corpus cần sinh hiệu hoặc dữ kiện ngất mà người kể ở xa không biết.",
      tags=("older_adult", "caregiver_remote", "comorbidity", "environmental", "unknown_onset", "unknown_mechanism",
            "missing_vitals", "null_unknown", "camera_observation"),
      test="Người kể chỉ nhìn qua camera: không biết có ngất, có ngã, có lơ mơ hay không và không có sinh hiệu; agent không "
           "được coi việc mẹ còn giơ tay là ổn mà phải chuyển nhân viên y tế ngay."),
    # ------------------------------------------------------- ngoài biển, vết cắn ban đêm
    S("x72", "lobster_diver_fast_ascent_leg_numbness", "Thợ lặn ống hơi ngoi lên nhanh, đột ngột tê yếu hai chân trên ghe còn xa bờ",
      P(29, "Male", "OTHER"),
      "Tui là chủ ghe lặn bắt tôm hùm. Thằng em lặn ống hơi trên ghe tui 29 tuổi, hôm nay lặn mấy chục lần, lần cuối nó "
      "ngoi lên nhanh quá. Mới lên ghe chừng mười lăm phút thì nó kêu hai chân tê rần, đột ngột yếu hẳn, đứng hổng nổi. "
      "Nó vẫn tỉnh, nói chuyện được, hổng khó thở. Ghe còn cách bờ hơn hai tiếng, trên ghe hổng có máy đo gì hết.",
      {"focal_neurologic_symptoms": "WEAKNESS_OR_NUMBNESS", "symptom_onset": "SUDDEN",
       "lower_extremity_problem_present": "YES", "lower_extremity_injury_location": "MULTIPLE",
       "weight_bearing_ability": "UNABLE", "distal_limb_symptoms": "MULTIPLE", "functional_status": "UNABLE_TO_AMBULATE",
       "altered_mental_status_present": "NO", "dyspnea_present": "NO", "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("diving_injury", "lower_extremity_weakness", "lower_extremity_numbness"), screen=QUIET,
      # Hoà điểm với esi_2_sudden_headache_weakness_numbness (thắng theo chữ cái) dù người bệnh không hề đau đầu.
      primary_atom="esi_2_sudden_sensory_loss",
      answers={"focal_neurologic_symptoms": "Hai chân nó tê rần, yếu hẳn, đứng hổng nổi.",
               "symptom_onset": "Đột ngột, đang ngồi trên ghe thì hai chân tê rần.",
               "lower_extremity_problem_present": "Có, hai chân nó tê rần, đứng hổng nổi.",
               "lower_extremity_injury_location": "Cả hai chân.",
               "weight_bearing_ability": "Nó đứng hổng nổi.",
               "distal_limb_symptoms": "Hai chân vừa tê rần vừa yếu.",
               "functional_status": "Nó hổng đứng dậy đi được.",
               "altered_mental_status_present": "Hổng, nó vẫn tỉnh, nói chuyện được.",
               "dyspnea_present": "Hổng, nó thở bình thường.",
               "symptom_duration_bucket": "Mới chừng mười lăm phút."},
      unknown={"systolic_bp": "Trên ghe hổng có máy đo huyết áp.",
               "heart_rate": "Tui hổng biết bắt mạch, trên ghe cũng hổng có máy.",
               "voiding_ability": "Từ lúc lên ghe nó chưa đi tiểu nên tui hổng biết."},
      tags=("occupational", "environmental", "dialect", "collateral_history", "missing_vitals", "decisive_despite_missing",
            "remote_location"),
      test="Đang ngoài biển, không có máy đo, không ai biết độ sâu và thời gian lặn: tê yếu hai chân khởi phát đột ngột sau "
           "khi ngoi lên đã đủ quyết định; agent không được chờ vào bờ hay đòi sinh hiệu."),
    S("x73", "night_floor_bite_unseen_animal", "Bé gái ngủ dưới nền nhà bị con gì cắn lúc 3 giờ sáng, không ai thấy con vật",
      P(10, "Female", "CHILD"),
      "Con gái tôi 10 tuổi ngủ trải chiếu dưới nền nhà. Khoảng 3 giờ sáng cháu giật mình khóc, kêu có con gì cắn ở mu "
      "bàn tay trái. Bật đèn lên thì không thấy con gì, chỉ thấy hai chấm nhỏ như vết kim châm, cách nhau chừng một đốt "
      "ngón tay. Cháu bảo chỉ hơi nhói, chừng 2 điểm, tay không sưng. Giờ được chừng nửa tiếng, cháu vẫn tỉnh, nói chuyện "
      "bình thường. Nhà tôi sát ruộng, mùa này hay có rắn bò vào nên tôi lo lắm.",
      {"bite_or_sting_present": "YES", "wound_present": "YES", "wound_type": "BITE", "wound_location": "HAND_FINGER",
       "upper_extremity_problem_present": "YES", "upper_extremity_injury_location": "HAND",
       "upper_extremity_injury_mechanism": "OTHER", "pain_present": "YES", "pain_severity": 2,
       "swelling_present": "NO", "altered_mental_status_present": "NO", "symptom_duration_bucket": "UNDER_1_HOUR"},
      INCOMPLETE, concepts=("bite_wound", "snakebite"), screen=QUIET,
      answers={"bite_or_sting_present": "Có, cháu kêu bị con gì cắn ở mu bàn tay trái.",
               "wound_present": "Có, ở mu bàn tay trái có hai chấm nhỏ như vết kim châm.",
               "wound_type": "Là vết cắn, hai chấm nhỏ như vết kim châm.",
               "wound_location": "Ở mu bàn tay trái.",
               "upper_extremity_problem_present": "Có, cháu bị cắn ở mu bàn tay trái.",
               "upper_extremity_injury_location": "Ở mu bàn tay trái.",
               "upper_extremity_injury_mechanism": "Bị con gì đó cắn lúc đang ngủ.",
               "pain_present": "Cháu bảo chỉ hơi nhói.",
               "pain_severity": "Cháu bảo chừng 2 điểm.",
               "swelling_present": "Tay cháu không sưng.",
               "altered_mental_status_present": "Không, cháu vẫn tỉnh, nói chuyện bình thường.",
               "symptom_duration_bucket": "Mới chừng nửa tiếng."},
      unknown={"bite_source": "Bật đèn lên thì không thấy con gì nữa, tôi không biết con gì cắn.",
               "wound_depth_category": "Chỉ thấy hai chấm nhỏ, tôi không biết có sâu không."},
      review_concern="Vết cắn khi ngủ dưới nền nhà ban đêm, không thấy con vật, hai dấu chấm nhỏ ít đau, chưa sưng: rắn độc "
                     "thần kinh (như rắn cạp nia) cắn có thể gần như không đau lúc đầu rồi gây liệt sau nhiều giờ; theo "
                     "Decision Point B đây là tình huống nguy cơ cao, nên xếp ESI 2; corpus không có tiêu chí cho vết cắn nghi "
                     "rắn độc khi chưa có sưng đau.",
      tags=("pediatric", "caregiver", "unknown_mechanism", "null_unknown", "corpus_gap", "environmental"),
      test="Không ai thấy con gì cắn: vết cắn ban đêm ít đau, chưa sưng không được coi là vô hại; agent không được tự đoán "
           "loài vật mà phải chuyển nhân viên y tế."),
    # ------------------------------------------- thiếu sinh hiệu quyết định, máy đo hỏng
    S("x74", "island_pregnant_34w_headache_flashes", "Thai 34 tuần ở xã đảo nhức đầu, thấy đom đóm, phù chân, không đo được huyết áp",
      P(27, "Female"),
      "Em mang thai con đầu được 34 tuần. Từ chiều em nhức đầu vùng trán, chừng 6 trên 10, mắt thỉnh thoảng thấy đom "
      "đóm, hai bàn chân phù hơn mấy hôm trước. Em bé vẫn đạp bình thường, em không đau bụng, không ra máu. Nhà em ở xã "
      "đảo, trạm y tế tối đóng cửa, nhà lại không có máy đo huyết áp nên em không biết huyết áp bao nhiêu.",
      {"pregnancy_present": "YES", "pregnancy_status": "PREGNANT", "gestational_age_weeks": 34,
       "headache_present": "YES", "headache_location": "FRONTAL", "pain_present": "YES", "pain_severity": 6,
       "visual_disturbance_present": "YES", "visual_disturbance_pattern": "FLASHES",
       "focal_neurologic_symptoms": "VISION_CHANGE", "swelling_present": "YES", "swelling_location": "OTHER",
       "fetal_movement_status": "NORMAL", "abdominal_pain_present": "NO", "vaginal_bleeding_present": "NO",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("headache_in_pregnancy", "visual_disturbance_in_pregnancy", "swelling_in_pregnancy"),
      screen=QUIET,
      answers={"pregnancy_present": "Dạ có, em đang mang thai con đầu.",
               "pregnancy_status": "Em đang mang thai ạ.",
               "gestational_age_weeks": "Thai được 34 tuần ạ.",
               "headache_present": "Dạ có, em nhức đầu từ chiều.",
               "headache_location": "Nhức vùng trán ạ.",
               "pain_present": "Dạ có, em nhức đầu.",
               "pain_severity": "Chừng 6 trên 10 ạ.",
               "visual_disturbance_present": "Dạ có, mắt em thỉnh thoảng thấy đom đóm.",
               "visual_disturbance_pattern": "Thỉnh thoảng thấy đom đóm ạ.",
               "focal_neurologic_symptoms": "Mắt em thỉnh thoảng thấy đom đóm ạ.",
               "swelling_present": "Dạ có, hai bàn chân em phù hơn mấy hôm trước.",
               "swelling_location": "Phù ở hai bàn chân ạ.",
               "fetal_movement_status": "Em bé vẫn đạp bình thường ạ.",
               "abdominal_pain_present": "Dạ không, em không đau bụng.",
               "vaginal_bleeding_present": "Dạ không, em không ra máu.",
               "symptom_duration_bucket": "Em nhức đầu từ chiều tới giờ ạ."},
      unknown={"systolic_bp": "Nhà em không có máy đo huyết áp, trạm y tế xã tối đóng cửa rồi ạ.",
               "diastolic_bp": "Em không đo được nên không biết ạ."},
      review_concern="Thai 34 tuần nhức đầu kèm nhìn thấy đom đóm và phù chân tăng: theo Decision Point B đây là tình huống "
                     "nguy cơ cao (cần loại trừ tiền sản giật nặng), nên xếp ESI 2; corpus chỉ xếp được khi có huyết áp đo "
                     "được (tâm thu từ 160 hoặc tâm trương từ 110), mà thai phụ ở xã đảo không đo được.",
      tags=("pregnancy", "missing_vitals", "null_unknown", "remote_location"),
      test="Không có huyết áp: nhức đầu, thấy đom đóm và phù chân ở thai 34 tuần không được coi là chuyện thường của thai kỳ; "
           "agent phải chuyển nhân viên y tế chứ không được hẹn sáng mai đo huyết áp."),
    S("x75", "af_palpitations_devices_show_errors", "Cụ bà rung nhĩ hồi hộp, choáng; máy đo huyết áp báo lỗi, máy kẹp ngón nhảy số",
      P(69, "Female", "PARENT", chronic=("Rung nhĩ", "Tăng huyết áp"), allergies=("Dị ứng aspirin",),
        meds=("Rivaroxaban 20 mg mỗi tối", "Losartan 50 mg mỗi sáng")),
      "Mẹ tôi 69 tuổi bị rung nhĩ. Chiều nay đang nấu cơm thì tự nhiên mẹ kêu tim đập loạn xạ, không đều, người choáng "
      "choáng phải ngồi xuống, tới giờ đã mấy tiếng. Tôi đo bằng máy đo huyết áp điện tử ba lần thì cả ba lần máy đều báo "
      "lỗi, không ra số. Máy kẹp ngón tay thì số nhảy liên tục, tôi không đọc được. Mẹ vẫn tỉnh, nói chuyện được, không "
      "đau ngực, không khó thở.",
      {"palpitation_present": "YES", "palpitation_pattern": "IRREGULAR", "symptom_onset": "SUDDEN",
       "dizziness_present": "YES", "dizziness_sensation": "LIGHTHEADED", "cardiorespiratory_symptom_present": "YES",
       "chest_pain_present": "NO", "dyspnea_present": "NO", "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("palpitations", "irregular_heartbeat", "lightheadedness"), screen=QUIET,
      answers={"palpitation_present": "Có, mẹ kêu tim đập loạn xạ.",
               "palpitation_pattern": "Mẹ bảo tim đập loạn xạ, không đều.",
               "symptom_onset": "Đột ngột, đang nấu cơm thì tự nhiên bị.",
               "dizziness_present": "Có, mẹ kêu choáng choáng.",
               "dizziness_sensation": "Mẹ bảo choáng choáng, phải ngồi xuống.",
               "cardiorespiratory_symptom_present": "Có, mẹ kêu tim đập loạn xạ, không đều.",
               "chest_pain_present": "Không, mẹ không đau ngực.",
               "dyspnea_present": "Không, mẹ không khó thở.",
               "altered_mental_status_present": "Không, mẹ vẫn tỉnh, nói chuyện được.",
               "symptom_duration_bucket": "Từ chiều tới giờ, mấy tiếng rồi."},
      unknown={"heart_rate": "Máy kẹp ngón tay cứ nhảy số liên tục, tôi không đọc được con số nào.",
               "systolic_bp": "Máy đo huyết áp báo lỗi cả ba lần, không ra số.",
               "spo2": "Máy kẹp ngón nhảy số liên tục nên tôi không đọc được."},
      review_concern="Người 69 tuổi rung nhĩ, hồi hộp loạn nhịp khởi phát đột ngột kèm choáng phải ngồi xuống, máy đo không ra "
                     "số: có thể đang nhịp rất nhanh hoặc tụt huyết áp; nhiều điều dưỡng sẽ xếp ESI 2 theo Decision Point B "
                     "trước khi có sinh hiệu; corpus chỉ xếp được khi biết nhịp tim hoặc huyết áp.",
      tags=("older_adult", "caregiver", "comorbidity", "anticoagulant", "missing_vitals", "device_error", "null_unknown"),
      test="Máy đo báo lỗi và nhảy số: agent không được tự đọc ra một con số hay coi máy lỗi là sinh hiệu bình thường; thiếu "
           "nhịp tim và huyết áp thì phải chuyển nhân viên y tế."),
    S("x76", "dual_antiplatelet_unseen_stool_dizzy", "Cụ ông dùng hai thuốc chống kết tập, mệt, choáng khi đứng, mạch 112; không ai thấy phân",
      P(73, "Male", "PARENT", chronic=("Bệnh mạch vành đã đặt stent",),
        meds=("Aspirin 81 mg mỗi sáng", "Ticagrelor 90 mg sáng và tối")),
      "Bố tôi 73 tuổi, năm ngoái đặt stent mạch vành, đang uống hai loại thuốc chống đông máu. Hai hôm nay bố mệt, da "
      "xanh hơn, đứng dậy là choáng phải vịn tường. Bố bảo đi ngoài nhiều lần hơn mọi ngày nhưng đi xong giật nước luôn, "
      "hỏi phân màu gì, lỏng hay đặc thì bố không để ý. Tôi đo máy huyết áp được 98/60, mạch 112. Bố không nôn, không đau "
      "bụng.",
      {"associated_systemic_symptoms": "GENERAL_WEAKNESS", "dizziness_present": "YES",
       "dizziness_sensation": "LIGHTHEADED", "gastrointestinal_symptom_present": "YES", "vomiting_present": "NO",
       "abdominal_pain_present": "NO", "systolic_bp": 98, "diastolic_bp": 60, "heart_rate": 112,
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, concepts=("lightheadedness", "fatigue", "pallor"), screen=QUIET,
      answers={"associated_systemic_symptoms": "Bố mệt hai hôm nay.",
               "dizziness_present": "Có, bố đứng dậy là choáng.",
               "dizziness_sensation": "Đứng dậy là choáng, phải vịn tường.",
               "gastrointestinal_symptom_present": "Có, bố đi ngoài nhiều lần hơn mọi ngày.",
               "vomiting_present": "Không, bố không nôn.",
               "abdominal_pain_present": "Không, bố không đau bụng.",
               "systolic_bp": "Máy đo được 98/60.",
               "diastolic_bp": "Số dưới là 60.",
               "heart_rate": "Máy báo mạch 112.",
               "symptom_duration_bucket": "Hai hôm nay rồi."},
      unknown={"stool_appearance": "Bố đi xong giật nước luôn, không ai nhìn thấy phân màu gì.",
               "blood_in_stool_present": "Bố không để ý có máu hay không.",
               "diarrhea_present": "Bố không nhớ phân lỏng hay đặc."},
      review_concern="Người dùng hai thuốc chống kết tập tiểu cầu, mệt, da xanh, choáng khi đứng, mạch 112, huyết áp 98/60: "
                     "cần loại trừ chảy máu tiêu hoá; mạch trên 100 là sinh hiệu vùng nguy hiểm theo Decision Point D nên "
                     "AHRQ cân nhắc ESI 2; corpus chỉ xếp được khi biết phân đen hay có máu.",
      tags=("older_adult", "caregiver", "comorbidity", "anticoagulant", "null_unknown", "hidden_red_flag"),
      test="Không ai nhìn thấy phân: agent không được ghi là phân bình thường hay phân đen; mạch 112, huyết áp 98 chưa khớp "
           "tiêu chí nào nên phải chuyển nhân viên y tế."),
    # ------------------------------------------------- người bệnh không tự kể được
    S("x77", "concealed_teen_pregnancy_labor_roommate", "Bạn cùng phòng trọ kể hộ: nữ 16 tuổi giấu thai, gò bụng từng cơn, không biết tuổi thai",
      P(16, "Female", "OTHER"),
      "Em la ban cung phong tro cua mot ban nu 16 tuoi. Tu toi toi gio da may tieng ban ay dau bung tung con, bung go "
      "cung len roi lai mem. Gio ban ay moi thu nhan la co bau, giau gia dinh nen chua di kham thai lan nao, khong biet "
      "duoc bao nhieu tuan. Em khong biet canh xem cac con cach nhau bao lau. Ban ay chua ra mau, con co ra nuoc o duoi "
      "hay khong thi ban ay bao khong biet.",
      {"pregnancy_present": "YES", "pregnancy_status": "PREGNANT", "uterine_contractions_present": "YES",
       "abdominal_pain_present": "YES", "abdominal_pain_character": "CRAMPING", "pain_present": "YES",
       "gastrointestinal_symptom_present": "YES", "vaginal_bleeding_present": "NO", "symptom_trend": "INTERMITTENT",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("uterine_contractions", "adolescent_pregnancy"), screen=QUIET,
      answers={"pregnancy_present": "Da co, ban ay moi thu nhan la co bau.",
               "pregnancy_status": "Ban ay dang co bau a.",
               "uterine_contractions_present": "Da co, bung ban ay go cung len tung con roi lai mem.",
               "abdominal_pain_present": "Da co, ban ay dau bung tung con.",
               "abdominal_pain_character": "Dau tung con, bung go cung len roi lai mem.",
               "pain_present": "Da co, ban ay dau bung tung con.",
               "gastrointestinal_symptom_present": "Da co, ban ay dau bung tung con.",
               "symptom_trend": "Dau tung con, bung go cung len roi lai mem.",
               "vaginal_bleeding_present": "Da chua, ban ay chua ra mau.",
               "symptom_duration_bucket": "Tu toi toi gio, may tieng roi a."},
      unknown={"gestational_age_weeks": "Ban ay chua di kham lan nao nen khong biet duoc bao nhieu tuan.",
               "contraction_interval_minutes": "Em khong biet canh gio nen khong biet cac con cach nhau bao lau.",
               "vaginal_fluid_leakage_status": "Ban ay bao khong biet co ra nuoc hay khong.",
               "pain_severity": "Hoi dau may diem thi ban ay khong tra loi."},
      clarification="Em noi lai cho ro: ban nu 16 tuoi o cung phong tro voi em dau bung tung con tu toi, bung go cung len "
                    "roi lai mem. Ban ay giau thai, chua kham lan nao nen khong biet bao nhieu tuan. Em khong canh duoc cac "
                    "con cach nhau bao lau. Ban ay chua ra mau, con ra nuoc hay chua thi ban ay khong biet.",
      confirmation="Dung roi, thong tin nhu vay.",
      review_concern="Thiếu niên 16 tuổi giấu thai, chưa khám thai lần nào, đang có cơn gò từng cơn: chưa rõ tuổi thai và "
                     "khoảng cách cơn gò nên corpus không xếp được; theo AHRQ, thai phụ đang gò mà chưa từng khám thai (có thể "
                     "non tháng hoặc sắp sinh) là tình huống nguy cơ cao, nên xếp ít nhất ESI 2.",
      tags=("adolescent", "pregnancy", "collateral_history", "null_unknown", "no_diacritics", "concealed_pregnancy"),
      test="Không biết tuổi thai, không ai canh khoảng cách cơn gò, không rõ đã vỡ ối chưa: agent không được tự đoán là "
           "chuyển dạ đủ tháng hay chưa mà phải chuyển nhân viên y tế ngay."),
    S("x78", "nonverbal_down_syndrome_belly_social_center", "Thanh niên hội chứng Down không nói được: ôm bụng, nôn, không chịu kẹp nhiệt kế",
      P(24, "Male", "OTHER", chronic=("Hội chứng Down", "Chậm phát triển trí tuệ")),
      "Tôi là nhân viên chăm sóc ở trung tâm bảo trợ xã hội. Một em 24 tuổi bị hội chứng Down, gần như không nói được, từ "
      "sáng tới giờ cứ ôm bụng, nằm co người, nôn hai lần, bỏ cả bữa trưa. Tôi đặt nhiệt kế thì em gạt ra, không chịu kẹp "
      "nên không đo được. Hỏi đau chỗ nào, đau nhiều không thì em không trả lời được. Ca đêm qua cũng không ghi gì vào sổ.",
      {"abdominal_pain_present": "YES", "pain_present": "YES", "vomiting_present": "YES",
       "vomiting_frequency": "FEW_TIMES", "gastrointestinal_symptom_present": "YES", "oral_intake_tolerance": "REDUCED",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("abdominal_pain", "vomiting"), screen=QUIET,
      answers={"abdominal_pain_present": "Có, em ấy cứ ôm bụng, nằm co người.",
               "pain_present": "Có, em ấy ôm bụng, nằm co người.",
               "vomiting_present": "Có, em ấy nôn hai lần.",
               "vomiting_frequency": "Nôn hai lần.",
               "gastrointestinal_symptom_present": "Có, em ấy ôm bụng và nôn hai lần.",
               "oral_intake_tolerance": "Em ấy bỏ cả bữa trưa.",
               "symptom_duration_bucket": "Từ sáng tới giờ."},
      unknown={"pain_severity": "Em ấy không nói được nên không chấm điểm được.",
               "abdominal_pain_location": "Em ấy không chỉ cho tôi được đau ở đâu.",
               "temperature": "Em ấy gạt nhiệt kế ra, không chịu kẹp nên không đo được.",
               "fever_present": "Tôi không đo được nên không biết em ấy có sốt không."},
      tags=("intellectual_disability", "communication_barrier", "collateral_history", "missing_vitals", "null_unknown",
            "institutional_care"),
      test="Người bệnh không nói được, không chịu đo nhiệt: agent không được tự gán vị trí, điểm đau hay coi là không sốt; "
           "thiếu các dữ kiện quyết định thì phải chuyển nhân viên y tế."),
    S("x79", "dementia_mother_clutching_chest_sweating", "Cụ bà sa sút trí tuệ ôm ngực, vã mồ hôi, không tả được đau",
      P(81, "Female", "PARENT", chronic=("Sa sút trí tuệ", "Đái tháo đường type 2", "Tăng huyết áp"),
        meds=("Metformin 500 mg sáng và tối", "Amlodipin 5 mg mỗi sáng")),
      "Mẹ tôi 81 tuổi bị lẫn, chừng nửa tiếng nay đang ngồi xem ti vi thì cứ ôm ngực, nhăn nhó, vã mồ hôi trán, hỏi thì "
      "chỉ bảo khó chịu ở ngực chứ không tả được đau kiểu gì, lan đi đâu, nhà lại không có máy đo huyết áp.",
      {"chest_pain_present": "YES", "pain_present": "YES", "cardiorespiratory_symptom_present": "YES",
       "exertional_relation": "OCCURS_AT_REST", "symptom_duration_bucket": "UNDER_1_HOUR"},
      INCOMPLETE, concepts=("chest_pain",), screen=HIT,
      answers={"chest_pain_present": "Có, mẹ ôm ngực, bảo khó chịu ở ngực.",
               "pain_present": "Có, mẹ nhăn nhó, kêu khó chịu ở ngực.",
               "cardiorespiratory_symptom_present": "Có, mẹ kêu khó chịu ở ngực.",
               "exertional_relation": "Mẹ đang ngồi xem ti vi thì bị.",
               "symptom_duration_bucket": "Chừng nửa tiếng nay."},
      unknown={"chest_pain_quality": "Mẹ chỉ nói khó chịu, không tả được kiểu đau.",
               "chest_pain_radiation": "Mẹ không nói được có lan đi đâu không.",
               "pain_severity": "Mẹ không hiểu khi tôi hỏi đau mấy điểm.",
               "systolic_bp": "Nhà không có máy đo huyết áp."},
      review_concern="Cụ bà 81 tuổi đái tháo đường, khó chịu ngực khi đang nghỉ kèm vã mồ hôi: theo Decision Point B đây là "
                     "tình huống nguy cơ cao (cần loại trừ hội chứng vành cấp), nên xếp ESI 2; corpus cần tính chất hoặc hướng "
                     "lan của cơn đau mà người bệnh sa sút trí tuệ không tả được.",
      tags=("older_adult", "caregiver", "baseline_cognitive_impairment", "comorbidity", "missing_vitals", "null_unknown",
            "corpus_gap"),
      test="Người bệnh sa sút trí tuệ không tả được tính chất và hướng lan của đau: agent không được hiểu 'không tả được' là "
           "đau nhẹ, phải chuyển nhân viên y tế ngay."),
    S("x80", "asthma_gel_nails_oximeter_blank", "Cơn hen xịt thuốc đỡ rồi lại khò khè, máy kẹp ngón không lên số vì sơn gel móng",
      P(22, "Female", chronic=("Hen phế quản",), allergies=("Dị ứng tôm cua",), meds=("Salbutamol xịt khi lên cơn",)),
      "E bị hen từ nhỏ. Từ chiều e khò khè, đi lại trong phòng là hụt hơi, ngồi yên thì đỡ hơn, vẫn nói dc trọn câu. E "
      "xịt thuốc cắt cơn 2 lần, đỡ dc 1 lúc rồi lại khò khè. E mượn máy kẹp ngón tay của chị cùng phòng để đo oxy mà e "
      "đang sơn gel móng nên máy ko lên số.",
      {"dyspnea_present": "YES", "dyspnea_context": "WITH_EXERTION", "respiratory_distress_symptoms": "WITH_ACTIVITY",
       "noisy_breathing_present": "YES", "breathing_sound": "WHEEZING", "cardiorespiratory_symptom_present": "YES",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, concepts=("wheezing",), screen=QUIET,
      answers={"dyspnea_present": "Dạ có, e hụt hơi.",
               "dyspnea_context": "Đi lại trong phòng là hụt hơi, ngồi yên thì đỡ hơn.",
               "respiratory_distress_symptoms": "Đi lại trong phòng là hụt hơi, ngồi yên thì đỡ, vẫn nói dc trọn câu.",
               "noisy_breathing_present": "Dạ có, e thở khò khè.",
               "breathing_sound": "Khò khè ạ.",
               "cardiorespiratory_symptom_present": "Dạ có, e khò khè, hụt hơi.",
               "symptom_duration_bucket": "Từ chiều tới giờ ạ."},
      unknown={"spo2": "E đang sơn gel móng nên máy kẹp ngón ko lên số.",
               "heart_rate": "Máy kẹp ngón ko lên số nào cả nên e ko biết.",
               "respiratory_rate": "E ko biết đếm nhịp thở."},
      tags=("comorbidity", "missing_vitals", "device_error", "null_unknown", "abbreviation"),
      test="Máy đo oxy không lên số vì sơn gel móng: agent không được coi SpO2 là bình thường; khò khè tái lại sau hai lần "
           "xịt mà thiếu SpO2 thì phải chuyển nhân viên y tế."),
]
