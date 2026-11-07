"""Nhóm CONFLICTING, đợt 2: mâu thuẫn quanh bỏng và chấn thương đè dập.

Đợt 2 tập trung vào những tình huống mà một chi tiết bị kể sai lúc đầu rồi được
sửa lại quyết định nhãn: phạm vi bỏng, bỏng vòng quanh chi, vị trí bỏng (bàn
tay, vùng sinh dục - tầng sinh môn, mặt cổ), màu da và cảm giác ở vùng bỏng, và
dấu hiệu thần kinh - mạch máu sau đè dập.

Quy ước giữ nguyên như ``conflict.py`` của đợt 1: ``facts`` là trạng thái CUỐI
CÙNG sau khi đính chính; lời đính chính nằm ở chỗ agent chắc chắn nghe thấy
(câu trả lời cho đúng dữ kiện đó, ``confirmation``, hoặc ``clarification``);
``conflict`` ghi hai phiên bản. Riêng trong tệp này:

- Khi phiên bản ban đầu tự nó đã cho một nhãn quyết định (ESI 1-2), agent có thể
  kết thúc trước bước xác nhận, nên lời đính chính được đặt ngay trong lời mở
  đầu (k35, k36, k39, k40).
- ``test`` ghi nhãn của cả hai phiên bản. Nhãn của phiên bản ban đầu được tính
  bằng chính bộ kiểm tra, bằng cách tạm thay ``facts`` của ca bằng dữ kiện ban
  đầu; không có nhãn nào được viết tay.
"""

from __future__ import annotations

from eval.generated_mock_v2.spec import CONFLICT, INCOMPLETE, P, SCREEN_HIT as HIT, SCREEN_QUIET as QUIET, Spec


def S(key: str, family: str, title: str, profile: dict, opening: str, facts: dict, intended, **kw) -> Spec:
    return Spec(case_id=key, family=family, group=CONFLICT, title=title, profile=profile,
                opening=opening, facts=facts, intended=intended, **kw)


