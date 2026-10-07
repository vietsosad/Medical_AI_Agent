"""Kênh thời gian thực và hội thoại trực tiếp giữa bệnh nhân và nhân viên lâm sàng.

Chạy trên SQLite dựng từ chính các model đang dùng, nên một sai sót về schema
hoặc về phạm vi quyền sẽ hỏng ở đây thay vì hỏng ngoài môi trường thật.
"""

from __future__ import annotations

import asyncio
from typing import cast

import pytest
import pytest_asyncio
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.routes_nurse import (
    access_case_pii,
    get_case_emergency_contacts,
    list_case_messages,
    mark_case_messages_read,
    send_case_message,
)
from src.api.routes_patient import (
    _care_team_view,
    _owned_case_or_404,
    mark_staff_messages_read,
    send_message_to_staff,
)
from src.api.routes_ws import _serve
from src.models.db_models import (
    ChatMessage,
    EHRProfile,
    NurseReviewState,
    TriageCase,
    User,
)
from src.models.nurse_schemas import PiiAccessRequestDTO, SendCaseMessageRequestDTO
from src.models.patient_schemas import SendStaffMessageRequestDTO
from src.services.db import POSTGRES_ONLY_TABLES as POSTGRES_ONLY
from src.services.event_bus import (
    EVENT_MESSAGE_CREATED,
    STAFF_QUEUE_TOPIC,
    InMemoryEventBus,
    case_topic,
)


@pytest_asyncio.fixture
async def db_session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'realtime.db'}")
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


async def _seed(
    session: AsyncSession,
    *,
    profile: EHRProfile | None = None,
    claimed: bool = True,
) -> tuple[TriageCase, User, User]:
    """Một ca đang rà soát, kèm bệnh nhân và điều dưỡng phụ trách."""
    patient = User(
        id="patient-1",
        email="patient@test.vn",
        full_name="Nguyễn Văn A",
        phone="0912345678",
        role="PATIENT",
    )
    nurse = User(
        id="nurse-1",
        email="nurse@test.vn",
        full_name="Điều dưỡng Trần B",
        role="CLINICAL_NURSE",
    )
    session.add_all([patient, nurse])
    if profile is not None:
        session.add(profile)
    case = TriageCase(
        id="case-1",
        patient_id=patient.id,
        profile_id=profile.id if profile else None,
        status="HITL_REVIEWING",
        assigned_nurse_id=nurse.id if claimed else None,
    )
    session.add(case)
    session.add(
        NurseReviewState(
            triage_case_id=case.id,
            review_status="IN_REVIEW" if claimed else "WAITING_REVIEW",
            assigned_nurse_id=nurse.id if claimed else None,
        )
    )
    await session.commit()
    return case, patient, nurse


# ---------------------------------------------------------------------------
# Bus sự kiện
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_an_event_reaches_only_the_topic_it_was_published_to():
    bus = InMemoryEventBus()
    async with bus.subscribe([case_topic("case-1")]) as mine:
        async with bus.subscribe([case_topic("case-2")]) as other:
            await bus.publish(case_topic("case-1"), EVENT_MESSAGE_CREATED, {"x": 1})

            assert mine.qsize() == 1
            assert other.qsize() == 0, "sự kiện của ca khác không được rò sang"


@pytest.mark.asyncio
async def test_unsubscribing_removes_the_listener_from_the_topic():
    bus = InMemoryEventBus()
    async with bus.subscribe([STAFF_QUEUE_TOPIC]):
        assert bus.subscriber_count(STAFF_QUEUE_TOPIC) == 1
    assert bus.subscriber_count(STAFF_QUEUE_TOPIC) == 0

    delivered = await bus.publish(STAFF_QUEUE_TOPIC, EVENT_MESSAGE_CREATED, {})
    assert delivered == 0


