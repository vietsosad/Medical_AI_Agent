"""Câu trả lời tự nhiên của người bệnh cho từng giá trị dữ kiện.

Kịch bản chỉ ghi ``fact -> giá trị`` theo đúng enum của corpus. Khi agent hỏi tới
một dữ kiện mà người viết không soạn câu trả lời riêng, câu trả lời lấy từ đây.
Mỗi giá trị có vài cách nói; cách nào được dùng do băm ổn định ``case_id + fact``
quyết định, nên cùng một bộ dữ liệu luôn sinh lại đúng như cũ.

Bảng này cố ý KHÔNG có nhánh dự phòng: giá trị nào thiếu câu nói thì
``build_dataset.py`` dừng và liệt kê ra, thay vì để lọt chữ tiếng Anh của enum
vào lời người bệnh (lỗi từng làm hỏng 97/300 ca của bộ mở rộng cũ).
"""

from __future__ import annotations

import hashlib
from typing import Any

YES = ("Có ạ.", "Dạ có.", "Có.", "Có, đúng vậy.")
NO = ("Không ạ.", "Dạ không.", "Không.", "Không có.")
UNKNOWN_DEFAULT = "Tôi chưa rõ thông tin này."

#: Câu có/không riêng cho dữ kiện mà "Có." trơn nghe lạ hoặc dễ hiểu sai.
YES_NO_OVERRIDES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "pregnancy_present": (("Dạ có, em đang có thai.",), ("Không, em không có thai.",)),
    "uterine_contractions_present": (("Có, bụng gò cứng từng cơn.",), ("Không thấy gò.",)),
}

#: Dữ kiện YES/NO/UNKNOWN dùng chung câu trả lời có/không.
_YES_NO_FACTS = {
    "abdominal_pain_present", "altered_mental_status_present", "back_or_spinal_problem_present",
    "bite_or_sting_present", "bleeding_present", "blood_in_stool_present", "burn_present",
    "cardiorespiratory_symptom_present", "chemotherapy_history_present", "chest_pain_present",
    "chills_present", "cold_exposure_present", "constipation_or_defecation_problem_present",
    "cough_present", "cyanosis_present", "dental_problem_present", "dental_trauma_present",
    "diarrhea_present", "dizziness_present", "drooling_present", "dysphagia_present",
    "dyspnea_present", "ent_bleeding_present", "ent_foreign_body_present", "epistaxis_present",
    "epistaxis_pressure_attempted", "eye_injury_present", "eye_problem_present",
    "facial_swelling_present", "fever_present", "gastrointestinal_symptom_present",
    "genital_discharge_present", "genital_symptom_present", "genitourinary_pain_present",
    "headache_present", "heat_exposure_present", "hemoptysis_present",
    "immunocompromised_state_present", "itching_present", "joint_pain_present",
    "lower_extremity_problem_present", "mucosal_involvement_present", "nasal_congestion_present",
    "neck_stiffness_present", "neck_swelling_present", "noisy_breathing_present",
    "oral_bleeding_present", "oral_discharge_present", "oral_pain_present", "oral_problem_present",
    "pain_present", "palpitation_present", "perceptual_disturbance_present", "pregnancy_present",
    "rash_or_skin_finding_present", "recent_head_trauma", "runny_nose_present",
    "seizure_occurrence", "seizure_present", "similar_symptoms_in_others", "sore_throat_present",
    "sputum_present", "suspected_trigger_exposure_present", "swelling_present", "syncope_present",
    "thermal_exposure_present", "tongue_swelling_present", "toxic_exposure_present",
    "trauma_present", "upper_extremity_problem_present", "urinary_symptom_present",
    "uterine_contractions_present", "vaginal_bleeding_present", "vision_impairment_present",
    "visible_deformity_present", "visual_disturbance_present", "vomiting_or_feeding_problem_present",
    "vomiting_present", "wound_present",
}

