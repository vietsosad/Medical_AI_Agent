"""Tạo (hoặc đặt lại) bộ tài khoản demo để chạy thử luồng Người bệnh ↔ Điều dưỡng.

Script này chỉ dùng cho môi trường phát triển. Nó tái hiện đúng những gì
``POST /auth/register`` tạo ra sau khi xác thực OTP: một tài khoản đang hoạt động
kèm hồ sơ EHR gốc, cộng thêm một hồ sơ người thân để thử đúng tình huống ở §28
(số của bệnh nhân khác số của người giám hộ).

Chạy lại được nhiều lần: mỗi lần đều đặt mật khẩu về giá trị đã biết, nên buổi
demo luôn bắt đầu từ một trạng thái xác định.

    python scripts/seed_demo_accounts.py
"""

import asyncio
import sys
from pathlib import Path

# Chạy thẳng bằng `python scripts/seed_demo_accounts.py` thì thư mục làm việc là
# scripts/, nên gói `src` không nằm trên sys.path. Cùng một bước nạp như
# scripts/seed_health_topics.py -- thiếu nó thì script chết ngay ở dòng import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import select  # noqa: E402
from sqlmodel.ext.asyncio.session import AsyncSession  # noqa: E402

from src.models.db_models import EHRProfile, User, get_utc_now  # noqa: E402
from src.services.db import async_engine, init_db_schema  # noqa: E402
from src.services.security import hash_password  # noqa: E402

# ---------------------------------------------------------------------------
# Bộ tài khoản demo
# ---------------------------------------------------------------------------

PATIENT_EMAIL = "demo.patient@ai20k.local"
PATIENT_PASSWORD = "DemoPatient123!"
PATIENT_NAME = "Nguyễn Văn Demo"
PATIENT_PHONE = "0912345678"

NURSE_EMAIL = "demo.nurse@ai20k.local"
NURSE_PASSWORD = "DemoNurse123!"
NURSE_NAME = "Điều dưỡng Trần Thị Bình"

DOCTOR_EMAIL = "demo.doctor@ai20k.local"
DOCTOR_PASSWORD = "DemoDoctor123!"
DOCTOR_NAME = "Bác sĩ Lê Minh Quân"

# Hồ sơ người thân, để thử đúng tình huống ca không thuộc về chủ tài khoản.
CHILD_NAME = "Bé Nguyễn An"
CHILD_PHONE = "0987654321"
GUARDIAN_CONTACT_NAME = "Bà nội - Trần Thị Hoa"
GUARDIAN_CONTACT_PHONE = "0911222333"


async def _upsert_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    role: str,
    phone: str | None = None,
) -> tuple[User, bool]:
    """Tạo mới hoặc đặt lại tài khoản về trạng thái demo đã biết."""
    found = (await session.execute(select(User).where(User.email == email))).scalars().first()
    if found is None:
        found = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
            phone=phone,
            is_active=True,
        )
        session.add(found)
        await session.commit()
        await session.refresh(found)
        return found, True

    found.hashed_password = hash_password(password)
    found.full_name = full_name
    found.role = role
    found.is_active = True
    if phone is not None:
        found.phone = phone
    found.updated_at = get_utc_now()
    await session.commit()
    await session.refresh(found)
    return found, False


async def _upsert_profile(
    session: AsyncSession,
    *,
    user_id: str,
    full_name: str,
    relationship_type: str,
    **fields: object,
) -> EHRProfile:
    """Một hồ sơ EHR cho mỗi (tài khoản, quan hệ, tên) trong bộ demo."""
    existing = (
        await session.execute(
            select(EHRProfile).where(
                EHRProfile.user_id == user_id,
                EHRProfile.relationship_type == relationship_type,
                EHRProfile.full_name == full_name,
            )
        )
    ).scalars().first()

    profile = existing or EHRProfile(
        user_id=user_id,
        full_name=full_name,
        relationship_type=relationship_type,
    )
    for key, value in fields.items():
        setattr(profile, key, value)
    profile.updated_at = get_utc_now()
    if existing is None:
        session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


async def main() -> None:
    await init_db_schema()

    # expire_on_commit=False: sau commit vẫn đọc được thuộc tính đã nạp mà không
    # kích hoạt một vòng IO đồng bộ giữa ngữ cảnh async.
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        patient, patient_created = await _upsert_user(
            session,
            email=PATIENT_EMAIL,
            password=PATIENT_PASSWORD,
            full_name=PATIENT_NAME,
            role="PATIENT",
            phone=PATIENT_PHONE,
        )
        nurse, nurse_created = await _upsert_user(
            session,
            email=NURSE_EMAIL,
            password=NURSE_PASSWORD,
            full_name=NURSE_NAME,
            role="CLINICAL_NURSE",
        )
        doctor, doctor_created = await _upsert_user(
            session,
            email=DOCTOR_EMAIL,
            password=DOCTOR_PASSWORD,
            full_name=DOCTOR_NAME,
            role="DOCTOR",
        )

        await _upsert_profile(
            session,
            user_id=patient.id,
            full_name=PATIENT_NAME,
            relationship_type="SELF",
            is_primary=True,
            age=34,
            gender="Male",
            blood_type="O+",
            phone_number=PATIENT_PHONE,
        )
        # Ca của người thân: số của bé khác hẳn số của chủ tài khoản, đúng tình
        # huống mà console lâm sàng phải hiển thị tách bạch.
        await _upsert_profile(
            session,
            user_id=patient.id,
            full_name=CHILD_NAME,
            relationship_type="CHILD",
            is_primary=False,
            age=7,
            gender="Male",
            blood_type="A+",
            phone_number=CHILD_PHONE,
            emergency_contact_name=GUARDIAN_CONTACT_NAME,
            emergency_contact_phone=GUARDIAN_CONTACT_PHONE,
        )

    print("\n" + "=" * 68)
    print("  TÀI KHOẢN DEMO ĐÃ SẴN SÀNG")
    print("=" * 68)
    for label, email, password, created in (
        ("Người bệnh ", PATIENT_EMAIL, PATIENT_PASSWORD, patient_created),
        ("Điều dưỡng ", NURSE_EMAIL, NURSE_PASSWORD, nurse_created),
        ("Bác sĩ     ", DOCTOR_EMAIL, DOCTOR_PASSWORD, doctor_created),
    ):
        print(f"  {label} {email:<32} {password:<18} {'(mới tạo)' if created else '(đã đặt lại)'}")
    print("=" * 68)
    print(f"  Hồ sơ người thân: {CHILD_NAME} — SĐT riêng {CHILD_PHONE}")
    print(f"  Chủ tài khoản   : {PATIENT_NAME} — SĐT {PATIENT_PHONE}")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
