from fastapi import APIRouter, Depends

from app.auth import require_current_user
from app.schemas import not_implemented
from app.schemas import ApiResponse

router = APIRouter(
    prefix="/api/v1/tm/billing",
    tags=["billing"],
    dependencies=[Depends(require_current_user)],
)


@router.get("/plan", response_model=ApiResponse)
def plan() -> dict:
    return not_implemented("GET /api/v1/tm/billing/plan")


@router.get("/usage", response_model=ApiResponse)
def usage() -> dict:
    return not_implemented("GET /api/v1/tm/billing/usage")


@router.post("/quota/check", response_model=ApiResponse)
def quota_check() -> dict:
    return not_implemented("POST /api/v1/tm/billing/quota/check")
