"""Nhóm MULTI_SYMPTOM, đợt 3 (tệp c, lượt 2): dữ kiện quyết định đến muộn hoặc ở dạng nói miệng.

Trọng tâm của tệp là lớp lỗi F2 của agent: lời kể nhiều triệu chứng, trong đó dữ kiện quyết định mức là (1) một số đo
của máy được đọc theo kiểu nói thường ngày ("một trăm hai" là 120, "một trăm linh hai" là 102, "tám bảy trên năm
lăm", "38 độ rưỡi", "ba chục", "13 rưỡi trên 8"), (2) một điều chỉ xuất hiện trong câu trả lời khi agent hỏi tới (gắn
``progressive_disclosure`` và ghi rõ trong ``test``), hoặc (3) lời của người thứ hai (con cháu đọc máy, hàng xóm mang
máy đo sang, giáo viên, đồng nghiệp). Agent phải hỏi tiếp tới đúng câu hỏi quyết định, hiểu đúng con số, không dừng
sớm ở một câu trả lời chung chung và không tự đoán khi con số thật sự chưa có.

Quy ước riêng của tệp:
- Sáu cặp tối thiểu, mỗi cặp hai ca liền nhau và chung một gia đình kịch bản, nằm hai phía một ngưỡng vùng nguy hiểm
  (Decision Point C): một ca khớp tiêu chí ESI 2, ca kia là một câu chuyện khác nằm ngay dưới ngưỡng (ESI 3 hoặc chuyển
  nhân viên y tế). Cả hai ca gắn ``minimal_pair`` và ``boundary_value``; ``test`` của mỗi ca giải thích cặp.
- Ca trẻ em dùng sinh hiệu hợp tuổi; khi corpus (ngưỡng người lớn) cho mức khác với ngưỡng AHRQ theo tuổi, ca có
  ``review_concern``.
- ``m137`` ghim tiêu chí đại diện (``primary_atom``) vì dữ kiện "nặng dần" mà lời kể nêu rõ làm một tiêu chí mang tên
  nhiễm trùng thắng theo số điều kiện; lý do ghi ngay tại ca. Không ca nào dùng số nguồn lực dự kiến.
"""

from __future__ import annotations

from eval.generated_mock_v2.spec import INCOMPLETE, MULTI, P, SCREEN_HIT as HIT, SCREEN_QUIET as QUIET, Spec


def S(key: str, family: str, title: str, profile: dict, opening: str, facts: dict, intended, **kw) -> Spec:
    return Spec(case_id=key, family=family, group=MULTI, title=title, profile=profile,
                opening=opening, facts=facts, intended=intended, **kw)


