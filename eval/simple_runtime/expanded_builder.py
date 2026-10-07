"""Bộ sinh ca vàng quy mô lớn, mở rộng từ ``golden_builder``.

Vì sao là một module riêng thay vì sửa ``golden_builder.py``: bộ 30 ca
(``simple_agent_golden_30.jsonl``) là một deliverable đã công bố — số liệu của
nó nằm trong tài liệu dự án và hình dạng của nó bị khoá bởi
``eval/tests/test_dataset_shape.py``. Mọi thứ ở đây chỉ **thêm vào**; không có
hàm nào trong ``golden_builder`` bị đổi hành vi, và bộ 30 ca vẫn sinh ra y
nguyên như trước.

Toàn bộ logic nặng được **dùng lại**, không sao chép: điều kiện đủ tư cách
(``_eligible``), phép chống nhãn vòng tròn (``_isolated_for_level``) và việc
dựng một ca từ hạt giống (``_case_from_seed``) đều gọi thẳng sang
``golden_builder``. File này chỉ trả lời đúng một câu hỏi mà bộ cũ không trả
lời được: **chọn hạt giống nào khi cần hàng trăm ca thay vì ba mươi.**

Nguyên tắc chọn, theo thứ tự:

1. **Phủ rộng trước, đào sâu sau.** Ưu tiên mỗi tổ hợp trường dữ kiện
   (*chữ ký*) một ca trước đã. Hết chữ ký mới quay lại lấy thêm những tiêu chí
   dùng chung chữ ký nhưng khác ngưỡng hoặc khác điểm quyết định. Nhờ vậy 100
   ca đầu tiên chạm được nhiều vùng lâm sàng khác nhau nhất có thể, thay vì
   xoáy vào một nhóm bệnh cảnh.
2. **Tất định tuyệt đối.** Sắp xếp theo ``atom_id``, không dùng số ngẫu nhiên.
   Chạy lại cùng một corpus phải ra đúng cùng một bộ ca, nếu không thì
   checksum trong manifest vô nghĩa.
3. **Không bịa dữ liệu.** Mọi ca vẫn suy ra từ tiêu chí phác đồ có thật trong
   PostgreSQL, mang theo ``postgres_provenance`` và fingerprint của từng dòng
   nguồn, y như bộ 30 ca.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .corpus_reader import CorpusSnapshot
from .golden_builder import _case_from_seed, _eligible, _isolated_for_level
from .golden_validator import branch_conditions
from .schemas import GoldenCase, Seed

#: Phân bố mặc định cho bộ 300 ca, chọn theo mức rủi ro lâm sàng chứ không chia
#: đều: ESI 1 lấy **toàn bộ** những tiêu chí người bệnh chạm tới được (kho chỉ
#: có chừng đó), ESI 2 lấy nhiều nhất vì đó là vùng bỏ sót nguy hiểm nhất và
#: cũng là vùng rộng nhất trong kho.
DEFAULT_TARGETS: dict[int, int] = {1: 20, 2: 150, 3: 50, 4: 35, 5: 35}

#: Ba kiểu tấn công có thật trong ``_case_from_seed`` cộng với một ca dò lộ
#: system prompt. Mỗi kiểu tấn công được gắn vào một tiêu chí nguồn khác nhau
#: để mười ca guardrail không trùng nội dung nhau.
_ADVERSARIAL_KINDS = ("force_low_esi", "ignore_protocol", "diagnosis_or_prescription")


def _eligible_atoms_by_level(corpus: CorpusSnapshot) -> dict[int, list[dict[str, Any]]]:
    """Các tiêu chí người bệnh tự khai được, nhóm theo mức ESI, đã sắp xếp cố định."""
    by_level: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for atom in corpus.atoms.values():
        if not _eligible(atom, corpus):
            continue
        level = int(atom["decision_effect"]["candidate_esi"])
        # Loại tiêu chí mà chính dữ kiện sinh cho nó lại thoả một mức khẩn hơn:
        # giữ nhãn của bộ đánh giá độc lập với bộ so khớp của sản phẩm.
        if not _isolated_for_level(atom, corpus):
            continue
        by_level[level].append(atom)
    for level in by_level:
        by_level[level].sort(key=lambda atom: atom["atom_id"])
    return by_level


def _signature(atom: dict[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(item["fact_target_id"] for item in branch_conditions(atom)))


def available_by_level(corpus: CorpusSnapshot) -> dict[int, int]:
    """Số ca tối đa có thể sinh cho từng mức, để gọi bên ngoài kiểm tra trước."""
    return {level: len(atoms) for level, atoms in _eligible_atoms_by_level(corpus).items()}


def _choose_atoms(atoms: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    """Chọn ``count`` tiêu chí, ưu tiên phủ hết chữ ký trước khi lấy trùng chữ ký.

    Vòng một lấy mỗi chữ ký đúng một đại diện. Nếu vẫn thiếu, vòng hai lấy tiếp
    những tiêu chí còn lại theo đúng thứ tự ``atom_id`` — chúng dùng chung tổ
    hợp trường nhưng khác ngưỡng hoặc khác điểm quyết định, nên vẫn là một phép
    thử khác chứ không phải bản sao.
    """
    chosen: list[dict[str, Any]] = []
    leftovers: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()

    for atom in atoms:
        signature = _signature(atom)
        if signature in seen:
            leftovers.append(atom)
            continue
        seen.add(signature)
        chosen.append(atom)
        if len(chosen) == count:
            return chosen

    for atom in leftovers:
        chosen.append(atom)
        if len(chosen) == count:
            break
    return chosen


def select_expanded_seeds(
    corpus: CorpusSnapshot,
    targets: dict[int, int] | None = None,
    *,
    guardrail_count: int = 10,
) -> list[Seed]:
    """Hạt giống cho một bộ ca quy mô lớn.

    Nếu một mức không đủ tiêu chí để đạt chỉ tiêu, hàm **không** ném lỗi mà lấy
    hết những gì có và đi tiếp -- trần của mức ESI 1 là một sự thật của kho dữ
    liệu, không phải một lỗi cấu hình (xem ``docs/OPEN_ISSUE_ESI1_REACHABILITY.md``).
    Bên gọi đọc lại số thực tế qua ``available_by_level``.
    """
    requested = dict(targets or DEFAULT_TARGETS)
    by_level = _eligible_atoms_by_level(corpus)

    seeds: list[Seed] = []
    chosen_by_level: dict[int, list[str]] = {}
    for level in sorted(requested):
        count = int(requested[level])
        if count <= 0:
            continue
        atoms = _choose_atoms(by_level.get(level, []), count)
        chosen_by_level[level] = [atom["atom_id"] for atom in atoms]
        for index, atom in enumerate(atoms, start=1):
            seeds.append(
                Seed(
                    case_id=f"exp-esi{level}-{index:03d}",
                    selected_atom_id=atom["atom_id"],
                    category=f"esi_{level}",
                    # Hai ca khói: một ca tối khẩn và một ca nhẹ. Nếu một trong
                    # hai hỏng thì gần như chắc chắn cả lượt chạy vô nghĩa, nên
                    # chúng chạy trước và chặn phần còn lại.
                    smoke=(level == 1 and index == 1) or (level == 4 and index == 1),
                )
            )

    seeds.extend(_guardrail_seeds(chosen_by_level, guardrail_count))
    return seeds


def _guardrail_seeds(chosen_by_level: dict[int, list[str]], guardrail_count: int) -> list[Seed]:
    """Ca tấn công, mỗi ca gắn vào một tiêu chí nguồn khác nhau.

    Ca dò lộ system prompt luôn là ca cuối cùng và không cần tiêu chí nguồn nào
    (xem nhánh ``prompt_probe`` trong ``_case_from_seed``).
    """
    if guardrail_count <= 0:
        return []

    # Lấy tiêu chí nguồn từ các mức khẩn trước: một câu lệnh "hãy xếp tôi ESI 5"
    # chỉ nguy hiểm khi nó được gắn vào một ca thực sự nặng.
    pool: list[str] = []
    for level in (1, 2, 3, 4, 5):
        pool.extend(chosen_by_level.get(level, []))
    if not pool:
        return []

    seeds: list[Seed] = []
    attack_slots = max(0, guardrail_count - 1)
    for index in range(attack_slots):
        seeds.append(
            Seed(
                case_id=f"exp-guardrail-{index + 1:03d}",
                selected_atom_id=pool[index % len(pool)],
                category="guardrail",
                adversarial_kind=_ADVERSARIAL_KINDS[index % len(_ADVERSARIAL_KINDS)],
            )
        )
    seeds.append(
        Seed(
            case_id=f"exp-guardrail-{guardrail_count:03d}",
            category="guardrail",
            adversarial_kind="prompt_probe",
        )
    )
    return seeds


def build_expanded_cases(
    corpus: CorpusSnapshot,
    seeds: list[Seed] | None = None,
) -> tuple[list[GoldenCase], list[Seed]]:
    """Dựng ca từ hạt giống, bỏ qua hạt giống nào không dựng được.

    ``_case_from_seed`` ném lỗi khi một tiêu chí, sau khi sinh dữ kiện, lại thoả
    một mức ESI khác với mức đã chọn. ``_isolated_for_level`` đã chặn phần lớn
    trường hợp đó từ khâu chọn, nhưng ở quy mô hàng trăm ca vẫn nên chịu lỗi
    một cách tường minh: bỏ đúng hạt giống hỏng và báo lại, thay vì để một tiêu
    chí lẻ làm hỏng cả bộ.
    """
    effective_seeds = seeds if seeds is not None else select_expanded_seeds(corpus)
    cases: list[GoldenCase] = []
    kept_seeds: list[Seed] = []
    rejected: list[tuple[str, str]] = []

    for seed in effective_seeds:
        try:
            cases.append(_case_from_seed(seed, corpus))
        except RuntimeError as exc:
            rejected.append((seed.case_id, str(exc)))
            continue
        kept_seeds.append(seed)

    if not cases:
        raise RuntimeError("Không dựng được ca nào từ corpus PostgreSQL.")
    if sum(case.smoke for case in cases) < 1:
        raise RuntimeError("Bộ ca phải có ít nhất một ca khói.")

    build_expanded_cases.last_rejected = rejected  # type: ignore[attr-defined]
    return cases, kept_seeds
