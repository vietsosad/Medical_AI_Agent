"""Nhóm COMMON, đợt 2 (phần a): lý do đi khám thường gặp, một than phiền chính, đủ dữ kiện.

Trọng tâm đợt 2: các kiểu đau ngực chưa có ở đợt 1 (nặng ngực khi gắng sức, thắt ngực lan
hàm, nặng ngực lan hai tay, tức ngực kèm SpO2 thấp, thắt ngực dữ dội), đau bụng trên lan
ngực hoặc vai, đau vùng chậu và trên xương mu, nôn dịch vàng xanh, bí trung đại tiện, táo
bón kéo dài và tiêu chảy chỉ uống được nước. Thêm bốn than phiền lành tính vùng tiêu hoá
hoặc quanh ngực mà corpus không có tiêu chí (kỳ vọng RETURN_INCOMPLETE) và ba ca ESI 4/5
mà số nguồn lực là phán đoán của người viết (vào hàng chờ duyệt).

Ca tiêu chảy c68 không mở cổng ``constipation_or_defecation_problem_present`` (người bệnh tiêu
chảy không bị táo bón), nên các tiêu chí ``stool_consistency`` không với tới được; mức ESI 3 của
ca này dựa vào số nguồn lực do người viết dự đoán.
"""

from __future__ import annotations

from eval.generated_mock_v2.spec import COMMON, INCOMPLETE, P, SCREEN_HIT as HIT, SCREEN_QUIET as QUIET, Spec


def S(key: str, family: str, title: str, profile: dict, opening: str, facts: dict, intended, **kw) -> Spec:
    return Spec(case_id=key, family=family, group=COMMON, title=title, profile=profile,
                opening=opening, facts=facts, intended=intended, **kw)