#: Câu nói cho từng giá trị enum, theo dữ kiện.
VALUE_PHRASES: dict[str, dict[str, tuple[str, ...]]] = {
    "chest_pain_quality": {
        "PRESSURE": ("Như có tảng đá đè lên ngực.", "Cảm giác bị đè ép ở ngực."),
        "TIGHTNESS": ("Thắt chặt, bó lại ở ngực.", "Như bị ai siết chặt ngực."),
        "HEAVINESS": ("Nặng trĩu ở ngực.", "Cảm giác nặng nề trong ngực."),
        "SHARP": ("Nhói như kim đâm.", "Đau nhói từng cái."),
        "BURNING": ("Nóng rát sau xương ức.", "Rát rát như bị bỏng trong ngực."),
        "ACHING": ("Đau âm ỉ.", "Ê ẩm, âm ỉ thôi."),
    },
    "chest_pain_location": {
        "CENTRAL": ("Ở giữa ngực.", "Ngay giữa ngực, sau xương ức."),
        "LEFT_CHEST": ("Bên ngực trái.", "Phía ngực trái."),
        "RIGHT_CHEST": ("Bên ngực phải.",),
        "DIFFUSE": ("Khắp cả ngực.",),
    },
    "chest_pain_radiation": {
        "NONE": ("Không lan đi đâu.", "Chỉ đau tại chỗ, không lan."),
        "LEFT_ARM": ("Lan xuống cánh tay trái.", "Có lan ra tay trái."),
        "JAW": ("Lan lên hàm.", "Lan lên cằm với hàm."),
        "BACK": ("Lan ra sau lưng.", "Xuyên ra sau lưng."),
        "SHOULDER": ("Lan lên vai.",),
        "NECK": ("Lan lên cổ.",),
        "MULTIPLE": ("Lan cả lên vai, xuống tay và lên hàm.",),
        "BOTH_ARMS": ("Lan xuống cả hai tay.",),
    },
    "breathing_relation": {
        "WORSE_WITH_DEEP_BREATH": ("Hít sâu vào là đau hơn.", "Thở mạnh thì đau tăng."),
        "WORSE_WITH_COUGH": ("Ho thì đau hơn.",),
        "WORSE_WITH_BOTH": ("Cả hít sâu lẫn ho đều đau hơn.",),
        "NO_CLEAR_RELATION": ("Hít thở không thấy thay đổi gì.", "Không liên quan đến thở."),
    },
    "exertional_relation": {
        "TRIGGERED_BY_EXERTION": ("Đi lại, leo cầu thang là bị.", "Gắng sức là xuất hiện."),
        "WORSE_WITH_EXERTION": ("Vận động thì nặng hơn.",),
        "NOT_RELATED_TO_EXERTION": ("Không liên quan, ngồi yên cũng vậy mà đi lại cũng vậy.",),
        "OCCURS_AT_REST": ("Đang ngồi nghỉ cũng bị.", "Nằm nghỉ cũng bị."),
    },
    "dyspnea_context": {
        "AT_REST": ("Ngồi yên cũng thấy khó thở.",),
        "WITH_EXERTION": ("Chỉ khi đi lại, làm việc nặng.",),
        "WHEN_LYING_FLAT": ("Nằm xuống là khó thở, phải kê gối cao.",),
        "MULTIPLE_CONTEXTS": ("Lúc nghỉ cũng khó thở, nằm xuống còn khó hơn.",),
    },
    "respiratory_distress_symptoms": {
        "NONE": ("Không khó thở.",),
        "WITH_ACTIVITY": ("Chỉ khó thở khi đi lại nhanh.", "Đi bộ một đoạn là hụt hơi."),
        "AT_REST": ("Ngồi nghỉ cũng thấy khó thở.", "Ngồi yên vẫn thở không đủ hơi."),
        "SEVERE_OR_UNABLE_TO_SPEAK_NORMALLY": ("Khó thở đến mức nói không hết câu.",),
    },
    "breathing_sound": {
        "WHEEZING": ("Có tiếng khò khè.", "Thở nghe khò khè."),
        "STRIDOR_LIKE": ("Hít vào có tiếng rít.",),
        "OTHER_NOISY_BREATHING": ("Thở nghe ồ ồ lạ lắm.",),
        "NONE": ("Không có tiếng gì lạ.",),
    },
    "cough_character": {
        "DRY": ("Ho khan.", "Ho khan, không có đờm."),
        "PRODUCTIVE": ("Ho có đờm.",),
        "MIXED": ("Lúc ho khan lúc có đờm.",),
    },
    "sputum_appearance": {
        "CLEAR_OR_WHITE": ("Đờm trắng trong.",),
        "YELLOW_OR_GREEN": ("Đờm vàng xanh.", "Đờm đặc màu xanh."),
        "BLOOD_STREAKED": ("Đờm có lẫn vài tia máu.",),
    },
    "hemoptysis_amount": {
        "STREAKS_OR_SPECKS": ("Chỉ vài vệt máu nhỏ lẫn trong đờm.",),
        "SMALL_AMOUNT": ("Một ít máu, chừng một thìa cà phê.",),
        "MODERATE_OR_LARGE_AMOUNT": ("Ho ra cả ngụm máu.",),
    },
    "allergic_reaction_features": {
        "NONE": ("Không nổi mẩn, không sưng gì.",),
        "RASH_OR_ITCHING": ("Có nổi mẩn ngứa.",),
        "FACIAL_OR_LIP_SWELLING": ("Môi với mặt sưng lên.",),
        "TONGUE_SWELLING": ("Lưỡi sưng to.",),
        "MULTIPLE_FEATURES": ("Vừa nổi mẩn vừa sưng môi sưng mặt.",),
    },
    "focal_neurologic_symptoms": {
        "NONE": ("Không yếu tay chân, không méo miệng, nói bình thường.", "Không có gì như vậy."),
        "WEAKNESS_OR_NUMBNESS": ("Tay chân một bên tê yếu.", "Có yếu một bên tay."),
        "FACIAL_ASYMMETRY": ("Miệng bị méo sang một bên.", "Mặt lệch một bên."),
        "SPEECH_OR_LANGUAGE_CHANGE": ("Nói ngọng, nói khó.", "Nói líu lưỡi."),
        "VISION_CHANGE": ("Mắt nhìn mờ hẳn đi.",),
        "MULTIPLE": ("Vừa méo miệng, vừa nói ngọng, tay cũng yếu.", "Có mấy cái cùng lúc: yếu tay, nói khó."),
    },
    "dizziness_sensation": {
        "SPINNING": ("Quay cuồng như mọi thứ xoay tròn.",),
        "LIGHTHEADED": ("Lâng lâng, choáng váng.",),
        "IMBALANCE": ("Đi đứng không vững.",),
        "NONSPECIFIC": ("Khó tả, cứ choáng choáng.",),
    },
    "headache_location": {
        "FRONTAL": ("Đau vùng trán.",),
        "TEMPORAL": ("Đau hai bên thái dương.",),
        "UNILATERAL": ("Đau một bên đầu.", "Đau nửa đầu bên phải."),
        "OCCIPITAL": ("Đau vùng sau gáy.",),
        "GLOBAL": ("Đau khắp cả đầu.",),
        "AROUND_EYE": ("Đau quanh hốc mắt.",),
    },
    "headache_character": {
        "THROBBING": ("Đau giật giật theo nhịp mạch.",),
        "SHARP": ("Đau nhói như dao đâm.",),
        "PRESSURE": ("Nặng đầu, như bị ép.",),
        "TIGHTNESS": ("Căng như bị đai siết quanh đầu.",),
        "DULL": ("Đau âm ỉ.",),
    },
    "syncope_context": {
        "DURING_EXERTION": ("Đang chạy, đang gắng sức thì bị.",),
        "WHILE_STANDING": ("Đang đứng yên thì bị.",),
        "AFTER_STANDING_UP": ("Vừa đứng dậy thì bị.",),
        "AT_REST": ("Đang ngồi nghỉ thì bị.",),
        "WHILE_SITTING": ("Đang ngồi thì bị.",),
    },
    "vomit_appearance": {
        "FOOD_CONTENT": ("Nôn ra thức ăn.", "Toàn thức ăn chưa tiêu."),
        "CLEAR_FLUID": ("Nôn ra nước trong.",),
        "YELLOW_GREEN": ("Nôn ra dịch vàng xanh, đắng.",),
        "BLOODY": ("Nôn ra máu đỏ.", "Có máu tươi trong chất nôn."),
        "DARK_COFFEE_GROUND_LIKE": ("Nôn ra chất đen như bã cà phê.",),
    },
    "vomiting_frequency": {
        "ONCE": ("Nôn một lần.",),
        "FEW_TIMES": ("Nôn vài lần.", "Vài lần thôi."),
        "REPEATED": ("Nôn liên tục, uống gì nôn nấy.", "Nôn đi nôn lại nhiều lần."),
    },
    "stool_appearance": {
        "NORMAL": ("Phân bình thường.",),
        "WATERY": ("Phân toàn nước.",),
        "LOOSE": ("Phân lỏng, nát.",),
        "HARD": ("Phân cứng.",),
        "BLACK": ("Phân đen như hắc ín.", "Đi ngoài phân đen, mùi rất khắm."),
        "RED_BLOOD": ("Có máu đỏ tươi lẫn trong phân.",),
    },
    "blood_in_stool_amount": {
        "TRACE": ("Chỉ dính chút máu trên giấy vệ sinh.",),
        "NOTICEABLE": ("Thấy rõ máu lẫn trong phân.",),
        "LARGE_AMOUNT": ("Ra nhiều máu, đỏ cả bồn cầu.",),
    },
    "abdominal_pain_location": {
        "UPPER_ABDOMEN": ("Vùng trên rốn, chỗ thượng vị.", "Bụng trên."),
        "LOWER_ABDOMEN": ("Bụng dưới.", "Vùng dưới rốn."),
        "RIGHT_SIDE": ("Bên phải, phía dưới.", "Hố chậu bên phải."),
        "LEFT_SIDE": ("Bên trái.",),
        "AROUND_UMBILICUS": ("Quanh rốn.",),
        "GENERALIZED": ("Đau khắp bụng.",),
    },
    "abdominal_pain_character": {
        "DULL": ("Đau âm ỉ.",),
        "CRAMPING": ("Quặn từng cơn.", "Đau quặn thắt từng đợt."),
        "BURNING": ("Nóng rát.",),
        "SHARP": ("Đau nhói.",),
        "PRESSURE": ("Căng tức, đầy bụng.",),
    },
    "abdominal_pain_radiation": {
        "NONE": ("Không lan đi đâu.",),
        "BACK": ("Lan ra sau lưng.", "Xuyên ra sau lưng như đai."),
        "CHEST": ("Lan lên ngực.",),
        "SHOULDER": ("Lan lên vai.",),
        "GROIN": ("Lan xuống bẹn.",),
    },
    "meal_relationship": {
        "WORSE_AFTER_EATING": ("Ăn xong là đau hơn.",),
        "BETTER_AFTER_EATING": ("Ăn vào thì đỡ.",),
        "WORSE_WHEN_HUNGRY": ("Đói thì đau hơn.",),
        "NO_CLEAR_RELATION": ("Không thấy liên quan ăn uống.",),
        "UNABLE_TO_EAT": ("Không ăn được gì.",),
    },
    "oral_intake_tolerance": {
        "NORMAL": ("Vẫn ăn uống bình thường.", "Ăn uống được như mọi ngày."),
        "REDUCED": ("Ăn ít hơn hẳn mọi ngày.", "Ăn uống kém."),
        "LIQUIDS_ONLY": ("Chỉ uống được nước, ăn không nổi.",),
        "UNABLE_TO_KEEP_DOWN": ("Uống ngụm nước cũng nôn ra.", "Ăn uống gì cũng nôn hết."),
    },
    "stool_consistency": {
        "PELLET_LIKE": ("Phân nhỏ như phân dê.",),
        "HARD_LUMPY": ("Phân cứng vón cục.",),
        "FORMED": ("Phân thành khuôn bình thường.",),
        "SOFT": ("Phân mềm.",),
        "LOOSE": ("Phân lỏng.",),
        "WATERY": ("Phân như nước.",),
    },
    "defecation_effort": {
        "NO_DIFFICULTY": ("Không phải rặn.",),
        "SOME_STRAINING": ("Phải rặn một chút.",),
        "MARKED_STRAINING": ("Rặn rất mạnh mới ra.",),
        "UNABLE_TO_DEFECATE": ("Rặn mãi không đi được.",),
    },
    "evacuation_completeness": {
        "COMPLETE": ("Đi hết rồi.",),
        "INCOMPLETE": ("Đi xong vẫn thấy chưa hết.",),
        "NO_STOOL_PASSED": ("Không đi ra được tí nào.",),
    },
    "gas_passage_status": {
        "NORMAL": ("Vẫn xì hơi bình thường.",),
        "REDUCED": ("Xì hơi ít hơn hẳn.",),
        "ABSENT": ("Không xì hơi được chút nào.",),
    },
    "fluid_retention": {
        "ABLE_TO_KEEP_FLUIDS": ("Uống vào vẫn giữ được.",),
        "PARTIALLY_ABLE": ("Uống được một ít, lúc nôn lúc không.",),
        "VOMITS_MOST_INTAKE": ("Uống vào nôn ra gần hết.",),
        "UNABLE_TO_KEEP_FLUIDS": ("Bú hay uống gì vào cũng nôn ra hết.",),
    },
    "dehydration_visible_signs": {
        "NONE": ("Không thấy môi khô, vẫn có nước mắt.",),
        "MILD_SIGNS": ("Môi hơi khô một chút.",),
        "MULTIPLE_SIGNS": ("Môi khô, khóc không có nước mắt.",),
        "PRONOUNCED_SIGNS": ("Môi khô nứt, mắt trũng sâu, khóc không ra nước mắt.",),
    },
    "activity_level": {
        "NORMAL": ("Vẫn chơi, tương tác bình thường.",),
        "LESS_ACTIVE": ("Ít chơi hơn, hay nằm.",),
        "VERY_INACTIVE": ("Mệt lả, nằm im.",),
        "DIFFICULT_TO_AROUSE": ("Ngủ li bì, gọi mãi mới mở mắt.",),
    },
    "feeding_intake_level": {
        "NORMAL": ("Bú, ăn như mọi ngày.",),
        "MILDLY_REDUCED": ("Bú ít hơn một chút.",),
        "MARKEDLY_REDUCED": ("Bú ít hẳn, chỉ được vài ngụm.",),
        "REFUSES_OR_UNABLE": ("Bỏ bú hoàn toàn.",),
    },
    "urine_output_level": {
        "NORMAL": ("Vẫn đi tiểu như mọi ngày.",),
        "REDUCED": ("Tã ướt ít hơn bình thường.",),
        "VERY_REDUCED": ("Cả buổi mới ướt một cái tã.",),
        "NO_URINE": ("Từ sáng đến giờ không thấy tè.",),
    },
    "urination_status": {
        "NORMAL": ("Đi tiểu bình thường.",),
        "DECREASED": ("Đi tiểu ít hơn hẳn.",),
        "VERY_LITTLE_OR_NONE": ("Gần như không đi tiểu.",),
    },
    "urine_output_status": {
        "NORMAL": ("Tiểu bình thường.",),
        "REDUCED": ("Tiểu ít hơn bình thường.",),
        "NONE": ("Không tiểu được giọt nào.",),
    },
    "urine_appearance": {
        "NORMAL": ("Nước tiểu bình thường.",),
        "CLOUDY": ("Nước tiểu đục.",),
        "DARK": ("Nước tiểu sẫm màu.",),
        "PINK_OR_RED": ("Nước tiểu hồng đỏ.", "Nước tiểu có màu đỏ như nước rửa thịt."),
        "BLOOD_CLOTS": ("Có cục máu trong nước tiểu.",),
    },
    "voiding_ability": {
        "NORMAL": ("Tiểu bình thường.",),
        "REDUCED": ("Tiểu ít, khó ra.",),
        "DROPS_ONLY": ("Chỉ ra vài giọt.",),
        "UNABLE_DESPITE_URGE": ("Buồn tiểu căng mà không tiểu ra được.",),
    },
    "genitourinary_pain_location": {
        "FLANK": ("Đau ở hông lưng.", "Đau vùng thắt lưng, bên hông."),
        "LOWER_ABDOMEN": ("Đau bụng dưới.",),
        "SUPRAPUBIC": ("Đau trên xương mu.",),
        "GROIN": ("Đau ở bẹn.",),
        "URETHRAL": ("Buốt rát ở đường tiểu.",),
        "TESTICULAR": ("Đau ở tinh hoàn.",),
        "SCROTAL": ("Đau ở bìu.",),
    },
    "genitourinary_pain_laterality": {
        "LEFT": ("Bên trái.",), "RIGHT": ("Bên phải.",), "BILATERAL": ("Cả hai bên.",),
        "MIDLINE": ("Ở giữa.",),
    },
    "genitourinary_pain_radiation": {
        "NONE": ("Không lan.",),
        "TO_GROIN": ("Lan xuống bẹn.",),
        "TO_LOWER_ABDOMEN": ("Lan xuống bụng dưới.",),
        "TO_GENITALS": ("Lan xuống bộ phận sinh dục.",),
    },
    "symptom_onset": {
        "SUDDEN": ("Đột ngột, đang bình thường thì bị.", "Xảy ra rất nhanh, chỉ trong vài giây."),
        "GRADUAL": ("Từ từ tăng dần.", "Bị từ từ chứ không đột ngột."),
    },
    "symptom_duration_bucket": {
        "UNDER_1_HOUR": ("Mới chưa đến một tiếng.",),
        "ONE_TO_24_HOURS": ("Mới mấy tiếng nay thôi.", "Chưa tới một ngày."),
        "ONE_TO_7_DAYS": ("Được vài ngày rồi.", "Mấy hôm nay rồi."),
        "OVER_7_DAYS": ("Hơn một tuần rồi.",),
    },
    "symptom_trend": {
        "CONSTANT": ("Vẫn vậy, không tăng không giảm.",),
        "INTERMITTENT": ("Lúc có lúc không.",),
        "WORSENING": ("Ngày càng nặng hơn.", "Nặng dần lên."),
        "IMPROVING": ("Đang đỡ dần.",),
    },
    "fever_pattern": {
        "CONTINUOUS": ("Sốt liên tục.",),
        "INTERMITTENT": ("Sốt từng cơn.",),
        "RECURRENT": ("Hạ rồi lại sốt lại.",),
    },
    "infection_source_symptom_group": {
        "RESPIRATORY": ("Chủ yếu là ho.",),
        "URINARY": ("Chủ yếu tiểu buốt.",),
        "GASTROINTESTINAL": ("Chủ yếu đau bụng, tiêu chảy.",),
        "SKIN_SOFT_TISSUE": ("Chỗ da bị sưng nóng đỏ.",),
        "MULTIPLE": ("Nhiều chỗ khó chịu cùng lúc.",),
        "NONE_CLEAR": ("Không thấy khó chịu chỗ nào rõ ràng, chỉ sốt thôi.",),
    },
    "associated_systemic_symptoms": {
        "NONE": ("Không sốt, không rét run.",),
        "FEVER": ("Có sốt.",),
        "CHILLS": ("Có rét run.",),
        "GENERAL_WEAKNESS": ("Mệt rã rời toàn thân.",),
        "MULTIPLE_SYMPTOMS": ("Vừa sốt vừa rét run, mệt lả.",),
    },
    "functional_status": {
        "NORMAL": ("Vẫn sinh hoạt bình thường.",),
        "REDUCED": ("Mệt hơn, làm việc nhẹ thôi.",),
        "MARKEDLY_REDUCED": ("Mệt đến mức chỉ nằm.",),
        "UNABLE_TO_AMBULATE": ("Không tự đi lại nổi.",),
    },
    "trauma_mechanism": {
        "FALL": ("Bị ngã.",),
        "MOTOR_VEHICLE_COLLISION": ("Tai nạn ô tô.",),
        "MOTORCYCLE_COLLISION": ("Tai nạn xe máy.", "Đi xe máy bị va quẹt ngã."),
        "BICYCLE_COLLISION": ("Ngã xe đạp.",),
        "SPORTS_INJURY": ("Chấn thương lúc chơi thể thao.",),
        "DIRECT_BLOW": ("Bị va đập trực tiếp.",),
        "ASSAULT": ("Bị đánh.",),
        "CRUSH_INJURY": ("Bị vật nặng đè.",),
        "PENETRATING_INJURY": ("Bị vật nhọn đâm.",),
    },
    "injury_region": {
        "HEAD": ("Ở đầu.",), "NECK": ("Ở cổ.",), "UPPER_BACK": ("Lưng trên.",),
        "LOWER_BACK": ("Thắt lưng.",), "ENTIRE_BACK": ("Cả lưng.",),
        "MULTIPLE_REGIONS": ("Nhiều chỗ.",),
    },
    "post_trauma_awareness_change": {
        "NONE": ("Không ngất, vẫn nhớ hết mọi chuyện.", "Tỉnh táo suốt, nhớ rõ."),
        "LOSS_OF_CONSCIOUSNESS": ("Có lịm đi một lúc.",),
        "MEMORY_GAP": ("Không nhớ lúc ngã xảy ra thế nào.",),
        "CONFUSION": ("Sau đó cứ lơ mơ, hỏi đi hỏi lại.",),
        "MULTIPLE": ("Lịm đi một lúc, tỉnh dậy thì lú lẫn, không nhớ gì.",),
    },
    "visible_head_injury_sign": {
        "NONE": ("Không thấy sưng hay chảy máu gì.",),
        "SCALP_SWELLING": ("Có u một cục trên đầu.",),
        "SCALP_WOUND": ("Có vết rách trên da đầu.",),
        "PERIORBITAL_BRUISING": ("Bầm tím quanh hai mắt.",),
        "MASTOID_BRUISING": ("Bầm tím sau tai.",),
        "EAR_BLEEDING": ("Có máu chảy ra từ tai.",),
        "CLEAR_FLUID_LEAK": ("Có nước trong chảy ra từ mũi.",),
    },
    "limb_neurologic_symptoms": {
        "NONE": ("Tay chân không tê, không yếu.",),
        "NUMBNESS": ("Tê tay chân.",),
        "TINGLING": ("Châm chích ở chân.",),
        "WEAKNESS": ("Chân yếu hẳn.",),
        "PARALYSIS": ("Không cử động được chân.",),
        "MULTIPLE": ("Vừa tê vừa yếu cả hai chân.",),
    },
    "lower_extremity_injury_location": {
        "HIP": ("Ở háng.",), "THIGH": ("Ở đùi.",), "KNEE": ("Ở đầu gối.",),
        "LOWER_LEG": ("Ở bắp chân.", "Cẳng chân."), "ANKLE": ("Ở cổ chân.", "Mắt cá chân."),
        "FOOT": ("Ở bàn chân.",), "TOE": ("Ở ngón chân.",),
    },
    "weight_bearing_ability": {
        "NORMAL": ("Đi lại bình thường.",),
        "PAINFUL_BUT_POSSIBLE": ("Vẫn đứng được nhưng đau, đi khập khiễng.",),
        "PARTIAL": ("Chỉ chống được một chút.",),
        "UNABLE": ("Không chống chân xuống được.",),
    },
    "distal_limb_symptoms": {
        "NONE": ("Bàn chân không tê, không lạnh.",),
        "NUMBNESS": ("Bàn chân tê bì.",),
        "WEAKNESS": ("Bàn chân yếu.",),
        "COLDNESS": ("Bàn chân lạnh ngắt.",),
        "COLOR_CHANGE": ("Bàn chân tím tái lại.",),
        "MULTIPLE": ("Bàn chân vừa tê vừa lạnh.",),
    },
    "wound_status": {
        "NO_OPEN_WOUND": ("Không có vết thương hở.",),
        "SUPERFICIAL_WOUND": ("Trầy xước ngoài da.",),
        "OPEN_WOUND": ("Có vết rách hở.",),
        "DEEP_WOUND": ("Vết thương sâu.",),
        "EXPOSED_BONE": ("Nhìn thấy cả xương lòi ra.",),
    },
    "upper_extremity_injury_location": {
        "SHOULDER": ("Ở vai.",), "UPPER_ARM": ("Ở cánh tay.",), "ELBOW": ("Ở khuỷu tay.",),
        "FOREARM": ("Ở cẳng tay.",), "WRIST": ("Ở cổ tay.",), "HAND": ("Ở bàn tay.",),
        "FINGER": ("Ở ngón tay.",),
    },
    "upper_extremity_injury_mechanism": {
        "FALL": ("Ngã chống tay.",), "DIRECT_IMPACT": ("Bị va đập.",), "TWISTING": ("Bị vặn.",),
        "CRUSH": ("Bị kẹp, đè.",), "CUT": ("Bị cắt.",), "PENETRATING": ("Bị vật nhọn đâm.",),
    },
    "upper_extremity_deformity": {"NONE": ("Không thấy lệch hay cong.",), "PRESENT": ("Thấy cong lệch hẳn.",)},
    "upper_extremity_sensory_change": {
        "NONE": ("Không tê.",), "NUMBNESS": ("Tê bì.",), "TINGLING": ("Châm chích.",),
        "LOSS_OF_SENSATION": ("Mất hẳn cảm giác.",),
    },
    "upper_extremity_movement_ability": {
        "NORMAL": ("Cử động bình thường.",), "LIMITED": ("Cử động được nhưng đau, hạn chế.",),
        "UNABLE": ("Không cử động được.",),
    },
    "distal_color_temperature_change": {
        "NONE": ("Tay vẫn ấm, màu bình thường.",), "COLD": ("Tay lạnh hơn.",), "PALE": ("Tay trắng bệch.",),
        "CYANOTIC": ("Ngón tay tím.",), "MULTIPLE_CHANGES": ("Vừa lạnh vừa tái.",),
    },
    "wound_type": {
        "LACERATION": ("Vết rách.", "Bị cứa rách."), "ABRASION": ("Trầy xước.",),
        "PUNCTURE": ("Vết đâm nhỏ.",), "BITE": ("Vết cắn.",), "CRUSH": ("Bị dập.",),
    },
    "wound_depth_category": {
        "SUPERFICIAL": ("Chỉ trầy ngoài da.",), "THROUGH_SKIN": ("Rách qua da.",),
        "DEEP": ("Sâu, nhìn thấy cả lớp mỡ.",), "PENETRATING": ("Đâm xuyên vào trong.",),
    },
    "wound_location": {
        "HEAD_FACE": ("Ở vùng đầu mặt.",), "NECK": ("Ở cổ.",), "CHEST": ("Ở ngực.",), "ABDOMEN": ("Ở bụng.",),
        "BACK": ("Ở lưng.",), "ARM": ("Ở tay.",), "HAND_FINGER": ("Ở ngón tay.", "Ở bàn tay."),
        "LEG": ("Ở chân.",), "FOOT_TOE": ("Ở bàn chân.",),
    },
    "wound_contamination": {
        "NONE_APPARENT": ("Sạch, không dính đất cát.",), "DIRT_OR_SOIL": ("Dính đất cát.",),
        "DIRTY_WATER": ("Dính nước bẩn.",), "SALIVA": ("Dính nước bọt.",),
    },
    "foreign_body_status": {
        "NONE_SEEN_OR_FELT": ("Không thấy gì mắc trong vết thương.",), "POSSIBLE": ("Hình như còn mảnh gì trong đó.",),
        "OBJECT_STILL_EMBEDDED": ("Vật vẫn còn cắm trong vết thương.",),
    },
    "bleeding_control_status": {
        "NO_BLEEDING": ("Không chảy máu.",), "STOPPED": ("Ép một lúc thì cầm máu rồi.",),
        "SLOW_CONTINUOUS": ("Vẫn rỉ máu chậm.",), "HEAVY_CONTINUOUS": ("Máu vẫn chảy nhiều, ép không cầm.",),
    },
    "burn_mechanism": {
        "FLAME": ("Bị lửa táp.",), "HOT_LIQUID": ("Bị nước nóng làm bỏng.",), "STEAM": ("Bị hơi nước nóng.",),
        "HOT_OBJECT": ("Chạm vào vật nóng.",), "CHEMICAL": ("Bị hoá chất.",), "ELECTRICAL": ("Bị điện giật.",),
    },
    "burn_location": {
        "FACE_OR_NECK": ("Ở mặt và cổ.",), "CHEST_OR_BACK": ("Ở ngực.",), "UPPER_LIMB": ("Ở cánh tay.",),
        "HAND": ("Ở bàn tay.",), "LOWER_LIMB": ("Ở chân.",), "FOOT": ("Ở bàn chân.",),
        "MULTIPLE_AREAS": ("Nhiều chỗ.",),
    },
    "burn_extent_estimate": {
        "TINY_SPOT": ("Chỉ một chấm nhỏ.",), "SMALL_LOCALIZED_AREA": ("Một mảng nhỏ.",),
        "LARGE_LOCALIZED_AREA": ("Một mảng lớn.",), "ONE_BODY_REGION": ("Cả một vùng.",),
        "MULTIPLE_BODY_REGIONS": ("Nhiều vùng trên người.",),
    },
    "burn_skin_appearance": {
        "RED": ("Đỏ rát.",), "BLISTERED": ("Phồng rộp nước.",), "PEELING": ("Bong da.",),
        "PALE_OR_WHITE": ("Trắng bệch.",), "DARKENED": ("Cháy sém đen.",), "MIXED_APPEARANCE": ("Chỗ đỏ chỗ trắng.",),
    },
    "burn_sensation": {
        "PAINFUL_OR_BURNING": ("Đau rát.",), "TINGLING": ("Châm chích.",), "NUMB": ("Tê tê.",),
        "NO_SENSATION": ("Chạm vào không thấy gì.",), "MIXED": ("Chỗ đau chỗ tê.",),
    },
    "burn_encirclement": {"NONE": ("Không quấn vòng quanh.",), "AROUND_ARM": ("Bỏng vòng quanh cánh tay.",)},
    "smoke_or_fume_exposure": {
        "NONE": ("Không hít phải khói.",), "SMOKE": ("Có hít phải khói.",), "HOT_STEAM": ("Hít phải hơi nóng.",),
        "CHEMICAL_FUMES": ("Hít phải hơi hoá chất.",), "MULTIPLE": ("Hít cả khói lẫn hơi nóng.",),
    },
    "rash_character": {
        "GENERAL_RASH": ("Nổi ban đỏ thường.",), "RED_SPOTS": ("Chấm đỏ li ti, ấn không mất.",),
        "PURPLE_PATCHES": ("Mảng tím trên da.",),
    },
    "skin_finding_appearance": {
        "RED_PATCHES": ("Mảng đỏ.",), "RAISED_WHEALS": ("Nổi mề đay, gồ lên.",), "SMALL_SPOTS": ("Chấm nhỏ.",),
        "BLISTERS": ("Nổi bóng nước.",), "CRUSTING_OR_SCALING": ("Đóng vảy.",), "PEELING": ("Bong tróc da.",),
        "ULCER_OR_OPEN_SKIN": ("Loét hở.",), "MIXED": ("Lẫn lộn đủ kiểu.",),
    },
    "skin_finding_distribution": {
        "LOCALIZED": ("Chỉ một chỗ.",), "MULTIPLE_AREAS": ("Ở nhiều chỗ.",), "GENERALIZED": ("Lan khắp người.",),
    },
    "swelling_location": {
        "EYELIDS": ("Sưng mí mắt.",), "FACE": ("Sưng mặt.",), "LIPS": ("Sưng môi.",), "TONGUE": ("Sưng lưỡi.",),
        "THROAT": ("Thấy sưng trong cổ họng.",), "OTHER": ("Sưng ở chỗ khác, không phải mặt.",),
        "MULTIPLE": ("Sưng nhiều chỗ: môi, mắt, mặt.",),
    },
    "suspected_allergy_trigger": {
        "MEDICATION": ("Sau khi uống thuốc.",), "FOOD": ("Sau khi ăn.",), "INSECT_STING_OR_BITE": ("Bị ong đốt.",),
        "LATEX": ("Đeo găng cao su.",), "COSMETIC_OR_TOPICAL_PRODUCT": ("Bôi kem mới.",),
        "NO_TRIGGER_IDENTIFIED": ("Không nghĩ ra do cái gì.",),
    },
    "exposure_to_symptom_interval": {
        "DURING_EXPOSURE": ("Bị ngay lúc đó.",), "WITHIN_MINUTES": ("Chỉ vài phút sau.",),
        "WITHIN_HOURS": ("Vài tiếng sau.",), "WITHIN_DAYS": ("Vài ngày sau.",),
    },
    "mucosal_involvement_location": {
        "NONE": ("Không có.",), "MOUTH": ("Loét trong miệng.",), "EYES": ("Mắt đỏ, đau.",),
        "GENITALS": ("Loét vùng kín.",), "MULTIPLE": ("Cả miệng lẫn mắt.",),
    },
    "pregnancy_status": {
        "PREGNANT": ("Đang mang thai.",), "POSSIBLY_PREGNANT": ("Có thể có thai, chậm kinh rồi.",),
        "POSTPARTUM": ("Mới sinh xong.",), "NOT_PREGNANT": ("Không có thai.",),
    },
    "vaginal_bleeding_amount": {
        "SPOTTING": ("Chỉ vài giọt.",), "LIGHT": ("Ra ít, thấm băng nhẹ.",), "MODERATE": ("Ra khá nhiều.",),
        "HEAVY": ("Ra rất nhiều, ướt đẫm băng.",),
    },
    "fetal_movement_status": {
        "NORMAL": ("Con vẫn đạp bình thường.",), "DECREASED": ("Con đạp ít hơn.",),
        "ABSENT": ("Từ sáng không thấy con đạp.",), "NOT_YET_PERCEIVED": ("Chưa thấy thai máy.",),
    },
    "vaginal_fluid_leakage_status": {
        "NONE": ("Không ra nước.",), "INTERMITTENT": ("Rỉ nước từng lúc.",), "CONTINUOUS": ("Chảy nước liên tục.",),
        "GUSH": ("Có một đợt nước ộc ra.",),
    },
    "birth_progress_sign": {"NONE": ("Không có.",), "URGE_TO_PUSH": ("Rất muốn rặn.",)},
    "self_safety_status": {
        "NO_RISK_REPORTED": ("Không, tôi không có ý định làm hại bản thân.",),
        "UNCERTAIN": ("Tôi không chắc nữa.",),
        "CURRENT_SELF_HARM_THOUGHTS": ("Có, dạo này cứ nghĩ đến chuyện làm hại mình.",),
        "CURRENT_SELF_HARM_INTENT": ("Có, tôi đang định làm thật.",),
        "RECENT_SELF_HARM_BEHAVIOR": ("Tôi vừa tự làm mình bị thương.",),
    },
    "other_safety_status": {
        "NO_RISK_REPORTED": ("Không có chuyện đó.",),
        "CURRENT_VIOLENT_THOUGHTS": ("Có lúc nghĩ muốn đánh người.",),
    },
    "perceptual_disturbance_type": {
        "AUDITORY": ("Nghe thấy tiếng người nói mà không có ai.",), "VISUAL": ("Nhìn thấy những thứ người khác không thấy.",),
        "MULTIPLE": ("Vừa nghe tiếng nói vừa thấy hình ảnh lạ.",),
    },
    "substance_involvement": {
        "NONE_REPORTED": ("Không dùng gì cả.",), "RECENT_USE_REPORTED": ("Có uống rượu tối qua.",),
        "RECENT_CESSATION_REPORTED": ("Mới bỏ rượu mấy hôm nay.",), "SUSPECTED": ("Có thể đã dùng gì đó.",),
    },
    "basic_self_care_capacity": {
        "INDEPENDENT": ("Tự lo được.",), "NEEDS_SOME_HELP": ("Cần người giúp một chút.",),
        "DEPENDENT": ("Phải có người chăm hoàn toàn.",),
        "UNABLE_TO_MAINTAIN_BASIC_NEEDS": ("Mấy ngày không ăn, không tắm, không lo được gì cho mình.",),
    },
    "toxic_substance_category": {
        "MEDICATION": ("Thuốc.",), "ALCOHOL": ("Rượu.",), "RECREATIONAL_DRUG": ("Chất kích thích.",),
        "HOUSEHOLD_CHEMICAL": ("Hoá chất tẩy rửa trong nhà.",), "PESTICIDE": ("Thuốc trừ sâu.",),
        "RODENTICIDE": ("Thuốc diệt chuột.",), "HYDROCARBON": ("Dầu hoả, xăng.",),
        "TOXIC_GAS_OR_SMOKE": ("Khói, khí độc.",), "MUSHROOM_OR_PLANT": ("Nấm lạ.",),
    },
    "toxic_exposure_route": {
        "INGESTION": ("Nuốt vào.",), "INHALATION": ("Hít phải.",), "DERMAL": ("Dính vào da.",),
        "OCULAR": ("Bắn vào mắt.",),
    },
    "estimated_exposure_amount": {
        "SMALL": ("Một ít thôi.",), "MODERATE": ("Khá nhiều.",), "LARGE": ("Rất nhiều.",),
        "VERY_LARGE": ("Rất rất nhiều.",),
    },
    "exposure_intent": {
        "ACCIDENTAL": ("Vô tình, nhầm.",), "MEDICATION_ERROR": ("Uống nhầm liều.",),
        "INTENTIONAL_SELF_HARM": ("Cố ý uống để hại mình.",),
    },
    "coingestion_status": {"NONE": ("Không dùng thêm gì.",), "ALCOHOL": ("Có uống cả rượu.",)},
    "eye_laterality": {"LEFT": ("Mắt trái.",), "RIGHT": ("Mắt phải.",), "BILATERAL": ("Cả hai mắt.",)},
    "eye_injury_mechanism": {
        "BLUNT": ("Bị va đập vào mắt.",), "CHEMICAL": ("Hoá chất bắn vào mắt.",),
        "FOREIGN_BODY": ("Bụi, mạt sắt bay vào mắt.",), "HIGH_VELOCITY": ("Mảnh kim loại bắn vào với tốc độ cao.",),
    },
    "vision_impairment_extent": {
        "BLURRED": ("Nhìn mờ.",), "PARTIAL_LOSS": ("Mất một phần tầm nhìn.",), "COMPLETE_LOSS": ("Không nhìn thấy gì.",),
    },
    "contact_lens_status": {"CURRENT_USE": ("Đang đeo lens.",), "NO_USE": ("Không đeo lens.",)},
    "bite_source": {
        "DOG": ("Chó cắn.",), "CAT": ("Mèo cắn.",), "SNAKE": ("Rắn cắn.",), "INSECT": ("Côn trùng đốt.",),
        "MONKEY": ("Khỉ cắn.",), "RODENT": ("Chuột cắn.",),
    },
    "joint_pain_location": {
        "KNEE": ("Đầu gối.",), "ANKLE": ("Cổ chân.",), "SHOULDER": ("Vai.",), "WRIST": ("Cổ tay.",),
        "FOOT_OR_TOE": ("Ngón chân cái.",), "HIP": ("Háng.",),
    },
    "joint_swelling_status": {"ABSENT": ("Không sưng.",), "PRESENT": ("Có sưng.",)},
    "joint_redness_warmth_status": {
        "NONE": ("Không đỏ, không nóng.",), "REDNESS_ONLY": ("Hơi đỏ.",), "WARMTH_ONLY": ("Sờ thấy nóng.",),
        "REDNESS_AND_WARMTH": ("Vừa đỏ vừa nóng.",),
    },
    "joint_mobility_status": {"NORMAL": ("Cử động bình thường.",), "LIMITED": ("Co duỗi bị hạn chế.",), "UNABLE_TO_MOVE": ("Không cử động được.",)},
    "limb_function_status": {
        "NORMAL_USE": ("Vẫn dùng bình thường.",), "DIFFICULT_USE": ("Dùng được nhưng khó khăn.",),
        "UNABLE_TO_USE": ("Không dùng được.",),
    },
    "joint_involvement_count": {"ONE_JOINT": ("Một khớp thôi.",), "TWO_TO_FOUR_JOINTS": ("Vài khớp.",)},
    "bowel_bladder_control_change": {
        "NONE": ("Đi tiểu, đi ngoài bình thường.",), "URINARY_RETENTION": ("Không tiểu được.",),
        "URINARY_INCONTINENCE": ("Tiểu không tự chủ.",), "FECAL_INCONTINENCE": ("Đi ngoài không tự chủ.",),
        "MULTIPLE": ("Cả tiểu lẫn đại tiện đều không tự chủ.",),
    },
    "epistaxis_current_status": {
        "STOPPED": ("Máu cam ngừng rồi.",), "ACTIVE_CONTINUOUS": ("Vẫn chảy liên tục.",),
        "INTERMITTENT": ("Lúc chảy lúc ngừng.",),
    },
    "epistaxis_side": {"LEFT": ("Lỗ mũi trái.",), "RIGHT": ("Lỗ mũi phải.",), "BILATERAL": ("Cả hai bên.",)},
    "epistaxis_flow_direction": {
        "OUT_OF_NOSTRILS": ("Chảy ra ngoài mũi.",), "INTO_THROAT": ("Chảy xuống họng.",),
        "BOTH": ("Vừa ra ngoài vừa chảy xuống họng.",),
    },
    "epistaxis_pressure_response": {
        "STOPPED": ("Bóp mũi thì ngừng.",), "REDUCED": ("Bóp mũi thì đỡ.",), "NO_CHANGE": ("Bóp mãi vẫn chảy.",),
        "RESTARTED": ("Ngừng rồi lại chảy lại.",),
    },
    "estimated_ent_bleeding_amount": {
        "TRACE": ("Một chút.",), "SMALL": ("Ít.",), "MODERATE": ("Khá nhiều.",), "LARGE": ("Rất nhiều, ướt cả khăn.",),
    },
    "oral_problem_location": {"TOOTH": ("Ở răng.",), "GUM": ("Ở lợi.",), "TONGUE": ("Ở lưỡi.",), "JAW": ("Ở hàm.",)},
    "tooth_condition": {"INTACT": ("Răng vẫn còn nguyên.",), "LOOSE": ("Răng lung lay.",), "CHIPPED_OR_FRACTURED": ("Răng bị mẻ.",)},
    "swallowing_ability": {
        "NORMAL": ("Vẫn nuốt được bình thường.",), "DIFFICULT_SOLIDS": ("Nuốt đồ ăn đặc thì khó.",),
        "DIFFICULT_LIQUIDS": ("Nuốt nước cũng khó.",), "UNABLE_TO_SWALLOW": ("Không nuốt được, kể cả nước bọt.",),
    },
    "thermal_exposure_type": {
        "HOT_WEATHER": ("Ở ngoài trời nắng nóng.",), "DIRECT_SUN": ("Làm dưới nắng gắt.",),
        "ENCLOSED_HOT_SPACE": ("Ở trong phòng kín rất nóng.",), "COLD_AIR": ("Ở ngoài trời lạnh.",),
    },
    "thermal_exposure_duration": {
        "LESS_THAN_30_MINUTES": ("Chưa tới nửa tiếng.",), "THIRTY_MINUTES_TO_TWO_HOURS": ("Khoảng một hai tiếng.",),
        "TWO_TO_SIX_HOURS": ("Mấy tiếng liền.",), "MORE_THAN_SIX_HOURS": ("Cả ngày.",),
    },
    "sweating_pattern": {"NORMAL": ("Mồ hôi bình thường.",), "INCREASED": ("Ra nhiều mồ hôi.",), "ABSENT": ("Da khô, không ra mồ hôi.",)},
    "palpitation_pattern": {
        "FAST": ("Tim đập rất nhanh.", "Đập nhanh dồn dập."), "POUNDING": ("Đập thình thịch, mạnh.",),
        "IRREGULAR": ("Đập không đều, lộn xộn.",), "SKIPPED_BEATS": ("Như bị hẫng mất một nhịp.",),
        "MIXED": ("Lúc nhanh lúc hẫng nhịp.",),
    },
    "nasal_discharge_character": {
        "CLEAR_WATERY": ("Nước mũi trong, loãng.",), "THICK": ("Nước mũi đặc.",), "BLOOD_TINGED": ("Nước mũi lẫn máu.",),
    },
    "ent_foreign_body_location": {"NOSE": ("Trong lỗ mũi.",), "EAR": ("Trong tai.",), "THROAT": ("Trong họng.",)},
    "dental_trauma_type": {
        "KNOCKED_OUT": ("Răng rơi hẳn ra ngoài.",), "LOOSE": ("Răng lung lay.",), "CHIPPED_OR_CRACKED": ("Răng bị mẻ.",),
        "DISPLACED": ("Răng bị lệch khỏi chỗ.",),
    },
    "oral_bleeding_status": {
        "STOPPED": ("Máu ngừng rồi.",), "MINOR_OOZING": ("Chỉ còn rỉ chút máu.",), "CONTINUOUS": ("Máu chảy liên tục.",),
        "PERSISTS_WITH_PRESSURE": ("Ép vào vẫn chảy.",),
    },
    "genital_discharge_appearance": {
        "CLEAR": ("Dịch trong.",), "WHITE": ("Dịch trắng.",), "YELLOW_OR_GREEN": ("Dịch vàng xanh, có mùi.",),
        "BLOODY": ("Dịch lẫn máu.",),
    },
    "mouth_opening_ability": {
        "NORMAL": ("Há miệng bình thường.",), "MILDLY_LIMITED": ("Há hơi khó.",),
        "MARKEDLY_LIMITED": ("Chỉ há được hai đốt ngón tay.",), "UNABLE_TO_OPEN": ("Không há miệng được.",),
    },
    "oral_swelling_distribution": {
        "NO_SWELLING": ("Không sưng.",), "LOCALIZED_TOOTH_OR_GUM": ("Sưng quanh chân răng.",),
        "CHEEK_OR_FACE": ("Sưng lan ra má.",), "UNDER_JAW": ("Sưng dưới hàm.",), "NECK": ("Sưng xuống cổ.",),
    },
    "oral_swelling_location": {
        "NONE": ("Không sưng.",), "TONGUE": ("Sưng ở lưỡi.",), "FACE": ("Sưng ở mặt.",), "UNDER_JAW": ("Sưng dưới hàm.",),
        "NECK": ("Sưng ở cổ.",), "LIP": ("Sưng môi.",),
    },
}