@pytest.mark.asyncio
async def test_a_slow_listener_drops_the_oldest_event_instead_of_blocking():
    bus = InMemoryEventBus()
    async with bus.subscribe([STAFF_QUEUE_TOPIC]) as queue:
        for index in range(200):
            await asyncio.wait_for(
                bus.publish(STAFF_QUEUE_TOPIC, EVENT_MESSAGE_CREATED, {"n": index}),
                timeout=1.0,
            )

        assert queue.qsize() <= 64
        newest = None
        while not queue.empty():
            newest = queue.get_nowait()
        assert newest is not None
        assert newest.payload["n"] == 199, "phải giữ lại sự kiện mới nhất"


@pytest.mark.asyncio
async def test_publishing_an_undeclared_event_is_a_programming_error():
    bus = InMemoryEventBus()
    with pytest.raises(ValueError):
        await bus.publish(STAFF_QUEUE_TOPIC, "case.exploded", {})


@pytest.mark.asyncio
async def test_disconnect_during_websocket_accept_is_not_a_server_error():
    class DisconnectedSocket:
        async def accept(self) -> None:
            raise OSError("client disconnected during handshake")

    with pytest.raises(WebSocketDisconnect) as error:
        await _serve(cast(WebSocket, DisconnectedSocket()), [STAFF_QUEUE_TOPIC])

    assert error.value.code == 1006


# ---------------------------------------------------------------------------
# Hội thoại hai chiều
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_nurse_message_is_stored_with_its_real_author(db_session):
    case, _, nurse = await _seed(db_session)

    await send_case_message(
        case.id,
        SendCaseMessageRequestDTO(content="Chị đang xem hồ sơ của anh."),
        nurse,
        db_session,
    )

    stored = (
        await db_session.execute(
            select(ChatMessage).where(ChatMessage.triage_case_id == case.id)
        )
    ).scalars().all()
    assert len(stored) == 1
    assert stored[0].sender_type == "NURSE"
    assert stored[0].sender_id == nurse.id
    assert stored[0].sender_display_name == "Điều dưỡng Trần B"


@pytest.mark.asyncio
async def test_resending_the_same_client_id_does_not_duplicate_the_record(db_session):
    case, _, nurse = await _seed(db_session)
    payload = SendCaseMessageRequestDTO(content="Anh còn đau ngực không?", client_message_id="c-1")

    await send_case_message(case.id, payload, nurse, db_session)
    await send_case_message(case.id, payload, nurse, db_session)

    stored = (
        await db_session.execute(
            select(ChatMessage).where(ChatMessage.triage_case_id == case.id)
        )
    ).scalars().all()
    assert len(stored) == 1, "một lần bấm gửi chỉ được tạo một bản ghi"


@pytest.mark.asyncio
async def test_reading_the_full_record_still_requires_claiming_the_case(db_session):
    """Kênh liên lạc mở, nhưng hồ sơ lâm sàng thì không."""
    case, _, _ = await _seed(db_session, claimed=False)
    stranger = User(id="nurse-2", email="n2@test.vn", full_name="ĐD Khác", role="CLINICAL_NURSE")
    db_session.add(stranger)
    await db_session.commit()

    with pytest.raises(HTTPException) as read_error:
        await list_case_messages(case.id, stranger, db_session)
    assert read_error.value.status_code == 409


@pytest.mark.asyncio
async def test_replying_from_the_queue_claims_the_case_for_that_nurse(db_session):
    """Trả lời người bệnh là đã nhận trách nhiệm với ca đó.

    Bắt nhân viên mở toàn bộ hồ sơ rồi bấm nhận ca mới được trả lời chính là thứ
    khiến tin của người bệnh nằm im ở bản trước.
    """
    case, _, _ = await _seed(db_session, claimed=False)
    nurse = User(id="nurse-2", email="n2@test.vn", full_name="ĐD Trực", role="CLINICAL_NURSE")
    db_session.add(nurse)
    await db_session.commit()

    await send_case_message(
        case.id,
        SendCaseMessageRequestDTO(content="Chào anh, em là điều dưỡng trực."),
        nurse,
        db_session,
    )

    review = (
        await db_session.execute(
            select(NurseReviewState).where(NurseReviewState.triage_case_id == case.id)
        )
    ).scalars().first()
    assert review is not None
    assert review.assigned_nurse_id == nurse.id
    assert review.review_status == "IN_REVIEW"


