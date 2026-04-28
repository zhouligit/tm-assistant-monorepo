import os
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.entities import ChatMessage, ChatSession, HandoffTicket, KnowledgeChunk
from app.models import ChatMessagePayload, ChatSessionCreatePayload, HandoffPayload
from app.request_context import get_tenant_id, get_user_id
from app.schemas import ApiResponse, ok

router = APIRouter(prefix="/internal/core/chat", tags=["chat"])
AUTO_HANDOFF_THRESHOLD = float(os.getenv("AUTO_HANDOFF_THRESHOLD", "0.45"))
MAX_CITATIONS = int(os.getenv("MAX_CITATIONS", "3"))


def _tokenize(text: str) -> set[str]:
    parts = [x for x in re.split(r"\W+", text.lower()) if x]
    if parts:
        return set(parts)
    return set(text.strip())


def _score_chunk(query_tokens: set[str], query_text: str, chunk_text: str) -> float:
    if not chunk_text:
        return 0.0
    chunk_tokens = _tokenize(chunk_text)
    overlap = len(query_tokens & chunk_tokens)
    substring_bonus = 1.5 if query_text and query_text in chunk_text else 0.0
    return overlap + substring_bonus


def _build_answer_from_chunks(query_text: str, chunks: list[KnowledgeChunk]) -> tuple[str, float, list[dict]]:
    if not chunks:
        return ("暂时没有检索到匹配知识，建议转人工继续跟进。", 0.2, [])
    query_tokens = _tokenize(query_text)
    ranked = sorted(chunks, key=lambda x: _score_chunk(query_tokens, query_text, x.chunk_text), reverse=True)
    top_chunks = ranked[:MAX_CITATIONS]
    top_score = _score_chunk(query_tokens, query_text, top_chunks[0].chunk_text)
    confidence = min(0.95, 0.25 + top_score * 0.15)
    citations = [
        {"chunk_id": str(chunk.id), "source_id": str(chunk.source_id), "snippet": chunk.chunk_text[:120]}
        for chunk in top_chunks
    ]
    if confidence < AUTO_HANDOFF_THRESHOLD:
        answer = "我找到了部分相关信息，但置信度不高，建议人工继续跟进。"
    else:
        answer = f"根据知识库信息：{top_chunks[0].chunk_text}"
    return (answer, round(confidence, 4), citations)


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

    chunk_rows = db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.tenant_id == tenant_id).order_by(KnowledgeChunk.id.desc())
    ).scalars().all()
    assistant_reply, confidence, citations = _build_answer_from_chunks(payload.content, chunk_rows)

    handoff_suggested = confidence < AUTO_HANDOFF_THRESHOLD
    if handoff_suggested:
        session.status = "handoff"
        ticket = db.execute(
            select(HandoffTicket).where(HandoffTicket.session_id == sid, HandoffTicket.tenant_id == tenant_id)
        ).scalar_one_or_none()
        if ticket is None:
            ticket = HandoffTicket(
                tenant_id=tenant_id,
                session_id=sid,
                status="queued",
                reason="low_confidence",
                assignee_id=None,
            )
            db.add(ticket)
        else:
            ticket.status = "queued"
            ticket.reason = "low_confidence"
            ticket.assignee_id = None
            ticket.claimed_at = None
            ticket.resolved_at = None

    assistant_msg = ChatMessage(
        tenant_id=tenant_id,
        session_id=session.id,
        role="assistant",
        content=assistant_reply,
        confidence=confidence,
        citations_json={"citations": citations},
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ok(
        {
            "reply": assistant_reply,
            "confidence": assistant_msg.confidence,
            "citations": citations,
            "handoff_suggested": handoff_suggested,
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
