"""Nạp nội dung "Thông tin sức khỏe đáng chú ý" vào cơ sở dữ liệu.

    python scripts/seed_health_topics.py              # nạp seed, sinh diễn giải cho chủ đề còn thiếu
    python scripts/seed_health_topics.py --no-llm     # chỉ nạp seed, bỏ qua bước gọi LLM
    python scripts/seed_health_topics.py --regenerate # bắt buộc sinh lại toàn bộ diễn giải

Trang chủ chỉ đọc dữ liệu đã xử lý sẵn trong CSDL, nên LLM được gọi ở đây - lúc
seed - chứ không phải mỗi lần có người tải trang.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import select  # noqa: E402
from sqlmodel.ext.asyncio.session import AsyncSession  # noqa: E402

from src.models.db_models import HealthTopic  # noqa: E402
from src.services.db import async_engine, init_db_schema  # noqa: E402
from src.services.health_topic_summary import generate_ai_summary  # noqa: E402
from src.services.health_topics import sync_seed_into_database, touch_updated  # noqa: E402


async def run(use_llm: bool, regenerate: bool) -> int:
    await init_db_schema()

    async with AsyncSession(async_engine) as session:
        created, updated = await sync_seed_into_database(session)
        print(f"[Seed] Chủ đề tạo mới: {created} | cập nhật: {updated}")

        if not use_llm:
            print("[Seed] Bỏ qua bước diễn giải bằng LLM (--no-llm).")
            return 0

        topics = list(
            (await session.execute(select(HealthTopic).order_by(HealthTopic.display_order)))
            .scalars()
            .all()
        )

        generated = 0
        skipped = 0
        refused = 0

        for topic in topics:
            if topic.ai_summary and not regenerate:
                skipped += 1
                continue

            result = await generate_ai_summary(topic)
            if result is None:
                # Nội dung seed vẫn hiển thị được, chỉ là không có bản diễn giải.
                refused += 1
                continue

            summary, model_name = result
            topic.ai_summary = summary
            topic.ai_summary_model = model_name
            touch_updated(topic)
            session.add(topic)
            generated += 1
            print(f"[Seed] Đã diễn giải '{topic.slug}' bằng {model_name}")

        await session.commit()
        print(
            f"[Seed] Diễn giải: {generated} mới | {skipped} dùng lại bản cache | "
            f"{refused} giữ nguyên bản seed"
        )

    await async_engine.dispose()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Nạp chủ đề sức khỏe vào cơ sở dữ liệu.")
    parser.add_argument("--no-llm", action="store_true", help="Chỉ nạp seed, không gọi LLM.")
    parser.add_argument(
        "--regenerate", action="store_true", help="Sinh lại diễn giải kể cả khi đã có bản cache."
    )
    args = parser.parse_args()
    return asyncio.run(run(use_llm=not args.no_llm, regenerate=args.regenerate))


if __name__ == "__main__":
    raise SystemExit(main())
