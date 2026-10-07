"""API Router Quản Trị Hồ Sơ Gia Đình & Thân Nhân Phụ Thuộc (Multi-Profile Family Care).

Tuân thủ tuyệt đối quy tắc tại .agents/rules/backend-rules.md:
- Kiến trúc modular async router với FastAPI.
- Trả về DTO chu đáo, tuyệt đối không lộ nhầm hồ sơ sang tài khoản không thuộc sở hữu.
- Cam kết an toàn lâm sàng, hỗ trợ tạo nhanh (<15s) và cấm xóa hồ sơ chủ tài khoản gốc.
"""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from src.api.dependencies import PatientUserDep, SessionDep
from src.models.auth_schemas import StandardMessageResponseDTO
from src.models.db_models import EHRProfile
from src.models.profile_schemas import (
    AllergyDTO,
    CreateProfileRequestDTO,
    EhrLiteDTO,
    EmergencyContactDTO,
    MedicationDTO,
    ProfileResponseDTO,
    UpdateProfileRequestDTO,
)
from src.services.log_redaction import pseudonym

router = APIRouter(prefix="/profiles", tags=["Family Medical Profiles"])


# ============================================================================
# HELPERS
# ============================================================================

def _build_ehr_lite(profile: EHRProfile) -> EhrLiteDTO:
    """Chuyển đổi EHRProfile ORM object → EhrLiteDTO cho API response."""
    allergies_dtos: list[AllergyDTO] = []
    if profile.allergies:
        for idx, item in enumerate(profile.allergies):
            if isinstance(item, dict):
                # Đảm bảo dict có id; nếu không thì tạo mới
                if "id" not in item or not item["id"]:
                    item["id"] = f"alg-{idx}-{uuid.uuid4().hex[:6]}"
                allergies_dtos.append(AllergyDTO(**item))
            elif isinstance(item, str):
                allergies_dtos.append(AllergyDTO(
                    id=f"alg-{idx}-{uuid.uuid4().hex[:6]}",
                    name=item,
                    type="MEDICATION",
                    severity="HIGH"
                ))

    medications_dtos: list[MedicationDTO] = []
    if profile.daily_medications:
        for idx, item in enumerate(profile.daily_medications):
            if isinstance(item, dict):
                if "id" not in item or not item["id"]:
                    item["id"] = f"med-{idx}-{uuid.uuid4().hex[:6]}"
                medications_dtos.append(MedicationDTO(**item))
            elif isinstance(item, str):
                medications_dtos.append(MedicationDTO(
                    id=f"med-{idx}-{uuid.uuid4().hex[:6]}",
                    name=item,
                    dosage="Theo chỉ định",
                    frequency="Hằng ngày"
                ))

    # Serialize last_updated thành ISO string để khớp Frontend Zod schema
    last_updated_str: str | None = None
    if profile.updated_at:
        last_updated_str = profile.updated_at.isoformat()

    return EhrLiteDTO(
        patient_id=profile.id,
        age=profile.age,
        gender=profile.gender,           # Validator trong EhrLiteDTO sẽ normalize UPPERCASE
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        blood_type=profile.blood_type,
        chronic_conditions=profile.chronic_conditions or [],
        allergies=allergies_dtos,
        current_medications=medications_dtos,
        last_updated=last_updated_str,
    )


def _build_emergency_contacts(profile: EHRProfile) -> list[EmergencyContactDTO]:
    """Đọc danh sách emergency contacts từ JSON column. Backward compat với legacy name+phone fields."""
    # Ưu tiên đọc từ JSON array đầy đủ
    if profile.emergency_contacts_json:
        contacts: list[EmergencyContactDTO] = []
        for idx, item in enumerate(profile.emergency_contacts_json):
            if isinstance(item, dict):
                # Đảm bảo luôn có id
                if "id" not in item or not item["id"]:
                    item["id"] = f"sos-{idx}-{uuid.uuid4().hex[:6]}"
                try:
                    contacts.append(EmergencyContactDTO(**item))
                except Exception:
                    pass  # Skip malformed records
        return contacts

    # Backward compat: nếu chưa có JSON array, đọc từ legacy columns
    if profile.emergency_contact_name and profile.emergency_contact_phone:
        return [EmergencyContactDTO(
            id=f"sos-legacy-{uuid.uuid4().hex[:6]}",
            full_name=profile.emergency_contact_name,
            relationship="OTHER",
            phone_number=profile.emergency_contact_phone,
            is_primary=True,
        )]

    return []


