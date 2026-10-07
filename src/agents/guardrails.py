"""Bộ lọc bảo vệ an toàn lâm sàng kép (Dual-Layer Medical Safety Shield).

Tuân thủ nghiêm ngặt hiến pháp clinical-rag-guardrails:
1. Layer 1: Reflex Emergency Shield (Interception tuyệt đối < 50ms)
   - Phát hiện từ khóa khẩn cấp bẫy nhanh từ điển Ontology & Regex Khẩn Cấp.
   - Ngắt ngay lập tức luồng RAG/LLM, chuyển ca thành ESI Level 1/2 kèm nút gọi tel:115.
2. Layer 2: Output Firewall & Diagnosis Suppression
   - Quét và loại bỏ lời khẳng định chẩn đoán tuyệt đối hoặc kê đơn thuốc từ AI.
   - Chuyển hóa văn phong thành nhận định nguy cơ và lời khuyên theo dõi trung lập.
"""

import json
import os
import re
import time
from functools import lru_cache
from typing import Any

from src.agents.nodes.intent_classifier import normalize_vietnamese_text

# Tổ hợp bộ từ khóa khẩn cấp sinh tử theo tiếng Việt & tiếng Anh (Báo Động Đỏ <50ms)
CORE_RED_FLAG_KEYWORDS = [
    # Tim mạch / Đau ngực cấp
    ("đau thắt ngực", "REFLEX_CARDIAC_CHEST_PAIN_V1", 2),
    ("đau ngực dữ dội", "REFLEX_CARDIAC_CHEST_PAIN_V1", 2),
    ("đau bóp thát cõi ngực", "REFLEX_CARDIAC_CHEST_PAIN_V1", 2),
    ("nhói buốt tim như kim châm", "REFLEX_CARDIAC_CHEST_PAIN_V1", 2),
    ("vã mồ hôi hột", "REFLEX_CARDIAC_CHEST_PAIN_V1", 2),
    ("chest pain", "REFLEX_CARDIAC_CHEST_PAIN_V1", 2),
    ("myocardial infarction", "REFLEX_CARDIAC_CHEST_PAIN_V1", 1),
    
    # Đột quỵ / FAST / Thần kinh
    ("liệt nửa người", "REFLEX_STROKE_FAST_V1", 1),
    ("méo miệng", "REFLEX_STROKE_FAST_V1", 1),
    ("nói ngớ ngẩn đột ngột", "REFLEX_STROKE_FAST_V1", 1),
    ("mất trí giác", "REFLEX_ALTERED_CONSCIOUSNESS_V1", 1),
    ("bất tỉnh", "REFLEX_ALTERED_CONSCIOUSNESS_V1", 1),
    ("lơ mơ ngất xỉu", "REFLEX_ALTERED_CONSCIOUSNESS_V1", 1),
    ("co giật liên hồi", "REFLEX_SEIZURE_V1", 1),
    ("fast stroke", "REFLEX_STROKE_FAST_V1", 1),

    # Cảm giác nguy kịch / sắp tử vong do người bệnh tự khai
    ("tôi sắp chết", "REFLEX_IMPENDING_DOOM_V1", 2),
    ("cảm giác sắp chết", "REFLEX_IMPENDING_DOOM_V1", 2),
    ("sắp chết rồi", "REFLEX_IMPENDING_DOOM_V1", 2),

    # Khó thở sâu / Hô hấp tối khẩn
    ("khó thở dữ dội", "REFLEX_RESPIRATORY_DISTRESS_V1", 1),
    ("nghẹt thở tái tím", "REFLEX_RESPIRATORY_DISTRESS_V1", 1),
    ("không thở nổi", "REFLEX_RESPIRATORY_DISTRESS_V1", 1),
    ("chao đảo lịm đi", "REFLEX_RESPIRATORY_DISTRESS_V1", 1),

    # Trao đổi chất / Xoắn ói / Chảy máu
    ("chảy máu không cầm", "REFLEX_UNCONTROLLED_BLEEDING_V1", 1),
    ("máu phun thành tia", "REFLEX_UNCONTROLLED_BLEEDING_V1", 1),
    ("thổ huyết ồ ạt", "REFLEX_MAJOR_GI_BLEEDING_V1", 1),
    ("thai ngoài tử cung vỡ", "REFLEX_OBSTETRIC_EMERGENCY_V1", 1),
    ("đau bụng hạ vị xỉu lả", "REFLEX_OBSTETRIC_EMERGENCY_V1", 2),
]

