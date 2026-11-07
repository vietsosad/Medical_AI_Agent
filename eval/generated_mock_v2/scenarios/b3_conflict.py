"""Nhóm CONFLICTING, đợt 3: thông tin mâu thuẫn rồi được đính chính, với kiểu sai mới.

Đợt 3 phủ những tiêu chí bỏng và đè dập chưa ca nào khớp (bỏng hoá chất lan rộng, bỏng
hoá chất / hơi nước vùng mặt cổ, bỏng nhiều màu da hoặc trắng bệch mất cảm giác, bỏng vùng
kín mất cảm giác, đè dập kèm lạnh / tê / nhiều dấu hiệu ở phần chân phía dưới), cùng vài
tình huống sinh hiệu và lời khai mới. Mỗi ca dùng một kiểu sai khác hẳn đợt 1-2: nhận nhầm
tác nhân, chữ không dấu hai nghĩa, cơ chế bị giấu, lần khám cũ và lần khám mới, ánh sáng làm
sai màu da, người nhà dịch nhầm, huyết áp nói tắt theo cmHg, đọc nhầm dòng trên máy đo, số
đo nhiễu do tay lạnh và sơn móng, ý định tự hại lộ ra sau.

Quy ước giữ nguyên như ``conflict.py`` và ``b2_conflict.py``: ``facts`` là trạng thái CUỐI
CÙNG sau khi đính chính; lời đính chính nằm ở chỗ agent chắc chắn nghe thấy (câu trả lời cho
đúng dữ kiện đó, ``confirmation``, hoặc ``clarification``); ``conflict`` ghi hai phiên bản.
Khi phiên bản ban đầu tự nó đã cho một nhãn quyết định (ESI 1-2), agent có thể kết thúc trước
bước xác nhận, nên lời đính chính nằm ngay trong lời mở đầu (k43, k54). ``test`` ghi nhãn của
cả hai phiên bản; nhãn của phiên bản ban đầu được tính bằng chính bộ kiểm tra, bằng cách tạm
thay ``facts`` của ca bằng dữ kiện ban đầu; không nhãn nào được viết tay.

Bộ tiêu chí ``distal_limb_symptoms`` của corpus chỉ mở khi có vấn đề chi dưới, còn cơ chế đè
dập lại là dữ kiện chi trên, nên ba ca đè dập (k45-k47) đều là vật nặng đè cùng lúc lên một
cẳng tay và một cẳng chân.
"""

from __future__ import annotations

from eval.generated_mock_v2.spec import CONFLICT, INCOMPLETE, P, SCREEN_QUIET as QUIET, Spec


def S(key: str, family: str, title: str, profile: dict, opening: str, facts: dict, intended, **kw) -> Spec:
    return Spec(case_id=key, family=family, group=CONFLICT, title=title, profile=profile,
                opening=opening, facts=facts, intended=intended, **kw)