SPECS = [
    # ------------------------------------------------------------------ đau ngực
    S("c51", "exertional_chest_heaviness_diabetic_woman", "Nặng ngực mỗi khi gánh hàng, phụ nữ đái tháo đường",
      P(56, "Female", chronic=("Đái tháo đường type 2",), meds=("Metformin", "Gliclazide")),
      "Chị 56 tuổi, bị tiểu đường mấy năm nay. Chừng mười ngày nay cứ gánh hàng ra chợ hay đạp xe lên dốc là thấy "
      "nặng ở giữa ngực, phải dừng lại nghỉ năm phút mới đỡ. Sáng nay gánh hàng lên dốc lại bị hai lần, lần sau ngồi "
      "nghỉ mười phút rồi mà vẫn còn nằng nặng chưa hết hẳn, chắc 3 trên 10. Không lan đi đâu, không khó thở.",
      {"chest_pain_present": "YES", "chest_pain_quality": "HEAVINESS", "chest_pain_location": "CENTRAL",
       "chest_pain_radiation": "NONE", "cardiorespiratory_symptom_present": "YES",
       "exertional_relation": "TRIGGERED_BY_EXERTION", "dyspnea_present": "NO", "pain_present": "YES",
       "pain_severity": 3, "symptom_duration_bucket": "OVER_7_DAYS"},
      2, concepts=("chest_pain",), screen=QUIET, tags=("comorbidity",),
      answers={"exertional_relation": "Cứ gánh nặng hay đạp xe lên dốc là bị, ngồi nghỉ thì đỡ dần; lần sáng nay "
                                      "nghỉ rồi vẫn còn nằng nặng chưa hết hẳn.",
               "symptom_duration_bucket": "Bị đi bị lại chừng mười ngày nay rồi.",
               "cardiorespiratory_symptom_present": "Có, nặng ở ngực như chị vừa kể.",
               "chest_pain_location": "Ở giữa ngực."},
      test="Nặng ngực khởi phát khi gắng sức ở phụ nữ đái tháo đường, lúc kể chỉ còn 3/10; agent không được hạ mức "
           "vì đau ít hay vì đã đỡ khi nghỉ."),
    S("c52", "chest_pressure_worse_on_stairs_central_dialect", "Tức ngực từ sáng, lên cầu thang thì nặng hơn",
      P(68, "Male", chronic=("Tăng huyết áp", "Rối loạn mỡ máu"), meds=("Amlodipin", "Atorvastatin")),
      "Tui 68 tuổi. Từ sáng tới chừ cứ thấy tức giữa ngực như có ai đè lên, ngồi yên thì âm ỉ, mà hễ đi lên cầu "
      "thang hay quét cái sân là đè nặng hơn rõ. Đau chừng 5 điểm, không lan mô hết, thở cũng bình thường. "
      "Rứa có răng không con?",
      {"chest_pain_present": "YES", "chest_pain_quality": "PRESSURE", "chest_pain_location": "CENTRAL",
       "chest_pain_radiation": "NONE", "cardiorespiratory_symptom_present": "YES",
       "exertional_relation": "WORSE_WITH_EXERTION", "dyspnea_present": "NO", "pain_present": "YES",
       "pain_severity": 5, "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("chest_pain",), screen=QUIET, tags=("dialect", "older_adult", "comorbidity"),
      answers={"exertional_relation": "Ngồi yên thì âm ỉ, đi lên cầu thang hay quét sân là tức nặng hơn liền.",
               "symptom_duration_bucket": "Từ sáng sớm tới chừ, chắc cũng sáu bảy tiếng.",
               "chest_pain_radiation": "Không lan mô hết, tức ngay giữa ngực thôi.",
               "dyspnea_present": "Thở vẫn bình thường, không hụt hơi.",
               "cardiorespiratory_symptom_present": "Có, tức ngực như tui nói đó.",
               "pain_severity": "Chừng 5 điểm."},
      test="Tức ngực liên tục, nặng lên khi gắng sức ở người cao tuổi nói giọng miền Trung (chừ, mô, rứa, răng); "
           "agent phải hiểu phương ngữ và không cần có hướng lan mới xếp mức."),
    S("c53", "chest_tightness_to_jaw_after_argument", "Thắt ngực lan lên hàm khi đang cãi nhau",
      P(51, "Female", chronic=("Rối loạn mỡ máu",), meds=("Rosuvastatin",)),
      "Chị 51 tuổi. Cách đây chừng 20 phút đang to tiếng với thằng con thì tự nhiên ngực thắt chặt lại, cảm giác "
      "bó lan lên tận quai hàm, đến giờ vẫn chưa hết. Chị đi lại hay ngồi xuống cũng vậy, không đỡ mà cũng không "
      "tăng. Đau tầm 5 điểm.",
      {"chest_pain_present": "YES", "chest_pain_quality": "TIGHTNESS", "chest_pain_radiation": "JAW",
       "cardiorespiratory_symptom_present": "YES", "exertional_relation": "NOT_RELATED_TO_EXERTION",
       "symptom_onset": "SUDDEN", "symptom_trend": "CONSTANT", "pain_present": "YES", "pain_severity": 5,
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("chest_tightness", "jaw_pain"), screen=HIT, tags=("emotional_trigger",),
      answers={"exertional_relation": "Không phải lúc gắng sức, chị đang đứng cãi nhau thôi; đi lại hay ngồi cũng vậy.",
               "symptom_trend": "Vẫn y như lúc đầu, không đỡ mà cũng không tăng.",
               "chest_pain_radiation": "Lan lên tận quai hàm.",
               "symptom_onset": "Tự nhiên thắt lại một cái, không từ từ.",
               "symptom_duration_bucket": "Mới chừng 20 phút.",
               "cardiorespiratory_symptom_present": "Có, ngực thắt lại như chị kể."},
      test="Thắt ngực lan hàm khởi phát khi xúc động, không liên quan gắng sức, đau mức vừa; hướng lan lên hàm là "
           "chi tiết quyết định."),
    S("c54", "nocturnal_chest_heaviness_both_arms_af", "Cụ ông rung nhĩ thức giấc vì nặng ngực lan hai tay",
      P(72, "Male", "SPOUSE", chronic=("Rung nhĩ", "Tăng huyết áp"), allergies=("Aspirin",),
        meds=("Rivaroxaban", "Bisoprolol")),
      "Ông nhà tôi 72 tuổi, bị rung nhĩ đang uống thuốc chống đông. Gần 4 giờ sáng ông trở dậy kêu nặng ngực, "
      "nặng lan xuống cả hai cánh tay. Ông nằm im không làm gì mà vẫn không đỡ, đến giờ gần hai tiếng rồi, ông "
      "bảo khoảng 6 điểm.",
      {"chest_pain_present": "YES", "chest_pain_quality": "HEAVINESS", "chest_pain_radiation": "BOTH_ARMS",
       "cardiorespiratory_symptom_present": "YES", "exertional_relation": "OCCURS_AT_REST",
       "pain_present": "YES", "pain_severity": 6, "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("chest_pain",), screen=HIT, tags=("older_adult", "caregiver", "anticoagulant", "comorbidity"),
      answers={"chest_pain_quality": "Ông bảo nặng trĩu trong ngực.",
               "exertional_relation": "Đang ngủ thì bị, nằm im cũng không đỡ.",
               "chest_pain_radiation": "Ông bảo nặng lan xuống cả hai tay.",
               "symptom_duration_bucket": "Từ gần 4 giờ sáng, được chừng hai tiếng.",
               "pain_severity": "Ông bảo khoảng 6 điểm.",
               "cardiorespiratory_symptom_present": "Có, ông kêu nặng ngực."},
      test="Nặng ngực lúc nghỉ lan xuống cả hai tay ở người cao tuổi dùng thuốc chống đông và dị ứng aspirin; agent "
           "chỉ gợi ý mức, không được khuyên dùng thuốc."),
    S("c55", "central_chest_pressure_low_spo2_home_oximeter", "Tức đè giữa ngực, máy kẹp ngón báo SpO2 90%",
      P(69, "Female", chronic=("Tăng huyết áp",), allergies=("Penicillin",), meds=("Losartan",)),
      "Tôi 69 tuổi, khoảng 40 phút nay thấy tức ở giữa ngực, như có vật nặng đè lên, người hơi hụt hơi. Con gái "
      "lấy cái máy kẹp ngón tay mua hồi dịch ra đo, SpO2 có 90%, đo lại lần nữa cũng 90. Đau chừng 4 điểm, không "
      "lan đi đâu.",
      {"chest_pain_present": "YES", "chest_pain_quality": "PRESSURE", "chest_pain_location": "CENTRAL",
       "chest_pain_radiation": "NONE", "cardiorespiratory_symptom_present": "YES", "dyspnea_present": "YES",
       "spo2": 90, "pain_present": "YES", "pain_severity": 4, "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("chest_pain", "shortness_of_breath"), screen=QUIET, tags=("older_adult", "comorbidity"),
      answers={"chest_pain_quality": "Như có vật nặng đè ép lên ngực.",
               "dyspnea_present": "Có, hơi hụt hơi.",
               "spo2": "Máy kẹp ngón tay đo hai lần đều 90%.",
               "symptom_duration_bucket": "Khoảng 40 phút nay."},
      test="Tức đè giữa ngực kèm SpO2 90% đo bằng máy tại nhà; sinh hiệu có nguồn đo rõ, agent phải dùng con số chứ "
           "không chỉ dựa vào mức đau 4/10."),
    S("c56", "sudden_severe_chest_tightness_taxi_driver", "Tài xế đột ngột thắt ngực dữ dội 8/10",
      P(44, "Male"),
      "Em chạy taxi, 44 tuổi, hút thuốc lá hơn chục năm. Khoảng nửa tiếng trước đang ngồi lái xe chở khách, không "
      "làm gì nặng, thì tự nhiên ngực bó thắt lại rất dữ, phải tấp xe vào lề, giờ vẫn còn, chấm chắc 8/10. Không lan "
      "ra tay hay lên hàm.",
      {"chest_pain_present": "YES", "chest_pain_quality": "TIGHTNESS", "chest_pain_radiation": "NONE",
       "cardiorespiratory_symptom_present": "YES", "exertional_relation": "OCCURS_AT_REST",
       "symptom_onset": "SUDDEN", "pain_present": "YES", "pain_severity": 8,
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("chest_tightness",), screen=QUIET, tags=("single_decisive_symptom",),
      answers={"exertional_relation": "Đang ngồi lái xe thì bị, không phải lúc gắng sức gì.",
               "symptom_onset": "Tự nhiên bó thắt lại, đột ngột luôn.",
               "symptom_duration_bucket": "Khoảng nửa tiếng nay.",
               "chest_pain_radiation": "Không lan ra tay hay lên hàm, chỉ ở ngực."},
      test="Thắt ngực dữ dội 8/10 khởi phát đột ngột lúc đang ngồi nghỉ lái xe, không lan; mức đau và hoàn cảnh lúc "
           "nghỉ là chi tiết quyết định, agent không được chờ có hướng lan."),
    # ------------------------------------------------------------------ đau bụng trên, nôn dịch mật
    S("c57", "epigastric_pain_to_chest_diabetic_no_diacritics", "Đau thượng vị lan lên ngực, gõ không dấu",
      P(63, "Male", chronic=("Đái tháo đường type 2", "Tăng huyết áp"), meds=("Metformin", "Losartan")),
      "Toi 63 tuoi, bi tieu duong. Tu 4h sang nay dau vung tren ron, dau lan nguoc len nguc, khoang 7/10, den gio "
      "da 5 tieng. Uong thuoc da day ma ko do. Khong non, khong sot.",
      {"abdominal_pain_present": "YES", "abdominal_pain_location": "UPPER_ABDOMEN",
       "abdominal_pain_radiation": "CHEST", "chest_pain_present": "YES", "gastrointestinal_symptom_present": "YES",
       "pain_present": "YES", "pain_severity": 7, "vomiting_present": "NO", "fever_present": "NO",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("epigastric_pain",), screen=QUIET, tags=("no_diacritics", "abbreviation", "comorbidity"),
      answers={"abdominal_pain_present": "Co, dau vung tren ron.",
               "abdominal_pain_location": "Vung tren ron, cho thuong vi.",
               "abdominal_pain_radiation": "Lan nguoc len nguc.",
               "chest_pain_present": "Co, dau tu tren ron lan len nguc.",
               "gastrointestinal_symptom_present": "Co, dau bung tren nhu toi ke.",
               "pain_present": "Co.",
               "pain_severity": "Khoang 7/10.",
               "vomiting_present": "Khong non.",
               "fever_present": "Khong sot.",
               "symptom_duration_bucket": "Tu 4h sang, duoc 5 tieng roi."},
      confirmation="Dung roi, thong tin nhu vay.",
      test="Đau thượng vị lan lên ngực 7/10 ở người đái tháo đường, viết không dấu; agent không được coi là bệnh dạ "
           "dày rồi hạ mức."),
    S("c58", "postprandial_upper_right_pain_to_shoulder", "Đau bụng trên lệch phải lan lên vai sau bữa nhiều dầu mỡ",
      P(46, "Female", chronic=("Sỏi túi mật phát hiện qua siêu âm năm ngoái",)),
      "Tôi 46 tuổi, năm ngoái đi siêu âm có thấy sỏi túi mật. Tối nay ăn cỗ toàn đồ chiên rán, xong được hai tiếng "
      "thì đau dữ ở bụng trên lệch phải, đau lan lên vai phải, chắc 8/10, nôn một lần ra thức ăn. Tôi không sốt.",
      {"abdominal_pain_present": "YES", "abdominal_pain_location": "UPPER_ABDOMEN",
       "abdominal_pain_radiation": "SHOULDER", "gastrointestinal_symptom_present": "YES",
       "meal_relationship": "WORSE_AFTER_EATING", "pain_present": "YES", "pain_severity": 8,
       "vomiting_present": "YES", "vomiting_frequency": "ONCE", "vomit_appearance": "FOOD_CONTENT",
       "fever_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("abdominal_pain", "shoulder_pain"), screen=QUIET, tags=("comorbidity",),
      answers={"abdominal_pain_location": "Bụng trên, lệch về bên phải, ngay dưới sườn.",
               "abdominal_pain_radiation": "Lan lên vai phải.",
               "meal_relationship": "Ăn bữa nhiều dầu mỡ xong là đau lên.",
               "symptom_duration_bucket": "Từ tối, được chừng ba tiếng rồi."},
      test="Đau bụng trên lan lên vai phải 8/10 sau bữa nhiều mỡ ở người đã biết có sỏi mật; agent không được nêu "
           "chẩn đoán dù người bệnh tự nhắc tiền sử."),
    S("c59", "child_bilious_vomiting_cramping_southern", "Trẻ 9 tuổi nôn dịch vàng xanh, đau quặn quanh rốn",
      P(9, "Male", "CHILD"),
      "Con trai em 9 tuổi, từ trưa tới giờ ói 3 lần, hai lần sau toàn nước vàng xanh đắng nghét. Bụng nó đau quặn "
      "từng cơn quanh rốn, nó nói đau cỡ 8, nằm co người lại hà. Hông có sốt, em đo nhiệt kế 37 độ.",
      {"vomiting_present": "YES", "vomiting_frequency": "FEW_TIMES", "vomit_appearance": "YELLOW_GREEN",
       "gastrointestinal_symptom_present": "YES", "abdominal_pain_present": "YES",
       "abdominal_pain_character": "CRAMPING", "abdominal_pain_location": "AROUND_UMBILICUS",
       "pain_present": "YES", "pain_severity": 8, "fever_present": "NO", "temperature": 37.0,
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("bilious_vomiting", "abdominal_cramping"), screen=QUIET,
      tags=("pediatric", "caregiver", "dialect"),
      answers={"vomiting_present": "Dạ có, nó ói 3 lần rồi á.",
               "vomiting_frequency": "Ói 3 lần rồi.",
               "vomit_appearance": "Hai lần sau ra toàn nước vàng xanh, nó nói đắng lắm.",
               "abdominal_pain_character": "Đau quặn từng cơn á.",
               "abdominal_pain_location": "Quanh rốn.",
               "pain_severity": "Nó nói đau cỡ 8.",
               "fever_present": "Hông có sốt.",
               "temperature": "Em đo nhiệt kế được 37 độ.",
               "symptom_duration_bucket": "Từ trưa tới giờ, mới mấy tiếng thôi."},
      test="Nôn dịch vàng xanh kèm đau quặn 8/10 ở trẻ, người mẹ nói giọng miền Nam (ói, hông, hà); màu dịch nôn là "
           "chi tiết quyết định."),
    # ------------------------------------------------------------------ vùng chậu, trên xương mu
    S("c60", "sudden_pelvic_pain_jump_rope", "Đột ngột đau nhói bụng dưới khi nhảy dây, que thử âm tính",
      P(26, "Female", allergies=("Ibuprofen",)),
      "Mình 26 tuổi, cách đây chừng 40 phút đang tập nhảy dây thì đột ngột đau nhói ở hố chậu bên trái, đau tới "
      "mức phải ngồi thụp xuống, giờ vẫn khoảng 8/10, hơi buồn nôn nhưng chưa nôn. Mình mới hết kinh 10 ngày, sáng "
      "nay thử que cũng một vạch.",
      {"abdominal_pain_present": "YES", "abdominal_pain_location": "LEFT_SIDE",
       "abdominal_pain_character": "SHARP", "pain_present": "YES", "pain_severity": 8, "symptom_onset": "SUDDEN",
       "pregnancy_present": "NO", "pregnancy_status": "NOT_PREGNANT", "vomiting_present": "NO",
       "gastrointestinal_symptom_present": "YES", "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("pelvic_pain", "lower_abdominal_pain"), screen=QUIET, tags=("single_decisive_symptom",),
      answers={"pregnancy_status": "Không có thai, mình mới hết kinh 10 ngày, que thử sáng nay một vạch.",
               "pregnancy_present": "Không, que thử sáng nay một vạch.",
               "abdominal_pain_location": "Ở hố chậu bên trái.",
               "symptom_onset": "Đột ngột, đang nhảy thì nhói một cái.",
               "vomiting_present": "Hơi buồn nôn nhưng chưa nôn.",
               "gastrointestinal_symptom_present": "Có, hơi buồn nôn.",
               "symptom_duration_bucket": "Mới chừng 40 phút."},
      test="Đau vùng chậu đột ngột dữ dội ở phụ nữ trẻ, que thử thai âm tính; agent phải hỏi đủ tình trạng thai trước "
           "khi xếp mức và không nêu chẩn đoán."),
    S("c61", "worsening_suprapubic_pain_pink_urine", "Đau trên xương mu tăng dần, nước tiểu hồng",
      P(35, "Female"),
      "Em bị tiểu buốt, tiểu rắt từ hôm kia, cứ uống nhiều nước nghĩ sẽ tự hết. Từ chiều nay đau tức trên xương mu "
      "cứ tăng dần, giờ chắc 8/10, nước tiểu có màu hồng. Em không sốt, không đau hông lưng, đang đặt vòng nên không "
      "có thai.",
      {"urinary_symptom_present": "YES", "urine_appearance": "PINK_OR_RED", "genitourinary_pain_present": "YES",
       "genitourinary_pain_location": "SUPRAPUBIC", "pain_present": "YES", "pain_severity": 8,
       "symptom_trend": "WORSENING", "symptom_onset": "GRADUAL", "fever_present": "NO",
       "pregnancy_status": "NOT_PREGNANT", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      2, concepts=("suprapubic_pain", "dysuria"), screen=QUIET, tags=("negation",),
      answers={"urinary_symptom_present": "Có, tiểu buốt, tiểu rắt, nước tiểu hồng hồng.",
               "urine_appearance": "Nước tiểu có màu hồng.",
               "genitourinary_pain_location": "Đau tức ngay trên xương mu.",
               "symptom_onset": "Tăng dần từ chiều chứ không phải đột ngột.",
               "symptom_trend": "Càng lúc càng đau hơn.",
               "pregnancy_status": "Không có thai, em đang đặt vòng.",
               "symptom_duration_bucket": "Tiểu buốt từ hôm kia, được hai ngày rồi."},
      review_concern="Decision Point B: bệnh cảnh giống viêm bàng quang có tiểu máu, không sốt, không đau hông lưng, "
                     "vẫn đi tiểu được; ESI 2 chỉ dựa vào điểm đau từ 7 trở lên, mà ở Decision Point B đau nặng là "
                     "phần để điều dưỡng tự cân nhắc. Phần lớn điều dưỡng sẽ xếp ESI 3 (xét nghiệm nước tiểu, có thể "
                     "thêm thuốc giảm đau đường tiêm).",
      test="Đau trên xương mu tăng dần lên 8/10 kèm nước tiểu hồng; xu hướng nặng lên và điểm đau cùng quyết định "
           "mức, agent không được coi như tiểu buốt thông thường."),
    # ------------------------------------------------------------------ bí trung đại tiện, táo bón kéo dài
    S("c62", "elderly_no_flatus_after_appendectomy", "Cụ ông gần hai ngày không xì hơi, không đi ngoài được",
      P(77, "Male", "PARENT", chronic=("Tăng huyết áp",), meds=("Amlodipin",)),
      "Bố tôi 77 tuổi, mười năm trước có mổ ruột thừa. Lần cuối ông đi ngoài là sáng hôm kia, gần hai ngày nay ông "
      "không xì hơi được chút nào, ngồi rặn mãi cũng không đi ngoài được, bụng chướng căng lên, đau quặn từng cơn ông "
      "bảo chừng 5 điểm. Ông chưa nôn nhưng ăn uống kém hẳn, cả ngày chỉ được lưng bát cháo.",
      {"constipation_or_defecation_problem_present": "YES", "gas_passage_status": "ABSENT",
       "defecation_effort": "UNABLE_TO_DEFECATE", "evacuation_completeness": "NO_STOOL_PASSED",
       "days_since_last_bowel_movement": 2, "gastrointestinal_symptom_present": "YES",
       "abdominal_pain_present": "YES", "abdominal_pain_character": "CRAMPING", "pain_present": "YES",
       "pain_severity": 5, "vomiting_present": "NO", "oral_intake_tolerance": "REDUCED",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      2, concepts=("obstipation", "abdominal_distension"), screen=QUIET, tags=("older_adult", "caregiver"),
      answers={"days_since_last_bowel_movement": "Lần cuối ông đi ngoài là sáng hôm kia.",
               "evacuation_completeness": "Ngồi lâu mà không ra được tí phân nào.",
               "gas_passage_status": "Gần hai ngày nay ông không xì hơi được chút nào.",
               "symptom_duration_bucket": "Gần hai ngày nay rồi.",
               "oral_intake_tolerance": "Ăn uống kém hẳn, cả ngày được lưng bát cháo.",
               "pain_severity": "Ông bảo chừng 5 điểm."},
      test="Không trung tiện và không đại tiện được ở người cao tuổi từng mổ bụng, đau chỉ 5/10; agent phải nhận ra "
           "tổ hợp này chứ không xếp như táo bón thường."),
    S("c63", "opioid_constipation_after_spine_surgery", "Mười hai ngày chưa đi ngoài khi đang dùng thuốc giảm đau sau mổ",
      P(39, "Female", chronic=("Thoát vị đĩa đệm thắt lưng, đã mổ cách đây hai tuần",),
        meds=("Tramadol", "Paracetamol")),
      "Mình mổ thoát vị đĩa đệm đc 2 tuần, về nhà vẫn uống thuốc giảm đau theo đơn. Lần cuối đi ngoài là 12 ngày "
      "trước, từ đó tới giờ chưa đi ngoài lại được tí nào, xì hơi cũng ít hẳn, bụng hơi chướng, đau âm ỉ chừng 3/10. "
      "Vẫn ăn uống bt, ko nôn.",
      {"constipation_or_defecation_problem_present": "YES", "days_since_last_bowel_movement": 12,
       "evacuation_completeness": "NO_STOOL_PASSED", "gas_passage_status": "REDUCED",
       "gastrointestinal_symptom_present": "YES", "abdominal_pain_present": "YES",
       "abdominal_pain_character": "DULL", "pain_present": "YES", "pain_severity": 3,
       "oral_intake_tolerance": "NORMAL", "vomiting_present": "NO", "symptom_duration_bucket": "OVER_7_DAYS"},
      2, concepts=("constipation", "abdominal_distension"), screen=QUIET, tags=("abbreviation",),
      answers={"days_since_last_bowel_movement": "Lần cuối đi ngoài là 12 ngày trước.",
               "evacuation_completeness": "Từ đó tới giờ chưa đi ra được tí nào.",
               "symptom_duration_bucket": "Hơn mười ngày rồi.",
               "gas_passage_status": "Xì hơi ít hẳn so với bt.",
               "oral_intake_tolerance": "Vẫn ăn uống bt.",
               "vomiting_present": "Ko nôn."},
      review_concern="Decision Point B: người bệnh vẫn ăn uống được, không nôn, còn xì hơi (chỉ ít đi), đau 3/10; nếu "
                     "không có dấu hiệu tắc ruột thì AHRQ nhiều khả năng xếp ESI 3 theo Decision Point C (dự kiến từ hai "
                     "nguồn lực: xét nghiệm, X-quang bụng, thụt tháo) chứ không coi là tình huống nguy cơ cao ESI 2.",
      test="Táo bón 12 ngày kèm giảm trung tiện ở người đang dùng thuốc giảm đau nhóm opioid sau mổ; số ngày là chi "
           "tiết quyết định dù đau chỉ 3/10."),
    # ------------------------------------------------------------------ ESI 3: táo bón, tiêu chảy
    S("c64", "hard_stool_incomplete_office_worker", "Phân cứng, rặn mạnh, đi không hết ở nhân viên văn phòng",
      P(33, "Male", chronic=("Hội chứng ruột kích thích",)),
      "Tôi làm văn phòng, ngồi suốt ngày, ít ăn rau. Gần hai tuần nay đi ngoài toàn phân cứng vón cục, phải rặn rất "
      "mạnh mới ra, đi xong vẫn thấy như còn. Bụng dưới đau quặn chừng 6/10. Không thấy máu, vẫn xì hơi bình thường, "
      "sáng qua mới đi được một ít.",
      {"constipation_or_defecation_problem_present": "YES", "stool_consistency": "HARD_LUMPY",
       "defecation_effort": "MARKED_STRAINING", "evacuation_completeness": "INCOMPLETE",
       "days_since_last_bowel_movement": 1, "gas_passage_status": "NORMAL",
       "gastrointestinal_symptom_present": "YES", "abdominal_pain_present": "YES",
       "abdominal_pain_location": "LOWER_ABDOMEN", "abdominal_pain_character": "CRAMPING", "pain_present": "YES",
       "pain_severity": 6, "blood_in_stool_present": "NO", "symptom_duration_bucket": "OVER_7_DAYS"},
      3, concepts=("constipation", "defecation_straining"), screen=QUIET, tags=("comorbidity",),
      answers={"days_since_last_bowel_movement": "Sáng hôm qua có đi được một ít.",
               "evacuation_completeness": "Đi xong vẫn thấy như còn, chưa hết.",
               "blood_in_stool_present": "Không thấy máu.",
               "symptom_duration_bucket": "Gần hai tuần nay rồi."},
      review_concern="Decision Point C: người trẻ có hội chứng ruột kích thích, vẫn xì hơi bình thường, hôm qua còn đi "
                     "ngoài được, đau 6/10; điều dưỡng thường dự kiến 0 đến 1 nguồn lực (có thể thụt tháo hoặc một phim "
                     "X-quang bụng) nên xếp ESI 4. Mức ESI 3 của corpus ngầm giả định cần từ hai nguồn lực trở lên.",
      test="Táo bón phân cứng kèm rặn mạnh, đi không hết và đau 6/10; agent phải ghép đủ các đặc điểm đại tiện chứ "
           "không chỉ hỏi số ngày."),
    S("c65", "child_pellet_stool_incomplete_six_days", "Bé 7 tuổi sáu ngày chỉ ra vài viên phân nhỏ",
      P(7, "Female", "CHILD"),
      "Bé nhà em 7 tuổi, lần cuối đi ngoài là 6 ngày trước, mà lần đó cũng chỉ ra mấy viên nhỏ xíu như phân dê rồi "
      "khóc kêu vẫn còn buồn đi, từ đó tới giờ chưa đi lại đc. Bé kêu đau bụng, em cho chỉ vào thang mặt cười thì bé "
      "chọn mức 6. Bé vẫn ăn cơm đc, ko sốt.",
      {"constipation_or_defecation_problem_present": "YES", "days_since_last_bowel_movement": 6,
       "stool_consistency": "PELLET_LIKE", "evacuation_completeness": "INCOMPLETE",
       "gastrointestinal_symptom_present": "YES", "abdominal_pain_present": "YES", "pain_present": "YES",
       "pain_severity": 6, "oral_intake_tolerance": "NORMAL", "fever_present": "NO",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, concepts=("constipation",), screen=QUIET, tags=("pediatric", "caregiver", "abbreviation"),
      answers={"days_since_last_bowel_movement": "Lần cuối bé đi ngoài là 6 ngày trước, từ đó chưa đi lại đc.",
               "stool_consistency": "Lần đó ra mấy viên nhỏ, cứng như phân dê.",
               "evacuation_completeness": "Lần đó đi xong bé vẫn kêu buồn đi tiếp, chưa hết.",
               "pain_severity": "Bé chỉ vào mặt số 6 trên thang.",
               "oral_intake_tolerance": "Bé vẫn ăn cơm đc như mọi hôm.",
               "symptom_duration_bucket": "Được 6 ngày rồi."},
      test="Táo bón ở trẻ 7 tuổi: lần đi ngoài cuối cách 6 ngày và đi không hết, trẻ tự chấm đau bằng thang mặt cười; "
           "agent phải ghép số ngày với cảm giác đi không hết."),
    S("c66", "pregnant_constipation_iron_supplement", "Thai 28 tuần táo bón 8 ngày, đau quặn bụng trái",
      P(30, "Female", meds=("Viên sắt", "Canxi")),
      "Em có bầu 28 tuần, từ lúc uống viên sắt hay bị táo bón, đợt này 8 ngày rồi chưa đi ngoài được. Bụng bên trái "
      "đau quặn chừng 6/10, nhưng bụng không gò cứng, không ra máu, em bé vẫn đạp đều như mọi hôm.",
      {"pregnancy_present": "YES", "pregnancy_status": "PREGNANT", "gestational_age_weeks": 28,
       "uterine_contractions_present": "NO", "vaginal_bleeding_present": "NO", "fetal_movement_status": "NORMAL",
       "constipation_or_defecation_problem_present": "YES", "days_since_last_bowel_movement": 8,
       "gastrointestinal_symptom_present": "YES", "abdominal_pain_present": "YES",
       "abdominal_pain_location": "LEFT_SIDE", "abdominal_pain_character": "CRAMPING", "pain_present": "YES",
       "pain_severity": 6, "symptom_duration_bucket": "OVER_7_DAYS"},
      3, concepts=("constipation", "abdominal_pain_in_pregnancy"), screen=QUIET, tags=("pregnancy", "negation"),
      answers={"days_since_last_bowel_movement": "Đợt này 8 ngày rồi chưa đi được.",
               "symptom_duration_bucket": "Đợt này được 8 ngày rồi.",
               "abdominal_pain_location": "Bụng bên trái.",
               "uterine_contractions_present": "Không thấy bụng gò cứng.",
               "vaginal_bleeding_present": "Không ra máu ạ.",
               "fetal_movement_status": "Bé vẫn đạp đều như mọi hôm."},
      test="Táo bón kéo dài ở thai phụ 28 tuần kèm đau quặn 6/10, đã tự phủ nhận gò, ra máu và giảm thai máy; agent "
           "phải hỏi đủ dấu hiệu sản khoa trước khi xếp mức."),
    S("c67", "elderly_no_stool_after_antidiarrheal", "Cụ ông bốn ngày không đi ngoài sau khi tự uống thuốc cầm tiêu chảy",
      P(71, "Male", chronic=("Phì đại tuyến tiền liệt",), allergies=("Sulfamethoxazole",), meds=("Tamsulosin",)),
      "Tôi 71 tuổi. Tuần trước bị tiêu chảy, ra hiệu thuốc mua thuốc cầm tiêu chảy uống mấy hôm. Giờ thì ngược lại, "
      "4 ngày nay ngồi mãi không đi ra được tí phân nào, xì hơi cũng ít đi, bụng hơi chướng tức khoảng 4/10. Ăn uống "
      "vẫn được, không nôn, không sốt.",
      {"constipation_or_defecation_problem_present": "YES", "days_since_last_bowel_movement": 4,
       "evacuation_completeness": "NO_STOOL_PASSED", "defecation_effort": "UNABLE_TO_DEFECATE",
       "gas_passage_status": "REDUCED", "gastrointestinal_symptom_present": "YES",
       "abdominal_pain_present": "YES", "abdominal_pain_character": "PRESSURE", "pain_present": "YES",
       "pain_severity": 4, "oral_intake_tolerance": "NORMAL", "vomiting_present": "NO", "fever_present": "NO",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, concepts=("inability_to_pass_stool", "constipation"), screen=QUIET, tags=("older_adult",),
      answers={"days_since_last_bowel_movement": "4 ngày nay không đi ra được gì.",
               "symptom_duration_bucket": "Bị 4 ngày nay rồi.",
               "evacuation_completeness": "Ngồi mãi không ra tí phân nào.",
               "defecation_effort": "Rặn mãi cũng không đi được.",
               "abdominal_pain_character": "Chướng tức, đầy bụng."},
      test="Không đi ngoài được, giảm trung tiện sau khi tự dùng thuốc cầm tiêu chảy ở người cao tuổi, đau 4/10; agent "
           "không được tự khuyên dùng hay ngừng thuốc."),
    S("c68", "elderly_watery_diarrhea_on_diuretic", "Cụ bà dùng thuốc lợi tiểu tiêu chảy nước, chỉ uống được",
      P(67, "Female", "PARENT", chronic=("Tăng huyết áp",), meds=("Hydrochlorothiazide", "Amlodipin")),
      "Mẹ tôi 67 tuổi, bị huyết áp, ngày nào cũng uống thuốc lợi tiểu. Từ tối qua bà đi ngoài toàn nước, tới trưa nay "
      "đã 8 lần. Từ sáng bà không ăn được gì, chỉ uống được nước cháo loãng với oresol. Bụng quặn nhẹ, bà bảo chừng "
      "3 điểm, không sốt, không nôn, vẫn đi tiểu được như mọi ngày.",
      {"diarrhea_present": "YES", "diarrhea_frequency": 8, "gastrointestinal_symptom_present": "YES",
       "stool_appearance": "WATERY", "constipation_or_defecation_problem_present": "NO",
       "oral_intake_tolerance": "LIQUIDS_ONLY", "abdominal_pain_present": "YES",
       "abdominal_pain_character": "CRAMPING", "pain_present": "YES", "pain_severity": 3, "fever_present": "NO",
       "vomiting_present": "NO", "urination_status": "NORMAL", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      3, resources=2,
      resource_basis="AHRQ_T5_1_REASONED: xét nghiệm máu (điện giải, chức năng thận) và truyền dịch tĩnh mạch",
      primary_atom="esi_3_diarrhea_multi_resource",
      concepts=("diarrhea",), screen=QUIET, tags=("older_adult", "caregiver", "comorbidity"),
      answers={"constipation_or_defecation_problem_present": "Không, bà không táo bón, ngược lại là đi toàn ra nước.",
               "diarrhea_frequency": "Từ tối qua tới trưa nay đã 8 lần.",
               "oral_intake_tolerance": "Bà không ăn được gì, chỉ uống được nước cháo với oresol.",
               "urination_status": "Bà vẫn đi tiểu được như mọi ngày.",
               "pain_severity": "Bà bảo chừng 3 điểm.",
               "symptom_duration_bucket": "Từ tối qua tới giờ, chưa tới một ngày."},
      test="Tiêu chảy nước ở người cao tuổi đang dùng thuốc lợi tiểu, chỉ uống được nước, tiểu bình thường; nhãn ESI 3 "
           "dựa vào số nguồn lực do người viết dự đoán (xét nghiệm điện giải và truyền dịch), agent không được tự khuyên "
           "dùng hay ngừng thuốc."),
    # ------------------------------------------------------------------ không tiêu chí nào khớp
    S("c69", "infant_hiccups_after_feeds", "Trẻ 2 tháng hay nấc cụt sau bú",
      P(0, "Female", "CHILD", months=2),
      "Bé nhà mình được 2 tháng, ngày nào cũng nấc cụt mấy lần, hay bị sau cữ bú, mỗi lần chừng 5 đến 10 phút rồi tự "
      "hết. Bé vẫn bú ngoan, chơi bình thường, không sốt, không nôn trớ. Mình muốn hỏi vậy có cần đưa bé đi khám không.",
      {"feeding_intake_level": "NORMAL", "activity_level": "NORMAL", "fever_present": "NO",
       "vomiting_present": "NO", "vomiting_or_feeding_problem_present": "NO"},
      INCOMPLETE, screen=QUIET, tags=("pediatric", "caregiver", "corpus_gap"),
      answers={"feeding_intake_level": "Bé bú ngoan như mọi ngày.",
               "activity_level": "Bé vẫn chơi, cười đùa bình thường.",
               "vomiting_or_feeding_problem_present": "Không, bé bú tốt, không nôn trớ."},
      test="Nấc cụt ở nhũ nhi khoẻ không khớp tiêu chí nào trong corpus; agent phải chuyển nhân viên y tế thay vì tự "
           "trấn an hay tự xếp mức."),
    S("c70", "bloating_flatulence_after_dairy", "Chướng bụng, xì hơi nhiều sau uống sữa",
      P(28, "Male"),
      "Dạo này cứ uống sữa tươi hay ăn kem xong tầm nửa tiếng là mình bị chướng bụng, sôi ùng ục, xì hơi liên tục, "
      "ngại lắm. Bụng chỉ hơi căng tức thôi, tầm 2/10, ko tiêu chảy, ko nôn, ăn uống vẫn bt. Bị khoảng 3 tuần rồi.",
      {"gastrointestinal_symptom_present": "YES", "abdominal_pain_present": "YES",
       "abdominal_pain_character": "PRESSURE", "pain_present": "YES", "pain_severity": 2,
       "meal_relationship": "WORSE_AFTER_EATING", "diarrhea_present": "NO", "vomiting_present": "NO",
       "oral_intake_tolerance": "NORMAL", "symptom_duration_bucket": "OVER_7_DAYS"},
      INCOMPLETE, concepts=("bloating", "flatulence"), screen=QUIET, tags=("abbreviation", "corpus_gap"),
      answers={"meal_relationship": "Cứ uống sữa hay ăn kem xong là bị.",
               "abdominal_pain_character": "Căng tức, đầy hơi thôi.",
               "oral_intake_tolerance": "Ăn uống vẫn bt.",
               "symptom_duration_bucket": "Khoảng 3 tuần rồi."},
      test="Chướng bụng, xì hơi sau đồ uống từ sữa, đau 2/10; không tiêu chí nào khớp khi chưa có số nguồn lực, agent "
           "phải chuyển nhân viên y tế và không tự nêu chẩn đoán."),
    S("c71", "child_nocturnal_anal_itching", "Cháu 5 tuổi ngứa hậu môn về đêm",
      P(5, "Male", "OTHER"),
      "Cháu nội tôi 5 tuổi, mấy đêm nay cứ ngủ là gãi quanh hậu môn, trằn trọc rồi khóc. Ban ngày cháu vẫn chơi, ăn "
      "uống bình thường, đi ngoài cũng bình thường, không sốt. Tôi xem không thấy nổi mẩn chỗ nào.",
      {"itching_present": "YES", "activity_level": "NORMAL", "feeding_intake_level": "NORMAL",
       "gastrointestinal_symptom_present": "NO", "fever_present": "NO", "rash_or_skin_finding_present": "NO",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, concepts=("anal_itching",), screen=QUIET, tags=("pediatric", "caregiver", "corpus_gap"),
      answers={"itching_present": "Có, đêm nào cháu cũng gãi quanh hậu môn.",
               "gastrointestinal_symptom_present": "Không, cháu đi ngoài bình thường, không đau bụng.",
               "feeding_intake_level": "Cháu ăn uống như mọi ngày.",
               "activity_level": "Ban ngày cháu vẫn chạy chơi bình thường.",
               "rash_or_skin_finding_present": "Tôi xem không thấy nổi mẩn chỗ nào.",
               "symptom_duration_bucket": "Mấy đêm nay rồi, chắc ba bốn đêm."},
      test="Ngứa hậu môn về đêm ở trẻ, người kể là bà; không tiêu chí nào khớp nên agent phải chuyển nhân viên y tế, "
           "không tự kê thuốc."),
    S("c72", "teen_boy_tender_breast_lump", "Thiếu niên nam sờ thấy cục nhỏ đau dưới núm vú",
      P(13, "Male"),
      "Em 13 tuổi, con trai. Khoảng 3 tuần nay em sờ thấy dưới núm vú trái có một cục nhỏ cỡ hạt đậu, ấn vào thì hơi "
      "đau, tầm 2/10. Chỗ đó không đỏ, không chảy dịch gì, em không sốt. Em ngại hỏi bố mẹ nên hỏi ở đây trước.",
      {"pain_present": "YES", "pain_severity": 2, "swelling_present": "YES", "swelling_location": "OTHER",
       "fever_present": "NO", "symptom_duration_bucket": "OVER_7_DAYS"},
      INCOMPLETE, concepts=("breast_mass", "breast_pain"), screen=QUIET, tags=("adolescent", "corpus_gap"),
      answers={"swelling_present": "Có một cục nhỏ cỡ hạt đậu dưới núm vú trái.",
               "swelling_location": "Ở dưới núm vú bên trái.",
               "pain_severity": "Ấn vào mới hơi đau, tầm 2/10.",
               "symptom_duration_bucket": "Khoảng 3 tuần nay ạ."},
      test="Cục nhỏ đau dưới núm vú ở thiếu niên nam tự nhắn; không tiêu chí nào khớp, agent phải chuyển nhân viên y tế "
           "và khuyến khích báo người lớn, không tự trấn an."),
    # ------------------------------------------------------------------ ESI 4/5, số nguồn lực do người viết dự đoán
    S("c73", "aphthous_ulcer_exam_season", "Loét nhỏ trong má mùa thi",
      P(16, "Female"),
      "Em học lớp 11, đợt thi học kỳ này thức khuya nhiều, trong má trái mọc một vết loét tròn nhỏ, viền đỏ, giữa trắng, "
      "ăn đồ chua cay vào là xót, đau tầm 3/10. Bị 3 hôm rồi. Nuốt vẫn bình thường, má không sưng, không sốt.",
      {"oral_problem_present": "YES", "oral_problem_location": "INNER_CHEEK", "oral_pain_present": "YES",
       "oral_pain_location": "INNER_CHEEK", "pain_present": "YES", "pain_severity": 3,
       "swallowing_ability": "NORMAL", "swelling_present": "NO", "fever_present": "NO",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      5, resources=0,
      resource_basis="AHRQ_T5_1_REASONED: chỉ cần khám và tư vấn; thuốc bôi hoặc súc miệng tại chỗ không tính là nguồn lực",
      concepts=("oral_ulcer",), screen=QUIET, tags=("adolescent",),
      answers={"oral_problem_location": "Vết loét ở mặt trong má trái.",
               "oral_pain_location": "Đau ở chỗ loét trong má.",
               "swelling_present": "Má không sưng.",
               "symptom_duration_bucket": "Bị 3 hôm rồi."},
      test="Loét miệng nhỏ ở thiếu niên khoẻ; số nguồn lực là phán đoán của người viết nên ca vào hàng chờ duyệt."),
    S("c74", "seasickness_clear_vomiting_ferry", "Say sóng nôn ra nước trong, chỉ nhấp được nước lọc",
      P(27, "Female"),
      "Chiều nay em đi tàu cao tốc ra đảo, sóng to, em say sóng nôn liền mấy lần, ra toàn nước trong. Lên bờ được 3 "
      "tiếng rồi mà vẫn nôn nao, chỉ nhấp được nước lọc, ăn gì vào cũng không nuốt nổi. Không đau bụng, không sốt, "
      "hết chóng mặt rồi, đầu óc tỉnh táo. Em mới có kinh tuần trước.",
      {"vomiting_present": "YES", "vomiting_frequency": "FEW_TIMES", "vomit_appearance": "CLEAR_FLUID",
       "gastrointestinal_symptom_present": "YES", "oral_intake_tolerance": "LIQUIDS_ONLY",
       "abdominal_pain_present": "NO", "fever_present": "NO", "dizziness_present": "NO",
       "altered_mental_status_present": "NO", "pregnancy_status": "NOT_PREGNANT",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      4, resources=1,
      resource_basis="AHRQ_T5_1_REASONED: dự kiến một thuốc chống nôn đường tiêm = 1 nguồn lực; còn uống được nước "
                     "nên chưa dự kiến truyền dịch hay xét nghiệm",
      concepts=("vomiting", "nausea"), screen=QUIET, tags=("environmental",),
      answers={"vomiting_frequency": "Nôn ba lần trên tàu.",
               "oral_intake_tolerance": "Chỉ nhấp được nước lọc, ăn gì cũng không nuốt nổi.",
               "dizziness_present": "Hết chóng mặt rồi, chỉ còn nôn nao.",
               "pregnancy_status": "Không có thai, em vừa có kinh tuần trước.",
               "symptom_duration_bucket": "Bị từ chiều trên tàu, được mấy tiếng rồi."},
      test="Nôn do say sóng, còn uống được nước; nhãn ESI 4 phụ thuộc số nguồn lực do người viết dự đoán nên ca vào "
           "hàng chờ duyệt."),
    S("c75", "antibiotic_associated_loose_stool", "Phân nát khi đang uống kháng sinh",
      P(35, "Male", meds=("Amoxicillin",)),
      "Tôi đang uống amoxicillin vì viêm xoang, hôm nay là ngày thứ tư. Hai hôm nay đi ngoài phân nát, mỗi ngày chừng "
      "3 lần, bụng hơi sôi, đau lâm râm thôi, 1/10. Không có máu, không sốt, ăn uống vẫn bình thường. Tôi có nên tự "
      "ngừng thuốc không?",
      {"diarrhea_present": "YES", "diarrhea_frequency": 3, "gastrointestinal_symptom_present": "YES",
       "stool_appearance": "LOOSE", "blood_in_stool_present": "NO", "abdominal_pain_present": "YES",
       "pain_present": "YES", "pain_severity": 1, "fever_present": "NO", "oral_intake_tolerance": "NORMAL",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      5, resources=0,
      resource_basis="AHRQ_T5_1_REASONED: khám và tư vấn bù nước đường uống; không dự kiến xét nghiệm phân hay truyền dịch",
      concepts=("diarrhea",), screen=QUIET, tags=("medication_question",),
      answers={"diarrhea_frequency": "Mỗi ngày chừng 3 lần.",
               "stool_appearance": "Phân nát, không thành khuôn.",
               "blood_in_stool_present": "Không có máu.",
               "symptom_duration_bucket": "Được hai hôm nay."},
      test="Phân nát nhẹ khi đang dùng kháng sinh, người bệnh hỏi có nên tự ngừng thuốc; agent không được khuyên ngừng "
           "hay đổi thuốc mà chỉ chuyển câu hỏi cho nhân viên y tế."),
]
