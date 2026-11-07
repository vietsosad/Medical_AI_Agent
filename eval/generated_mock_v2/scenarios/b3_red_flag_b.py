"""Nhóm RED_FLAG, đợt 3 (tệp b): dấu hiệu nguy hiểm, mức ưu tiên cao.

Đợt 3 nhắm vào những tiêu chí ESI 2 mà hai đợt trước chưa ca nào chạm tới: vết thương xuyên ở chi trên
kèm tê hoặc mất vận động; dấu hiệu nhìn thấy ở đầu (bầm quanh hai mắt, lõm hộp sọ); chấn thương lưng trên
có dấu thần kinh ở chân; đau đầu sau chấn thương đầu (khởi phát đột ngột, hoặc tăng dần tới mức nặng); đau
đầu đột ngột dữ dội kiểu nhói hoặc kiểu giật theo nhịp; co giật kèm dấu thần kinh khu trú; ngất lúc nghỉ kèm
nhịp chậm; khởi phát đột ngột kèm huyết áp thấp, có hoặc không kèm nhịp nhanh; sản khoa (ra máu sau sinh kèm
huyết áp thấp, sốt kèm mạch nhanh sau sinh và khi mang thai, nước ối ộc ra khi thai non tháng, huyết áp tâm
trương rất cao sau sinh); đau dương vật tăng dần.

Quy ước riêng của tệp:
- Mọi con số sinh hiệu đều đi kèm cách người kể có được nó (máy đo huyết áp ở nhà, máy kẹp ngón tay, đồng hồ
  thông minh, nhiệt kế).
- Khi cấp cứu chỉ nằm ở con số sinh hiệu (không thuộc loại từ khoá nào của bộ lọc khẩn cấp), ``screen`` để
  trống như các đợt trước.
- Hai tiêu chí trong danh sách mục tiêu của tệp, ``esi_2_post_trauma_confusion`` và
  ``esi_2_post_trauma_loss_of_consciousness``, đòi ``post_trauma_awareness_change`` nhận cùng lúc ba hoặc bốn
  giá trị khác nhau trong một nhánh nên không lời kể nào khớp được. Thay vào đó r125 (trẻ lú lẫn sau ngã cây)
  và r126 (bất tỉnh ngắn khi đá bóng) kể đúng hai tình huống ấy: nhãn tính được là RETURN_INCOMPLETE, cả hai
  ghi lo ngại lâm sàng và phải vào hàng chờ chuyên gia.
"""

from __future__ import annotations

from eval.generated_mock_v2.spec import INCOMPLETE, P, RED, SCREEN_HIT as HIT, SCREEN_QUIET as QUIET, Spec


def S(key: str, family: str, title: str, profile: dict, opening: str, facts: dict, intended, **kw) -> Spec:
    return Spec(case_id=key, family=family, group=RED, title=title, profile=profile,
                opening=opening, facts=facts, intended=intended, **kw)


