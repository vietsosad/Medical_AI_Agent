from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete
from sqlmodel import Session, select

from src.models.db_models import (
    EHRProfile, SimpleAgentChatMessage, SimpleAgentChatSession,
    SimpleAgentNurseReview, SimpleAgentSessionRecord, User,
)
from src.services.db import sync_engine
from src.services.security import create_access_token


DEFAULT_EVAL_EMAIL = "simple-agent-eval@local.test"


@dataclass(frozen=True)
class EvalIdentity:
    user_id: str
    access_token: str


def ensure_eval_identity(email: str = DEFAULT_EVAL_EMAIL) -> EvalIdentity:
    with Session(sync_engine, expire_on_commit=False) as db:
        user = db.exec(select(User).where(User.email == email)).first()
        if user is None:
            user = User(email=email, full_name="Simple Agent Evaluation", role="PATIENT", oauth_provider="none", is_guest=False, is_active=True)
            db.add(user)
            db.commit()
            db.refresh(user)
        return EvalIdentity(user_id=user.id, access_token=create_access_token(subject=user.id, additional_claims={"role": user.role, "email": user.email}))


def create_eval_profile(identity: EvalIdentity, profile: dict[str, object], *, case_id: str) -> str:
    with Session(sync_engine, expire_on_commit=False) as db:
        row = EHRProfile(
            user_id=identity.user_id, full_name=f"Eval {case_id}", relationship_type=str(profile.get("relationship_type") or "SELF"),
            is_primary=False, age=int(profile["age_years"]) if profile.get("age_years") is not None else None,
            gender=str(profile.get("sex") or "Other"), chronic_conditions=list(profile.get("chronic_conditions") or []),
            allergies=list(profile.get("allergies") or []), daily_medications=list(profile.get("daily_medications") or []),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id


def cleanup_run(*, identity: EvalIdentity, session_ids: list[str], profile_ids: list[str]) -> int:
    ids = [item for item in session_ids if item]
    profiles = [item for item in profile_ids if item]
    if not ids and not profiles:
        return 0
    with Session(sync_engine, expire_on_commit=False) as db:
        owned = [row.session_id for row in db.exec(select(SimpleAgentChatSession).where(SimpleAgentChatSession.session_id.in_(ids), SimpleAgentChatSession.patient_id == identity.user_id)).all()]
        if owned:
            db.exec(delete(SimpleAgentNurseReview).where(SimpleAgentNurseReview.session_id.in_(owned)))
            db.exec(delete(SimpleAgentChatMessage).where(SimpleAgentChatMessage.session_id.in_(owned)))
            db.exec(delete(SimpleAgentSessionRecord).where(SimpleAgentSessionRecord.session_id.in_(owned)))
            db.exec(delete(SimpleAgentChatSession).where(SimpleAgentChatSession.session_id.in_(owned)))
        if profiles:
            db.exec(delete(EHRProfile).where(EHRProfile.id.in_(profiles), EHRProfile.user_id == identity.user_id))
        db.commit()
        return len(owned)