# Bộ regex bắt mẫu chẩn đoán cấm kỵ và kê toa thuốc (Layer 2 Firewall)
FORBIDDEN_DIAGNOSIS_PATTERNS = [
    re.compile(r"bạn (đã|chắc chắn)?\s*(bị|mắc|mắc bệnh)\s+([A-Z\sàáạảãèéẹẻẽìíịỉĩòóọỏõùúụủũưứựừửữđ]+)(?=[,\.]|$)", re.IGNORECASE),
    re.compile(r"chẩn đoán (chính xác |của bạn )?(là|:)\s+([A-Z\sàáạảãèéẹẻẽìíịỉĩòóọỏõùúụủũưứựừửữđ]+)(?=[,\.]|$)", re.IGNORECASE),
    re.compile(r"(hãy|bạn nên)\s+(uống|dùng|mua|tiêm)\s+(thuốc\s+)?([a-z0-9\s]+(\d+mg|\d+g|\d+ml|viên/ngày))", re.IGNORECASE),
]


def load_ontology_red_flags() -> list[tuple[str, str, int]]:
    """Tải động từ điển Ontology y khoa vi-en nhằm làm giàu bộ nạp nhanh bẫy Red-Flag."""
    ontology_path = os.path.join("data", "guard_rules", "ontology_vi_en.json")
    additional_flags: list[tuple[str, str, int]] = []
    if os.path.exists(ontology_path):
        try:
            with open(ontology_path, encoding="utf-8") as f:
                data = json.load(f)
                for key, val in data.items():
                    rule_id = f"REFLEX_ONTOLOGY_{key.upper()}_V1"
                    esi_str = val.get("esi_baseline_acuity", "")
                    esi = 1 if "Level 1" in esi_str or "Resuscitation" in esi_str else 2
                    for term in val.get("standard_vi_terms", []) + val.get("patient_slang_dialect", []):
                        if any(crit in term.lower() for crit in ["cấp", "dữ dội", "thét", "xỉu", "ngất", "vã mồ hôi", "ép chặt"]):
                            additional_flags.append((term.lower(), rule_id, esi))
        except Exception as e:
            print(f"⚠️ [Guardrails] Lỗi đọc ontology_vi_en.json: {e}")
    return additional_flags


# Bộ nhớ đệm tĩnh ghép bộ chìa khóa bẫy
EXTENDED_RED_FLAGS = CORE_RED_FLAG_KEYWORDS + load_ontology_red_flags()

EDUCATIONAL_QUERY_MARKERS = (
    "là gì",
    "nghĩa là gì",
    "có nghĩa gì",
    "giải thích",
    "tìm hiểu",
    "ví dụ",
)
CURRENT_EVENT_MARKERS = (
    "tôi đang",
    "mình đang",
    "em đang",
    "cháu đang",
    "hiện tại",
    "ngay lúc này",
    "bây giờ",
)

OPEN_FRACTURE_PATTERNS = (
    re.compile(r"\b(?:gay|vo)\s+xuong\s+ho\b"),
    re.compile(
        r"\b(?:gay|vo)\s+(?:chan|tay|xuong|dui|cang\s+chan|canh\s+tay)\b"
        r".{0,100}\b(?:xuong\s+(?:trang\s+)?(?:loi|lo|thoi|choc)|(?:loi|lo|thoi|choc)\s+(?:dau\s+)?xuong|dau\s+xuong\s+(?:loi|lo))\b"
    ),
    re.compile(
        r"\b(?:xuong\s+(?:trang\s+)?(?:loi|lo|thoi|choc)|(?:loi|lo|thoi|choc)\s+(?:dau\s+)?xuong|dau\s+xuong\s+(?:loi|lo))\b"
        r".{0,100}\b(?:gay|vo)\s+(?:chan|tay|xuong|dui|cang\s+chan|canh\s+tay)\b"
    ),
)