#: Mẫu câu cho dữ kiện số; ``{v}`` là giá trị.
NUMERIC_TEMPLATES: dict[str, tuple[str, ...]] = {
    "heart_rate": ("Mạch đo được {v} lần mỗi phút.", "Máy đo nhịp tim báo {v}.", "Tim đập khoảng {v} nhịp một phút."),
    "respiratory_rate": ("Đếm được khoảng {v} lần thở mỗi phút.", "Nhịp thở chừng {v} lần một phút."),
    "spo2": ("Máy kẹp ngón tay báo {v}%.", "SpO2 đo được {v} phần trăm."),
    "systolic_bp": ("Huyết áp số trên {v}.", "Đo huyết áp số trên được {v}."),
    "diastolic_bp": ("Huyết áp số dưới {v}.",),
    "temperature": ("Nhiệt kế đo {v} độ.", "Đo được {v} độ C."),
    "pain_severity": ("Đau khoảng {v}/10.", "Chắc tầm {v} trên 10.", "Nếu chấm điểm thì {v} điểm."),
    "gestational_age_weeks": ("Thai được {v} tuần.", "Thai {v} tuần rồi."),
    "days_since_last_bowel_movement": ("{v} ngày nay chưa đi ngoài được.",),
    "contraction_interval_minutes": ("Cơn gò cách nhau khoảng {v} phút.",),
    "post_trauma_vomiting_count": ("Nôn {v} lần.",),
    "itching_severity": ("Ngứa mức {v}/10.",),
    "diarrhea_frequency": ("Đi khoảng {v} lần từ hôm qua tới giờ.",),
}

