import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.routers import (
    analytics_router,
    chat_router,
    handoff_router,
    health_router,
    knowledge_router,
)
from app.schemas import fail, request_id_ctx

app = FastAPI(title="Assistant Core")
logger = logging.getLogger("assistant-core")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning("request.error id=%s status=%s detail=%s", request_id_ctx.get(), exc.status_code, exc.detail)
    body = fail(
        code=exc.status_code,
        message=str(exc.detail),
        data={"path": request.url.path},
    )
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("request.unhandled id=%s path=%s", request_id_ctx.get(), request.url.path)
    body = fail(
        code=5000,
        message="internal server error",
        data={"path": request.url.path, "error": str(exc)},
    )
    return JSONResponse(status_code=500, content=body)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or str(uuid4())
    token = request_id_ctx.set(request_id)
    logger.info("request.start id=%s method=%s path=%s", request_id, request.method, request.url.path)
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    response.headers["X-Request-Id"] = request_id
    logger.info("request.end id=%s status=%s", request_id, response.status_code)
    return response

app.include_router(health_router)
app.include_router(knowledge_router)
app.include_router(chat_router)
app.include_router(handoff_router)
app.include_router(analytics_router)
