from fastapi import APIRouter, Depends

from app.auth import require_current_user
from app.context import build_core_headers
from app.core_client import forward
from app.models import CandidateRejectRequest
from app.schemas import ApiResponse

router = APIRouter(
    prefix="/api/v1/tm/kb-candidates",
    tags=["kb-candidates"],
    dependencies=[Depends(require_current_user)],
)


@router.get("", response_model=ApiResponse)
async def list_candidates(
    status: str | None = None, claims: dict = Depends(require_current_user)
) -> dict:
    return await forward(
        "GET",
        "/internal/core/handoff/candidates",
        params={"status": status},
        headers=build_core_headers(claims),
    )


@router.post("/{candidate_id}/approve", response_model=ApiResponse)
async def approve_candidate(
    candidate_id: str, claims: dict = Depends(require_current_user)
) -> dict:
    return await forward(
        "POST",
        f"/internal/core/handoff/candidates/{candidate_id}/approve",
        headers=build_core_headers(claims),
    )


@router.post("/{candidate_id}/reject", response_model=ApiResponse)
async def reject_candidate(
    candidate_id: str,
    payload: CandidateRejectRequest,
    claims: dict = Depends(require_current_user),
) -> dict:
    return await forward(
        "POST",
        f"/internal/core/handoff/candidates/{candidate_id}/reject",
        json_body=payload.model_dump(exclude_none=True),
        headers=build_core_headers(claims),
    )
