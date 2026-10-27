"""HTTP contract of the pre-LLM emergency screen, patient side to nurse queue.

The agent runtime is replaced by a fake: what is under test is the route's
own behaviour -- the screen runs before any model, its flag survives a turn
that fails, and a flagged case reaches the nurse queue while still ACTIVE.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

import src.api.routes_nurse_simple as routes_nurse_simple
import src.api.routes_simple_triage as routes_simple_triage
from src.api.dependencies import get_current_nurse, get_current_patient
from src.main import app
from src.models.db_models import SimpleAgentChatSession, User
from src.services.db import POSTGRES_ONLY_TABLES, get_async_session
from src.simple_agent.session import Session
from src.simple_agent.sql_bundle_corpus import load_corpus_from_sql_bundle

PATIENT = User(id="patient-1", email="patient@test.local", full_name="Người bệnh", role="PATIENT")
NURSE = User(id="nurse-1", email="nurse@test.local", full_name="Điều dưỡng", role="CLINICAL_NURSE")


def _turn(action: str = "ASK_NEXT", levels: list[int] | None = None) -> dict[str, Any]:
    return {
        "message": "Bạn bị như vậy từ khi nào?",
        "decision": {"route": "TRIAGE", "action": action, "matched_esi_levels": levels or [], "concepts": []},
    }


class FakeRuntime:
    def __init__(self) -> None:
        # The nurse case view builds an SBAR from it -- for a still-ACTIVE case too.
        self.corpus = load_corpus_from_sql_bundle()
        self.next_result: dict[str, Any] = _turn()
        self.fail = False
        self.calls = 0

    async def process_turn(self, session_id: str, message: str, restore: Session | None = None) -> dict[str, Any]:
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        return self.next_result

    def export_session(self, session_id: str) -> Session:
        return Session()

    def has_hot_session(self, session_id: str) -> bool:
        return True


@pytest_asyncio.fixture
async def db_session(tmp_path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'emergency_flow.db'}")
    tables = [table for table in SQLModel.metadata.sorted_tables if table.name not in POSTGRES_ONLY_TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(User(id=PATIENT.id, email=PATIENT.email, full_name=PATIENT.full_name, role="PATIENT"))
        await session.commit()
        yield session
    await engine.dispose()


@pytest.fixture
def runtime(monkeypatch: pytest.MonkeyPatch) -> FakeRuntime:
    fake = FakeRuntime()
    enabled = SimpleNamespace(simple_agent_enabled=True)
    monkeypatch.setattr(routes_simple_triage, "get_simple_agent_runtime", lambda: fake)
    monkeypatch.setattr(routes_nurse_simple, "get_simple_agent_runtime", lambda: fake)
    monkeypatch.setattr(routes_simple_triage, "get_settings", lambda: enabled)
    monkeypatch.setattr(routes_nurse_simple, "get_settings", lambda: enabled)
    return fake


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _session_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def _patient() -> User:
        return PATIENT

    async def _nurse() -> User:
        return NURSE

    app.dependency_overrides[get_async_session] = _session_override
    app.dependency_overrides[get_current_patient] = _patient
    app.dependency_overrides[get_current_nurse] = _nurse
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


async def _queue(client: AsyncClient) -> list[dict[str, Any]]:
    response = await client.get("/api/v1/nurse-simple/queue")
    assert response.status_code == 200
    return response.json()["items"]


@pytest.mark.asyncio
async def test_an_emergency_phrase_puts_115_first_and_the_case_at_the_top_of_the_queue(client, runtime) -> None:
    benign = await client.post("/api/v1/simple-triage/start", json={"message": "tôi bị đau họng"})
    flagged = await client.post("/api/v1/simple-triage/start", json={"message": "con tôi ngất xỉu"})

    assert benign.status_code == flagged.status_code == 200
    assert "115" not in benign.json()["message"]
    body = flagged.json()
    assert body["message"].startswith("Lưu ý an toàn")
    assert "115" in body["message"]
    assert body["decision"]["safety_alert"]["rule_id"] == "SA_SCREEN_SYNCOPE_V1"

    items = await _queue(client)
    # Only the flagged case is in the queue: it is still ACTIVE, the benign one is not reviewable yet.
    assert [item["session_id"] for item in items] == [body["session_id"]]
    assert items[0]["attention_required"] is True
    assert items[0]["session_status"] == "ACTIVE"
    assert items[0]["ai_proposed_esi"] is None


@pytest.mark.asyncio
async def test_the_flag_survives_a_turn_the_model_fails(client, runtime, db_session) -> None:
    started = await client.post("/api/v1/simple-triage/start", json={"message": "tôi bị đau bụng"})
    session_id = started.json()["session_id"]
    runtime.fail = True

    failed = await client.post(f"/api/v1/simple-triage/chat/{session_id}", json={"message": "mẹ tôi vừa nôn ra máu"})

    assert failed.status_code == 502
    assert "115" in failed.json()["detail"]
    chat = (await db_session.exec(select(SimpleAgentChatSession).where(SimpleAgentChatSession.session_id == session_id))).first()
    assert chat is not None and chat.attention_required
    assert chat.attention_rule_id == "SA_SCREEN_BLEEDING_GI_V1"
    assert [item["session_id"] for item in await _queue(client)] == [session_id]
    detail = await client.get(f"/api/v1/nurse-simple/cases/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["attention_required"] is True


@pytest.mark.asyncio
async def test_a_decisive_esi_1_outcome_is_not_given_a_second_115_preamble(client, runtime) -> None:
    runtime.next_result = {
        "message": "Hãy gọi cấp cứu 115 ngay.",
        "decision": {"route": "TRIAGE", "action": "RETURN_MATCH", "matched_esi_levels": [1, 3], "concepts": []},
    }

    response = await client.post("/api/v1/simple-triage/start", json={"message": "môi con tôi tím tái"})

    assert response.json()["message"] == "Hãy gọi cấp cứu 115 ngay."
    assert response.json()["decision"]["safety_alert"]["rule_id"] == "SA_SCREEN_CYANOSIS_V1"


@pytest.mark.asyncio
async def test_a_denied_symptom_raises_nothing(client, runtime) -> None:
    response = await client.post("/api/v1/simple-triage/start", json={"message": "tôi không bị ngất, chỉ đau đầu"})

    assert "safety_alert" not in response.json()["decision"]
    assert await _queue(client) == []
