from collections import defaultdict, deque
from time import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import (
    authenticate,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    require_current_user,
)
from app.db import get_db
from app.models import LoginRequest, RefreshTokenRequest
from app.schemas import ApiResponse, ok

router = APIRouter(prefix="/api/v1/tm/auth", tags=["auth"])
FAILED_LOGIN_WINDOW_SECONDS = 5 * 60
FAILED_LOGIN_LIMIT = 5
LOGIN_LOCK_SECONDS = 10 * 60
_failed_login_events: dict[str, deque[float]] = defaultdict(deque)
_login_locks_until: dict[str, float] = {}


def _login_throttle_key(email: str, client_ip: str) -> str:
    return f"{email.lower()}::{client_ip}"


def _prune_old_failures(now: float, events: deque[float]) -> None:
    while events and now - events[0] > FAILED_LOGIN_WINDOW_SECONDS:
        events.popleft()


def _ensure_login_not_locked(key: str, now: float) -> None:
    locked_until = _login_locks_until.get(key, 0)
    if locked_until > now:
        wait_seconds = int(locked_until - now)
        raise HTTPException(status_code=429, detail=f"too many failed attempts, retry in {wait_seconds}s")


def _record_login_failure(key: str, now: float) -> None:
    events = _failed_login_events[key]
    _prune_old_failures(now, events)
    events.append(now)
    if len(events) >= FAILED_LOGIN_LIMIT:
        _login_locks_until[key] = now + LOGIN_LOCK_SECONDS


def _clear_login_failures(key: str) -> None:
    _failed_login_events.pop(key, None)
    _login_locks_until.pop(key, None)


@router.post("/login", response_model=ApiResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    now = time()
    client_ip = request.client.host if request.client else "unknown"
    key = _login_throttle_key(payload.email, client_ip)
    _ensure_login_not_locked(key, now)

    user = authenticate(db, payload.email, payload.password)
    if not user:
        _record_login_failure(key, now)
        raise HTTPException(status_code=401, detail="invalid credentials")

    _clear_login_failures(key)
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    return ok(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "role": user["role"],
                "tenant_id": user["tenant_id"],
            },
        }
    )


@router.post("/refresh", response_model=ApiResponse)
def refresh_token(payload: RefreshTokenRequest) -> dict:
    claims = decode_refresh_token(payload.refresh_token)
    user = {
        "id": claims.get("sub"),
        "name": claims.get("name"),
        "role": claims.get("role"),
        "tenant_id": claims.get("tenant_id"),
        "email": claims.get("email"),
    }
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    return ok({"access_token": access_token, "refresh_token": refresh_token})


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
