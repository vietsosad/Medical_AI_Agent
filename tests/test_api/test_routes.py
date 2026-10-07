import pytest

from src.api.routes_patient import _requires_nurse_review


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_empty_message(client):
    response = await client.post("/api/v1/chat", json={"message": ""})
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_agent_status(client):
    response = await client.get("/api/v1/status")
    assert response.status_code == 200


def test_unconfirmed_fail_closed_handoff_still_creates_nurse_review() -> None:
    assert _requires_nurse_review(
        {
            "decision_status": "INSUFFICIENT_EVIDENCE",
            "patient_confirmed_intake": False,
            "current_esi_level": None,
        }
    ) is True


def test_retrieval_outage_does_not_claim_an_automatic_nurse_review() -> None:
    assert _requires_nurse_review(
        {
            "decision_status": "RETRIEVAL_FAILURE",
            "patient_confirmed_intake": True,
            "current_esi_level": None,
        }
    ) is False