# ============================================================================
# ROUTE HANDLERS
# ============================================================================

@router.get("", response_model=list[ProfileResponseDTO], status_code=status.HTTP_200_OK)
async def list_user_profiles(
    current_user: PatientUserDep,
    session: SessionDep,
) -> list[ProfileResponseDTO]:
    """Lấy danh sách toàn bộ hồ sơ trong gia đình thuộc thẩm quyền tài khoản đang đăng nhập.
    
    Hồ sơ chính (SELF - is_primary=True) luôn được sắp xếp hiển thị lên hàng đầu tiên.
    """
    query = (
        select(EHRProfile)
        .where(EHRProfile.user_id == current_user.id)
        .order_by(EHRProfile.is_primary.desc(), EHRProfile.updated_at.desc())
    )
    result = await session.execute(query)
    profiles = result.scalars().all()

    if not profiles:
        # Tạo hồ sơ SELF với thông tin thực từ tài khoản, không hardcode mock data
        print(f"🏥 [Family Care] Tài khoản {pseudonym(current_user.id, prefix='user')} chưa có hồ sơ y tế, tự động khởi tạo SELF profile...")
        self_profile = EHRProfile(
            user_id=current_user.id,
            full_name=current_user.full_name or "Bệnh nhân chính chủ",
            relationship_type="SELF",
            is_primary=True,
            avatar_color="blue",
            # Không hardcode age, gender, blood_type — để người dùng tự khai báo
            age=None,
            gender=None,
            blood_type=None,
            chronic_conditions=[],
            daily_medications=[],
            allergies=[],
            emergency_contacts_json=[],
        )
        session.add(self_profile)
        await session.commit()
        await session.refresh(self_profile)
        profiles = [self_profile]

    return [ProfileResponseDTO.model_validate(p) for p in profiles]


@router.post("", response_model=ProfileResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_dependent_profile(
    payload: CreateProfileRequestDTO,
    current_user: PatientUserDep,
    session: SessionDep,
) -> ProfileResponseDTO:
    """Tạo nhanh hồ sơ y tế cho thành viên thân nhân trong gia đình (< 15s Agile Onboarding)."""
    is_primary = False
    if payload.relationship_type == "SELF":
        check_query = select(EHRProfile).where(
            EHRProfile.user_id == current_user.id, EHRProfile.relationship_type == "SELF"
        )
        res = await session.execute(check_query)
        if res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tài khoản này đã sở hữu hồ sơ gốc của bản thân (SELF). Mỗi tài khoản chỉ có 1 hồ sơ SELF duy nhất."
            )
        is_primary = True

    new_profile = EHRProfile(
        user_id=current_user.id,
        full_name=payload.full_name,
        relationship_type=payload.relationship_type,
        is_primary=is_primary,
        dob=payload.dob,
        age=payload.age,
        gender=payload.gender,
        phone_number=payload.phone_number,
        avatar_color=payload.avatar_color,
        blood_type=payload.blood_type,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        chronic_conditions=payload.chronic_conditions or [],
        daily_medications=payload.daily_medications or [],
        allergies=payload.allergies or [],
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
        emergency_contacts_json=[],
    )
    session.add(new_profile)
    await session.commit()
    await session.refresh(new_profile)

    print(f"🏥 [Family Care] Tài khoản {pseudonym(current_user.id, prefix='user')} vừa thêm hồ sơ thân nhân {pseudonym(new_profile.id, prefix='profile')} ({new_profile.relationship_type})")
    return ProfileResponseDTO.model_validate(new_profile)


