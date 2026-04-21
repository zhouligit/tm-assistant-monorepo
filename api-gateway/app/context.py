from typing import Any


def build_core_headers(claims: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    tenant_id = claims.get("tenant_id")
    user_id = claims.get("sub")
    role = claims.get("role")
    if tenant_id is not None:
        headers["X-Tenant-Id"] = str(tenant_id)
    if user_id is not None:
        headers["X-User-Id"] = str(user_id)
    if role is not None:
        headers["X-User-Role"] = str(role)
    return headers
