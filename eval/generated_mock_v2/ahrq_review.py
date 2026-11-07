"""Đối chiếu nhãn với AHRQ ESI v5, độc lập với corpus đã sinh ra nhãn.

Nhãn của mỗi ca do ``golden_validator.satisfied_esi`` tính từ các tiêu chí
CLINICAL_AUTHORITY trong PostgreSQL (nguồn ``doc:esi_v4``). Module này đọc một
tài liệu KHÁC trong repo, ``data/protocols/ahrq_esi_v5.draft-manifest.json``
(trích AHRQ ESI Implementation Handbook v5), và chỉ áp dụng những quy tắc mà
văn bản đó viết ra một cách tường minh:

- Bảng 5 (chunk 007): ngưỡng sinh hiệu nguy hiểm theo tuổi (Decision Point D);
- Bảng 4 (chunk 006): sinh hiệu bình thường của trẻ theo nhóm tuổi;
- Bảng 6 (chunk 008): sốt ở trẻ theo tuổi;
- Decision Point B (chunk 001/002): lú lẫn, lơ mơ, mất định hướng -> ESI 2;
- Bảng 1 (chunk 003) và Decision Point A (chunk 002): can thiệp cứu sống,
  gồm epinephrine tiêm bắp cho phản vệ và suy hô hấp nặng;
- Bảng 3 (chunk 005, Table 5-2): sáu ca mẫu dự đoán số nguồn lực.

Không có ngưỡng nào được gõ tay ở đây: mọi con số đều được đọc từ manifest,
và mọi kết luận đều kèm ``citation_id`` của đoạn đã dùng. Khi văn bản AHRQ không
nói gì về một tình huống, kết luận là CONSISTENT (không mâu thuẫn), không phải
AGREE. Manifest này chính nó đang ở trạng thái NOT_READY_FOR_INGESTION và
REQUIRES_CLINICAL_OWNER, nên kết quả đối chiếu là bằng chứng hỗ trợ, không thay
thế người duyệt lâm sàng.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MANIFEST_PATH = Path("data/protocols/ahrq_esi_v5.draft-manifest.json")

AGREE = "AGREE"
CONSISTENT = "CONSISTENT"
CANNOT_VERIFY = "CANNOT_VERIFY"
DISAGREE_OVER = "DISAGREE_OVER"
DISAGREE_UNDER = "DISAGREE_UNDER"
_SEVERITY = {CONSISTENT: 0, AGREE: 1, CANNOT_VERIFY: 2, DISAGREE_OVER: 3, DISAGREE_UNDER: 4}
NEEDS_REVIEW_VERDICTS = {CANNOT_VERIFY, DISAGREE_OVER, DISAGREE_UNDER}

#: Nhóm tuổi theo hàng của AHRQ Table 6-1 / bảng ngưỡng nguy hiểm.
AGE_GROUPS = ("neonate", "infant", "toddler", "preschooler", "school_age", "adolescent", "adult")
_DANGER_ROW_PREFIX = {
    "neonate": "< 1 mo", "infant": "1–12 mo", "toddler": "1–3 y", "preschooler": "3–5 y",
    "school_age": "5–12 y", "adolescent": "12–18 y", "adult": "> 18 y",
}
_NORMAL_ROW_PREFIX = {
    "neonate": "Term neonate", "infant": "Infant", "toddler": "Toddler", "preschooler": "Preschooler",
    "school_age": "School age", "adolescent": "Adolescent",
}

#: Ca mẫu Table 5-2: khoá -> (mức ESI, cụm từ phải có trong hàng, số nguồn lực tối thiểu, tối đa).
TABLE_5_2_ANCHORS = {
    "ESI5_EAR_PAIN_3YO": (5, "ear pain", 0, 0),
    "ESI5_LOST_INHALER_42YO": (5, "lost rescue inhaler", 0, 0),
    "ESI4_SORE_THROAT_19YO": (4, "sore throat", 1, 1),
    "ESI4_DYSURIA_29YO": (4, "dysuria", 1, 1),
    "ESI3_RLQ_PAIN_22YO": (3, "RLQ abdominal pain", 2, 10),
    "ESI3_LEG_SWELLING_CAR_TRIP_45YO": (3, "car trip", 2, 10),
}

VITAL_FACTS = {"heart_rate", "respiratory_rate", "spo2", "systolic_bp", "diastolic_bp", "temperature"}
#: Dữ kiện mà ngưỡng của corpus không chỉnh theo tuổi.
_AGE_SENSITIVE_FACTS = {"heart_rate", "respiratory_rate", "spo2", "temperature", "fever_present"}


def age_group(age_years: int, age_months: int | None) -> str:
    if age_years < 1:
        months = age_months if age_months is not None else 0
        return "neonate" if months < 1 else "infant"
    if age_years < 3:
        return "toddler"
    if age_years < 5:
        return "preschooler"
    if age_years < 12:
        return "school_age"
    if age_years < 18:
        return "adolescent"
    return "adult"


def _numbers(text: str) -> list[float]:
    return [float(item) for item in re.findall(r"\d+(?:\.\d+)?", text)]


@dataclass
class AhrqReference:
    chunks: dict[str, dict[str, Any]]
    danger: dict[str, dict[str, float]] = field(default_factory=dict)
    normal: dict[str, dict[str, tuple[float, float]]] = field(default_factory=dict)
    anchors: dict[str, dict[str, Any]] = field(default_factory=dict)
    fever_rows: list[str] = field(default_factory=list)
    fever: dict[str, dict[str, Any]] = field(default_factory=dict)

    def cite(self, chunk_id: str) -> str:
        return str(self.chunks[chunk_id]["citation_id"])


def load_reference(path: Path = MANIFEST_PATH) -> AhrqReference:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    chunks = {chunk["chunk_id"]: chunk for chunk in manifest["chunks"]}
    ref = AhrqReference(chunks=chunks)

    for row in chunks["ahrq_esi_v5-007"]["decision_criteria"][1:]:
        cells = [cell.strip() for cell in row.split("|")]
        group = next((g for g, prefix in _DANGER_ROW_PREFIX.items() if cells[0] == prefix), None)
        if group is None:
            raise RuntimeError(f"Unrecognised danger-zone row in AHRQ chunk 007: {row!r}")
        hr, rr, spo2 = (_numbers(cell)[0] for cell in cells[1:4])
        ref.danger[group] = {"heart_rate_above": hr, "respiratory_rate_above": rr, "spo2_below": spo2}
    if set(ref.danger) != set(AGE_GROUPS):
        raise RuntimeError("AHRQ chunk 007 does not cover every age group.")

    for row in chunks["ahrq_esi_v5-006"]["decision_criteria"][1:]:
        cells = [cell.strip() for cell in row.split("|")]
        group = next((g for g, prefix in _NORMAL_ROW_PREFIX.items() if cells[0].startswith(prefix)), None)
        if group is None:
            raise RuntimeError(f"Unrecognised normal-range row in AHRQ chunk 006: {row!r}")
        hr, rr, sbp = (tuple(_numbers(cell)) for cell in cells[1:4])
        ref.normal[group] = {"heart_rate": hr, "respiratory_rate": rr, "systolic_bp": sbp}

    rows = chunks["ahrq_esi_v5-005"]["decision_criteria"][1:]
    for key, (level, phrase, low, high) in TABLE_5_2_ANCHORS.items():
        match = next((row for row in rows if phrase.lower() in row.lower()), None)
        if match is None or not match.strip().startswith(str(level)):
            raise RuntimeError(f"Table 5-2 anchor {key} not found at ESI {level} in AHRQ chunk 005.")
        ref.anchors[key] = {"esi": level, "row": match, "resources_min": low, "resources_max": high}

    ref.fever_rows = list(chunks["ahrq_esi_v5-008"]["decision_criteria"][1:])
    ref.fever = _parse_fever_rows(ref.fever_rows)
    return ref


def _celsius(cell: str) -> dict[str, float]:
    """``T > 39.0°C (102.2°F) or < 36.0°C`` -> {"above": 39.0, "below": 36.0}."""
    found: dict[str, float] = {}
    for sign, number in re.findall(r"([<>])\s*(\d+(?:\.\d+)?)\s*°C", cell):
        found["above" if sign == ">" else "below"] = float(number)
    return found


def _parse_fever_rows(rows: list[str]) -> dict[str, dict[str, Any]]:
    wanted = {
        "neonate": ("1 - 28 days", "Assign at least ESI 2"),
        "infant_1_3_months": ("1 - 3 months", "Consider assigning ESI 2"),
        "three_months_plus": ("3 months and older", "Consider assigning ESI 2 or 3"),
        "red_flag_under_90_days": ("< 90 days", "High Risk Indicator"),
        "red_flag_over_3_months": ("> 3 months", "High Risk Indicator"),
    }
    parsed: dict[str, dict[str, Any]] = {}
    for key, (prefix, action) in wanted.items():
        row = next((item for item in rows if item.strip().startswith(prefix)), None)
        if row is None or action not in row:
            raise RuntimeError(f"AHRQ chunk 008 no longer carries the {key} fever rule ({prefix!r} / {action!r}).")
        cells = [cell.strip() for cell in row.split("|")]
        thresholds = _celsius(cells[1])
        if "above" not in thresholds:
            raise RuntimeError(f"AHRQ chunk 008 row {prefix!r} has no temperature threshold.")
        parsed[key] = {**thresholds, "action": action, "row": row}
    return parsed


def _peds_fever_supported(ref: "AhrqReference", group: str, age_months: int | None, temp: Any) -> bool:
    """Nhiệt độ tới ngưỡng sốt nhi khoa (Table 6-2) hoặc ngưỡng dấu hiệu đỏ của tuổi đó (chunk 008)."""
    if not isinstance(temp, (int, float)) or group == "adult":
        return False
    young = group == "neonate" or (group == "infant" and (age_months or 0) < 3)
    rules = [ref.fever["neonate"] if group == "neonate" else ref.fever["infant_1_3_months"] if young
             else ref.fever["three_months_plus"],
             ref.fever["red_flag_under_90_days"] if young else ref.fever["red_flag_over_3_months"]]
    return any(temp > rule["above"] or ("below" in rule and temp < rule["below"]) for rule in rules)


@dataclass
class Finding:
    rule_id: str
    effect: str
    chunk_id: str
    citation_id: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return self.__dict__.copy()


def _short(facts: dict[str, Any]) -> dict[str, Any]:
    return {key.removeprefix("fact_target:"): value for key, value in facts.items()}


def review(
    ref: AhrqReference,
    *,
    label: int | None,
    patient_facts: dict[str, Any],
    resources: int | None,
    resource_basis: str,
    age_years: int,
    age_months: int | None,
    matched_atoms: list[dict[str, Any]],
) -> dict[str, Any]:
    """Kết luận đối chiếu AHRQ cho một ca. ``label`` None nghĩa là RETURN_INCOMPLETE."""
    facts = _short(patient_facts)
    group = age_group(age_years, age_months)
    findings: list[Finding] = []

    def add(rule_id: str, effect: str, chunk_id: str, detail: str) -> None:
        findings.append(Finding(rule_id, effect, chunk_id, ref.cite(chunk_id), detail))

    # --- Decision Point D: sinh hiệu nguy hiểm theo tuổi (chunk 007).
    limits = ref.danger[group]
    exceeded: list[str] = []
    if isinstance(facts.get("heart_rate"), (int, float)) and facts["heart_rate"] > limits["heart_rate_above"]:
        exceeded.append(f"HR {facts['heart_rate']} > {limits['heart_rate_above']:g}")
    if isinstance(facts.get("respiratory_rate"), (int, float)) and facts["respiratory_rate"] > limits["respiratory_rate_above"]:
        exceeded.append(f"RR {facts['respiratory_rate']} > {limits['respiratory_rate_above']:g}")
    if isinstance(facts.get("spo2"), (int, float)) and facts["spo2"] < limits["spo2_below"]:
        exceeded.append(f"SpO2 {facts['spo2']} < {limits['spo2_below']:g}")
    if exceeded and label in (3, None):
        add(
            "AHRQ_D_DANGER_ZONE", CANNOT_VERIFY, "ahrq_esi_v5-007",
            f"Sinh hiệu ngoài ngưỡng nguy hiểm của nhóm tuổi {group} ({'; '.join(exceeded)}); "
            "AHRQ yêu cầu điều dưỡng cân nhắc nâng lên ESI 2. Corpus chỉ áp dụng Decision Point D khi đã biết "
            "resource_count >= 2 (dữ kiện CLINICIAN_ONLY), nên ở đây không nâng.",
        )
    elif exceeded and label in (1, 2):
        add("AHRQ_D_DANGER_ZONE", CONSISTENT, "ahrq_esi_v5-007",
            f"Sinh hiệu ngoài ngưỡng nguy hiểm của nhóm tuổi {group} ({'; '.join(exceeded)}), phù hợp mức khẩn cấp cao.")

    # Nhãn 1/2 chỉ vì sinh hiệu hoặc nhiệt độ ở trẻ em: corpus dùng một ngưỡng cho mọi tuổi. Nhiệt độ chỉ
    # được coi là đủ khi tới ngưỡng sốt nhi khoa hoặc ngưỡng dấu hiệu đỏ của AHRQ cho tuổi đó (chunk 008).
    if label in (1, 2) and matched_atoms and group != "adult":
        vital_only = all(
            atom["patient_condition_facts"] and set(atom["patient_condition_facts"]) <= _AGE_SENSITIVE_FACTS
            for atom in matched_atoms
        )
        if vital_only and not exceeded and not _peds_fever_supported(ref, group, age_months, facts.get("temperature")):
            add(
                "AHRQ_AGE_ADJUSTED_VITALS", DISAGREE_OVER, "ahrq_esi_v5-007",
                f"Nhãn ESI {label} chỉ đến từ ngưỡng sinh hiệu/nhiệt độ dùng chung cho mọi tuổi, nhưng các chỉ số trẻ "
                f"khai không vượt ngưỡng nguy hiểm của nhóm tuổi {group} và nhiệt độ (nếu có) chưa tới ngưỡng sốt hay "
                "dấu hiệu đỏ nhi khoa (đối chiếu thêm Bảng 4, chunk 006 và Bảng 6, chunk 008).",
            )
        elif vital_only and label == 1:
            add(
                "AHRQ_AGE_ADJUSTED_VITALS", CANNOT_VERIFY, "ahrq_esi_v5-007",
                f"Sinh hiệu vượt ngưỡng nguy hiểm của nhóm tuổi {group}, mà theo Decision Point D thì chỉ dẫn tới "
                "'cân nhắc ESI 2'; ESI 1 đòi hỏi can thiệp cứu sống (Decision Point A), cần người khám xác định.",
            )

    # --- Sốt ở trẻ (chunk 008). Chỉ áp dụng cho người dưới 18 tuổi.
    temp = facts.get("temperature")
    if isinstance(temp, (int, float)) and group != "adult":
        fever = ref.fever
        young = group == "neonate" or (group == "infant" and (age_months or 0) < 3)

        def outside(rule: dict[str, Any]) -> bool:
            return temp > rule["above"] or ("below" in rule and temp < rule["below"])

        if group == "neonate" and outside(fever["neonate"]):
            effect = AGREE if label in (1, 2) else DISAGREE_UNDER
            add("AHRQ_PEDS_FEVER_NEONATE", effect, "ahrq_esi_v5-008",
                f"Trẻ dưới 1 tháng tuổi, {temp} °C: {fever['neonate']['row']}")
        elif young and outside(fever["infant_1_3_months"]):
            effect = CONSISTENT if label in (1, 2) else CANNOT_VERIFY
            add("AHRQ_PEDS_FEVER_1_3_MONTHS", effect, "ahrq_esi_v5-008",
                f"Trẻ 1-3 tháng, {temp} °C: {fever['infant_1_3_months']['row']}")
        elif not young and outside(fever["three_months_plus"]):
            effect = CONSISTENT if label in (1, 2, 3) else CANNOT_VERIFY
            add("AHRQ_PEDS_FEVER_3_MONTHS_PLUS", effect, "ahrq_esi_v5-008",
                f"Trẻ từ 3 tháng, {temp} °C: {fever['three_months_plus']['row']}")
        red_flag = fever["red_flag_under_90_days"] if young else fever["red_flag_over_3_months"]
        if outside(red_flag) and label not in (1, 2):
            add("AHRQ_PEDS_FEVER_RED_FLAG", CANNOT_VERIFY, "ahrq_esi_v5-008",
                f"{temp} °C là 'High Risk Indicator' theo bảng dấu hiệu đỏ ({red_flag['row']}); "
                f"nhãn hiện tại là {'RETURN_INCOMPLETE' if label is None else f'ESI {label}'}.")

    # --- Decision Point B: lú lẫn, lơ mơ, mất định hướng (chunk 001, 002).
    lethargy = []
    if facts.get("altered_mental_status_present") == "YES":
        lethargy.append("altered_mental_status_present=YES")
    if facts.get("post_trauma_awareness_change") in {"CONFUSION", "MULTIPLE"}:
        lethargy.append(f"post_trauma_awareness_change={facts['post_trauma_awareness_change']}")
    if facts.get("activity_level") in {"VERY_INACTIVE", "DIFFICULT_TO_AROUSE"}:
        lethargy.append(f"activity_level={facts['activity_level']}")
    if lethargy:
        if label in (1, 2):
            add("AHRQ_B_ALTERED_MENTAL_STATUS", AGREE, "ahrq_esi_v5-001",
                f"Decision Point B: {', '.join(lethargy)} tương ứng 'Confused/lethargic/disoriented' -> ESI 2.")
        else:
            add("AHRQ_B_ALTERED_MENTAL_STATUS", DISAGREE_UNDER, "ahrq_esi_v5-001",
                f"Decision Point B: {', '.join(lethargy)} tương ứng 'Confused/lethargic/disoriented' -> ESI 2, "
                f"nhưng corpus cho {'RETURN_INCOMPLETE' if label is None else f'ESI {label}'}.")
        if facts.get("activity_level") == "DIFFICULT_TO_AROUSE" and label == 2:
            add("AHRQ_A_UNRESPONSIVE", CANNOT_VERIFY, "ahrq_esi_v5-002",
                "Khó đánh thức có thể là 'unresponsive' (cần kích thích đau) ở Decision Point A -> ESI 1; cần người khám.")

    # --- Decision Point A / Table 3-1: can thiệp cứu sống (chunk 002, 003).
    airway_swelling = (
        facts.get("allergic_reaction_features") in {"TONGUE_SWELLING", "FACIAL_OR_LIP_SWELLING", "MULTIPLE_FEATURES"}
        or facts.get("tongue_swelling_present") == "YES"
        or facts.get("swelling_location") in {"TONGUE", "THROAT", "LIPS", "MULTIPLE"}
    )
    breathing_trouble = (
        facts.get("dyspnea_present") == "YES"
        or facts.get("respiratory_distress_symptoms") in {"AT_REST", "SEVERE_OR_UNABLE_TO_SPEAK_NORMALLY"}
        or facts.get("noisy_breathing_present") == "YES"
    )
    if airway_swelling and breathing_trouble:
        effect = AGREE if label == 1 else CANNOT_VERIFY
        add("AHRQ_A_EPINEPHRINE_ANAPHYLAXIS", effect, "ahrq_esi_v5-003",
            "Sưng môi/lưỡi/họng kèm khó thở: Table 3-1 liệt kê 'Epinephrine (including IM for anaphylaxis)' là can thiệp cứu sống. "
            f"Nếu người khám xác định phản vệ cần epinephrine thì AHRQ xếp ESI 1; corpus cho {'RETURN_INCOMPLETE' if label is None else f'ESI {label}'}.")
    if facts.get("bleeding_control_status") == "HEAVY_CONTINUOUS":
        if label == 1:
            effect = AGREE
        elif label is None:
            effect = DISAGREE_UNDER
        else:
            effect = CANNOT_VERIFY
        add("AHRQ_A_EXTERNAL_HEMORRHAGE", effect, "ahrq_esi_v5-003",
            "Máu chảy nhiều, ép không cầm: Table 3-1 liệt kê 'Control of external hemorrhage' là can thiệp cứu sống (ESI 1); "
            f"corpus cho {'RETURN_INCOMPLETE' if label is None else f'ESI {label}'}.")
    if facts.get("respiratory_distress_symptoms") == "SEVERE_OR_UNABLE_TO_SPEAK_NORMALLY":
        effect = AGREE if label == 1 else CANNOT_VERIFY
        add("AHRQ_A_SEVERE_RESPIRATORY_DISTRESS", effect, "ahrq_esi_v5-002",
            "Khó thở đến mức không nói được hết câu: Decision Point A liệt kê 'severe respiratory distress'. "
            "Người bệnh tự khai, cần người khám xác nhận mức suy hô hấp.")

    # --- Dự đoán nguồn lực (chunk 004, 005).
    if resources is not None:
        anchor_key = resource_basis.removeprefix("AHRQ_T5_2:") if resource_basis.startswith("AHRQ_T5_2:") else ""
        anchor = ref.anchors.get(anchor_key)
        if anchor:
            if anchor["esi"] != label or not anchor["resources_min"] <= resources <= anchor["resources_max"]:
                raise RuntimeError(f"Resource anchor {anchor_key} does not support ESI {label} with {resources} resources.")
            add("AHRQ_C_TABLE_5_2_ANCHOR", AGREE, "ahrq_esi_v5-005",
                f"Trùng ca mẫu Table 5-2: {anchor['row']}")
        else:
            add("AHRQ_C_RESOURCE_PREDICTION", CANNOT_VERIFY, "ahrq_esi_v5-004",
                f"ESI {label} dựa vào dự đoán {resources} nguồn lực (dữ kiện CLINICIAN_ONLY), "
                f"không trùng ca mẫu nào của Table 5-2; căn cứ người viết: {resource_basis or 'không ghi'}.")

    if label is None and not findings:
        add("AHRQ_C_HANDOFF", CONSISTENT, "ahrq_esi_v5-004",
            "Không có tiêu chí A/B nào được khai; mức C/D phụ thuộc dự đoán nguồn lực của điều dưỡng, "
            "nên chuyển nhân viên y tế là phù hợp.")

    verdict = max((item.effect for item in findings), key=_SEVERITY.__getitem__, default=CONSISTENT)
    return {
        "verdict": verdict,
        "age_group": group,
        "findings": [item.as_dict() for item in findings],
    }
