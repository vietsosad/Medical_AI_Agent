"""APIRouter tra cứu cơ sở y tế gần người bệnh.

Router bổ sung, hoàn toàn tách khỏi luồng lâm sàng: nó không đọc ``triage_cases``,
không đọc nhóm bảng ``simple_agent_*``, không ghi ``AuditLog`` lâm sàng và không
tham gia vào bất kỳ quyết định ESI nào. Bật hay tắt nó cũng không làm thay đổi
một dòng nào trong hành vi phân loại.

**Vì sao endpoint không tự khoá theo mức ESI.** Yêu cầu sản phẩm là hiện tính
năng này cho các mức ESI 1/2/3, và điều kiện đó được áp ở tầng hiển thị, dựa
trên mức ESI mà backend đã chốt (xem ``NearbyFacilitiesCard``). Nếu áp thêm một
lần nữa ở đây, ta đặt một điểm có thể hỏng nằm đúng trên đường thoát khẩn cấp:
gate lỗi đồng nghĩa với việc **giấu danh sách bệnh viện khỏi một người đang cấp
cứu**. Chiều hỏng ngược lại -- một người bệnh nhẹ xem được danh sách bệnh viện
công khai -- không gây hại cho ai. Nên cổng ở đây chỉ là cổng xác thực.

**Vì sao là POST.** Toạ độ của một người đang cấp cứu là dữ liệu cá nhân nhạy
cảm. Đặt nó trong query string thì nó đọng lại ở access log của web server, ở
lịch sử trình duyệt và ở header ``Referer`` gửi sang bên thứ ba. Thân request
không đi qua những chỗ đó.
"""

from fastapi import APIRouter, status

from src.api.dependencies import PatientUserDep, SessionDep
from src.models.facility_schemas import NearbyFacilitiesResponse, NearbyFacilityRequest
from src.services.log_redaction import pseudonym
from src.services.nearby_facilities import find_nearby_facilities

router = APIRouter(prefix="/facilities", tags=["Nearby Facilities"])


@router.post(
    "/nearby",
    response_model=NearbyFacilitiesResponse,
    status_code=status.HTTP_200_OK,
)
async def search_nearby_facilities(
    payload: NearbyFacilityRequest,
    session: SessionDep,
    current_user: PatientUserDep,
) -> NearbyFacilitiesResponse:
    """Cơ sở y tế gần toạ độ người bệnh vừa chia sẻ, sắp xếp theo khoảng cách.

    Không có nhánh nào trong endpoint này trả về lỗi vì lý do hạ tầng: provider
    ngoài hỏng hay hết hạn mức đều được lớp dịch vụ nuốt lại thành cờ
    ``degraded`` kèm dữ liệu dự phòng. Người bệnh luôn nhận được một câu trả lời
    dùng được, kể cả khi đó là một danh sách rỗng kèm lời nhắc gọi 115.
    """
    return await find_nearby_facilities(
        session,
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_meters=payload.radius_meters,
        accuracy_meters=payload.accuracy_meters,
        # Định danh đã giả danh hoá: đủ để đếm hạn mức gọi API theo từng tài
        # khoản, không đủ để lần ngược ra người dùng từ bộ đếm trong bộ nhớ.
        user_key=pseudonym(current_user.id, prefix="facility"),
    )
