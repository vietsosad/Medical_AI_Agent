"""Red-flag timestamps must be storable, and must record when it was raised.

Both defects here were found from a live session, not from a test, and both had
the same shape: the code worked against SQLite in the suite and failed against
PostgreSQL in the product.

The first was fatal. ``red_flag_resolved_at`` was written as a timezone-aware
datetime into a ``TIMESTAMP WITHOUT TIME ZONE`` column; asyncpg rejects that
outright, so the whole transaction failed *mid-turn* and the patient saw
"network error" at the precise moment the system had decided their case was an
emergency. SQLite accepts either kind, which is why the suite stayed green.

The second was quieter: the raised-at stamp was only written on a turn whose
status was CANDIDATE, so a candidate raised and confirmed within a single turn
-- the most urgent case there is -- ended up in the ledger with a resolution
time and no beginning.

These tests assert the property that actually matters (naive UTC), rather than
the dialect that happened to expose it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models.db_models import TriageCase, User, get_utc_now
from src.services.clinical_state_persistence import persist_red_flag_lifecycle

from src.services.db import POSTGRES_ONLY_TABLES as POSTGRES_ONLY

# Every timestamp column in this schema is naive UTC; asyncpg enforces it.
TIMESTAMP_FIELDS = ("red_flag_raised_at", "red_flag_resolved_at")


@pytest_asyncio.fixture
async def db_session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'rf.db'}")
    tables = [
        table
        for table in SQLModel.metadata.sorted_tables
        if table.name not in POSTGRES_ONLY
    ]
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables)
        )
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


async def _case(session: AsyncSession) -> TriageCase:
    user = User(email="p@example.invalid", hashed_password="x", role="PATIENT")
    session.add(user)
    await session.flush()
    case = TriageCase(
        patient_id=user.id,
        session_title="ca thử",
        status="IN_PROGRESS",
    )
    session.add(case)
    await session.flush()
    return case


def _state(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "red_flag_status": status,
        "is_red_flag": status == "CONFIRMED",
        "red_flag_candidate_reason": "đau ngực dữ dội",
        "red_flag_candidate_esi": 2,
        "emergency_detection_source": "SEMANTIC_LLM",
        **extra,
    }


# --------------------------------------------------------------------------
# The storable-timestamp property
# --------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status", ["CANDIDATE", "CONFIRMED", "NOT_CONFIRMED", "SAFETY_FALLBACK", "UNCERTAIN"],
)
async def test_written_timestamps_are_naive_utc(
    db_session: AsyncSession, status: str
) -> None:
    """An aware datetime here is rejected by PostgreSQL and fails the turn."""
    case = await _case(db_session)

    persist_red_flag_lifecycle(db_session, case, _state(status))

    for field in TIMESTAMP_FIELDS:
        value = getattr(case, field)
        if value is None:
            continue
        assert isinstance(value, datetime)
        assert value.tzinfo is None, (
            f"{field} is timezone-aware; asyncpg will refuse it"
        )


@pytest.mark.asyncio
async def test_the_lifecycle_commits_to_a_real_database(
    db_session: AsyncSession,
) -> None:
    """The failure was at COMMIT, so the test has to reach a commit."""
    case = await _case(db_session)

    persist_red_flag_lifecycle(db_session, case, _state("CONFIRMED"))
    await db_session.commit()

    await db_session.refresh(case)
    assert case.red_flag_status == "CONFIRMED"
    assert case.is_red_flag_triggered is True


def test_the_shared_clock_is_naive() -> None:
    """The convention every column depends on, asserted once."""
    assert get_utc_now().tzinfo is None


# --------------------------------------------------------------------------
# A raised emergency always has a beginning
# --------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status", ["CANDIDATE", "CONFIRMED", "NOT_CONFIRMED", "SAFETY_FALLBACK", "UNCERTAIN"],
)
async def test_any_active_status_records_when_it_was_raised(
    db_session: AsyncSession, status: str
) -> None:
    case = await _case(db_session)

    persist_red_flag_lifecycle(db_session, case, _state(status))

    assert case.red_flag_raised_at is not None, (
        f"{status} left no raised-at time"
    )


@pytest.mark.asyncio
async def test_a_candidate_confirmed_in_one_turn_has_both_times(
    db_session: AsyncSession,
) -> None:
    """The urgent case: raised and confirmed without an intervening turn."""
    case = await _case(db_session)

    persist_red_flag_lifecycle(db_session, case, _state("CONFIRMED"))

    assert case.red_flag_raised_at is not None
    assert case.red_flag_resolved_at is not None
    assert case.red_flag_raised_at <= case.red_flag_resolved_at


@pytest.mark.asyncio
async def test_no_candidate_records_no_timestamps(
    db_session: AsyncSession,
) -> None:
    """A quiet turn must not stamp an emergency that never happened."""
    case = await _case(db_session)

    persist_red_flag_lifecycle(db_session, case, _state("NO_CANDIDATE"))

    assert case.red_flag_raised_at is None
    assert case.red_flag_resolved_at is None


@pytest.mark.asyncio
async def test_the_raised_time_is_not_overwritten_on_later_turns(
    db_session: AsyncSession,
) -> None:
    """When it began is a fact about the case, not about the latest turn."""
    case = await _case(db_session)

    persist_red_flag_lifecycle(db_session, case, _state("CANDIDATE"))
    first_raised = case.red_flag_raised_at
    assert first_raised is not None

    persist_red_flag_lifecycle(db_session, case, _state("CONFIRMED"))

    assert case.red_flag_raised_at == first_raised
    assert case.red_flag_resolved_at is not None
