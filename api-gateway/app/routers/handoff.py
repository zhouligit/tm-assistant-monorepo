from fastapi import APIRouter, Depends

from app.auth import require_current_user
from app.context import build_core_headers
from app.core_client import forward
from app.models import HandoffReplyRequest
from app.schemas import ApiResponse

router = APIRouter(
    prefix="/api/v1/tm/handoff/queue",
    tags=["handoff"],
    dependencies=[Depends(require_current_user)],
)


@router.get("", response_model=ApiResponse)
async def handoff_queue(
    status: str | None = None,
    assignee_id: str | None = None,
    claims: dict = Depends(require_current_user),
) -> dict:
    return await forward(
        "GET",
        "/internal/core/handoff/queue",
        params={"status": status, "assignee_id": assignee_id},
        headers=build_core_headers(claims),
    )


@router.post("/{handoff_id}/claim", response_model=ApiResponse)
async def claim_handoff(handoff_id: str, claims: dict = Depends(require_current_user)) -> dict:
    return await forward(
        "POST",
        f"/internal/core/handoff/queue/{handoff_id}/claim",
        headers=build_core_headers(claims),
    )


@router.post("/{handoff_id}/reply", response_model=ApiResponse)
async def reply_handoff(
    handoff_id: str,
    payload: HandoffReplyRequest,
    claims: dict = Depends(require_current_user),
) -> dict:
    return await forward(
        "POST",
        f"/internal/core/handoff/queue/{handoff_id}/reply",
        json_body=payload.model_dump(),
        headers=build_core_headers(claims),
    )


@router.post("/{handoff_id}/close", response_model=ApiResponse)
async def close_handoff(handoff_id: str, claims: dict = Depends(require_current_user)) -> dict:
    return await forward(
        "POST",
        f"/internal/core/handoff/queue/{handoff_id}/close",
        headers=build_core_headers(claims),
    )
