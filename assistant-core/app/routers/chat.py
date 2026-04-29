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


def _zh_ngrams(text: str, n: int = 2) -> set[str]:
    chars = [ch for ch in text if "\u4e00" <= ch <= "\u9fff"]
    if len(chars) < n:
        return set(chars)
    return {"".join(chars[i : i + n]) for i in range(len(chars) - n + 1)}


def _tokenize(text: str) -> set[str]:
    normalized = text.lower().strip()
    latin_tokens = {x for x in re.split(r"[^a-z0-9]+", normalized) if x}
    zh_tokens = _zh_ngrams(normalized, 2)
    tokens = latin_tokens | zh_tokens
    if tokens:
        return tokens
    return {normalized} if normalized else set()


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
    def _handoff_feedback_bonus(chunk: KnowledgeChunk) -> float:
        # 人工回流知识只在“问题部分”与用户提问相近时才加权，避免所有问题都命中回流答案。
        if not chunk.metadata_json:
            return 0.0
        if chunk.metadata_json.get("topic") != "handoff_feedback":
            return 0.0
        # chunk_text 格式：问题：...\n答复：...
        m = re.search(r"问题：(.*?)\\n答复：", chunk.chunk_text or "", flags=re.S)
        if not m:
            return 0.0
        q = m.group(1).strip()
        if not q:
            return 0.0
        q_tokens = _tokenize(q)
        overlap = len(query_tokens & q_tokens)
        if overlap <= 0:
            return 0.0
        # 重叠越多，加权越高，但上限较小
        return min(1.0, 0.3 + overlap * 0.4)

    ranked = sorted(
        chunks,
        key=lambda x: _score_chunk(query_tokens, query_text, x.chunk_text) + _handoff_feedback_bonus(x),
        reverse=True,
    )
    top_chunks = ranked[:MAX_CITATIONS]
    top_score = _score_chunk(query_tokens, query_text, top_chunks[0].chunk_text) + _handoff_feedback_bonus(top_chunks[0])
    confidence = min(0.95, 0.25 + top_score * 0.15)
    top_topic = (top_chunks[0].metadata_json or {}).get("topic") if top_chunks else None
    if top_topic == "handoff_feedback":
        # chunk_text 格式：问题：...\n答复：...
        m = re.split(r"答复：", top_chunks[0].chunk_text, maxsplit=1)
        answer_body = m[1].strip() if len(m) == 2 else top_chunks[0].chunk_text
        answer = answer_body
        citations = [
            {"chunk_id": str(chunk.id), "source_id": str(chunk.source_id), "snippet": chunk.chunk_text[:120]}
            for chunk in top_chunks
        ]
        # 置信度不够时仍走兜底策略，避免“乱答”（否则会导致所有问题都落到回流答案）。
        if confidence < AUTO_HANDOFF_THRESHOLD:
            return ("我找到了部分相关信息，但置信度不高，建议人工继续跟进。", round(confidence, 4), citations)
        return (answer, round(confidence, 4), citations)
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


@router.get("/sessions", response_model=ApiResponse)
def list_sessions(
    limit: int = 20,
    status: str | None = None,
    channel: str | None = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
) -> dict:
    safe_limit = max(1, min(limit, 100))
    stmt = (
        select(ChatSession)
        .where(ChatSession.tenant_id == tenant_id)
        .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
    )
    if status:
        stmt = stmt.where(ChatSession.status == status)
    if channel:
        stmt = stmt.where(ChatSession.channel == channel)
    sessions = db.execute(stmt.limit(safe_limit)).scalars().all()
    result: list[dict] = []
    for session in sessions:
        latest_msg = db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id, ChatMessage.tenant_id == tenant_id)
            .order_by(ChatMessage.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        result.append(
            {
                "session_id": str(session.id),
                "status": session.status,
                "channel": session.channel,
                "visitor_id": session.visitor_id,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "last_message_role": latest_msg.role if latest_msg else None,
                "last_message_preview": latest_msg.content[:120] if latest_msg else "",
                "last_message_at": latest_msg.created_at.isoformat() if latest_msg and latest_msg.created_at else None,
            }
        )
    return ok({"list": result, "total": len(result)})


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
