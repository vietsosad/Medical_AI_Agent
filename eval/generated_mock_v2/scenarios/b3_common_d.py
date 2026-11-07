"""Nhóm COMMON, đợt 3 (phần d, lượt 2): than phiền nhẹ hằng ngày và độ bền với cách người Việt thật sự gõ.

Trọng tâm phần này là phủ định và cách viết chứ không phải tiêu chí mới: phủ định miền Nam và miền Trung ("hổng",
"hông", "hổng có", "đâu có", "chả", "chẳng", "không hề", "không ... mô", "không ... chi hết"), viết tắt kiểu học sinh
("k", "ko", "khum", "j", "bt"), gõ không dấu, lời đọc bằng giọng nói không dấu câu và có từ bị nhận nhầm, lời mở đầu rất
ngắn hoặc rất dài, và tiền sử đã qua được kể cạnh than phiền hiện tại ("hồi năm ngoái bị ..."). Mười bốn ca là than phiền
thường ngày mà corpus không có tiêu chí (kỳ vọng RETURN_INCOMPLETE: agent chuyển nhân viên y tế, không tự gán ESI 4-5),
sáu ca ESI 3 và hai ca ESI 2 có mức do một dữ kiện hay một sinh hiệu được kể rõ quyết định, ba ca ESI 4-5 dựa vào số
nguồn lực do người viết lập luận (vào hàng chờ duyệt).

Quy ước riêng của tệp:
- Kỳ vọng của bộ lọc khẩn cấp đặt theo nghĩa lâm sàng: chữ bị phủ định ("hổng có xỉu", "hổng có ói ra máu") hoặc sự việc
  đã qua ("năm ngoái từng xỉu") là không có, nên kỳ vọng QUIET; hai ca chỉ nguy hiểm vì con số sinh hiệu (c196, c197)
  để trống. Lời mở đầu không được viết lại cho khớp bộ lọc.
- Lời đọc bằng giọng nói (c176, c181) giữ nguyên lỗi nhận nhầm từ trong lời mở đầu; câu trả lời khi được hỏi viết đúng
  chính tả nhưng giữ giọng địa phương của người kể.
- Khi người kể không chấm được điểm đau (c183 kể hộ, c190 "ko bik chấm", c191 trẻ 3 tuổi), ``pain_severity`` nằm ở dạng
  không biết; không bịa điểm đau.
- c193: "hông có đau hông lưng" dùng chữ "hông" hai nghĩa (phủ định và bộ phận cơ thể); câu chỉ có một cách hiểu theo
  giọng miền Nam và ca đo đúng việc agent hiểu là không đau hông lưng.
"""

from __future__ import annotations

from eval.generated_mock_v2.spec import COMMON, INCOMPLETE, P, SCREEN_QUIET as QUIET, Spec


def S(key: str, family: str, title: str, profile: dict, opening: str, facts: dict, intended, **kw) -> Spec:
    return Spec(case_id=key, family=family, group=COMMON, title=title, profile=profile,
                opening=opening, facts=facts, intended=intended, **kw)


