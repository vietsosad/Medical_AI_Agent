"""Kiểm tra độc lập bộ ca generated_mock_v2 và ghi ``validation_report.md``.

Không tin vào metadata do ``build_dataset.py`` ghi ra: nhãn, tiêu chí khớp, vân
tay corpus, trùng lặp, rò rỉ giữa các tập và độ phủ đều được tính lại từ chính các
tệp JSONL và từ PostgreSQL. Bản ghi đợt 1 được đối chiếu từng byte với
``split_lock.json``.

Chạy đầy đủ (cần PostgreSQL, trong container backend):

    MSYS_NO_PATHCONV=1 docker exec -i -e PYTHONIOENCODING=utf-8 -w /app triage_backend \
        python -m eval.generated_mock_v2.validate_dataset

Chạy ngoài container (chỉ thư viện chuẩn; bỏ qua các kiểm tra cần corpus):

    python eval/generated_mock_v2/validate_dataset.py --offline

Mã thoát khác 0 khi có ít nhất một kiểm tra FAIL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPLITS = ("train", "validation", "test")
REVIEW = "needs_medical_review"
FILES = (*SPLITS, REVIEW)
REFERENCE_DATASETS = (REPO / "eval/cases/simple_agent_golden_30.jsonl", REPO / "eval/cases/simple_agent_golden_300.jsonl")
FT = "fact_target:"
ALLOWED_CATEGORIES = {"esi_1", "esi_2", "esi_3", "esi_4", "esi_5", "incomplete"}
ALLOWED_AGE_BANDS = {"neonate", "infant", "toddler", "preschooler", "school_age", "adolescent", "adult"}
ALLOWED_SEX = {"Male", "Female", "Other"}
ALLOWED_RELATIONSHIP = {"SELF", "CHILD", "SPOUSE", "PARENT", "SIBLING", "OTHER"}
UNKNOWN_DEFAULT = "Tôi chưa rõ thông tin này."
NEAR_DUPLICATE_JACCARD = 0.5
COPY_OF_EXISTING_JACCARD = 0.8
SAFETY_KEYS_TRUE = ("must_not_undertriage", "must_not_assert_diagnosis", "must_not_prescribe")
#: Đợt 1 (200 bản ghi, đã khoá) + đợt 2 (200 bản ghi).
RECORDS_PER_BATCH = {1: 200, 2: 200, 3: 190}
EXPECTED_RECORDS = sum(RECORDS_PER_BATCH.values())
LOCK_FILE = HERE / "split_lock.json"
_ENUM_TOKEN = re.compile(r"\b[A-Z]{2,}(?:_[A-Z0-9]+)+\b")


@dataclass
class Check:
    name: str
    status: str = "PASS"  # PASS | FAIL | SKIPPED | INFO
    details: list[str] = field(default_factory=list)
    summary: str = ""

    def fail(self, message: str) -> None:
        self.status = "FAIL"
        self.details.append(message)


# --------------------------------------------------------------------------- tải dữ liệu


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_all() -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    data = {name: load_jsonl(HERE / f"{name}.jsonl") for name in FILES}
    metadata = {row["case_id"]: row for row in load_jsonl(HERE / "metadata.jsonl")}
    return data, metadata


def reference_schema() -> dict[str, set[str]]:
    """Bộ khoá của từng mục, lấy từ các ca triage của bộ 300 ca hiện có."""
    rows = [r for r in load_jsonl(REFERENCE_DATASETS[1]) if r.get("kind") == "triage"]
    sections = ("profile", "presentation", "expected_state", "adaptive_dialogue", "expected_retrieval",
                "expected_decision", "expected_safety", "postgres_provenance")
    schema = {"__top__": set(rows[0].keys())}
    for section in sections:
        keysets = {tuple(sorted(r[section].keys())) for r in rows}
        if len(keysets) != 1:
            raise RuntimeError(f"Reference dataset has inconsistent keys in {section}")
        schema[section] = set(next(iter(keysets)))
    schema["__answer_keys__"] = set(rows[0]["adaptive_dialogue"]["answers_by_fact_target"].keys())
    return schema


# --------------------------------------------------------------------------- tiện ích văn bản


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).replace("đ", "d")
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", text)).strip()


def shingles(text: str, size: int = 4) -> set[str]:
    norm = normalise(text)
    return {norm[i:i + size] for i in range(max(1, len(norm) - size + 1))}


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 0.0


def signature(record: dict[str, Any]) -> str:
    return json.dumps(sorted(record["expected_state"]["facts"].items()), ensure_ascii=False, default=str)


# --------------------------------------------------------------------------- kiểm tra cấu trúc


def check_structure(data: dict[str, list[dict[str, Any]]], schema: dict[str, set[str]]) -> Check:
    check = Check("1. Cấu trúc và kiểu dữ liệu so với schema hiện có")
    try:
        from eval.simple_runtime.schemas import GoldenCase  # noqa: PLC0415 - tuỳ chọn khi chạy ngoài container
    except Exception:  # pragma: no cover - chạy ngoài môi trường dự án
        GoldenCase = None
    total = 0
    for name, rows in data.items():
        if not any(r.get("smoke") for r in rows):
            check.fail(f"{name}.jsonl không có ca smoke nào (eval/run.py bắt buộc).")
        for r in rows:
            total += 1
            cid = r.get("case_id", "?")
            if GoldenCase is not None:
                try:
                    GoldenCase.model_validate(r)
                except Exception as exc:  # noqa: BLE001
                    check.fail(f"{cid}: GoldenCase từ chối bản ghi: {exc}")
            if set(r) != schema["__top__"]:
                check.fail(f"{cid}: khoá cấp ngoài khác schema: {sorted(set(r) ^ schema['__top__'])}")
            for section, keys in schema.items():
                if section.startswith("__"):
                    continue
                if set(r.get(section, {})) != keys:
                    check.fail(f"{cid}: khoá của {section} khác schema: {sorted(set(r.get(section, {})) ^ keys)}")
            prof, dec, pres = r["profile"], r["expected_decision"], r["presentation"]
            if r["schema_version"] != "simple-agent-golden-v1" or r["kind"] != "triage":
                check.fail(f"{cid}: schema_version/kind không hợp lệ")
            if r["clinical_review_status"] != "PENDING_CLINICAL_REVIEW":
                check.fail(f"{cid}: clinical_review_status phải là PENDING_CLINICAL_REVIEW (chưa có chuyên gia duyệt)")
            if r["category"] not in ALLOWED_CATEGORIES:
                check.fail(f"{cid}: category ngoài tập cho phép: {r['category']}")
            if not isinstance(prof["age_years"], int) or prof["sex"] not in ALLOWED_SEX \
                    or prof["relationship_type"] not in ALLOWED_RELATIONSHIP or prof["age_band"] not in ALLOWED_AGE_BANDS:
                check.fail(f"{cid}: profile có giá trị ngoài miền cho phép")
            for key in ("chronic_conditions", "allergies", "daily_medications"):
                if not isinstance(prof[key], list) or not all(isinstance(v, str) for v in prof[key]):
                    check.fail(f"{cid}: profile.{key} phải là list[str] (cột JSON của EHRProfile)")
            if pres["language"] != "vi" or pres["style"] != "controlled" or not isinstance(pres["contains_temporal_context"], bool):
                check.fail(f"{cid}: presentation có giá trị ngoài miền")
            if not pres["initial_message"] or not (pres["initial_message"][0].isupper() or pres["initial_message"][0].isdigit()):
                check.fail(f"{cid}: lời mở đầu phải bắt đầu bằng chữ hoa hoặc chữ số")
            esi = dec["esi"]
            if r["category"] == "incomplete":
                if esi is not None or dec["terminal_action"] != "RETURN_INCOMPLETE":
                    check.fail(f"{cid}: category incomplete phải đi với esi=None và RETURN_INCOMPLETE")
            elif not (isinstance(esi, int) and r["category"] == f"esi_{esi}" and dec["terminal_action"] == "RETURN_MATCH"):
                check.fail(f"{cid}: category/esi/terminal_action không khớp nhau")
            if dec["terminal_route"] != "TRIAGE":
                check.fail(f"{cid}: terminal_route phải là TRIAGE")
            safety = r["expected_safety"]
            if not all(safety[k] is True for k in SAFETY_KEYS_TRUE) or safety["must_refuse_prompt_probe"] is not False:
                check.fail(f"{cid}: cờ an toàn không đúng mặc định của ca triage")
            ad = r["adaptive_dialogue"]
            if set(ad["answers_by_fact_target"]) != schema["__answer_keys__"]:
                check.fail(f"{cid}: answers_by_fact_target không phủ đúng 233 dữ kiện người bệnh trả lời được")
            if sorted(ad["answers_by_fact_target"]) != ad["allowed_question_target_ids"]:
                check.fail(f"{cid}: allowed_question_target_ids không khớp khoá của answers_by_fact_target")
            if not ad["confirmation_reply"].strip() or not ad["clarification_reply"].strip():
                check.fail(f"{cid}: thiếu confirmation_reply hoặc clarification_reply (backend_client cần cả hai)")
            texts = [pres["initial_message"], ad["confirmation_reply"], ad["clarification_reply"], *ad["answers_by_fact_target"].values()]
            leaked = [t for t in texts if _ENUM_TOKEN.search(t)]
            if leaked:
                check.fail(f"{cid}: chữ enum tiếng Anh lọt vào lời người bệnh: {leaked[0][:80]!r}")
    ids = [r["case_id"] for rows in data.values() for r in rows]
    dupes = [cid for cid, n in Counter(ids).items() if n > 1]
    if dupes:
        check.fail(f"case_id trùng giữa các tệp: {dupes}")
    if len(ids) != EXPECTED_RECORDS:
        check.fail(f"Tổng số bản ghi là {len(ids)}, yêu cầu {EXPECTED_RECORDS}.")
    check.summary = f"{total} bản ghi, {len(FILES)} tệp; mỗi tệp có ca smoke; khoá từng mục so với {REFERENCE_DATASETS[1].name}."
    return check


def check_dialogue_consistency(data: dict[str, list[dict[str, Any]]]) -> Check:
    check = Check("2. Lời thoại khớp với dữ kiện kỳ vọng")
    n_answers = n_unknown = 0
    for rows in data.values():
        for r in rows:
            cid = r["case_id"]
            st, ad = r["expected_state"], r["adaptive_dialogue"]
            answers = ad["answers_by_fact_target"]
            facts = {k: v for k, v in st["facts"].items() if k != FT + "resource_count"}
            for fact_id in facts:
                n_answers += 1
                if answers.get(fact_id) in (None, UNKNOWN_DEFAULT):
                    check.fail(f"{cid}: dữ kiện {fact_id} có giá trị nhưng câu trả lời là 'chưa rõ'")
            for fact_id in st["unknown_fact_ids"]:
                n_unknown += 1
                if fact_id in st["facts"]:
                    check.fail(f"{cid}: {fact_id} vừa có giá trị vừa nằm trong unknown_fact_ids")
                if answers.get(fact_id) in (None, ""):
                    check.fail(f"{cid}: {fact_id} không biết nhưng không có câu trả lời")
            rc = st["resource_count"]
            if rc is not None:
                if st["clinician_only_facts"] != {FT + "resource_count": rc} or st["facts"].get(FT + "resource_count") != rc \
                        or r["expected_decision"]["resource_count"] != rc:
                    check.fail(f"{cid}: resource_count không nhất quán giữa facts, clinician_only_facts và expected_decision")
            elif st["clinician_only_facts"] or r["expected_decision"]["resource_count"] is not None:
                check.fail(f"{cid}: có clinician_only_facts dù resource_count là None")
    check.summary = f"{n_answers} dữ kiện có giá trị đều có câu trả lời riêng; {n_unknown} dữ kiện 'không biết' đều có câu trả lời nói rõ là không biết."
    return check


# --------------------------------------------------------------------------- kiểm tra theo corpus


def corpus_checks(data: dict[str, list[dict[str, Any]]], metadata: dict[str, dict[str, Any]]) -> list[Check]:
    from eval.simple_runtime.corpus_reader import load_postgres_corpus, row_fingerprint  # noqa: PLC0415
    from eval.simple_runtime.golden_validator import satisfied_esi  # noqa: PLC0415

    corpus = load_postgres_corpus()
    facts_check = Check("3. Dữ kiện hợp lệ theo schema của corpus PostgreSQL")
    label_check = Check("4. Nhãn tính lại độc lập bằng golden_validator.satisfied_esi")
    fp_check = Check("5. Vân tay corpus và checksum manifest")

    for rows in data.values():
        for r in rows:
            cid = r["case_id"]
            st = r["expected_state"]
            sex = r["profile"]["sex"]
            facts = st["facts"]
            for fact_id, value in facts.items():
                row = corpus.facts.get(fact_id)
                if row is None:
                    facts_check.fail(f"{cid}: dữ kiện không có trong corpus: {fact_id}")
                    continue
                if row.get("reporting_style") == "CLINICIAN_ONLY" and fact_id != FT + "resource_count":
                    facts_check.fail(f"{cid}: dữ kiện CLINICIAN_ONLY bị đặt vào lời người bệnh: {fact_id}")
                schema = row.get("value_schema") or {}
                allowed = schema.get("allowed_values")
                if allowed is not None and value not in allowed:
                    facts_check.fail(f"{cid}: {fact_id}={value!r} ngoài enum {allowed}")
                if allowed is None:
                    lo, hi = schema.get("minimum"), schema.get("maximum")
                    if not isinstance(value, (int, float)) or (lo is not None and value < lo) or (hi is not None and value > hi):
                        facts_check.fail(f"{cid}: {fact_id}={value!r} ngoài khoảng [{lo}, {hi}]")
                gate = row.get("gated_by")
                if gate and facts.get(gate["fact_target_id"]) != gate["expected_value"]:
                    facts_check.fail(f"{cid}: {fact_id} cần {gate['fact_target_id']}={gate['expected_value']}")
                if str(row.get("requires_sex") or "").upper().startswith("F") and sex != "Female":
                    facts_check.fail(f"{cid}: {fact_id} chỉ dùng cho nữ nhưng hồ sơ là {sex}")
            for fact_id in st["unknown_fact_ids"]:
                if fact_id not in corpus.facts:
                    facts_check.fail(f"{cid}: unknown_fact_id không có trong corpus: {fact_id}")
            for concept in (*st["concept_ids"], *st["negated_concept_ids"]):
                if concept not in corpus.concepts:
                    facts_check.fail(f"{cid}: concept không có trong corpus: {concept}")

            level, matched = satisfied_esi(corpus.atoms, facts)
            expected = r["expected_decision"]["esi"]
            if level != expected:
                label_check.fail(f"{cid}: nhãn ghi {expected}, tính lại được {level}")
            if sorted(matched) != r["expected_decision"]["acceptable_matched_atom_ids"]:
                label_check.fail(f"{cid}: tập tiêu chí khớp khác với lúc dựng")
            primary = r["expected_retrieval"]["primary_atom_id"]
            if (primary is None) != (expected is None) or (primary and primary not in matched):
                label_check.fail(f"{cid}: primary_atom_id không thuộc tập tiêu chí khớp")
            for atom_id in matched:
                if corpus.atoms[atom_id].get("authority_scope") != "CLINICAL_AUTHORITY":
                    label_check.fail(f"{cid}: tiêu chí khớp {atom_id} không phải CLINICAL_AUTHORITY")
            if st["resource_count"] is not None:
                without, _ = satisfied_esi(corpus.atoms, {k: v for k, v in facts.items() if k != FT + "resource_count"})
                if without == level:
                    label_check.fail(f"{cid}: resource_count có mặt nhưng không đổi nhãn (dữ kiện thừa của người dựng)")
            meta = metadata.get(cid)
            if meta is None or meta["label"]["esi"] != expected:
                label_check.fail(f"{cid}: metadata thiếu hoặc lệch nhãn")

            prov = r["postgres_provenance"]
            if primary:
                atom = corpus.atoms[primary]
                if prov["atom_fingerprint"] != row_fingerprint({k: v for k, v in atom.items() if k != "embedding"}):
                    fp_check.fail(f"{cid}: atom_fingerprint lệch với corpus hiện tại")
            for fact_id, fp in prov["fact_target_fingerprints"].items():
                if row_fingerprint(corpus.facts[fact_id]) != fp:
                    fp_check.fail(f"{cid}: fact fingerprint lệch: {fact_id}")
            for concept_id, fp in prov["concept_fingerprints"].items():
                if row_fingerprint(corpus.concepts[concept_id]) != fp:
                    fp_check.fail(f"{cid}: concept fingerprint lệch: {concept_id}")
            if sorted(facts) != prov["fact_target_ids"]:
                fp_check.fail(f"{cid}: fact_target_ids không khớp expected_state.facts")

    for name in FILES:
        manifest = json.loads((HERE / f"{name}.manifest.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256((HERE / f"{name}.jsonl").read_bytes()).hexdigest()
        if manifest["dataset_sha256"] != digest:
            fp_check.fail(f"{name}.manifest.json: dataset_sha256 không khớp tệp")
        if manifest["table_fingerprints"] != corpus.table_fingerprints:
            fp_check.fail(f"{name}.manifest.json: corpus đã thay đổi so với lúc dựng (table_fingerprints)")
    n = sum(len(rows) for rows in data.values())
    facts_check.summary = f"Mọi dữ kiện của {n} bản ghi nằm trong enum/khoảng của corpus, có dữ kiện mở cổng đi kèm, đúng giới tính."
    label_check.summary = f"{n} nhãn được tính lại từ {sum(1 for a in corpus.atoms.values() if a.get('authority_scope') == 'CLINICAL_AUTHORITY')} tiêu chí CLINICAL_AUTHORITY."
    fp_check.summary = "Vân tay tiêu chí, dữ kiện, concept và checksum của 4 manifest được đối chiếu với PostgreSQL hiện tại."
    return [facts_check, label_check, fp_check]


def independent_review(data: dict[str, list[dict[str, Any]]], metadata: dict[str, dict[str, Any]]) -> Check:
    """Chạy lại đối chiếu AHRQ từ chính bản ghi và so với metadata."""
    from eval.generated_mock_v2 import ahrq_review  # noqa: PLC0415

    check = Check("6. Đối chiếu độc lập với AHRQ ESI v5 và phân loại hàng chờ duyệt")
    ref = ahrq_review.load_reference(REPO / "data/protocols/ahrq_esi_v5.draft-manifest.json")
    verdicts: Counter[str] = Counter()
    for name, rows in data.items():
        for r in rows:
            cid = r["case_id"]
            meta = metadata[cid]
            facts = {k: v for k, v in r["expected_state"]["facts"].items() if k != FT + "resource_count"}
            matched = [{"atom_id": a["atom_id"], "patient_condition_facts": a["patient_condition_facts"]}
                       for a in meta["label"]["matched_atoms"]]
            result = ahrq_review.review(
                ref, label=r["expected_decision"]["esi"], patient_facts=facts,
                resources=r["expected_state"]["resource_count"], resource_basis=meta["label"]["resource_basis"] or "",
                age_years=r["profile"]["age_years"], age_months=meta["age_months"], matched_atoms=matched,
            )
            verdicts[result["verdict"]] += 1
            if result["verdict"] != meta["ahrq_review"]["verdict"]:
                check.fail(f"{cid}: kết luận AHRQ tính lại ({result['verdict']}) khác metadata ({meta['ahrq_review']['verdict']})")
            needs = result["verdict"] in ahrq_review.NEEDS_REVIEW_VERDICTS or any(
                reason.startswith("AUTHOR_CONCERN") for reason in meta["ground_truth"]["reasons"]
            )
            in_review = name == REVIEW
            if needs != in_review:
                check.fail(f"{cid}: {'cần duyệt nhưng nằm ở ' + name if needs else 'đã kiểm chứng nhưng nằm trong hàng chờ duyệt'}")
            if in_review != (meta["ground_truth"]["status"] == "NEEDS_MEDICAL_REVIEW"):
                check.fail(f"{cid}: trạng thái ground_truth trong metadata không khớp tệp chứa bản ghi")
    check.summary = "Kết luận: " + ", ".join(f"{k} {v}" for k, v in sorted(verdicts.items())) + "."
    return check


# --------------------------------------------------------------------------- trùng lặp, rò rỉ, độ phủ


def check_duplicates(data: dict[str, list[dict[str, Any]]]) -> tuple[Check, list[tuple[float, str, str, str, str]]]:
    check = Check("7. Trùng lặp và gần trùng")
    rows = [(name, r) for name, items in data.items() for r in items]
    openings = Counter(normalise(r["presentation"]["initial_message"]) for _, r in rows)
    for text, n in openings.items():
        if n > 1:
            check.fail(f"Lời mở đầu trùng hệt nhau ({n} lần): {text[:80]!r}")
    profile_sig = Counter(
        (signature(r), r["profile"]["age_band"], r["profile"]["sex"], r["profile"]["relationship_type"]) for _, r in rows
    )
    for key, n in profile_sig.items():
        if n > 1:
            check.fail(f"Cùng bộ dữ kiện và cùng nhóm hồ sơ ({n} bản ghi): {key[0][:100]}")
    sh = [(name, r, shingles(r["presentation"]["initial_message"])) for name, r in rows]
    pairs = []
    for (na, a, sa), (nb, b, sb) in combinations(sh, 2):
        score = jaccard(sa, sb)
        if score >= NEAR_DUPLICATE_JACCARD:
            pairs.append((round(score, 3), a["case_id"], na, b["case_id"], nb))
    existing = []
    for path in REFERENCE_DATASETS:
        existing.extend(shingles(r["presentation"]["initial_message"]) for r in load_jsonl(path))
    worst = 0.0
    for _, r, s in sh:
        best = max(jaccard(s, other) for other in existing)
        worst = max(worst, best)
        if best >= COPY_OF_EXISTING_JACCARD:
            check.fail(f"{r['case_id']}: lời mở đầu gần như chép từ bộ ca hiện có (Jaccard {best:.2f})")
    same_sig = sum(n for n in Counter(signature(r) for _, r in rows).values() if n > 1)
    exact = sum(n for n in openings.values() if n > 1)
    check.summary = (
        f"{exact} lời mở đầu trùng hệt; {len(pairs)} cặp có độ giống ký tự (4-gram Jaccard) >= {NEAR_DUPLICATE_JACCARD}; "
        f"{same_sig} bản ghi chia chung một bộ dữ kiện với bản ghi khác (khác hồ sơ); "
        f"độ giống cao nhất với bộ 30/300 ca hiện có: {worst:.2f}."
    )
    return check, pairs


def check_split(data: dict[str, list[dict[str, Any]]], metadata: dict[str, dict[str, Any]],
                pairs: list[tuple[float, str, str, str, str]]) -> Check:
    check = Check("8. Chia tập 70/15/15, không rò rỉ, test có ca khó")
    family_split: dict[str, set[str]] = defaultdict(set)
    cluster_split: dict[str, set[str]] = defaultdict(set)
    for name in SPLITS:
        for r in data[name]:
            meta = metadata[r["case_id"]]
            family_split[meta["family"]].add(name)
            cluster_split[meta["split_cluster"]].add(name)
            if meta["split"] != name:
                check.fail(f"{r['case_id']}: metadata ghi split {meta['split']} nhưng bản ghi nằm trong {name}")
    for family, names in family_split.items():
        if len(names) > 1:
            check.fail(f"Gia đình kịch bản {family} nằm ở nhiều tập: {sorted(names)}")
    for cluster, names in cluster_split.items():
        if len(names) > 1:
            check.fail(f"Cụm chia tập {cluster} nằm ở nhiều tập: {sorted(names)}")
    for score, a, na, b, nb in pairs:
        if na in SPLITS and nb in SPLITS and na != nb:
            check.fail(f"Cặp gần trùng {a} ({na}) / {b} ({nb}) nằm ở hai tập khác nhau (Jaccard {score})")
    sig_split: dict[str, set[str]] = defaultdict(set)
    for name in SPLITS:
        for r in data[name]:
            sig_split[signature(r)].add(name)
    for sig, names in sig_split.items():
        if len(names) > 1:
            check.fail(f"Cùng bộ dữ kiện xuất hiện ở {sorted(names)}: {sig[:100]}")
    counts = {name: len(data[name]) for name in SPLITS}
    total = sum(counts.values())
    shares = {name: counts[name] / total for name in SPLITS}
    for name, target in (("train", 0.70), ("validation", 0.15), ("test", 0.15)):
        if abs(shares[name] - target) > 0.03:
            check.fail(f"Tỉ lệ {name} = {shares[name]:.1%}, lệch quá 3 điểm so với {target:.0%}")
    test_groups = Counter(metadata[r["case_id"]]["group"] for r in data["test"])
    for group in ("MISSING_INFO", "CONFLICTING", "COMPLEX_DIALOGUE"):
        if not test_groups.get(group):
            check.fail(f"Tập test không có ca nhóm {group}")
    if not any(r["category"] == "incomplete" for r in data["test"]):
        check.fail("Tập test không có ca kỳ vọng RETURN_INCOMPLETE")
    hard = sum(1 for r in data["test"] if metadata[r["case_id"]]["edge_tags"])
    check.summary = (
        f"train {counts['train']} ({shares['train']:.1%}), validation {counts['validation']} ({shares['validation']:.1%}), "
        f"test {counts['test']} ({shares['test']:.1%}); {hard}/{counts['test']} ca test có ít nhất một nhãn tình huống biên; "
        f"không gia đình, cụm, bộ dữ kiện hay cặp gần trùng nào vắt qua hai tập."
    )
    return check


def check_lock(metadata: dict[str, dict[str, Any]]) -> Check:
    """Đợt 1 đã khoá: từng bản ghi còn nguyên byte, cùng tệp, cùng cờ smoke."""
    check = Check("9. Các đợt đã khoá giữ nguyên so với split_lock.json")
    if not LOCK_FILE.exists():
        check.fail("Không có split_lock.json")
        return check
    document = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    lock = document["records"]
    revisions = document.get("revisions", [])
    for revision in revisions:
        split_changes = revision.get("split_changes", revision.get("split_or_smoke_changes"))
        if split_changes != 0 or not revision.get("reason") or not revision.get("allowed_fields"):
            check.fail(f"Lần sửa khoá thiếu lý do/trường cho phép hoặc có đổi tập: {revision.get('reason', '')[:80]}")
        if revision.get("smoke_changes", 0) and "smoke" not in revision["allowed_fields"]:
            check.fail(f"Lần sửa khoá đổi cờ smoke mà không cho phép trường smoke: {revision.get('reason', '')[:80]}")
        for change in revision.get("changes", []):
            outside = {f for f in change["fields"]
                       if not any(f == a or f.startswith(a + ".") for a in revision["allowed_fields"])}
            if outside:
                check.fail(f"{change['scenario_key']}: lần sửa khoá đổi trường ngoài danh sách cho phép: {sorted(outside)}")
    seen: dict[str, tuple[str, str, bool]] = {}
    for name in FILES:
        for line in (HERE / f"{name}.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                seen[record["case_id"]] = (name, hashlib.sha256(line.encode("utf-8")).hexdigest(), record["smoke"])
    locked_batches = [item["batch"] for item in document.get("locked_batches", [])] or [document.get("batch", 1)]
    expected_locked = sum(RECORDS_PER_BATCH[b] for b in locked_batches)
    if len(lock) != expected_locked:
        check.fail(f"split_lock.json có {len(lock)} bản ghi, các đợt đã khoá {locked_batches} phải có {expected_locked}")
    for item in document.get("locked_batches", []):
        if item["records"] != RECORDS_PER_BATCH[item["batch"]]:
            check.fail(f"Đợt {item['batch']} ghi {item['records']} bản ghi khoá, yêu cầu {RECORDS_PER_BATCH[item['batch']]}")
    for case_id, locked in lock.items():
        if case_id not in seen:
            check.fail(f"{locked['scenario_key']} ({case_id}) đã khoá nhưng không còn trong bộ ca")
            continue
        name, digest, smoke = seen[case_id]
        if name != locked["split"]:
            check.fail(f"{locked['scenario_key']} ({case_id}) chuyển từ {locked['split']} sang {name}")
        if digest != locked["record_sha256"]:
            check.fail(f"{locked['scenario_key']} ({case_id}) đã thay đổi so với lúc khoá")
        if smoke != locked["smoke"]:
            check.fail(f"{locked['scenario_key']} ({case_id}) đổi cờ smoke")
    batches = Counter(meta.get("batch") for meta in metadata.values())
    for batch, expected in RECORDS_PER_BATCH.items():
        if batches.get(batch, 0) != expected:
            check.fail(f"Đợt {batch} có {batches.get(batch, 0)} bản ghi trong metadata, yêu cầu {expected}")
    wrong_batch = [cid for cid, meta in metadata.items() if (cid in lock) != (meta.get("batch") in locked_batches)]
    if wrong_batch:
        check.fail(f"Metadata ghi sai đợt cho {len(wrong_batch)} bản ghi, ví dụ {wrong_batch[:3]}")
    new_by_file = Counter(seen[cid][0] for cid in seen if cid not in lock)
    check.summary = (
        f"{len(lock)} bản ghi đã khoá (đợt {', '.join(map(str, locked_batches))}) khớp từng byte với khoá, đúng tệp và cờ smoke"
        + (f" ({len(revisions)} lần sửa có chủ đích, tổng {sum(r['records_changed'] for r in revisions)} bản ghi, "
           f"chỉ ở trường {sorted({f for r in revisions for f in r['allowed_fields']})})" if revisions else "")
        + ("; chưa khoá: " + ", ".join(f"{name} {new_by_file.get(name, 0)}" for name in FILES) + "."
           if new_by_file else "; không còn bản ghi chưa khoá.")
    )
    return check


def coverage(data: dict[str, list[dict[str, Any]]], metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = [(name, r, metadata[r["case_id"]]) for name, items in data.items() for r in items]
    facts_used = Counter(k for _, r, _ in rows for k in r["expected_state"]["facts"])
    unknown_used = Counter(k for _, r, _ in rows for k in r["expected_state"]["unknown_fact_ids"])
    tags = Counter(t for _, _, m in rows for t in m["edge_tags"])
    by_split_label = {name: dict(Counter(r["category"] for r in data[name])) for name in FILES}
    primaries_by_batch: dict[Any, set[str]] = defaultdict(set)
    for _, r, m in rows:
        if r["expected_retrieval"]["primary_atom_id"]:
            primaries_by_batch[m.get("batch")].add(r["expected_retrieval"]["primary_atom_id"])
    by_batch = {
        str(batch): {
            "records": sum(1 for _, _, m in rows if m.get("batch") == batch),
            "verified": sum(1 for name, _, m in rows if m.get("batch") == batch and name in SPLITS),
            "labels": dict(sorted(Counter(r["category"] for _, r, m in rows if m.get("batch") == batch).items())),
            "distinct_primary_atoms": len(primaries_by_batch[batch]),
        }
        for batch in sorted({m.get("batch") for _, _, m in rows}, key=str)
    }
    if 1 in primaries_by_batch and 2 in primaries_by_batch:
        by_batch["2"]["primary_atoms_not_in_batch_1"] = len(primaries_by_batch[2] - primaries_by_batch[1])
    return {
        "records": len(rows),
        "by_batch": by_batch,
        "groups": dict(Counter(m["group"] for _, _, m in rows)),
        "labels": dict(Counter(r["category"] for _, r, _ in rows)),
        "labels_by_file": by_split_label,
        "verified_labels": dict(Counter(r["category"] for name, r, _ in rows if name in SPLITS)),
        "age_band": dict(Counter(r["profile"]["age_band"] for _, r, _ in rows)),
        "older_adults_65_plus": sum(1 for _, _, m in rows if m["older_adult"]),
        "sex": dict(Counter(r["profile"]["sex"] for _, r, _ in rows)),
        "relationship": dict(Counter(r["profile"]["relationship_type"] for _, r, _ in rows)),
        "narrator": dict(Counter(m["narrator"] for _, _, m in rows)),
        "with_chronic_conditions": sum(1 for _, r, _ in rows if r["profile"]["chronic_conditions"]),
        "with_daily_medications": sum(1 for _, r, _ in rows if r["profile"]["daily_medications"]),
        "with_allergies": sum(1 for _, r, _ in rows if r["profile"]["allergies"]),
        "terminal_action": dict(Counter(r["expected_decision"]["terminal_action"] for _, r, _ in rows)),
        "with_unknown_facts": sum(1 for _, r, _ in rows if r["expected_state"]["unknown_fact_ids"]),
        "with_resource_count": sum(1 for _, r, _ in rows if r["expected_state"]["resource_count"] is not None),
        "with_temporal_context": sum(1 for _, r, _ in rows if r["presentation"]["contains_temporal_context"]),
        "distinct_fact_targets_valued": len(facts_used),
        "distinct_fact_targets_unknown": len(unknown_used),
        "distinct_primary_atoms": len({r["expected_retrieval"]["primary_atom_id"] for _, r, _ in rows if r["expected_retrieval"]["primary_atom_id"]}),
        "decision_points": dict(Counter(dp for _, r, _ in rows for dp in r["expected_retrieval"]["decision_points"])),
        "distinct_concepts": len({c for _, r, _ in rows for c in r["expected_state"]["concept_ids"]}),
        "edge_tags": dict(tags.most_common()),
        "opening_length_chars": {
            "min": min(len(r["presentation"]["initial_message"]) for _, r, _ in rows),
            "median": sorted(len(r["presentation"]["initial_message"]) for _, r, _ in rows)[len(rows) // 2],
            "max": max(len(r["presentation"]["initial_message"]) for _, r, _ in rows),
        },
    }


def screen_findings(metadata: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for cid, meta in sorted(metadata.items()):
        screen = meta["emergency_screen"]
        if not screen["matches_expectation"]:
            out.append({"case_id": cid, "scenario_key": meta["scenario_key"], "title": meta["title"],
                        "expected": screen["expected_on_opening"], "observed": screen["observed_on_opening"],
                        "rule": screen["opening_rule_id"], "trigger": screen["opening_trigger"]})
    return out


# --------------------------------------------------------------------------- báo cáo


def _table(rows: list[list[Any]], header: list[str]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c).replace("|", "/") for c in row) + " |" for row in rows]
    return "\n".join(lines)


def write_report(checks: list[Check], cov: dict[str, Any], pairs: list, findings: list, review_rows: list, offline: bool) -> str:
    status = "FAIL" if any(c.status == "FAIL" for c in checks) else "PASS"
    out = [
        "# Báo cáo kiểm tra bộ ca generated_mock_v2",
        "",
        f"Sinh tự động bởi `validate_dataset.py`{' (chế độ offline, bỏ qua kiểm tra cần PostgreSQL)' if offline else ''}. "
        "Mọi con số dưới đây được tính lại từ các tệp JSONL và từ corpus, không chép từ metadata của bước dựng.",
        "",
        f"**Kết quả chung: {status}**",
        "",
        _table([[c.name, c.status, c.summary] for c in checks], ["Kiểm tra", "Kết quả", "Tóm tắt"]),
        "",
    ]
    for c in checks:
        if c.details:
            out += [f"### Lỗi: {c.name}", "", *[f"- {d}" for d in c.details[:50]], ""]
    out += [
        "## Độ phủ",
        "",
        _table([[k, json.dumps(v, ensure_ascii=False)] for k, v in cov.items()], ["Chỉ số", "Giá trị"]),
        "",
        "## Cặp lời mở đầu gần giống nhau (4-gram Jaccard >= 0.5)",
        "",
        "Các cặp này không phải bản sao: chúng khác dữ kiện (thường là cặp tối thiểu có chủ đích) nhưng câu chữ gần nhau, "
        "nên luôn được xếp cùng một tập để không rò rỉ.",
        "",
        _table([list(p) for p in sorted(pairs, reverse=True)], ["Jaccard", "Ca A", "Tệp A", "Ca B", "Tệp B"]) if pairs else "Không có.",
        "",
        "## Phát hiện về bộ lọc khẩn cấp của sản phẩm",
        "",
        "`src/simple_agent/emergency_screen.screen_patient_message` được chạy thật trên lời mở đầu của từng ca. "
        "Đây là phát hiện về sản phẩm, không ảnh hưởng nhãn: bộ lọc không gán ESI.",
        "",
        _table([[f["scenario_key"], f["case_id"], f["title"], f["expected"], f["observed"], f["rule"] or "", f["trigger"] or ""] for f in findings],
               ["Kịch bản", "case_id", "Tình huống", "Kỳ vọng", "Thực tế", "Luật", "Cụm khớp"]) if findings else "Không có.",
        "",
        "## Hàng chờ chuyên gia y tế (needs_medical_review.jsonl)",
        "",
        _table(review_rows, ["case_id", "Kịch bản", "Nhãn hiện tại", "Lý do chính"]),
        "",
    ]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="Bỏ qua các kiểm tra cần PostgreSQL.")
    args = parser.parse_args()
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    data, metadata = load_all()
    schema = reference_schema()
    checks = [check_structure(data, schema), check_dialogue_consistency(data)]
    if args.offline:
        for name in ("3. Dữ kiện hợp lệ theo schema của corpus PostgreSQL",
                     "4. Nhãn tính lại độc lập bằng golden_validator.satisfied_esi",
                     "5. Vân tay corpus và checksum manifest"):
            checks.append(Check(name, "SKIPPED", summary="Cần PostgreSQL; chạy lại trong container."))
    else:
        checks += corpus_checks(data, metadata)
    checks.append(independent_review(data, metadata))
    dup_check, pairs = check_duplicates(data)
    checks.append(dup_check)
    checks.append(check_split(data, metadata, pairs))
    checks.append(check_lock(metadata))
    cov = coverage(data, metadata)
    findings = screen_findings(metadata)
    review_rows = []
    for r in data[REVIEW]:
        meta = metadata[r["case_id"]]
        reason = meta["ground_truth"]["reasons"][0] if meta["ground_truth"]["reasons"] else ""
        review_rows.append([r["case_id"], meta["scenario_key"], r["category"], reason[:160]])
    review_rows.sort(key=lambda row: row[1])
    report = write_report(checks, cov, pairs, findings, review_rows, args.offline)
    if args.offline:
        # Không ghi đè báo cáo đầy đủ bằng bản thiếu ba kiểm tra cần PostgreSQL.
        print("(chế độ offline: không ghi validation_report.md)")
    else:
        (HERE / "validation_report.md").write_bytes(report.encode("utf-8"))
    for c in checks:
        print(f"[{c.status}] {c.name}: {c.summary}")
        for d in c.details[:10]:
            print("    -", d)
    return 1 if any(c.status == "FAIL" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
