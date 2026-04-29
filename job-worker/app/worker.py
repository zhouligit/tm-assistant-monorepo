import json
import os
import time
from datetime import datetime
from typing import Any

import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
MYSQL_DSN = os.getenv("MYSQL_DSN", "mysql+pymysql://tm_app:123456@127.0.0.1:3306/tm_assistant")
JOB_QUEUE_NAME = os.getenv("JOB_QUEUE_NAME", "tm:jobs")
DEAD_LETTER_QUEUE_NAME = os.getenv("JOB_DLQ_NAME", "tm:jobs:dlq")
JOB_POLL_TIMEOUT_SECONDS = int(os.getenv("JOB_POLL_TIMEOUT_SECONDS", "5"))
MAX_RETRIES = int(os.getenv("JOB_MAX_RETRIES", "3"))

engine = create_engine(MYSQL_DSN, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def _set_source_status(db: Session, source_id: int, status: str, error: str | None = None) -> None:
    db.execute(
        text(
            """
            UPDATE knowledge_sources
            SET status = :status,
                last_error = :last_error,
                last_synced_at = :last_synced_at
            WHERE id = :source_id
            """
        ),
        {
            "status": status,
            "last_error": error,
            "last_synced_at": datetime.utcnow() if status == "ready" else None,
            "source_id": source_id,
        },
    )
    db.commit()


def _process_job(db: Session, job: dict[str, Any]) -> None:
    job_type = job.get("type")
    payload = job.get("payload") or {}
    if job_type == "knowledge_sync":
        source_id = int(payload["source_id"])
        _set_source_status(db, source_id, "syncing", None)
        # Placeholder for real chunking/vectorization workflow.
        time.sleep(0.2)
        _set_source_status(db, source_id, "ready", None)
        return
    if job_type == "metrics_aggregate":
        # Keep a minimal executable path.
        return
    raise ValueError(f"unsupported job type: {job_type}")


def _handle_failed_job(rdb: redis.Redis, raw_job: str, job: dict[str, Any], err: Exception) -> None:
    retry_count = int(job.get("retry_count", 0)) + 1
    job["retry_count"] = retry_count
    job["last_error"] = str(err)
    if retry_count >= MAX_RETRIES:
        rdb.lpush(DEAD_LETTER_QUEUE_NAME, json.dumps(job, ensure_ascii=False))
    else:
        rdb.lpush(JOB_QUEUE_NAME, json.dumps(job, ensure_ascii=False))


def main() -> None:
    print(f"job-worker started, queue={JOB_QUEUE_NAME}")
    rdb = redis.from_url(REDIS_URL, decode_responses=True)
    while True:
        item = rdb.brpop(JOB_QUEUE_NAME, timeout=JOB_POLL_TIMEOUT_SECONDS)
        if not item:
            continue
        _, raw_job = item
        try:
            job = json.loads(raw_job)
            with SessionLocal() as db:
                _process_job(db, job)
        except Exception as exc:  # noqa: BLE001
            try:
                parsed = json.loads(raw_job)
            except Exception:  # noqa: BLE001
                parsed = {"raw": raw_job}
            _handle_failed_job(rdb, raw_job, parsed, exc)


if __name__ == "__main__":
    main()
