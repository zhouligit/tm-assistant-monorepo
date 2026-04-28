import logging
import os
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import (
    analytics_router,
    auth_router,
    billing_router,
    chat_router,
    handoff_router,
    health_router,
    kb_candidates_router,
    knowledge_router,
    retrieval_router,
)
from app.schemas import fail, request_id_ctx

app = FastAPI(title="API Gateway")
logger = logging.getLogger("api-gateway")

_cors_origins_raw = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
)
_cors_allow_origins = [x.strip() for x in _cors_origins_raw.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
app.include_router(auth_router)
app.include_router(knowledge_router)
app.include_router(retrieval_router)
app.include_router(chat_router)
app.include_router(handoff_router)
app.include_router(kb_candidates_router)
app.include_router(analytics_router)
app.include_router(billing_router)
