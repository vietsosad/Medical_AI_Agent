"""Dựng bộ ca vàng mở rộng từ 5 bảng corpus PostgreSQL.

    python -m eval.build_golden_expanded                 # 300 ca, phân bố mặc định
    python -m eval.build_golden_expanded --count 500     # chia lại theo tỉ lệ mặc định
    python -m eval.build_golden_expanded --coverage      # chỉ in trần khả dụng, không ghi gì
    python -m eval.build_golden_expanded --validate-only # kiểm tra checksum bộ đã có

Khác với ``eval/build_golden_from_postgres.py`` (bộ 30 ca, cố định, là
deliverable đã công bố), lệnh này ghi ra một bộ **riêng** và không đụng tới bất
kỳ file nào của bộ 30 ca, cũng không xoá ảnh chụp kết quả trong ``eval/results``.

Không có bước nào ở đây gọi mô hình ngôn ngữ. Mọi ca đều suy ra tất định từ
tiêu chí phác đồ có thật trong PostgreSQL, nên chạy lại trên cùng một corpus sẽ
cho ra đúng cùng một bộ ca và cùng một checksum.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from eval.simple_runtime.corpus_reader import load_postgres_corpus
from eval.simple_runtime.expanded_builder import (
    DEFAULT_TARGETS,
    available_by_level,
    build_expanded_cases,
    select_expanded_seeds,
)
from eval.simple_runtime.golden_builder import write_dataset
from eval.simple_runtime.schemas import Seed

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "eval" / "cases"

DEFAULT_OUTPUT = CASES / "simple_agent_golden_300.jsonl"
DEFAULT_SEEDS = CASES / "simple_agent_expanded_seed_manifest.json"


def _scaled_targets(count: int) -> dict[int, int]:
    """Chia ``count`` theo đúng tỉ lệ của phân bố mặc định."""
    total = sum(DEFAULT_TARGETS.values())
    scaled = {level: max(1, round(share * count / total)) for level, share in DEFAULT_TARGETS.items()}
    # Bù phần lệch do làm tròn vào ESI 2 -- mức rộng nhất, nên cộng trừ vài ca
    # ở đó không làm méo phân bố.
    scaled[2] += count - sum(scaled.values())
    return scaled


def _report_coverage(corpus) -> None:
    available = available_by_level(corpus)
    print("Trần khả dụng cho ca bệnh nhân tự khai (đã lọc tiêu chí chỉ nhân viên y tế điền được):")
    print(f"  {'ESI':<6}{'tối đa':<10}{'mặc định lấy':<14}")
    for level in sorted(set(available) | set(DEFAULT_TARGETS)):
        print(f"  {level:<6}{available.get(level, 0):<10}{DEFAULT_TARGETS.get(level, 0):<14}")
    print(f"  {'tổng':<6}{sum(available.values()):<10}{sum(DEFAULT_TARGETS.values()):<14}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        # Console Windows mặc định không phải UTF-8 ở khu vực Việt Nam.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Dựng bộ ca vàng mở rộng từ PostgreSQL.")
    parser.add_argument("--count", type=int, default=sum(DEFAULT_TARGETS.values()) + 10)
    parser.add_argument("--guardrail-count", type=int, default=10)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed-manifest", type=Path, default=DEFAULT_SEEDS)
    parser.add_argument("--coverage", action="store_true", help="Chỉ in trần khả dụng rồi thoát.")
    parser.add_argument("--validate-only", action="store_true", help="Đối chiếu checksum bộ đã ghi.")
    args = parser.parse_args()

    corpus = load_postgres_corpus()
    if args.coverage:
        _report_coverage(corpus)
        return 0

    output: Path = args.output
    manifest_path = output.with_suffix(".manifest.json")

    if args.validate_only:
        if not output.exists() or not manifest_path.exists():
            raise SystemExit("Chưa có bộ ca hoặc manifest; chạy lệnh này không kèm --validate-only trước.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if hashlib.sha256(output.read_bytes()).hexdigest() != manifest["dataset_sha256"]:
            raise SystemExit("Checksum bộ ca không khớp manifest của nó; dựng lại bộ ca.")
        if manifest.get("table_fingerprints") != corpus.table_fingerprints:
            print("Checksum khớp, nhưng corpus PostgreSQL đã đổi so với lúc dựng bộ ca.")
        else:
            print("Bộ ca và corpus 5 bảng đều khớp.")
        return 0

    clinical_count = max(0, args.count - args.guardrail_count)
    targets = _scaled_targets(clinical_count)

    # Dùng lại hạt giống đã duyệt nếu có, để lần dựng sau không âm thầm chọn
    # một tập tiêu chí khác -- cùng quy ước với bộ 30 ca.
    seeds: list[Seed] | None = None
    if args.seed_manifest.exists():
        seeds = [Seed.model_validate(item) for item in json.loads(args.seed_manifest.read_text(encoding="utf-8"))]
        print(f"Dùng lại {len(seeds)} hạt giống đã có trong {args.seed_manifest.name}.")
    else:
        seeds = select_expanded_seeds(corpus, targets, guardrail_count=args.guardrail_count)

    cases, kept_seeds = build_expanded_cases(corpus, seeds)
    rejected = getattr(build_expanded_cases, "last_rejected", [])

    write_dataset(
        cases,
        kept_seeds,
        corpus,
        output=output,
        seed_path=args.seed_manifest,
        manifest_path=manifest_path,
    )

    counts: dict[str, int] = {}
    for case in cases:
        counts[case.category] = counts.get(case.category, 0) + 1
    print(f"Đã ghi {len(cases)} ca vào {output}")
    print("Phân bố:", json.dumps(counts, ensure_ascii=False, sort_keys=True))
    print("Số ca khói:", sum(case.smoke for case in cases))
    distinct_atoms = len({case.postgres_provenance.get("protocol_atom_id") for case in cases} - {None})
    print("Số tiêu chí phác đồ khác nhau được dùng:", distinct_atoms)
    if rejected:
        print(f"Bỏ qua {len(rejected)} hạt giống không dựng được:")
        for case_id, reason in rejected[:10]:
            print(f"   {case_id}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