@router.get("/{profile_id}", response_model=ProfileResponseDTO, status_code=status.HTTP_200_OK)
async def get_profile_detail(
    profile_id: str,
    current_user: PatientUserDep,
    session: SessionDep,
) -> ProfileResponseDTO:
    """Truy vấn thông tin chi tiết một hồ sơ cụ thể trong danh sách gia đình."""
    query = select(EHRProfile).where(
        EHRProfile.id == profile_id, EHRProfile.user_id == current_user.id
    )
    result = await session.execute(query)
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hồ sơ thân nhân y khoa không tồn tại hoặc không thuộc quyền truy cập của bạn."
        )
    return ProfileResponseDTO.model_validate(profile)


@router.put("/{profile_id}", response_model=ProfileResponseDTO, status_code=status.HTTP_200_OK)
async def update_profile_detail(
    profile_id: str,
    payload: UpdateProfileRequestDTO,
    current_user: PatientUserDep,
    session: SessionDep,
) -> ProfileResponseDTO:
    """Cập nhật các thông số sinh trắc học, tiền sử bệnh nền, hoặc dị ứng thuốc cho hồ sơ."""
    query = select(EHRProfile).where(
        EHRProfile.id == profile_id, EHRProfile.user_id == current_user.id
    )
    result = await session.execute(query)
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hồ sơ thân nhân y khoa không tồn tại hoặc không thuộc quyền sở hữu của bạn."
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field_name, val in update_data.items():
        setattr(profile, field_name, val)

    session.add(profile)
    await session.commit()
    await session.refresh(profile)

    return ProfileResponseDTO.model_validate(profile)


@router.delete("/{profile_id}", response_model=StandardMessageResponseDTO, status_code=status.HTTP_200_OK)
async def delete_dependent_profile(
    profile_id: str,
    current_user: PatientUserDep,
    session: SessionDep,
) -> StandardMessageResponseDTO:
    """Xóa bỏ một hồ sơ người thân khỏi danh sách (Nghiêm cấm xóa hồ sơ gốc SELF của tài khoản)."""
    query = select(EHRProfile).where(
        EHRProfile.id == profile_id, EHRProfile.user_id == current_user.id
    )
    result = await session.execute(query)
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hồ sơ y tế cần xóa không tồn tại hoặc bạn không có thẩm quyền."
        )

    if profile.is_primary or profile.relationship_type == "SELF":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn không thể tự xóa bỏ hồ sơ y khoa chính chủ (SELF) của chính tài khoản mình!"
        )

    profile_name = profile.full_name
    await session.delete(profile)
    await session.commit()

    return StandardMessageResponseDTO(
        success=True,
        message=f"Đã gõ bỏ hoàn toàn hồ sơ của thành viên '{profile_name}' ra khỏi danh sách quản trị gia đình."
    )


# ============================================================================
# EHR LITE ENDPOINTS
# ============================================================================

@router.get("/{profile_id}/ehr-lite", response_model=EhrLiteDTO, status_code=status.HTTP_200_OK)
async def get_profile_ehr_lite(
    profile_id: str,
    current_user: PatientUserDep,
    session: SessionDep,
) -> EhrLiteDTO:
    """Lấy dữ liệu lâm sàng ngắn gọn (EHR Lite) cho một hồ sơ cụ thể."""
    query = select(EHRProfile).where(
        EHRProfile.id == profile_id, EHRProfile.user_id == current_user.id
    )
    result = await session.execute(query)
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hồ sơ lâm sàng không tồn tại.")
    return _build_ehr_lite(profile)


