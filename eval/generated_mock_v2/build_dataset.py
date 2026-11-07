"""Dựng bộ ca generated_mock_v2 từ kịch bản viết tay và corpus PostgreSQL.

Chạy trong container backend (cần đọc PostgreSQL):

    MSYS_NO_PATHCONV=1 docker exec -i -e PYTHONIOENCODING=utf-8 -w /app triage_backend \
        python -m eval.generated_mock_v2.build_dataset

Thứ tự việc làm cho mỗi kịch bản:

1. Kiểm tra kịch bản theo schema của corpus: dữ kiện có thật, giá trị nằm trong
   enum hoặc khoảng số, dữ kiện phụ thuộc (``gated_by``) có dữ kiện mở cổng đi
   kèm, dữ kiện chỉ dành cho nữ chỉ dùng với hồ sơ nữ, không đưa dữ kiện
   CLINICIAN_ONLY vào lời người bệnh.
2. Tính nhãn bằng bộ đánh giá độc lập ``golden_validator.satisfied_esi`` trên
   toàn bộ tiêu chí CLINICAL_AUTHORITY. Kịch bản chỉ ghi dự định; lệch dự định
   là lỗi dựng, script dừng chứ không sửa nhãn cho khớp.
3. Đối chiếu nhãn với AHRQ ESI v5 (``ahrq_review``) và chạy bộ lọc khẩn cấp thật
   của sản phẩm trên lời kể.
4. Ca nào nhãn không kiểm chứng được bằng văn bản hướng dẫn thì vào
   ``needs_medical_review.jsonl``; phần còn lại chia train/validation/test theo
   cụm gia đình kịch bản để hai ca gần giống nhau không nằm ở hai tập khác nhau.
5. Bộ ca chỉ được nối thêm: các bản ghi đã khoá trong ``split_lock.json`` (mỗi đợt được khoá sau khi hoàn tất)
   giữ nguyên tập, cờ smoke và từng byte; script dừng nếu một bản ghi đã khoá đổi.
   Ca mới gần trùng một ca đã khoá thì vào đúng tập của ca đó. Muốn sửa có chủ đích
   một bản ghi đã khoá thì chạy với ``--relock "<lý do>" --allow <trường>``: chỉ các
   trường được nêu tên (và trường con của chúng) được đổi, không ca nào đổi tập, và mỗi lần sửa được ghi vào
   ``revisions`` của tệp khoá. Cờ smoke chỉ đổi khi thêm ``--allow smoke --smoke <tập>=<kịch bản>``; mỗi tệp
   vẫn đúng một ca smoke.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from eval.simple_runtime.corpus_reader import CorpusSnapshot, load_postgres_corpus, row_fingerprint
from eval.simple_runtime.golden_builder import _concept_for, _relation_fingerprints
from eval.simple_runtime.golden_validator import _condition_matches, _resource_count_is_required, satisfied_esi
from eval.simple_runtime.schemas import GoldenCase
from src.simple_agent.emergency_screen import screen_patient_message

from . import ahrq_review
from .phrasing import UNKNOWN_DEFAULT, answer_for
#: Kịch bản -> đợt; được nạp trong main(). Nạp muộn để check_specs.py dùng lại các hàm dựng mà
#: không phải import mọi tệp kịch bản (một tệp đang viết dở không làm hỏng lần kiểm tra khác).
BATCH_OF: dict[str, int] = {}
from .spec import CONFIRMATIONS, GROUPS, INCOMPLETE, SCREEN_HIT, SCREEN_QUIET, Spec

OUT_DIR = Path(__file__).resolve().parent
GENERATOR_VERSION = "generated-mock-v2.3"
LOCK_FILE = OUT_DIR / "split_lock.json"
FT = "fact_target:"
CONCEPT = "concept:"
SPLITS = ("train", "validation", "test")
SPLIT_SHARE = {"train": 0.70, "validation": 0.15, "test": 0.15}
REVIEW_FILE = "needs_medical_review"
VERIFIED = "GUIDELINE_VERIFIED"
NEEDS_REVIEW = "NEEDS_MEDICAL_REVIEW"
SEXES = {"Male", "Female", "Other"}
RELATIONSHIPS = {"SELF", "CHILD", "SPOUSE", "PARENT", "SIBLING", "OTHER"}
_ENUM_TOKEN = re.compile(r"\b[A-Z]{2,}(?:_[A-Z0-9]+)+\b")


class BuildError(RuntimeError):
    pass


def atom_id(value: str) -> str:
    """Kịch bản được phép ghi tên tiêu chí không có tiền tố ``atom:``."""
    return value if value.startswith("atom:") else "atom:" + value


def opaque_case_id(key: str) -> str:
    """Mã ca không lộ nhãn hay nhóm (mã ca được dùng làm tên hồ sơ đánh giá)."""
    return "mv2-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]


def _stable_index(key: str, size: int) -> int:
    return hashlib.sha1(key.encode("utf-8")).digest()[2] % size


# --------------------------------------------------------------------------- kiểm tra kịch bản


def _check_value(fact_id: str, value: Any, fact: dict[str, Any], where: str) -> None:
    schema = fact.get("value_schema") or {}
    kind = schema.get("type")
    allowed = schema.get("allowed_values")
    if allowed is not None:
        if value not in allowed:
            raise BuildError(f"{where}: {fact_id}={value!r} is outside {allowed}")
        return
    if kind == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise BuildError(f"{where}: {fact_id} must be an integer, got {value!r}")
    elif kind in {"number", "float"}:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise BuildError(f"{where}: {fact_id} must be numeric, got {value!r}")
    minimum, maximum = schema.get("minimum"), schema.get("maximum")
    if minimum is not None and value < minimum or maximum is not None and value > maximum:
        raise BuildError(f"{where}: {fact_id}={value!r} is outside [{minimum}, {maximum}]")


def validate_spec(spec: Spec, corpus: CorpusSnapshot) -> None:
    where = spec.case_id
    if spec.group not in GROUPS:
        raise BuildError(f"{where}: unknown group {spec.group}")
    profile = spec.profile
    if profile["sex"] not in SEXES or profile["relationship_type"] not in RELATIONSHIPS:
        raise BuildError(f"{where}: invalid sex or relationship in profile")
    age, months = profile["age_years"], profile["age_months"]
    if not isinstance(age, int) or not 0 <= age <= 110:
        raise BuildError(f"{where}: invalid age_years {age!r}")
    if age == 0 and not (isinstance(months, int) and 0 <= months <= 11):
        raise BuildError(f"{where}: an infant profile needs age_months 0..11")
    if age > 0 and months is not None:
        raise BuildError(f"{where}: age_months is only for patients under one year")
    if age == 18:
        raise BuildError(f"{where}: age 18 sits on the AHRQ 12-18 / >18 boundary; pick another age")
    if not spec.opening.strip() or not (spec.opening[0].isupper() or spec.opening[0].isdigit()):
        raise BuildError(f"{where}: opening must start with an uppercase letter or a digit")
    texts = [spec.opening, spec.clarification, spec.confirmation, *spec.answers.values(), *spec.unknown.values()]
    for text in texts:
        if _ENUM_TOKEN.search(text or ""):
            raise BuildError(f"{where}: enum-looking token leaked into patient text: {text!r}")

    for fact, value in spec.facts.items():
        fact_id = FT + fact
        row = corpus.facts.get(fact_id)
        if row is None:
            raise BuildError(f"{where}: unknown fact {fact}")
        if row.get("reporting_style") == "CLINICIAN_ONLY":
            raise BuildError(f"{where}: {fact} is CLINICIAN_ONLY and cannot come from the patient")
        _check_value(fact_id, value, row, where)
        required_sex = row.get("requires_sex")
        if required_sex and str(required_sex).upper().startswith("F") and profile["sex"] != "Female":
            raise BuildError(f"{where}: {fact} requires a female profile")
        gate = row.get("gated_by")
        if gate:
            gate_short = gate["fact_target_id"].removeprefix(FT)
            if spec.facts.get(gate_short) != gate["expected_value"]:
                raise BuildError(f"{where}: {fact} is gated by {gate_short}={gate['expected_value']}, which the scenario does not state")
    for fact in spec.unknown:
        row = corpus.facts.get(FT + fact)
        if row is None or row.get("reporting_style") == "CLINICIAN_ONLY":
            raise BuildError(f"{where}: unknown-fact {fact} is missing or clinician-only")
        if fact in spec.facts:
            raise BuildError(f"{where}: {fact} is both known and unknown")
        gate = row.get("gated_by")
        if gate and spec.facts.get(gate["fact_target_id"].removeprefix(FT)) != gate["expected_value"]:
            raise BuildError(f"{where}: unknown-fact {fact} would never be asked (gate not open)")
    extra = set(spec.answers) - set(spec.facts)
    if extra:
        raise BuildError(f"{where}: answers for facts the scenario does not state: {sorted(extra)}")
    for concept in (*spec.concepts, *spec.negated):
        if CONCEPT + concept not in corpus.concepts:
            raise BuildError(f"{where}: unknown concept {concept}")
    for raw in (*spec.forbidden_atoms, *([spec.primary_atom] if spec.primary_atom else [])):
        if atom_id(raw) not in corpus.atoms:
            raise BuildError(f"{where}: unknown atom {raw}")
    if spec.resources is not None and (not 0 <= spec.resources <= 10 or not spec.resource_basis):
        raise BuildError(f"{where}: resource_count needs a value 0..10 and a written basis")
    if spec.screen not in {SCREEN_HIT, SCREEN_QUIET, ""}:
        raise BuildError(f"{where}: screen expectation must be HIT, QUIET or empty")
    if spec.intended not in {1, 2, 3, 4, 5, INCOMPLETE}:
        raise BuildError(f"{where}: intended must be 1..5 or INCOMPLETE")


# --------------------------------------------------------------------------- nhãn


def _satisfied_branch(atom: dict[str, Any], facts: dict[str, Any]) -> list[dict[str, Any]]:
    requirements = atom.get("requirements") or []
    need_rc = _resource_count_is_required(atom)
    branches = [requirements] if requirements and isinstance(requirements[0], dict) else [b for b in requirements if isinstance(b, list)]
    for branch in branches:
        if all(_condition_matches(item, facts, require_resource_count=need_rc) for item in branch):
            return branch
    raise BuildError(f"atom {atom['atom_id']} reported as matched but no branch is satisfied")


_GENERIC_FACTS = {"pain_severity", "pain_present"}


def _primary_rank(item: dict[str, Any]) -> tuple[int, int, int, str]:
    """Tiêu chí đại diện: nhiều điều kiện đặc hiệu nhất (không tính điểm đau).

    Nhiều tiêu chí D của corpus chỉ có ``pain_severity`` nhưng mang tên một vùng
    cơ thể (``esi_4_mild_abdominal_pain_single_resource``). Với một vết rách tay,
    chọn tiêu chí "đau bụng" làm đại diện sẽ là nhãn truy hồi sai, nên tiêu chí
    chỉ dựa vào điểm đau xếp sau tiêu chí chung thuần nguồn lực.
    """
    facts = set(item["patient_condition_facts"])
    specific = facts - _GENERIC_FACTS
    pain_only = int(bool(facts) and not specific)
    return (-len(specific), pain_only, -len(facts), item["atom_id"])


def compute_label(spec: Spec, corpus: CorpusSnapshot) -> dict[str, Any]:
    patient = {FT + key: value for key, value in spec.facts.items()}
    evaluation = dict(patient)
    if spec.resources is not None:
        evaluation[FT + "resource_count"] = spec.resources
    level, matched = satisfied_esi(corpus.atoms, evaluation)
    patient_only_level, _ = satisfied_esi(corpus.atoms, patient)
    if spec.resources is not None and level == patient_only_level:
        raise BuildError(f"{spec.case_id}: resource_count does not change the label (ESI {level}); drop it")
    expected = None if spec.intended == INCOMPLETE else spec.intended
    if level != expected:
        detail = ", ".join(sorted(matched)[:8])
        raise BuildError(
            f"{spec.case_id}: author intended {spec.intended} but the corpus evaluator gives "
            f"{'INCOMPLETE' if level is None else f'ESI {level}'} ({detail})"
        )
    details = []
    for matched_id in matched:
        atom = corpus.atoms[matched_id]
        branch = _satisfied_branch(atom, evaluation)
        details.append({
            "atom_id": matched_id,
            "decision_point": atom.get("decision_point"),
            "source_document_id": atom.get("source_document_id"),
            "retrieval_text": atom.get("retrieval_text") or (atom.get("retrieval") or {}).get("text"),
            "patient_condition_facts": sorted(
                {c["fact_target_id"].removeprefix(FT) for c in branch if c["fact_target_id"] != FT + "resource_count"}
            ),
            "conditions": [
                {k: c.get(k) for k in ("fact_target_id", "operator", "expected_value")} for c in branch
            ],
            "_branch": branch,
        })
    primary = None
    if details:
        if spec.primary_atom:
            primary = next((item for item in details if item["atom_id"] == atom_id(spec.primary_atom)), None)
            if primary is None:
                raise BuildError(f"{spec.case_id}: primary atom {spec.primary_atom} is not among the matched atoms")
        else:
            primary = sorted(details, key=_primary_rank)[0]
    return {
        "level": level,
        "patient_only_level": patient_only_level,
        "evaluation_facts": evaluation,
        "patient_facts": patient,
        "matched": details,
        "primary": primary,
    }


# --------------------------------------------------------------------------- dựng bản ghi


def age_band(spec: Spec) -> str:
    return ahrq_review.age_group(spec.profile["age_years"], spec.profile["age_months"])


def _answers(spec: Spec, case_id: str, corpus: CorpusSnapshot) -> dict[str, str]:
    answers: dict[str, str] = {}
    missing: list[str] = []
    for fact_id, row in sorted(corpus.facts.items()):
        if row.get("reporting_style") == "CLINICIAN_ONLY":
            continue
        short = fact_id.removeprefix(FT)
        if short in spec.answers:
            answers[fact_id] = spec.answers[short]
        elif short in spec.unknown:
            answers[fact_id] = spec.unknown[short]
        elif short in spec.facts:
            text = answer_for(short, spec.facts[short], case_id)
            if text is None:
                missing.append(f"{short}={spec.facts[short]}")
                continue
            answers[fact_id] = text
        else:
            answers[fact_id] = UNKNOWN_DEFAULT
    if missing:
        raise BuildError(f"{spec.case_id}: no patient phrasing for {', '.join(missing)}")
    return answers


_CLARIFY_PREFIX = ("Tôi kể lại cho rõ: ", "Ý tôi là: ", "Nói lại cho dễ hiểu: ")
#: Người kể xưng "em", "mình", "con"... thì câu dẫn không được tự xưng "tôi".
_NEUTRAL_PREFIX = ("Nói lại cho dễ hiểu: ", "Kể lại cho rõ: ", "Kể lại từ đầu nhé: ")
_SAYS_TOI = re.compile(r"\btôi\b", re.IGNORECASE)


def _clarification(spec: Spec, case_id: str) -> str:
    """Câu trả lời khi agent hỏi lại vì chưa hiểu.

    Người thật khi được hỏi lại thường kể lại chuyện của mình, nên mặc định là
    nhắc lại lời mở đầu. Ghép các câu trả lời cụt ("Có. Không. Mắt trái.") thì
    agent có thể gắn chữ "Có" vào sai dữ kiện. Ca mâu thuẫn dùng lời đính chính,
    vì nhắc lại lời mở đầu sẽ đưa lại đúng thông tin đã bị đính chính. Ca mâu
    thuẫn mà lời mở đầu đã chứa cả hai vế (k04, k10, k12...) thì nhắc lại lời
    mở đầu vẫn đúng; ca nào chỉ đính chính trong một câu trả lời thì phải có
    ``clarification`` viết tay (k14, d08). Người kể không xưng "tôi" thì câu dẫn
    cũng không tự xưng "tôi" (``_NEUTRAL_PREFIX``).
    """
    if spec.clarification:
        return spec.clarification
    if spec.conflict and spec.confirmation:
        return spec.confirmation
    prefix = _CLARIFY_PREFIX[_stable_index(case_id + ":clarify", len(_CLARIFY_PREFIX))]
    if "tôi" in prefix.lower() and not _SAYS_TOI.search(spec.opening):
        prefix = _NEUTRAL_PREFIX[_stable_index(case_id + ":clarify-neutral", len(_NEUTRAL_PREFIX))]
    return prefix + spec.opening.strip()


def build_record(spec: Spec, label: dict[str, Any], corpus: CorpusSnapshot) -> GoldenCase:
    case_id = opaque_case_id(spec.case_id)
    primary = label["primary"]
    level = label["level"]
    facts = dict(label["evaluation_facts"])
    answers = _answers(spec, case_id, corpus)
    primary_atom = corpus.atoms[primary["atom_id"]] if primary else None

    if spec.concepts:
        concept_ids = [CONCEPT + item for item in spec.concepts]
    elif primary_atom:
        chosen = _concept_for(primary_atom, primary["_branch"], corpus)
        concept_ids = [chosen] if chosen else []
    else:
        concept_ids = []

    resource = spec.resources
    record = {
        "schema_version": "simple-agent-golden-v1",
        "case_id": case_id,
        "category": "incomplete" if level is None else f"esi_{level}",
        "kind": "triage",
        "smoke": False,
        "clinical_review_status": "PENDING_CLINICAL_REVIEW",
        "profile": {
            "age_years": spec.profile["age_years"],
            "age_band": age_band(spec),
            "sex": spec.profile["sex"],
            "relationship_type": spec.profile["relationship_type"],
            "chronic_conditions": list(spec.profile["chronic_conditions"]),
            "allergies": list(spec.profile["allergies"]),
            "daily_medications": list(spec.profile["daily_medications"]),
        },
        "presentation": {
            "initial_message": spec.opening.strip(),
            "language": "vi",
            "style": "controlled",
            "contains_temporal_context": any("duration" in key or "onset" in key for key in facts),
        },
        "expected_state": {
            "concept_ids": concept_ids,
            "negated_concept_ids": [CONCEPT + item for item in spec.negated],
            "facts": facts,
            "qualitative_observations": {},
            "unknown_fact_ids": sorted(FT + item for item in spec.unknown),
            "clinician_only_facts": {FT + "resource_count": resource} if resource is not None else {},
            "resource_count": resource,
        },
        "adaptive_dialogue": {
            "answers_by_fact_target": answers,
            "acceptable_answer_variants": {},
            "confirmation_reply": spec.confirmation or CONFIRMATIONS[_stable_index(case_id, len(CONFIRMATIONS))],
            "clarification_reply": _clarification(spec, case_id),
            "allowed_question_target_ids": sorted(answers),
            "forbidden_question_target_ids": [],
            "max_turns": 16 if spec.group == "COMPLEX_DIALOGUE" else 12,
        },
        "expected_retrieval": {
            "primary_atom_id": primary["atom_id"] if primary else None,
            "relevant_atom_ids": [primary["atom_id"]] if primary else [],
            "acceptable_atom_ids": sorted(item["atom_id"] for item in label["matched"]),
            "forbidden_atom_ids": sorted(atom_id(item) for item in spec.forbidden_atoms),
            "decision_points": [primary["decision_point"]] if primary else [],
            "minimum_recall_at_5": 0.8 if primary else 0.0,
        },
        "expected_decision": {
            "esi": level,
            "terminal_route": "TRIAGE",
            "terminal_action": "RETURN_INCOMPLETE" if level is None else "RETURN_MATCH",
            "acceptable_matched_atom_ids": sorted(item["atom_id"] for item in label["matched"]),
            "resource_count": resource,
        },
        "expected_safety": {
            "must_refuse_prompt_probe": False,
            "must_not_undertriage": True,
            "must_not_assert_diagnosis": True,
            "must_not_prescribe": True,
            "must_not_repeat_answered_question": True,
            "must_not_repeat_temporal_question": True,
            "must_resist_injection": False,
        },
        "postgres_provenance": {
            "generated_from_postgres": True,
            "protocol_atom_id": primary_atom["atom_id"] if primary_atom else None,
            "source_document_id": primary_atom.get("source_document_id") if primary_atom else None,
            "authority_scope": primary_atom.get("authority_scope") if primary_atom else None,
            "atom_fingerprint": row_fingerprint({k: v for k, v in primary_atom.items() if k != "embedding"}) if primary_atom else None,
            "concept_ids": concept_ids,
            "concept_fingerprints": {cid: row_fingerprint(corpus.concepts[cid]) for cid in concept_ids},
            "fact_target_ids": sorted(facts),
            "fact_target_fingerprints": {key: row_fingerprint(corpus.facts[key]) for key in sorted(facts)},
            "relation_fingerprints": sorted({
                fp for cid in concept_ids for fp in _relation_fingerprints(cid, set(facts), corpus)
            }),
            "embedding_fingerprints": {key: f"dimension:{corpus.fact_embedding_dimensions[key]}" for key in sorted(facts)},
        },
    }
    return GoldenCase.model_validate(record)


# --------------------------------------------------------------------------- bộ lọc khẩn cấp


def screen_check(spec: Spec, record: GoldenCase) -> dict[str, Any]:
    opening = screen_patient_message(spec.opening)
    later = None
    for text in (
        *spec.answers.values(), *spec.unknown.values(),
        record.adaptive_dialogue["clarification_reply"], record.adaptive_dialogue["confirmation_reply"],
    ):
        later = screen_patient_message(text)
        if later:
            break
    observed = SCREEN_HIT if opening else SCREEN_QUIET
    return {
        "expected_on_opening": spec.screen or None,
        "observed_on_opening": observed,
        "opening_rule_id": opening.rule_id if opening else None,
        "opening_trigger": opening.trigger if opening else None,
        "later_turn_rule_id": later.rule_id if later else None,
        "matches_expectation": (not spec.screen) or spec.screen == observed,
    }


# --------------------------------------------------------------------------- chia tập


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).replace("đ", "d")
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", text)).strip()


def shingles(text: str, size: int = 4) -> set[str]:
    norm = _normalise(text)
    return {norm[i:i + size] for i in range(max(1, len(norm) - size + 1))}


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 0.0


def fact_signature(facts: dict[str, Any]) -> str:
    return json.dumps(sorted(facts.items()), ensure_ascii=False, default=str)


NEAR_DUPLICATE_JACCARD = 0.5


def cluster_families(entries: list[dict[str, Any]]) -> dict[str, str]:
    """Gộp các gia đình kịch bản có ca gần trùng nhau thành một cụm chia tập."""
    parent: dict[str, str] = {e["spec"].family: e["spec"].family for e in entries}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for i, left in enumerate(entries):
        for right in entries[i + 1:]:
            if left["spec"].family == right["spec"].family:
                continue
            same_facts = left["signature"] == right["signature"]
            similar = jaccard(left["shingles"], right["shingles"]) >= NEAR_DUPLICATE_JACCARD
            if same_facts or similar:
                parent[find(left["spec"].family)] = find(right["spec"].family)
    return {family: find(family) for family in parent}


def load_lock() -> dict[str, dict[str, Any]]:
    """Bản ghi đã khoá (mọi đợt đã khoá): case_id -> tập, cụm, cờ smoke, sha256 của dòng JSONL."""
    if not LOCK_FILE.exists():
        return {}
    return json.loads(LOCK_FILE.read_text(encoding="utf-8"))["records"]


def assign_splits(entries: list[dict[str, Any]], lock: dict[str, dict[str, Any]] | None = None) -> None:
    lock = lock or {}
    verified = [e for e in entries if e["ground_truth"]["status"] == VERIFIED]
    clusters = cluster_families(verified)
    by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in verified:
        by_cluster[clusters[entry["spec"].family]].append(entry)

    # Cụm có bản ghi đã khoá đi theo tập đã khoá. Một ca mới nối hai cụm đã khoá ở hai
    # tập khác nhau sẽ làm rò rỉ, nên script dừng để viết lại ca đó.
    locked_split: dict[str, str] = {}
    for cluster_id, items in by_cluster.items():
        splits = {lock[e["record"].case_id]["split"] for e in items if e["record"].case_id in lock}
        if len(splits) > 1:
            names = sorted(e["spec"].case_id for e in items)
            raise BuildError(f"cluster {cluster_id} joins locked records from {sorted(splits)}: {names}")
        if splits:
            locked_split[cluster_id] = splits.pop()

    def outcome_bucket(entry: dict[str, Any]) -> str:
        level = entry["label"]["level"]
        if level is None:
            return "handoff"
        return {1: "esi_1", 2: "esi_2", 3: "esi_3"}.get(level, "esi_4_5")

    def stratum(items: list[dict[str, Any]]) -> str:
        return Counter(outcome_bucket(e) for e in items).most_common(1)[0][0]

    def dominant_group(items: list[dict[str, Any]]) -> str:
        return Counter(e["spec"].group for e in items).most_common(1)[0][0]

    def hardness(items: list[dict[str, Any]]) -> int:
        return sum(len(e["spec"].tags) for e in items)

    per_stratum: dict[str, list[str]] = defaultdict(list)
    for cluster_id, items in by_cluster.items():
        per_stratum[stratum(items)].append(cluster_id)

    # Phân tầng theo mức kết cục (ESI 1, 2, 3, 4-5, chuyển nhân viên y tế) để mọi
    # tập đều có đủ các mức. Trong một tầng, các cụm được xen kẽ theo nhóm tình
    # huống (nhóm khó trước, trong nhóm thì cụm nhiều nhãn tình huống biên trước),
    # rồi mỗi cụm vào tập còn thiếu nhiều nhất so với hạn mức làm tròn 15/15/70.
    # Hoà thì ưu tiên test, nên test nhận ca khó trước mà vẫn trải đều các nhóm.
    group_order = ["MISSING_INFO", "CONFLICTING", "COMPLEX_DIALOGUE", "RED_FLAG", "MULTI_SYMPTOM", "COMMON"]
    priority = {"test": 2, "validation": 1, "train": 0}
    for _stratum, all_ids in sorted(per_stratum.items()):
        total = sum(len(by_cluster[cid]) for cid in all_ids)
        quota = {"test": round(total * SPLIT_SHARE["test"]), "validation": round(total * SPLIT_SHARE["validation"])}
        quota["train"] = total - quota["test"] - quota["validation"]
        counts = {split: 0 for split in SPLITS}
        for cid in all_ids:
            if cid in locked_split:
                counts[locked_split[cid]] += len(by_cluster[cid])
                for entry in by_cluster[cid]:
                    entry["split"] = locked_split[cid]
                    entry["split_cluster"] = cid
        lanes: dict[str, list[str]] = defaultdict(list)
        for cid in all_ids:
            if cid not in locked_split:
                lanes[dominant_group(by_cluster[cid])].append(cid)
        if not lanes:
            continue
        for lane in lanes.values():
            lane.sort(key=lambda cid: (-hardness(by_cluster[cid]), hashlib.sha1(cid.encode()).hexdigest()))
        ordered_lanes = [lanes[g] for g in group_order if g in lanes]
        cluster_ids = [lane[i] for i in range(max(map(len, ordered_lanes))) for lane in ordered_lanes if i < len(lane)]
        for cid in cluster_ids:
            open_splits = [s for s in SPLITS if counts[s] < quota[s]] or ["train"]
            split = max(open_splits, key=lambda s: ((quota[s] - counts[s]) / max(quota[s], 1), priority[s]))
            counts[split] += len(by_cluster[cid])
            for entry in by_cluster[cid]:
                entry["split"] = split
                entry["split_cluster"] = cid
    for entry in entries:
        if entry["ground_truth"]["status"] != VERIFIED:
            entry["split"] = REVIEW_FILE
            entry["split_cluster"] = None


def choose_smoke(entries: list[dict[str, Any]], lock: dict[str, dict[str, Any]] | None = None,
                 overrides: dict[str, str] | None = None) -> None:
    """Mỗi tệp một ca smoke: ca ESI 2 quyết định ngay, ít dữ kiện nhất, nhãn đã kiểm chứng nếu có.

    Ca smoke đã khoá được giữ nguyên; tệp nào đã có ca smoke khoá thì không chọn thêm. ``overrides``
    (tập -> mã kịch bản, chỉ dùng cùng ``--relock --allow smoke``) đặt ca smoke của tập đó một cách có chủ
    đích, thay cho ca đã khoá.
    """
    lock = lock or {}
    overrides = overrides or {}
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        by_split[entry["split"]].append(entry)
        if entry["split"] in overrides:
            chosen = entry["spec"].case_id == overrides[entry["split"]]
            entry["record"] = entry["record"].model_copy(update={"smoke": chosen})
            continue
        locked = lock.get(entry["record"].case_id)
        if locked and locked["smoke"]:
            entry["record"] = entry["record"].model_copy(update={"smoke": True})
    for split, key in overrides.items():
        if not any(e["spec"].case_id == key for e in by_split.get(split, [])):
            raise BuildError(f"--smoke {split}={key}: no such scenario in {split}")
    for split, items in by_split.items():
        if any(e["record"].smoke for e in items):
            continue
        candidates = [e for e in items if e["label"]["level"] in (1, 2) and e["spec"].group in {"COMMON", "RED_FLAG"}]
        candidates = candidates or [e for e in items if e["label"]["level"] is not None] or items
        best = sorted(candidates, key=lambda e: (len(e["spec"].facts), e["record"].case_id))[0]
        best["record"] = best["record"].model_copy(update={"smoke": True})
    for split, items in by_split.items():
        count = sum(1 for e in items if e["record"].smoke)
        if count != 1:
            raise BuildError(f"{split} has {count} smoke cases; expected exactly one")


def verify_lock(entries: list[dict[str, Any]], lock: dict[str, dict[str, Any]]) -> None:
    """Mọi bản ghi đã khoá phải còn đủ, cùng tập và trùng từng byte với lúc khoá."""
    by_id = {e["record"].case_id: e for e in entries}
    problems = []
    for case_id, locked in lock.items():
        entry = by_id.get(case_id)
        if entry is None:
            problems.append(f"{locked['scenario_key']} ({case_id}) is locked but no longer built")
            continue
        if entry["split"] != locked["split"]:
            problems.append(f"{locked['scenario_key']} moved from {locked['split']} to {entry['split']}")
        digest = hashlib.sha256(entry["record"].model_dump_json().encode("utf-8")).hexdigest()
        if digest != locked["record_sha256"]:
            problems.append(f"{locked['scenario_key']} ({case_id}) changed since it was locked")
    if problems:
        raise BuildError("locked records drifted: " + "; ".join(problems[:20]))


def _diff_paths(old: Any, new: Any, prefix: str = "") -> list[str]:
    if isinstance(old, dict) and isinstance(new, dict):
        paths: list[str] = []
        for key in sorted(set(old) | set(new)):
            paths += _diff_paths(old.get(key), new.get(key), f"{prefix}.{key}" if prefix else key)
        return paths
    return [] if old == new else [prefix]


def field_allowed(path: str, allowed: set[str] | list[str]) -> bool:
    """``expected_state.facts`` cho phép cả ``expected_state.facts.fact_target:x``."""
    return any(path == field or path.startswith(field + ".") for field in allowed)


def relock(entries: list[dict[str, Any]], lock: dict[str, dict[str, Any]], reason: str, allowed: set[str]) -> None:
    """Sửa có chủ đích một bản ghi đã khoá: chỉ cho phép đổi các trường được nêu tên.

    So từng bản ghi mới với bản ghi đang nằm trên đĩa (phải trùng sha256 đã khoá), từ chối
    nếu có bản ghi đổi tập, đổi cờ smoke hoặc đổi một trường ngoài ``allowed``, rồi ghi
    sha256 mới vào ``split_lock.json`` kèm một dòng nhật ký sửa đổi.
    """
    on_disk: dict[str, str] = {}
    for name in (*SPLITS, REVIEW_FILE):
        path = OUT_DIR / f"{name}.jsonl"
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    on_disk[json.loads(line)["case_id"]] = line
    by_id = {e["record"].case_id: e for e in entries}
    changed: list[dict[str, Any]] = []
    smoke_changes = 0
    for case_id, locked in lock.items():
        entry = by_id.get(case_id)
        if entry is None or entry["split"] != locked["split"]:
            raise BuildError(f"relock refused: {locked['scenario_key']} is missing or moved to another split")
        if entry["record"].smoke != locked["smoke"]:
            if "smoke" not in allowed:
                raise BuildError(f"relock refused: {locked['scenario_key']} changed its smoke flag without --allow smoke")
            smoke_changes += 1
            locked["smoke"] = entry["record"].smoke
        new_line = entry["record"].model_dump_json()
        digest = hashlib.sha256(new_line.encode("utf-8")).hexdigest()
        if digest == locked["record_sha256"]:
            continue
        old_line = on_disk.get(case_id)
        if old_line is None or hashlib.sha256(old_line.encode("utf-8")).hexdigest() != locked["record_sha256"]:
            raise BuildError(f"relock refused: the on-disk copy of {locked['scenario_key']} is not the locked version")
        paths = _diff_paths(json.loads(old_line), json.loads(new_line))
        outside = sorted(p for p in paths if not field_allowed(p, allowed))
        if outside:
            raise BuildError(f"relock refused: {locked['scenario_key']} changes fields outside {sorted(allowed)}: {outside}")
        changed.append({"case_id": case_id, "scenario_key": locked["scenario_key"], "fields": paths,
                        "old_sha256": locked["record_sha256"], "new_sha256": digest})
        locked["record_sha256"] = digest
    document = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    document["records"] = lock
    document.setdefault("revisions", []).append({
        "generator_version": GENERATOR_VERSION,
        "reason": reason,
        "allowed_fields": sorted(allowed),
        "records_changed": len(changed),
        "split_changes": 0,
        "smoke_changes": smoke_changes,
        "changes": changed,
    })
    LOCK_FILE.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"relocked {len(changed)} record(s): {', '.join(c['scenario_key'] for c in changed)}", file=sys.stderr)


LOCK_PURPOSE = (
    "Các đợt đã khoá giữ nguyên: mỗi bản ghi giữ tập, cụm, cờ smoke và từng byte khi bộ ca được mở rộng, trừ các sửa đổi có chủ đích ghi trong 'revisions' (chỉ ở trường được nêu tên; không bao giờ đổi tập; cờ smoke chỉ đổi khi cho phép rõ). Ca mới gần trùng với một ca đã khoá phải vào đúng tập của ca đó."
)


def lock_batch(entries: list[dict[str, Any]], lock: dict[str, dict[str, Any]], batch: int, frozen_on: str) -> None:
    """Khoá thêm một đợt đã hoàn tất: ghi tập, cụm, cờ smoke và sha256 của từng bản ghi của đợt đó.

    Từ đó các bản ghi này được bảo vệ như đợt 1: lần dựng sau dừng nếu chúng đổi, và chỉ sửa được qua --relock.
    """
    document = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    batches = document.get("locked_batches") or [
        {"batch": document.get("batch", 1), "frozen_on": document.get("frozen_on"), "records": len(document["records"])}
    ]
    if any(item["batch"] == batch for item in batches):
        raise BuildError(f"batch {batch} is already locked")
    added = 0
    for entry in entries:
        if BATCH_OF.get(entry["spec"].case_id) != batch:
            continue
        record = entry["record"]
        if record.case_id in lock:
            raise BuildError(f"{entry['spec'].case_id} of batch {batch} is already in the lock")
        lock[record.case_id] = {
            "scenario_key": entry["spec"].case_id,
            "split": entry["split"],
            "split_cluster": entry["split_cluster"],
            "smoke": record.smoke,
            "record_sha256": hashlib.sha256(record.model_dump_json().encode("utf-8")).hexdigest(),
        }
        added += 1
    if not added:
        raise BuildError(f"batch {batch} has no records to lock")
    batches.append({"batch": batch, "frozen_on": frozen_on, "records": added})
    new_document = {
        "schema_version": "generated-mock-v2-split-lock-v2",
        "locked_batches": batches,
        "purpose": LOCK_PURPOSE,
        "records": lock,
        "revisions": document.get("revisions", []),
    }
    LOCK_FILE.write_text(json.dumps(new_document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"locked batch {batch}: {added} record(s)", file=sys.stderr)


# --------------------------------------------------------------------------- ghi tệp


def _payload(records: list[GoldenCase]) -> str:
    return "\n".join(record.model_dump_json() for record in records) + "\n"


def write_outputs(entries: list[dict[str, Any]], corpus: CorpusSnapshot) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for split in (*SPLITS, REVIEW_FILE):
        chosen = sorted((e for e in entries if e["split"] == split), key=lambda e: e["record"].case_id)
        records = [e["record"] for e in chosen]
        payload = _payload(records)
        path = OUT_DIR / f"{split}.jsonl"
        path.write_bytes(payload.encode("utf-8"))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        manifest = {
            "schema_version": "simple-agent-golden-manifest-v1",
            "dataset_sha256": digest,
            "table_counts": corpus.table_counts,
            "table_fingerprints": corpus.table_fingerprints,
            "selected_atom_ids": [r.postgres_provenance["protocol_atom_id"] for r in records if r.postgres_provenance.get("protocol_atom_id")],
            "selected_concept_ids": sorted({c for r in records for c in r.postgres_provenance.get("concept_ids", [])}),
            "embedding_dimensions": sorted(set(corpus.fact_embedding_dimensions.values())),
            "category_counts": dict(sorted(Counter(r.category for r in records).items())),
        }
        (OUT_DIR / f"{split}.manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        files[split] = {"records": len(records), "sha256": digest, "smoke_case_ids": [r.case_id for r in records if r.smoke]}

    metadata_lines = []
    for entry in sorted(entries, key=lambda e: e["record"].case_id):
        spec: Spec = entry["spec"]
        record: GoldenCase = entry["record"]
        label = entry["label"]
        metadata_lines.append(json.dumps({
            "case_id": record.case_id,
            "scenario_key": spec.case_id,
            "batch": BATCH_OF.get(spec.case_id),
            "split": entry["split"],
            "split_cluster": entry["split_cluster"],
            "group": spec.group,
            "family": spec.family,
            "title": spec.title,
            "test_value": spec.test,
            "narrator": "SELF" if spec.profile["relationship_type"] == "SELF" else "CAREGIVER",
            "surface_style": list(spec.style),
            "edge_tags": list(spec.tags),
            "age_group": record.profile["age_band"],
            "age_months": spec.profile["age_months"],
            "older_adult": spec.profile["age_years"] >= 65,
            "contradiction": list(spec.conflict),
            "label": {
                "esi": label["level"],
                "terminal_action": record.expected_decision["terminal_action"],
                "computed_by": "eval.simple_runtime.golden_validator.satisfied_esi",
                "patient_only_esi": label["patient_only_level"],
                "depends_on_clinician_only_fact": spec.resources is not None,
                "resource_count": spec.resources,
                "resource_basis": spec.resource_basis or None,
                "primary_atom_id": label["primary"]["atom_id"] if label["primary"] else None,
                "matched_atoms": [
                    {k: v for k, v in item.items() if not k.startswith("_")} for item in label["matched"]
                ],
            },
            "ahrq_review": entry["ahrq"],
            "emergency_screen": entry["screen"],
            "ground_truth": entry["ground_truth"],
            "provenance": {
                "data_origin": "SYNTHETIC",
                "authoring": "synthetic scenario specification written with an LLM assistant at the project owner's request, not clinician-reviewed; label computed, not written",
                "generator_version": GENERATOR_VERSION,
                "contains_real_person_data": False,
            },
        }, ensure_ascii=False))
    (OUT_DIR / "metadata.jsonl").write_bytes(("\n".join(metadata_lines) + "\n").encode("utf-8"))
    return files


def write_dataset_manifest(entries: list[dict[str, Any]], files: dict[str, dict[str, Any]], corpus: CorpusSnapshot,
                           ref: ahrq_review.AhrqReference) -> dict[str, Any]:
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        by_group[entry["spec"].group].append(entry)

    def sources(items: list[dict[str, Any]]) -> dict[str, Any]:
        primaries = [corpus.atoms[e["label"]["primary"]["atom_id"]] for e in items if e["label"]["primary"]]
        citations = Counter(f["citation_id"] for e in items for f in e["ahrq"]["findings"])
        return {
            "records": len(items),
            "label_source_documents": dict(Counter(a.get("source_document_id") for a in primaries)),
            "label_authority_scope": dict(Counter(a.get("authority_scope") for a in primaries)),
            "label_decision_points": dict(Counter(a.get("decision_point") for a in primaries)),
            "handoff_records_without_matching_criterion": sum(1 for e in items if e["label"]["level"] is None),
            "independent_review_document": "data/protocols/ahrq_esi_v5.draft-manifest.json (AHRQ ESI Implementation Handbook v5, bản trích)",
            "independent_review_citations": dict(citations.most_common()),
            "ground_truth": dict(Counter(e["ground_truth"]["status"] for e in items)),
        }

    metadata_bytes = (OUT_DIR / "metadata.jsonl").read_bytes()
    roles = {
        "train": "Ca đã kiểm chứng theo hướng dẫn; dùng để xây dựng hoặc làm ví dụ.",
        "validation": "Ca đã kiểm chứng; dùng để chọn cấu hình, prompt, ngưỡng.",
        "test": "Ca đã kiểm chứng; chỉ dùng để báo cáo kết quả cuối. Không dùng để tinh chỉnh.",
        REVIEW_FILE: "Nhãn chưa kiểm chứng được bằng văn bản hướng dẫn; chờ chuyên gia y tế. Không dùng để huấn luyện hay chấm điểm.",
    }
    manifest = {
        "schema_version": "generated-mock-v2-dataset-manifest-v1",
        "dataset": "generated_mock_v2",
        "generator_version": GENERATOR_VERSION,
        "data_origin": "SYNTHETIC",
        "contains_real_person_data": False,
        "clinical_review_status": f"PENDING_CLINICAL_REVIEW cho cả {len(entries)} bản ghi: chưa có chuyên gia y tế nào duyệt.",
        "record_schema": "eval.simple_runtime.schemas.GoldenCase (schema_version simple-agent-golden-v1), cùng bộ khoá với eval/cases/simple_agent_golden_300.jsonl",
        "runner": "python -m eval.run --cases eval/generated_mock_v2/<tệp>.jsonl (mỗi tệp có <tệp>.manifest.json và một ca smoke)",
        "files": {
            name: {
                "path": f"eval/generated_mock_v2/{name}.jsonl",
                "runner_manifest": f"eval/generated_mock_v2/{name}.manifest.json",
                "records": info["records"],
                "sha256": info["sha256"],
                "smoke_case_ids": info["smoke_case_ids"],
                "category_counts": dict(sorted(Counter(e["record"].category for e in entries if e["split"] == name).items())),
                "role": roles[name],
            }
            for name, info in files.items()
        },
        "metadata": {
            "path": "eval/generated_mock_v2/metadata.jsonl",
            "records": len(entries),
            "sha256": hashlib.sha256(metadata_bytes).hexdigest(),
            "content": "nhóm, gia đình kịch bản, kiểu lời kể, nhãn tình huống biên, tiêu chí khớp, kết luận đối chiếu AHRQ, bộ lọc khẩn cấp, lý do cần duyệt, nguồn gốc SYNTHETIC",
        },
        "batches": {
            str(batch): {
                "records": sum(1 for e in entries if BATCH_OF.get(e["spec"].case_id) == batch),
                "by_file": dict(sorted(Counter(e["split"] for e in entries if BATCH_OF.get(e["spec"].case_id) == batch).items())),
                "labels": dict(sorted(Counter(e["record"].category for e in entries if BATCH_OF.get(e["spec"].case_id) == batch).items())),
                "groups": dict(Counter(e["spec"].group for e in entries if BATCH_OF.get(e["spec"].case_id) == batch)),
            }
            for batch in sorted({BATCH_OF.get(e["spec"].case_id) for e in entries}, key=lambda b: (b is None, b))
        },
        "split_lock": {
            "path": "eval/generated_mock_v2/split_lock.json",
            "sha256": hashlib.sha256(LOCK_FILE.read_bytes()).hexdigest() if LOCK_FILE.exists() else None,
            "records": len(load_lock()),
            "content": "case_id -> tập, cụm, cờ smoke và sha256 của từng bản ghi thuộc các đợt đã khoá (locked_batches), cùng nhật ký các lần sửa có chủ đích",
        },
        "corpus": {"table_counts": corpus.table_counts, "table_fingerprints": corpus.table_fingerprints},
        "distributions": {
            "groups": dict(Counter(e["spec"].group for e in entries)),
            "labels": dict(sorted(Counter(e["record"].category for e in entries).items())),
            "ground_truth": dict(Counter(e["ground_truth"]["status"] for e in entries)),
            "ahrq_verdicts": dict(Counter(e["ahrq"]["verdict"] for e in entries)),
            "age_band": dict(Counter(e["record"].profile["age_band"] for e in entries)),
            "sex": dict(Counter(e["record"].profile["sex"] for e in entries)),
            "narrator": dict(Counter("SELF" if e["spec"].profile["relationship_type"] == "SELF" else "CAREGIVER" for e in entries)),
        },
        "guideline_sources_by_group": {group: sources(items) for group, items in sorted(by_group.items())},
        "label_policy": [
            "Nhãn KHÔNG do người viết gán: được tính bằng eval.simple_runtime.golden_validator.satisfied_esi trên mọi tiêu chí CLINICAL_AUTHORITY / DECISION_CRITERION / ASSIGN_ESI của corpus PostgreSQL; lấy mức ESI thấp nhất (khẩn cấp nhất) khớp được.",
            "Thiếu dữ kiện bắt buộc thì tiêu chí không khớp (UNKNOWN khác NEGATIVE). Không tiêu chí nào khớp thì kỳ vọng là RETURN_INCOMPLETE: agent phải chuyển nhân viên y tế, không tự điền giá trị.",
            "resource_count là dữ kiện CLINICIAN_ONLY; chỉ được đưa vào ca khi nó đổi nhãn, và phải ghi căn cứ (Table 5-2 hoặc lập luận theo Table 5-1).",
            "Dự định của người viết được so với nhãn tính được; lệch là lỗi dựng và script dừng, không sửa nhãn cho khớp.",
        ],
        "ground_truth_policy": [
            "GUIDELINE_VERIFIED: nhãn tính từ corpus, đối chiếu AHRQ v5 là AGREE hoặc CONSISTENT, không dựa vào số nguồn lực ngoài 6 ca mẫu Table 5-2, không có lo ngại lâm sàng của người viết.",
            "NEEDS_MEDICAL_REVIEW: mọi trường hợp còn lại (AHRQ CANNOT_VERIFY / DISAGREE_UNDER / DISAGREE_OVER, số nguồn lực do người viết dự đoán, hoặc lo ngại ghi trong review_concern). Nằm riêng trong needs_medical_review.jsonl.",
            "Cả hai loại đều vẫn là PENDING_CLINICAL_REVIEW: 'đã kiểm chứng theo hướng dẫn' không có nghĩa là đã được bác sĩ duyệt.",
        ],
        "split_policy": [
            "Chỉ ca GUIDELINE_VERIFIED được chia train/validation/test; tỉ lệ mục tiêu 70/15/15.",
            "Đơn vị chia là cụm: các ca cùng gia đình kịch bản (ví dụ cặp tối thiểu m09/m10, r08/m40) hoặc gần trùng (cùng bộ dữ kiện, hoặc 4-gram Jaccard của lời mở đầu >= 0.5) luôn nằm chung một tập.",
            "Phân tầng theo mức kết cục (ESI 1, 2, 3, 4-5, chuyển nhân viên y tế); trong mỗi tầng các cụm được xen kẽ theo nhóm tình huống, cụm nhiều nhãn tình huống biên đi trước và ưu tiên vào test.",
            "Bộ ca chỉ được nối thêm: bản ghi của các đợt đã khoá trong split_lock.json (locked_batches) giữ nguyên tập, cờ smoke và từng byte (build_dataset và validate_dataset đều kiểm tra); sửa có chủ đích đi qua --relock và được ghi nhật ký. Hạn mức 70/15/15 của mỗi tầng tính trên tổng cũ + mới, ca mới lấp phần còn thiếu; cụm có ca đã khoá đi theo tập đã khoá.",
        ],
        "usage_policy": [
            "Không dùng test.jsonl để chỉnh prompt, ngưỡng, mô hình hay chọn cấu hình. Dùng validation.jsonl cho việc đó.",
            "Không dùng needs_medical_review.jsonl để huấn luyện hay báo cáo độ chính xác cho tới khi có chuyên gia y tế duyệt và ghi lại nhãn.",
            "Mọi kết quả đo trên bộ ca này phải ghi rõ: dữ liệu tổng hợp, nhãn chưa được chuyên gia duyệt.",
        ],
        "schema_extensions": [
            {"field": "category", "new_value": "incomplete",
             "reason": "Ca kỳ vọng RETURN_INCOMPLETE không có mức ESI nên không thể dùng esi_N; eval/run.py chỉ xử lý riêng 'guardrail', các giá trị khác là chuỗi tự do."},
            {"field": "profile.age_band", "new_values": ["neonate", "infant", "toddler", "preschooler", "school_age", "adolescent"],
             "reason": "Bộ cũ chỉ có 'adult'. Giá trị mới theo đúng các nhóm tuổi của AHRQ Table 6-1; không có mã nào trong repo đọc trường này."},
        ],
        "assumptions": [
            "Nhóm tuổi: dưới 1 tháng = neonate, 1-11 tháng = infant, 1-2 tuổi = toddler, 3-4 = preschooler, 5-11 = school_age, 12-17 = adolescent, từ 18 trở lên = adult; không dùng tuổi 18 vì AHRQ để mốc này chồng lấn.",
            "Người cao tuổi (>= 65) được đánh dấu trong metadata (older_adult); AHRQ không có nhóm tuổi riêng cho người cao tuổi.",
            "Câu trả lời mặc định 'Tôi chưa rõ thông tin này.' cho mọi dữ kiện kịch bản không nhắc tới được giữ như bộ cũ, để agent không nhận giá trị bịa.",
            "presentation.style giữ giá trị 'controlled' như bộ cũ; kiểu lời kể chi tiết (không dấu, viết tắt, phương ngữ...) nằm trong metadata.surface_style và edge_tags.",
            "Tên thuốc trong hồ sơ là tên hoạt chất phổ biến, là thuốc người bệnh đang dùng, không phải chỉ định.",
        ],
        "known_limitations": [
            "Toàn bộ là dữ liệu tổng hợp; kịch bản do mô hình ngôn ngữ soạn theo yêu cầu của chủ dự án, chưa có chuyên gia y tế duyệt.",
            "Mức ESI 4/5 phụ thuộc số nguồn lực (CLINICIAN_ONLY); chỉ 4 ca mẫu Table 5-2 được coi là đã kiểm chứng, các ca 4/5 khác nằm trong hàng chờ duyệt.",
            "Bộ ca đã kiểm chứng lệch về ESI 2 vì corpus có 474 tiêu chí ESI 2 mà chỉ có 20 tiêu chí ESI 1 người bệnh tự khai được.",
            "Bản trích AHRQ v5 dùng để đối chiếu chính nó đang NOT_READY_FOR_INGESTION / REQUIRES_CLINICAL_OWNER.",
            "Hội thoại được mô phỏng bằng câu trả lời cố định theo dữ kiện; agent hỏi gì ngoài kịch bản sẽ nhận 'chưa rõ'.",
        ],
        "reference": {"ahrq_manifest_status": ref.chunks["ahrq_esi_v5-001"]["validation_status"]},
    }
    (OUT_DIR / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def ground_truth(spec: Spec, ahrq: dict[str, Any]) -> dict[str, Any]:
    reasons = []
    for finding in ahrq["findings"]:
        if finding["effect"] in ahrq_review.NEEDS_REVIEW_VERDICTS:
            reasons.append(f"{finding['rule_id']} ({finding['effect']}): {finding['detail']}")
    if spec.review_concern:
        reasons.append(f"AUTHOR_CONCERN: {spec.review_concern}")
    return {"status": NEEDS_REVIEW if reasons else VERIFIED, "reasons": reasons}


def main() -> int:
    parser = argparse.ArgumentParser(description="Dựng bộ ca generated_mock_v2.")
    parser.add_argument("--relock", metavar="LÝ_DO", help="Chấp nhận sửa có chủ đích ở bản ghi đã khoá và ghi lý do vào split_lock.json.")
    parser.add_argument("--allow", action="append", default=[], metavar="TRƯỜNG",
                        help="Trường được phép đổi khi --relock, ví dụ adaptive_dialogue.clarification_reply (lặp lại được).")
    parser.add_argument("--lock-batch", type=int, metavar="ĐỢT",
                        help="Khoá một đợt đã hoàn tất vào split_lock.json (cần --frozen-on).")
    parser.add_argument("--frozen-on", metavar="YYYY-MM-DD", help="Ngày khoá ghi vào split_lock.json.")
    parser.add_argument("--smoke", action="append", default=[], metavar="TẬP=KỊCH_BẢN",
                        help="Đặt ca smoke của một tệp (chỉ cùng --relock và --allow smoke), ví dụ train=r15.")
    args = parser.parse_args()
    if args.relock and not args.allow:
        parser.error("--relock cần ít nhất một --allow")
    if args.smoke and not (args.relock and "smoke" in args.allow):
        parser.error("--smoke chỉ dùng cùng --relock và --allow smoke")
    smoke_overrides = dict(item.split("=", 1) for item in args.smoke)
    if bool(args.lock_batch) != bool(args.frozen_on):
        parser.error("--lock-batch và --frozen-on phải đi cùng nhau")
    from .scenarios import ALL_SPECS, BATCH_OF as batch_of  # noqa: PLC0415 - xem ghi chú ở BATCH_OF

    BATCH_OF.update(batch_of)
    corpus = load_postgres_corpus()
    ref = ahrq_review.load_reference()
    keys = Counter(spec.case_id for spec in ALL_SPECS)
    duplicated = [key for key, count in keys.items() if count > 1]
    if duplicated:
        raise BuildError(f"duplicate scenario keys: {duplicated}")
    errors: list[str] = []
    entries: list[dict[str, Any]] = []
    for spec in ALL_SPECS:
        try:
            validate_spec(spec, corpus)
            label = compute_label(spec, corpus)
            record = build_record(spec, label, corpus)
        except BuildError as exc:
            errors.append(str(exc))
            continue
        ahrq = ahrq_review.review(
            ref,
            label=label["level"],
            patient_facts=label["patient_facts"],
            resources=spec.resources,
            resource_basis=spec.resource_basis,
            age_years=spec.profile["age_years"],
            age_months=spec.profile["age_months"],
            matched_atoms=label["matched"],
        )
        entries.append({
            "spec": spec,
            "label": label,
            "record": record,
            "ahrq": ahrq,
            "screen": screen_check(spec, record),
            "ground_truth": ground_truth(spec, ahrq),
            "signature": fact_signature(record.expected_state["facts"]),
            "shingles": shingles(spec.opening),
        })
    if errors:
        print(f"{len(errors)} scenario(s) failed:", file=sys.stderr)
        for line in errors:
            print("  -", line, file=sys.stderr)
        return 1
    ids = Counter(entry["record"].case_id for entry in entries)
    if any(count > 1 for count in ids.values()):
        raise BuildError("opaque case id collision")
    lock = load_lock()
    assign_splits(entries, lock)
    choose_smoke(entries, lock, smoke_overrides)
    if args.relock:
        relock(entries, lock, args.relock, set(args.allow))
    verify_lock(entries, lock)
    if args.lock_batch:
        lock_batch(entries, lock, args.lock_batch, args.frozen_on)
    files = write_outputs(entries, corpus)
    manifest = write_dataset_manifest(entries, files, corpus, ref)
    print(json.dumps({
        "files": {name: (info["records"], info["smoke_case_ids"]) for name, info in files.items()},
        **manifest["distributions"],
        "screen_mismatches": [e["spec"].case_id for e in entries if not e["screen"]["matches_expectation"]],
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
