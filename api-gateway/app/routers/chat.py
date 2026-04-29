import os

from fastapi import APIRouter, Depends

from app.auth import optional_current_user, require_current_user
from app.context import build_core_headers
from app.core_client import forward
from app.models import ChatHandoffRequest, ChatMessageRequest, ChatSessionCreateRequest
from app.schemas import ApiResponse

VISITOR_TENANT_ID = os.getenv("VISITOR_TENANT_ID", "1001")
VISITOR_USER_ID = os.getenv("VISITOR_USER_ID", "0")
VISITOR_ROLE = os.getenv("VISITOR_ROLE", "visitor")
router = APIRouter(prefix="/api/v1/tm/chat", tags=["chat"])


def _claims_or_visitor(claims: dict | None) -> dict:
    if claims:
        return claims
    return {
        "tenant_id": VISITOR_TENANT_ID,
        "sub": VISITOR_USER_ID,
        "role": VISITOR_ROLE,
        "name": "Web Visitor",
        "email": "visitor@example.com",
    }


@router.post("/sessions", response_model=ApiResponse)
async def create_session(
    payload: ChatSessionCreateRequest, claims: dict | None = Depends(optional_current_user)
) -> dict:
    resolved_claims = _claims_or_visitor(claims)
    return await forward(
        "POST",
        "/internal/core/chat/sessions",
        json_body=payload.model_dump(),
        headers=build_core_headers(resolved_claims),
    )


@router.get("/admin/sessions", response_model=ApiResponse)
async def list_sessions(
    limit: int = 20,
    status: str | None = None,
    channel: str | None = None,
    claims: dict = Depends(require_current_user),
) -> dict:
    params: dict[str, int | str] = {"limit": limit}
    if status:
        params["status"] = status
    if channel:
        params["channel"] = channel
    return await forward(
        "GET",
        "/internal/core/chat/sessions",
        params=params,
        headers=build_core_headers(claims),
    )


@router.post("/sessions/{session_id}/messages", response_model=ApiResponse)
async def send_message(
    session_id: str, payload: ChatMessageRequest, claims: dict | None = Depends(optional_current_user)
) -> dict:
    resolved_claims = _claims_or_visitor(claims)
    return await forward(
        "POST",
        f"/internal/core/chat/sessions/{session_id}/messages",
        json_body=payload.model_dump(),
        headers=build_core_headers(resolved_claims),
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
async def get_session(session_id: str, claims: dict | None = Depends(optional_current_user)) -> dict:
    resolved_claims = _claims_or_visitor(claims)
    return await forward(
        "GET",
        f"/internal/core/chat/sessions/{session_id}",
        headers=build_core_headers(resolved_claims),
    )