@router.put("/{profile_id}/ehr-lite", response_model=EhrLiteDTO, status_code=status.HTTP_200_OK)
async def update_profile_ehr_lite(
    profile_id: str,
    payload: EhrLiteDTO,
    current_user: PatientUserDep,
    session: SessionDep,
) -> EhrLiteDTO:
    """Cập nhật dữ liệu lâm sàng ngắn gọn cho hồ sơ y tế."""
    query = select(EHRProfile).where(
        EHRProfile.id == profile_id, EHRProfile.user_id == current_user.id
    )
    result = await session.execute(query)
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hồ sơ lâm sàng không tồn tại.")

    # Chỉ cập nhật fields được gửi lên; bảo toàn các fields khác
    if payload.age is not None:
        profile.age = payload.age
    if payload.gender is not None:
        profile.gender = payload.gender
    if payload.height_cm is not None:
        profile.height_cm = payload.height_cm
    if payload.weight_kg is not None:
        profile.weight_kg = payload.weight_kg
    if payload.blood_type is not None:
        profile.blood_type = payload.blood_type

    profile.chronic_conditions = payload.chronic_conditions
    profile.allergies = [a.model_dump() for a in payload.allergies]
    profile.daily_medications = [m.model_dump() for m in payload.current_medications]

    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return _build_ehr_lite(profile)


# ============================================================================
# EMERGENCY CONTACTS ENDPOINTS
# ============================================================================

@router.get("/{profile_id}/emergency-contacts", response_model=list[EmergencyContactDTO], status_code=status.HTTP_200_OK)
async def get_profile_emergency_contacts(
    profile_id: str,
    current_user: PatientUserDep,
    session: SessionDep,
) -> list[EmergencyContactDTO]:
    """Lấy danh sách người liên hệ khẩn cấp (SOS) cho một hồ sơ — hỗ trợ tối đa 3 contacts."""
    query = select(EHRProfile).where(
        EHRProfile.id == profile_id, EHRProfile.user_id == current_user.id
    )
    result = await session.execute(query)
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hồ sơ lâm sàng không tồn tại.")

    return _build_emergency_contacts(profile)


@router.put("/{profile_id}/emergency-contacts", response_model=list[EmergencyContactDTO], status_code=status.HTTP_200_OK)
async def update_profile_emergency_contacts(
    profile_id: str,
    contacts: list[EmergencyContactDTO],
    current_user: PatientUserDep,
    session: SessionDep,
) -> list[EmergencyContactDTO]:
    """Cập nhật toàn bộ danh sách người liên hệ khẩn cấp (SOS) — tối đa 3 thẻ."""
    if len(contacts) > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hệ thống chỉ cho phép tối đa 3 người liên hệ khẩn cấp (SOS) trên mỗi hồ sơ."
        )

    query = select(EHRProfile).where(
        EHRProfile.id == profile_id, EHRProfile.user_id == current_user.id
    )
    result = await session.execute(query)
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hồ sơ lâm sàng không tồn tại.")

    # Đảm bảo mỗi contact có id duy nhất
    contacts_with_ids: list[EmergencyContactDTO] = []
    for contact in contacts:
        if not contact.id:
            contact = contact.model_copy(update={"id": f"sos-{uuid.uuid4().hex[:8]}"})
        contacts_with_ids.append(contact)

    # Lưu toàn bộ array vào JSON column
    profile.emergency_contacts_json = [c.model_dump() for c in contacts_with_ids]

    # Cập nhật derived legacy columns từ contact ưu tiên số 1
    primary_contact = next((c for c in contacts_with_ids if c.is_primary), None)
    if primary_contact is None and contacts_with_ids:
        primary_contact = contacts_with_ids[0]

    if primary_contact:
        profile.emergency_contact_name = primary_contact.full_name
        profile.emergency_contact_phone = primary_contact.phone_number
    else:
        profile.emergency_contact_name = None
        profile.emergency_contact_phone = None

    session.add(profile)
    await session.commit()
    await session.refresh(profile)

    return contacts_with_ids
