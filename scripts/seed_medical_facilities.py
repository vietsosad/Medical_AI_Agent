"""Nạp danh bạ cơ sở y tế vào cơ sở dữ liệu.

    python scripts/seed_medical_facilities.py           # nạp seed
    python scripts/seed_medical_facilities.py --check   # chỉ kiểm định file seed, không ghi CSDL

Lệnh này là điều kiện để tính năng "tìm cơ sở y tế gần nhất" có dữ liệu dự phòng
khi hệ thống chạy mà không có khoá Google Maps Platform. Không chạy lệnh này thì
tính năng vẫn hoạt động, nhưng danh sách dự phòng sẽ rỗng.

Khác với ``seed_health_topics.py``, ở đây KHÔNG có bước gọi LLM: danh bạ cơ sở y
tế là dữ liệu hành chính, không có phần nào để diễn giải lại.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel.ext.asyncio.session import AsyncSession  # noqa: E402

from src.services.db import async_engine, init_db_schema  # noqa: E402
from src.services.facility_directory import (  # noqa: E402
    count_published_facilities,
    load_seed_facilities,
    sync_seed_into_database,
)

_DRAFT_WARNING = (
    "[Seed] LƯU Ý: danh bạ này là BẢN NHÁP do nhóm dự án biên soạn, chưa đối chiếu\n"
    "       nguồn công bố chính thức. Trước khi dùng cho người bệnh thật, phải rà\n"
    "       soát tên, địa chỉ, toạ độ và khả năng tiếp nhận cấp cứu của từng cơ sở."
)


async def run(check_only: bool) -> int:
    seeds = load_seed_facilities()

    missing_phone = sum(1 for seed in seeds if not seed.phone_number)
    unknown_emergency = sum(1 for seed in seeds if seed.emergency_capability == "UNKNOWN")
    print(f"[Seed] File seed hợp lệ: {len(seeds)} cơ sở.")
    print(f"[Seed] Chưa có số điện thoại: {missing_phone} | chưa xác minh khoa cấp cứu: {unknown_emergency}")
    print(_DRAFT_WARNING)

    if check_only:
        print("[Seed] Chế độ --check: không ghi gì vào cơ sở dữ liệu.")
        return 0

    await init_db_schema()
    async with AsyncSession(async_engine) as session:
        created, updated = await sync_seed_into_database(session)
        total = await count_published_facilities(session)

    print(f"[Seed] Cơ sở tạo mới: {created} | cập nhật: {updated} | đang hiển thị: {total}")
    return 0


def main() -> int:
    # Console Windows mặc định không phải UTF-8 (cp1258 ở khu vực Việt Nam), nên
    # mọi dòng tiếng Việt có dấu sẽ làm script chết vì UnicodeEncodeError trước
    # khi kịp nạp được gì. Ép stdout về UTF-8 thay vì bỏ dấu khỏi thông báo.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Nạp danh bạ cơ sở y tế từ data/facilities/vi.json")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Chỉ kiểm định file seed rồi thoát, không chạm vào cơ sở dữ liệu.",
    )
    args = parser.parse_args()
    return asyncio.run(run(check_only=args.check))


if __name__ == "__main__":
    raise SystemExit(main())
