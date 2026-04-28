import hashlib
import hmac
import os
from collections import deque
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="Connector Service")
VERIFY_WEBHOOK_SIGNATURE = os.getenv("CONNECTOR_VERIFY_SIGNATURE", "false").lower() == "true"
FEISHU_SIGN_SECRET = os.getenv("FEISHU_SIGN_SECRET", "")
WECOM_SIGN_SECRET = os.getenv("WECOM_SIGN_SECRET", "")
MOCK_EVENTS: deque[dict[str, Any]] = deque(maxlen=200)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _verify_signature(provider: str, body: dict[str, Any], signature: str | None) -> None:
    if not VERIFY_WEBHOOK_SIGNATURE:
        return
    if not signature:
        raise HTTPException(status_code=401, detail="missing signature")
    secret = FEISHU_SIGN_SECRET if provider == "feishu" else WECOM_SIGN_SECRET
    if not secret:
        raise HTTPException(status_code=500, detail="missing webhook sign secret")
    digest = hmac.new(secret.encode("utf-8"), str(body).encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, signature):
        raise HTTPException(status_code=401, detail="invalid signature")


def _append_event(provider: str, body: dict[str, Any]) -> dict[str, Any]:
    event = {
        "provider": provider,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "event_type": body.get("event_type") or body.get("type") or "message",
        "payload": body,
    }
    MOCK_EVENTS.appendleft(event)
    return event


@app.post("/webhook/feishu")
def feishu_webhook(payload: dict[str, Any], x_signature: str | None = Header(default=None)) -> dict[str, Any]:
    _verify_signature("feishu", payload, x_signature)
    event = _append_event("feishu", payload)
    return {"status": "ok", "mock": True, "event": event}


@app.post("/webhook/wecom")
def wecom_webhook(payload: dict[str, Any], x_signature: str | None = Header(default=None)) -> dict[str, Any]:
    _verify_signature("wecom", payload, x_signature)
    event = _append_event("wecom", payload)
    return {"status": "ok", "mock": True, "event": event}


@app.get("/webhook/events")
def list_mock_events(limit: int = 20) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 100))
    return {"status": "ok", "total": len(MOCK_EVENTS), "items": list(MOCK_EVENTS)[:safe_limit]}