SPECS = [
    # ------------------------------------------------------------------ INCOMPLETE: than phiền thường ngày, phủ định
    #                                                                     và cách gõ khác nhau, corpus không có tiêu chí
    S("c176", "elder_nocturia_weak_stream_voice_typed_southern", "Cụ ông tiểu đêm, tia yếu, đọc bằng giọng nói miền Nam",
      P(68, "Male", chronic=("Tăng huyết áp", "Sỏi thận đã tán năm ngoái"), meds=("Amlodipin",)),
      "Tui năm nay 68 tuổi mấy tháng nay đêm nào cũng phải thức dậy đi tiểu ba bốn lần tia nước tiểu yếu phải dặn một "
      "hồi mới ra đi xong còn nhỏ giọt hổng có tiểu buốt nước tiểu vẫn trong hổng thấy máu hổng sốt năm ngoái tui bị "
      "sỏi thận đã tán rồi giờ lưng hổng đau gì hết dậy có cần đi khám gấp hông",
      {"urinary_symptom_present": "YES", "voiding_ability": "REDUCED", "urine_appearance": "NORMAL",
       "genitourinary_pain_present": "NO", "back_or_spinal_problem_present": "NO", "pain_present": "NO",
       "fever_present": "NO", "symptom_duration_bucket": "OVER_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("nocturia", "weak_urine_stream", "urinary_hesitancy"),
      tags=("older_adult", "comorbidity", "dialect", "negation", "voice_to_text", "typo", "remote_history", "corpus_gap"),
      answers={"urinary_symptom_present": "Có, đêm nào tui cũng phải dậy đi tiểu ba bốn lần.",
               "voiding_ability": "Tia nước tiểu yếu, phải rặn một hồi mới ra, đi xong còn nhỏ giọt.",
               "urine_appearance": "Nước tiểu vẫn trong, hổng thấy máu.",
               "genitourinary_pain_present": "Hổng đau chỗ nào hết, đi tiểu cũng hổng buốt.",
               "back_or_spinal_problem_present": "Hổng, lưng tui giờ hổng đau gì hết.",
               "pain_present": "Hổng đau chỗ nào hết.",
               "fever_present": "Hổng sốt.",
               "symptom_duration_bucket": "Mấy tháng nay rồi."},
      test="Lời đọc bằng giọng nói miền Nam, không dấu câu, có từ bị nhận nhầm ('dặn' thay 'rặn', 'dậy' thay 'vậy'): cụ "
           "ông tiểu đêm, tia yếu, 'hổng' phủ nhận tiểu buốt, tiểu máu, sốt, còn sỏi thận là chuyện năm ngoái đã tán; agent "
           "không được đọc 'hổng' thành có, không coi tiền sử sỏi là cơn đau hiện tại, và phải chuyển nhân viên y tế vì "
           "corpus không có tiêu chí."),
    S("c177", "teen_dusty_storeroom_sneezing_teencode", "Thiếu nữ hắt hơi, nghẹt mũi sau dọn kho sách bụi, viết tắt",
      P(15, "Female", chronic=("Viêm mũi dị ứng",)),
      "Từ trưa dọn kho sách cũ xong tới giờ e hắt xì liên tục, nghẹt mũi, nc mũi trong chảy ròng ròng. K sốt k đau họng.",
      {"runny_nose_present": "YES", "nasal_discharge_character": "CLEAR_WATERY", "nasal_congestion_present": "YES",
       "fever_present": "NO", "sore_throat_present": "NO", "suspected_trigger_exposure_present": "YES",
       "suspected_allergy_trigger": "ENVIRONMENTAL_ALLERGEN", "exposure_to_symptom_interval": "WITHIN_MINUTES",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, screen=QUIET, concepts=("sneezing", "nasal_congestion", "runny_nose"),
      tags=("adolescent", "abbreviation", "negation", "short_opening", "comorbidity", "corpus_gap"),
      answers={"runny_nose_present": "Có, nc mũi chảy ròng ròng luôn.",
               "nasal_discharge_character": "Nc mũi trong, chảy ròng ròng.",
               "nasal_congestion_present": "Có, nghẹt mũi.",
               "fever_present": "K sốt.",
               "sore_throat_present": "K đau họng.",
               "suspected_trigger_exposure_present": "Có, e dọn kho sách cũ nhiều bụi.",
               "suspected_allergy_trigger": "Chắc do bụi kho sách cũ.",
               "exposure_to_symptom_interval": "Dọn xong vài phút là bắt đầu hắt xì.",
               "symptom_duration_bucket": "Từ trưa tới giờ, mấy tiếng r."},
      confirmation="Dạ đúng r.",
      test="Lời mở đầu rất ngắn, viết tắt kiểu học sinh ('e', 'nc', 'k'): hắt hơi, nghẹt mũi sau khi dọn kho sách bụi ở "
           "thiếu nữ có viêm mũi dị ứng; agent phải đọc 'k sốt k đau họng' là phủ định, không tự kê thuốc chống dị ứng, và "
           "chuyển nhân viên y tế vì corpus không có tiêu chí."),
    S("c178", "year_end_bookkeeper_band_headache_central", "Kế toán cuối năm nhức hai bên thái dương, giọng miền Trung",
      P(44, "Male"),
      "Răng mấy bữa ni tui nhức đầu hoài, nhức âm ỉ hai bên thái dương như có cái vòng siết lại, chừng 4 điểm. Cuối năm "
      "làm sổ sách, ngồi máy tính tới khuya. Tui không hề ói, mắt không mờ, tay chân không tê yếu chi hết, nói năng bình "
      "thường. Nghỉ ngơi uống nước ấm thì đỡ được chút.",
      {"headache_present": "YES", "headache_location": "TEMPORAL", "headache_character": "TIGHTNESS",
       "pain_present": "YES", "pain_severity": 4, "symptom_onset": "GRADUAL", "vomiting_present": "NO",
       "vision_impairment_present": "NO", "focal_neurologic_symptoms": "NONE",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("headache",),
      tags=("dialect", "negation", "occupational", "corpus_gap"),
      answers={"headache_present": "Có, tui nhức đầu hoài mấy bữa ni.",
               "headache_location": "Nhức hai bên thái dương.",
               "headache_character": "Như có cái vòng siết quanh đầu.",
               "pain_present": "Có, nhức đầu âm ỉ.",
               "pain_severity": "Chừng 4 điểm.",
               "symptom_onset": "Nhức từ từ, chứ không phải tự nhiên nhức dữ dội một cái.",
               "vomiting_present": "Không hề ói.",
               "vision_impairment_present": "Mắt không mờ chi hết.",
               "focal_neurologic_symptoms": "Tay chân không tê yếu chi hết, nói năng bình thường.",
               "symptom_duration_bucket": "Mấy bữa ni rồi, chừng ba bốn bữa."},
      test="Đau đầu kiểu căng siết ở người làm sổ sách cuối năm, giọng miền Trung ('răng', 'ni', 'chi hết'), tự phủ nhận "
           "nôn, mờ mắt, tê yếu bằng 'không hề' và 'không ... chi hết'; agent không được nâng mức vì chữ 'nhức đầu', không "
           "đọc phủ định thành có dấu thần kinh, và chuyển nhân viên y tế vì corpus không có tiêu chí khi đau 4/10, khởi "
           "phát từ từ."),
    S("c179", "infant_miliaria_hot_spell_grandmother_southern", "Nhũ nhi 5 tháng nổi rôm sảy mùa nóng, bà nội kể",
      P(0, "Male", "OTHER", months=5),
      "Thằng cu nội tui được 5 tháng. Trời oi quá nên ba bữa nay nó nổi rôm sảy đỏ rần ở cổ, sau lưng với hai nách, hạt "
      "nhỏ hơi gồ, sờ rám ráp, chỗ nào mát mẻ thì lặn bớt. Nó hổng sốt, bú vẫn ngon, ngủ được, chơi giỡn bình thường, chỉ "
      "hơi quấy lúc trưa nóng. Tui có tắm nước lá cho nó rồi, vậy có cần đem đi khám hông?",
      {"rash_or_skin_finding_present": "YES", "skin_finding_appearance": "SMALL_SPOTS",
       "skin_finding_distribution": "MULTIPLE_AREAS", "rash_character": "GENERAL_RASH", "fever_present": "NO",
       "feeding_intake_level": "NORMAL", "activity_level": "NORMAL", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("skin_rash",),
      tags=("pediatric", "caregiver", "dialect", "negation", "environmental", "folk_remedy", "corpus_gap"),
      answers={"rash_or_skin_finding_present": "Có, nó nổi rôm sảy đỏ rần.",
               "skin_finding_appearance": "Hạt rôm nhỏ, hơi gồ, sờ rám ráp.",
               "skin_finding_distribution": "Ở cổ, sau lưng với hai nách.",
               "rash_character": "Rôm đỏ thường thôi, chỗ nào mát mẻ là lặn bớt.",
               "fever_present": "Hổng sốt.",
               "feeding_intake_level": "Bú vẫn ngon như mọi bữa.",
               "activity_level": "Nó vẫn chơi giỡn bình thường, chỉ hơi quấy lúc trưa nóng.",
               "symptom_duration_bucket": "Ba bữa nay rồi."},
      test="Rôm sảy ở nhũ nhi 5 tháng do trời oi, bà nội kể giọng miền Nam, 'hổng sốt', bú và chơi bình thường, đã tắm "
           "nước lá; agent không được coi hạt đỏ là ban xuất huyết khi bà đã tả rôm lặn bớt lúc mát, không tự khuyên "
           "thuốc bôi, và chuyển nhân viên y tế vì corpus không có tiêu chí."),
    S("c180", "pregnant_26w_market_seller_low_back_ache", "Thai 26 tuần mỏi thắt lưng do đứng bán hàng, phủ định 'chả', 'chẳng'",
      P(27, "Female"),
      "Em đang bầu con so được 26 tuần. Mấy hôm nay đứng bán hàng cả ngày là mỏi nhừ thắt lưng, đau âm ỉ chừng 4 điểm, "
      "tối nằm nghiêng kê gối thì đỡ. Em không ngã hay va chạm gì. Em chả ra máu, chẳng ra nước, bụng không gò từng cơn, "
      "con vẫn đạp đều, đi tiểu bình thường, không sốt. Em có cần đi khám luôn không hay chờ đến lịch hẹn?",
      {"pregnancy_present": "YES", "pregnancy_status": "PREGNANT", "gestational_age_weeks": 26,
       "back_or_spinal_problem_present": "YES", "bowel_bladder_control_change": "NONE", "pain_present": "YES",
       "pain_severity": 4, "trauma_present": "NO", "vaginal_bleeding_present": "NO",
       "vaginal_fluid_leakage_status": "NONE", "uterine_contractions_present": "NO", "fetal_movement_status": "NORMAL",
       "urinary_symptom_present": "NO", "fever_present": "NO", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("back_pain_in_pregnancy",),
      tags=("pregnancy", "negation", "occupational", "corpus_gap"),
      answers={"pregnancy_present": "Dạ có, em đang bầu 26 tuần.",
               "pregnancy_status": "Em đang mang thai con so.",
               "gestational_age_weeks": "Được 26 tuần rồi ạ.",
               "back_or_spinal_problem_present": "Có, em mỏi nhừ thắt lưng.",
               "bowel_bladder_control_change": "Không ạ, em đi tiểu bình thường.",
               "pain_present": "Có, đau âm ỉ ở thắt lưng.",
               "pain_severity": "Chừng 4 điểm ạ.",
               "trauma_present": "Không, em không ngã hay va chạm gì.",
               "vaginal_bleeding_present": "Em chả ra máu ạ.",
               "vaginal_fluid_leakage_status": "Chẳng ra nước gì ạ.",
               "uterine_contractions_present": "Bụng không gò từng cơn ạ.",
               "fetal_movement_status": "Con vẫn đạp đều ạ.",
               "urinary_symptom_present": "Không, em đi tiểu bình thường.",
               "fever_present": "Không sốt ạ.",
               "symptom_duration_bucket": "Mấy hôm nay rồi ạ."},
      test="Đau mỏi thắt lưng do đứng bán hàng ở thai 26 tuần, tự phủ nhận ra máu, ra nước, gò, sốt bằng 'chả', 'chẳng', "
           "'không'; agent phải đọc đúng các phủ định, không tự kết luận là đau lưng sinh lý của thai kỳ, và chuyển nhân "
           "viên y tế vì corpus không có tiêu chí (khác c148: phù mắt cá ở thai 34 tuần)."),
    S("c181", "elder_winter_itch_dry_scaly_skin_voice_typed", "Cụ bà ngứa da khô bong vảy mùa hanh, con gái đọc bằng giọng nói",
      P(74, "Female", "PARENT", chronic=("Đái tháo đường type 2",), meds=("Metformin",)),
      "Mẹ em năm nay 74 tuổi bị tiểu đường mấy tuần nay trời hành khô mẹ ngứa khắp người nhất là hai cẳng chân với lưng "
      "da khô bông vảy trắng như phấn đêm gãi nhiều mất ngủ mẹ bảo đâu có nổi mẩn gì đâu cũng đâu có sốt ăn uống vẫn bình "
      "thường em muốn hỏi có cần đưa mẹ đi khám da liễu không ạ",
      {"itching_present": "YES", "rash_or_skin_finding_present": "YES", "skin_finding_appearance": "CRUSTING_OR_SCALING",
       "skin_finding_distribution": "MULTIPLE_AREAS", "fever_present": "NO", "oral_intake_tolerance": "NORMAL",
       "symptom_duration_bucket": "OVER_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("pruritus", "skin_dryness", "skin_scaling"),
      tags=("older_adult", "caregiver", "comorbidity", "voice_to_text", "typo", "negation", "corpus_gap"),
      answers={"itching_present": "Có ạ, mẹ em ngứa khắp người, nhất là hai cẳng chân với lưng.",
               "rash_or_skin_finding_present": "Mẩn thì đâu có, chỉ là da khô bong vảy trắng như phấn thôi ạ.",
               "skin_finding_appearance": "Da khô, bong vảy trắng như phấn.",
               "skin_finding_distribution": "Ở hai cẳng chân với lưng ạ.",
               "fever_present": "Đâu có sốt ạ.",
               "oral_intake_tolerance": "Mẹ em ăn uống vẫn bình thường.",
               "symptom_duration_bucket": "Mấy tuần nay rồi ạ."},
      test="Lời đọc bằng giọng nói không dấu câu, có từ bị nhận nhầm ('hành khô', 'bông vảy'): con gái kể mẹ 74 tuổi "
           "ngứa, da khô bong vảy mùa hanh; 'đâu có nổi mẩn', 'đâu có sốt' là phủ định kiểu nói miệng, agent không được ghi "
           "là không có tổn thương da khi da đang bong vảy, và chuyển nhân viên y tế vì corpus không có tiêu chí."),
    S("c182", "child_post_cold_lingering_cough_no_diacritics", "Trẻ 7 tuổi ho khan kéo dài sau cảm, bố gõ không dấu",
      P(7, "Male", "CHILD", allergies=("Amoxicillin",)),
      "Con trai toi 7 tuoi, bi cam tu hon 10 ngay truoc, gio het so mui roi nhung van con ho khan, ho nhieu ve dem va "
      "sang som. Chau khong sot, khong kho tho, tho khong nghe kho khe gi, van di hoc, an choi binh thuong. Nha co mua siro "
      "ho cho chau uong ma chua thay bot. Chau di ung amoxicillin.",
      {"cough_present": "YES", "cough_character": "DRY", "runny_nose_present": "NO", "fever_present": "NO",
       "dyspnea_present": "NO", "noisy_breathing_present": "NO", "activity_level": "NORMAL",
       "oral_intake_tolerance": "NORMAL", "symptom_trend": "CONSTANT", "symptom_duration_bucket": "OVER_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("cough",),
      tags=("pediatric", "caregiver", "no_diacritics", "negation", "corpus_gap"),
      answers={"cough_present": "Co, chau van con ho khan.",
               "cough_character": "Ho khan, khong co dom.",
               "runny_nose_present": "Het so mui roi, gio chi con ho.",
               "fever_present": "Khong sot.",
               "dyspnea_present": "Khong kho tho.",
               "noisy_breathing_present": "Tho khong nghe kho khe gi.",
               "activity_level": "Chau van di hoc, choi binh thuong.",
               "oral_intake_tolerance": "Chau an uong binh thuong.",
               "symptom_trend": "Uong siro ma chua thay bot, van ho nhu vay.",
               "symptom_duration_bucket": "Hon 10 ngay roi."},
      clarification="Noi lai cho ro: chau 7 tuoi, cam tu hon 10 ngay truoc, gio het so mui nhung con ho khan, nhat la dem "
                    "va sang som, khong sot, khong kho tho, khong kho khe.",
      confirmation="Dung roi, nhu vay.",
      test="Ho khan kéo dài sau cảm ở trẻ 7 tuổi dị ứng amoxicillin, bố viết không dấu 'khong sot, khong kho tho', không "
           "khò khè; agent phải đọc đúng phủ định không dấu, không suy ra hen hay viêm phổi, không tự gợi ý kháng sinh, và "
           "chuyển nhân viên y tế vì corpus không có tiêu chí."),
    S("c183", "diuretic_night_calf_cramps_wife_southern", "Cụ ông dùng thuốc lợi tiểu bị vọp bẻ bắp chân về đêm, vợ kể",
      P(66, "Male", "SPOUSE", chronic=("Tăng huyết áp",), meds=("Amlodipin", "Hydroclorothiazid")),
      "Ông xã tui 66 tuổi, uống thuốc huyết áp có cả viên lợi tiểu. Năm bữa nay đêm nào ổng cũng bị vọp bẻ bắp chân trái, "
      "co rút cứng ngắc chừng vài phút, la đau oai oái, xoa dầu kéo duỗi chân ra thì hết. Ban ngày ổng đi đứng bình "
      "thường, bắp chân hổng sưng, hổng đỏ, sờ hổng thấy nóng, bàn chân hổng tê.",
      {"lower_extremity_problem_present": "YES", "lower_extremity_injury_location": "LOWER_LEG",
       "weight_bearing_ability": "NORMAL", "swelling_present": "NO", "distal_limb_symptoms": "NONE",
       "pain_present": "YES", "symptom_trend": "INTERMITTENT", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("muscle_cramps",),
      tags=("older_adult", "caregiver", "comorbidity", "dialect", "negation", "corpus_gap"),
      answers={"lower_extremity_problem_present": "Có, đêm nào ổng cũng bị vọp bẻ bắp chân trái.",
               "lower_extremity_injury_location": "Ở bắp chân trái.",
               "weight_bearing_ability": "Ban ngày ổng đi đứng bình thường.",
               "swelling_present": "Bắp chân hổng sưng.",
               "distal_limb_symptoms": "Bàn chân hổng tê gì hết.",
               "pain_present": "Lúc vọp bẻ thì ổng la đau, hết cơn thì hết đau.",
               "symptom_trend": "Lúc bị lúc hết, toàn bị ban đêm, mỗi lần vài phút.",
               "symptom_duration_bucket": "Năm bữa nay rồi."},
      unknown={"pain_severity": "Lúc vọp bẻ ổng la đau oai oái, chứ chấm mấy điểm thì tui hổng biết."},
      test="Chuột rút bắp chân về đêm ở cụ ông dùng thuốc lợi tiểu, vợ kể giọng miền Nam ('vọp bẻ', 'hổng sưng, hổng đỏ, "
           "hổng tê'); agent không được đọc các chữ 'hổng' thành có sưng đỏ hay tê, không tự khuyên ngừng thuốc lợi tiểu, "
           "không bịa điểm đau, và chuyển nhân viên y tế vì corpus không có tiêu chí."),
    S("c184", "layoff_worry_insomnia_denies_self_harm", "Mất ngủ gần một tháng vì lo mất việc, tự nói không hề có ý nghĩ dại dột",
      P(35, "Male"),
      "Gần một tháng nay tôi mất ngủ, đêm nào cũng trằn trọc đến hai ba giờ sáng mới thiếp đi được, sáng dậy uể oải, làm "
      "việc hay mất tập trung. Công ty đang cắt giảm người nên tôi lo nhiều. Tôi nói trước là tôi không hề có ý nghĩ dại "
      "dột, cũng đâu có muốn tự tử gì đâu, chỉ muốn ngủ được một giấc cho ra hồn. Có loại thuốc ngủ nào mua ở hiệu thuốc "
      "được không?",
      {"self_safety_status": "NO_RISK_REPORTED", "associated_systemic_symptoms": "GENERAL_WEAKNESS",
       "symptom_duration_bucket": "OVER_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("insomnia", "acute_psychosocial_stress"),
      tags=("mental_health", "negation", "requests_prescription", "occupational", "corpus_gap"),
      answers={"self_safety_status": "Không, tôi không hề có ý nghĩ làm hại bản thân, đâu có muốn tự tử, chỉ là mất ngủ thôi.",
               "associated_systemic_symptoms": "Sáng dậy người uể oải vì thiếu ngủ thôi.",
               "symptom_duration_bucket": "Gần một tháng nay rồi."},
      test="Mất ngủ gần một tháng vì lo bị cắt giảm, người bệnh chủ động nói 'không hề có ý nghĩ dại dột, cũng đâu có muốn "
           "tự tử gì đâu' (đối chứng âm của F1, phủ định 'đâu có' đứng trước chữ 'tự tử'): agent không được đọc câu phủ nhận "
           "thành có ý nghĩ tự hại, vẫn có thể hỏi lại an toàn một cách tôn trọng, không gợi ý thuốc ngủ, và chuyển nhân "
           "viên y tế vì corpus không có tiêu chí."),
    S("c185", "elder_cold_after_last_year_pneumonia_normal_readings", "Cụ ông từng viêm phổi năm ngoái nay cảm nhẹ, đo nhiệt độ và SpO2 bình thường",
      P(72, "Male", "PARENT", chronic=("Tăng huyết áp", "Đái tháo đường type 2"), meds=("Losartan", "Metformin")),
      "Ba con 72 tuổi, hồi năm ngoái bị viêm phổi phải nằm viện cả tuần nên giờ ổng ho chút xíu là cả nhà lo. Từ hôm kia "
      "ba sổ mũi, ho khan lai rai. Con kẹp nhiệt độ được 37 độ 2, máy kẹp ngón tay báo 97. Ba hổng có khó thở, môi hổng "
      "có tím, hổng mệt, vẫn ăn cơm ngon, chiều còn đi bộ quanh xóm.",
      {"runny_nose_present": "YES", "cough_present": "YES", "cough_character": "DRY", "temperature": 37.2,
       "fever_present": "NO", "spo2": 97, "dyspnea_present": "NO", "cyanosis_present": "NO",
       "associated_systemic_symptoms": "NONE",
       "oral_intake_tolerance": "NORMAL", "functional_status": "NORMAL", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("cough", "runny_nose"),
      tags=("older_adult", "caregiver", "comorbidity", "dialect", "negation", "remote_history", "corpus_gap"),
      answers={"runny_nose_present": "Dạ có, ba sổ mũi từ hôm kia.",
               "cough_present": "Dạ có, ba ho khan lai rai.",
               "cough_character": "Ho khan thôi.",
               "temperature": "Con kẹp được 37 độ 2.",
               "fever_present": "Hổng sốt, kẹp có 37 độ 2.",
               "spo2": "Máy kẹp ngón tay báo 97.",
               "dyspnea_present": "Ba hổng có khó thở.",
               "cyanosis_present": "Môi ba hổng có tím.",
               "associated_systemic_symptoms": "Ba hổng sốt, hổng mệt gì hết.",
               "oral_intake_tolerance": "Ba vẫn ăn cơm ngon.",
               "functional_status": "Ba vẫn sinh hoạt bình thường, chiều còn đi bộ quanh xóm.",
               "symptom_duration_bucket": "Từ hôm kia tới giờ."},
      test="Cụ ông từng viêm phổi phải nằm viện năm ngoái, nay chỉ sổ mũi, ho khan hai hôm, nhiệt độ và SpO2 con gái đo "
           "đều bình thường, 'hổng có khó thở, môi hổng có tím, hổng mệt'; agent không được đọc 'môi hổng có tím' thành tím "
           "tái, không nâng mức vì tiền sử hay vì người nhà lo, và chuyển nhân viên y tế vì corpus không có tiêu chí (đối "
           "chứng với c197: cùng than phiền nhưng SpO2 90)."),
    S("c186", "teen_late_period_exam_stress_teencode", "Thiếu nữ 16 tuổi trễ kinh gần hai tuần mùa ôn thi, viết tắt",
      P(16, "Female"),
      "E 16t, kì kinh tháng này trễ gần 2 tuần r mà vẫn chưa thấy, mấy tháng trc cũng lúc sớm lúc muộn. E chưa quan hệ j "
      "hết. Bụng khum đau, khum ra máu j, ng vẫn bt. Đợt này e ôn thi thức khuya nhiều, có sao ko ạ?",
      {"pregnancy_present": "NO", "pregnancy_status": "NOT_PREGNANT", "abdominal_pain_present": "NO",
       "pain_present": "NO", "vaginal_bleeding_present": "NO", "symptom_duration_bucket": "OVER_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("amenorrhea",),
      tags=("adolescent", "abbreviation", "negation", "sensitive_topic", "corpus_gap"),
      answers={"pregnancy_present": "Ko ạ, e chưa quan hệ j hết.",
               "pregnancy_status": "E ko có thai, e chưa quan hệ bao giờ.",
               "abdominal_pain_present": "Bụng khum đau ạ.",
               "pain_present": "Khum đau chỗ nào hết ạ.",
               "vaginal_bleeding_present": "Khum ra máu j hết ạ.",
               "symptom_duration_bucket": "Trễ gần 2 tuần r ạ."},
      confirmation="Dạ đúng r ạ.",
      test="Thiếu nữ 16 tuổi trễ kinh gần hai tuần, viết tắt kiểu học sinh ('khum', 'j', 'bt'), nói rõ chưa quan hệ, không "
           "đau bụng, không ra máu; agent phải hiểu 'khum' là phủ định, không tự suy ra có thai hay gợi ý thuốc nội tiết, và "
           "chuyển nhân viên y tế vì corpus không có tiêu chí."),
    S("c187", "standing_teacher_morning_heel_pain_ibuprofen_allergy", "Giáo viên đứng lớp đau gót chân mỗi sáng, dị ứng ibuprofen",
      P(47, "Female", allergies=("Ibuprofen",)),
      "Tôi dạy cấp hai, đứng lớp cả ngày. Gần một tháng nay sáng ngủ dậy vừa đặt chân xuống đất là gót chân phải đau nhói, "
      "đi vài chục bước thì đỡ dần, chiều đứng lâu lại đau, chừng 4 trên 10. Tôi không hề bị ngã hay trẹo chân, gót chẳng "
      "sưng chẳng đỏ, vẫn đi lại được, chỉ hơi tập tễnh lúc mới dậy. Tôi dị ứng ibuprofen nên không dám tự mua thuốc giảm "
      "đau.",
      {"lower_extremity_problem_present": "YES", "lower_extremity_injury_location": "FOOT",
       "weight_bearing_ability": "PAINFUL_BUT_POSSIBLE", "trauma_present": "NO", "swelling_present": "NO",
       "pain_present": "YES", "pain_severity": 4, "symptom_trend": "INTERMITTENT",
       "symptom_duration_bucket": "OVER_7_DAYS"},
      INCOMPLETE, screen=QUIET, concepts=("heel_pain", "foot_pain"),
      tags=("occupational", "negation", "corpus_gap"),
      answers={"lower_extremity_problem_present": "Có, gót chân phải của tôi đau.",
               "lower_extremity_injury_location": "Ở gót chân phải.",
               "weight_bearing_ability": "Vẫn đi lại được, chỉ hơi tập tễnh lúc mới ngủ dậy.",
               "trauma_present": "Không hề bị ngã hay trẹo chân.",
               "swelling_present": "Gót chẳng sưng.",
               "pain_present": "Có, đau nhói ở gót chân.",
               "pain_severity": "Chừng 4 trên 10.",
               "symptom_trend": "Sáng mới dậy thì đau, đi một lúc đỡ, chiều đứng lâu lại đau.",
               "symptom_duration_bucket": "Gần một tháng nay rồi."},
      test="Đau gót chân buổi sáng ở giáo viên đứng lớp, 'không hề bị ngã', 'chẳng sưng chẳng đỏ', dị ứng ibuprofen; agent "
           "phải đọc đúng phủ định, không tự gợi ý thuốc giảm đau khác, và chuyển nhân viên y tế vì corpus chỉ có tiêu chí "
           "chịu lực khi biết số nguồn lực."),
    S("c188", "kindergarten_pink_eye_outbreak_boy_southern", "Bé trai mẫu giáo đỏ hai mắt có ghèn khi lớp đang có dịch",
      P(4, "Male", "CHILD"),
      "Lớp mẫu giáo của bé nhà em đang có mấy bạn bị đau mắt đỏ. Sáng nay bé dậy hai mắt đỏ, ghèn vàng dính lông mi, em "
      "phải lấy khăn ấm lau mới mở ra được, chảy nước mắt hoài. Bé hông sốt, hổng kêu đau nhức mắt, vẫn nhìn rõ, mí mắt "
      "hổng sưng, hổng bị va chạm gì vô mắt, vẫn chơi bình thường. Em có cần cho bé nghỉ học hông?",
      {"eye_problem_present": "YES", "eye_laterality": "BILATERAL", "eye_injury_present": "NO",
       "vision_impairment_present": "NO", "swelling_present": "NO", "pain_present": "NO", "fever_present": "NO",
       "activity_level": "NORMAL", "similar_symptoms_in_others": "YES", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      INCOMPLETE, screen=QUIET, concepts=("eye_redness", "eye_discharge", "sick_contact"),
      tags=("pediatric", "caregiver", "dialect", "negation", "corpus_gap"),
      answers={"eye_problem_present": "Dạ có, sáng nay bé dậy hai mắt đỏ, có ghèn vàng.",
               "eye_laterality": "Cả hai mắt.",
               "eye_injury_present": "Hổng bị va chạm gì vô mắt hết.",
               "vision_impairment_present": "Bé vẫn nhìn rõ.",
               "swelling_present": "Mí mắt hổng sưng.",
               "pain_present": "Bé hổng kêu đau nhức gì.",
               "fever_present": "Bé hông sốt.",
               "activity_level": "Bé vẫn chơi bình thường.",
               "similar_symptoms_in_others": "Dạ có, lớp bé đang có mấy bạn bị đau mắt đỏ.",
               "symptom_duration_bucket": "Mới từ sáng nay."},
      test="Đỏ hai mắt có ghèn ở bé trai mẫu giáo khi lớp đang có dịch đau mắt đỏ, mẹ kể giọng miền Nam; 'hông sốt', 'hổng "
           "kêu đau', 'mí mắt hổng sưng' là phủ định, agent không được ghi sưng mí hay giảm thị lực, không tự kê thuốc nhỏ "
           "mắt, và chuyển nhân viên y tế vì corpus không có tiêu chí."),
    S("c189", "student_skipped_breakfast_presyncope_roommate", "Sinh viên choáng khi đứng dậy nhanh, bạn cùng phòng kể 'hổng có xỉu'",
      P(19, "Male", "OTHER"),
      "Em ở chung phòng trọ với bạn, bạn ấy 19 tuổi, mấy hôm nay ôn thi thức khuya, sáng nay bỏ bữa. Lúc nãy bạn đứng dậy "
      "nhanh khỏi giường thì choáng, tối sầm mắt, phải vịn tường đứng một lát mới hết, chứ hổng có xỉu. Hồi năm ngoái bạn "
      "từng xỉu một lần lúc chào cờ ở trường. Em đo bằng máy đo huyết áp cổ tay của em được 106/68, mạch 84. Giờ bạn ngồi "
      "yên thì hổng sao, vẫn tỉnh táo, nói chuyện bình thường.",
      {"dizziness_present": "YES", "dizziness_sensation": "LIGHTHEADED", "syncope_present": "NO", "systolic_bp": 106,
       "diastolic_bp": 68, "heart_rate": 84, "altered_mental_status_present": "NO",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      INCOMPLETE, screen=QUIET, concepts=("lightheadedness", "dizziness"),
      tags=("collateral_history", "dialect", "negation", "remote_history", "corpus_gap"),
      answers={"dizziness_present": "Có, lúc nãy bạn ấy đứng dậy nhanh thì choáng.",
               "dizziness_sensation": "Bạn ấy bảo choáng váng, tối sầm mắt lúc mới đứng dậy.",
               "syncope_present": "Hổng có xỉu, vịn tường một lát là hết choáng.",
               "systolic_bp": "Máy đo cổ tay báo số trên 106.",
               "diastolic_bp": "Số dưới 68.",
               "heart_rate": "Máy báo mạch 84.",
               "altered_mental_status_present": "Không, bạn ấy vẫn tỉnh táo, nói chuyện bình thường.",
               "symptom_duration_bucket": "Mới lúc nãy thôi, chừng nửa tiếng trước."},
      test="Choáng khi đứng dậy nhanh ở sinh viên thức khuya bỏ bữa, bạn cùng phòng kể 'chứ hổng có xỉu' và nhắc lần xỉu "
           "năm ngoái; huyết áp, mạch đo bằng máy cổ tay bình thường; agent không được đọc 'hổng có xỉu' hay lần xỉu năm "
           "ngoái thành ngất hiện tại (tiêu chí ngất xếp ESI 2) và phải chuyển nhân viên y tế vì corpus không có tiêu chí."),
    # ------------------------------------------------------------------ ESI 3: than phiền thường ngày, dấu hiệu nặng
    #                                                                     bị phủ định, mức do dữ kiện được kể rõ
    S("c190", "boarding_house_dengue_fear_fever_poor_intake_teencode", "Sốt 38,8 ăn kém giữa xóm trọ có người sốt xuất huyết, tự phủ nhận dấu hiệu chảy máu",
      P(22, "Male"),
      "E 22t, sốt từ hôm kia, sáng nay cặp nách 38 độ 8, ng mệt rã rời, đau nhức mình mẩy với sau hốc mắt, ăn uống kém "
      "hẳn, mỗi bữa đc vài muỗng cháo. Xóm trọ e mấy ng bị sốt xuất huyết r nên e sợ. E khum chảy máu chân răng, khum chảy "
      "máu cam, ko nổi chấm đỏ, bụng ko đau, ko ói.",
      {"fever_present": "YES", "temperature": 38.8, "associated_systemic_symptoms": "MULTIPLE_SYMPTOMS",
       "infection_source_symptom_group": "NONE_CLEAR", "pain_present": "YES", "headache_present": "YES",
       "headache_location": "AROUND_EYE", "oral_intake_tolerance": "REDUCED", "oral_bleeding_present": "NO",
       "epistaxis_present": "NO", "rash_or_skin_finding_present": "NO", "abdominal_pain_present": "NO",
       "vomiting_present": "NO", "similar_symptoms_in_others": "YES", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, screen=QUIET, concepts=("fever", "myalgia", "sick_contact"),
      tags=("abbreviation", "negation", "environmental"),
      answers={"fever_present": "Có, e sốt từ hôm kia.",
               "temperature": "Sáng nay cặp nách 38 độ 8.",
               "associated_systemic_symptoms": "Sốt với ng mệt rã rời luôn.",
               "infection_source_symptom_group": "Chỉ sốt với nhức mình mẩy thôi, ko thấy chỗ nào khác.",
               "pain_present": "Có, đau nhức mình mẩy với sau hốc mắt.",
               "headache_present": "Có, nhức sau hốc mắt.",
               "headache_location": "Sau hốc mắt.",
               "oral_intake_tolerance": "Ăn uống kém hẳn, mỗi bữa đc vài muỗng cháo.",
               "oral_bleeding_present": "Khum chảy máu chân răng.",
               "epistaxis_present": "Khum chảy máu cam.",
               "rash_or_skin_finding_present": "Ko nổi chấm đỏ j hết.",
               "abdominal_pain_present": "Bụng ko đau.",
               "vomiting_present": "Ko ói.",
               "similar_symptoms_in_others": "Có, xóm trọ e mấy ng bị sốt xuất huyết r.",
               "symptom_duration_bucket": "Sốt từ hôm kia tới giờ."},
      unknown={"pain_severity": "Đau nhức khắp ng á, e ko bik chấm mấy điểm."},
      confirmation="Dạ đúng r.",
      test="Sốt 38,8 kèm ăn kém ở thanh niên sống giữa xóm trọ có người sốt xuất huyết, viết tắt ('khum', 'ko', 'ng'), tự "
           "phủ nhận chảy máu chân răng, chảy máu cam, chấm đỏ, đau bụng, nôn; agent không được đọc các dấu hiệu bị phủ "
           "nhận thành có để nâng lên ESI 2, cũng không trấn an hạ mức, và không tự nêu chẩn đoán sốt xuất huyết: ESI 3 nhờ "
           "sốt kèm ăn kém."),
    S("c191", "toddler_mouth_sores_less_drinking_fewer_wees_southern", "Bé 3 tuổi lở miệng, ăn uống ít, tiểu ít, mẹ phủ nhận bóng nước tay chân",
      P(3, "Female", "CHILD"),
      "Bé nhà em 3 tuổi, ba bữa nay trong miệng lở mấy chỗ ở lưỡi với nướu, đỏ rát, đụng muỗng vô là khóc, nên bé biếng ăn "
      "hẳn, uống sữa uống nước cũng ít. Từ sáng tới giờ bé mới tè có hai lần, ít hơn mọi bữa nhiều. Bé hông sốt, tay chân "
      "với mông hổng có nổi bóng nước, vẫn chơi được.",
      {"oral_problem_present": "YES", "oral_problem_location": "MULTIPLE_LOCATIONS", "oral_pain_present": "YES",
       "oral_pain_location": "DIFFUSE_ORAL", "pain_present": "YES", "oral_intake_tolerance": "REDUCED",
       "urination_status": "DECREASED", "urine_output_level": "REDUCED", "fever_present": "NO",
       "rash_or_skin_finding_present": "NO", "activity_level": "NORMAL", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, screen=QUIET, concepts=("oral_ulcer", "decreased_fluid_intake", "decreased_urination"),
      tags=("pediatric", "caregiver", "dialect", "negation"),
      answers={"oral_problem_present": "Dạ có, trong miệng bé lở mấy chỗ.",
               "oral_problem_location": "Lở ở lưỡi với nướu.",
               "oral_pain_present": "Dạ có, đụng muỗng vô là bé khóc.",
               "oral_pain_location": "Đau ở mấy chỗ lở trên lưỡi với nướu.",
               "pain_present": "Dạ có, mấy chỗ lở trong miệng đỏ rát.",
               "oral_intake_tolerance": "Bé biếng ăn hẳn, uống sữa uống nước cũng ít.",
               "urination_status": "Từ sáng tới giờ bé mới tè có hai lần, ít hơn mọi bữa nhiều.",
               "urine_output_level": "Từ sáng tới giờ mới tè có hai lần, ít hơn mọi bữa.",
               "fever_present": "Bé hông sốt.",
               "rash_or_skin_finding_present": "Tay chân với mông hổng có nổi bóng nước gì hết.",
               "activity_level": "Bé vẫn chơi được.",
               "symptom_duration_bucket": "Ba bữa nay rồi."},
      unknown={"pain_severity": "Bé còn nhỏ, hổng biết chấm điểm, chỉ đụng muỗng vô là khóc."},
      test="Trẻ 3 tuổi lở miệng ba ngày, ăn uống ít và tiểu ít hơn hẳn, mẹ kể giọng miền Nam 'hông sốt', 'hổng có nổi bóng "
           "nước' ở tay chân và mông; agent phải nhận ra ăn kém kèm tiểu ít (ESI 3), không đọc phủ định thành bóng nước của "
           "tay chân miệng, và không hạ mức vì 'chỉ là lở miệng'."),
    S("c192", "death_anniversary_feast_vomiting_home_cuff_husband", "Nôn liên tục sau ăn đám giỗ, chồng đo huyết áp 118/76, 'hổng có ói ra máu'",
      P(34, "Female", "SPOUSE"),
      "Vợ tui 34 tuổi, tối qua đi ăn đám giỗ bên ngoại về, từ ba giờ sáng tới giờ ói chắc bảy tám lần, ra đồ ăn chưa tiêu, "
      "uống miếng nước là ói ra lại. Hổng có ói ra máu, hổng sốt, bụng chỉ quặn nhẹ chừng 3 điểm, chưa đi cầu lần nào. "
      "Nghe nói mấy người bên ngoại ăn chung mâm cũng đang đau bụng, ói. Tui đo máy huyết áp ở nhà được 118 trên 76, mạch "
      "96. Vợ tui vẫn tỉnh, nói chuyện bình thường, đang đặt vòng nên hổng có thai.",
      {"vomiting_present": "YES", "vomiting_frequency": "REPEATED", "vomit_appearance": "FOOD_CONTENT",
       "oral_intake_tolerance": "UNABLE_TO_KEEP_DOWN", "gastrointestinal_symptom_present": "YES",
       "abdominal_pain_present": "YES", "abdominal_pain_character": "CRAMPING", "pain_present": "YES",
       "pain_severity": 3, "fever_present": "NO", "diarrhea_present": "NO", "systolic_bp": 118, "diastolic_bp": 76,
       "heart_rate": 96, "altered_mental_status_present": "NO", "pregnancy_status": "NOT_PREGNANT",
       "similar_symptoms_in_others": "YES", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      3, screen=QUIET, concepts=("vomiting", "abdominal_cramping"),
      tags=("caregiver", "dialect", "negation", "food_related"),
      answers={"vomiting_present": "Có, vợ tui ói từ ba giờ sáng tới giờ.",
               "vomiting_frequency": "Ói chắc bảy tám lần rồi, ói hoài.",
               "vomit_appearance": "Ra đồ ăn chưa tiêu, hổng có máu.",
               "oral_intake_tolerance": "Uống miếng nước là ói ra lại.",
               "gastrointestinal_symptom_present": "Có, ói hoài, bụng quặn nhẹ.",
               "abdominal_pain_present": "Có, bụng quặn nhẹ.",
               "abdominal_pain_character": "Quặn nhẹ từng cơn.",
               "pain_present": "Có, bụng quặn nhẹ thôi.",
               "pain_severity": "Chừng 3 điểm.",
               "fever_present": "Hổng sốt.",
               "diarrhea_present": "Hổng có tiêu chảy, chưa đi cầu lần nào.",
               "systolic_bp": "Máy đo ở nhà báo số trên 118.",
               "diastolic_bp": "Số dưới 76.",
               "heart_rate": "Máy báo mạch 96.",
               "altered_mental_status_present": "Hổng, vợ tui vẫn tỉnh, nói chuyện bình thường.",
               "pregnancy_status": "Hổng có thai, vợ tui đang đặt vòng.",
               "similar_symptoms_in_others": "Có, nghe nói mấy người bên ngoại ăn chung mâm cũng đang đau bụng, ói.",
               "symptom_duration_bucket": "Từ ba giờ sáng tới giờ."},
      test="Nôn liên tục không giữ được nước sau ăn đám giỗ, chồng đo huyết áp 118/76 và mạch 96 bằng máy ở nhà, kể giọng "
           "miền Nam 'hổng có ói ra máu, hổng sốt'; agent phải xếp ESI 3 vì không giữ được nước khi sinh hiệu ổn, không đọc "
           "'ói ra máu' sau 'hổng có' thành có (khác m10 ở nguyên nhân là ngộ độc tập thể sau bữa giỗ, người kể, và câu "
           "phủ định đứng trước chữ đáng sợ)."),
    S("c193", "febrile_cystitis_hong_hong_lung_southern", "Tiểu buốt kèm sốt 38,3, tức trên xương mu, 'hông có đau hông lưng'",
      P(38, "Female", allergies=("Cotrimoxazol",)),
      "Em 38 tuổi, từ hôm kia đi tiểu buốt gắt, mắc tiểu hoài mà mỗi lần ra một ít, bụng dưới ngay trên xương mu tức chừng "
      "5 điểm. Tối qua em lên cơn sốt, sáng nay kẹp nách được 38 độ 3. Em hông có đau hông lưng, hông ói, nước tiểu hơi "
      "đục chứ hổng có máu. Em mới sạch kinh tuần trước. Em dị ứng thuốc cotrimoxazol.",
      {"urinary_symptom_present": "YES", "genitourinary_pain_present": "YES",
       "genitourinary_pain_location": "SUPRAPUBIC", "pain_present": "YES", "pain_severity": 5,
       "voiding_ability": "REDUCED", "urine_appearance": "CLOUDY", "fever_present": "YES", "temperature": 38.3,
       "infection_source_symptom_group": "URINARY", "associated_systemic_symptoms": "FEVER",
       "back_or_spinal_problem_present": "NO", "vomiting_present": "NO", "pregnancy_status": "NOT_PREGNANT",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, screen=QUIET, concepts=("dysuria", "suprapubic_pain", "fever"),
      tags=("dialect", "negation", "ambiguous_wording"),
      answers={"urinary_symptom_present": "Dạ có, em đi tiểu buốt gắt, mắc tiểu hoài.",
               "genitourinary_pain_present": "Dạ có, tức ở bụng dưới ngay trên xương mu, đi tiểu thì buốt.",
               "genitourinary_pain_location": "Tức ngay trên xương mu.",
               "pain_present": "Dạ có, tức bụng dưới với buốt lúc đi tiểu.",
               "pain_severity": "Chừng 5 điểm.",
               "voiding_ability": "Mắc tiểu hoài mà mỗi lần ra một ít.",
               "urine_appearance": "Nước tiểu hơi đục, hổng có máu.",
               "fever_present": "Dạ có, tối qua em lên cơn sốt.",
               "temperature": "Sáng nay kẹp nách được 38 độ 3.",
               "infection_source_symptom_group": "Chủ yếu là tiểu buốt, mắc tiểu hoài.",
               "associated_systemic_symptoms": "Em có sốt.",
               "back_or_spinal_problem_present": "Hông có, em hông có đau hông lưng gì hết.",
               "vomiting_present": "Hông ói.",
               "pregnancy_status": "Hổng có thai, em mới sạch kinh tuần trước.",
               "symptom_duration_bucket": "Tiểu buốt từ hôm kia, sốt thì từ tối qua."},
      test="Tiểu buốt kèm sốt 38,3 và tức trên xương mu 5/10, giọng miền Nam 'hông có đau hông lưng' (chữ 'hông' vừa là "
           "phủ định vừa là bộ phận cơ thể); agent phải hiểu là không đau hông lưng chứ không ghi đau vùng hông lưng (sẽ "
           "khớp tiêu chí sốt kèm đau hông lưng ESI 2), và xếp ESI 3 nhờ sốt kèm đau mức vừa."),
    S("c194", "office_worker_worsening_lower_belly_ache_cha_chang", "Phụ nữ trẻ đau âm ỉ bụng dưới tăng dần tới 6/10, phủ định 'chả', 'chẳng'",
      P(24, "Female"),
      "Em 24 tuổi, làm văn phòng. Từ hôm kia em đau âm ỉ bụng dưới, lúc đầu chỉ lâm râm, đến hôm nay đau tăng dần, giờ "
      "chừng 6 điểm, đi lại mạnh thì đau hơn. Sáng nay em thử que được một vạch, kinh vừa hết được mười ngày. Em chả sốt, "
      "chẳng nôn, không ra máu hay khí hư lạ, đi tiểu bình thường, đi ngoài vẫn đều.",
      {"abdominal_pain_present": "YES", "abdominal_pain_location": "LOWER_ABDOMEN", "abdominal_pain_character": "DULL",
       "gastrointestinal_symptom_present": "YES", "pain_present": "YES", "pain_severity": 6, "symptom_onset": "GRADUAL",
       "symptom_trend": "WORSENING", "pregnancy_status": "NOT_PREGNANT", "fever_present": "NO", "vomiting_present": "NO",
       "vaginal_bleeding_present": "NO", "genital_discharge_present": "NO", "urinary_symptom_present": "NO",
       "constipation_or_defecation_problem_present": "NO", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, screen=QUIET, concepts=("lower_abdominal_pain",),
      tags=("negation",),
      answers={"abdominal_pain_present": "Có ạ, em đau âm ỉ bụng dưới.",
               "abdominal_pain_location": "Ở bụng dưới ạ.",
               "abdominal_pain_character": "Đau âm ỉ ạ.",
               "gastrointestinal_symptom_present": "Có, em đau bụng dưới, chẳng nôn.",
               "pain_present": "Có ạ, đau bụng dưới.",
               "pain_severity": "Giờ chừng 6 điểm ạ.",
               "symptom_onset": "Từ từ ạ, lúc đầu chỉ lâm râm.",
               "symptom_trend": "Đau tăng dần, hôm nay đau hơn hôm kia.",
               "pregnancy_status": "Sáng nay em thử que được một vạch, kinh vừa hết được mười ngày.",
               "fever_present": "Em chả sốt ạ.",
               "vomiting_present": "Chẳng nôn ạ.",
               "vaginal_bleeding_present": "Không ra máu ạ.",
               "genital_discharge_present": "Không có khí hư lạ ạ.",
               "urinary_symptom_present": "Đi tiểu bình thường ạ.",
               "constipation_or_defecation_problem_present": "Không ạ, đi ngoài vẫn đều.",
               "symptom_duration_bucket": "Từ hôm kia ạ."},
      test="Đau âm ỉ bụng dưới tăng dần tới 6/10 ở phụ nữ trẻ, que thử một vạch, tự phủ nhận sốt, nôn, ra máu bằng 'chả', "
           "'chẳng', 'không'; agent phải hỏi và ghi đúng tình trạng thai (que thử một vạch), xếp ESI 3 nhờ đau mức vừa đang "
           "tăng, không hạ mức vì người bệnh phủ nhận nhiều triệu chứng, và không tự nêu chẩn đoán (khác c157 của "
           "b3_common_c: người 57 tuổi đau bụng trái, không có bước hỏi thai)."),
    S("c195", "second_pregnancy_9w_vomiting_home_cuff_cha_chang", "Thai 9 tuần nôn không giữ được nước, huyết áp 112/70, mạch 98",
      P(30, "Female"),
      "Em có bầu 9 tuần, con thứ hai. Ba hôm nay em nôn suốt, ngày cả chục lần, uống ngụm nước cũng nôn ra, mấy hôm không "
      "ăn được gì. Chồng em đo huyết áp được 112/70, mạch 98. Em chả ra máu, bụng chẳng đau, không sốt, vẫn tỉnh táo, chỉ "
      "mệt lả người.",
      {"pregnancy_present": "YES", "pregnancy_status": "PREGNANT", "gestational_age_weeks": 9,
       "vomiting_present": "YES", "vomiting_frequency": "REPEATED", "oral_intake_tolerance": "UNABLE_TO_KEEP_DOWN",
       "gastrointestinal_symptom_present": "YES", "systolic_bp": 112, "diastolic_bp": 70, "heart_rate": 98,
       "vaginal_bleeding_present": "NO", "abdominal_pain_present": "NO", "fever_present": "NO",
       "altered_mental_status_present": "NO", "associated_systemic_symptoms": "GENERAL_WEAKNESS",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      3, screen=QUIET, concepts=("vomiting_in_pregnancy", "nausea_in_pregnancy"),
      tags=("pregnancy", "negation"),
      answers={"pregnancy_present": "Dạ có, em đang bầu 9 tuần.",
               "pregnancy_status": "Em đang mang thai con thứ hai.",
               "gestational_age_weeks": "Thai được 9 tuần ạ.",
               "vomiting_present": "Có ạ, em nôn suốt ba hôm nay.",
               "vomiting_frequency": "Ngày cả chục lần ạ.",
               "oral_intake_tolerance": "Uống ngụm nước cũng nôn ra, mấy hôm không ăn được gì.",
               "gastrointestinal_symptom_present": "Có ạ, em nôn suốt, bụng thì chẳng đau.",
               "systolic_bp": "Chồng em đo số trên 112.",
               "diastolic_bp": "Số dưới 70.",
               "heart_rate": "Mạch 98 ạ.",
               "vaginal_bleeding_present": "Em chả ra máu ạ.",
               "abdominal_pain_present": "Bụng chẳng đau ạ.",
               "fever_present": "Không sốt ạ.",
               "altered_mental_status_present": "Không ạ, em vẫn tỉnh táo.",
               "associated_systemic_symptoms": "Em không sốt, chỉ mệt lả người.",
               "symptom_duration_bucket": "Ba hôm nay rồi ạ."},
      test="Thai 9 tuần nôn liên tục không giữ được nước ba ngày, chồng đo huyết áp 112/70 và mạch 98, tự phủ nhận ra máu, "
           "đau bụng bằng 'chả', 'chẳng'; agent phải xếp ESI 3 (giữa c43 nghén nhẹ ESI 4 và m39 nôn kèm mạch 124 ESI 2), "
           "không coi đây là nghén bình thường và không tự khuyên thuốc chống nôn."),
    # ------------------------------------------------------------------ ESI 2: than phiền thường ngày, con số sinh hiệu
    #                                                                     đo tại nhà quyết định, lời kể phủ định triệu chứng
    S("c196", "new_prostate_pill_standing_dizzy_low_bp_central", "Cụ ông mới thêm thuốc tiền liệt tuyến, choáng khi đứng, vợ đo huyết áp 86/52",
      P(71, "Male", "SPOUSE", chronic=("Tăng huyết áp", "Phì đại tuyến tiền liệt"), allergies=("Penicillin",),
        meds=("Amlodipin", "Doxazosin")),
      "Ông nhà tui 71 tuổi, có bệnh huyết áp với tiền liệt tuyến. Hôm kia đi khám được cho thêm một loại thuốc tiền liệt "
      "tuyến uống buổi tối. Từ sáng ni hễ đứng dậy là ổng choáng váng, chân muốn khuỵu, phải ngồi xuống liền, chứ không "
      "có xỉu mô. Tui để ổng ngồi nghỉ rồi đo máy huyết áp ở nhà được 86 trên 52, mạch 88. Ổng vẫn tỉnh, nói năng bình "
      "thường, tay chân không yếu chi, không đau ngực.",
      {"dizziness_present": "YES", "dizziness_sensation": "LIGHTHEADED", "syncope_present": "NO", "systolic_bp": 86,
       "diastolic_bp": 52, "heart_rate": 88, "altered_mental_status_present": "NO",
       "focal_neurologic_symptoms": "NONE", "chest_pain_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, screen="", concepts=("lightheadedness", "hypotension"),
      tags=("older_adult", "caregiver", "comorbidity", "dialect", "negation", "medication_reaction"),
      answers={"dizziness_present": "Có, hễ đứng dậy là ổng choáng váng.",
               "dizziness_sensation": "Choáng váng, chân muốn khuỵu, phải ngồi xuống liền.",
               "syncope_present": "Không có xỉu mô, ổng ngồi xuống kịp.",
               "systolic_bp": "Ngồi nghỉ rồi đo, máy báo số trên 86.",
               "diastolic_bp": "Số dưới 52.",
               "heart_rate": "Máy báo mạch 88.",
               "altered_mental_status_present": "Không, ổng vẫn tỉnh, nói năng bình thường.",
               "focal_neurologic_symptoms": "Tay chân không yếu chi, nói năng bình thường.",
               "chest_pain_present": "Không đau ngực.",
               "symptom_duration_bucket": "Từ sáng ni tới chừ."},
      test="Cụ ông mới thêm thuốc tiền liệt tuyến, choáng mỗi khi đứng dậy, vợ đo huyết áp 86/52 sau khi cho ngồi nghỉ, "
           "giọng miền Trung 'không có xỉu mô'; agent phải xếp ESI 2 nhờ con số huyết áp, không hạ mức vì 'không xỉu' và "
           "đầu óc tỉnh, và không tự khuyên ngừng hay đổi thuốc."),
    S("c197", "elder_cold_denies_breathlessness_oximeter_90_son", "Cụ bà cảm, nói 'hổng có khó thở' nhưng con đo SpO2 hai lần đều 90",
      P(76, "Female", "PARENT", chronic=("Tăng huyết áp",), meds=("Amlodipin",)),
      "Má tui 76 tuổi, cảm ba bữa nay, ho khan, sổ mũi, người hơi mệt nên nằm nhiều hơn mọi bữa. Bả nói hổng có khó thở "
      "gì hết, mà tui lấy máy kẹp ngón tay đo hai lần, lần nào cũng 90, đổi qua ngón khác cũng 90. Nhiệt kế đo 37 độ 6. "
      "Má vẫn tỉnh táo, ăn uống được, hổng ho ra máu.",
      {"cough_present": "YES", "cough_character": "DRY", "runny_nose_present": "YES", "spo2": 90,
       "dyspnea_present": "NO", "temperature": 37.6, "fever_present": "NO",
       "associated_systemic_symptoms": "GENERAL_WEAKNESS", "altered_mental_status_present": "NO",
       "oral_intake_tolerance": "NORMAL", "hemoptysis_present": "NO", "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      2, screen="", concepts=("cough", "runny_nose", "fatigue"),
      tags=("older_adult", "caregiver", "comorbidity", "dialect", "negation", "minimization", "vitals_inconsistent"),
      answers={"cough_present": "Có, má ho khan.",
               "cough_character": "Ho khan thôi.",
               "runny_nose_present": "Có, má sổ mũi.",
               "spo2": "Máy kẹp ngón tay đo hai lần đều 90, đổi qua ngón khác cũng 90.",
               "dyspnea_present": "Bả nói hổng có khó thở gì hết.",
               "temperature": "Nhiệt kế đo 37 độ 6.",
               "fever_present": "Nhiệt kế đo có 37 độ 6 thôi.",
               "associated_systemic_symptoms": "Má hơi mệt, nằm nhiều hơn mọi bữa.",
               "altered_mental_status_present": "Không, má vẫn tỉnh táo.",
               "oral_intake_tolerance": "Má vẫn ăn uống được.",
               "hemoptysis_present": "Hổng ho ra máu.",
               "symptom_duration_bucket": "Ba bữa nay rồi."},
      test="Cụ bà cảm ba ngày, tự nói 'hổng có khó thở' nhưng con trai đo SpO2 hai lần trên hai ngón đều 90; agent phải tin "
           "con số đo được hơn lời phủ nhận và xếp ESI 2, không coi là cảm thường như c185 (cùng than phiền, SpO2 97)."),
    # ------------------------------------------------------------------ ESI 4-5: số nguồn lực do người viết lập luận
    S("c198", "tour_guide_voice_strain_sore_throat_central", "Hướng dẫn viên du lịch rát họng, khàn giọng vì nói nhiều, không sốt",
      P(33, "Male"),
      "Tui làm hướng dẫn viên du lịch, tuần ni dẫn đoàn nói suốt ngày nên họng rát rát, giọng hơi khàn, đau chừng 2 điểm. "
      "Tui không sốt, nuốt cơm uống nước bình thường, không ho, không chảy mũi chi hết. Bị được ba bữa rồi.",
      {"sore_throat_present": "YES", "pain_present": "YES", "pain_severity": 2, "swallowing_ability": "NORMAL",
       "fever_present": "NO", "cough_present": "NO", "runny_nose_present": "NO",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      5, screen=QUIET, resources=0,
      resource_basis="AHRQ_T5_1_REASONED: đau rát họng không sốt, không ho, nuốt bình thường: chỉ cần khám và dặn nghỉ "
                     "giọng; không dự kiến xét nghiệm nhanh liên cầu, thuốc tiêm hay thủ thuật nào tính là nguồn lực",
      concepts=("sore_throat", "hoarseness"),
      tags=("dialect", "negation", "occupational"),
      answers={"sore_throat_present": "Có, họng rát rát.",
               "pain_present": "Có, rát họng thôi.",
               "pain_severity": "Đau chừng 2 điểm.",
               "swallowing_ability": "Nuốt cơm uống nước bình thường.",
               "fever_present": "Không sốt.",
               "cough_present": "Không ho.",
               "runny_nose_present": "Không chảy mũi chi hết.",
               "symptom_duration_bucket": "Bị được ba bữa rồi."},
      test="Rát họng, khàn giọng vì nói nhiều ở hướng dẫn viên du lịch, giọng miền Trung 'không sốt', 'không ho, không chảy "
           "mũi chi hết', nuốt bình thường; ESI 5 nhờ số nguồn lực 0 do người viết lập luận, agent không được nâng mức như "
           "ca mẫu đau họng c03 khi không sốt và không tự kê kháng sinh."),
    S("c199", "school_camp_mosquito_bites_teacher_southern", "Cô giáo kể học sinh 6 tuổi bị muỗi cắn chục nốt ở cẳng chân sau cắm trại",
      P(6, "Male", "OTHER"),
      "Tui là cô giáo chủ nhiệm lớp một. Hôm qua lớp đi cắm trại, sáng nay có một bé trai 6 tuổi cẳng chân phải bị muỗi "
      "cắn nổi cả chục cục đỏ gồ lên, ngứa gãi hoài, bé nói ngứa chừng 3 điểm. Hổng sưng lan ra chỗ khác, hổng sốt, mặt "
      "mũi môi hổng sưng, bé vẫn chơi bình thường. Phụ huynh nhờ tui hỏi giùm.",
      {"bite_or_sting_present": "YES", "bite_source": "INSECT", "rash_or_skin_finding_present": "YES",
       "skin_finding_appearance": "RAISED_WHEALS", "skin_finding_distribution": "LOCALIZED", "itching_present": "YES",
       "itching_severity": 3, "facial_swelling_present": "NO", "fever_present": "NO", "activity_level": "NORMAL",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      5, screen=QUIET, resources=0,
      resource_basis="AHRQ_T5_1_REASONED: muỗi cắn khu trú ở một cẳng chân, không sưng lan, không dấu hiệu toàn thân: chỉ "
                     "cần khám, thuốc bôi hoặc thuốc uống chống ngứa không tính là nguồn lực",
      concepts=("insect_bite", "pruritus"),
      tags=("pediatric", "collateral_history", "dialect", "negation"),
      answers={"bite_or_sting_present": "Có, bé bị muỗi cắn lúc cắm trại.",
               "bite_source": "Muỗi cắn.",
               "rash_or_skin_finding_present": "Có, cẳng chân phải nổi cả chục cục đỏ gồ lên.",
               "skin_finding_appearance": "Mấy cục đỏ gồ lên chỗ muỗi cắn.",
               "skin_finding_distribution": "Chỉ ở cẳng chân phải thôi.",
               "itching_present": "Có, bé ngứa gãi hoài.",
               "itching_severity": "Bé nói ngứa chừng 3 điểm.",
               "facial_swelling_present": "Mặt mũi môi hổng sưng.",
               "fever_present": "Hổng sốt.",
               "activity_level": "Bé vẫn chơi bình thường.",
               "symptom_duration_bucket": "Sáng nay mới thấy, hôm qua đi cắm trại."},
      test="Muỗi cắn khu trú ở cẳng chân học sinh 6 tuổi sau cắm trại, cô giáo kể giọng miền Nam 'hổng sưng lan, hổng sốt, "
           "mặt mũi môi hổng sưng'; ESI 5 nhờ số nguồn lực 0 do người viết lập luận, agent không được đọc các chữ 'hổng "
           "sưng' thành có sưng môi mặt kiểu phản vệ."),
    S("c200", "bamboo_strip_splinter_fingertip_no_diacritics", "Dằm tre nằm dưới da đầu ngón trỏ, gõ không dấu, rất ngắn",
      P(52, "Male"),
      "Chieu nay che lat tre bi dam dam vao dau ngon tro tay trai, thay 1 doan den den nam duoi da, tu nhe ko ra, nhoi "
      "nhoi tam 3/10. Ko chay mau, ko sung do.",
      {"wound_present": "YES", "wound_type": "PUNCTURE", "wound_location": "HAND_FINGER",
       "wound_depth_category": "THROUGH_SKIN", "foreign_body_status": "RETAINED", "bleeding_present": "NO",
       "swelling_present": "NO", "pain_present": "YES", "pain_severity": 3, "trauma_present": "YES",
       "trauma_mechanism": "PENETRATING_INJURY", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      4, screen=QUIET, resources=1,
      resource_basis="AHRQ_T5_1_REASONED: lấy dằm nằm dưới da là thủ thuật đơn giản = 1 nguồn lực; băng vết thương và tiêm "
                     "phòng uốn ván không tính",
      concepts=("retained_foreign_body", "finger_pain"),
      tags=("no_diacritics", "abbreviation", "negation", "short_opening"),
      answers={"wound_present": "Co, bi dam tre dam vao dau ngon tro.",
               "wound_type": "Dam tre dam vao, lo nho thoi.",
               "wound_location": "O dau ngon tro tay trai.",
               "wound_depth_category": "Dam nam duoi da, khong sau lam.",
               "foreign_body_status": "Con thay 1 doan dam den den nam duoi da, tu nhe ko ra.",
               "bleeding_present": "Ko chay mau.",
               "swelling_present": "Ko sung do.",
               "pain_present": "Co, nhoi nhoi.",
               "pain_severity": "Tam 3/10.",
               "trauma_present": "Co, che lat tre bi dam dam vao tay.",
               "trauma_mechanism": "Dam tre dam vao ngon tay.",
               "symptom_duration_bucket": "Moi chieu nay."},
      clarification="Noi lai cho ro: chieu nay che lat tre bi dam dam vao dau ngon tro tay trai, dam con nam duoi da, nhoi "
                    "tam 3/10, ko chay mau, ko sung do.",
      confirmation="Dung roi.",
      test="Lời rất ngắn, không dấu: dằm tre nằm dưới da đầu ngón trỏ, 'ko chay mau, ko sung do'; ESI 4 nhờ một nguồn lực "
           "(lấy dị vật) do người viết lập luận, agent phải đọc 'bi dam dam' là bị dằm đâm chứ không phải vết đâm sâu, và "
           "không đọc 'ko chay mau' thành đang chảy máu."),
]
