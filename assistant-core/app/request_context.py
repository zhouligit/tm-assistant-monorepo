from fastapi import Header, HTTPException


def get_tenant_id(x_tenant_id: str | None = Header(default=None)) -> int:
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="missing X-Tenant-Id")
    try:
        return int(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid X-Tenant-Id") from exc


def get_user_id(x_user_id: str | None = Header(default=None)) -> int:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="missing X-User-Id")
    value = x_user_id.removeprefix("u_")
    try:
        return int(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid X-User-Id") from exc
