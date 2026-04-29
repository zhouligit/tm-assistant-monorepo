import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.entities import KnowledgeChunk, KnowledgeSource
from app.models import (
    KnowledgeSourceCreatePayload,
    KnowledgeSourcePatchPayload,
    RetrievalDebugPayload,
)
from app.request_context import get_tenant_id, get_user_id
from app.schemas import ApiResponse, ok

router = APIRouter(prefix="/internal/core/knowledge", tags=["knowledge"])


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


def _score(query_tokens: set[str], query: str, text: str) -> float:
    if not text:
        return 0.0
    tokens = _tokenize(text)
    overlap = len(query_tokens & tokens)
    contains_bonus = 1.5 if query and query in text else 0.0
    return overlap + contains_bonus


def _parse_source_id(source_id: str) -> int:
    try:
        return int(source_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid source_id") from exc


@router.post("/sources", response_model=ApiResponse)
def create_source(
    payload: KnowledgeSourceCreatePayload,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user_id: int = Depends(get_user_id),
) -> dict:
    source = KnowledgeSource(
        tenant_id=tenant_id,
        type=payload.type,
        name=payload.name,
        config_json=payload.config,
        status="pending",
        created_by=user_id,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return ok(
        {
            "id": str(source.id),
            "name": source.name,
            "type": source.type,
            "status": source.status,
            "last_synced_at": source.last_synced_at.isoformat() if source.last_synced_at else None,
        }
    )


@router.get("/sources", response_model=ApiResponse)
def list_sources(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
) -> dict:
    rows = db.execute(
        select(KnowledgeSource).where(KnowledgeSource.tenant_id == tenant_id).order_by(KnowledgeSource.id.desc())
    ).scalars()
    data = [
        {
            "id": str(row.id),
            "name": row.name,
            "type": row.type,
            "status": row.status,
            "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None,
        }
        for row in rows
    ]
    return ok({"list": data, "total": len(data)})


@router.get("/sources/{source_id}", response_model=ApiResponse)
def get_source(
    source_id: str, db: Session = Depends(get_db), tenant_id: int = Depends(get_tenant_id)
) -> dict:
    row = db.get(KnowledgeSource, _parse_source_id(source_id))
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="knowledge source not found")
    return ok(
        {
            "id": str(row.id),
            "name": row.name,
            "type": row.type,
            "status": row.status,
            "config": row.config_json,
            "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None,
            "last_error": row.last_error,
        }
    )


@router.post("/sources/{source_id}/sync", response_model=ApiResponse)
def sync_source(
    source_id: str, db: Session = Depends(get_db), tenant_id: int = Depends(get_tenant_id)
) -> dict:
    row = db.get(KnowledgeSource, _parse_source_id(source_id))
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="knowledge source not found")
    row.status = "ready"
    row.last_synced_at = datetime.utcnow()
    row.last_error = None
    db.commit()
    return ok({"id": str(row.id), "status": row.status})


@router.patch("/sources/{source_id}", response_model=ApiResponse)
def patch_source(
    source_id: str,
    payload: KnowledgeSourcePatchPayload,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
) -> dict:
    row = db.get(KnowledgeSource, _parse_source_id(source_id))
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="knowledge source not found")
    if payload.name is not None:
        row.name = payload.name
    if payload.tags is not None:
        row.config_json = {**(row.config_json or {}), "tags": payload.tags}
    if payload.status is not None:
        row.status = payload.status
    db.commit()
    db.refresh(row)
    return ok({"id": str(row.id), "updated": True, "status": row.status})


@router.delete("/sources/{source_id}", response_model=ApiResponse)
def delete_source(
    source_id: str, db: Session = Depends(get_db), tenant_id: int = Depends(get_tenant_id)
) -> dict:
    row = db.get(KnowledgeSource, _parse_source_id(source_id))
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="knowledge source not found")
    db.delete(row)
    db.commit()
    return ok({"id": source_id, "deleted": True})


@router.get("/chunks", response_model=ApiResponse)
def list_chunks(
    source_id: str | None = None,
    keyword: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
) -> dict:
    safe_limit = max(1, min(limit, 100))
    stmt = select(KnowledgeChunk).where(KnowledgeChunk.tenant_id == tenant_id).order_by(KnowledgeChunk.id.desc())
    if source_id:
        stmt = stmt.where(KnowledgeChunk.source_id == _parse_source_id(source_id))
    rows = db.execute(stmt).scalars().all()
    if keyword:
        rows = [x for x in rows if keyword.lower() in x.chunk_text.lower()]
    rows = rows[:safe_limit]
    data = [
        {
            "id": str(x.id),
            "source_id": str(x.source_id),
            "chunk_text": x.chunk_text,
            "metadata": x.metadata_json,
            "embedding_ref": x.embedding_ref,
        }
        for x in rows
    ]
    return ok({"list": data, "total": len(data)})


@router.post("/retrieval/debug", response_model=ApiResponse)
def retrieval_debug(
    payload: RetrievalDebugPayload,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
) -> dict:
    safe_top_k = max(1, min(payload.top_k, 20))
    rows = db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.tenant_id == tenant_id).order_by(KnowledgeChunk.id.desc())
    ).scalars().all()
    query_tokens = _tokenize(payload.query)
    ranked = sorted(rows, key=lambda x: _score(query_tokens, payload.query, x.chunk_text), reverse=True)
    top = ranked[:safe_top_k]
    candidates = [
        {
            "chunk_id": str(x.id),
            "source_id": str(x.source_id),
            "score": round(_score(query_tokens, payload.query, x.chunk_text), 4),
            "snippet": x.chunk_text[:160],
            "metadata": x.metadata_json,
        }
        for x in top
    ]
    context = "\n".join([x.chunk_text for x in top])
    return ok(
        {
            "query": payload.query,
            "top_k": safe_top_k,
            "candidates": candidates,
            "selected_context": context[:1000],
        }
    )
