import uuid

from fastapi import APIRouter, HTTPException

from src.agents.deepagent_runtime import get_deepagent_runtime
from src.api.routes_auth import router as auth_router
from src.api.routes_facilities import router as facilities_router
from src.api.routes_health import router as health_router
from src.api.routes_nurse import router as nurse_router
from src.api.routes_nurse_simple import router as nurse_simple_router
from src.api.routes_patient import router as patient_router
from src.api.routes_pdf import router as pdf_router
from src.api.routes_profiles import router as profiles_router
from src.api.routes_simple_triage import router as simple_triage_router
from src.api.routes_ws import router as ws_router
from src.api.routes_ws_simple import router as ws_simple_router
from src.models.schemas import ChatRequest, ChatResponse

router = APIRouter()
router.include_router(auth_router)
router.include_router(profiles_router)
router.include_router(patient_router)
# Additive pilot path for src/simple_agent -- disabled unless
# SIMPLE_AGENT_ENABLED=true, see routes_simple_triage.py's _require_enabled().
router.include_router(simple_triage_router)
# Nurse-side pilot counterpart -- separate table (SimpleAgentNurseReview),
# never touches TriageCase/NurseReviewState, same SIMPLE_AGENT_ENABLED gate.
router.include_router(nurse_simple_router)
router.include_router(nurse_router)
router.include_router(pdf_router)
router.include_router(health_router)
# Tra cứu cơ sở y tế gần người bệnh. Router bổ sung, không đụng tới luồng
# lâm sàng: chỉ đọc bảng danh bạ riêng của nó và gọi provider bản đồ bên
# ngoài -- xem src/api/routes_facilities.py.
router.include_router(facilities_router)
# Kênh WebSocket tự kiểm tra quyền bên trong từng endpoint vì Depends()
# theo kiểu HTTP Bearer không áp dụng được cho handshake WebSocket.
router.include_router(ws_router)
# Kênh WebSocket riêng của pilot simple_agent -- chủ đề tách biệt hoàn toàn
# với ws_router ở trên, xem src/simple_agent/realtime.py.
router.include_router(ws_simple_router)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat với AI agent."""
    try:
        session_id = str(uuid.uuid4())
        result = await get_deepagent_runtime().run_start(
            {"query": request.message},
            session_id=session_id,
        )
        return ChatResponse(
            response=result.get("response", ""),
            analysis=result.get("analysis", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def agent_status() -> dict:
    """Kiểm tra trạng thái agent."""
    return {
        "status": "ready",
        "agent": "MedTriage DeepAgent Supervisor v1.0",
        "clinical_gates": "tool-enforced",
        "durable_recovery": "chat_messages",
    }
