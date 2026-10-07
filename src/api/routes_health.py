"""APIRouter cho mục "Thông tin sức khỏe đáng chú ý" (Health Education).

Đây là nội dung giáo dục sức khỏe công khai: khách chưa đăng nhập vẫn đọc được
danh sách và chi tiết. Chỉ nút "Kiểm tra triệu chứng với AI" mới đi qua luồng
đăng nhập hiện có, vì nó dẫn vào phiên Triage lâm sàng thật.

Endpoint ở đây KHÔNG gọi LLM. Bản diễn giải đã được sinh sẵn và lưu trong CSDL
qua ``scripts/seed_health_topics.py``, nên trang chủ chỉ đọc dữ liệu đã xử lý.
"""

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import SessionDep
from src.models.health_schemas import HealthTopicDetailDTO, HealthTopicSummaryDTO
from src.services.health_topics import get_topic_by_slug, list_published_topics

router = APIRouter(prefix="/health-topics", tags=["Health Education"])

#: Trang chủ trình bày các thẻ thành một dòng chảy ngang liên tục chứ không còn
#: là một lưới cố định, nên trần này giới hạn kích thước phản hồi chứ không còn
#: là quyết định bố cục. Giữ một trần rõ ràng để danh sách không phình vô hạn.
MAX_HOMEPAGE_TOPICS = 24


@router.get("", response_model=list[HealthTopicSummaryDTO], status_code=status.HTTP_200_OK)
async def list_health_topics(session: SessionDep) -> list[HealthTopicSummaryDTO]:
    """Danh sách chủ đề sức khỏe hiển thị trên trang chủ."""
    topics = await list_published_topics(session, limit=MAX_HOMEPAGE_TOPICS)
    return [HealthTopicSummaryDTO.from_model(topic) for topic in topics]


@router.get("/{slug}", response_model=HealthTopicDetailDTO, status_code=status.HTTP_200_OK)
async def get_health_topic_detail(slug: str, session: SessionDep) -> HealthTopicDetailDTO:
    """Nội dung đầy đủ của một chủ đề sức khỏe."""
    topic = await get_topic_by_slug(session, slug)
    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy chủ đề sức khỏe này.",
        )
    return HealthTopicDetailDTO.from_model(topic)