SPECS = [
    S("k41", "lime_pit_mistaken_for_mud_toddler", "Mẹ tưởng con ngã hố bùn, thợ xây nói là hố vôi tôi: bỏng hoá chất lan rộng",
      P(4, "Male", "CHILD"),
      "Con trai tôi 4 tuổi chạy sang nhà hàng xóm đang xây thì sẩy chân ngã xuống một cái hố bùn trắng, ngập tới ngực, "
      "người lớn kéo lên ngay. Tôi tắm rửa sạch cho cháu rồi mà cháu cứ khóc ré, kêu rát khắp người, da đỏ lựng từ ngực "
      "xuống tới hai bàn chân. Chuyện mới chừng nửa tiếng.",
      {"burn_present": "YES", "burn_mechanism": "CHEMICAL", "burn_location": "MULTIPLE_AREAS",
       "burn_extent_estimate": "WIDESPREAD", "burn_skin_appearance": "RED", "burn_sensation": "PAINFUL_OR_BURNING",
       "pain_present": "YES", "trauma_present": "YES", "trauma_mechanism": "FALL", "eye_problem_present": "NO",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("chemical_burn", "chemical_exposure"), screen=QUIET,
      answers={"burn_present": "Có, giờ thì tôi biết là cháu bị bỏng chứ không phải chỉ lấm bùn.",
               "burn_mechanism": "Anh thợ xây bên đó vừa chạy sang bảo đó không phải hố bùn mà là hố tôi vôi để xây nhà, "
                                 "cháu bị vôi ăn da.",
               "burn_location": "Từ ngực, bụng xuống hết hai chân, cả hai bàn chân.",
               "burn_extent_estimate": "Gần như khắp người, từ ngực trở xuống chỗ nào cũng đỏ.",
               "burn_skin_appearance": "Da đỏ lựng.",
               "burn_sensation": "Cháu kêu rát, chạm vào là khóc thét.",
               "pain_present": "Có, cháu kêu rát khắp người.",
               "trauma_present": "Có, cháu sẩy chân ngã xuống hố.",
               "trauma_mechanism": "Sẩy chân ngã xuống hố, người lớn kéo lên ngay.",
               "eye_problem_present": "Mắt cháu không sao, cháu chỉ ngập tới ngực, mặt không dính.",
               "symptom_duration_bucket": "Mới chừng nửa tiếng."},
      unknown={"pain_severity": "Cháu còn bé quá, chỉ khóc với kêu rát chứ không chấm điểm được."},
      confirmation="Tôi phải sửa lại: anh thợ xây bảo cái hố cháu ngã xuống là hố tôi vôi chứ không phải hố bùn, cháu bị "
                   "vôi ăn da từ ngực xuống tới hai bàn chân.",
      conflict=("Mẹ kể: ngã xuống 'hố bùn trắng', tưởng chỉ lấm bùn",
                "Thợ xây đính chính: hố vôi tôi, bỏng hoá chất từ ngực xuống hai bàn chân"),
      tags=("contradiction", "collateral_history", "changed_answer", "pediatric", "caregiver", "hidden_red_flag"),
      test="Tác nhân bị người kể nhận nhầm: bản đầu (ngã hố bùn, không rõ tác nhân) là INCOMPLETE, bản đính chính (vôi tôi, "
           "bỏng hoá chất lan rộng từ ngực xuống hai bàn chân) là ESI 2."),
    S("k42", "caustic_jerrycan_collar_neck_burn", "Vác can xút ướt cổ áo: tưởng chỉ dính ngực, vợ thấy vệt bỏng trắng bên cổ",
      P(48, "Male", allergies=("Cotrimoxazol",)),
      "Tôi làm ở xưởng rửa nhựa phế liệu. Khoảng hai tiếng trước tôi vác can nước xút lên vai phải thì nắp bị hở, xút sóng "
      "sánh ướt hết cổ áo với ngực áo. Tôi thay áo, dội nước luôn, thấy rát ở ngực, giờ vẫn rát chừng 5/10.",
      {"burn_present": "YES", "burn_mechanism": "CHEMICAL", "burn_location": "FACE_OR_NECK",
       "burn_skin_appearance": "PALE_OR_WHITE", "burn_sensation": "PAINFUL_OR_BURNING",
       "burn_extent_estimate": "SMALL_LOCALIZED_AREA", "pain_present": "YES", "pain_severity": 5,
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("chemical_burn",), screen=QUIET,
      answers={"burn_present": "Có, bị xút làm bỏng.",
               "burn_mechanism": "Nước xút dùng để rửa nhựa, chảy từ can ra.",
               "burn_location": "Vợ tôi vừa xem kỹ: ngực không bị gì cả, chỗ bỏng là bên cổ phải, dọc theo đường cổ áo.",
               "burn_skin_appearance": "Một vệt da trắng bệch bên cổ phải.",
               "burn_extent_estimate": "Một vệt dài cỡ hai đốt ngón tay.",
               "burn_sensation": "Rát, cái rát tôi tưởng ở ngực hoá ra là ở cổ.",
               "pain_present": "Có, rát ở chỗ dính xút.",
               "pain_severity": "Rát chừng 5.",
               "symptom_duration_bucket": "Khoảng hai tiếng rồi."},
      confirmation="Tôi sửa lại: ngực tôi không bị gì, vợ tôi xem thì chỗ bỏng xút là một vệt da trắng bệch bên cổ phải, dọc "
                   "theo cổ áo; cái rát tôi tưởng ở ngực là rát ở cổ.",
      conflict=("Lời kể: xút dính ngực, rát ở ngực", "Vợ xem: ngực lành, vệt bỏng trắng bệch bên cổ phải dọc cổ áo"),
      tags=("contradiction", "collateral_history", "changed_answer", "occupational", "wrong_location"),
      test="Vị trí bỏng hoá chất được đính chính từ ngực sang cổ: bản đầu (bỏng xút ở ngực) là INCOMPLETE, bản đính chính "
           "(vệt bỏng xút trắng bệch ở cổ) là ESI 2."),
    S("k43", "boiler_steam_burst_mistaken_for_fire", "Tưởng lò cháy nổ, khói trắng; chủ xưởng đính chính là ống hơi bục, hít hơi nước nóng",
      P(29, "Male", "OTHER"),
      "Em làm cùng xưởng bánh phở với anh ấy, anh ấy 29 tuổi. Khoảng 20 phút trước nghe đùng một cái, khói trắng mù mịt, "
      "tụi em tưởng lò cháy nổ, anh ấy bị táp lửa vào mặt với cổ, hít phải khói. Nhưng chủ xưởng vừa xem lại bảo ko có lửa "
      "gì hết: ống dẫn hơi của lò hơi bị bục, cái mù trắng là hơi nước nóng phụt thẳng vào mặt, cổ anh ấy, anh ấy hít phải "
      "luôn. Giờ mặt với cổ đỏ rực, phồng mấy chỗ, anh ấy kêu rát, ho khan, giọng hơi khàn, chưa thấy khó thở.",
      {"burn_present": "YES", "burn_mechanism": "STEAM", "burn_location": "FACE_OR_NECK",
       "burn_skin_appearance": "BLISTERED", "burn_sensation": "PAINFUL_OR_BURNING", "smoke_or_fume_exposure": "HOT_STEAM",
       "cough_present": "YES", "cough_character": "DRY", "dyspnea_present": "NO", "pain_present": "YES",
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("steam_exposure", "inhalation_injury", "hoarseness"), screen=QUIET,
      answers={"burn_present": "Có, mặt với cổ bị bỏng.",
               "burn_mechanism": "Hơi nước nóng phụt ra từ ống dẫn hơi bị bục, ko phải lửa.",
               "burn_location": "Ở mặt với cổ.",
               "burn_skin_appearance": "Đỏ rực, phồng mấy bóng nước.",
               "burn_sensation": "Anh ấy kêu rát.",
               "smoke_or_fume_exposure": "Anh ấy hít phải hơi nước nóng lúc ống bục; chủ xưởng bảo ko có khói lửa gì.",
               "cough_present": "Có, ho khan từ lúc bị.",
               "cough_character": "Ho khan.",
               "dyspnea_present": "Chưa thấy khó thở, anh ấy vẫn nói được, chỉ giọng hơi khàn.",
               "pain_present": "Có, anh ấy kêu rát mặt với cổ.",
               "symptom_duration_bucket": "Mới chừng 20 phút."},
      unknown={"pain_severity": "Anh ấy chỉ kêu rát chứ ko chấm điểm."},
      conflict=("Câu đầu: lò cháy nổ, táp lửa vào mặt cổ, hít khói",
                "Chủ xưởng đính chính ngay trong lời kể: ống hơi bục, bỏng hơi nước nóng ở mặt cổ và hít hơi nóng"),
      tags=("contradiction", "collateral_history", "changed_answer", "occupational", "abbreviation"),
      test="Tác nhân được đính chính ngay trong lời kể: giữ 'lửa, khói' vẫn ra ESI 2 nhưng qua tiêu chí bỏng lửa vùng mặt cổ, "
           "bản đúng (hơi nước nóng, có hít hơi nóng) là ESI 2 qua tiêu chí hít hơi nóng vùng mặt cổ, nên ca này phân biệt ở "
           "dữ kiện tác nhân và tiêu chí đại diện chứ không ở mức ESI."),
    S("k44", "spa_facial_steamer_blisters", "Nhân viên spa bảo đỏ do xông là bình thường, khách soi gương thấy phồng nước ở má và cổ",
      P(27, "Female", allergies=("Tôm cua",)),
      "Chiều nay em đi spa làm mặt, đang xông hơi thì cái máy xông phụt mạnh một luồng hơi nóng vô má phải với bên cổ phải, "
      "em giật mình né ra liền. Chị nhân viên bảo da đỏ là do xông, bình thường, về đắp nha đam là hết. Mà giờ chỗ đó rát "
      "lắm, chắc cỡ 6/10.",
      {"burn_present": "YES", "burn_mechanism": "STEAM", "burn_location": "FACE_OR_NECK",
       "burn_skin_appearance": "BLISTERED", "burn_sensation": "PAINFUL_OR_BURNING", "smoke_or_fume_exposure": "NONE",
       "pain_present": "YES", "pain_severity": 6, "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("steam_exposure", "skin_blistering"), screen=QUIET,
      answers={"burn_present": "Em nghĩ là bỏng thật chứ hông phải đỏ do xông như chị spa nói, em soi gương thấy phồng "
                               "nước rồi.",
               "burn_mechanism": "Hơi nóng từ máy xông mặt phụt ra.",
               "burn_location": "Má phải với bên cổ phải.",
               "burn_skin_appearance": "Em vừa soi gương: má phải với bên cổ phải nổi mấy bóng nước nhỏ, da đỏ rực, hông "
                                       "phải đỏ thường.",
               "burn_sensation": "Rát lắm.",
               "smoke_or_fume_exposure": "Hông, em nín thở né ra liền nên hông hít phải hơi nóng.",
               "pain_present": "Có, chỗ bị hơi nóng phụt vô rát lắm.",
               "pain_severity": "Cỡ 6 trên 10.",
               "symptom_duration_bucket": "Hồi chiều, chừng ba tiếng trước."},
      confirmation="Em nói lại cho rõ: hông phải đỏ bình thường như chị spa nói đâu, em soi gương thấy má phải với bên cổ "
                   "phải phồng mấy bóng nước rồi, rát lắm.",
      conflict=("Nhân viên spa: da đỏ do xông, bình thường", "Người bệnh soi gương: phồng bóng nước ở má và cổ, là bỏng hơi nước"),
      tags=("contradiction", "minimization", "changed_answer", "dialect"),
      test="Lời trấn an của người ngoài trái với điều người bệnh tự thấy: bản đầu (đỏ do xông, không bỏng) là INCOMPLETE, bản "
           "đính chính (bỏng hơi nước phồng nước ở mặt cổ, không hít hơi nóng) là ESI 2 (khác k39 đợt 2: ở đó vị trí mặt bị "
           "rút lại)."),
    S("k45", "storm_branch_crush_cold_foot_no_diacritics", "Vợ gõ không dấu 'ban chan van lanh': đọc thành 'lành' hay 'lạnh' quyết định nhãn",
      P(52, "Male", "SPOUSE", chronic=("Tăng huyết áp",), meds=("Amlodipin 5 mg mỗi sáng",)),
      "Chong em 52 tuoi, sang nay don cay sau bao thi bi mot canh cay lon gay do de ngang cang tay trai voi bap chan trai, "
      "hang xom cua may chuc phut moi keo ra duoc. Cang tay trai bam tim, dau lam nhung van cu dong duoc, khong chay mau. "
      "Ban chan trai tu luc keo ra toi gio van lanh.",
      {"trauma_present": "YES", "trauma_mechanism": "CRUSH_INJURY",
       "upper_extremity_problem_present": "YES", "upper_extremity_injury_location": "FOREARM",
       "upper_extremity_injury_mechanism": "CRUSH", "upper_extremity_movement_ability": "LIMITED",
       "lower_extremity_problem_present": "YES", "lower_extremity_injury_location": "LOWER_LEG",
       "distal_limb_symptoms": "COLDNESS", "bleeding_present": "NO", "pain_present": "YES",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("upper_extremity_crush_injury", "lower_extremity_coldness"), screen=QUIET,
      answers={"trauma_present": "Co, bi canh cay gay do de len nguoi.",
               "trauma_mechanism": "Canh cay lon gay do de ngang tay voi chan, may chuc phut moi keo ra.",
               "upper_extremity_problem_present": "Co, cang tay trai bi de, bam tim.",
               "upper_extremity_injury_location": "O cang tay trai.",
               "upper_extremity_injury_mechanism": "Bi canh cay de len.",
               "upper_extremity_movement_ability": "Van cu dong duoc nhung dau.",
               "lower_extremity_problem_present": "Co, bap chan trai bi de.",
               "lower_extremity_injury_location": "O bap chan trai, cho canh cay de ngang.",
               "distal_limb_symptoms": "Lanh ngat nhu nuoc da, so vao lanh hon han ban chan phai, chu khong phai lanh lan dau.",
               "bleeding_present": "Khong chay mau.",
               "pain_present": "Co, anh ay keu dau tay voi chan.",
               "symptom_duration_bucket": "Tu 8 gio sang, toi gio duoc 5 tieng roi."},
      unknown={"pain_severity": "Anh ay khong cham diem duoc, hoi thi chi bao dau lam."},
      clarification="Y em la ban chan trai lanh ngat nhu nuoc da, so vao lanh hon han ban chan phai, chu khong phai van binh "
                    "thuong dau.",
      confirmation="Em noi lai cho ro: ban chan trai cua chong em lanh ngat nhu nuoc da tu luc keo ra, chu khong phai lanh lan "
                   "binh thuong.",
      conflict=("Lời kể không dấu: 'ban chan ... van lanh' (đọc được là 'vẫn lành' = bình thường)",
                "Làm rõ: 'lạnh ngắt như nước đá', lạnh hơn hẳn bàn chân bên kia"),
      tags=("contradiction", "no_diacritics", "ambiguous_wording", "caregiver", "comorbidity", "environmental"),
      test="Chữ không dấu 'lanh' có hai nghĩa ngược nhau: hiểu là 'lành' (bàn chân bình thường) thì đè dập cẳng tay chỉ là "
           "INCOMPLETE, hiểu đúng là 'lạnh' (bàn chân lạnh sau đè dập) thì là ESI 2, nên agent phải hỏi lại chứ không tự đoán."),
    S("k46", "hand_tractor_rollover_concealed_as_fall", "Ông nói tự té ruộng, hàng xóm kể máy cày tay lật đè tay chân, bàn chân tê",
      P(67, "Male", "OTHER", chronic=("Thay van hai lá cơ học",), meds=("Warfarin 3 mg mỗi tối",)),
      "Ông nội tui 67 tuổi, chiều ni đi cày về kể là tự té xuống ruộng, cẳng tay trái với bắp chân trái bầm tím, ông nói "
      "đau chừng 6. Chừ ông kêu bàn chân trái tê rần. Ông đang uống thuốc chống đông vì thay van tim.",
      {"trauma_present": "YES", "trauma_mechanism": "CRUSH_INJURY",
       "upper_extremity_problem_present": "YES", "upper_extremity_injury_location": "FOREARM",
       "upper_extremity_injury_mechanism": "CRUSH", "upper_extremity_sensory_change": "NONE",
       "upper_extremity_movement_ability": "LIMITED",
       "lower_extremity_problem_present": "YES", "lower_extremity_injury_location": "LOWER_LEG",
       "distal_limb_symptoms": "NUMBNESS", "limb_neurologic_symptoms": "NUMBNESS",
       "pain_present": "YES", "pain_severity": 6, "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("upper_extremity_crush_injury", "lower_extremity_numbness"), screen=QUIET,
      answers={"trauma_present": "Có, chú hàng xóm kể máy cày lật đè lên ông.",
               "trauma_mechanism": "Chú hàng xóm kéo ông lên mới kể: máy cày tay bị lật, đè lên ông chừng mười lăm phút, "
                                   "chớ không phải ông tự té. Ông sợ con cháu la nên giấu.",
               "upper_extremity_problem_present": "Có, cẳng tay trái bầm tím, đau.",
               "upper_extremity_injury_location": "Cẳng tay trái.",
               "upper_extremity_injury_mechanism": "Bị máy cày tay lật đè lên cẳng tay, không phải té.",
               "upper_extremity_sensory_change": "Tay thì không tê, chỉ bầm với đau.",
               "upper_extremity_movement_ability": "Tay co duỗi được nhưng đau.",
               "lower_extremity_problem_present": "Có, bắp chân trái bầm, bàn chân tê.",
               "lower_extremity_injury_location": "Bắp chân trái, chỗ máy đè ngang.",
               "distal_limb_symptoms": "Bàn chân trái tê rần, ông nói sờ vô như cách một lớp vải.",
               "limb_neurologic_symptoms": "Bàn chân trái tê rần từ lúc được kéo ra.",
               "pain_present": "Có, ông kêu đau tay với chân bên trái.",
               "pain_severity": "Ông nói đau chừng 6.",
               "symptom_duration_bucket": "Chuyện xảy ra chiều ni, chừng hai tiếng trước."},
      confirmation="Tui phải nói lại: ông nội tui không tự té mô, chú hàng xóm kể máy cày tay bị lật đè lên cẳng tay trái với "
                   "bắp chân trái của ông chừng mười lăm phút; ông sợ con cháu la nên giấu.",
      conflict=("Ông kể: tự té xuống ruộng", "Hàng xóm chứng kiến: máy cày tay lật đè lên tay và chân trái khoảng 15 phút"),
      tags=("contradiction", "collateral_history", "minimization", "progressive_disclosure", "older_adult", "anticoagulant",
            "caregiver", "dialect", "occupational"),
      test="Cơ chế chấn thương bị giấu và chỉ lộ ra khi hỏi lại: bản đầu (tự té, tê bàn chân) là INCOMPLETE, bản đính chính "
           "(máy cày lật đè tay và chân, bàn chân tê) là ESI 2, ở người đang dùng warfarin."),
    S("k47", "school_gate_crush_evolving_foot_ischemia", "Y tế trường khám lúc 7 giờ bảo chân bình thường; giáo viên khám lại thấy bàn chân lạnh, tê, tím",
      P(8, "Female", "OTHER"),
      "Tôi là giáo viên chủ nhiệm lớp 3. Khoảng 7 giờ sáng nay cánh cổng sắt trượt của trường bật khỏi ray, đổ đè ngang cẳng "
      "tay phải và bắp chân phải của một em học sinh lớp tôi, 8 tuổi; các thầy nâng cổng ra ngay. Cô y tế trường đã khám, "
      "bảo tay chân em chỉ bầm, bàn chân vẫn hồng, ấm, nên cho em nằm nghỉ ở phòng y tế chờ bố mẹ đến đón.",
      {"trauma_present": "YES", "trauma_mechanism": "CRUSH_INJURY",
       "upper_extremity_problem_present": "YES", "upper_extremity_injury_location": "FOREARM",
       "upper_extremity_injury_mechanism": "CRUSH", "upper_extremity_movement_ability": "NORMAL",
       "upper_extremity_sensory_change": "NONE",
       "lower_extremity_problem_present": "YES", "lower_extremity_injury_location": "LOWER_LEG",
       "distal_limb_symptoms": "MULTIPLE", "limb_neurologic_symptoms": "NUMBNESS",
       "pain_present": "YES", "pain_severity": 7, "symptom_trend": "WORSENING",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("upper_extremity_crush_injury", "lower_extremity_coldness", "lower_extremity_numbness"), screen=QUIET,
      answers={"trauma_present": "Có, em bị cổng sắt đổ đè.",
               "trauma_mechanism": "Cổng sắt trượt bật khỏi ray đổ đè lên em.",
               "upper_extremity_problem_present": "Có, cẳng tay phải bị cổng đè, bầm.",
               "upper_extremity_injury_location": "Cẳng tay phải.",
               "upper_extremity_injury_mechanism": "Cánh cổng sắt đổ đè ngang cẳng tay.",
               "upper_extremity_movement_ability": "Tay em vẫn cử động bình thường, cầm bút được.",
               "upper_extremity_sensory_change": "Tay không tê.",
               "lower_extremity_problem_present": "Có, bắp chân phải bị cổng đè.",
               "lower_extremity_injury_location": "Bắp chân phải, chỗ cổng đè ngang.",
               "distal_limb_symptoms": "Lúc 7 giờ cô y tế khám thì bàn chân vẫn hồng, ấm. Tôi vừa vào xem lại: giờ bàn chân "
                                       "phải lạnh hơn hẳn bên trái, mấy ngón chân tím tái, em kêu tê.",
               "limb_neurologic_symptoms": "Em kêu bàn chân phải tê, lúc sáng thì chưa tê.",
               "pain_present": "Có, em kêu đau bắp chân phải.",
               "pain_severity": "Giờ em nói đau chừng 7, lúc sáng chỉ khoảng 4.",
               "symptom_trend": "Nặng hơn: bắp chân đau tăng dần, bàn chân lúc sáng còn hồng ấm mà giờ lạnh, tím.",
               "symptom_duration_bucket": "Từ 7 giờ sáng, đến giờ hơn hai tiếng."},
      confirmation="Tôi phải sửa lại thông tin lúc 7 giờ: giờ bàn chân phải của em lạnh hơn hẳn chân trái, ngón chân tím tái, "
                   "em kêu tê và đau bắp chân tăng lên chừng 7.",
      conflict=("Y tế trường lúc 7 giờ: bàn chân hồng, ấm, chỉ bầm",
                "Giáo viên khám lại hơn hai giờ sau: bàn chân lạnh, tím, tê, đau tăng"),
      tags=("contradiction", "changed_answer", "collateral_history", "pediatric", "caregiver"),
      test="Phải dùng lần khám mới nhất chứ không dùng lần khám cũ: bản lúc 7 giờ (bàn chân hồng ấm, chỉ bầm) là INCOMPLETE, "
           "bản hiện tại (bàn chân lạnh, tím, tê, đau tăng sau đè dập) là ESI 2."),
    S("k48", "molten_aluminum_foot_painless_misread", "Thợ đúc nhôm tưởng hết rát là đỡ; chọc thử thì chỗ bỏng mất cảm giác, trắng xen cháy đen",
      P(38, "Male"),
      "Sáng nay tui đổ khuôn ở lò đúc nhôm, một vệt nhôm nóng chảy bắn trúng mu bàn chân trái, cháy lủng cái dép. Hồi đó rát "
      "dữ lắm, mà giờ hết rát rồi, chắc là đỡ. Mai tui đi làm lại được hông?",
      {"burn_present": "YES", "burn_mechanism": "HOT_OBJECT", "burn_location": "FOOT",
       "burn_skin_appearance": "MIXED_APPEARANCE", "burn_sensation": "NO_SENSATION",
       "burn_extent_estimate": "SMALL_LOCALIZED_AREA", "pain_present": "NO",
       "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("burn_injury",), screen=QUIET,
      answers={"burn_present": "Có, bị nhôm nóng chảy làm bỏng.",
               "burn_mechanism": "Vệt nhôm nóng chảy bắn trúng.",
               "burn_location": "Mu bàn chân trái.",
               "burn_skin_appearance": "Chỗ đó cỡ bao diêm, chỗ trắng bệch, chỗ cháy đen.",
               "burn_sensation": "Tui lấy cây tăm chọc thử rồi: chọc vô chỗ trắng hay chỗ đen gì cũng hông thấy gì hết.",
               "burn_extent_estimate": "Cỡ bao diêm.",
               "pain_present": "Giờ hông đau, hông rát gì hết.",
               "symptom_duration_bucket": "Hồi sáng, chừng 6 tiếng trước."},
      unknown={"symptom_trend": "Hết rát thì có, mà giờ tui hông biết vậy là đỡ hay nặng thêm nữa."},
      confirmation="Tui nói lại: hết rát hông phải là đỡ đâu, chỗ bỏng chọc vô hông còn cảm giác gì hết, da chỗ trắng bệch "
                   "chỗ cháy đen.",
      conflict=("Lời kể: hết rát nên tưởng đã đỡ", "Khi hỏi kỹ: hết rát vì chỗ bỏng mất cảm giác, da trắng bệch xen cháy đen"),
      tags=("contradiction", "changed_answer", "minimization", "occupational", "dialect"),
      test="Người bệnh hiểu nhầm 'hết rát' là đang khỏi rồi tự rút lại: bản đầu (đang đỡ, chưa tả da và cảm giác) là INCOMPLETE, "
           "bản đính chính (bỏng nhiều màu da, mất cảm giác) là ESI 2, nên agent không được ghi 'đang đỡ'."),
    S("k49", "banh_chung_pot_firelight_pale_scald", "Dưới ánh lửa tưởng bỏng đỏ hồng; soi đèn pin thấy hai cẳng chân và bụng trắng bệch",
      P(68, "Male", "PARENT", chronic=("Đái tháo đường type 2",), meds=("Metformin 500 mg ngày hai lần",)),
      "Tối nay nhà tôi luộc bánh chưng ngoài sân để mai làm giỗ, bố tôi 68 tuổi ngồi canh nồi thì cái kiềng gãy, nồi nước "
      "sôi đổ ụp vào hai cẳng chân với bụng bố. Tôi dội nước mát cho bố rồi, nhìn dưới ánh lửa thì da chỉ đỏ hồng thôi, bố "
      "kêu rát chừng 5/10. Chuyện mới chừng nửa tiếng.",
      {"burn_present": "YES", "burn_mechanism": "HOT_LIQUID", "burn_location": "MULTIPLE_AREAS",
       "burn_extent_estimate": "MULTIPLE_BODY_REGIONS", "burn_skin_appearance": "PALE_OR_WHITE",
       "burn_sensation": "PAINFUL_OR_BURNING", "pain_present": "YES", "pain_severity": 5,
       "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("scald_exposure", "burn_injury"), screen=QUIET,
      # Da trắng bệch trên nhiều vùng cũng khớp một nhánh của esi_2_multiple_regions_mixed_appearance; hai tiêu chí hoà
      # điểm và tiêu chí "mixed" thắng theo thứ tự chữ cái. Ca không có da nhiều màu nên ghim tiêu chí "pale" đúng tên.
      primary_atom="esi_2_multiple_regions_pale_burn",
      answers={"burn_present": "Có, bố tôi bị nước sôi làm bỏng.",
               "burn_mechanism": "Nồi nước sôi luộc bánh chưng đổ vào.",
               "burn_location": "Hai cẳng chân với bụng.",
               "burn_extent_estimate": "Cả hai cẳng chân với một mảng to ở bụng.",
               "burn_skin_appearance": "Hàng xóm mang đèn pin ra soi mới thấy không phải đỏ hồng như tôi nhìn dưới ánh lửa: chỗ "
                                       "bỏng ở hai cẳng chân với bụng trắng bệch, như da luộc.",
               "burn_sensation": "Bố kêu rát.",
               "pain_present": "Có, bố kêu rát chỗ bỏng.",
               "pain_severity": "Bố bảo rát chừng 5.",
               "symptom_duration_bucket": "Mới chừng nửa tiếng."},
      confirmation="Tôi sửa lại: soi đèn pin mới thấy chỗ bỏng ở hai cẳng chân và bụng bố tôi trắng bệch, không phải đỏ hồng "
                   "như lúc nhìn dưới ánh lửa.",
      conflict=("Nhìn dưới ánh lửa: da đỏ hồng", "Soi đèn pin: hai cẳng chân và bụng trắng bệch"),
      tags=("contradiction", "changed_answer", "collateral_history", "older_adult", "caregiver", "comorbidity"),
      test="Ánh sáng làm sai màu da: bản đầu (bỏng nước sôi nhiều vùng, đỏ hồng dưới ánh lửa) là INCOMPLETE, bản đính chính "
           "(nhiều vùng trắng bệch khi soi đèn pin) là ESI 2."),
    S("k50", "hearth_ember_perineal_burn_interpreter", "Cháu dịch nhầm 'lúc đó nóng rát' thành 'giờ vẫn rát': bỏng vùng kín của bà đã mất cảm giác",
      P(74, "Female", "OTHER"),
      "Bà nội em 74 tuổi, chỉ nói tiếng dân tộc, em dịch lại. Tối qua bà ngồi sưởi sát bếp lửa giữa nhà thì than hồng bắn "
      "vào làm váy bén lửa, cháy thủng một lỗ, bà bị bỏng ở vùng kín. Bà bảo chỗ đó nóng rát lắm.",
      {"burn_present": "YES", "burn_mechanism": "FLAME", "burn_location": "GENITAL_OR_PERINEAL",
       "burn_sensation": "NO_SENSATION", "pain_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("burn_injury",), screen=QUIET,
      answers={"burn_present": "Có, bà bị bỏng ở vùng kín.",
               "burn_mechanism": "Than hồng bắn vào làm váy bén lửa, cháy thủng một lỗ.",
               "burn_location": "Ở vùng kín của bà.",
               "burn_sensation": "Em hỏi lại bà cho kỹ: lúc than bắn vào thì nóng rát, còn giờ bà chạm tay vào chỗ bỏng thì "
                                 "không thấy gì cả. Lúc nãy em dịch nhầm.",
               "pain_present": "Giờ bà bảo không đau, chạm vào chỗ bỏng cũng không thấy gì.",
               "symptom_duration_bucket": "Từ tối qua, khoảng 9 giờ tối."},
      unknown={"burn_skin_appearance": "Bà không cho em xem chỗ đó, em là cháu trai nên cũng không tiện, em không biết da ra "
                                       "sao.",
               "burn_extent_estimate": "Em không được xem nên không biết vết bỏng rộng cỡ nào."},
      confirmation="Em xin sửa lại: lúc nãy em dịch nhầm, bà nói chỉ lúc than bắn vào mới nóng rát, còn giờ bà chạm vào chỗ "
                   "bỏng ở vùng kín thì không thấy gì cả.",
      conflict=("Cháu dịch lần đầu: chỗ bỏng 'nóng rát lắm' (hiểu là hiện tại)",
                "Dịch lại: rát là lúc bị, giờ chạm vào chỗ bỏng không có cảm giác"),
      tags=("contradiction", "changed_answer", "language_barrier", "older_adult", "caregiver", "null_unknown"),
      test="Người nhà dịch sai thì của lời bà: bản đầu (bỏng vùng kín còn đau rát) là INCOMPLETE, bản đính chính (bỏng vùng kín "
           "mất cảm giác) là ESI 2, và màu da chưa ai xem nên phải để là chưa biết chứ không coi là bình thường."),
    S("k51", "pregnancy_bp_cmhg_shorthand", "Chồng báo vợ thai 33 tuần 'huyết áp 17/10': cách nói tắt, thật ra là 170/100",
      P(27, "Female", "SPOUSE"),
      "Vợ tôi có bầu 33 tuần, ba hôm nay phù hai chân. Sáng nay khám thai ở trạm y tế xã, cô y sĩ đo huyết áp được 17/10, "
      "đo lại vẫn thế, bảo lên viện huyện. Vợ tôi không đau đầu, không nhìn mờ, con vẫn đạp đều. Có cần đi ngay không hay "
      "để chiều?",
      {"pregnancy_present": "YES", "pregnancy_status": "PREGNANT", "gestational_age_weeks": 33,
       "systolic_bp": 170, "diastolic_bp": 100, "swelling_present": "YES", "swelling_location": "OTHER",
       "headache_present": "NO", "vision_impairment_present": "NO", "fetal_movement_status": "NORMAL",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      2, concepts=("pregnancy", "hypertension", "swelling_in_pregnancy"), negated=("headache", "blurred_vision"),
      answers={"pregnancy_present": "Có, vợ tôi đang có bầu 33 tuần.",
               "pregnancy_status": "Vợ tôi đang có bầu.",
               "gestational_age_weeks": "Thai được 33 tuần.",
               "systolic_bp": "Số trên 170, tôi nói 17 là nói tắt kiểu ở quê.",
               "diastolic_bp": "Số dưới 100, tôi nói 10 là nói tắt.",
               "swelling_present": "Có, phù hai chân.",
               "swelling_location": "Phù ở hai bàn chân với cổ chân.",
               "headache_present": "Không đau đầu.",
               "vision_impairment_present": "Không, vợ tôi vẫn nhìn rõ.",
               "fetal_movement_status": "Con vẫn đạp đều như mọi hôm.",
               "symptom_duration_bucket": "Phù chân thì ba hôm nay, còn huyết áp cao thì sáng nay đo mới biết."},
      clarification="Ý tôi là 170 trên 100, ở quê tôi quen nói tắt là 17/10.",
      conflict=("Lời kể: huyết áp '17/10' (nói tắt theo cmHg; hiểu nguyên văn là 17 mmHg)", "Làm rõ: 170/100 mmHg"),
      tags=("units", "vitals_inconsistent", "regional_convention", "pregnancy", "caregiver"),
      test="Huyết áp nói tắt theo cmHg: hiểu nguyên văn 17 là tụt huyết áp cực nặng (ESI 1 sai), hiểu đúng 170/100 ở thai 33 "
           "tuần là ESI 2, nên agent phải hỏi lại chứ không ghi một con số vô lý."),
    S("k52", "bp_monitor_pulse_line_misread_af", "Con gái đọc nhầm dòng máy đo huyết áp: 'mạch 73' thật ra là số dưới, mạch là 146",
      P(77, "Female", "PARENT", chronic=("Tăng huyết áp",), meds=("Amlodipin 5 mg mỗi sáng",)),
      "Mẹ tôi 77 tuổi, từ trưa kêu tim đập loạn xạ trong ngực, người mệt, không đau ngực, không khó thở. Tôi đo bằng máy đo "
      "huyết áp điện tử ở nhà được 128/73, mạch 73, vậy chắc vẫn ổn phải không?",
      {"palpitation_present": "YES", "palpitation_pattern": "IRREGULAR", "cardiorespiratory_symptom_present": "YES",
       "heart_rate": 146, "systolic_bp": 128, "diastolic_bp": 73, "associated_systemic_symptoms": "GENERAL_WEAKNESS",
       "chest_pain_present": "NO", "dyspnea_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("palpitations", "tachycardia"), negated=("chest_pain", "shortness_of_breath"),
      answers={"palpitation_present": "Có, mẹ tôi thấy tim đập loạn xạ.",
               "palpitation_pattern": "Đập loạn xạ, không đều.",
               "cardiorespiratory_symptom_present": "Có, mẹ tôi thấy tim đập loạn trong ngực.",
               "heart_rate": "Tôi đọc nhầm dòng: 73 là số dưới của huyết áp; dòng dưới cùng có hình trái tim nhấp nháy mới là "
                             "mạch, máy báo 146.",
               "systolic_bp": "Số trên 128.",
               "diastolic_bp": "Số dưới 73.",
               "associated_systemic_symptoms": "Mẹ tôi thấy người mệt.",
               "chest_pain_present": "Không đau ngực.",
               "dyspnea_present": "Không khó thở.",
               "symptom_duration_bucket": "Từ trưa, chừng 5 tiếng rồi."},
      unknown={"symptom_onset": "Mẹ tôi ngủ trưa dậy mới thấy nên không biết nó đến đột ngột hay từ từ."},
      confirmation="Tôi phải sửa lại: mạch của mẹ tôi là 146 chứ không phải 73; 73 là số dưới của huyết áp, tôi đọc nhầm dòng.",
      conflict=("Lời kể: mạch 73 (chép lại số dưới của huyết áp)", "Đọc lại màn hình: mạch 146, có biểu tượng nhịp không đều"),
      tags=("contradiction", "vitals_inconsistent", "device_misread", "older_adult", "caregiver", "comorbidity"),
      test="Người nhà đọc nhầm dòng trên máy đo huyết áp: giữ mạch 73 thì hồi hộp không đều là INCOMPLETE, mạch đúng 146 kèm "
           "nhịp không đều ở người 77 tuổi là ESI 2."),
    S("k53", "hornet_stings_dark_urine_oliguria_collateral", "Bị ong vò vẽ đốt, ông nói tiểu bình thường, vợ kể từ tối mới tiểu một lần ít, sẫm",
      P(56, "Male", allergies=("Cefalexin",)),
      "Chiều qua tôi phát bờ rào bị cả đàn ong vò vẽ đốt, chắc phải hai chục nốt ở đầu, cổ với hai tay. Sáng nay người mệt "
      "rũ, nước tiểu sẫm như nước chè đặc, chắc tại nóng trong, chứ tiểu tiện vẫn bình thường. Con tôi lấy máy đo huyết áp "
      "được 94/60, mạch 104. Không thấy khó thở.",
      {"bite_or_sting_present": "YES", "bite_source": "INSECT", "urinary_symptom_present": "YES",
       "urine_appearance": "DARK", "urine_output_status": "REDUCED", "urination_status": "VERY_LITTLE_OR_NONE",
       "systolic_bp": 94, "diastolic_bp": 60, "heart_rate": 104, "associated_systemic_symptoms": "GENERAL_WEAKNESS",
       "dyspnea_present": "NO", "symptom_duration_bucket": "ONE_TO_24_HOURS"},
      2, concepts=("insect_sting", "dark_urine", "reduced_urine_output"), negated=("shortness_of_breath",), screen=QUIET,
      answers={"bite_or_sting_present": "Có, bị cả đàn ong vò vẽ đốt.",
               "bite_source": "Ong vò vẽ đốt.",
               "urinary_symptom_present": "Có, nước tiểu sẫm như nước chè đặc.",
               "urine_appearance": "Sẫm như nước chè đặc.",
               "urine_output_status": "Bà nhà tôi bảo từ tối qua tới giờ tôi mới đi tiểu có một lần, được ít; tôi cứ tưởng "
                                      "vẫn bình thường.",
               "urination_status": "Ít hơn hẳn, bà nhà tôi để ý từ tối qua tới giờ tôi mới tiểu một lần, được một ít.",
               "systolic_bp": "Con tôi đo được số trên 94.",
               "diastolic_bp": "Số dưới 60.",
               "heart_rate": "Máy báo mạch 104.",
               "associated_systemic_symptoms": "Người mệt rũ.",
               "dyspnea_present": "Không khó thở.",
               "symptom_duration_bucket": "Bị đốt từ khoảng 5 giờ chiều qua."},
      confirmation="Tôi nói lại cho đúng: bà nhà tôi bảo từ tối qua tới giờ tôi mới đi tiểu một lần, được ít, nước sẫm đặc, "
                   "chứ không phải tiểu bình thường như tôi nói.",
      conflict=("Người bệnh: tiểu tiện vẫn bình thường", "Vợ để ý: từ tối qua mới tiểu một lần, rất ít, sẫm đặc"),
      tags=("contradiction", "collateral_history", "minimization", "changed_answer", "hidden_red_flag"),
      test="Lời vợ về lượng nước tiểu bác bỏ lời người bệnh: bản đầu (tiểu bình thường, huyết áp 94) là INCOMPLETE, bản đính "
           "chính (tiểu rất ít, sẫm màu, huyết áp 94 sau khi bị ong vò vẽ đốt nhiều nốt) là ESI 2."),
    S("k54", "oximeter_nail_polish_cold_hands_artifact", "Máy SpO2 báo 82% do tay lạnh và sơn móng sẫm; đo lại đúng cách 97%, không khó thở",
      P(66, "Female", "PARENT"),
      "Mẹ em 66 tuổi bị sổ mũi, ho khan lai rai 3 hôm, không sốt, vẫn đi chợ nấu cơm bình thường. Em mới mua máy kẹp ngón "
      "tay, đo thử thì ra 82%, em hoảng quá. Nhưng lúc đó mẹ vừa rửa rau bằng nước lạnh, tay lạnh ngắt, móng lại sơn màu đỏ "
      "đô sẫm; em lau sạch sơn, ủ ấm tay rồi đo lại ngón khác thì được 97%, đo mấy lần đều 97, 98. Mẹ em vẫn nói chuyện bình "
      "thường, không khó thở.",
      {"spo2": 97, "cough_present": "YES", "cough_character": "DRY", "runny_nose_present": "YES", "fever_present": "NO",
       "dyspnea_present": "NO", "cardiorespiratory_symptom_present": "NO", "functional_status": "NORMAL",
       "symptom_duration_bucket": "ONE_TO_7_DAYS"},
      INCOMPLETE, concepts=("cough", "runny_nose"), negated=("shortness_of_breath", "fever"), screen=QUIET,
      answers={"spo2": "Đo lại đúng cách thì 97%; số 82% lúc đầu là lúc tay mẹ lạnh ngắt, móng còn sơn sẫm.",
               "cough_present": "Có, ho khan lai rai.",
               "cough_character": "Ho khan.",
               "runny_nose_present": "Có, sổ mũi.",
               "fever_present": "Không sốt.",
               "dyspnea_present": "Không khó thở.",
               "cardiorespiratory_symptom_present": "Không, mẹ em không khó thở.",
               "functional_status": "Mẹ em vẫn đi chợ, nấu cơm bình thường.",
               "symptom_duration_bucket": "Ba hôm nay."},
      conflict=("Lần đo đầu: SpO2 82% (tay lạnh ngắt, móng sơn sẫm)",
                "Đo lại ở ngón đã lau sơn, tay đã ủ ấm: 97-98%, không khó thở"),
      tags=("contradiction", "vitals_inconsistent", "measurement_artifact", "negation", "older_adult", "caregiver"),
      test="Số đo nhiễu được người nhà đo lại ngay trong lời kể: giữ 82% là ESI 1 sai, bản đúng (SpO2 97%, cảm thông thường, "
           "không khó thở) không khớp tiêu chí nào nên là INCOMPLETE (khác k04, k19: ở đây không có triệu chứng hô hấp nặng "
           "nào đi kèm số thấp)."),
    S("k55", "dorm_antihistamine_accident_then_intent", "Bạn cùng phòng nói uống nhầm thuốc, sau đó bạn ấy thừa nhận cố ý uống",
      P(17, "Female", "OTHER"),
      "Bạn cùng phòng ký túc xá của em 17 tuổi uống nhầm mấy viên thuốc chống dị ứng của em, bạn ấy bảo tưởng là viên "
      "vitamin. Chuyện khoảng 40 phút trước. Giờ bạn ấy vẫn tỉnh, nói chuyện bt, ko uống rượu bia gì.",
      {"toxic_exposure_present": "YES", "toxic_substance_category": "MEDICATION", "toxic_exposure_route": "INGESTION",
       "estimated_exposure_amount": "MODERATE", "exposure_intent": "INTENTIONAL_SELF_HARM", "coingestion_status": "NONE",
       "altered_mental_status_present": "NO", "symptom_duration_bucket": "UNDER_1_HOUR"},
      2, concepts=("intentional_ingestion", "medication_ingestion"), screen=QUIET,
      answers={"toxic_exposure_present": "Có, bạn ấy uống mấy viên thuốc chống dị ứng của em.",
               "toxic_substance_category": "Thuốc chống dị ứng của em.",
               "toxic_exposure_route": "Uống.",
               "estimated_exposure_amount": "Bạn ấy nói uống 6 viên, vỉ 10 viên giờ còn 4, khá nhiều.",
               "exposure_intent": "Lúc đầu bạn ấy bảo uống nhầm, nhưng vừa rồi bạn ấy khóc và nói thật là cố ý uống vì "
                                  "chuyện buồn.",
               "coingestion_status": "Ko uống rượu bia hay thuốc gì khác.",
               "altered_mental_status_present": "Ko, bạn ấy vẫn tỉnh, nói chuyện bt.",
               "symptom_duration_bucket": "Khoảng 40 phút trước."},
      unknown={"self_safety_status": "Em ko biết, bạn ấy chỉ khóc, ko nói gì thêm."},
      confirmation="Em phải sửa lại: bạn em ko uống nhầm đâu, bạn ấy vừa nói thật là cố ý uống 6 viên thuốc chống dị ứng của "
                   "em vì chuyện buồn.",
      conflict=("Lời kể: uống nhầm vì tưởng là vitamin", "Bạn thừa nhận: cố ý uống 6 viên vì chuyện buồn"),
      tags=("contradiction", "collateral_history", "progressive_disclosure", "changed_answer", "mental_health", "adolescent",
            "abbreviation"),
      test="Ý định tự hại chỉ lộ ra khi bạn cùng phòng kể lại lời thú nhận: bản đầu (uống nhầm vài viên) là INCOMPLETE, bản đính "
           "chính (cố ý uống thuốc để tự hại) là ESI 2, nên agent phải cập nhật ý định chứ không giữ 'uống nhầm'."),
]