_ZERO_TEMPLATES = {
    "post_trauma_vomiting_count": "Không nôn lần nào.",
}


def _pick(options: tuple[str, ...], key: str) -> str:
    digest = hashlib.sha1(key.encode("utf-8")).digest()
    return options[digest[0] % len(options)]


def _format_number(value: Any, key: str) -> str:
    if isinstance(value, float) and not value.is_integer():
        # Viết số thập phân lúc kiểu Việt (38,5), lúc kiểu máy đo (38.5).
        text = f"{value:.1f}"
        return text.replace(".", ",") if hashlib.sha1(key.encode()).digest()[1] % 2 else text
    return str(int(value)) if isinstance(value, float) else str(value)


def answer_for(fact: str, value: Any, case_id: str) -> str | None:
    """Câu trả lời cho ``fact`` (id ngắn, không có tiền tố ``fact_target:``)."""
    key = f"{case_id}:{fact}"
    if fact in NUMERIC_TEMPLATES:
        if value == 0 and fact in _ZERO_TEMPLATES:
            return _ZERO_TEMPLATES[fact]
        return _pick(NUMERIC_TEMPLATES[fact], key).format(v=_format_number(value, key))
    if fact in _YES_NO_FACTS:
        yes, no = YES_NO_OVERRIDES.get(fact, (YES, NO))
        if value == "YES":
            return _pick(yes, key)
        if value == "NO":
            return _pick(no, key)
        return None
    options = VALUE_PHRASES.get(fact, {}).get(str(value))
    return _pick(options, key) if options else None
