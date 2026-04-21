import os
from typing import Any
from uuid import uuid4
import json

import httpx

from app.schemas import fail, ok, request_id_ctx

ASSISTANT_CORE_BASE_URL = os.getenv("ASSISTANT_CORE_BASE_URL", "http://127.0.0.1:18001")


async def forward(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    url = f"{ASSISTANT_CORE_BASE_URL}{path}"
    current_request_id = request_id_ctx.get() or str(uuid4())
    merged_headers = {"X-Request-Id": current_request_id}
    if headers:
        merged_headers.update(headers)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                headers=merged_headers,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        try:
            payload = exc.response.json()
            if isinstance(payload, dict) and {"code", "message", "request_id", "data"}.issubset(payload.keys()):
                return payload
        except json.JSONDecodeError:
            pass
        return fail(
            code=1001,
            message="core service returned error",
            request_id=current_request_id,
            data={
                "status_code": exc.response.status_code,
                "body": exc.response.text,
                "url": url,
            },
        )
    except httpx.HTTPError as exc:
        return ok(
            {
                "status": "core_unreachable",
                "error": str(exc),
                "url": url,
            },
            message="gateway forward failed",
            request_id=current_request_id,
        )