HEAVY_BLEEDING_PATTERNS = (
    re.compile(r"\bchay\s+(?:rat\s+)?nhieu\s+mau\b"),
    re.compile(r"\bmau\s+(?:chay|ra|tuon|phun)\s+(?:rat\s+)?(?:nhieu|o\s+at|am\s+am)\b"),
    re.compile(r"\bchay\s+mau\s+(?:khong\s+cam|rat\s+nhieu|nhieu|o\s+at|am\s+am)\b"),
    re.compile(r"\b(?:tuon|phun|ra)\s+mau\s+(?:rat\s+)?(?:nhieu|o\s+at|am\s+am)\b"),
)

ESI1_PATTERN_RED_FLAGS = (
    (
        re.compile(
            r"\bngung\s+(?:tho|tim)\b"
            r"|\bkhong\s+con\s+tho\b"
            r"|\bkhong\s+bat\s+duoc\s+mach\b"
            r"|\bmat\s+mach\b"
            r"|\btim\s+ngung\s+dap\b"
            r"|\bdang\s+(?:phai\s+)?ep\s+tim\b"
            r"|\bcpr\b"
        ),
        "ngừng thở/ngừng tim hoặc mất mạch",
        "REFLEX_CARDIORESPIRATORY_ARREST_V1",
    ),
    (
        re.compile(
            r"\b(?:dat\s+noi\s+khi\s+quan|mo\s+khi\s+quan|bop\s+bong|bvm|tho\s+may|cpap|bipap)\b"
            r"|\b(?:soc\s+dien\s+pha\s+rung|pha\s+rung|chuyen\s+nhip\s+cap\s+cuu|tao\s+nhip\s+ngoai)\b"
        ),
        "đang/cần can thiệp cứu sống đường thở hoặc điện học",
        "REFLEX_LIFESAVING_INTERVENTION_V1",
    ),
    (
        re.compile(
            r"\bkhong\s+tho\s+duoc\b"
            r"|\btho\s+(?:ngap\s+ca|yeu\s+dan)\b"
            r"|\btim\s+tai\s+khong\s+tho\s+duoc\b"
            r"|\bnghet\s+tho\s+tim\s+tai\b"
            r"|\bngung\s+tho\s+tung\s+con\b"
        ),
        "suy hô hấp tối khẩn",
        "REFLEX_RESPIRATORY_FAILURE_V1",
    ),
    (
        re.compile(
            r"\bgoi\s+khong\s+tinh\b"
            r"|\blay\s+khong\s+day\b"
            r"|\bkhong\s+dap\s+ung\b"
            r"|\bhon\s+me\b"
            r"|\bavpu\s+[pu]\b"
            r"|\bchi\s+dap\s+ung\s+khi\s+dau\b"
        ),
        "không đáp ứng/AVPU P-U",
        "REFLEX_UNRESPONSIVE_AVPU_V1",
    ),
    (
        re.compile(
            r"\bco\s+giat\s+(?:hon\s+)?5\s+phut\b"
            r"|\bco\s+giat\s+(?:mai\s+)?khong\s+(?:dung|ngung)\b"
            r"|\bco\s+giat\s+lien\s+tuc\s+khong\s+tinh(?:\s+lai)?\b"
            r"|\bco\s+giat\s+roi\s+khong\s+tinh(?:\s+lai)?\b"
        ),
        "co giật kéo dài/không hồi tỉnh",
        "REFLEX_STATUS_SEIZURE_V1",
    ),
    (
        re.compile(
            r"\bmau\s+(?:vot|phun\s+phot|chay\s+thanh\s+voi)\b"
            r"|\buot\s+dam\s+bang\s+gac\b"
            r"|\b(?:phai\s+)?garo\s+(?:cam\s+mau)?\b"
            r"|\bcan\s+garo\b"
        ),
        "xuất huyết lớn cần kiểm soát ngay",
        "REFLEX_MAJOR_EXTERNAL_HEMORRHAGE_V1",
    ),
    (
        re.compile(
            r"\bbong\s+(?:mat|mat\s+co|co|duong\s+ho\s+hap)\b.{0,80}\b(?:khan\s+tieng|tho\s+kho\s+khe|hit\s+khoi|sac\s+khoi|kho\s+tho)\b"
            r"|\b(?:chay|dam\s+chay)\b.{0,80}\b(?:sac\s+khoi|hit\s+khoi)\b.{0,80}\b(?:kho\s+tho|tho\s+kho\s+khe|khan\s+tieng)\b"
            r"|\bbong\s+do\s+3\s+dien\s+rong\s+(?:tren\s+)?(?:15|20)\s*%?\b"
        ),
        "bỏng đường thở/hít khói hoặc bỏng nặng diện rộng",
        "REFLEX_AIRWAY_BURN_INHALATION_V1",
    ),
    (
        re.compile(
            r"\b(?:di\s+ung|an\s+hai\s+san|an\s+tom|ong\s+dot|uong\s+thuoc|tiem\s+thuoc)\b"
            r".{0,100}\b(?:moi\s+luoi\s+sung|luoi\s+sung|nghet\s+co|nghet\s+hong|tho\s+khong\s+ra|kho\s+tho|tut\s+huyet\s+ap|ngat|lo\s+mo)\b"
        ),
        "phản vệ đe dọa đường thở hoặc sốc",
        "REFLEX_ANAPHYLAXIS_AIRWAY_SHOCK_V1",
    ),
    (
        re.compile(
            r"\b(?:tut\s+huyet\s+ap|huyet\s+ap\s+tut|soc|shock)\b"
            r".{0,100}\b(?:lo\s+mo|ngat|lim|lanh\s+toat|da\s+tai|vang\s+mo\s+hoi)\b"
            r"|\b(?:lo\s+mo|ngat|lim|lanh\s+toat|da\s+tai|vang\s+mo\s+hoi)\b"
            r".{0,100}\b(?:tut\s+huyet\s+ap|huyet\s+ap\s+tut|soc|shock)\b"
        ),
        "sốc/tụt huyết áp kèm giảm tưới máu hoặc tri giác",
        "REFLEX_HEMODYNAMIC_SHOCK_V1",
    ),
    (
        re.compile(
            r"\b(?:qua\s+lieu|chich\s+ma\s+tuy|opioid|heroin)\b"
            r".{0,100}\b(?:tho\s+cham|tim\s+tai|dong\s+tu\s+co\s+nho|ngat|hon\s+me)\b"
            r"|\b(?:thuoc\s+tru\s+sau|hoa\s+chat)\b"
            r".{0,100}\b(?:sui\s+bot\s+mep|tho\s+yeu|lo\s+mo|ngat|co\s+that\s+phe\s+quan)\b"
        ),
        "ngộ độc/quá liều gây suy hô hấp hoặc hôn mê",
        "REFLEX_TOXIC_OVERDOSE_RESPIRATORY_FAILURE_V1",
    ),
    (
        re.compile(
            r"\b(?:bang\s+huyet\s+sau\s+sinh|sau\s+sinh\s+mau\s+chay\s+o\s+at)\b"
            r"|\bsau\s+sinh\b.{0,60}\bbang\s+huyet\b"
            r"|\b(?:mang\s+thai|co\s+bau|dang\s+bau)\b.{0,100}\b(?:chay\s+mau\s+o\s+at|mau\s+chay\s+o\s+at)\b.{0,100}\b(?:ngat|tut\s+huyet\s+ap|lo\s+mo)\b"
        ),
        "băng huyết sản khoa hoặc chảy máu thai kỳ kèm sốc",
        "REFLEX_OBSTETRIC_HEMORRHAGE_SHOCK_V1",
    ),
)


