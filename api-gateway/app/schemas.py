from typing import Any
from uuid import uuid4

from pydantic import BaseModel
from contextvars import ContextVar


request_id_ctx: ContextVar[str | None] = ContextVar("gateway_request_id", default=None)


class ApiResponse(BaseModel):
    code: int
    message: str
    request_id: str
    data: Any = None


def ok(data: Any = None, message: str = "ok", request_id: str | None = None) -> dict[str, Any]:
    rid = request_id or request_id_ctx.get() or str(uuid4())
    return {
        "code": 0,
        "message": message,
        "request_id": rid,
        "data": data,
    }


def not_implemented(endpoint: str) -> dict[str, Any]:
    return ok(
        data={"endpoint": endpoint, "status": "not_implemented"},
        message="route scaffold ready",
    )


def fail(
    code: int,
    message: str,
    *,
    data: Any = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    rid = request_id or request_id_ctx.get() or str(uuid4())
    return {
        "code": code,
        "message": message,
        "request_id": rid,
        "data": data,
    }
