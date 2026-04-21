from fastapi import APIRouter, Depends

from app.auth import require_current_user
from app.context import build_core_headers
from app.core_client import forward
from app.models import RetrievalDebugRequest
from app.schemas import ApiResponse

router = APIRouter(
    prefix="/api/v1/tm/retrieval",
    tags=["retrieval"],
    dependencies=[Depends(require_current_user)],
)


@router.post("/debug", response_model=ApiResponse)
async def retrieval_debug(
    payload: RetrievalDebugRequest, claims: dict = Depends(require_current_user)
) -> dict:
    return await forward(
        "POST",
        "/internal/core/knowledge/retrieval/debug",
        json_body=payload.model_dump(),
        headers=build_core_headers(claims),
    )
