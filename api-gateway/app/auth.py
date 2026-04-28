import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Header, HTTPException
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.entities import User

JWT_SECRET = os.getenv("JWT_SECRET", "replace_me")
JWT_ALG = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
REFRESH_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "14"))
PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _verify_password(plain_password: str, password_hash: str) -> bool:
    # Keep backward compatibility for pre-hash seed data.
    if password_hash.startswith("$2"):
        return PWD_CONTEXT.verify(plain_password, password_hash)
    return plain_password == password_hash


def authenticate(db: Session, email: str, password: str) -> dict[str, Any] | None:
    user = db.execute(select(User).where(User.email == email, User.status == 1)).scalar_one_or_none()
    if not user:
        return None
    if not _verify_password(password, user.password_hash):
        return None
    return {
        "id": str(user.id),
        "name": user.name,
        "role": user.role,
        "tenant_id": str(user.tenant_id),
        "email": user.email,
    }


def _create_token(user: dict[str, Any], expires_at: datetime, token_type: str) -> str:
    payload = {
        "sub": user["id"],
        "tenant_id": user["tenant_id"],
        "role": user["role"],
        "name": user["name"],
        "email": user["email"],
        "type": token_type,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def create_access_token(user: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    return _create_token(user, now + timedelta(hours=JWT_EXPIRE_HOURS), "access")


def create_refresh_token(user: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    return _create_token(user, now + timedelta(days=REFRESH_EXPIRE_DAYS), "refresh")


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="invalid access token")
        return payload
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc


def decode_refresh_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="invalid refresh token")
        return payload
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc


def require_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    return decode_access_token(token)


def optional_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return decode_access_token(token)
