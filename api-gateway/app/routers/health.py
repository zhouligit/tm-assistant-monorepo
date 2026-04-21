from fastapi import APIRouter

from app.schemas import ApiResponse, ok

router = APIRouter(prefix="/api/v1/tm", tags=["health"])


@router.get("/health", response_model=ApiResponse)
def health() -> dict:
    return ok({"status": "ok"})
