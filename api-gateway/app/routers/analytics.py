from fastapi import APIRouter, Depends

from app.auth import require_current_user
from app.context import build_core_headers
from app.core_client import forward
from app.schemas import ApiResponse

router = APIRouter(
    prefix="/api/v1/tm/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_current_user)],
)


@router.get("/overview", response_model=ApiResponse)
async def analytics_overview(
    start_date: str | None = None,
    end_date: str | None = None,
    claims: dict = Depends(require_current_user),
) -> dict:
    return await forward(
        "GET",
        "/internal/core/analytics/overview",
        params={"start_date": start_date, "end_date": end_date},
        headers=build_core_headers(claims),
    )


@router.get("/unresolved-topics", response_model=ApiResponse)
async def unresolved_topics(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int | None = None,
    claims: dict = Depends(require_current_user),
) -> dict:
    return await forward(
        "GET",
        "/internal/core/analytics/unresolved-topics",
        params={"start_date": start_date, "end_date": end_date, "limit": limit},
        headers=build_core_headers(claims),
    )


@router.get("/export", response_model=ApiResponse)
async def analytics_export(
    format: str | None = None, claims: dict = Depends(require_current_user)
) -> dict:
    return await forward(
        "GET",
        "/internal/core/analytics/export",
        params={"format": format},
        headers=build_core_headers(claims),
    )
