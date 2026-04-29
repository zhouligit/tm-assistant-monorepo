import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.models import QuotaCheckRequest
from app.schemas import ApiResponse
from app.schemas import ok

router = APIRouter(
    prefix="/api/v1/tm/billing",
    tags=["billing"],
    dependencies=[Depends(require_current_user)],
)
DEFAULT_PLAN = os.getenv("BILLING_DEFAULT_PLAN", "starter")
DEFAULT_DAILY_MESSAGE_QUOTA = int(os.getenv("BILLING_DAILY_MESSAGE_QUOTA", "500"))


@router.get("/plan", response_model=ApiResponse)
def plan(claims: dict = Depends(require_current_user)) -> dict:
    return ok(
        {
            "tenant_id": claims.get("tenant_id"),
            "plan_code": DEFAULT_PLAN,
            "limits": {
                "daily_messages": DEFAULT_DAILY_MESSAGE_QUOTA,
            },
        }
    )


@router.get("/usage", response_model=ApiResponse)
def usage(db: Session = Depends(get_db), claims: dict = Depends(require_current_user)) -> dict:
    tenant_id = int(claims.get("tenant_id"))
    today = datetime.utcnow().date()
    row = db.execute(
        text(
            """
            SELECT total_sessions, total_tokens
            FROM daily_metrics
            WHERE tenant_id = :tenant_id AND `date` = :date
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "date": today},
    ).mappings().first()
    total_sessions = int(row["total_sessions"]) if row and row["total_sessions"] is not None else 0
    total_tokens = int(row["total_tokens"]) if row and row["total_tokens"] is not None else 0
    return ok(
        {
            "tenant_id": str(tenant_id),
            "date": str(today),
            "messages_used": total_sessions,
            "token_used": total_tokens,
            "daily_messages_quota": DEFAULT_DAILY_MESSAGE_QUOTA,
        }
    )


@router.post("/quota/check", response_model=ApiResponse)
def quota_check(
    payload: QuotaCheckRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_current_user),
) -> dict:
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")
    tenant_id = int(claims.get("tenant_id"))
    today = datetime.utcnow().date()
    row = db.execute(
        text(
            """
            SELECT total_sessions
            FROM daily_metrics
            WHERE tenant_id = :tenant_id AND `date` = :date
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "date": today},
    ).mappings().first()
    used = int(row["total_sessions"]) if row and row["total_sessions"] is not None else 0
    allowed = used + payload.amount <= DEFAULT_DAILY_MESSAGE_QUOTA
    return ok(
        {
            "tenant_id": str(tenant_id),
            "action": payload.action,
            "amount": payload.amount,
            "used": used,
            "quota": DEFAULT_DAILY_MESSAGE_QUOTA,
            "allowed": allowed,
            "reason": None if allowed else "daily quota exceeded",
        }
    )
