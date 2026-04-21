from fastapi import APIRouter, Depends, HTTPException

from app.auth import authenticate, create_access_token, require_current_user
from app.models import LoginRequest
from app.schemas import ApiResponse, ok

router = APIRouter(prefix="/api/v1/tm/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse)
def login(payload: LoginRequest) -> dict:
    user = authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="invalid credentials")
    access_token = create_access_token(user)
    return ok(
        {
            "access_token": access_token,
            "refresh_token": "",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "role": user["role"],
                "tenant_id": user["tenant_id"],
            },
        }
    )


@router.get("/me", response_model=ApiResponse)
def me(claims: dict = Depends(require_current_user)) -> dict:
    return ok(
        {
            "id": claims.get("sub"),
            "name": claims.get("name"),
            "role": claims.get("role"),
            "tenant_id": claims.get("tenant_id"),
            "email": claims.get("email"),
        }
    )
