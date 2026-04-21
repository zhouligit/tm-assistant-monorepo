import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Header, HTTPException

JWT_SECRET = os.getenv("JWT_SECRET", "replace_me")
JWT_ALG = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

DEMO_USER = {
    "id": "u_2002",
    "name": "Admin Demo",
    "role": "tenant_admin",
    "tenant_id": "1001",
    "email": os.getenv("DEMO_ADMIN_EMAIL", "admin@demo.com"),
    "password": os.getenv("DEMO_ADMIN_PASSWORD", "123456"),
}


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    if email == DEMO_USER["email"] and password == DEMO_USER["password"]:
        return {
            "id": DEMO_USER["id"],
            "name": DEMO_USER["name"],
            "role": DEMO_USER["role"],
            "tenant_id": DEMO_USER["tenant_id"],
            "email": DEMO_USER["email"],
        }
    return None


def create_access_token(user: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["id"],
        "tenant_id": user["tenant_id"],
        "role": user["role"],
        "name": user["name"],
        "email": user["email"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_EXPIRE_HOURS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc


def require_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    return decode_access_token(token)