SPECS = [
    S("k21", "battery_acid_extent_after_undressing", "Axit ắc quy: tưởng chỉ cánh tay, cởi áo mới thấy nhiều vùng",
      P(34, "Male", allergies=("Penicilin",)),
      "Em làm tiệm sạc bình ắc quy, chừng 20 phút trước cái bình bị nứt, axit văng trúng cánh tay trái, chỗ đó đỏ rát cỡ lòng "
      "bàn tay. Em xả nước rồi mà vẫn rát.",
      {"burn_present": "YES", "burn_mechanism": "CHEMICAL", "burn_location": "MULTIPLE_AREAS",
       "burn_extent_estimate": "MULTIPLE_BODY_REGIONS", "burn_skin_appearance": "RED",
       "burn_sensation": "PAINFUL_OR_BURNING", "pain_present": "YES", "pain_severity": 6,
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("chemical_burn",), screen=QUIET,
      answers={"burn_mechanism": "Axit trong bình ắc quy văng ra.",
               "burn_location": "Không chỉ cánh tay đâu, em thay đồ ra mới thấy ngực, bụng với đùi phải cũng bị.",
               "burn_extent_estimate": "Lúc nãy em tưởng chỉ một mảng ở cánh tay, cởi áo với quần ra mới thấy axit thấm qua "
                                       "đồ: ngực, bụng với đùi phải cũng đỏ rát từng mảng.",
               "pain_severity": "Rát nhiều, chắc cỡ 6.",
               "symptom_duration_bucket": "Mới chừng 20 phút."},
      confirmation="Em nói lại: cởi áo với quần ra mới thấy axit thấm qua đồ, không chỉ cánh tay trái mà ngực, bụng với đùi "
                   "phải cũng đỏ rát từng mảng.",
      conflict=("Lời kể: chỉ cánh tay trái, cỡ lòng bàn tay", "Đính chính sau khi cởi đồ: thêm ngực, bụng, đùi phải (nhiều vùng)"),
      tags=("contradiction", "changed_answer", "progressive_disclosure", "occupational", "dialect"),
      test="Phạm vi bỏng hoá chất chỉ lộ ra muộn, sau khi cởi áo quần: bản đầu (một mảng ở cánh tay) là INCOMPLETE, bản đính "
           "chính (nhiều vùng cơ thể) là ESI 2."),
    S("k22", "sleeve_fire_circumferential_forearm", "Bà nội bỏng do tay áo bắt lửa, hoá ra vòng kín quanh cẳng tay",
      P(72, "Female", "OTHER", chronic=("Tăng huyết áp",), meds=("Losartan 50 mg mỗi sáng",)),
      "Bà nội em 72 tuổi nấu cám heo bằng bếp củi, lửa bén vô tay áo, bỏng một mảng ở mặt trong cẳng tay phải, da phồng nước. "
      "Bà kêu rát lắm, chừ phải làm răng?",
      {"burn_present": "YES", "burn_mechanism": "FLAME", "burn_location": "UPPER_LIMB",
       "burn_skin_appearance": "BLISTERED", "burn_sensation": "PAINFUL_OR_BURNING", "burn_encirclement": "AROUND_ARM",
       "pain_present": "YES"},
      2, concepts=("burn_injury", "skin_blistering"), screen=QUIET,
      answers={"burn_mechanism": "Lửa bếp củi bén vô tay áo.",
               "burn_location": "Ở cẳng tay phải.",
               "burn_encirclement": "Lúc đầu em tưởng một mảng, nhưng tháo khăn ra xem kỹ thì vết bỏng chạy vòng kín quanh "
                                    "cẳng tay, mặt ngoài cũng phồng."},
      unknown={"pain_severity": "Bà không chấm điểm được, em hỏi thì bà chỉ lắc đầu."},
      confirmation="Em sửa lại một chỗ: vết bỏng của bà không phải một mảng mà chạy vòng kín quanh cẳng tay phải, cả mặt "
                   "ngoài cũng phồng nước.",
      conflict=("Lời kể: một mảng ở mặt trong cẳng tay", "Đính chính khi hỏi lại: vòng kín quanh cẳng tay"),
      tags=("contradiction", "changed_answer", "older_adult", "caregiver", "comorbidity", "dialect"),
      test="Bỏng vòng quanh chi chỉ lộ ra khi được hỏi lại: bản đầu (một mảng) là INCOMPLETE, bản đính chính (vòng kín "
           "quanh cẳng tay) là ESI 2."),
    S("k23", "infant_bucket_scald_circumferential", "Mẹ thấy bỏng mu bàn chân, bà thấy vòng kín cổ chân và bắp chân",
      P(0, "Female", "CHILD", months=11),
      "Con em 11 tháng đang tập đi, vịn vào xô nước nóng bà pha để tắm rồi hụt chân bước vào trong. Em thấy mu bàn chân "
      "phải đỏ ửng, phồng mấy bóng nước nhỏ, bé khóc ré lên.",
      {"burn_present": "YES", "burn_mechanism": "HOT_LIQUID", "burn_location": "LOWER_LIMB",
       "burn_encirclement": "AROUND_LEG", "burn_skin_appearance": "BLISTERED"},
      2, concepts=("scald_exposure", "burn_injury"), screen=QUIET,
      answers={"burn_mechanism": "Nước nóng trong xô pha để tắm.",
               "burn_location": "Bà cháu cởi tất ra xem: không chỉ mu bàn chân mà cả cổ chân lên gần nửa bắp chân phải.",
               "burn_encirclement": "Bà bảo vết bỏng vòng kín quanh cổ chân với nửa dưới bắp chân như đi tất, mặt sau cũng "
                                    "phồng; lúc nãy em chỉ nhìn mặt trước."},
      confirmation="Em sửa lại theo lời bà cháu: bé bỏng vòng kín quanh cổ chân và nửa dưới bắp chân phải, không chỉ ở mu "
                   "bàn chân.",
      conflict=("Mẹ: chỉ mu bàn chân", "Bà: vòng kín quanh cổ chân và nửa dưới bắp chân"),
      tags=("contradiction", "collateral_history", "pediatric", "caregiver"),
      test="Hai người chăm sóc tả vết bỏng khác nhau: bản của mẹ (mu bàn chân) là INCOMPLETE, bản của bà (vòng kín quanh "
           "chân) là ESI 2."),
    S("k24", "wall_collapse_back_hidden_leg_numbness", "Thợ hồ bị tường sập đè lưng, giấu chuyện tê hai chân",
      P(45, "Male"),
      "Tui làm hồ, chiều nay bức tường gạch đang xây sập đè lên lưng tui, anh em kéo ra liền. Giờ đau nguyên cái lưng thôi, "
      "chân cẳng bình thường, chắc hông sao đâu.",
      {"trauma_present": "YES", "trauma_mechanism": "CRUSH_INJURY", "injury_region": "ENTIRE_BACK",
       "back_or_spinal_problem_present": "YES", "limb_neurologic_symptoms": "NUMBNESS", "pain_present": "YES",
       "pain_severity": 6, "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("crush_injury", "back_injury", "lower_extremity_numbness"), screen=QUIET,
      answers={"trauma_mechanism": "Bức tường gạch sập đè lên lưng.",
               "injury_region": "Nguyên cái lưng, từ bả vai xuống tới thắt lưng.",
               "back_or_spinal_problem_present": "Có, đau nguyên cái lưng từ lúc bị tường đè.",
               "limb_neurologic_symptoms": "Nói thiệt là từ lúc bị đè, hai chân tê rần, nhéo vô không thấy rõ. Tui sợ mất "
                                           "việc nên nói vậy.",
               "pain_severity": "Chắc cỡ 6.",
               "symptom_duration_bucket": "Từ chiều nay, mấy tiếng rồi."},
      unknown={"bowel_bladder_control_change": "Từ lúc bị đè tới giờ tui chưa đi vệ sinh lần nào nên hông biết."},
      confirmation="Tui nói lại cho đúng: từ lúc bị tường đè, hai chân tui tê rần, nhéo vô không thấy rõ, chứ không phải bình "
                   "thường như hồi nãy tui nói.",
      conflict=("Lời kể: chân cẳng bình thường", "Thừa nhận: hai chân tê từ lúc bị đè"),
      tags=("contradiction", "minimization", "changed_answer", "occupational", "dialect", "progressive_disclosure"),
      test="Người bệnh nói giảm vì sợ mất việc, chỉ thừa nhận muộn khi được hỏi: bản đầu (chân bình thường) là INCOMPLETE, "
           "bản thừa nhận (tê hai chân sau khi bị đè cả lưng) là ESI 2."),
    S("k25", "sugarcane_press_fingers_teen", "Mẹ nói con còn cử động ngón, con nói ba ngón không nhúc nhích",
      P(15, "Male", "CHILD"),
      "Thằng con tôi 15 tuổi phụ tôi bán nước mía, chừng nửa tiếng trước ba ngón tay trái bị cuốn vào trục máy ép, dập bầm "
      "tím, nó kêu đau 6. Tôi thấy nó vẫn nhúc nhích được ngón tay, chắc chỉ dập phần mềm thôi.",
      {"trauma_present": "YES", "trauma_mechanism": "CRUSH_INJURY",
       "upper_extremity_problem_present": "YES", "upper_extremity_injury_location": "FINGER",
       "upper_extremity_injury_mechanism": "CRUSH", "upper_extremity_movement_ability": "UNABLE",
       "pain_present": "YES", "pain_severity": 6, "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("upper_extremity_crush_injury", "finger_pain"), screen=QUIET,
      review_concern="Ba ngón tay bị dập, bầm, không có dấu hiệu mạch máu (không lạnh, không tím tái), đau 6/10: tiêu chí "
                     "'đè dập kèm không cử động được' của corpus vốn dành cho cả chi. Ở Decision Point B không thấy dấu hiệu "
                     "nguy cơ cao rõ; điều dưỡng nhiều khả năng xếp ESI 3 (chụp X-quang, hội chẩn phẫu thuật bàn tay).",
      answers={"trauma_mechanism": "Bị trục máy ép mía cuốn tay vào, kẹp dập.",
               "symptom_duration_bucket": "Mới chừng nửa tiếng.",
               "upper_extremity_injury_mechanism": "Bị trục máy ép mía cuốn vào, kẹp dập.",
               "upper_extremity_movement_ability": "Cháu bảo tôi nhìn nhầm: cái nhúc nhích là ngón cái với ngón út, còn ba "
                                                   "ngón bị cuốn thì không gập duỗi được tí nào.",
               "pain_severity": "Cháu nói đau 6."},
      confirmation="Tôi sửa lại theo lời cháu: ba ngón bị cuốn vào máy không cử động được chút nào, hai ngón tôi thấy nhúc "
                   "nhích là ngón cái với ngón út.",
      conflict=("Mẹ: vẫn nhúc nhích được ngón", "Con: ba ngón bị cuốn không cử động được"),
      tags=("contradiction", "collateral_history", "adolescent", "caregiver", "occupational"),
      test="Lời mẹ và lời con về cử động ngón tay khác nhau: bản của mẹ (còn cử động) là INCOMPLETE, bản của con (ba ngón "
           "bị dập không cử động được) là ESI 2."),
    S("k26", "rolling_shutter_forearm_wrong_hand_checked", "Con gái sờ nhầm tay lành, tay bị cửa cuốn đè lạnh và trắng nhợt",
      P(68, "Male", "PARENT", chronic=("Rung nhĩ",), meds=("Apixaban 5 mg ngày hai lần",)),
      "Bố tôi 68 tuổi bị cửa cuốn sập xuống đè vào cẳng tay trái lúc mất điện, kẹt chừng mười phút mới nâng lên được. Bố "
      "đang uống thuốc chống đông, kêu đau chừng 6. Tôi sờ thì bàn tay vẫn ấm, hồng hào bình thường.",
      {"trauma_present": "YES", "trauma_mechanism": "CRUSH_INJURY",
       "upper_extremity_problem_present": "YES", "upper_extremity_injury_location": "FOREARM",
       "upper_extremity_injury_mechanism": "CRUSH", "distal_color_temperature_change": "MULTIPLE_CHANGES",
       "pain_present": "YES", "pain_severity": 6},
      2, concepts=("upper_extremity_crush_injury", "upper_extremity_coldness"), screen=QUIET,
      answers={"trauma_mechanism": "Cửa cuốn sập xuống đè lên cẳng tay.",
               "upper_extremity_injury_mechanism": "Cửa cuốn sập xuống đè lên cẳng tay.",
               "distal_color_temperature_change": "Lúc nãy tôi sờ nhầm bàn tay phải. Bàn tay trái, tay bị đè, lạnh hơn hẳn "
                                                  "và trắng nhợt.",
               "pain_severity": "Bố bảo đau 6."},
      confirmation="Tôi phải sửa lại: lúc nãy tôi sờ nhầm bàn tay phải của bố; bàn tay trái bị cửa đè thì lạnh và trắng nhợt "
                   "hơn hẳn.",
      conflict=("Lời kể: bàn tay ấm, hồng (sờ nhầm tay lành)", "Đính chính: bàn tay trái bị đè lạnh và trắng nhợt"),
      tags=("contradiction", "wrong_side", "changed_answer", "older_adult", "anticoagulant", "caregiver"),
      test="Người kể kiểm tra nhầm bên tay lành: bản đầu (tay ấm, hồng) là INCOMPLETE, bản đính chính (tay bị đè lạnh, "
           "trắng nhợt) là ESI 2."),
    S("k27", "hot_salt_pack_neuropathy_dark_burn", "Cụ ông mắt kém tưởng vết chườm chỉ đỏ, con gái thấy mảng sẫm đen",
      P(76, "Male", chronic=("Đái tháo đường type 2", "Bệnh thần kinh ngoại biên do đái tháo đường"),
        meds=("Metformin 850 mg ngày hai lần",)),
      "Tối qua tôi chườm túi muối rang lên bắp chân phải cho đỡ mỏi rồi ngủ quên. Sáng ra thấy chỗ đó hơi đỏ, không đau gì "
      "nên chắc không sao. Mắt tôi kém, nhìn không rõ lắm.",
      {"burn_present": "YES", "burn_mechanism": "HOT_OBJECT", "burn_location": "LOWER_LIMB",
       "burn_skin_appearance": "DARKENED", "burn_sensation": "NO_SENSATION", "pain_present": "NO",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("burn_injury",), screen=QUIET,
      answers={"burn_mechanism": "Túi muối rang nóng để chườm.",
               "burn_location": "Ở bắp chân phải.",
               "burn_skin_appearance": "Con gái tôi vừa xem bảo không phải đỏ: cả mảng đó sẫm nâu đen, khô cứng như da thuộc.",
               "burn_sensation": "Con gái tôi lấy tăm chọc nhẹ vào giữa mảng đó, tôi không thấy gì cả.",
               "pain_present": "Không thấy đau.",
               "symptom_duration_bucket": "Chườm từ tối qua, sáng nay mới thấy."},
      confirmation="Con gái tôi xem kỹ rồi: chỗ bỏng không đỏ như tôi tưởng mà sẫm nâu đen, khô cứng, lấy tăm chọc vào không "
                   "thấy gì.",
      conflict=("Người bệnh (mắt kém): chỉ hơi đỏ", "Con gái xem: mảng sẫm nâu đen, khô cứng, chọc không cảm giác"),
      tags=("contradiction", "collateral_history", "minimization", "older_adult", "comorbidity"),
      test="Người bệnh mắt kém, mất cảm giác do bệnh thần kinh đái tháo đường tả sai vết bỏng: bản đầu (hơi đỏ) là "
           "INCOMPLETE, bản người nhà xem (sẫm đen, mất cảm giác) là ESI 2."),
    S("k28", "toddler_charger_cord_mouth_burn", "Bé cắn dây sạc, bố mẹ tưởng không bỏng, sau thấy vết ở khoé miệng",
      P(2, "Male", "CHILD"),
      "Bé nhà mình 2 tuổi cắn vào dây sạc điện thoại đang cắm, bị giật một cái rồi khóc thét. Giờ bé tỉnh, chơi lại rồi, mình "
      "xem qua thì không thấy bỏng gì.",
      {"burn_present": "YES", "burn_mechanism": "ELECTRICAL", "burn_location": "FACE_OR_NECK",
       "burn_skin_appearance": "PALE_OR_WHITE", "altered_mental_status_present": "NO", "activity_level": "NORMAL"},
      2, concepts=("electrical_exposure", "oral_burn"), screen=QUIET,
      answers={"burn_present": "Lúc nãy mình nhìn vội; giờ bé há miệng mới thấy khoé miệng bên trái có một vết trắng xám.",
               "burn_mechanism": "Do cắn vào dây sạc đang cắm điện.",
               "burn_location": "Ở khoé miệng bên trái, chỗ môi trên với môi dưới gặp nhau.",
               "burn_skin_appearance": "Trắng xám, hơi lõm xuống.",
               "activity_level": "Bé chơi bình thường như mọi ngày."},
      confirmation="Mình sửa lại: có bỏng đó, khoé miệng trái của bé có một vết trắng xám, lúc nãy mình nhìn vội nên không thấy.",
      conflict=("Lời kể: xem qua không thấy bỏng", "Đính chính: vết bỏng điện trắng xám ở khoé miệng trái"),
      tags=("contradiction", "changed_answer", "pediatric", "caregiver", "hidden_red_flag"),
      test="Bỏng điện ở khoé miệng bị bỏ sót lúc đầu: bản đầu (không bỏng) là INCOMPLETE, bản đính chính (bỏng điện vùng "
           "mặt) là ESI 2."),
    S("k29", "heat_press_palm_self_corrected", "Thợ in áo tự đính chính: lòng bàn tay không đỏ rát mà trắng bệch, mất cảm giác",
      P(23, "Female"),
      "Em lam o xuong in ao thun, tay phai bi ban ep nhiet dap xuong. Long ban tay do rat... a khoan, em nhin ky lai thi cho "
      "bi ep trang bech, cham vao khong thay gi het.",
      {"burn_present": "YES", "burn_mechanism": "HOT_OBJECT", "burn_location": "HAND",
       "burn_skin_appearance": "PALE_OR_WHITE", "burn_sensation": "NO_SENSATION"},
      2, concepts=("burn_injury", "hand_pain"), screen=QUIET,
      answers={"burn_present": "Co, bi bong.",
               "burn_mechanism": "Ban ep nhiet in ao dap xuong tay.",
               "burn_location": "Long ban tay phai.",
               "burn_skin_appearance": "Cho bi ep trang bech.",
               "burn_sensation": "Cham vao khong thay gi het."},
      conflict=("Câu đầu: lòng bàn tay đỏ rát", "Tự đính chính trong cùng lời kể: trắng bệch, chạm không cảm giác"),
      tags=("contradiction", "no_diacritics", "occupational"),
      test="Tự đính chính ngay trong lời kể không dấu: phần đầu (đỏ rát) là INCOMPLETE, phần đính chính (bàn tay trắng bệch, "
           "mất cảm giác) là ESI 2."),
    S("k30", "teen_firecracker_hand_concealed", "Con nói bỏng nhẹ cẳng tay do bật lửa, mẹ thấy bàn tay cháy sém do pháo",
      P(14, "Male", "CHILD"),
      "Con trai tôi 14 tuổi đi chơi về cứ giấu tay trong áo. Nó bảo chỉ bị bỏng nhẹ ở cẳng tay do nghịch bật lửa, da hơi đen "
      "một chút, đau chừng 5, không sao đâu.",
      {"burn_present": "YES", "burn_mechanism": "FLAME", "burn_location": "HAND",
       "burn_skin_appearance": "DARKENED", "pain_present": "YES", "pain_severity": 5},
      2, concepts=("burn_injury", "hand_pain"), screen=QUIET,
      answers={"burn_location": "Tôi bắt nó xoè tay ra thì không phải cẳng tay: lòng bàn tay phải với mấy đầu ngón cháy sém đen.",
               "burn_mechanism": "Nó thú nhận là châm pháo tự chế, pháo nổ sớm, lửa táp vào tay.",
               "burn_skin_appearance": "Cháy sém đen, rửa nước rồi vẫn đen.",
               "pain_severity": "Nó bảo đau 5."},
      confirmation="Tôi sửa lại: con tôi bỏng ở bàn tay phải chứ không phải cẳng tay, lòng bàn tay và mấy đầu ngón cháy sém "
                   "đen, do pháo tự chế nổ sớm.",
      conflict=("Con kể: bỏng nhẹ ở cẳng tay do bật lửa", "Mẹ xem: lòng bàn tay và đầu ngón phải cháy sém đen do pháo"),
      tags=("contradiction", "collateral_history", "adolescent", "caregiver", "hidden_red_flag", "progressive_disclosure"),
      test="Vị trí bỏng bị con giấu, chỉ lộ ra muộn khi mẹ xem tay: bản đầu (cẳng tay, hơi đen) là INCOMPLETE, bản đính chính "
           "(bàn tay cháy sém đen) là ESI 2."),
    S("k31", "pregnant_scald_inverted_pain_scale", "Thai 31 tuần bỏng nước sôi ở đùi, chấm đau '2 điểm' như điểm ở trường",
      P(29, "Female", allergies=("Ibuprofen",)),
      "Em có bầu 31 tuần, chừng 20 phút trước bưng nồi nước luộc gà bị trượt tay, nước sôi đổ trúng đùi trái, da đỏ phồng "
      "rộp một mảng lớn cỡ quyển vở. Đau lắm, nếu chấm điểm như ở trường thì chỉ được 2 điểm thôi.",
      {"pregnancy_present": "YES", "pregnancy_status": "PREGNANT", "gestational_age_weeks": 31,
       "burn_present": "YES", "burn_mechanism": "HOT_LIQUID", "burn_location": "LOWER_LIMB",
       "burn_extent_estimate": "LARGE_LOCALIZED_AREA", "burn_skin_appearance": "BLISTERED",
       "pain_present": "YES", "pain_severity": 9, "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("scald_exposure", "burn_injury", "pregnancy"), screen=QUIET,
      answers={"burn_mechanism": "Nước sôi trong nồi luộc gà đổ vào.",
               "symptom_duration_bucket": "Mới chừng 20 phút.",
               "burn_location": "Ở đùi trái.",
               "burn_extent_estimate": "Một mảng lớn cỡ quyển vở ở mặt trước đùi, chưa tới hết đùi.",
               "pain_severity": "À, em tưởng chấm như điểm ở trường, 10 là tốt nhất. Nếu 0 là không đau, 10 là đau nhất thì "
                                "em đau 9.",
               "gestational_age_weeks": "Thai được 31 tuần."},
      confirmation="Em nói lại cho rõ: lúc nãy em chấm ngược như điểm ở trường; tính theo 0 là không đau, 10 là đau nhất thì "
                   "em đau 9.",
      conflict=("Lời kể: 'chấm 2 điểm' theo kiểu điểm ở trường (10 là tốt)", "Làm rõ trên thang 0-10: đau 9"),
      tags=("contradiction", "vitals_inconsistent", "scale_misunderstanding", "pregnancy", "changed_answer"),
      test="Thang điểm đau bị hiểu ngược: giữ số 2 thì bỏng mảng lớn là INCOMPLETE, đau 9 trên thang chuẩn thì là ESI 2."),
    S("k32", "postpartum_herbal_steam_perineal_burn", "Sản phụ xông hơi lá bị bỏng, ngại nên nói 'đùi trong'",
      P(26, "Female", meds=("Viên sắt bổ sung mỗi ngày",)),
      "Em mới sinh được 9 ngày, mẹ chồng bảo xông hơi lá cho mau lành nên em ngồi trên nồi nước lá đang sôi, bị bỏng ở đùi "
      "trong. Rát lắm, đi lại khó.",
      {"pregnancy_status": "POSTPARTUM", "burn_present": "YES", "burn_mechanism": "STEAM",
       "burn_location": "GENITAL_OR_PERINEAL", "burn_skin_appearance": "PALE_OR_WHITE",
       "burn_sensation": "PAINFUL_OR_BURNING", "pain_present": "YES", "pain_severity": 6},
      2, concepts=("steam_exposure", "perineal_pain", "postpartum_state"), screen=QUIET,
      answers={"pregnancy_status": "Em mới sinh được 9 ngày.",
               "burn_mechanism": "Hơi nước lá đang sôi bốc lên.",
               "burn_location": "Em ngại nên nói đùi trong, thật ra bỏng ở vùng kín chứ không phải đùi, chỗ tầng sinh môn.",
               "burn_skin_appearance": "Em soi gương thấy chỗ đó trắng nhợt.",
               "pain_severity": "Chắc 6."},
      confirmation="Em xin nói thật: lúc nãy em ngại nên nói đùi trong, chứ bỏng ở vùng kín, chỗ tầng sinh môn, không phải ở "
                   "đùi; da chỗ đó trắng nhợt.",
      conflict=("Lời kể: bỏng đùi trong", "Thừa nhận: bỏng vùng tầng sinh môn, không phải đùi, da trắng nhợt"),
      tags=("contradiction", "minimization", "changed_answer", "postpartum", "cultural_practice", "progressive_disclosure"),
      test="Vị trí bỏng bị nói tránh vì ngại và chỉ được thừa nhận muộn: bản đầu (đùi trong, trắng nhợt) là INCOMPLETE, bản "
           "thừa nhận (tầng sinh môn) là ESI 2."),
    S("k33", "bedbound_heating_pad_perineal_burn", "Con gái tưởng hăm tã, điều dưỡng tại nhà nhận ra bỏng sẫm màu do túi chườm",
      P(83, "Male", "PARENT", chronic=("Di chứng đột quỵ, nằm một chỗ", "Sa sút trí tuệ"), meds=("Aspirin 81 mg mỗi sáng",)),
      "Bố tôi 83 tuổi nằm liệt sau tai biến, không nói được rõ. Mấy đêm trời lạnh tôi lót túi chườm điện dưới mông cho bố ấm. "
      "Sáng nay thay bỉm thấy vùng bìu với tầng sinh môn đỏ lên, tôi nghĩ chắc hăm tã thôi.",
      {"burn_present": "YES", "burn_mechanism": "HOT_OBJECT", "burn_location": "GENITAL_OR_PERINEAL",
       "burn_skin_appearance": "DARKENED"},
      2, concepts=("burn_injury", "scrotal_skin_discoloration"), screen=QUIET,
      unknown={"symptom_duration_bucket": "Sáng nay thay bỉm tôi mới thấy, còn bị từ đêm nào thì tôi không rõ."},
      answers={"burn_present": "Chị điều dưỡng chăm sóc tại nhà vừa đến xem, bảo không phải hăm mà là bỏng do túi chườm.",
               "burn_mechanism": "Túi chườm điện lót dưới mông cả đêm, nóng quá.",
               "burn_location": "Ở bìu với tầng sinh môn.",
               "burn_skin_appearance": "Chị ấy chỉ cho tôi: ở bìu với tầng sinh môn có mấy mảng sẫm nâu đen, khô cứng, không "
                                       "phải đỏ như tôi tưởng."},
      confirmation="Tôi sửa lại theo lời chị điều dưỡng: không phải hăm tã, bố tôi bị bỏng do túi chườm ở bìu và tầng sinh "
                   "môn, có mấy mảng sẫm nâu đen, khô cứng.",
      conflict=("Con gái: hăm tã đỏ", "Điều dưỡng chăm sóc tại nhà: bỏng do túi chườm, mảng sẫm nâu đen"),
      tags=("contradiction", "collateral_history", "older_adult", "caregiver", "baseline_cognitive_impairment", "comorbidity"),
      test="Người chăm sóc tưởng hăm tã, người thứ hai nhận ra bỏng: bản đầu (hăm đỏ, không bỏng) là INCOMPLETE, bản đính "
           "chính (bỏng sẫm màu vùng sinh dục) là ESI 2."),
    S("k34", "hotpot_canister_burn_time_corrected", "Chồng nói vợ vừa bị bỏng, vợ thú nhận bị từ tối qua",
      P(38, "Female", "SPOUSE"),
      "Vợ tôi bị bình gas mini của bếp lẩu phát nổ, lửa táp vào hai cẳng tay và hai bắp chân, có mấy mảng cháy sém đen, cô "
      "ấy kêu đau 7. Chuyện mới xảy ra chừng nửa tiếng trước thôi.",
      {"burn_present": "YES", "burn_mechanism": "FLAME", "burn_location": "MULTIPLE_AREAS",
       "burn_extent_estimate": "MULTIPLE_BODY_REGIONS", "burn_skin_appearance": "DARKENED",
       "symptom_duration_bucket": "ONE_TO_24_HOURS", "pain_present": "YES", "pain_severity": 7},
      2, concepts=("burn_injury",), screen=QUIET,
      answers={"burn_mechanism": "Bình gas mini của bếp lẩu nổ, lửa táp vào.",
               "burn_location": "Hai cẳng tay với hai bắp chân.",
               "burn_extent_estimate": "Hai cẳng tay với hai bắp chân, chỗ nào cũng có mảng bỏng.",
               "symptom_duration_bucket": "Vợ tôi vừa nói thật: không phải nửa tiếng đâu, bình nổ từ khoảng 9 giờ tối qua ở "
                                          "quán, cô ấy giấu tôi, tới giờ hơn 12 tiếng rồi.",
               "pain_severity": "Cô ấy bảo đau 7."},
      clarification="Tôi kể lại cho đúng: vợ tôi bị bình gas mini nổ từ khoảng 9 giờ tối qua chứ không phải nửa tiếng trước; "
                    "lửa táp vào hai cẳng tay và hai bắp chân, có mấy mảng cháy sém đen.",
      confirmation="Còn một chỗ phải sửa: vợ tôi bị từ khoảng 9 giờ tối qua, hơn 12 tiếng rồi, không phải vừa mới bị.",
      conflict=("Chồng kể: mới bị chừng nửa tiếng", "Vợ thú nhận: bị từ 9 giờ tối qua, hơn 12 tiếng"),
      tags=("contradiction", "collateral_history", "caregiver", "changed_answer", "time_corrected"),
      test="Thời gian bị được đính chính qua ranh giới dưới 1 giờ / 1-24 giờ; nhãn không đổi (ESI 2 ở cả hai bản) nhưng "
           "trạng thái phải cập nhật thời gian."),
    S("k35", "trench_collapse_breaths_counted_15s", "Sạt hố móng vùi tới ngực: đếm thở '11 lần' hoá ra là trong 15 giây",
      P(42, "Male", "OTHER"),
      "Anh thợ cùng tổ tôi 42 tuổi đang đào hố móng thì vách đất sạt, vùi tới ngực chừng 15 phút mới moi ra được. Giờ anh ấy "
      "tỉnh nhưng thở gấp, nói vài chữ lại phải ngừng lấy hơi. Tôi đếm nhịp thở được 11 lần... à không, tôi chỉ đếm trong "
      "15 giây, tính ra cả phút là khoảng 44 lần.",
      {"trauma_present": "YES", "trauma_mechanism": "CRUSH_INJURY", "injury_region": "MULTIPLE_REGIONS", "dyspnea_present": "YES",
       "cardiorespiratory_symptom_present": "YES", "exertional_relation": "OCCURS_AT_REST",
       "respiratory_distress_symptoms": "SEVERE_OR_UNABLE_TO_SPEAK_NORMALLY", "respiratory_rate": 44,
       "altered_mental_status_present": "NO"},
      1, concepts=("crush_injury", "shortness_of_breath"), screen=HIT,
      answers={"trauma_mechanism": "Bị đất sạt vùi tới ngực, đè ép khoảng 15 phút.",
               "cardiorespiratory_symptom_present": "Có, anh ấy khó thở từ lúc được moi ra.",
               "exertional_relation": "Anh ấy đang nằm nghỉ mà vẫn thở gấp, không phải do gắng sức.",
               "respiratory_distress_symptoms": "Nói vài chữ là phải ngừng lấy hơi, không nói hết câu được.",
               "respiratory_rate": "Khoảng 44 lần một phút; tôi đếm 15 giây được 11 lần rồi nhân bốn.",
               "injury_region": "Đất ép từ hai chân lên tới ngực.",
               "altered_mental_status_present": "Không, anh ấy vẫn tỉnh, trả lời đúng."},
      unknown={"limb_neurologic_symptoms": "Tôi chưa hỏi anh ấy chân tay có tê hay yếu không."},
      conflict=("Câu đầu: đếm được 11 lần (không ghi khoảng thời gian)", "Tự đính chính: 11 lần trong 15 giây, tức khoảng 44 lần/phút"),
      tags=("contradiction", "vitals_inconsistent", "units", "occupational", "collateral_history"),
      test="Số đếm nhịp thở trong 15 giây bị kể như số mỗi phút: giữ 11 thì chỉ còn tiêu chí khó thở khi nghỉ (ESI 2), 44 "
           "lần/phút là ESI 1."),
    S("k36", "thresher_hand_bleeding_minimized", "Chồng bảo máu cầm rồi, vợ thấy khăn ướt sũng liên tục, HA 84/52",
      P(57, "Male", "SPOUSE"),
      "Chồng tôi bị máy tuốt lúa cuốn bàn tay phải, dập nát mấy ngón. Ông ấy cứ bảo máu cầm rồi ko sao, nhưng tôi quấn khăn "
      "mà khăn ướt sũng liên tục, thay 3 cái rồi vẫn chảy. Máy đo HA ở nhà đo dc 84/52, mạch 126, người tái nhợt, vã mồ hôi.",
      {"trauma_present": "YES", "trauma_mechanism": "CRUSH_INJURY",
       "upper_extremity_problem_present": "YES", "upper_extremity_injury_location": "HAND",
       "upper_extremity_injury_mechanism": "CRUSH", "wound_present": "YES", "wound_location": "HAND_FINGER",
       "wound_type": "CRUSH", "bleeding_present": "YES",
       "bleeding_control_status": "HEAVY_CONTINUOUS", "systolic_bp": 84, "diastolic_bp": 52, "heart_rate": 126},
      1, concepts=("upper_extremity_crush_injury", "uncontrolled_extremity_bleeding", "hypotension"), screen=HIT,
      answers={"trauma_mechanism": "Bị máy tuốt lúa cuốn bàn tay vào, dập nát.",
               "wound_location": "Ở bàn tay phải, mấy ngón dập nát.",
               "wound_type": "Bị máy cuốn dập nát.",
               "upper_extremity_injury_mechanism": "Bị máy tuốt lúa cuốn vào, dập nát.",
               "bleeding_control_status": "Không cầm được, khăn quấn cứ ướt sũng, thay ba cái rồi vẫn chảy."},
      conflict=("Người bệnh: máu cầm rồi, không sao", "Vợ quan sát: khăn ướt sũng liên tục, thay ba cái vẫn chảy"),
      tags=("contradiction", "collateral_history", "minimization", "caregiver", "occupational", "abbreviation"),
      test="Lời phủ định của người bệnh và quan sát của vợ cùng nằm trong lời kể: giữ 'máu cầm rồi' là ESI 2, chảy máu không "
           "cầm kèm huyết áp 84 là ESI 1 (khác r09 đợt 1: dập do máy, lời người bệnh và người nhà trái nhau)."),
    S("k37", "child_scald_infected_remeasured_fever", "Bé bỏng canh nóng 4 hôm, sáng cặp 37,6, cặp lại 38,7",
      P(9, "Female", "CHILD", allergies=("Amoxicillin",)),
      "Con gái tôi 9 tuổi bị nước canh nóng đổ vào đùi phải từ 4 hôm trước, ở nhà bôi lòng trắng trứng. Hôm nay chỗ bỏng đỏ, "
      "rỉ dịch đục, bé kêu đau khoảng 6. Sáng nay cặp nhiệt độ được 37,6 nên tôi nghĩ không sốt.",
      {"burn_present": "YES", "burn_mechanism": "HOT_LIQUID", "burn_location": "LOWER_LIMB",
       "burn_skin_appearance": "RED", "pain_present": "YES", "pain_severity": 6, "fever_present": "YES",
       "temperature": 38.7, "infection_source_symptom_group": "SKIN_SOFT_TISSUE", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, concepts=("recent_burn", "wound_infection", "fever"), screen=QUIET,
      answers={"burn_mechanism": "Nước canh nóng đổ vào.",
               "burn_location": "Ở đùi phải.",
               "burn_skin_appearance": "Chỗ bỏng đỏ, trên mặt vết rỉ dịch đục.",
               "infection_source_symptom_group": "Ngoài sốt thì chỉ thấy chỗ bỏng ở đùi đỏ, rỉ dịch đục.",
               "fever_present": "Sáng tôi cặp có 37,6 nên tưởng không sốt; giờ sờ người bé nóng ran, cặp lại thì sốt thật.",
               "temperature": "Vừa cặp lại đủ 5 phút thì 38,7 độ; lúc sáng chắc tôi cặp chưa đủ lâu.",
               "symptom_duration_bucket": "Bé bị bỏng 4 hôm rồi."},
      confirmation="Tôi vừa cặp nhiệt độ lại cho bé, đủ 5 phút thì được 38,7 độ, vậy là bé có sốt chứ không phải 37,6.",
      conflict=("Lời kể: sáng cặp 37,6, nghĩ là không sốt", "Đo lại: 38,7 độ"),
      tags=("contradiction", "changed_answer", "pediatric", "caregiver"),
      test="Lần đo nhiệt độ mới thay lần đo cũ: giữ 37,6 thì vết bỏng nhiễm trùng đau 6 là INCOMPLETE, sốt 38,7 kèm đau 6 "
           "là ESI 3."),
    S("k38", "cement_burn_knee_onset_corrected", "Thợ hồ bỏng xi măng ở gối: 'sáng nay' đính chính thành 3 hôm trước",
      P(50, "Male"),
      "Tôi thợ hồ, đầu gối phải bị bỏng do quỳ trong vữa xi măng lúc đổ sàn sáng nay, da bong tróc, loét đỏ. Càng lúc càng "
      "rát, giờ đau chừng 6.",
      {"burn_present": "YES", "burn_mechanism": "CHEMICAL", "burn_location": "LOWER_LIMB",
       "burn_skin_appearance": "MIXED_APPEARANCE", "pain_present": "YES", "pain_severity": 6,
       "symptom_trend": "WORSENING", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, concepts=("chemical_burn", "knee_pain"), screen=QUIET,
      review_concern="Bỏng do vữa xi măng ướt ở một đầu gối, đau 6/10, chỉ cần chăm sóc vết thương: ở Decision Point C điều "
                     "dưỡng dự đoán một nguồn lực nên thường xếp ESI 4. Nhãn ESI 3 của corpus đến từ tiêu chí chung 'đau vừa "
                     "đang tăng', vốn được viết cho đau bụng, không dựa trên số nguồn lực thật của ca này.",
      answers={"burn_mechanism": "Vữa xi măng ướt dính vào da, ăn da.",
               "burn_skin_appearance": "Chỗ thì bong tróc, chỗ thì loét đỏ.",
               "burn_location": "Ở đầu gối phải.",
               "symptom_duration_bucket": "Vợ tôi nhắc là tôi nhớ lộn: đổ sàn là hôm thứ Bảy, tính tới nay 3 hôm rồi; sáng "
                                          "nay là lúc tôi mới để ý thấy loét.",
               "symptom_trend": "Rát tăng dần lên."},
      confirmation="Tôi sửa một chỗ: bỏng xi măng từ hôm thứ Bảy, tức 3 hôm rồi, chứ không phải sáng nay; sáng nay tôi mới để "
                   "ý thấy loét.",
      conflict=("Lời kể: bị từ sáng nay", "Đính chính: đổ sàn hôm thứ Bảy, 3 hôm trước"),
      tags=("contradiction", "changed_answer", "occupational", "time_corrected"),
      test="Thời gian bị được đính chính qua ranh giới 1-24 giờ / 1-7 ngày; nhãn không đổi (ESI 3 vì đau vừa đang tăng ở "
           "cả hai bản) nhưng trạng thái phải cập nhật thời gian (khác k20 đợt 1: bỏng xi măng, mâu thuẫn về thời gian chứ không về diễn tiến)."),
    S("k39", "pressure_cooker_steam_face_retracted", "Nói hơi nồi áp suất phụt vào mặt, đính chính ngay: chỉ cẳng tay",
      P(47, "Female", chronic=("Suy giáp",), meds=("Levothyroxin 50 mcg mỗi sáng",)),
      "Tôi mở nắp nồi áp suất khi chưa xả hết hơi, hơi nóng phụt thẳng vào mặt... à không, tôi kịp quay mặt đi, hơi phụt "
      "trúng cẳng tay trái thôi, mặt không sao, cũng không hít phải hơi nóng. Chỗ bỏng đỏ rát, chưa phồng, đau chừng 4.",
      {"burn_present": "YES", "burn_mechanism": "STEAM", "burn_location": "UPPER_LIMB",
       "burn_skin_appearance": "RED", "burn_sensation": "PAINFUL_OR_BURNING", "smoke_or_fume_exposure": "NONE",
       "pain_present": "YES", "pain_severity": 4},
      INCOMPLETE, concepts=("steam_exposure", "burn_injury"), screen=QUIET,
      answers={"burn_mechanism": "Hơi nóng trong nồi áp suất phụt ra.",
               "burn_location": "Cẳng tay trái thôi, mặt không bị.",
               "smoke_or_fume_exposure": "Không, tôi không hít phải hơi nóng."},
      conflict=("Câu đầu: hơi nóng phụt vào mặt", "Tự đính chính ngay: kịp quay đi, chỉ bỏng cẳng tay trái, không hít hơi nóng"),
      tags=("contradiction", "negation"),
      test="Vị trí được đính chính ngay trong lời kể: giữ 'mặt' sẽ thành ESI 2 sai; bản đúng (cẳng tay đỏ rát, không hít hơi "
           "nóng) không khớp tiêu chí nào nên là INCOMPLETE."),
    S("k40", "exhaust_burn_cream_and_ice_retraction", "Bỏng pô bắp chân: 'trắng bệch, không cảm giác' hoá ra do kem bôi và chườm đá",
      P(17, "Female"),
      "Em ngồi sau xe máy, bắp chân phải áp trúng ống pô nóng. Chỗ bỏng trắng bệch, chạm vào không thấy gì. À khoan, em nói "
      "lại: màu trắng là lớp kem trị bỏng chị bán thuốc bôi dày lên, em chưa lau ra nên không biết da bên dưới thế nào; còn "
      "không thấy gì là do em chườm đá nãy giờ, chân tê cóng hết rồi.",
      {"burn_present": "YES", "burn_mechanism": "HOT_OBJECT", "burn_location": "LOWER_LIMB"},
      INCOMPLETE, concepts=("burn_injury",), screen=QUIET,
      answers={"burn_mechanism": "Bắp chân áp trúng ống pô xe máy đang nóng.",
               "burn_location": "Ở bắp chân phải."},
      clarification="Em nói lại: màu trắng là lớp kem trị bỏng chị bán thuốc bôi lên, em chưa lau ra nên chưa biết da bên dưới "
                    "thế nào; chân em đang tê vì chườm đá nên cũng chưa biết chỗ bỏng có đau hay mất cảm giác không.",
      unknown={"burn_skin_appearance": "Lớp kem còn phủ kín chỗ đó, em chưa lau ra nên không biết da bên dưới ra sao.",
               "burn_sensation": "Chân đang tê cóng vì chườm đá nên em không biết chỗ bỏng có cảm giác không.",
               "burn_extent_estimate": "Kem bôi rộng hơn vết bỏng nên em không đoán được vết bỏng to cỡ nào."},
      conflict=("Câu đầu: chỗ bỏng trắng bệch, chạm không thấy gì",
                "Tự đính chính: màu trắng là kem bôi, tê là do chườm đá; chưa biết màu da và cảm giác thật"),
      tags=("contradiction", "null_unknown", "adolescent"),
      test="Dữ kiện quyết định bị rút lại thành 'không biết': giữ 'trắng bệch, mất cảm giác' là ESI 2 sai; sau đính chính, màu "
           "da và cảm giác chưa biết nên là INCOMPLETE, không được coi là bình thường (khác m31 đợt 1: bỏng pô ở bàn tay, mô tả rõ)."),
]