SPECS = [
    S("m131", "spoken_pulse_120_vs_102_pair", "Ăn tiết canh hai hôm trước, sốt 38,9, rét run, máy đo báo nhịp tim 'một trăm hai'",
      P(46, "Male", "SPOUSE", chronic=("Tăng huyết áp",), meds=("Amlodipin 5 mg mỗi sáng",)),
      "Chồng em 46 tuổi, hôm kia về quê ăn cỗ có ăn tiết canh lợn. Từ đêm qua anh ấy sốt, rét run cầm cập, nhức mỏi "
      "khắp người, sáng nay nôn hai lần, đi ngoài lỏng một lần, chỉ ăn được mấy thìa cháo. Em đo nhiệt kế điện tử được "
      "38 độ 9, lấy máy đo huyết áp ra đo thì 118 trên 72, nhịp tim máy báo một trăm hai. Anh ấy vẫn tỉnh, nói chuyện "
      "bình thường. Nghe người ta nói ăn tiết canh dễ bị liên cầu lợn nên em lo quá.",
      {"fever_present": "YES", "temperature": 38.9, "chills_present": "YES",
       "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS", "pain_present": "YES", "vomiting_present": "YES",
       "vomiting_frequency": "FEW_TIMES", "diarrhea_present": "YES", "stool_appearance": "LOOSE",
       "gastrointestinal_symptom_present": "YES", "oral_intake_tolerance": "REDUCED",
       "infection_source_symptom_group": "GASTROINTESTINAL", "systolic_bp": 118, "diastolic_bp": 72,
       "heart_rate": 120, "altered_mental_status_present": "NO", "neck_stiffness_present": "NO",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen="", concepts=("fever", "chills", "tachycardia", "myalgia"),
      answers={"fever_present": "Có, anh ấy sốt từ đêm qua.",
               "temperature": "Nhiệt kế điện tử kẹp nách được 38 độ 9.",
               "chills_present": "Có, rét run cầm cập.",
               "associated_systemic_symptoms": "Vừa sốt vừa rét run, người mệt rũ ra.",
               "pain_present": "Có, anh ấy kêu nhức mỏi khắp người.",
               "vomiting_present": "Có, sáng nay nôn hai lần.",
               "vomiting_frequency": "Nôn hai lần thôi.",
               "diarrhea_present": "Có, sáng nay đi ngoài lỏng một lần.",
               "stool_appearance": "Phân lỏng.",
               "gastrointestinal_symptom_present": "Có, anh ấy nôn hai lần với đi ngoài lỏng một lần.",
               "oral_intake_tolerance": "Ăn kém hẳn, sáng nay chỉ ăn được mấy thìa cháo.",
               "infection_source_symptom_group": "Ngoài sốt thì chủ yếu nôn với đi ngoài lỏng, mỏi khắp người.",
               "systolic_bp": "Máy đo huyết áp được 118 trên 72.",
               "diastolic_bp": "Số dưới là 72.",
               "heart_rate": "Máy báo nhịp tim một trăm hai, em đo lại lần nữa vẫn một trăm hai.",
               "altered_mental_status_present": "Không, anh ấy vẫn tỉnh, nói chuyện bình thường.",
               "neck_stiffness_present": "Không, cổ anh ấy vẫn cúi được bình thường.",
               "symptom_duration_bucket": "Sốt từ đêm qua, tới giờ chưa được một ngày."},
      unknown={"pain_severity": "Anh ấy chỉ kêu mỏi nhừ cả người, không nói được mấy điểm."},
      tags=("caregiver", "comorbidity", "minimal_pair", "boundary_value", "colloquial_vitals", "multiple_complaints"),
      test="Cặp tối thiểu với m132: nhịp tim nói kiểu 'một trăm hai' nghĩa là 120, đúng ngưỡng mạch ≥ 120 của tiêu chí sốt "
           "≥ 38,5 kèm mạch nhanh nên ESI 2; agent phải hiểu đúng con số (không đọc thành 102) và không hạ mức vì người "
           "bệnh vẫn tỉnh, nói chuyện được."),

    S("m132", "spoken_pulse_120_vs_102_pair", "Bé 8 tuổi sốt 38 độ rưỡi, đau tai, ăn ít; máy kẹp ngón báo mạch 'một trăm linh hai'",
      P(8, "Female", "CHILD"),
      "Con gái mình 8 tuổi, sổ mũi ho mấy hôm nay, từ chiều qua thì sốt lại, mình đo nhiệt kế điện tử ở nách được 38 độ "
      "rưỡi. Bé kêu đau tai trái, ăn cơm chỉ được nửa bát, uống nước thì vẫn uống được. Mình kẹp cái máy đo ô xy vào ngón "
      "tay thì máy báo 98, mạch một trăm linh hai. Bé vẫn chơi, xem ti vi được, không nôn.",
      {"fever_present": "YES", "temperature": 38.5, "pain_present": "YES", "oral_intake_tolerance": "REDUCED",
       "spo2": 98, "heart_rate": 102, "cough_present": "YES", "runny_nose_present": "YES", "vomiting_present": "NO",
       "infection_source_symptom_group": "RESPIRATORY", "activity_level": "NORMAL",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, screen=QUIET, concepts=("fever", "ear_pain", "poor_oral_intake"),
      answers={"fever_present": "Có, bé sốt lại từ chiều qua.",
               "temperature": "Nhiệt kế điện tử kẹp nách báo 38 độ rưỡi.",
               "pain_present": "Có, bé kêu đau tai trái.",
               "oral_intake_tolerance": "Ăn cơm chỉ được nửa bát, uống nước thì vẫn uống được.",
               "spo2": "Số ô xy trên máy là 98.",
               "heart_rate": "Máy kẹp ngón báo mạch một trăm linh hai.",
               "cough_present": "Có, bé ho mấy hôm nay.",
               "runny_nose_present": "Có, sổ mũi mấy hôm nay rồi.",
               "vomiting_present": "Không, bé không nôn.",
               "infection_source_symptom_group": "Ngoài sốt thì bé kêu đau tai trái, kèm sổ mũi với ho.",
               "activity_level": "Bé vẫn chơi, vẫn xem ti vi được.",
               "symptom_duration_bucket": "Sổ mũi, ho thì mấy hôm nay rồi, còn sốt với đau tai mới từ chiều qua."},
      unknown={"pain_severity": "Bé chỉ kêu đau tai, mình không biết bé đau mấy điểm."},
      tags=("pediatric", "caregiver", "minimal_pair", "boundary_value", "colloquial_vitals"),
      test="Cặp tối thiểu với m131: 'một trăm linh hai' là 102, xa dưới ngưỡng mạch ≥ 120, còn nhiệt độ 38,5 vừa chạm ngưỡng "
           "nhưng không có mạch nhanh đi kèm, nên chỉ có tiêu chí sốt kèm ăn kém (ESI 3); agent phải phân biệt 'một trăm "
           "linh hai' với 'một trăm hai' và không nâng lên ESI 2."),

    S("m133", "post_laparoscopic_appendectomy_day3_wife_brings_thermometer", "Mổ nội soi ruột thừa ba hôm, đau quanh vết mổ 5/10, ăn kém; nhiệt độ 38,3 chỉ có khi vợ mua nhiệt kế về",
      P(24, "Male", allergies=("Penicillin",)),
      "Em 24 tuổi, mổ nội soi ruột thừa được ba hôm, hôm qua được ra viện. Từ chiều nay em thấy người hâm hấp, mệt, đau "
      "quanh rốn chỗ vết mổ to nhất chừng 5 trên 10, ăn kém hơn hôm qua, hơi buồn nôn nhưng không nôn. Các vết mổ khô, không "
      "chảy dịch. Nhà em không có nhiệt kế, vợ em đang chạy đi mua.",
      {"pain_present": "YES", "pain_severity": 5, "abdominal_pain_present": "YES",
       "abdominal_pain_location": "AROUND_UMBILICUS", "gastrointestinal_symptom_present": "YES", "vomiting_present": "NO",
       "oral_intake_tolerance": "REDUCED", "fever_present": "YES", "temperature": 38.3,
       "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS", "infection_source_symptom_group": "GASTROINTESTINAL",
       "wound_present": "YES", "wound_location": "ABDOMEN", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      3, screen=QUIET, concepts=("fever", "abdominal_pain", "wound_pain"),
      answers={"pain_present": "Có, em đau quanh vết mổ.",
               "pain_severity": "Chừng 5 trên 10.",
               "abdominal_pain_present": "Có, đau quanh rốn chỗ vết mổ to nhất.",
               "abdominal_pain_location": "Quanh rốn, chỗ vết mổ to nhất.",
               "gastrointestinal_symptom_present": "Có, em đau bụng với hơi buồn nôn.",
               "vomiting_present": "Không, em buồn nôn chứ không nôn.",
               "oral_intake_tolerance": "Ăn kém hơn hôm qua, được nửa bát cháo.",
               "fever_present": "Người em hâm hấp, lúc đầu chưa đo được.",
               "temperature": "Vợ em vừa mua nhiệt kế về cặp nách cho em: 38 độ 3.",
               "associated_systemic_symptoms": "Người hâm hấp sốt với mệt.",
               "infection_source_symptom_group": "Ngoài sốt thì chủ yếu đau bụng chỗ vết mổ.",
               "wound_present": "Có mấy vết mổ nội soi nhỏ trên bụng, khô, không chảy dịch.",
               "wound_location": "Ở bụng.",
               "symptom_duration_bucket": "Từ chiều nay, mới mấy tiếng."},
      tags=("progressive_disclosure", "collateral_history", "missing_vitals"),
      test="Nhiệt độ 38,3 chỉ có khi agent hỏi, do vợ vừa mua nhiệt kế về cặp (tiết lộ muộn có chủ đích); thiếu con số này "
           "thì đau 5/10 sau mổ không khớp tiêu chí nào, có nó thì sốt kèm đau vừa và ăn kém cho ESI 3 — agent phải hỏi lại "
           "nhiệt độ chứ không dừng ở 'người hâm hấp'."),

    S("m134", "spoken_systolic_87_vs_94_pair", "Ba ngày sau hút mỡ bụng: căng đau 6/10, lả, choáng; em gái đo huyết áp 'tám bảy trên năm lăm'",
      P(29, "Female", "SIBLING"),
      "Chị gái em 29 tuổi, ba hôm trước đi hút mỡ bụng ở một cơ sở thẩm mỹ. Từ tối qua chị kêu bụng căng tức, đau khắp "
      "vùng hút mỡ chừng 6 trên 10, buồn nôn, người lả đi, ngồi dậy là choáng. Em lấy máy đo huyết áp của mẹ ra đo thì "
      "được tám bảy trên năm lăm, mạch một trăm mười tám. Chị không sốt, vẫn nói chuyện với em bình thường.",
      {"abdominal_pain_present": "YES", "abdominal_pain_location": "GENERALIZED", "abdominal_pain_character": "PRESSURE",
       "pain_present": "YES", "pain_severity": 6, "gastrointestinal_symptom_present": "YES", "vomiting_present": "NO",
       "dizziness_present": "YES", "dizziness_sensation": "LIGHTHEADED", "syncope_present": "NO",
       "associated_systemic_symptoms": "GENERAL_WEAKNESS", "systolic_bp": 87, "diastolic_bp": 55, "heart_rate": 118,
       "fever_present": "NO", "altered_mental_status_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen="", concepts=("hypotension", "abdominal_pain", "dizziness"),
      answers={"abdominal_pain_present": "Có, chị kêu bụng căng tức, đau khắp vùng hút mỡ.",
               "abdominal_pain_location": "Đau khắp vùng bụng chỗ hút mỡ.",
               "abdominal_pain_character": "Căng tức.",
               "pain_present": "Có, chị đau bụng.",
               "pain_severity": "Chị bảo chừng 6 trên 10.",
               "gastrointestinal_symptom_present": "Có, chị đau bụng với buồn nôn.",
               "vomiting_present": "Không, chị buồn nôn chứ chưa nôn.",
               "dizziness_present": "Có, ngồi dậy là chị choáng.",
               "dizziness_sensation": "Choáng kiểu tối sầm mắt, chứ không thấy nhà quay.",
               "syncope_present": "Chưa ngất, chị chỉ choáng rồi phải nằm xuống.",
               "associated_systemic_symptoms": "Người chị lả đi, không sốt.",
               "systolic_bp": "Máy đo được tám bảy trên năm lăm.",
               "diastolic_bp": "Số dưới là năm lăm.",
               "heart_rate": "Máy báo mạch một trăm mười tám.",
               "fever_present": "Không, chị không sốt.",
               "altered_mental_status_present": "Không, chị vẫn tỉnh, nói chuyện bình thường.",
               "symptom_duration_bucket": "Từ tối qua tới giờ."},
      tags=("caregiver", "minimal_pair", "boundary_value", "colloquial_vitals", "multiple_complaints"),
      test="Cặp tối thiểu với m135: huyết áp đọc kiểu nói 'tám bảy trên năm lăm' (87/55) nằm trong vùng 71–89 nên ESI 2, kèm "
           "lả người và đau bụng 6/10 sau thủ thuật thẩm mỹ; agent phải giữ đúng con số và không coi là ổn chỉ vì người "
           "bệnh vẫn nói chuyện bình thường."),

    S("m135", "spoken_systolic_87_vs_94_pair", "Đồng nghiệp kể: nôn, tiêu chảy, sốt 38,2, ăn ít; phòng y tế công ty đo 'chín tư trên sáu mươi'",
      P(32, "Female", "OTHER", allergies=("Cotrimoxazol",)),
      "Em hỏi giúp chị trưởng nhóm của em, 32 tuổi. Trưa nay chị ăn bún chả ở quán đầu ngõ, đầu giờ chiều thì đau bụng âm "
      "ỉ quanh rốn, nôn hai lần, đi ngoài lỏng ba lần, người hâm hấp. Phòng y tế công ty đo nhiệt độ 38 độ 2, huyết áp chín "
      "tư trên sáu mươi, mạch chín mươi sáu. Chị vẫn uống được nước, chỉ là không ăn được mấy. Chị bảo huyết áp chị bình "
      "thường cũng thấp, tầm chín mươi mấy thôi.",
      {"abdominal_pain_present": "YES", "abdominal_pain_location": "AROUND_UMBILICUS", "abdominal_pain_character": "DULL",
       "pain_present": "YES", "pain_severity": 4, "vomiting_present": "YES", "vomiting_frequency": "FEW_TIMES",
       "diarrhea_present": "YES", "diarrhea_frequency": 3, "stool_appearance": "LOOSE",
       "gastrointestinal_symptom_present": "YES", "vomiting_or_feeding_problem_present": "YES",
       "fluid_retention": "ABLE_TO_KEEP_FLUIDS", "oral_intake_tolerance": "REDUCED", "fever_present": "YES",
       "temperature": 38.2, "infection_source_symptom_group": "GASTROINTESTINAL", "systolic_bp": 94,
       "diastolic_bp": 60, "heart_rate": 96, "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      3, screen=QUIET, concepts=("vomiting", "diarrhea", "fever"),
      answers={"abdominal_pain_present": "Có, chị đau bụng âm ỉ quanh rốn.",
               "abdominal_pain_location": "Quanh rốn.",
               "abdominal_pain_character": "Đau âm ỉ thôi.",
               "pain_present": "Có, chị đau bụng âm ỉ.",
               "pain_severity": "Chị bảo chừng 4 điểm.",
               "vomiting_present": "Có, chị nôn hai lần.",
               "vomiting_frequency": "Nôn hai lần từ đầu giờ chiều.",
               "diarrhea_present": "Có, chị đi ngoài lỏng.",
               "diarrhea_frequency": "Chị đi ngoài lỏng ba lần từ đầu giờ chiều tới giờ.",
               "stool_appearance": "Phân lỏng.",
               "gastrointestinal_symptom_present": "Có, chị đau bụng, nôn với đi ngoài lỏng.",
               "vomiting_or_feeding_problem_present": "Có, chị nôn hai lần, ăn uống kém đi.",
               "fluid_retention": "Uống nước vào thì vẫn giữ được.",
               "oral_intake_tolerance": "Uống nước được, chỉ là không ăn được mấy.",
               "fever_present": "Có, người chị hâm hấp sốt.",
               "temperature": "Phòng y tế đo được 38 độ 2.",
               "infection_source_symptom_group": "Ngoài sốt thì chủ yếu đau bụng, nôn với đi ngoài lỏng.",
               "systolic_bp": "Phòng y tế đo huyết áp chín tư trên sáu mươi.",
               "diastolic_bp": "Số dưới là sáu mươi.",
               "heart_rate": "Mạch chín mươi sáu.",
               "symptom_duration_bucket": "Từ đầu giờ chiều nay, mới mấy tiếng."},
      tags=("collateral_history", "minimal_pair", "boundary_value", "colloquial_vitals", "multiple_complaints"),
      test="Cặp tối thiểu với m134: huyết áp 'chín tư trên sáu mươi' ở người vốn huyết áp thấp đã ra khỏi vùng ≤ 89, sốt 38,2 "
           "chưa tới 38,5 và vẫn giữ được nước uống, nên chỉ có tiêu chí sốt kèm ăn kém (ESI 3); agent không được nâng lên "
           "ESI 2 chỉ vì nghe 'huyết áp thấp'."),

    S("m136", "pregnant_31w_household_gastro_brother_reads_cuff", "Thai 31 tuần lây tiêu chảy từ con, nôn hết nước; khi được hỏi mới có mạch 126, huyết áp 94/58 do em trai đo",
      P(30, "Female", meds=("Viên sắt và axit folic",)),
      "Em có thai 31 tuần. Bé lớn nhà em 3 tuổi bị tiêu chảy từ hôm kia, đêm qua đến lượt em. Từ nửa đêm em nôn liên "
      "tục, uống ngụm nước cũng nôn ra, đi ngoài toàn nước, bụng quặn từng cơn, người mệt lả, đứng lên là hoa mắt. Em "
      "không sốt, con trong bụng vẫn đạp, không ra máu, không ra nước, bụng không gò cứng.",
      {"pregnancy_present": "YES", "pregnancy_status": "PREGNANT", "gestational_age_weeks": 31,
       "vomiting_present": "YES", "vomiting_frequency": "REPEATED", "oral_intake_tolerance": "UNABLE_TO_KEEP_DOWN",
       "vomiting_or_feeding_problem_present": "YES", "fluid_retention": "UNABLE_TO_KEEP_FLUIDS",
       "diarrhea_present": "YES", "diarrhea_frequency": 8, "stool_appearance": "WATERY",
       "abdominal_pain_present": "YES", "abdominal_pain_character": "CRAMPING", "pain_present": "YES",
       "gastrointestinal_symptom_present": "YES", "associated_systemic_symptoms": "GENERAL_WEAKNESS",
       "dizziness_present": "YES", "dizziness_sensation": "LIGHTHEADED", "fever_present": "NO",
       "fetal_movement_status": "NORMAL", "vaginal_bleeding_present": "NO", "vaginal_fluid_leakage_status": "NONE",
       "uterine_contractions_present": "NO", "similar_symptoms_in_others": "YES", "symptom_trend": "INTERMITTENT",
       "heart_rate": 126,
       "systolic_bp": 94, "diastolic_bp": 58, "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen="", concepts=("vomiting_in_pregnancy", "diarrhea", "tachycardia", "hypotension"),
      answers={"pregnancy_present": "Dạ có, em đang có thai 31 tuần.",
               "pregnancy_status": "Em đang mang thai.",
               "gestational_age_weeks": "Thai được 31 tuần ạ.",
               "vomiting_present": "Có, em nôn liên tục từ nửa đêm.",
               "vomiting_frequency": "Nôn đi nôn lại, không đếm được mấy lần.",
               "oral_intake_tolerance": "Uống ngụm nước cũng nôn ra.",
               "vomiting_or_feeding_problem_present": "Có, em nôn hết, không ăn uống được gì.",
               "fluid_retention": "Uống vào bao nhiêu nôn ra bấy nhiêu.",
               "diarrhea_present": "Có, em đi ngoài toàn nước.",
               "diarrhea_frequency": "Từ nửa đêm tới giờ em đi tám lần.",
               "stool_appearance": "Phân toàn nước.",
               "abdominal_pain_present": "Có, bụng quặn từng cơn.",
               "abdominal_pain_character": "Quặn từng cơn rồi đỡ.",
               "pain_present": "Có, bụng em quặn từng cơn.",
               "gastrointestinal_symptom_present": "Có, em nôn, đi ngoài toàn nước, bụng quặn.",
               "associated_systemic_symptoms": "Em mệt lả người, không sốt.",
               "dizziness_present": "Có, đứng lên là hoa mắt.",
               "dizziness_sensation": "Hoa mắt, chao đảo như sắp ngã, chứ không thấy nhà quay.",
               "fever_present": "Không, em không sốt.",
               "fetal_movement_status": "Con trong bụng vẫn đạp như mọi ngày.",
               "vaginal_bleeding_present": "Không ra máu ạ.",
               "vaginal_fluid_leakage_status": "Không ra nước ạ.",
               "uterine_contractions_present": "Bụng không gò cứng ạ.",
               "similar_symptoms_in_others": "Có, bé lớn nhà em 3 tuổi bị tiêu chảy từ hôm kia, em bị lây.",
               "symptom_trend": "Bụng quặn từng cơn, lúc đau lúc đỡ.",
               "heart_rate": "Em trai em làm ở hiệu thuốc vừa mang máy về đo cho em: mạch một trăm hai mươi sáu.",
               "systolic_bp": "Nó đọc huyết áp chín mươi tư trên năm mươi tám.",
               "diastolic_bp": "Số dưới là năm mươi tám.",
               "symptom_duration_bucket": "Từ nửa đêm qua tới giờ."},
      unknown={"pain_severity": "Quặn từng cơn rồi đỡ, em không biết chấm mấy điểm."},
      tags=("pregnancy", "progressive_disclosure", "collateral_history", "multiple_complaints", "negation"),
      test="Mạch 126 và huyết áp 94/58 chỉ xuất hiện khi agent hỏi, do em trai mang máy về đo (tiết lộ muộn có chủ đích); "
           "cùng tiêu chí với m39 nhưng khác hẳn bệnh cảnh (thai 31 tuần lây tiêu chảy nước từ con, không phải nghén ba "
           "tháng đầu), agent phải hỏi tới sinh hiệu chứ không dừng ở 'mệt, hoa mắt'."),

    S("m137", "spoken_spo2_91_vs_93_pair", "Thợ đục đá về hưu khó thở tăng dần, cháu nội đọc máy kẹp ngón: hàng số to 'chín mốt'",
      P(67, "Male", chronic=("Bụi phổi do nghề đục đá",), meds=("Thuốc xịt giãn phế quản khi khó thở",)),
      "Tôi 67 tuổi, hồi trẻ làm thợ đục đá ở mỏ gần hai chục năm, bác sĩ bảo bị bụi phổi. Hơn một tuần nay tôi ho khan "
      "nhiều hơn, khó thở tăng dần, đi lại trong nhà là hụt hơi phải đứng lại thở, ngồi yên thì đỡ. Không sốt. Con gái "
      "mua cho cái máy kẹp ngón tay đo ô xy, sáng nay tôi kẹp thử mà mắt kém, chỉ thấy hai hàng số, không biết đọc số nào.",
      {"cough_present": "YES", "cough_character": "DRY", "dyspnea_present": "YES", "dyspnea_context": "WITH_EXERTION",
       "respiratory_distress_symptoms": "WITH_ACTIVITY", "cardiorespiratory_symptom_present": "YES",
       "symptom_trend": "WORSENING", "fever_present": "NO", "spo2": 91, "heart_rate": 88,
       "symptom_duration_bucket": "OVER_7_DAYS"},
      2, screen="", concepts=("shortness_of_breath", "cough"),
      # Lời kể nói rõ khó thở "tăng dần" nên có symptom_trend=WORSENING; tiêu chí chung
      # esi_2_worsening_infection_with_hypoxemia (nặng dần + SpO2 <= 92) nhiều điều kiện hơn nên thắng,
      # dù ca không có nhiễm trùng. Ghim tiêu chí SpO2 vùng nguy hiểm vì đúng bệnh cảnh.
      primary_atom="esi_2_danger_zone_hypoxemia_v2",
      answers={"cough_present": "Có, tôi ho khan nhiều hơn mọi khi.",
               "cough_character": "Ho khan, không có đờm.",
               "dyspnea_present": "Có, đi lại là hụt hơi.",
               "dyspnea_context": "Đi lại trong nhà là hụt hơi, ngồi yên thì đỡ.",
               "respiratory_distress_symptoms": "Đi vài bước là phải đứng lại thở, ngồi nghỉ thì đỡ.",
               "cardiorespiratory_symptom_present": "Có, tôi hụt hơi, ho khan.",
               "symptom_trend": "Khó thở tăng dần, tuần này nặng hơn tuần trước.",
               "fever_present": "Không sốt.",
               "spo2": "Thằng cháu nội đọc giúp tôi: hàng số to bên trên là chín mốt, hàng dưới là tám mươi tám.",
               "heart_rate": "Cháu bảo hàng số nhỏ bên dưới là tám mươi tám, chắc là mạch.",
               "symptom_duration_bucket": "Hơn một tuần nay rồi."},
      tags=("older_adult", "comorbidity", "occupational", "minimal_pair", "boundary_value", "progressive_disclosure",
            "collateral_history", "colloquial_vitals"),
      test="Cặp tối thiểu với m138: con số quyết định chỉ có khi được hỏi và do cháu nội đọc từ máy có hai hàng số (tiết lộ "
           "muộn có chủ đích); SpO2 'chín mốt' vừa chạm mép trên vùng 86–91 nên ESI 2, agent phải hỏi bằng được con số và "
           "phân biệt hàng SpO2 với hàng mạch."),

    S("m138", "spoken_spo2_91_vs_93_pair", "Mười ngày sau cúm vẫn ho, mệt, hụt hơi khi leo cầu thang; máy kẹp ngón ba lần đều 'chín ba'",
      P(44, "Female", chronic=("Suy giáp",), meds=("Levothyroxin mỗi sáng",)),
      "Mình 44 tuổi, bị cúm cách đây khoảng mười hôm, hết sốt được năm hôm rồi mà vẫn ho khan, người mệt, leo hai tầng cầu "
      "thang là hụt hơi. Ngồi nghỉ thì thở bình thường, nói chuyện bình thường. Chồng mình đếm nhịp thở lúc mình ngồi được "
      "18 lần một phút. Máy kẹp ngón ở nhà đo ba lần đều chín ba, mình đọc trên mạng thấy dưới 95 là thấp nên lo.",
      {"cough_present": "YES", "cough_character": "DRY", "dyspnea_present": "YES", "dyspnea_context": "WITH_EXERTION",
       "respiratory_distress_symptoms": "WITH_ACTIVITY", "cardiorespiratory_symptom_present": "YES",
       "associated_systemic_symptoms": "GENERAL_WEAKNESS", "fever_present": "NO", "spo2": 93,
       "respiratory_rate": 18, "symptom_duration_bucket": "OVER_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("cough", "shortness_of_breath", "fatigue"),
      answers={"cough_present": "Có, vẫn ho khan.",
               "cough_character": "Ho khan, không có đờm.",
               "dyspnea_present": "Có, leo cầu thang là hụt hơi.",
               "dyspnea_context": "Chỉ khi leo cầu thang hay đi nhanh, ngồi nghỉ thì thở bình thường.",
               "respiratory_distress_symptoms": "Leo hai tầng là hụt hơi, ngồi nghỉ thì bình thường.",
               "cardiorespiratory_symptom_present": "Có, mình ho với hụt hơi khi leo cầu thang.",
               "associated_systemic_symptoms": "Người mệt, không sốt nữa.",
               "fever_present": "Không, hết sốt được năm hôm rồi.",
               "spo2": "Máy kẹp ngón đo ba lần đều chín ba.",
               "respiratory_rate": "Chồng mình đếm lúc mình ngồi yên được 18 lần một phút.",
               "symptom_duration_bucket": "Từ lúc bị cúm tới giờ khoảng mười hôm."},
      tags=("comorbidity", "collateral_history", "minimal_pair", "boundary_value", "colloquial_vitals"),
      test="Cặp tối thiểu với m137: SpO2 'chín ba' nằm trên ngưỡng 91, nhịp thở 18 và không khó thở khi nghỉ nên không tiêu "
           "chí nào khớp, kỳ vọng là chuyển nhân viên y tế; agent không được đoán ESI 2 vì 'SpO2 dưới 95', cũng không được "
           "tự kết luận là bình thường."),

    S("m139", "acute_vertigo_vomiting_son_reads_cmhg_shorthand", "Ngủ dậy nhà quay tít, nôn không giữ được nước; con trai đọc huyết áp 'mười ba rưỡi trên tám'",
      P(58, "Female", "PARENT", chronic=("Tăng huyết áp",), meds=("Losartan 50 mg mỗi sáng",)),
      "Mẹ em 58 tuổi, sáng nay ngủ dậy vừa ngồi lên thì thấy nhà cửa quay tít, nôn thốc nôn tháo, từ sáng tới giờ uống "
      "ngụm nước cũng nôn ra. Mẹ nằm im một tư thế thì đỡ quay, cứ cựa đầu là quay lại. Mẹ vẫn nói chuyện rõ ràng, tay "
      "chân cử động được, miệng không méo, không đau đầu. Em đo máy thì huyết áp mười ba rưỡi trên tám, mạch tám mươi tư.",
      {"dizziness_present": "YES", "dizziness_sensation": "SPINNING", "symptom_onset": "SUDDEN",
       "focal_neurologic_symptoms": "NONE", "headache_present": "NO", "vomiting_present": "YES",
       "vomiting_frequency": "REPEATED", "oral_intake_tolerance": "UNABLE_TO_KEEP_DOWN",
       "vomiting_or_feeding_problem_present": "YES", "fluid_retention": "UNABLE_TO_KEEP_FLUIDS",
       "gastrointestinal_symptom_present": "YES", "altered_mental_status_present": "NO", "systolic_bp": 135,
       "diastolic_bp": 80, "heart_rate": 84, "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      3, screen=QUIET, concepts=("vertigo", "vomiting"),
      answers={"dizziness_present": "Có, mẹ thấy nhà cửa quay tít.",
               "dizziness_sensation": "Quay tít như mọi thứ xoay vòng, cựa đầu là quay lại.",
               "symptom_onset": "Đột ngột, sáng nay vừa ngồi dậy là bị.",
               "focal_neurologic_symptoms": "Không, tay chân mẹ cử động bình thường, miệng không méo, nói rõ ràng.",
               "headache_present": "Không, mẹ không đau đầu.",
               "vomiting_present": "Có, mẹ nôn thốc nôn tháo.",
               "vomiting_frequency": "Nôn đi nôn lại từ sáng tới giờ.",
               "oral_intake_tolerance": "Uống ngụm nước cũng nôn ra.",
               "vomiting_or_feeding_problem_present": "Có, mẹ nôn hết, không ăn uống được gì.",
               "fluid_retention": "Uống vào là nôn ra hết.",
               "gastrointestinal_symptom_present": "Có, mẹ nôn nhiều.",
               "altered_mental_status_present": "Không, mẹ vẫn tỉnh, nói chuyện rõ ràng.",
               "systolic_bp": "Máy đo được mười ba rưỡi trên tám.",
               "diastolic_bp": "Số dưới là tám, tức tám mươi.",
               "heart_rate": "Mạch tám mươi tư.",
               "symptom_duration_bucket": "Từ sáng nay lúc ngủ dậy, được mấy tiếng rồi."},
      tags=("caregiver", "comorbidity", "colloquial_vitals", "negation", "multiple_complaints"),
      test="Huyết áp nói theo kiểu tắt 'mười ba rưỡi trên tám' (135/80) và mạch 84 là chỗ dựa để xếp nôn không giữ được gì "
           "vào ESI 3 thay vì ESI 2; agent phải hiểu '13 rưỡi' là 135 chứ không phải 13, và không nâng mức vì 'nhà quay' khi "
           "lời kể đã phủ nhận yếu liệt, méo miệng, nói khó."),

    S("m140", "toddler_mild_gastro_toe_oximeter_pulse_136", "Bé 2 tuổi tiêu chảy, vẫn uống được oresol, không sốt; máy kẹp ngón chân báo mạch 136, mẹ gõ không dấu",
      P(2, "Male", "CHILD"),
      "Con trai em 2 tuoi, tu toi qua bi tieu chay 4 lan phan long, non 2 lan, tu sang den gio uong oresol tung thia van "
      "giu duoc, ko non nua. Be ko sot, em do nhiet ke 37 do 2. Be van choi, chi quay hon moi khi, van co nuoc mat, ta van "
      "uot deu. Em kep may do oxy vao ngon chan be thi may bao 98, mach mot tram ba muoi sau. Mach nhanh vay co sao ko a?",
      {"diarrhea_present": "YES", "diarrhea_frequency": 4, "stool_appearance": "LOOSE", "vomiting_present": "YES",
       "vomiting_frequency": "FEW_TIMES", "gastrointestinal_symptom_present": "YES",
       "vomiting_or_feeding_problem_present": "YES", "fluid_retention": "ABLE_TO_KEEP_FLUIDS", "fever_present": "NO",
       "temperature": 37.2, "activity_level": "NORMAL", "dehydration_visible_signs": "NONE",
       "urine_output_level": "NORMAL", "spo2": 98, "heart_rate": 136, "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen=QUIET, concepts=("diarrhea", "vomiting", "tachycardia"),
      answers={"diarrhea_present": "Co, be di ngoai phan long.",
               "diarrhea_frequency": "Tu toi qua toi gio be di 4 lan.",
               "stool_appearance": "Phan long.",
               "vomiting_present": "Co, toi qua be non 2 lan.",
               "vomiting_frequency": "Non 2 lan thoi, tu sang ko non nua.",
               "gastrointestinal_symptom_present": "Co, be tieu chay voi non 2 lan.",
               "vomiting_or_feeding_problem_present": "Co, toi qua be non 2 lan.",
               "fluid_retention": "Uong oresol tung thia van giu duoc.",
               "fever_present": "Ko a, be ko sot.",
               "temperature": "Em do nhiet ke duoc 37 do 2.",
               "activity_level": "Be van choi, chi quay hon moi khi chut.",
               "dehydration_visible_signs": "Be khoc van co nuoc mat.",
               "urine_output_level": "Ta van uot deu nhu moi ngay.",
               "spo2": "May kep ngon chan bao 98.",
               "heart_rate": "May bao mach mot tram ba muoi sau.",
               "symptom_duration_bucket": "Tu toi qua toi gio."},
      review_concern="Trẻ 2 tuổi tỉnh, chơi được, không sốt, giữ được nước uống: mạch 136 nằm trong giới hạn bình thường "
                     "80–140 của nhóm 1–3 tuổi (AHRQ Bảng 4) và chưa tới ngưỡng nguy hiểm > 140 của tuổi này (Decision "
                     "Point D, Bảng 5); corpus dùng ngưỡng người lớn (121–149) nên xếp ESI 2, trong khi theo AHRQ ca này "
                     "nhiều khả năng là ESI 4 hoặc 5 (bù nước đường uống).",
      tags=("pediatric", "caregiver", "age_adjusted_vitals", "colloquial_vitals", "no_diacritics"),
      test="Mạch 'mot tram ba muoi sau' đo ở ngón chân trẻ 2 tuổi tiêu chảy nhẹ: corpus dùng ngưỡng người lớn nên ra ESI 2 "
           "dù với tuổi này là bình thường; ca đo xem agent đọc đúng con số viết không dấu, còn chênh lệch với AHRQ được đưa "
           "sang hàng chờ duyệt."),

    S("m141", "spoken_slow_pulse_39_vs_44_pair", "Cụ bà Alzheimer mới tăng liều donepezil, choáng, ăn kém; người giúp việc nhắn nhịp tim 'ba mươi chín'",
      P(82, "Female", "PARENT", chronic=("Bệnh Alzheimer", "Tăng huyết áp"),
        meds=("Donepezil 10 mg mỗi tối", "Amlodipin 5 mg mỗi sáng")),
      "Mẹ tôi 82 tuổi bị Alzheimer, tháng trước bác sĩ tăng thuốc donepezil lên 10 mg. Mấy hôm nay mẹ hay choáng, đứng lên "
      "là phải vịn tường, ăn kém, hay buồn nôn. Tôi đang ở cơ quan, chị giúp việc ở nhà vừa nhắn là đo máy cho mẹ được huyết "
      "áp 124 trên 70, còn nhịp tim máy báo ba mươi chín. Chị ấy bảo mẹ vẫn nhận ra người nhà, nói chuyện như mọi ngày, "
      "không ngã, không ngất.",
      {"heart_rate": 39, "systolic_bp": 124, "diastolic_bp": 70, "dizziness_present": "YES",
       "dizziness_sensation": "LIGHTHEADED", "oral_intake_tolerance": "REDUCED", "gastrointestinal_symptom_present": "YES",
       "vomiting_present": "NO", "syncope_present": "NO", "trauma_present": "NO", "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      2, screen="", concepts=("dizziness", "cardiac_arrhythmia", "recent_medication_change"),
      answers={"heart_rate": "Chị giúp việc nhắn máy báo nhịp tim ba mươi chín, chị ấy đo hai lần đều vậy.",
               "systolic_bp": "Huyết áp 124 trên 70.",
               "diastolic_bp": "Số dưới là 70.",
               "dizziness_present": "Có, mẹ hay choáng, đứng lên là phải vịn tường.",
               "dizziness_sensation": "Choáng váng như muốn ngã, chị giúp việc bảo mẹ không kêu nhà quay.",
               "oral_intake_tolerance": "Mẹ ăn kém hẳn, mỗi bữa vài thìa.",
               "gastrointestinal_symptom_present": "Có, mẹ hay buồn nôn.",
               "vomiting_present": "Không, mẹ buồn nôn chứ chưa nôn.",
               "syncope_present": "Không, chị giúp việc bảo mẹ không ngất lần nào.",
               "trauma_present": "Không, mẹ không bị ngã, không va đập gì.",
               "altered_mental_status_present": "Không, mẹ vẫn nhận ra người nhà, nói chuyện như mọi ngày.",
               "symptom_duration_bucket": "Mấy hôm nay rồi, từ đầu tuần."},
      tags=("older_adult", "caregiver_remote", "baseline_cognitive_impairment", "polypharmacy", "collateral_history",
            "minimal_pair", "boundary_value", "colloquial_vitals"),
      test="Cặp tối thiểu với m142: nhịp tim 'ba mươi chín' do người giúp việc nhắn lại nằm dưới ngưỡng ≤ 40 nên ESI 2 dù "
           "huyết áp bình thường và bà không ngất; agent phải giữ con số do người thứ hai báo và không hạ mức vì bà 'vẫn "
           "như mọi ngày'."),

    S("m142", "spoken_slow_pulse_39_vs_44_pair", "Người chạy bộ đường dài bị cảm, đồng hồ rung báo 'nhịp tim thấp', đo lại 44, viết tắt",
      P(27, "Male"),
      "Mình 27t, chạy bộ đường dài 4 năm nay, tuần nào cũng chạy 50-60 km. 2 hôm nay bị cảm, đau họng, sổ mũi, ko sốt. "
      "Đêm qua đồng hồ thông minh rung báo 'nhịp tim thấp', sáng ngủ dậy nằm đo lại thì 44. Mình ko chóng mặt, ko ngất, "
      "ko tức ngực, vẫn đi làm bt. Có cần đi khám gấp ko?",
      {"heart_rate": 44, "sore_throat_present": "YES", "runny_nose_present": "YES", "fever_present": "NO",
       "dizziness_present": "NO", "syncope_present": "NO", "chest_pain_present": "NO",
       "cardiorespiratory_symptom_present": "NO", "functional_status": "NORMAL",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("sore_throat", "runny_nose"),
      answers={"heart_rate": "Sáng nằm đo lại đồng hồ báo 44.",
               "sore_throat_present": "Có, đau họng 2 hôm nay.",
               "runny_nose_present": "Có, sổ mũi.",
               "fever_present": "Ko sốt.",
               "dizziness_present": "Ko chóng mặt.",
               "syncope_present": "Ko ngất lần nào.",
               "chest_pain_present": "Ko tức ngực, ko đau ngực.",
               "cardiorespiratory_symptom_present": "Ko đau ngực, ko khó thở, ko thấy tim đập lạ.",
               "functional_status": "Vẫn đi làm bt.",
               "symptom_duration_bucket": "Cảm 2 hôm nay, đồng hồ báo từ đêm qua."},
      tags=("minimal_pair", "boundary_value", "abbreviation", "negation", "colloquial_vitals"),
      test="Cặp tối thiểu với m141: nhịp tim 44 ở người chạy bộ đường dài nằm trên ngưỡng ≤ 40, không ngất, không triệu "
           "chứng tim, nên không tiêu chí nào khớp và kỳ vọng là chuyển nhân viên y tế; agent không được nâng lên ESI 2 chỉ "
           "vì đồng hồ báo 'nhịp tim thấp', cũng không tự kết luận là bình thường."),

    S("m143", "detox_fasting_sglt2_deep_rapid_breathing", "Cụ bà tiểu đường nhịn ăn 'thải độc' vẫn uống thuốc, nôn, đau bụng 6/10, con gái đếm thở 'đúng ba chục'",
      P(66, "Female", "PARENT", chronic=("Đái tháo đường type 2", "Tăng huyết áp"),
        meds=("Empagliflozin 10 mg mỗi sáng", "Metformin 1000 mg chia hai lần", "Losartan 50 mg mỗi sáng")),
      "Mẹ em 66 tuổi bị tiểu đường, đang uống ba thứ thuốc. Mẹ nghe người ta mách nhịn ăn ba ngày để thải độc, chỉ uống "
      "nước lọc mà thuốc thì vẫn uống đều. Từ chiều qua mẹ buồn nôn, nôn ba bốn lần, uống nước vào cũng nôn ra, đau bụng "
      "quanh rốn chừng 6 điểm, người mệt lả, thở nhanh và sâu. Em đếm nhịp thở của mẹ được đúng ba chục cái một phút. Mẹ "
      "vẫn tỉnh, trả lời được. Em thử đường huyết bằng máy thì chỉ có 9 chấm 6, không cao, nên em không hiểu sao mẹ mệt vậy.",
      {"vomiting_present": "YES", "vomiting_frequency": "FEW_TIMES", "oral_intake_tolerance": "UNABLE_TO_KEEP_DOWN",
       "gastrointestinal_symptom_present": "YES", "abdominal_pain_present": "YES",
       "abdominal_pain_location": "AROUND_UMBILICUS", "pain_present": "YES", "pain_severity": 6,
       "associated_systemic_symptoms": "GENERAL_WEAKNESS", "respiratory_rate": 30, "dyspnea_present": "NO",
       "altered_mental_status_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen="", concepts=("tachypnea", "vomiting", "abdominal_pain", "diabetes_mellitus"),
      answers={"vomiting_present": "Có, mẹ nôn từ chiều qua.",
               "vomiting_frequency": "Nôn ba bốn lần rồi.",
               "oral_intake_tolerance": "Mẹ nhịn ăn ba hôm, giờ uống nước vào cũng nôn ra.",
               "gastrointestinal_symptom_present": "Có, mẹ buồn nôn, nôn, đau bụng.",
               "abdominal_pain_present": "Có, mẹ đau bụng quanh rốn.",
               "abdominal_pain_location": "Quanh rốn.",
               "pain_present": "Có, mẹ đau bụng.",
               "pain_severity": "Mẹ bảo chừng 6 điểm.",
               "associated_systemic_symptoms": "Mẹ mệt lả người.",
               "respiratory_rate": "Em đếm đúng một phút được ba chục cái.",
               "dyspnea_present": "Mẹ không kêu hụt hơi, chỉ là em thấy mẹ thở nhanh và sâu.",
               "altered_mental_status_present": "Không, mẹ vẫn tỉnh, trả lời được.",
               "symptom_duration_bucket": "Nôn với đau bụng từ chiều qua, tới giờ chưa được một ngày."},
      tags=("older_adult", "caregiver", "comorbidity", "polypharmacy", "boundary_value", "colloquial_vitals",
            "collateral_history", "hidden_red_flag"),
      test="Nhịp thở 'đúng ba chục' do con gái đếm nằm đúng ngưỡng ≥ 30 và cùng đau bụng 6/10 cho ESI 2; con số đường huyết "
           "9,6 'không cao' là chi tiết trấn an sai, agent phải dựa vào nhịp thở chứ không hạ mức vì đường huyết bình thường."),

    S("m144", "kidney_stone_colic_returning_after_pharmacy_shot", "Có sỏi thận, đỡ sau mũi tiêm ở hiệu thuốc rồi đau tăng lại; vợ kể 'đau lắm' nhưng chấm 6/10 khi được hỏi",
      P(41, "Male", "SPOUSE", chronic=("Sỏi thận",)),
      "Chồng em 41 tuổi có sỏi thận. Từ sáng anh ấy đau quặn hông lưng bên trái lan xuống bẹn, trưa ra hiệu thuốc tiêm một "
      "mũi giảm đau thì đỡ, nhưng từ chiều lại đau tăng dần lên, anh ấy kêu đau lắm. Anh ấy nôn hai lần, nước tiểu hơi "
      "hồng. Không sốt, em cặp nhiệt được 37 độ 1.",
      {"genitourinary_pain_present": "YES", "genitourinary_pain_location": "FLANK",
       "genitourinary_pain_laterality": "LEFT", "genitourinary_pain_radiation": "TO_GROIN", "pain_present": "YES",
       "pain_severity": 6, "symptom_trend": "WORSENING", "vomiting_present": "YES", "vomiting_frequency": "FEW_TIMES",
       "gastrointestinal_symptom_present": "YES", "urinary_symptom_present": "YES", "urine_appearance": "PINK_OR_RED",
       "fever_present": "NO", "temperature": 37.1, "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      3, screen=QUIET, concepts=("flank_pain", "vomiting", "urine_color_change"),
      answers={"genitourinary_pain_present": "Có, anh ấy đau quặn hông lưng bên trái.",
               "genitourinary_pain_location": "Đau ở hông lưng.",
               "genitourinary_pain_laterality": "Bên trái.",
               "genitourinary_pain_radiation": "Lan xuống bẹn trái.",
               "pain_present": "Có, anh ấy đau quặn hông lưng.",
               "pain_severity": "Em hỏi kỹ thì anh ấy chấm 6 trên 10, bảo kêu đau lắm vì sợ nó lên như lúc sáng chưa tiêm.",
               "symptom_trend": "Tiêm xong thì đỡ, từ chiều lại đau tăng dần lên.",
               "vomiting_present": "Có, nôn hai lần.",
               "vomiting_frequency": "Hai lần thôi.",
               "gastrointestinal_symptom_present": "Có, anh ấy nôn hai lần.",
               "urinary_symptom_present": "Có, nước tiểu hơi hồng.",
               "urine_appearance": "Nước tiểu hơi hồng.",
               "fever_present": "Không sốt.",
               "temperature": "Em cặp nhiệt được 37 độ 1.",
               "symptom_duration_bucket": "Từ sáng nay tới giờ."},
      tags=("caregiver", "comorbidity", "progressive_disclosure", "minimization"),
      test="Lời kể chỉ nói 'đau lắm', điểm đau 6/10 chỉ có khi agent hỏi (tiết lộ muộn có chủ đích): đau vừa tăng dần cho ESI 3, "
           "còn nếu agent tự hiểu 'đau lắm' thành từ 7 trở lên thì sẽ nâng nhầm lên ESI 2; khác m95 ở chỗ không sốt (37,1, dưới "
           "ngưỡng 38 của tiêu chí sốt kèm đau hông lưng) và không đo mạch."),

    S("m145", "spoken_temperature_40_2_vs_39_8_pair", "Giáo viên trường nội trú: nữ sinh 15 tuổi giữa đợt cúm, nhiệt kế 'bốn mươi độ hai', mạch 114",
      P(15, "Female", "OTHER"),
      "Tôi là giáo viên chủ nhiệm ở một trường nội trú. Ký túc xá đang có nhiều em bị cúm. Một em nữ lớp 10, 15 tuổi, từ "
      "chiều qua sốt, ho, đau đầu, đau mỏi người, sáng nay em nằm lả trên giường, chỉ ăn được vài thìa cháo. Tôi đo nhiệt "
      "kế điện tử được bốn mươi độ hai, kẹp máy đo ô xy vào ngón tay thì máy báo 97, mạch một trăm mười bốn. Em vẫn tỉnh, "
      "trả lời tôi rõ ràng, cổ cúi được.",
      {"fever_present": "YES", "temperature": 40.2, "cough_present": "YES", "headache_present": "YES",
       "pain_present": "YES", "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS", "functional_status": "MARKEDLY_REDUCED",
       "oral_intake_tolerance": "REDUCED", "spo2": 97, "heart_rate": 114, "altered_mental_status_present": "NO",
       "neck_stiffness_present": "NO", "similar_symptoms_in_others": "YES",
       "infection_source_symptom_group": "RESPIRATORY", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen="", concepts=("fever", "cough", "headache", "tachycardia"),
      answers={"fever_present": "Có, em ấy sốt từ chiều qua.",
               "temperature": "Nhiệt kế điện tử đo được bốn mươi độ hai.",
               "cough_present": "Có, em ấy ho.",
               "headache_present": "Có, em ấy kêu đau đầu.",
               "pain_present": "Có, đau đầu với đau mỏi người.",
               "associated_systemic_symptoms": "Vừa sốt vừa mệt lả.",
               "functional_status": "Sáng nay em ấy chỉ nằm lả trên giường.",
               "oral_intake_tolerance": "Chỉ ăn được vài thìa cháo.",
               "spo2": "Máy kẹp ngón báo 97.",
               "heart_rate": "Máy báo mạch một trăm mười bốn.",
               "altered_mental_status_present": "Không, em ấy vẫn tỉnh, trả lời rõ ràng.",
               "neck_stiffness_present": "Không, cổ em ấy cúi được bình thường.",
               "similar_symptoms_in_others": "Có, ký túc xá đang có nhiều em bị cúm.",
               "infection_source_symptom_group": "Ngoài sốt thì chủ yếu ho, đau đầu.",
               "symptom_duration_bucket": "Từ chiều qua tới giờ."},
      unknown={"pain_severity": "Em ấy chỉ bảo đau đầu, mỏi người, không chấm được mấy điểm."},
      tags=("adolescent", "collateral_history", "minimal_pair", "boundary_value", "colloquial_vitals",
            "multiple_complaints"),
      test="Cặp tối thiểu với m146: 'bốn mươi độ hai' vượt ngưỡng 40 và mạch 114 vượt 110 nên tiêu chí sốt cao kèm mạch nhanh "
           "cho ESI 2; người kể là giáo viên nội trú, agent phải giữ đúng hai con số và không coi là cúm thông thường chỉ vì "
           "cả ký túc xá đang bị."),

    S("m146", "spoken_temperature_40_2_vs_39_8_pair", "Người bán bún giọng miền Trung sốt, nhức mỏi 5/10, ăn không vô; nhiệt kế 'lên tới vạch 39 độ 8'",
      P(52, "Female", allergies=("Aspirin",)),
      "Tui 52 tuổi, bán bún ngoài chợ. Từ hôm kia tui bị sốt, nhức đầu, đau mỏi khắp mình mẩy chừng 5 điểm, ho khan lai "
      "rai, ăn chi cũng không vô, mỗi bữa vài muỗng cháo. Tối ni tui cặp nhiệt kế thuỷ ngân thì lên tới vạch 39 độ 8, gần "
      "chạm 40. Nhà không có máy đo huyết áp chi hết. Tui vẫn đi lại trong nhà được, không khó thở. Răng mà sốt dữ rứa hè?",
      {"fever_present": "YES", "temperature": 39.8, "headache_present": "YES", "pain_present": "YES",
       "pain_severity": 5, "cough_present": "YES", "cough_character": "DRY", "oral_intake_tolerance": "REDUCED",
       "dyspnea_present": "NO", "functional_status": "REDUCED", "infection_source_symptom_group": "MULTIPLE",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, screen=QUIET, concepts=("fever", "myalgia", "headache"),
      answers={"fever_present": "Có, tui sốt từ hôm kia.",
               "temperature": "Nhiệt kế thuỷ ngân lên tới vạch 39 độ 8, chưa tới 40.",
               "headache_present": "Có, nhức đầu.",
               "pain_present": "Có, nhức đầu với đau mỏi khắp mình mẩy.",
               "pain_severity": "Chừng 5 điểm.",
               "cough_present": "Có, ho khan lai rai.",
               "cough_character": "Ho khan, không có đàm.",
               "oral_intake_tolerance": "Ăn chi cũng không vô, mỗi bữa vài muỗng cháo.",
               "dyspnea_present": "Không, tui không khó thở.",
               "functional_status": "Tui vẫn đi lại trong nhà được, chỉ mệt hơn mọi bữa.",
               "infection_source_symptom_group": "Nhức đầu, mỏi mình mẩy là chính, có ho khan lai rai.",
               "symptom_duration_bucket": "Từ hôm kia tới chừ."},
      unknown={"heart_rate": "Nhà tui không có máy đo chi hết, tui không biết đếm mạch.",
               "systolic_bp": "Nhà không có máy đo huyết áp nên tui không biết."},
      tags=("dialect", "minimal_pair", "boundary_value", "colloquial_vitals", "missing_vitals", "multiple_complaints"),
      test="Cặp tối thiểu với m145: nhiệt kế 'lên tới vạch 39 độ 8, gần chạm 40' vẫn dưới ngưỡng 40 và không có mạch đo được, "
           "nên chỉ có tiêu chí sốt kèm ăn kém, đau vừa (ESI 3); agent không được làm tròn thành 40 độ để nâng lên ESI 2, "
           "cũng không được đoán mạch khi nhà không có máy đo."),
]
