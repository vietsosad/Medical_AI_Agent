"""Dịch vụ Quản Trị Kết Nối Cơ Sở Dữ Liệu Bất Đồng Bộ (Async DB Service).

Tuân thủ tuyệt đối quy tắc tại .agents/rules/backend-rules.md:
- An toàn Non-Blocking Loop: Sử dụng AsyncSession từ SQLModel & SQLAlchemy.
- Quản lý tài nguyên Lifespan Factory.
"""

from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlmodel import Session, SQLModel

from src.config import get_settings
from src.models.db_models import (  # noqa: F401
    AuditLog,
    ChatMessage,
    ClinicalObservation,
    EHRProfile,
    NurseReviewState,
    OtpCode,
    RefreshTokenSession,
    SimpleAgentChatMessage,
    SimpleAgentChatSession,
    SimpleAgentClinicalConcept,
    SimpleAgentConceptRelation,
    SimpleAgentFactTarget,
    SimpleAgentFactTargetEmbedding,
    SimpleAgentNurseReview,
    SimpleAgentProtocolAtom,
    SimpleAgentSessionRecord,
    TriageCase,
    User,
)

settings = get_settings()

# -----------------------------------------------------------------------------
# 1. Khởi tạo Engine Bất Đồng Bộ (Async Engine - Phục vụ FastAPI Endpoints & Asyncer)
# -----------------------------------------------------------------------------
# Đảm bảo URL kết nối sử dụng asyncpg hoặc sqlite async (aiosqlite / fallback)
async_db_url = settings.database_url
if async_db_url.startswith("postgresql://"):
    async_db_url = async_db_url.replace("postgresql://", "postgresql+asyncpg://")
elif async_db_url.startswith("sqlite:///"):
    # Sử dụng engine async cho sqlite khi test local nếu có hoặc chạy chuẩn
    if "aiosqlite" not in async_db_url:
        async_db_url = async_db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

# Khởi tạo Async Engine cho production router concurrency
async_engine: AsyncEngine = create_async_engine(
    async_db_url,
    echo=(settings.log_level == "DEBUG"),
    future=True,
    pool_pre_ping=True if "postgresql" in async_db_url else False,
)

# -----------------------------------------------------------------------------
# 2. Khởi tạo Sync Engine (Phục vụ CLI Seeding Scripts & Alembic Migrations)
# -----------------------------------------------------------------------------
sync_db_url = settings.sync_database_url
if not sync_db_url:
    sync_db_url = settings.database_url.replace("+asyncpg", "").replace("+aiosqlite", "")

sync_engine = create_engine(
    sync_db_url,
    echo=(settings.log_level == "DEBUG"),
    future=True,
    pool_pre_ping=True if "postgresql" in sync_db_url else False,
)


# Tables that only exist on PostgreSQL: they use pgvector or ARRAY columns that
# SQLite cannot compile. Exported so schema setup and tests share one list —
# it previously lived in three separate copies that drifted apart.
POSTGRES_ONLY_TABLES = frozenset(
    {
        "esi_knowledge_documents",
        "mietic_cases",
        "simple_agent_clinical_concepts",
        "simple_agent_protocol_atoms",
        "simple_agent_fact_target_embeddings",
    }
)


# -----------------------------------------------------------------------------
# 3. Hàm Khởi Tạo & Tiêu Hủy Schema (Gọi từ Lifespan trong src/main.py)
# -----------------------------------------------------------------------------
async def init_db_schema() -> None:
    """Khởi tạo toàn bộ các bảng SQLModel trong cơ sở dữ liệu nếu chưa tồn tại.

    Được thực hiện an toàn qua async connection trong tiến trình Lifespan Startup.
    """
    async with async_engine.begin() as conn:
        if "postgresql" in async_db_url:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            application_tables = [
                table
                for table in SQLModel.metadata.sorted_tables
            ]
            await conn.run_sync(
                lambda sync_conn: SQLModel.metadata.create_all(
                    sync_conn,
                    tables=application_tables,
                )
            )
            # create_all does not add columns to an existing deployment.
            for statement in _ADDITIVE_COLUMNS_PG:
                await conn.execute(text(statement))
        else:
            sqlite_tables = [
                table
                for table in SQLModel.metadata.sorted_tables
                if table.name not in POSTGRES_ONLY_TABLES
            ]
            await conn.run_sync(lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=sqlite_tables))
            for table_name, additive_columns in _ADDITIVE_COLUMNS_BY_TABLE:
                columns = await conn.execute(text(f"PRAGMA table_info({table_name})"))
                existing = {str(row[1]) for row in columns.fetchall()}
                for column, ddl_type in additive_columns:
                    if column not in existing:
                        await conn.execute(text(
                            f"ALTER TABLE {table_name} ADD COLUMN {column} {ddl_type}"
                        ))
    print("[Database Service] Database schema is ready.")