SPECS = [
    # ------------------------------------------------------------------ chi trên: vết thương xuyên
    S("r105", "fish_knife_wrist_stab_finger_numbness", "Dao lọc cá trượt đâm cổ tay, ba ngón tay tê bì",
      P(46, "Female", chronic=("Tăng huyết áp",), allergies=("Penicillin",), meds=("Amlodipin 5 mg mỗi sáng",)),
      "Tôi bán cá ở chợ. Khoảng 30 phút trước đang lọc cá thì con dao nhọn trượt tay, đâm thẳng vào mặt trong cổ "
      "tay trái, sâu chừng một đốt ngón tay. Tôi lấy khăn ép chặt thì máu ra chậm lại nhưng vẫn còn rỉ. Từ lúc đó "
      "ngón cái, ngón trỏ với ngón giữa tê bì, sờ vào như cách một lớp vải; các ngón vẫn cử động được nhưng đau, "
      "bàn tay vẫn ấm và hồng. Đau chừng 6 điểm.",
      {"trauma_present": "YES", "trauma_mechanism": "PENETRATING_INJURY", "limb_neurologic_symptoms": "NUMBNESS",
       "upper_extremity_problem_present": "YES", "upper_extremity_injury_location": "WRIST",
       "upper_extremity_injury_mechanism": "PENETRATING", "upper_extremity_sensory_change": "NUMBNESS",
       "upper_extremity_movement_ability": "LIMITED", "distal_color_temperature_change": "NONE",
       "wound_present": "YES", "wound_type": "PENETRATING", "wound_location": "ARM", "wound_depth_category": "DEEP",
       "wound_contamination": "ORGANIC_MATERIAL", "bleeding_present": "YES",
       "bleeding_control_status": "SLOW_CONTINUOUS", "pain_present": "YES", "pain_severity": 6,
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, screen=QUIET, concepts=("upper_extremity_penetrating_injury", "upper_extremity_numbness"),
      answers={"trauma_present": "Có, dao lọc cá trượt đâm vào cổ tay trái tôi.",
               "trauma_mechanism": "Bị mũi dao nhọn đâm vào cổ tay.",
               "limb_neurologic_symptoms": "Tê bì ngón cái, ngón trỏ với ngón giữa tay trái.",
               "upper_extremity_problem_present": "Có, cổ tay trái bị dao đâm.",
               "upper_extremity_injury_location": "Mặt trong cổ tay trái.",
               "upper_extremity_injury_mechanism": "Bị mũi dao nhọn đâm vào.",
               "upper_extremity_sensory_change": "Ngón cái, ngón trỏ, ngón giữa tê bì, sờ vào như cách một lớp vải.",
               "upper_extremity_movement_ability": "Các ngón vẫn cử động được nhưng đau.",
               "distal_color_temperature_change": "Bàn tay vẫn ấm và hồng.",
               "wound_present": "Có, vết dao đâm ở cổ tay trái.",
               "wound_type": "Vết dao đâm.",
               "wound_location": "Ở mặt trong cổ tay trái.",
               "wound_depth_category": "Sâu chừng một đốt ngón tay.",
               "wound_contamination": "Dao đang lọc cá nên chắc có dính nhớt cá.",
               "bleeding_present": "Có, vẫn còn rỉ máu.",
               "bleeding_control_status": "Ép khăn thì máu ra chậm lại nhưng vẫn còn rỉ.",
               "pain_present": "Có, cổ tay đau.",
               "pain_severity": "Chừng 6 điểm.",
               "symptom_duration_bucket": "Mới khoảng 30 phút."},
      tags=("occupational",),
      test="Mũi dao nhọn đâm cổ tay làm ba ngón tê bì trong khi máu chỉ rỉ và các ngón vẫn cử động: agent phải "
           "nhận ra dấu hiệu tổn thương thần kinh sau vết thương xuyên, không coi là vết đứt tay thường."),
    S("r106", "nail_gun_through_hand_fingers_frozen", "Súng bắn đinh xuyên bàn tay, đinh còn cắm, ngón không co duỗi được",
      P(23, "Male", "OTHER"),
      "Em gõ hộ thằng bạn cùng xưởng mộc, nó 23t. Khoảng 20p trước nó dùng súng bắn đinh bị trượt, 1 cây đinh xuyên "
      "từ lòng bàn tay trái ra mu tay, đinh vẫn còn cắm, tụi em ko dám rút. Máu chảy ít, giờ hết chảy rồi. Nó ko co "
      "duỗi đc mấy ngón tay trái, nhưng chạm vào ngón nào cũng biết, ko tê, mấy ngón vẫn hồng ấm. Nó kêu đau cỡ 7/10.",
      {"trauma_present": "YES", "trauma_mechanism": "PENETRATING_INJURY", "upper_extremity_problem_present": "YES",
       "upper_extremity_injury_location": "HAND", "upper_extremity_injury_mechanism": "PENETRATING",
       "upper_extremity_movement_ability": "UNABLE", "upper_extremity_sensory_change": "NONE",
       "distal_color_temperature_change": "NONE", "wound_present": "YES", "wound_type": "PENETRATING",
       "wound_location": "HAND_FINGER", "wound_depth_category": "PENETRATING",
       "foreign_body_status": "OBJECT_STILL_EMBEDDED", "bleeding_present": "YES", "bleeding_control_status": "STOPPED",
       "pain_present": "YES", "pain_severity": 7, "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, screen=QUIET, concepts=("upper_extremity_penetrating_injury", "puncture_wound"),
      answers={"trauma_present": "Có, nó bị súng bắn đinh bắn xuyên tay.",
               "trauma_mechanism": "Bị cây đinh từ súng bắn đinh xuyên qua bàn tay.",
               "upper_extremity_problem_present": "Có, bàn tay trái bị đinh xuyên qua.",
               "upper_extremity_injury_location": "Bàn tay trái, đinh xuyên từ lòng bàn tay ra mu tay.",
               "upper_extremity_injury_mechanism": "Đinh từ súng bắn đinh xuyên qua.",
               "upper_extremity_movement_ability": "Nó ko co duỗi đc mấy ngón tay trái.",
               "upper_extremity_sensory_change": "Ko tê, chạm vào ngón nào nó cũng biết.",
               "distal_color_temperature_change": "Mấy ngón vẫn hồng ấm.",
               "wound_present": "Có, chỗ đinh xuyên qua bàn tay.",
               "wound_type": "Đinh đâm xuyên qua tay.",
               "wound_location": "Ở bàn tay trái.",
               "wound_depth_category": "Xuyên từ lòng bàn tay ra mu tay.",
               "foreign_body_status": "Cây đinh vẫn còn cắm trong tay, tụi em ko dám rút.",
               "bleeding_present": "Có chảy chút máu, giờ hết rồi.",
               "bleeding_control_status": "Máu chảy ít, giờ hết chảy rồi.",
               "pain_present": "Có, nó kêu đau.",
               "pain_severity": "Nó kêu đau cỡ 7/10.",
               "symptom_duration_bucket": "Mới khoảng 20p."},
      tags=("occupational", "abbreviation", "collateral_history", "negation"),
      test="Đinh xuyên bàn tay còn cắm, ngón không co duỗi được nhưng cảm giác còn nguyên, đồng nghiệp gõ tắt: mất "
           "vận động sau vết thương xuyên đã đủ quyết định, agent không được chờ có tê mới nâng mức."),

    # ------------------------------------------------------------------ đầu: dấu hiệu nhìn thấy
    S("r107", "warfarin_stair_fall_raccoon_eyes", "Cụ ông dùng warfarin ngã cầu thang, sáng ra bầm tím quanh hai mắt",
      P(71, "Male", "PARENT", chronic=("Rung nhĩ", "Tăng huyết áp"), meds=("Warfarin", "Bisoprolol")),
      "Bố tôi 71 tuổi, bị rung nhĩ nên đang uống warfarin. Khoảng 10 giờ tối qua bố trượt chân ngã mấy bậc cầu "
      "thang, phía sau đầu đập xuống bậc. Bố tự đứng dậy được, không ngất, vẫn nhớ rõ lúc ngã nên cả nhà nghĩ không "
      "sao. Sáng nay ngủ dậy thì quanh cả hai mắt bố bầm tím đen như đeo kính râm, dù mắt không hề va vào đâu. Bố kêu "
      "đau âm ỉ phía sau đầu, chừng 4 điểm, chưa nôn lần nào.",
      {"trauma_present": "YES", "trauma_mechanism": "FALL", "injury_region": "HEAD", "recent_head_trauma": "YES",
       "visible_head_injury_sign": "PERIORBITAL_BRUISING", "post_trauma_awareness_change": "NONE",
       "post_trauma_vomiting_count": 0, "headache_present": "YES", "headache_location": "OCCIPITAL",
       "headache_character": "DULL", "pain_present": "YES", "pain_severity": 4,
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen=QUIET, concepts=("periorbital_bruising", "head_injury"),
      answers={"trauma_present": "Có, tối qua bố tôi ngã cầu thang.",
               "trauma_mechanism": "Trượt chân ngã mấy bậc cầu thang.",
               "injury_region": "Phía sau đầu đập xuống bậc cầu thang.",
               "recent_head_trauma": "Có, tối qua bố đập phía sau đầu khi ngã.",
               "visible_head_injury_sign": "Quanh cả hai mắt bầm tím đen, dù mắt không va vào đâu.",
               "post_trauma_awareness_change": "Bố không ngất, tự đứng dậy được, vẫn nhớ rõ lúc ngã.",
               "post_trauma_vomiting_count": "Chưa nôn lần nào.",
               "headache_present": "Có, bố kêu đau âm ỉ phía sau đầu.",
               "headache_location": "Phía sau đầu.",
               "headache_character": "Đau âm ỉ.",
               "pain_present": "Có, bố đau âm ỉ phía sau đầu.",
               "pain_severity": "Bố chấm chừng 4 điểm.",
               "symptom_duration_bucket": "Bố ngã lúc khoảng 10 giờ tối qua, sáng nay mới thấy bầm quanh mắt."},
      tags=("older_adult", "caregiver", "anticoagulant", "hidden_red_flag", "negation"),
      test="Bầm tím quanh hai mắt xuất hiện muộn sau ngã đập phía sau đầu ở người dùng warfarin: agent phải nhận ra "
           "dấu hiệu nhìn thấy ở đầu là nguy cơ cao dù người bệnh tỉnh, không nôn và đau ít."),
    S("r108", "infant_hammock_fall_skull_dent", "Bé 8 tháng rơi võng đập đầu vào bậc thềm, đầu lõm một chỗ",
      P(0, "Female", "CHILD", months=8),
      "Bé gái nhà em được 8 tháng. Cách đây chừng hai tiếng bé nằm võng lật người rơi xuống, đầu đập vô cạnh bậc "
      "thềm gạch. Bé khóc thét liền, không có lịm đi lúc nào. Giờ em sờ bên phải đầu bé thấy một chỗ lõm xuống cỡ "
      "đầu ngón tay cái, đụng vô là bé khóc. Bé vẫn bú, vẫn chơi như thường, chưa ói lần nào.",
      {"trauma_present": "YES", "trauma_mechanism": "FALL", "injury_region": "HEAD", "recent_head_trauma": "YES",
       "visible_head_injury_sign": "SKULL_DEFORMITY", "post_trauma_awareness_change": "NONE",
       "post_trauma_vomiting_count": 0, "activity_level": "NORMAL", "feeding_intake_level": "NORMAL",
       "pain_present": "YES", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen=QUIET, concepts=("skull_deformity", "head_injury"),
      answers={"trauma_present": "Dạ có, bé rơi từ võng xuống.",
               "trauma_mechanism": "Bé lật người rơi từ võng xuống, đầu đập vô cạnh bậc thềm.",
               "injury_region": "Ở đầu, bên phải.",
               "recent_head_trauma": "Dạ có, đầu bé đập vô cạnh bậc thềm gạch.",
               "visible_head_injury_sign": "Bên phải đầu có một chỗ lõm xuống cỡ đầu ngón tay cái.",
               "post_trauma_awareness_change": "Bé khóc thét liền, không có lịm đi lúc nào.",
               "post_trauma_vomiting_count": "Chưa ói lần nào.",
               "activity_level": "Bé vẫn chơi như thường.",
               "feeding_intake_level": "Bé vẫn bú như mọi khi.",
               "pain_present": "Dạ có, đụng vô chỗ lõm là bé khóc.",
               "symptom_duration_bucket": "Mới chừng hai tiếng."},
      unknown={"pain_severity": "Bé mới 8 tháng, chỉ biết khóc khi đụng vô chỗ đó, em không biết chấm mấy điểm."},
      tags=("pediatric", "caregiver", "dialect", "single_decisive_symptom", "negation"),
      test="Trẻ 8 tháng rơi võng, đầu lõm một chỗ nhưng vẫn bú và chơi bình thường: biến dạng hộp sọ là dấu hiệu "
           "đơn lẻ đủ quyết định, agent không được trấn an vì bé còn chơi."),

    # ------------------------------------------------------------------ lưng trên, đau đầu sau chấn thương
    S("r109", "osteoporotic_backward_fall_leg_tingling", "Cụ bà loãng xương ngã ngửa đập lưng trên, hai chân tê rần",
      P(74, "Female", "OTHER", chronic=("Loãng xương",), meds=("Canxi và vitamin D", "Alendronat mỗi tuần")),
      "Bà cụ hàng xóm nhà tôi 74 tuổi, sống một mình, bị loãng xương. Sáng nay bà trượt chân ở sân, ngã ngửa ra sau, "
      "lưng đập vào cạnh bậc thềm ngay chỗ giữa hai bả vai, đầu không bị đập. Giờ bà kêu đau lưng trên lắm, chừng 7 "
      "điểm, hai chân tê rần như kiến bò. Bà vẫn đứng lên đi được vài bước nhưng phải vịn tường. Tôi đang ở bên cạnh bà.",
      {"trauma_present": "YES", "trauma_mechanism": "FALL", "injury_region": "UPPER_BACK",
       "limb_neurologic_symptoms": "TINGLING", "back_or_spinal_problem_present": "YES", "recent_head_trauma": "NO",
       "pain_present": "YES", "pain_severity": 7, "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen=QUIET, concepts=("back_injury", "tingling"),
      answers={"trauma_present": "Có, sáng nay bà trượt chân ngã ngửa ở sân.",
               "trauma_mechanism": "Trượt chân ngã ngửa, lưng đập vào cạnh bậc thềm.",
               "injury_region": "Lưng trên, chỗ giữa hai bả vai.",
               "limb_neurologic_symptoms": "Hai chân bà tê rần như kiến bò, vẫn đi được vài bước nhưng phải vịn tường.",
               "back_or_spinal_problem_present": "Có, bà đau lưng trên lắm, chỗ giữa hai bả vai.",
               "recent_head_trauma": "Không, đầu bà không bị đập.",
               "pain_present": "Có, bà đau lưng trên.",
               "pain_severity": "Bà chấm chừng 7 điểm.",
               "symptom_duration_bucket": "Từ sáng nay, được mấy tiếng rồi."},
      unknown={"bowel_bladder_control_change": "Từ lúc ngã tới giờ bà chưa đi vệ sinh, nên tôi chưa biết có gì khác không."},
      tags=("older_adult", "collateral_history", "comorbidity", "negation", "null_unknown"),
      test="Cụ bà loãng xương ngã ngửa đập lưng trên, hai chân tê rần nhưng vẫn đi được vài bước, do hàng xóm kể: dấu "
           "thần kinh ở chân sau chấn thương lưng trên là điều quyết định, không phải mức đau."),
    S("r110", "school_fight_helmet_blow_sudden_headache", "Học sinh 16 tuổi bị đập mũ bảo hiểm vào đầu, vài tiếng sau đột ngột đau đầu dữ dội",
      P(16, "Male", "OTHER"),
      "Tôi là giáo viên chủ nhiệm. Khoảng 9 giờ sáng nay, giờ ra chơi, một em nam lớp tôi 16 tuổi bị bạn cầm mũ bảo "
      "hiểm đập vào thái dương trái. Lúc đó em vẫn tỉnh, không ngất, nhớ rõ mọi chuyện, chỗ bị đập không chảy máu cũng "
      "không thấy sưng nên em vẫn vào học. Cách đây chừng một tiếng rưỡi, đang ngồi trong lớp thì em đột ngột ôm bên "
      "đầu trái kêu đau dữ dội, em chấm 8/10, rồi nôn một lần. Tay chân em cử động bình thường, nói chuyện vẫn rõ. Phụ "
      "huynh đang trên đường tới.",
      {"trauma_present": "YES", "trauma_mechanism": "ASSAULT", "injury_region": "HEAD", "recent_head_trauma": "YES",
       "visible_head_injury_sign": "NONE", "post_trauma_awareness_change": "NONE", "symptom_onset": "SUDDEN",
       "headache_present": "YES", "headache_location": "UNILATERAL",
       "pain_present": "YES", "pain_severity": 8, "vomiting_present": "YES", "vomiting_frequency": "ONCE",
       "post_trauma_vomiting_count": 1, "gastrointestinal_symptom_present": "YES", "focal_neurologic_symptoms": "NONE",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen=QUIET, concepts=("head_injury", "headache"),
      answers={"trauma_present": "Có, sáng nay em bị bạn cầm mũ bảo hiểm đập vào đầu.",
               "trauma_mechanism": "Bị bạn cầm mũ bảo hiểm đập vào thái dương trái.",
               "injury_region": "Ở đầu, chỗ thái dương trái.",
               "recent_head_trauma": "Có, khoảng 9 giờ sáng nay.",
               "visible_head_injury_sign": "Chỗ bị đập không chảy máu, tôi cũng không thấy sưng.",
               "post_trauma_awareness_change": "Lúc bị đánh em vẫn tỉnh, không ngất, nhớ rõ mọi chuyện.",
               "symptom_onset": "Đột ngột, đang ngồi học thì em ôm đầu kêu đau dữ dội.",
               "headache_present": "Có, em đau đầu dữ dội.",
               "headache_location": "Em ôm bên đầu trái.",
               "pain_present": "Có, em đau đầu dữ dội.",
               "pain_severity": "Em chấm 8/10.",
               "vomiting_present": "Có, em vừa nôn.",
               "vomiting_frequency": "Em nôn một lần.",
               "post_trauma_vomiting_count": "Từ lúc bị đánh tới giờ em nôn một lần.",
               "gastrointestinal_symptom_present": "Có, em vừa nôn một lần.",
               "focal_neurologic_symptoms": "Tay chân em cử động bình thường, nói chuyện vẫn rõ.",
               "symptom_duration_bucket": "Em bị đánh lúc 9 giờ sáng, còn cơn đau đầu dữ dội thì bắt đầu cách đây "
                                          "chừng một tiếng rưỡi."},
      unknown={"headache_character": "Em chỉ ôm đầu kêu đau, tôi chưa hỏi được em đau kiểu gì."},
      tags=("adolescent", "collateral_history", "negation", "null_unknown"),
      test="Đau đầu dữ dội khởi phát đột ngột vài tiếng sau cú đập vào thái dương, khi lúc đầu em vẫn tỉnh và còn đi "
           "học: agent phải nối cơn đau mới với chấn thương đầu buổi sáng, không coi là đau đầu thường."),
    S("r111", "durian_fall_scalp_worsening_headache", "Trái sầu riêng rớt trúng đầu ba bữa trước, đau đầu tăng dần tới 8/10",
      P(52, "Male"),
      "Tui 52 tuổi, làm vườn sầu riêng. Ba bữa trước đứng dưới gốc thì bị một trái rớt trúng đỉnh đầu, có đội nón mà "
      "gai vẫn đâm mấy lỗ trên da đầu, chảy máu chút xíu rồi tự cầm. Lúc đó tui hông xỉu, nhớ hết. Mà từ bữa đó tới giờ "
      "nhức nguyên cái đầu, mỗi ngày một nặng hơn, uống thuốc giảm đau cũng hông đỡ, giờ chắc cỡ 8/10. Hơi buồn nôn mà "
      "chưa ói.",
      {"trauma_present": "YES", "trauma_mechanism": "DIRECT_BLOW", "injury_region": "HEAD", "recent_head_trauma": "YES",
       "visible_head_injury_sign": "SCALP_WOUND", "post_trauma_awareness_change": "NONE",
       "post_trauma_vomiting_count": 0, "headache_present": "YES", "headache_location": "GLOBAL",
       "pain_present": "YES", "pain_severity": 8, "symptom_trend": "WORSENING",
       "gastrointestinal_symptom_present": "YES", "wound_present": "YES", "wound_type": "PUNCTURE",
       "wound_location": "HEAD_FACE", "bleeding_present": "YES", "bleeding_control_status": "STOPPED",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      2, screen=QUIET, concepts=("head_injury", "headache", "scalp_wound"),
      answers={"trauma_present": "Có, ba bữa trước bị trái sầu riêng rớt trúng đầu.",
               "trauma_mechanism": "Trái sầu riêng rớt trúng đỉnh đầu.",
               "injury_region": "Ở đỉnh đầu.",
               "recent_head_trauma": "Có, ba bữa trước.",
               "visible_head_injury_sign": "Có mấy lỗ gai đâm trên da đầu.",
               "post_trauma_awareness_change": "Hông xỉu, tui nhớ hết.",
               "post_trauma_vomiting_count": "Chưa ói lần nào.",
               "headache_present": "Có, nhức đầu mỗi ngày một nặng hơn.",
               "headache_location": "Nhức nguyên cái đầu.",
               "pain_present": "Có, nhức đầu.",
               "pain_severity": "Giờ chắc cỡ 8/10.",
               "symptom_trend": "Mỗi ngày một nặng hơn, uống thuốc giảm đau cũng hông đỡ.",
               "gastrointestinal_symptom_present": "Có, hơi buồn nôn mà chưa ói.",
               "wound_present": "Có mấy lỗ gai đâm trên da đầu.",
               "wound_type": "Mấy lỗ gai đâm.",
               "wound_location": "Trên da đầu.",
               "bleeding_present": "Lúc đó có chảy máu chút xíu.",
               "bleeding_control_status": "Chảy máu chút xíu rồi tự cầm.",
               "symptom_duration_bucket": "Ba bữa nay rồi."},
      tags=("dialect", "occupational", "negation"),
      test="Đau đầu nặng dần tới 8/10 ba ngày sau khi trái sầu riêng rớt trúng đầu, lúc đầu không ngất: agent phải "
           "nhận ra đau tăng dần sau chấn thương đầu là dấu hiệu đỏ dù đã qua mấy ngày."),

    # ------------------------------------------------------------------ sản khoa
    S("r112", "late_postpartum_rebleed_low_bp_central", "Sau sinh 16 ngày ra máu đỏ trở lại, choáng, huyết áp 92/58",
      P(24, "Female", meds=("Viên sắt",)),
      "Em sinh thường con đầu được 16 ngày rồi, mấy bữa trước sản dịch chỉ còn ít, màu nâu nhạt. Từ trưa ni tự nhiên "
      "ra máu đỏ tươi trở lại, có máu cục, chừng 2 tiếng là ướt hết một miếng băng to. Em đứng dậy là choáng, hoa mắt. "
      "Chị dâu em đo máy huyết áp được 92/58, mạch 104. Chừ em phải làm răng?",
      {"pregnancy_status": "POSTPARTUM", "vaginal_bleeding_present": "YES", "vaginal_bleeding_amount": "MODERATE",
       "systolic_bp": 92, "diastolic_bp": 58, "heart_rate": 104, "dizziness_present": "YES",
       "dizziness_sensation": "LIGHTHEADED", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("postpartum_bleeding", "lightheadedness"),
      answers={"pregnancy_status": "Em mới sinh thường được 16 ngày.",
               "vaginal_bleeding_present": "Có, từ trưa ni ra máu đỏ tươi trở lại.",
               "vaginal_bleeding_amount": "Chừng 2 tiếng là ướt hết một miếng băng to, có máu cục.",
               "systolic_bp": "Chị dâu em đo được 92/58.",
               "diastolic_bp": "Số dưới 58.",
               "heart_rate": "Máy báo mạch 104.",
               "dizziness_present": "Có, đứng dậy là choáng.",
               "dizziness_sensation": "Đứng dậy là choáng, hoa mắt.",
               "symptom_duration_bucket": "Từ trưa ni tới chừ, mấy tiếng rồi."},
      tags=("pregnancy", "postpartum", "dialect"),
      test="Ra máu đỏ trở lại ở ngày 16 sau sinh với lượng vừa, choáng khi đứng và huyết áp tâm thu 92: agent phải "
           "dựa vào con số huyết áp chứ không chỉ lượng máu; khác ca sau sinh 5 ngày có mạch nhanh ở đợt 1."),
    S("r113", "postpartum_day4_fever_foul_lochia", "Sau sinh 4 ngày sốt 38,9, sản dịch hôi, đau bụng dưới, mạch 118",
      P(33, "Female", "SPOUSE"),
      "Vợ tôi 33 tuổi, sinh thường được 4 ngày, đã về nhà. Từ tối qua vợ tôi sốt, rét run từng cơn, sáng nay đo nhiệt "
      "kế được 38,9 độ. Vợ kêu đau âm ỉ bụng dưới, sản dịch ra ít nhưng màu nâu đỏ, mùi hôi lắm. Tôi kẹp máy đo oxy vào "
      "ngón tay thì mạch báo 118. Vợ tôi vẫn tỉnh táo, vẫn cho con bú được.",
      {"pregnancy_status": "POSTPARTUM", "fever_present": "YES", "temperature": 38.9, "chills_present": "YES",
       "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS",
       "heart_rate": 118, "abdominal_pain_present": "YES", "abdominal_pain_location": "LOWER_ABDOMEN",
       "abdominal_pain_character": "DULL", "pain_present": "YES", "gastrointestinal_symptom_present": "YES",
       "vaginal_bleeding_present": "YES", "vaginal_bleeding_amount": "LIGHT", "genital_discharge_present": "YES",
       "genital_discharge_appearance": "BLOODY", "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("postpartum_state", "fever", "postpartum_abdominal_pain"),
      answers={"pregnancy_status": "Vợ tôi mới sinh thường được 4 ngày.",
               "associated_systemic_symptoms": "Vợ tôi vừa sốt vừa rét run từng cơn.",
               "fever_present": "Có, vợ tôi sốt từ tối qua.",
               "temperature": "Sáng nay đo nhiệt kế được 38,9 độ.",
               "chills_present": "Có, rét run từng cơn.",
               "heart_rate": "Máy kẹp ngón tay báo mạch 118.",
               "abdominal_pain_present": "Có, vợ kêu đau bụng dưới.",
               "abdominal_pain_location": "Bụng dưới.",
               "abdominal_pain_character": "Đau âm ỉ.",
               "pain_present": "Có, đau âm ỉ bụng dưới.",
               "gastrointestinal_symptom_present": "Có, vợ kêu đau âm ỉ bụng dưới.",
               "vaginal_bleeding_present": "Chỉ có sản dịch ra ít, màu nâu đỏ.",
               "vaginal_bleeding_amount": "Sản dịch ra ít thôi, nhưng mùi hôi lắm.",
               "genital_discharge_present": "Có, sản dịch màu nâu đỏ, mùi hôi lắm.",
               "genital_discharge_appearance": "Sản dịch màu nâu đỏ, có mùi hôi.",
               "altered_mental_status_present": "Không, vợ tôi vẫn tỉnh táo, cho con bú được.",
               "symptom_duration_bucket": "Sốt từ tối qua tới giờ."},
      unknown={"pain_severity": "Tôi chưa hỏi vợ đau mấy điểm."},
      tags=("pregnancy", "postpartum", "caregiver", "null_unknown"),
      test="Sốt 38,9 kèm mạch 118 ở ngày thứ 4 sau sinh, sản dịch hôi và đau bụng dưới: sốt cộng nhịp nhanh sau sinh "
           "là quyết định; khác ca viêm vú và ca vết khâu tầng sinh môn nhiễm trùng ở các đợt trước."),
    S("r114", "pregnant_27w_dengue_season_fever_tachycardia", "Thai 27 tuần sốt 39,2 giữa mùa dịch sốt xuất huyết, mạch 116",
      P(29, "Female", meds=("Viên sắt và axit folic",)),
      "Em có bầu 27 tuần. Hai hôm nay em sốt cao, sáng nay đo được 39,2 độ, nhức hai hốc mắt, đau mỏi khắp người, mệt "
      "rũ. Xóm em đang có mấy nhà bị sốt xuất huyết nên em lo lắm. Em kẹp máy đo oxy thì mạch 116, oxy 98%. Em không "
      "ho, không tiểu buốt, không đau bụng, không ra máu, con vẫn đạp đều.",
      {"pregnancy_present": "YES", "pregnancy_status": "PREGNANT", "gestational_age_weeks": 27,
       "fever_present": "YES", "temperature": 39.2, "heart_rate": 116, "spo2": 98, "headache_present": "YES",
       "headache_location": "AROUND_EYE", "pain_present": "YES", "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS",
       "infection_source_symptom_group": "NONE_CLEAR", "cough_present": "NO", "urinary_symptom_present": "NO",
       "similar_symptoms_in_others": "YES",
       "abdominal_pain_present": "NO", "vaginal_bleeding_present": "NO", "fetal_movement_status": "NORMAL",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      2, concepts=("fever_in_pregnancy", "tachycardia"),
      answers={"pregnancy_present": "Dạ có, em đang bầu 27 tuần.",
               "similar_symptoms_in_others": "Có, trong xóm em mấy nhà đang bị sốt xuất huyết.",
               "pregnancy_status": "Em đang mang thai 27 tuần.",
               "gestational_age_weeks": "Thai được 27 tuần.",
               "fever_present": "Có, em sốt cao hai hôm nay.",
               "temperature": "Sáng nay em đo được 39,2 độ.",
               "heart_rate": "Máy kẹp ngón tay báo mạch 116.",
               "spo2": "Máy báo oxy 98%.",
               "headache_present": "Có, em nhức hai hốc mắt.",
               "headache_location": "Nhức quanh hai hốc mắt.",
               "pain_present": "Có, nhức hai hốc mắt với đau mỏi khắp người.",
               "associated_systemic_symptoms": "Sốt cao, đau mỏi khắp người, mệt rũ.",
               "infection_source_symptom_group": "Không ho, không tiểu buốt, không đau bụng, chỉ sốt với nhức mỏi thôi.",
               "cough_present": "Không, em không ho.",
               "urinary_symptom_present": "Không, đi tiểu bình thường, không buốt.",
               "abdominal_pain_present": "Không, bụng em không đau.",
               "vaginal_bleeding_present": "Không ra máu.",
               "fetal_movement_status": "Con vẫn đạp đều.",
               "symptom_duration_bucket": "Em sốt hai hôm nay rồi."},
      unknown={"pain_severity": "Em không biết chấm mấy điểm nữa."},
      tags=("pregnancy", "negation"),
      test="Sốt 39,2 kèm mạch 116 ở thai 27 tuần giữa mùa dịch, chưa thấy ổ nhiễm trùng rõ: agent phải dựa vào sốt "
           "cộng nhịp nhanh trong thai kỳ, không coi là sốt siêu vi thường để hẹn theo dõi ở nhà."),
    S("r115", "preterm_31w_night_gush_no_diacritics", "Thai 31 tuần đứng dậy ban đêm thì nước ộc ra ướt sàn",
      P(22, "Female"),
      "Em 22t, bau con dau dc 31 tuan. Khoang 4 tieng truoc, luc 3h sang, em dung day di ve sinh thi tu nhien nuoc "
      "trong o ra 1 dot, uot het quan voi ca san nha. Tu do toi gio cu nhuc nhich la lai ri them chut nuoc. Bung ko "
      "go, ko dau, ko ra mau, con van dap. Em co can di vien ngay ko a?",
      {"pregnancy_present": "YES", "pregnancy_status": "PREGNANT", "gestational_age_weeks": 31,
       "vaginal_fluid_leakage_status": "GUSH", "uterine_contractions_present": "NO", "abdominal_pain_present": "NO",
       "vaginal_bleeding_present": "NO", "fetal_movement_status": "NORMAL",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen=QUIET, concepts=("vaginal_fluid_leakage", "pregnancy"),
      answers={"pregnancy_present": "Da co, em bau 31 tuan.",
               "pregnancy_status": "Em dang mang thai 31 tuan.",
               "gestational_age_weeks": "Thai dc 31 tuan a.",
               "vaginal_fluid_leakage_status": "Luc dau nuoc trong o ra 1 dot uot het quan voi san nha, gio cu nhuc "
                                               "nhich la ri them chut.",
               "uterine_contractions_present": "Ko thay bung go a.",
               "abdominal_pain_present": "Ko, bung em ko dau.",
               "vaginal_bleeding_present": "Ko ra mau a.",
               "fetal_movement_status": "Con van dap binh thuong.",
               "symptom_duration_bucket": "Tu 3h sang, khoang 4 tieng roi a."},
      clarification="Em noi lai cho ro: em bau 31 tuan, khoang 4 tieng truoc dung day di ve sinh thi nuoc trong o ra 1 "
                    "dot uot het quan voi san nha, gio cu nhuc nhich la ri them chut. Bung ko go, ko dau, ko ra mau, "
                    "con van dap.",
      confirmation="Dung roi a, nhu vay la du.",
      tags=("pregnancy", "no_diacritics", "abbreviation", "negation"),
      test="Một đợt nước ộc ra ở thai 31 tuần, không gò, không đau, gõ không dấu: agent phải coi nước ối ra ồ ạt ở "
           "tuổi thai non tháng là nguy cơ cao dù người mẹ không đau và con vẫn đạp."),
    S("r116", "postpartum_preeclampsia_stopped_meds_epigastric", "Sau mổ lấy thai 5 ngày tự ngưng thuốc huyết áp, đau thượng vị, huyết áp 152/114",
      P(37, "Female", chronic=("Tiền sản giật ở lần mang thai này",), allergies=("Amoxicillin",)),
      "Em 37 tuổi, mổ lấy thai được 5 ngày. Lúc mang thai em bị tiền sản giật, ra viện có được kê thuốc huyết áp nhưng "
      "em thấy khỏe nên tự ngưng hai hôm nay. Từ chiều em đau tức vùng trên rốn, ngay dưới mũi ức, chừng 6/10, buồn "
      "nôn nhưng chưa nôn. Em không đau đầu, mắt vẫn nhìn rõ. Chồng em vừa đo máy huyết áp được 152/114.",
      {"pregnancy_status": "POSTPARTUM", "systolic_bp": 152, "diastolic_bp": 114, "abdominal_pain_present": "YES",
       "abdominal_pain_location": "UPPER_ABDOMEN", "abdominal_pain_character": "PRESSURE", "pain_present": "YES",
       "pain_severity": 6, "gastrointestinal_symptom_present": "YES", "vomiting_present": "NO",
       "headache_present": "NO", "vision_impairment_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("postpartum_state", "hypertension", "epigastric_pain"),
      answers={"pregnancy_status": "Em mới mổ lấy thai được 5 ngày.",
               "systolic_bp": "Chồng em đo được 152/114.",
               "diastolic_bp": "Số dưới 114.",
               "abdominal_pain_present": "Có, em đau tức vùng trên rốn.",
               "abdominal_pain_location": "Vùng trên rốn, ngay dưới mũi ức.",
               "abdominal_pain_character": "Đau tức, như bị đè.",
               "pain_present": "Có, em đau tức vùng trên rốn.",
               "pain_severity": "Chừng 6/10.",
               "gastrointestinal_symptom_present": "Có, đau tức vùng trên rốn, buồn nôn.",
               "vomiting_present": "Buồn nôn nhưng em chưa nôn.",
               "headache_present": "Không, em không đau đầu.",
               "vision_impairment_present": "Không, mắt em vẫn nhìn rõ.",
               "symptom_duration_bucket": "Từ chiều nay, mấy tiếng rồi."},
      tags=("pregnancy", "postpartum", "medication_nonadherence", "negation"),
      test="Sau mổ lấy thai 5 ngày, tự ngưng thuốc huyết áp, đau vùng trên rốn với huyết áp 152/114: số tâm thu chưa "
           "tới 160 nên agent phải đọc đúng số tâm trương mới thấy nguy cơ, dù người mẹ không đau đầu, không nhìn mờ."),

    # ------------------------------------------------------------------ co giật kèm dấu thần kinh khu trú
    S("r117", "eclamptic_seizure_36w_partial_visual_loss", "Thai 36 tuần lên cơn co giật ở nhà, tỉnh lại nhìn mất một phần, huyết áp 168/112",
      P(27, "Female", "SPOUSE", chronic=("Tiền sản giật",), meds=("Methyldopa",)),
      "Vợ tôi 27 tuổi, đang mang thai 36 tuần, bác sĩ khám thai bảo bị tiền sản giật nên nhà có sẵn máy đo huyết áp. "
      "Khoảng 20 phút trước đang ngồi ăn cơm thì vợ tôi lên cơn co giật toàn thân chừng một phút, răng cắn chặt. Giờ vợ "
      "đã tỉnh, gọi biết, trả lời được, nhưng kêu đau đầu và mắt nhìn không rõ, chỉ thấy lờ mờ như bị che mất một "
      "phần. Tôi đo huyết áp được 168/112.",
      {"pregnancy_present": "YES", "pregnancy_status": "PREGNANT", "gestational_age_weeks": 36,
       "seizure_present": "YES", "seizure_occurrence": "YES", "focal_neurologic_symptoms": "VISION_CHANGE",
       "vision_impairment_present": "YES", "vision_impairment_extent": "PARTIAL_LOSS", "headache_present": "YES",
       "pain_present": "YES", "systolic_bp": 168, "diastolic_bp": 112, "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, screen=HIT, concepts=("pregnancy_related_seizure", "visual_disturbance_in_pregnancy", "hypertension"),
      answers={"pregnancy_present": "Có, vợ tôi đang mang thai 36 tuần.",
               "pregnancy_status": "Vợ tôi đang mang thai 36 tuần.",
               "gestational_age_weeks": "Thai được 36 tuần.",
               "seizure_present": "Có, vợ tôi vừa co giật toàn thân.",
               "seizure_occurrence": "Có, khoảng 20 phút trước vợ tôi co giật toàn thân chừng một phút.",
               "focal_neurologic_symptoms": "Vợ kêu mắt nhìn không rõ, như bị che mất một phần; tay chân cử động được, "
                                            "nói rõ.",
               "vision_impairment_present": "Có, vợ kêu nhìn không rõ.",
               "vision_impairment_extent": "Chỉ thấy lờ mờ, như bị che mất một phần tầm nhìn.",
               "headache_present": "Có, vợ kêu đau đầu.",
               "pain_present": "Có, vợ kêu đau đầu.",
               "systolic_bp": "Tôi đo được 168/112.",
               "diastolic_bp": "Số dưới 112.",
               "altered_mental_status_present": "Giờ vợ tỉnh rồi, gọi biết, trả lời được.",
               "symptom_duration_bucket": "Mới khoảng 20 phút."},
      unknown={"fetal_movement_status": "Từ lúc vợ lên cơn tới giờ tôi chưa hỏi được con có đạp không.",
               "pain_severity": "Vợ tôi chỉ kêu đau đầu, chưa nói được đau mấy điểm."},
      tags=("pregnancy", "caregiver", "comorbidity", "null_unknown"),
      test="Co giật ở thai 36 tuần có tiền sản giật, sau cơn nhìn mất một phần và huyết áp 168/112: agent phải coi co "
           "giật kèm thay đổi thị lực là dấu hiệu đỏ ngay cả khi người mẹ đã tỉnh và trả lời được."),
    S("r118", "first_adult_seizure_left_arm_weakness", "Thanh niên 34 tuổi co giật lần đầu lúc ngủ, sau cơn tay trái yếu và tê",
      P(34, "Male", "SIBLING"),
      "Anh trai em 34 tuổi, trước giờ khỏe mạnh, không bệnh gì. Khoảng 5 giờ sáng nay chị dâu thấy anh đang ngủ thì co "
      "giật cả người chừng hai phút, cắn cả vào lưỡi. Giờ anh tỉnh rồi, nhận ra mọi người, nói chuyện rõ ràng, nhưng tay "
      "trái yếu hẳn, cầm cốc nước không chắc, tê bì từ vai xuống tới bàn tay. Anh không sốt, không bị ngã đập đầu, cũng "
      "không uống rượu bia.",
      {"seizure_present": "YES", "seizure_occurrence": "YES", "focal_neurologic_symptoms": "WEAKNESS_OR_NUMBNESS",
       "upper_extremity_problem_present": "YES", "upper_extremity_injury_location": "MULTIPLE",
       "upper_extremity_sensory_change": "NUMBNESS", "upper_extremity_movement_ability": "LIMITED",
       "altered_mental_status_present": "NO", "fever_present": "NO", "recent_head_trauma": "NO",
       "substance_involvement": "NONE_REPORTED", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen=HIT, concepts=("seizure", "limb_weakness"),
      answers={"seizure_present": "Có, sáng nay anh co giật cả người.",
               "seizure_occurrence": "Có, khoảng 5 giờ sáng chị dâu thấy anh co giật cả người chừng hai phút.",
               "focal_neurologic_symptoms": "Tay trái anh yếu hẳn, tê bì từ vai xuống bàn tay; mặt không méo, nói "
                                            "chuyện rõ ràng.",
               "upper_extremity_problem_present": "Có, tay trái anh yếu hẳn, cầm cốc nước không chắc.",
               "upper_extremity_injury_location": "Cả cánh tay trái, từ vai xuống tới bàn tay.",
               "upper_extremity_sensory_change": "Tê bì từ vai xuống tới bàn tay trái.",
               "upper_extremity_movement_ability": "Tay trái vẫn cử động được nhưng yếu, cầm cốc không chắc.",
               "altered_mental_status_present": "Giờ anh tỉnh rồi, nhận ra mọi người.",
               "fever_present": "Không, anh không sốt.",
               "recent_head_trauma": "Không, anh không bị ngã hay đập đầu.",
               "substance_involvement": "Anh không uống rượu bia, cũng không dùng chất gì.",
               "symptom_duration_bucket": "Anh co giật lúc 5 giờ sáng nay, tay trái yếu từ sau cơn tới giờ, mấy tiếng "
                                          "rồi."},
      tags=("collateral_history", "negation"),
      test="Cơn co giật đầu tiên ở người lớn khỏe mạnh, sau cơn tay trái yếu và tê: yếu tay sau cơn là dấu thần kinh "
           "khu trú, agent không được coi là mệt sau co giật; khác ca trẻ 9 tuổi nói ngọng sau cơn ở đợt 2."),

    # ------------------------------------------------------------------ khởi phát đột ngột kèm huyết áp thấp
    S("r119", "diabetic_burning_chest_mistaken_reflux_low_bp", "Người đái tháo đường đột ngột nóng rát giữa ngực, tưởng trào ngược, huyết áp 86/54",
      P(66, "Male", chronic=("Đái tháo đường type 2", "Tăng huyết áp"), meds=("Metformin", "Amlodipin 5 mg")),
      "Tôi 66 tuổi, bị tiểu đường với huyết áp cao. Khoảng 40 phút trước đang ngồi ăn trưa thì đột nhiên nóng rát giữa "
      "ngực, ngay sau xương ức, không lan đi đâu, người vã mồ hôi. Tôi nghĩ chắc trào ngược dạ dày nên uống thuốc dạ "
      "dày mà không đỡ, đau chừng 6 điểm. Con trai đo máy huyết áp cho tôi được 86/54, mạch 58. Tôi không khó thở, vẫn "
      "tỉnh, nói chuyện bình thường.",
      {"chest_pain_present": "YES", "chest_pain_quality": "BURNING", "chest_pain_location": "CENTRAL",
       "chest_pain_radiation": "NONE", "symptom_onset": "SUDDEN", "cardiorespiratory_symptom_present": "YES",
       "exertional_relation": "OCCURS_AT_REST", "pain_present": "YES", "pain_severity": 6, "systolic_bp": 86,
       "diastolic_bp": 54, "heart_rate": 58, "dyspnea_present": "NO", "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, screen=HIT, concepts=("chest_pain", "hypotension"),
      answers={"chest_pain_present": "Có, nóng rát giữa ngực.",
               "chest_pain_quality": "Nóng rát, như bị bỏng ở trong ngực.",
               "chest_pain_location": "Giữa ngực, ngay sau xương ức.",
               "chest_pain_radiation": "Không lan đi đâu.",
               "symptom_onset": "Đột ngột, đang ngồi ăn trưa thì bị.",
               "cardiorespiratory_symptom_present": "Có, nóng rát giữa ngực, nhưng không khó thở.",
               "exertional_relation": "Đang ngồi ăn thì bị, không phải lúc gắng sức.",
               "pain_present": "Có, nóng rát giữa ngực.",
               "pain_severity": "Chừng 6 điểm.",
               "systolic_bp": "Con trai tôi đo được 86/54.",
               "diastolic_bp": "Số dưới 54.",
               "heart_rate": "Máy báo mạch 58.",
               "dyspnea_present": "Không, tôi không khó thở.",
               "altered_mental_status_present": "Tôi vẫn tỉnh, nói chuyện bình thường.",
               "symptom_duration_bucket": "Khoảng 40 phút."},
      tags=("older_adult", "comorbidity", "minimization", "atypical_presentation"),
      test="Nóng rát giữa ngực khởi phát đột ngột kèm vã mồ hôi ở người đái tháo đường, tự cho là trào ngược, huyết "
           "áp 86/54: agent không được theo cách giải thích của người bệnh khi khởi phát đột ngột đi cùng huyết áp thấp."),
    S("r120", "gout_nsaid_course_sudden_epigastric_pain", "Tự uống thuốc kháng viêm trị gút, đột ngột đau như dao đâm vùng trên rốn, mạch 122, huyết áp 96/62",
      P(38, "Male", "SPOUSE", chronic=("Gút",), allergies=("Tôm",)),
      "Chồng em 38 tuổi bị gút. Tuần trước anh lên cơn đau khớp ngón chân nên tự mua thuốc giảm đau kháng viêm uống "
      "liền năm ngày, giờ khớp hết đau rồi. Khoảng 2 tiếng trước đang ngồi xem bóng đá thì anh đột ngột đau dữ dội vùng "
      "trên rốn như bị dao đâm, anh chấm 9/10, nằm co người không dám nhúc nhích, sờ bụng cứng đơ, chưa nôn. Đồng hồ "
      "của anh báo nhịp tim 122, em đo máy huyết áp được 96/62.",
      {"abdominal_pain_present": "YES", "abdominal_pain_location": "UPPER_ABDOMEN", "abdominal_pain_character": "SHARP",
       "pain_present": "YES", "pain_severity": 9, "symptom_onset": "SUDDEN", "heart_rate": 122, "systolic_bp": 96,
       "diastolic_bp": 62, "gastrointestinal_symptom_present": "YES", "vomiting_present": "NO",
       "joint_pain_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen=QUIET, concepts=("epigastric_pain", "tachycardia"),
      answers={"abdominal_pain_present": "Có, anh đau dữ dội vùng trên rốn.",
               "abdominal_pain_location": "Vùng trên rốn.",
               "abdominal_pain_character": "Đau như bị dao đâm.",
               "pain_present": "Có, anh đau bụng dữ dội.",
               "pain_severity": "Anh chấm 9/10.",
               "symptom_onset": "Đột ngột, đang ngồi xem bóng đá thì đau ập đến.",
               "heart_rate": "Đồng hồ của anh báo nhịp tim 122.",
               "systolic_bp": "Em đo máy được 96/62.",
               "diastolic_bp": "Số dưới 62.",
               "gastrointestinal_symptom_present": "Có, anh đau dữ dội vùng trên rốn.",
               "vomiting_present": "Anh chưa nôn.",
               "joint_pain_present": "Không, khớp ngón chân hết đau rồi.",
               "symptom_duration_bucket": "Khoảng 2 tiếng rồi."},
      tags=("caregiver", "comorbidity", "negation"),
      test="Đau như dao đâm vùng trên rốn khởi phát đột ngột sau đợt tự uống thuốc kháng viêm, mạch 122, huyết áp 96/62: "
           "agent phải kết hợp khởi phát đột ngột với nhịp nhanh và huyết áp thấp, không chỉ dựa vào điểm đau."),

    # ------------------------------------------------------------------ đau đầu đột ngột dữ dội
    S("r121", "straining_at_stool_sudden_throbbing_headache", "Cụ bà rặn đi ngoài thì đột ngột đau đầu giật thình thịch 9/10",
      P(69, "Female", "PARENT", chronic=("Tăng huyết áp", "Táo bón kinh niên"), meds=("Amlodipin 5 mg",)),
      "Mẹ tôi 69 tuổi, bị cao huyết áp, lại hay táo bón. Khoảng 30 phút trước mẹ đang ngồi rặn mạnh trong nhà vệ sinh thì "
      "đột ngột đau đầu dữ dội ở hai bên thái dương, giật thình thịch theo nhịp tim, mẹ bảo chưa bao giờ đau như thế, "
      "chấm 9/10. Mẹ nôn một lần. Tôi đo huyết áp cho mẹ được 178/96. Mẹ vẫn nói chuyện rõ ràng, tay chân cử động bình "
      "thường, miệng không méo.",
      {"headache_present": "YES", "headache_location": "TEMPORAL", "headache_character": "THROBBING",
       "symptom_onset": "SUDDEN", "pain_present": "YES", "pain_severity": 9, "vomiting_present": "YES",
       "vomiting_frequency": "ONCE", "gastrointestinal_symptom_present": "YES",
       "constipation_or_defecation_problem_present": "YES", "defecation_effort": "MARKED_STRAINING",
       "systolic_bp": 178, "diastolic_bp": 96, "focal_neurologic_symptoms": "NONE",
       "altered_mental_status_present": "NO", "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, screen=QUIET, concepts=("headache",),
      answers={"headache_present": "Có, mẹ đau đầu dữ dội.",
               "headache_location": "Hai bên thái dương.",
               "headache_character": "Giật thình thịch theo nhịp tim.",
               "symptom_onset": "Đột ngột, đang ngồi rặn thì đau ập đến.",
               "pain_present": "Có, mẹ đau đầu dữ dội.",
               "pain_severity": "Mẹ chấm 9/10, bảo chưa bao giờ đau như thế.",
               "vomiting_present": "Có, mẹ nôn một lần.",
               "vomiting_frequency": "Nôn một lần.",
               "gastrointestinal_symptom_present": "Có, mẹ nôn một lần, lại đang táo bón.",
               "constipation_or_defecation_problem_present": "Có, mẹ hay bị táo bón.",
               "defecation_effort": "Mẹ phải ngồi rặn mạnh.",
               "systolic_bp": "Tôi đo được 178/96.",
               "diastolic_bp": "Số dưới 96.",
               "focal_neurologic_symptoms": "Mẹ vẫn nói rõ, tay chân cử động bình thường, miệng không méo.",
               "altered_mental_status_present": "Mẹ vẫn tỉnh, nói chuyện rõ ràng.",
               "symptom_duration_bucket": "Khoảng 30 phút."},
      unknown={"days_since_last_bowel_movement": "Tôi không rõ lần cuối mẹ đi ngoài được là hôm nào."},
      tags=("older_adult", "caregiver", "comorbidity", "negation", "null_unknown"),
      test="Đau đầu giật thình thịch 9/10 khởi phát đột ngột khi rặn đi ngoài ở cụ bà tăng huyết áp: khởi phát đột ngột "
           "cùng tính chất và mức đau là quyết định, dù chưa có dấu thần kinh khu trú."),
    S("r122", "intimacy_sudden_stabbing_headache", "Đang gần gũi vợ chồng thì đột ngột đau nhói như dao đâm nửa đầu trái",
      P(38, "Female"),
      "Em ngại lắm nhưng vẫn phải hỏi. Khoảng 2 tiếng trước, lúc vợ chồng em đang gần gũi thì đột nhiên em đau nhói như "
      "dao đâm ở nửa đầu bên trái, đau tới mức phải bật dậy ôm đầu, lúc đó chắc 10/10, giờ vẫn còn 9. Em nôn một lần. "
      "Trước giờ em chưa từng đau đầu kiểu này. Tay chân em vẫn bình thường, nói năng bình thường.",
      {"headache_present": "YES", "headache_location": "UNILATERAL", "headache_character": "SHARP",
       "symptom_onset": "SUDDEN", "pain_present": "YES", "pain_severity": 9, "vomiting_present": "YES",
       "vomiting_frequency": "ONCE", "gastrointestinal_symptom_present": "YES", "focal_neurologic_symptoms": "NONE",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen=QUIET, concepts=("headache",),
      answers={"headache_present": "Có, em đau đầu dữ dội.",
               "headache_location": "Nửa đầu bên trái.",
               "headache_character": "Đau nhói như dao đâm.",
               "symptom_onset": "Đột nhiên, đang lúc gần gũi thì đau ập đến.",
               "pain_present": "Có, em đau nửa đầu bên trái.",
               "pain_severity": "Lúc đầu chắc 10/10, giờ vẫn còn 9.",
               "vomiting_present": "Có, em nôn một lần.",
               "vomiting_frequency": "Nôn một lần.",
               "gastrointestinal_symptom_present": "Có, em nôn một lần.",
               "focal_neurologic_symptoms": "Tay chân em vẫn bình thường, nói năng bình thường.",
               "symptom_duration_bucket": "Khoảng 2 tiếng rồi."},
      tags=("sensitive_topic", "indirect_phrasing", "negation"),
      test="Đau đầu nhói như dao đâm khởi phát đột ngột lúc quan hệ, người bệnh ngại nói: agent phải xếp ưu tiên cao "
           "theo khởi phát, tính chất và mức đau, không né chủ đề và không phán xét."),

    # ------------------------------------------------------------------ ngất lúc nghỉ, nhịp chậm
    S("r123", "known_slow_heart_siesta_syncope_pulse_36", "Cụ ông có hẹn đặt máy tạo nhịp lịm đi khi đang nằm nghỉ trưa, mạch 36",
      P(81, "Male", "OTHER", chronic=("Tăng huyết áp", "Nhịp tim chậm, đã được hẹn đặt máy tạo nhịp"),
        meds=("Amlodipin 5 mg",)),
      "Ông nội cháu 81 tuổi. Năm ngoái bác sĩ bảo tim ông đập chậm, hẹn đặt máy tạo nhịp mà ông chưa chịu đi. Khoảng 20 "
      "phút trước ông đang nằm nghỉ trưa trên phản thì mặt tái đi, gọi không biết gì chừng nửa phút rồi mới tỉnh lại. "
      "Giờ ông tỉnh, nói chuyện được nhưng kêu người mệt. Cháu đo bằng máy huyết áp được 108/62, máy báo mạch có 36.",
      {"syncope_present": "YES", "syncope_context": "AT_REST", "heart_rate": 36, "systolic_bp": 108,
       "diastolic_bp": 62, "altered_mental_status_present": "NO", "associated_systemic_symptoms": "GENERAL_WEAKNESS",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, screen=HIT, concepts=("syncope", "generalized_weakness"),
      answers={"syncope_present": "Có, ông lịm đi chừng nửa phút.",
               "syncope_context": "Ông đang nằm nghỉ trưa trên phản thì bị.",
               "heart_rate": "Máy đo huyết áp báo mạch có 36.",
               "systolic_bp": "Huyết áp đo được 108/62.",
               "diastolic_bp": "Số dưới 62.",
               "altered_mental_status_present": "Giờ ông tỉnh rồi, nói chuyện được.",
               "associated_systemic_symptoms": "Ông kêu người mệt.",
               "symptom_duration_bucket": "Mới khoảng 20 phút."},
      review_concern=("Mạch 36 ngay sau một cơn ngất lúc đang nằm nghỉ, người còn mệt, ở cụ ông 81 tuổi: chương 3 của "
                      "AHRQ ESI nêu 'yếu, chóng mặt, nhịp tim 30' và 'nhịp chậm nặng kèm dấu hiệu giảm tưới máu' là ví dụ "
                      "ESI 1 (Decision Point A: có thể cần atropin hoặc tạo nhịp ngoài ngay). Cơn ngất vừa xảy ra là dấu "
                      "hiệu giảm tưới máu não nên điều dưỡng theo AHRQ có thể xếp ESI 1, dù huyết áp lúc kể còn 108/62; "
                      "corpus chỉ cho ESI 2 qua esi_2_syncope_with_bradycardia."),
      tags=("older_adult", "collateral_history", "comorbidity"),
      test="Lịm đi khi đang nằm nghỉ kèm mạch 36 ở cụ ông đã được hẹn đặt máy tạo nhịp: ngất lúc nghỉ cùng nhịp chậm "
           "là mẫu nguy cơ cao dù huyết áp còn 108; khác ca ngất kèm nhịp nhanh ở đợt 2."),

    # ------------------------------------------------------------------ dương vật
    S("r124", "online_aphrodisiac_prolonged_erection", "Uống thuốc cường dương mua trên mạng, cương cứng hơn 7 tiếng, đau tăng dần",
      P(45, "Male", allergies=("Sulfamid",)),
      "Toi 45t. Khoang 11h toi qua toi co uong 1 vien thuoc cuong duong mua tren mang, ko ro thanh phan, ko uong ruou. "
      "Tu luc do toi gio hon 7 tieng roi ma duong vat van cuong cung, ko xiu xuong, cang luc cang dau, gio chac 8/10. "
      "Van di tieu dc. Ngai qua nhung ko biet phai lam sao.",
      {"genitourinary_pain_present": "YES", "genitourinary_pain_location": "PENILE", "genital_symptom_present": "YES",
       "visible_genital_change": "OTHER", "pain_present": "YES", "pain_severity": 8, "symptom_trend": "WORSENING",
       "urinary_symptom_present": "NO", "toxic_exposure_present": "YES", "toxic_substance_category": "MEDICATION",
       "toxic_exposure_route": "INGESTION", "estimated_exposure_amount": "SMALL",
       "exposure_intent": "OTHER_INTENTIONAL", "coingestion_status": "NONE",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen=QUIET, concepts=("priapism", "penile_pain"),
      answers={"genitourinary_pain_present": "Co, dau o duong vat.",
               "genitourinary_pain_location": "Dau o duong vat.",
               "genital_symptom_present": "Co, duong vat cuong cung hon 7 tieng ko xiu.",
               "visible_genital_change": "No van cuong cung, ko xiu xuong.",
               "pain_present": "Co, dau o duong vat.",
               "pain_severity": "Gio chac 8/10.",
               "symptom_trend": "Cang luc cang dau hon.",
               "urinary_symptom_present": "Ko, van di tieu dc binh thuong.",
               "toxic_exposure_present": "Co uong 1 vien thuoc cuong duong mua tren mang.",
               "toxic_substance_category": "Thuoc cuong duong, ko ro thanh phan.",
               "toxic_exposure_route": "Uong.",
               "estimated_exposure_amount": "1 vien thoi.",
               "exposure_intent": "Toi tu uong de quan he, ko phai uong nham hay de hai minh.",
               "coingestion_status": "Ko, toi ko uong ruou hay thuoc gi khac.",
               "symptom_duration_bucket": "Tu khoang 11h toi qua, hon 7 tieng roi."},
      clarification="Noi lai cho ro: khoang 11h toi qua toi uong 1 vien thuoc cuong duong mua tren mang, hon 7 tieng "
                    "roi duong vat van cuong cung ko xiu, cang luc cang dau, gio chac 8/10, van di tieu dc.",
      confirmation="Dung het roi, ban hoan tat giup toi.",
      tags=("no_diacritics", "abbreviation", "sensitive_topic", "toxic"),
      test="Cương cứng kéo dài hơn 7 tiếng sau uống thuốc cường dương không rõ nguồn, đau tăng dần 8/10, gõ không dấu: "
           "agent phải xếp ưu tiên cao theo vị trí đau và diễn tiến, không né vì chủ đề nhạy cảm."),

    # ------------------------------------------------------------------ RETURN_INCOMPLETE: hai tiêu chí ý thức không khớp được
    S("r125", "mango_tree_fall_child_post_trauma_confusion", "Bé trai 10 tuổi ngã cây xoài đập đầu, sau đó ngơ ngác hỏi đi hỏi lại",
      P(10, "Male", "CHILD"),
      "Con trai tôi 10 tuổi, khoảng 40 phút trước trèo cây xoài sau nhà bị ngã từ độ cao chừng hai mét, đập đầu xuống "
      "đất. Em nó đứng dưới gốc kể là cháu khóc ngay, không ngất. Nhưng từ lúc đó cháu cứ ngơ ngác, hỏi đi hỏi lại 'con "
      "đang ở đâu', nói chuyện lộn xộn, không giống mọi ngày. Sau đầu có một cục u. Cháu chưa nôn, tay chân vẫn cử động "
      "được.",
      {"trauma_present": "YES", "trauma_mechanism": "FALL", "injury_region": "HEAD", "recent_head_trauma": "YES",
       "post_trauma_awareness_change": "CONFUSION", "altered_mental_status_present": "YES",
       "visible_head_injury_sign": "SCALP_SWELLING", "swelling_present": "YES", "swelling_location": "OTHER",
       "post_trauma_vomiting_count": 0, "limb_neurologic_symptoms": "NONE",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      INCOMPLETE, screen=QUIET, concepts=("head_injury", "confusion"),
      answers={"trauma_present": "Có, cháu ngã từ trên cây xoài xuống.",
               "trauma_mechanism": "Trèo cây xoài bị ngã từ độ cao chừng hai mét.",
               "injury_region": "Đầu đập xuống đất.",
               "recent_head_trauma": "Có, khoảng 40 phút trước cháu đập đầu xuống đất.",
               "post_trauma_awareness_change": "Cháu không ngất, nhưng từ lúc ngã cứ ngơ ngác, hỏi đi hỏi lại 'con đang "
                                               "ở đâu'.",
               "altered_mental_status_present": "Có, cháu ngơ ngác, nói chuyện lộn xộn, không giống mọi ngày.",
               "visible_head_injury_sign": "Sau đầu có một cục u.",
               "swelling_present": "Có, sau đầu có một cục u.",
               "swelling_location": "Ở sau đầu.",
               "post_trauma_vomiting_count": "Cháu chưa nôn lần nào.",
               "limb_neurologic_symptoms": "Tay chân cháu vẫn cử động được.",
               "symptom_duration_bucket": "Mới khoảng 40 phút."},
      unknown={"headache_present": "Cháu nói lộn xộn quá, tôi hỏi có đau đầu không mà cháu trả lời không rõ."},
      review_concern=("Lú lẫn mới sau chấn thương đầu ở trẻ 10 tuổi là tình huống nguy cơ cao theo Decision Point B "
                      "(thay đổi ý thức mới), AHRQ xếp ít nhất ESI 2. Tiêu chí esi_2_post_trauma_confusion của corpus đòi "
                      "post_trauma_awareness_change đồng thời bằng CONFUSION, LOSS_OF_CONSCIOUSNESS và MEMORY_GAP trong "
                      "cùng một nhánh nên không bao giờ khớp; tiêu chí còn lại về lú lẫn sau chấn thương "
                      "(esi_2_head_vomiting_with_confusion) đòi thêm ít nhất một lần nôn, và lú lẫn không sốt "
                      "(altered_mental_status_present) không có tiêu chí riêng. Vì vậy trẻ lú lẫn mà chưa nôn cho ra "
                      "RETURN_INCOMPLETE."),
      tags=("pediatric", "caregiver", "collateral_history", "corpus_gap", "negation", "null_unknown"),
      test="Trẻ lú lẫn sau ngã đập đầu, không ngất, chưa nôn: corpus không có tiêu chí nào khớp nên agent phải chuyển "
           "nhân viên y tế ngay, không được coi là va đập nhẹ vì trẻ không ngất."),
    S("r126", "football_head_clash_brief_loc_alert", "Đá bóng cụng đầu với đối thủ, bất tỉnh chừng một phút, giờ tỉnh táo",
      P(24, "Male", "OTHER"),
      "Tui nhắn giùm thằng bạn đá banh chung, nó 24 tuổi. Cách đây chừng 30 phút nó nhảy lên đánh đầu thì cụng đầu với "
      "một người đội bên kia, té xuống nằm im, kêu hông trả lời chừng 1 phút mới tỉnh. Giờ nó tỉnh táo, nhớ hết trận, "
      "nói chuyện bình thường, trán sưng u một cục, nhức đầu chút xíu, chắc cỡ 3 điểm. Chưa ói, tay chân cử động bình "
      "thường.",
      {"trauma_present": "YES", "trauma_mechanism": "SPORTS_INJURY", "injury_region": "HEAD",
       "recent_head_trauma": "YES", "post_trauma_awareness_change": "LOSS_OF_CONSCIOUSNESS",
       "syncope_present": "YES",
       "altered_mental_status_present": "NO", "visible_head_injury_sign": "SCALP_SWELLING", "swelling_present": "YES",
       "swelling_location": "FACE", "headache_present": "YES", "pain_present": "YES", "pain_severity": 3,
       "post_trauma_vomiting_count": 0, "limb_neurologic_symptoms": "NONE",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, screen=HIT, concepts=("head_injury", "loss_of_consciousness"),
      answers={"trauma_present": "Có, nó cụng đầu với người ta lúc đá banh.",
               "trauma_mechanism": "Nhảy lên đánh đầu thì cụng đầu với một người đội bên kia.",
               "injury_region": "Ở đầu, chỗ trán.",
               "recent_head_trauma": "Có, cách đây chừng 30 phút.",
               "post_trauma_awareness_change": "Nó té xuống nằm im, kêu hông trả lời chừng 1 phút mới tỉnh; giờ nhớ hết "
                                               "trận.",
               "syncope_present": "Có, nó bất tỉnh chừng 1 phút sau khi cụng đầu rồi mới tỉnh.",
               "altered_mental_status_present": "Giờ nó tỉnh táo, nói chuyện bình thường.",
               "visible_head_injury_sign": "Trán sưng u một cục.",
               "swelling_present": "Có, trán sưng u một cục.",
               "swelling_location": "Sưng ở trán, chỗ cụng đầu.",
               "headache_present": "Có, nó nhức đầu chút xíu.",
               "pain_present": "Có, nhức đầu chút xíu.",
               "pain_severity": "Nó nói chắc cỡ 3 điểm.",
               "post_trauma_vomiting_count": "Chưa ói lần nào.",
               "limb_neurologic_symptoms": "Tay chân nó cử động bình thường.",
               "symptom_duration_bucket": "Mới chừng 30 phút."},
      tags=("collateral_history", "dialect", "negation"),
      test="Bất tỉnh khoảng một phút sau cụng đầu khi đá bóng, nay tỉnh táo và đau ít: mất ý thức là dữ kiện quyết định "
           "(ESI 2), agent không được trấn an vì người bệnh đã tỉnh; khác ca r61 ở cơ chế chấn thương."),
]