def is_educational_query(text: str) -> bool:
    """Identify explicit definition/example requests without a current-event claim."""
    normalized = text.strip().lower()
    return any(marker in normalized for marker in EDUCATIONAL_QUERY_MARKERS) and not any(
        marker in normalized for marker in CURRENT_EVENT_MARKERS
    )


def fold_for_screening(text: str) -> str:
    """Accent-fold and collapse repeated letters so typos still raise a candidate.

    Vietnamese orthography has no doubled letters, so collapsing runs turns
    "choangg" into "choang" and "nguccc" into "nguc" without merging distinct
    words. Patients type without diacritics far more often than not.
    """
    folded = re.sub(r"([a-z])\1+", r"\1", normalize_vietnamese_text(text))
    return re.sub(r"[^a-z0-9\s]", " ", folded).strip()


@lru_cache(maxsize=2048)
def _candidate_pattern(keyword: str) -> re.Pattern[str] | None:
    """Build a recall-oriented matcher tolerating one stray letter per token.

    This low-level matcher only returns rule metadata.  The deterministic
    detector owns the policy decision and turns a positive configured match
    into a monotonic safety lock. Recall is therefore worth more here than
    precision, and a missed match is the expensive error.
    """
    tokens = [token for token in fold_for_screening(keyword).split() if token]
    if not tokens:
        return None
    body = r"[a-z]?\s+".join(re.escape(token) for token in tokens)
    return re.compile(rf"(?<![a-z0-9]){body}[a-z]?(?![a-z0-9])")