@pytest.mark.asyncio
async def test_a_second_nurse_cannot_take_over_a_case_by_replying(db_session):
    """Hai người cùng tưởng mình độc quyền một ca là tình huống phải chặn."""
    case, _, owner = await _seed(db_session, claimed=True)
    intruder = User(id="nurse-3", email="n3@test.vn", full_name="ĐD Khác", role="CLINICAL_NURSE")
    db_session.add(intruder)
    await db_session.commit()

    with pytest.raises(HTTPException) as error:
        await send_case_message(
            case.id,
            SendCaseMessageRequestDTO(content="Để tôi xử lý ca này"),
            intruder,
            db_session,
        )
    assert error.value.status_code == 409
    assert owner.full_name in error.value.detail


@pytest.mark.asyncio
async def test_a_patient_cannot_touch_a_case_that_is_not_theirs(db_session):
    case, _, _ = await _seed(db_session)
    intruder = User(id="patient-2", email="p2@test.vn", full_name="B", role="PATIENT")
    db_session.add(intruder)
    await db_session.commit()

    with pytest.raises(HTTPException) as error:
        await _owned_case_or_404(db_session, case.id, intruder)
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_unread_count_falls_to_zero_only_after_the_staff_reads(db_session):
    case, patient, nurse = await _seed(db_session)
    await send_message_to_staff(
        case.id,
        SendStaffMessageRequestDTO(content="Em vẫn thấy tức ngực ạ."),
        patient,
        db_session,
    )

    before = await list_case_messages(case.id, nurse, db_session)
    assert before.unread_count == 1

    after = await mark_case_messages_read(case.id, nurse, db_session)
    assert after.unread_count == 0


@pytest.mark.asyncio
async def test_the_patient_can_write_before_anyone_has_taken_the_case(db_session):
    """Tin phải tới được trạm trực trước khi có người mở hồ sơ.

    Bản trước chặn ở đây, và vì việc nhận ca lại xảy ra bằng cách mở hồ sơ, hệ
    quả là không tin nào của người bệnh tới được trạm trực cho tới lúc có ai đó
    chủ động mở ca ra — ngược hẳn mô hình HITL.
    """
    case, patient, _ = await _seed(db_session, claimed=False)

    state = await send_message_to_staff(
        case.id,
        SendStaffMessageRequestDTO(content="Có ai ở đó không ạ?"),
        patient,
        db_session,
    )
    assert state.care_team_status == "WAITING_REVIEW"

    stored = (
        await db_session.execute(
            select(ChatMessage).where(
                ChatMessage.triage_case_id == case.id,
                ChatMessage.sender_type == "PATIENT",
            )
        )
    ).scalars().all()
    assert len(stored) == 1
    assert stored[0].channel == "CARE_TEAM"


@pytest.mark.asyncio
async def test_a_closed_case_stops_accepting_new_messages(db_session):
    case, patient, _ = await _seed(db_session, claimed=False)
    case.status = "COMPLETED"
    await db_session.commit()

    with pytest.raises(HTTPException) as error:
        await send_message_to_staff(
            case.id,
            SendStaffMessageRequestDTO(content="Cho em hỏi thêm"),
            patient,
            db_session,
        )
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_the_patient_sees_who_is_helping_them(db_session):
    case, _, _ = await _seed(db_session)

    name, care_status = await _care_team_view(db_session, case)
    assert name == "Điều dưỡng Trần B"
    assert care_status == "STAFF_REVIEWING"


@pytest.mark.asyncio
async def test_an_unclaimed_case_never_names_a_carer(db_session):
    case, _, _ = await _seed(db_session, claimed=False)

    name, care_status = await _care_team_view(db_session, case)
    assert name is None
    assert care_status == "WAITING_REVIEW"