# Additive-only columns. Existing deployments predate these, and every one is
# nullable so an old row still deserializes: a NULL lifecycle means "written
# before the lifecycle existed", never "no red flag" and never a clinical value.
_ADDITIVE_TRIAGE_CASE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("rag_citation_details", "JSON"),
    ("red_flag_status", "VARCHAR"),
    ("red_flag_candidate_esi", "INTEGER"),
    ("red_flag_detection_source", "VARCHAR"),
    ("red_flag_resolution_reason", "VARCHAR"),
    ("red_flag_raised_at", "TIMESTAMP"),
    ("red_flag_resolved_at", "TIMESTAMP"),
    ("canonical_state", "JSON"),
    ("canonical_state_version", "INTEGER"),
    ("conversation_memory", "JSON"),
    ("conversation_control", "JSON"),
)
# ``ehr_profiles.phone_number`` is the member's own contact number. Existing rows
# predate it and stay NULL, which reads as "chưa cập nhật" - never as a real number.
_ADDITIVE_EHR_PROFILE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("phone_number", "VARCHAR"),
)

# Hội thoại giữa bệnh nhân và nhân viên lâm sàng là hồ sơ giao tiếp y tế, nên
# mỗi dòng phải nói được ai viết và bên kia đã đọc chưa. Dòng cũ để NULL, đọc là
# "không rõ tác giả cụ thể" chứ không phải "hệ thống viết".
_ADDITIVE_CHAT_MESSAGE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("sender_id", "VARCHAR"),
    ("sender_display_name", "VARCHAR"),
    ("read_at", "TIMESTAMP"),
    ("client_message_id", "VARCHAR"),
    ("channel", "VARCHAR"),
)

# simple_agent_chat_messages already has real pilot rows before care-team chat
# existed -- same reasoning as _ADDITIVE_CHAT_MESSAGE_COLUMNS above, just for
# the simple_agent pilot's own message table (see SimpleAgentChatMessage).
_ADDITIVE_SIMPLE_AGENT_CHAT_MESSAGE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("channel", "VARCHAR"),
    ("read_at", "TIMESTAMP"),
    ("client_message_id", "VARCHAR"),
)

# simple_agent_sessions already has real pilot rows before the proactive-ask
# confidence gate existed (see decision.py's
# MIN_ATOM_RELEVANCE_SCORE_FOR_PROACTIVE_ASK). A NULL/missing value here reads
# as "no confidence data yet for this atom", identical to how agent.py already
# treats a never-recorded atom_id -- never a clinical judgment either way.
_ADDITIVE_SIMPLE_AGENT_SESSION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("atom_relevance_score", "JSON"),
    ("retrieval_query", "VARCHAR"),
    ("card_gender", "VARCHAR"),
    ("card_relationship", "VARCHAR"),
)

# simple_agent_fact_targets already has real corpus rows from the initial
# scripts/migrate_simple_agent_corpus_to_pg.py run, predating the gated_by
# askable-ordering mechanism (see db_models.py's SimpleAgentFactTarget).
_ADDITIVE_SIMPLE_AGENT_FACT_TARGET_COLUMNS: tuple[tuple[str, str], ...] = (
    ("gated_by", "JSON"),
    ("requires_sex", "VARCHAR"),
)

# simple_agent_chat_sessions already has real pilot rows predating profile_id
# (see db_models.py's SimpleAgentChatSession).
_ADDITIVE_SIMPLE_AGENT_CHAT_SESSION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("profile_id", "VARCHAR"),
)

# simple_agent_nurse_reviews already has real pilot rows predating the
# "tạm gác lại" (PARKED) bucket (see db_models.py's SimpleAgentNurseReview).
_ADDITIVE_SIMPLE_AGENT_NURSE_REVIEW_COLUMNS: tuple[tuple[str, str], ...] = (
    ("parked_at", "TIMESTAMP"),
    ("parked_by_nurse_id", "VARCHAR"),
    ("parked_reason", "VARCHAR"),
)

_ADDITIVE_COLUMNS_BY_TABLE: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("triage_cases", _ADDITIVE_TRIAGE_CASE_COLUMNS),
    ("ehr_profiles", _ADDITIVE_EHR_PROFILE_COLUMNS),
    ("simple_agent_chat_messages", _ADDITIVE_SIMPLE_AGENT_CHAT_MESSAGE_COLUMNS),
    ("simple_agent_sessions", _ADDITIVE_SIMPLE_AGENT_SESSION_COLUMNS),
    ("simple_agent_fact_targets", _ADDITIVE_SIMPLE_AGENT_FACT_TARGET_COLUMNS),
    ("simple_agent_chat_sessions", _ADDITIVE_SIMPLE_AGENT_CHAT_SESSION_COLUMNS),
    ("simple_agent_nurse_reviews", _ADDITIVE_SIMPLE_AGENT_NURSE_REVIEW_COLUMNS),
    ("chat_messages", _ADDITIVE_CHAT_MESSAGE_COLUMNS),
)

_ADDITIVE_COLUMNS_PG: tuple[str, ...] = tuple(
    f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column} {ddl_type}"
    for table_name, additive_columns in _ADDITIVE_COLUMNS_BY_TABLE
    for column, ddl_type in additive_columns
)


async def dispose_db_engine() -> None:
    """Đóng sạch các kết nối trong connection pool khi shutdown Server."""
    await async_engine.dispose()
    print("💤 [Database Service] Đã đóng Connection Pool an toàn.")


# -----------------------------------------------------------------------------
# 4. Dependency Injection Generators (`Depends(get_async_session)`)
# -----------------------------------------------------------------------------
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Cung cấp AsyncSession non-blocking cho các FastAPI APIRouter."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_sync_session() -> Generator[Session, None, None]:
    """Cung cấp Sync Session cho các script Seeding ngoại vi."""
    with Session(sync_engine, expire_on_commit=False) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