def _mentions_candidate(folded_text: str, keyword: str) -> bool:
    pattern = _candidate_pattern(keyword)
    return pattern is not None and pattern.search(folded_text) is not None


def _is_negated_mention(folded_text: str, keyword: str) -> bool:
    """Ignore explicit denial such as 'không đau ngực'.

    Danger phrases that themselves begin with "không" (for example
    "không thở nổi") are current emergency claims, not denials.
    """
    folded_keyword = fold_for_screening(keyword)
    if not folded_keyword or folded_keyword.startswith(("khong ", "ko ")):
        return False
    match = _candidate_pattern(keyword)
    if match is None:
        return False
    found = match.search(folded_text)
    if found is None:
        return False
    prefix = folded_text[max(0, found.start() - 32):found.start()].strip()
    return bool(
        re.search(
            r"(?:^|\s)(?:khong|ko|chua)(?:\s+(?:co|bi|thay))?\s*$",
            prefix,
        )
    )


def _pattern_redflag(folded_text: str) -> tuple[str, int, str] | None:
    for pattern, trigger, safety_rule_id in ESI1_PATTERN_RED_FLAGS:
        if pattern.search(folded_text):
            return trigger, 1, safety_rule_id
    return None


def _trauma_hemorrhage_redflag(folded_text: str) -> tuple[str, int, str] | None:
    """Detect exposed/open fracture trauma before model work.

    Open fracture is a high-risk emergency presentation.  When the patient also
    reports heavy, spurting, or uncontrolled bleeding, the reflex path must
    treat it as likely immediate life-saving intervention need (ESI 1).
    """
    has_open_fracture = any(pattern.search(folded_text) for pattern in OPEN_FRACTURE_PATTERNS)
    if not has_open_fracture:
        return None

    has_heavy_bleeding = any(pattern.search(folded_text) for pattern in HEAVY_BLEEDING_PATTERNS)
    if has_heavy_bleeding:
        return (
            "gãy xương hở kèm chảy máu nhiều",
            1,
            "REFLEX_OPEN_FRACTURE_HEMORRHAGE_V1",
        )
    return (
        "gãy xương hở/lòi xương",
        2,
        "REFLEX_OPEN_FRACTURE_V1",
    )


