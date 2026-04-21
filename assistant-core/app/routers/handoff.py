from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.entities import HandoffReply, HandoffTicket, KbCandidate
from app.models import CandidateRejectPayload, HandoffReplyPayload
from app.request_context import get_tenant_id, get_user_id
from app.schemas import ApiResponse, ok

router = APIRouter(prefix="/internal/core/handoff", tags=["handoff"])


@router.get("/queue", response_model=ApiResponse)
def queue(
    status: str | None = None,
    assignee_id: str | None = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
) -> dict:
    stmt = select(HandoffTicket).where(HandoffTicket.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(HandoffTicket.status == status)
    if assignee_id:
        try:
            assignee = int(assignee_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid assignee_id") from exc
        stmt = stmt.where(HandoffTicket.assignee_id == assignee)
    rows = db.execute(stmt.order_by(HandoffTicket.id.desc())).scalars().all()
    data = [
        {
            "id": str(row.id),
            "session_id": str(row.session_id),
            "status": row.status,
            "reason": row.reason,
            "assignee_id": str(row.assignee_id) if row.assignee_id else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
    return ok({"list": data, "total": len(data)})


@router.post("/queue/{handoff_id}/reply", response_model=ApiResponse)
def reply(
    handoff_id: str,
    payload: HandoffReplyPayload,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user_id: int = Depends(get_user_id),
) -> dict:
    try:
        ticket_id = int(handoff_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid handoff_id") from exc
    ticket = db.get(HandoffTicket, ticket_id)
    if not ticket or ticket.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="handoff not found")

    reply_row = HandoffReply(
        tenant_id=tenant_id,
        ticket_id=ticket.id,
        agent_id=ticket.assignee_id or user_id,
        content=payload.content,
        marked_as_kb_candidate=payload.mark_as_kb_candidate,
    )
    db.add(reply_row)
    db.flush()

    candidate_id = None
    if payload.mark_as_kb_candidate:
        candidate = KbCandidate(
            tenant_id=tenant_id,
            source_reply_id=reply_row.id,
            question=f"handoff:{ticket.id}",
            answer=payload.content,
            status="pending",
        )
        db.add(candidate)
        db.flush()
        candidate_id = candidate.id

    db.commit()
    return ok({"reply_id": str(reply_row.id), "saved": True, "candidate_id": str(candidate_id) if candidate_id else None})


@router.post("/queue/{handoff_id}/claim", response_model=ApiResponse)
def claim(
    handoff_id: str,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user_id: int = Depends(get_user_id),
) -> dict:
    try:
        ticket_id = int(handoff_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid handoff_id") from exc
    ticket = db.get(HandoffTicket, ticket_id)
    if not ticket or ticket.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="handoff not found")
    ticket.status = "claimed"
    ticket.assignee_id = ticket.assignee_id or user_id
    ticket.claimed_at = datetime.utcnow()
    db.commit()
    return ok({"id": str(ticket.id), "status": ticket.status})


@router.post("/queue/{handoff_id}/close", response_model=ApiResponse)
def close(
    handoff_id: str, db: Session = Depends(get_db), tenant_id: int = Depends(get_tenant_id)
) -> dict:
    try:
        ticket_id = int(handoff_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid handoff_id") from exc
    ticket = db.get(HandoffTicket, ticket_id)
    if not ticket or ticket.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="handoff not found")
    ticket.status = "resolved"
    ticket.resolved_at = datetime.utcnow()
    db.commit()
    return ok({"id": str(ticket.id), "status": ticket.status})


@router.get("/candidates", response_model=ApiResponse)
def list_candidates(
    status: str | None = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
) -> dict:
    stmt = select(KbCandidate).where(KbCandidate.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(KbCandidate.status == status)
    rows = db.execute(stmt.order_by(KbCandidate.id.desc())).scalars().all()
    data = [
        {
            "id": str(row.id),
            "question": row.question,
            "answer": row.answer,
            "status": row.status,
        }
        for row in rows
    ]
    return ok({"list": data, "total": len(data)})


@router.post("/candidates/{candidate_id}/approve", response_model=ApiResponse)
def approve(
    candidate_id: str,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user_id: int = Depends(get_user_id),
) -> dict:
    try:
        cid = int(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid candidate_id") from exc
    row = db.get(KbCandidate, cid)
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="candidate not found")
    row.status = "approved"
    row.reviewed_by = user_id
    row.reviewed_at = datetime.utcnow()
    db.commit()
    return ok({"id": str(row.id), "status": row.status})


@router.post("/candidates/{candidate_id}/reject", response_model=ApiResponse)
def reject(
    candidate_id: str,
    payload: CandidateRejectPayload,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user_id: int = Depends(get_user_id),
) -> dict:
    try:
        cid = int(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid candidate_id") from exc
    row = db.get(KbCandidate, cid)
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="candidate not found")
    row.status = "rejected"
    row.reviewed_by = user_id
    row.reviewed_at = datetime.utcnow()
    db.commit()
    return ok({"id": str(row.id), "status": row.status, "reason": payload.reason})