@pytest.mark.asyncio
async def test_marking_staff_messages_read_clears_the_patient_badge(db_session):
    case, patient, nurse = await _seed(db_session)
    await send_case_message(
        case.id,
        SendCaseMessageRequestDTO(content="Anh giữ máy giúp em nhé."),
        nurse,
        db_session,
    )

    state = await mark_staff_messages_read(case.id, patient, db_session)
    assert state.unread_from_staff == 0
    assert state.care_team_name == "Điều dưỡng Trần B"

    # PostgreSQL dùng TIMESTAMP WITHOUT TIME ZONE: ghi một datetime mang múi giờ
    # sẽ ném DataError lúc chạy thật, dù SQLite trong bài kiểm thử vẫn chấp nhận.
    stored = (
        await db_session.execute(
            select(ChatMessage).where(ChatMessage.sender_type == "NURSE")
        )
    ).scalars().first()
    assert stored is not None and stored.read_at is not None
    assert stored.read_at.tzinfo is None, "mốc thời gian phải là UTC không mang offset"


# ---------------------------------------------------------------------------
# Danh bạ khẩn cấp — không được lẫn số bệnh nhân với số chủ tài khoản
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_case_about_a_relative_keeps_the_two_numbers_apart(db_session):
    child = EHRProfile(
        id="profile-child",
        user_id="patient-1",
        full_name="Bé Nguyễn Văn C",
        relationship_type="CHILD",
        phone_number="0987654321",
        emergency_contact_name="Bà nội",
        emergency_contact_phone="0911222333",
    )
    case, _, nurse = await _seed(db_session, profile=child)

    result = await get_case_emergency_contacts(case.id, nurse, db_session)
    by_label = {contact.label: contact for contact in result.contacts}

    assert by_label["Bệnh nhân"].full_name == "Bé Nguyễn Văn C"
    assert by_label["Bệnh nhân"].phone == "0987654321"
    assert by_label["Chủ tài khoản / người giám hộ"].phone == "0912345678"
    assert by_label["Người liên hệ khẩn cấp"].phone == "0911222333"
    assert (
        by_label["Bệnh nhân"].phone != by_label["Chủ tài khoản / người giám hộ"].phone
    ), "số của trẻ và số của người giám hộ phải tách bạch"


@pytest.mark.asyncio
async def test_a_missing_number_is_reported_as_missing_not_invented(db_session):
    child = EHRProfile(
        id="profile-child",
        user_id="patient-1",
        full_name="Bé Nguyễn Văn C",
        relationship_type="CHILD",
        phone_number=None,
    )
    case, _, nurse = await _seed(db_session, profile=child)

    result = await get_case_emergency_contacts(case.id, nurse, db_session)
    patient_contact = next(c for c in result.contacts if c.label == "Bệnh nhân")
    assert patient_contact.phone is None, "không được mượn tạm số của chủ tài khoản"


@pytest.mark.asyncio
async def test_the_account_owners_own_case_lists_a_single_patient_number(db_session):
    own = EHRProfile(
        id="profile-self",
        user_id="patient-1",
        full_name="Nguyễn Văn A",
        relationship_type="SELF",
        is_primary=True,
    )
    case, _, nurse = await _seed(db_session, profile=own)

    result = await get_case_emergency_contacts(case.id, nurse, db_session)
    labels = [contact.label for contact in result.contacts]
    assert labels == ["Bệnh nhân"]
    assert result.contacts[0].phone == "0912345678"


@pytest.mark.asyncio
async def test_the_legacy_pii_dialog_also_returns_the_patients_own_number(db_session):
    """Cả hai lối xem thông tin liên hệ phải trả về cùng một số.

    Nếu lối cũ vẫn trả số chủ tài khoản thì nhân viên có thể gọi nhầm người
    giám hộ khi tưởng đang gọi bệnh nhân.
    """
    child = EHRProfile(
        id="profile-child",
        user_id="patient-1",
        full_name="Bé Nguyễn Văn C",
        relationship_type="CHILD",
        phone_number="0987654321",
    )
    case, _, nurse = await _seed(db_session, profile=child)

    legacy = await access_case_pii(
        case.id,
        PiiAccessRequestDTO(reason="Cần gọi xác minh triệu chứng cho ca khẩn."),
        nurse,
        db_session,
    )
    assert legacy.phone == "0987654321", "phải là số của bé, không phải số chủ tài khoản"
    assert legacy.full_name == "Bé Nguyễn Văn C"