def extract_patient_reported_vitals(user_input: str) -> dict[str, int | float | str]:
    """Extract only explicitly labelled vital signs with conservative ranges."""
    text = user_input.strip().lower().replace(",", ".")
    vitals: dict[str, int | float | str] = {}

    blood_pressure = re.search(
        r"(?:huyết\s*áp|blood\s*pressure|\bbp\b)\s*(?:là|:|=)?\s*(\d{2,3})\s*/\s*(\d{2,3})",
        text,
    )
    if blood_pressure:
        systolic = int(blood_pressure.group(1))
        diastolic = int(blood_pressure.group(2))
        if 40 <= systolic <= 260 and 20 <= diastolic <= 180:
            vitals.update({
                "blood_pressure": f"{systolic}/{diastolic}",
                "systolic_bp": systolic,
                "diastolic_bp": diastolic,
            })

    labelled_patterns: tuple[
        tuple[str, str, type[int] | type[float], float, float],
        ...,
    ] = (
        ("spo2", r"(?:spo2|sp[oô]₂|nồng\s*độ\s*oxy)\s*(?:là|:|=)?\s*(\d{2,3})", int, 50, 100),
        ("heart_rate", r"(?:mạch|nhịp\s*tim|heart\s*rate|\bhr\b)\s*(?:là|:|=)?\s*(\d{2,3})", int, 20, 250),
        ("respiratory_rate", r"(?:nhịp\s*thở|respiratory\s*rate|\brr\b)\s*(?:là|:|=)?\s*(\d{1,2})", int, 5, 80),
        ("temperature_c", r"(?:nhiệt\s*độ|temperature|\btemp\b)\s*(?:là|:|=)?\s*(\d{2}(?:\.\d)?)", float, 30, 45),
        ("gcs", r"(?:gcs|glasgow|tri\s*giác)\s*(?:là|:|=)?\s*(\d{1,2})", int, 3, 15),
        ("blood_glucose_mg_dl", r"(?:đường\s*huyết|glucose|blood\s*sugar)\s*(?:là|:|=)?\s*(\d{1,3})(?:\s*mg/?dl)?", int, 20, 600),
    )
    for key, pattern, converter, minimum, maximum in labelled_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = converter(match.group(1))
        if minimum <= value <= maximum:
            vitals[key] = value
    return vitals


def extract_patient_reported_vital_context(user_input: str) -> dict[str, str]:
    """Preserve source/time labels emitted by the structured patient form."""
    source_match = re.search(
        r"nguồn\s*đo\s*:\s*([^;]+)",
        user_input,
        flags=re.IGNORECASE,
    )
    measured_at_match = re.search(
        r"thời\s*điểm\s*đo\s*:\s*([^;]+)",
        user_input,
        flags=re.IGNORECASE,
    )
    context: dict[str, str] = {}
    if source_match:
        context["source"] = source_match.group(1).strip()[:80]
    if measured_at_match:
        context["measured_at"] = measured_at_match.group(1).strip()[:40]
    return context


def _vital_redflag(vitals: dict[str, int | float | str]) -> tuple[str, int] | None:
    spo2 = vitals.get("spo2")
    heart_rate = vitals.get("heart_rate")
    systolic = vitals.get("systolic_bp")
    gcs = vitals.get("gcs")
    glucose = vitals.get("blood_glucose_mg_dl")
    if (
        isinstance(spo2, int) and spo2 <= 88
        or isinstance(gcs, int) and gcs <= 8
        or isinstance(systolic, int) and systolic < 70
        or isinstance(glucose, int) and glucose <= 50
    ):
        return "sinh hiệu do người bệnh khai ở ngưỡng nguy cấp", 1
    if (
        isinstance(spo2, int) and spo2 < 92
        or isinstance(heart_rate, int) and (heart_rate > 130 or heart_rate < 40)
        or isinstance(systolic, int) and systolic < 85
    ):
        return "sinh hiệu do người bệnh khai cần đánh giá khẩn", 2
    return None


