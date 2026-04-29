"""
Log warnings when obvious dev-default secrets are still in use (production hygiene).
"""

from __future__ import annotations

import logging
import os
import re
from urllib.parse import unquote

logger = logging.getLogger("api-gateway")

# Documented dev defaults; extend via TM_WEAK_SECRET_MARKERS (comma-separated).
_DEFAULT_MARKERS = ("123456", "replace_me", "password")


def _markers() -> frozenset[str]:
    raw = os.getenv("TM_WEAK_SECRET_MARKERS", "")
    extra = {x.strip().lower() for x in raw.split(",") if x.strip()}
    base = {m.lower() for m in _DEFAULT_MARKERS}
    return frozenset(base | extra)


def _extract_mysql_password(dsn: str) -> str | None:
    if not dsn.strip():
        return None
    m = re.match(r"mysql\+pymysql://([^:]+):([^@]+)@", dsn)
    if not m:
        return None
    return unquote(m.group(2))


def log_weak_configuration_warnings() -> None:
    if os.getenv("TM_SKIP_WEAK_CONFIG_CHECK", "").lower() in ("1", "true", "yes"):
        return
    markers = _markers()
    issues: list[str] = []

    dsn = os.getenv("MYSQL_DSN", "")
    mp = _extract_mysql_password(dsn)
    if mp is not None and mp.lower() in markers:
        issues.append("MYSQL_DSN uses a known weak password")

    redis_url = os.getenv("REDIS_URL", "")
    if ":123456@" in redis_url:
        issues.append("REDIS_URL appears to use default redis password (123456)")

    jwt = os.getenv("JWT_SECRET", "")
    if not jwt or jwt.strip().lower() in markers or len(jwt) < 16:
        issues.append("JWT_SECRET is missing, too short, or still a placeholder")

    if not issues:
        return

    msg = (
        "SECURITY/OPS: production hygiene checks failed — "
        + "; ".join(issues)
        + ". Rotate credentials and update /opt/tm-assistant-monorepo/.env before go-live."
    )
    logger.warning(msg)
