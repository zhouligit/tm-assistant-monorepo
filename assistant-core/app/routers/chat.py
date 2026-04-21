from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.entities import ChatMessage, ChatSession, HandoffTicket
from app.models import ChatMessagePayload, ChatSessionCreatePayload, HandoffPayload
from app.request_context import get_tenant_id, get_user_id
from app.schemas import ApiResponse, ok

router = APIRouter(prefix="/internal/core/chat", tags=["chat"])


@router.post("/sessions", response_model=ApiResponse)
def create_session(
    payload: ChatSessionCreatePayload,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
) -> dict:
    session = ChatSession(
        tenant_id=tenant_id,
        channel=payload.channel,
        visitor_id=payload.visitor_id,
        status="open",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return ok({"session_id": str(session.id), "status": session.status})


@router.post("/sessions/{session_id}/messages", response_model=ApiResponse)
def reply(
    session_id: str,
    payload: ChatMessagePayload,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
) -> dict:
    try:
        sid = int(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid session_id") from exc
    session = db.get(ChatSession, sid)
    if not session or session.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="session not found")

    user_msg = ChatMessage(
        tenant_id=tenant_id,
        session_id=session.id,
        role=payload.role,
        content=payload.content,
    )
    db.add(user_msg)

    # MVP: 固定回复，后续替换为真实RAG与模型调用
    assistant_reply = "已收到你的问题，我们会尽快给出处理建议。"
    assistant_msg = ChatMessage(
        tenant_id=tenant_id,
        session_id=session.id,
        role="assistant",
        content=assistant_reply,
        confidence=0.5,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ok(
        {
            "reply": assistant_reply,
            "confidence": assistant_msg.confidence,
            "citations": [],
            "handoff_suggested": False,
        }
    )


@router.post("/sessions/{session_id}/handoff", response_model=ApiResponse)
def handoff(
    session_id: str,
    payload: HandoffPayload,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user_id: int = Depends(get_user_id),
) -> dict:
    try:
        sid = int(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid session_id") from exc
    session = db.get(ChatSession, sid)
    if not session or session.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="session not found")

    session.status = "handoff"
    ticket = db.execute(
        select(HandoffTicket).where(HandoffTicket.session_id == sid, HandoffTicket.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if ticket is None:
        ticket = HandoffTicket(
            tenant_id=tenant_id,
            session_id=sid,
            status="queued",
            reason=payload.reason,
            assignee_id=user_id,
        )
        db.add(ticket)
        db.flush()
    else:
        ticket.status = "queued"
        ticket.reason = payload.reason
        ticket.assignee_id = None
        ticket.claimed_at = None
        ticket.resolved_at = None

    db.commit()
    return ok({"handoff_id": str(ticket.id), "status": ticket.status})


@router.get("/sessions/{session_id}", response_model=ApiResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
) -> dict:
    try:
        sid = int(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid session_id") from exc
    session = db.get(ChatSession, sid)
    if not session or session.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="session not found")

    messages = db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == sid, ChatMessage.tenant_id == tenant_id)
        .order_by(ChatMessage.id.asc())
    ).scalars()
    message_data = [
        {
            "id": str(msg.id),
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
        for msg in messages
    ]

    return ok(
        {
            "session_id": str(session.id),
            "status": session.status,
            "messages": message_data,
        }
    )
