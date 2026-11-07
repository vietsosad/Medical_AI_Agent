"""Kiểm tra nhanh một hoặc vài tệp kịch bản trước khi gộp vào bộ ca (không ghi tệp nào).

Dùng khi viết kịch bản mới: chạy đủ các bước của ``build_dataset`` cho từng kịch bản
(kiểm tra schema, tính nhãn, dựng bản ghi, đối chiếu AHRQ, bộ lọc khẩn cấp) rồi so
lời mở đầu và bộ dữ kiện với mọi kịch bản khác và với bộ 30/300 ca hiện có.

    MSYS_NO_PATHCONV=1 docker exec -i -e PYTHONIOENCODING=utf-8 -w /app triage_backend \
        python -m eval.generated_mock_v2.check_specs eval/generated_mock_v2/scenarios/b2_common.py

Thêm ``--verbose`` để in câu trả lời người bệnh sẽ nói cho từng dữ kiện có giá trị hoặc
"không biết", cùng câu làm rõ và câu xác nhận, để đọc lại xem có khớp với câu chuyện.

Mọi tệp kịch bản (mọi đợt) được nạp theo đường dẫn, không qua
``scenarios/__init__.py``, nên một tệp đang viết dở của người khác chỉ bị bỏ qua khi so
trùng chứ không làm hỏng lần kiểm tra này.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from eval.simple_runtime.corpus_reader import load_postgres_corpus

from . import ahrq_review
from .build_dataset import (
    NEAR_DUPLICATE_JACCARD,
    BuildError,
    build_record,
    compute_label,
    fact_signature,
    ground_truth,
    jaccard,
    opaque_case_id,
    screen_check,
    shingles,
    validate_spec,
)
from .spec import Spec

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BATCH1_MODULES = ("common", "multi", "red_flag", "missing", "conflict", "complex")
SCENARIO_PACKAGE = "eval.generated_mock_v2.scenarios"
REFERENCE_DATASETS = (REPO / "eval/cases/simple_agent_golden_30.jsonl", REPO / "eval/cases/simple_agent_golden_300.jsonl")


def load_file(path: Path) -> list[Spec]:
    # Tên module nằm trong gói scenarios để ``from ..spec import`` (đợt 1) vẫn chạy, nhưng
    # không đi qua ``scenarios/__init__.py``.
    module_spec = importlib.util.spec_from_file_location(f"{SCENARIO_PACKAGE}._check_{path.stem}", path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return list(module.SPECS)


def scenario_files() -> list[Path]:
    return sorted(p for p in (HERE / "scenarios").glob("*.py") if p.name != "__init__.py")


def main(argv: list[str]) -> int:
    verbose = "--verbose" in argv
    targets = [Path(arg).resolve() for arg in argv if not arg.startswith("--")]
    if not targets:
        print("usage: python -m eval.generated_mock_v2.check_specs <scenario file> [...]", file=sys.stderr)
        return 2
    corpus = load_postgres_corpus()
    ref = ahrq_review.load_reference()

    others: list[tuple[str, Spec]] = []
    for path in scenario_files():
        if path.resolve() in targets:
            continue
        where = "batch1" if path.stem in BATCH1_MODULES else path.stem
        try:
            others.extend((where, s) for s in load_file(path))
        except Exception as exc:  # noqa: BLE001 - tệp của người khác có thể đang viết dở
            print(f"(bỏ qua {path.name} khi so trùng: {type(exc).__name__}: {exc})")
    # Tiêu chí đại diện -> các kịch bản đã dựng (mọi đợt trong metadata) dùng nó làm đại diện.
    primary_users: dict[str, set[str]] = {}
    meta_path = HERE / "metadata.jsonl"
    if meta_path.exists():
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            if item["label"]["primary_atom_id"]:
                primary_users.setdefault(item["label"]["primary_atom_id"], set()).add(item["scenario_key"])

    def reused_elsewhere(primary: str | None, key: str) -> bool:
        return bool(primary and primary_users.get(primary, set()) - {key})
    reference_shingles = [
        shingles(json.loads(line)["presentation"]["initial_message"])
        for path in REFERENCE_DATASETS for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    other_keys = Counter(s.case_id for _, s in others)
    other_families = {s.family for _, s in others}
    other_sh = [(where, s, shingles(s.opening)) for where, s in others]

    failures = 0
    rows: list[dict[str, Any]] = []
    loaded: list[tuple[Path, list[Spec]]] = []
    for path in targets:
        try:
            loaded.append((path, load_file(path)))
        except Exception as exc:  # noqa: BLE001
            print(f"{path.name}: KHÔNG NẠP ĐƯỢC: {type(exc).__name__}: {exc}")
            return 1
    # Nhiều tệp được kiểm cùng lúc thì so cả với nhau, không chỉ trong từng tệp.
    pooled = [(path.stem, spec) for path, specs in loaded for spec in specs]
    keys = Counter(spec.case_id for _, spec in pooled)
    for path, specs in loaded:
        for spec in specs:
            problems: list[str] = []
            if keys[spec.case_id] > 1 or other_keys[spec.case_id]:
                problems.append("mã kịch bản trùng")
            if spec.family in other_families or any(
                where != path.stem and other.family == spec.family for where, other in pooled
            ):
                problems.append(f"family '{spec.family}' đã có ở tệp khác")
            try:
                validate_spec(spec, corpus)
                label = compute_label(spec, corpus)
                record = build_record(spec, label, corpus)
            except BuildError as exc:
                failures += 1
                print(f"[LỖI] {spec.case_id}: {exc}")
                continue
            ahrq = ahrq_review.review(
                ref, label=label["level"], patient_facts=label["patient_facts"], resources=spec.resources,
                resource_basis=spec.resource_basis, age_years=spec.profile["age_years"],
                age_months=spec.profile["age_months"], matched_atoms=label["matched"],
            )
            truth = ground_truth(spec, ahrq)
            screen = screen_check(spec, record)
            if not screen["matches_expectation"]:
                problems.append(f"bộ lọc khẩn cấp: kỳ vọng {screen['expected_on_opening']}, thực tế {screen['observed_on_opening']} ({screen['opening_rule_id']})")
            mine = shingles(spec.opening)
            best, best_with = 0.0, ""
            for where, other, sh in other_sh:
                score = jaccard(mine, sh)
                if score > best:
                    best, best_with = score, f"{other.case_id}@{where}"
            for where, other in pooled:
                if other.case_id != spec.case_id:
                    score = jaccard(mine, shingles(other.opening))
                    if score > best:
                        best, best_with = score, f"{other.case_id}@{where}"
            ref_best = max(jaccard(mine, sh) for sh in reference_shingles)
            if best >= NEAR_DUPLICATE_JACCARD:
                problems.append(f"lời mở đầu gần trùng {best_with} (Jaccard {best:.2f})")
            if ref_best >= 0.5:
                problems.append(f"lời mở đầu gần với bộ 30/300 ca (Jaccard {ref_best:.2f})")
            sig = fact_signature(record.expected_state["facts"])
            same_sig = [f"{o.case_id}@{w}" for w, o in others if fact_signature(
                {("fact_target:" + k): v for k, v in {**o.facts, **({"resource_count": o.resources} if o.resources is not None else {})}.items()}
            ) == sig]
            same_sig += [f"{o.case_id}@{w}" for w, o in pooled if o.case_id != spec.case_id and fact_signature(
                {("fact_target:" + k): v for k, v in {**o.facts, **({"resource_count": o.resources} if o.resources is not None else {})}.items()}
            ) == sig]
            if same_sig:
                problems.append(f"cùng bộ dữ kiện với {', '.join(same_sig)}")
            primary = label["primary"]["atom_id"] if label["primary"] else None
            rows.append({
                "key": spec.case_id,
                "case_id": opaque_case_id(spec.case_id),
                "esi": label["level"],
                "primary": primary,
                "primary_reused": reused_elsewhere(primary, spec.case_id),
                "matched": len(label["matched"]),
                "truth": truth["status"],
                "ahrq": ahrq["verdict"],
                "screen": screen["observed_on_opening"],
                "max_jaccard": round(best, 2),
            })
            flag = "[CẢNH BÁO]" if problems else "[OK]"
            if problems:
                failures += 1
            level = "INCOMPLETE" if label["level"] is None else f"ESI {label['level']}"
            reused = " (tiêu chí đã có ca khác dùng)" if rows[-1]["primary_reused"] else ""
            print(f"{flag} {spec.case_id} {level} | {primary or '-'}{reused} | {truth['status']} ({ahrq['verdict']}) | "
                  f"lọc: {screen['observed_on_opening']} | Jaccard max {best:.2f} ({best_with})")
            for reason in truth["reasons"]:
                print(f"      lý do duyệt: {reason[:220]}")
            for problem in problems:
                print(f"      !! {problem}")
            if verbose:
                answers = record.adaptive_dialogue["answers_by_fact_target"]
                for fact in [*spec.facts, *spec.unknown]:
                    marker = "?" if fact in spec.unknown else "="
                    value = "" if fact in spec.unknown else f"{spec.facts[fact]!r} "
                    print(f"      {marker} {fact} {value}-> {answers['fact_target:' + fact]}")
                print(f"      làm rõ: {record.adaptive_dialogue['clarification_reply'][:200]}")
                print(f"      xác nhận: {record.adaptive_dialogue['confirmation_reply']}")
                if label["matched"]:
                    print("      tiêu chí khớp: " + ", ".join(sorted(m["atom_id"].removeprefix("atom:") for m in label["matched"]))[:400])
    if rows:
        print()
        print("Tổng:", len(rows), "kịch bản dựng được;",
              dict(Counter("INCOMPLETE" if r["esi"] is None else f"ESI {r['esi']}" for r in rows)),
              dict(Counter(r["truth"] for r in rows)))
        primaries = [r["primary"] for r in rows if r["primary"]]
        print("Tiêu chí đại diện khác nhau:", len(set(primaries)), "; trong đó chưa ca đã dựng nào dùng:",
              len({r["primary"] for r in rows if r["primary"] and not r["primary_reused"]}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
