from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.entities import ChatSession, HandoffTicket
from app.request_context import get_tenant_id
from app.schemas import ApiResponse, ok

router = APIRouter(prefix="/internal/core/analytics", tags=["analytics"])


def _parse_datetime(date_str: str, field_name: str) -> datetime:
    try:
        return datetime.fromisoformat(date_str)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid {field_name}") from exc


@router.get("/overview", response_model=ApiResponse)
def overview(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
) -> dict:
    session_stmt = select(ChatSession).where(ChatSession.tenant_id == tenant_id)
    handoff_stmt = select(HandoffTicket).where(HandoffTicket.tenant_id == tenant_id)

    if start_date:
        start_dt = _parse_datetime(start_date, "start_date")
        session_stmt = session_stmt.where(ChatSession.created_at >= start_dt)
        handoff_stmt = handoff_stmt.where(HandoffTicket.created_at >= start_dt)
    if end_date:
        end_dt = _parse_datetime(end_date, "end_date")
        session_stmt = session_stmt.where(ChatSession.created_at <= end_dt)
        handoff_stmt = handoff_stmt.where(HandoffTicket.created_at <= end_dt)

    total_sessions = db.execute(
        select(func.count()).select_from(session_stmt.subquery())
    ).scalar_one()
    handoff_sessions = db.execute(
        select(func.count()).select_from(handoff_stmt.subquery())
    ).scalar_one()
    resolved_handoffs = db.execute(
        select(func.count()).select_from(
            handoff_stmt.where(HandoffTicket.status == "resolved").subquery()
        )
    ).scalar_one()

    auto_resolved_sessions = max(total_sessions - handoff_sessions, 0)
    auto_resolved_rate = (auto_resolved_sessions / total_sessions) if total_sessions else 0.0
    handoff_rate = (handoff_sessions / total_sessions) if total_sessions else 0.0

    return ok(
        {
            "total_sessions": total_sessions,
            "auto_resolved_sessions": auto_resolved_sessions,
            "auto_resolved_rate": round(auto_resolved_rate, 4),
            "handoff_sessions": handoff_sessions,
            "handoff_rate": round(handoff_rate, 4),
            "resolved_handoffs": resolved_handoffs,
            "avg_latency_ms": 0,  # MVP: 后续接入真实埋点后计算
        }
    )


@router.get("/unresolved-topics", response_model=ApiResponse)
def unresolved_topics(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
) -> dict:
    stmt = (
        select(HandoffTicket.reason, func.count(HandoffTicket.id).label("count"))
        .where(HandoffTicket.tenant_id == tenant_id)
        .group_by(HandoffTicket.reason)
        .order_by(func.count(HandoffTicket.id).desc())
        .limit(limit)
    )
    if start_date:
        stmt = stmt.where(HandoffTicket.created_at >= _parse_datetime(start_date, "start_date"))
    if end_date:
        stmt = stmt.where(HandoffTicket.created_at <= _parse_datetime(end_date, "end_date"))

    rows = db.execute(stmt).all()
    topics = [{"question": row.reason, "count": row.count} for row in rows]
    return ok({"topics": topics})


@router.get("/export", response_model=ApiResponse)
def export(format_: str | None = Query(default=None, alias="format")) -> dict:
    export_format = format_ or "csv"
    return ok(
        {
            "file_url": f"/api/v1/tm/analytics/export/download?format={export_format}",
            "status": "generated",
        }
    )