def screen_red_flag_candidate(user_input: str) -> dict[str, Any] | None:
    """Return metadata for the first configured deterministic safety match.

    This pure matcher does not mutate workflow state.  Its caller applies the
    rule-owned acuity and monotonic emergency lock before model work.
    """
    start_time = time.perf_counter()
    folded = fold_for_screening(user_input)
    if not folded:
        return None
    if is_educational_query(user_input):
        return None

    pattern_alert = _pattern_redflag(folded)
    if pattern_alert:
        trigger, esi_level, safety_rule_id = pattern_alert
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": "CANDIDATE",
            "candidate_esi": esi_level,
            "trigger_keyword": trigger,
            "latency_ms": round(elapsed_ms, 2),
            "safety_rule_id": safety_rule_id,
            "candidate_source": "DETERMINISTIC_REFLEX",
        }

    trauma_alert = _trauma_hemorrhage_redflag(folded)
    if trauma_alert:
        trigger, esi_level, safety_rule_id = trauma_alert
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": "CANDIDATE",
            "candidate_esi": esi_level,
            "trigger_keyword": trigger,
            "latency_ms": round(elapsed_ms, 2),
            "safety_rule_id": safety_rule_id,
            "candidate_source": "DETERMINISTIC_REFLEX",
        }

    for keyword, safety_rule_id, esi_level in EXTENDED_RED_FLAGS:
        if _mentions_candidate(folded, keyword) and not _is_negated_mention(folded, keyword):
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "CANDIDATE",
                "candidate_esi": esi_level,
                "trigger_keyword": keyword,
                "latency_ms": round(elapsed_ms, 2),
                "safety_rule_id": safety_rule_id,
                "candidate_source": "DETERMINISTIC_REFLEX",
            }

    vitals = extract_patient_reported_vitals(user_input)
    vital_alert = _vital_redflag(vitals)
    if vital_alert:
        trigger, esi_level = vital_alert
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        vital_values = ", ".join(f"{key}={value}" for key, value in vitals.items())
        return {
            "status": "CANDIDATE",
            "candidate_esi": esi_level,
            "trigger_keyword": f"{trigger}: {vital_values}",
            "latency_ms": round(elapsed_ms, 2),
            "safety_rule_id": "REFLEX_PATIENT_REPORTED_VITALS_V1",
            "candidate_source": "DETERMINISTIC_REFLEX",
        }

    return None


def filter_output_diagnosis(raw_llm_response: str) -> str:
    """Tường lửa quét đầu ra LLM (Output Firewall & Diagnosis Suppression).
    
    Tuyệt đối nghiêm cấm việc Trợ lý AI tự ý khẳng định chẩn đoán hoặc kê đơn.
    Cải biến tự động sang nhận định nhóm nguy cơ và lời khuyên chuyển chuyên khoa.
    """
    filtered_text = raw_llm_response

    # Kiểm tra và thay thế các từ cấm kỵ kê đơn / khẳng định bệnh
    for pattern in FORBIDDEN_DIAGNOSIS_PATTERNS:
        matches = pattern.findall(filtered_text)
        if matches:
            print(f"🛡️ [OUTPUT FIREWALL] Chặn thành công nỗ lực chẩn đoán/kê đơn tự động từ LLM: {matches}")
            # Cải biến câu từ bị cấm thành khuyến cáo trung lập
            filtered_text = pattern.sub(
                "Dựa trên các dấu hiệu lâm sàng bạn phác họa, triệu chứng thuộc nhóm nguy cơ cần được kiểm tra kỹ lưỡng bởi Bác sĩ chuyên khoa",
                filtered_text
            )

    # Nếu LLM sót disclaimer y khoa, bổ sung ở cuối nếu là phác họa bệnh tình dài
    disclaimer_tag = "*(Lưu ý: Trợ lý AI Triage hỗ trợ thẩm định mức độ khẩn cấp theo chuẩn ESI và không thay thế chẩn đoán hoặc kê đơn của Bác sĩ điều trị)*"
    if "ESI" in filtered_text and "Lưu ý:" not in filtered_text and len(filtered_text) > 200:
        filtered_text += f"\n\n--- \n{disclaimer_tag}"

    return filtered_text
