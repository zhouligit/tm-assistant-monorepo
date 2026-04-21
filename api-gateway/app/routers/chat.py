from fastapi import APIRouter, Depends

from app.auth import require_current_user
from app.context import build_core_headers
from app.core_client import forward
from app.models import ChatHandoffRequest, ChatMessageRequest, ChatSessionCreateRequest
from app.schemas import ApiResponse

router = APIRouter(
    prefix="/api/v1/tm/chat",
    tags=["chat"],
    dependencies=[Depends(require_current_user)],
)


@router.post("/sessions", response_model=ApiResponse)
async def create_session(
    payload: ChatSessionCreateRequest, claims: dict = Depends(require_current_user)
) -> dict:
    return await forward(
        "POST",
        "/internal/core/chat/sessions",
        json_body=payload.model_dump(),
        headers=build_core_headers(claims),
    )


@router.post("/sessions/{session_id}/messages", response_model=ApiResponse)
async def send_message(
    session_id: str, payload: ChatMessageRequest, claims: dict = Depends(require_current_user)
) -> dict:
    return await forward(
        "POST",
        f"/internal/core/chat/sessions/{session_id}/messages",
        json_body=payload.model_dump(),
        headers=build_core_headers(claims),
    )


@router.post("/sessions/{session_id}/handoff", response_model=ApiResponse)
async def handoff_session(
    session_id: str, payload: ChatHandoffRequest, claims: dict = Depends(require_current_user)
) -> dict:
    return await forward(
        "POST",
        f"/internal/core/chat/sessions/{session_id}/handoff",
        json_body=payload.model_dump(),
        headers=build_core_headers(claims),
    )


@router.get("/sessions/{session_id}", response_model=ApiResponse)
async def get_session(session_id: str, claims: dict = Depends(require_current_user)) -> dict:
    return await forward(
        "GET",
        f"/internal/core/chat/sessions/{session_id}",
        headers=build_core_headers(claims),
    )
