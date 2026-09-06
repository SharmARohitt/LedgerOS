import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import (
    auth,
    dashboard,
    decisions,
    demo,
    events,
    exceptions,
    health,
    investigations,
    proofs,
    traces,
    webhooks,
)
from app.core.config import get_settings
from app.core.logging import configure_logging, log_event, new_request_id, request_id_var

configure_logging()
logger = logging.getLogger("ledgeros")
settings = get_settings()

app = FastAPI(
    title="LedgerOS API",
    description="Autonomous Financial Control Plane — event pipeline, investigation agents, policy-bounded decisions, tamper-evident proof.",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", new_request_id())
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        log_event(
            logger,
            "request_completed",
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
        )
        request_id_var.reset(token)
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log_event(logger, "unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id_var.get()})


API_PREFIX = "/api/v1"
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(events.router, prefix=API_PREFIX)
app.include_router(exceptions.router, prefix=API_PREFIX)
app.include_router(investigations.router, prefix=API_PREFIX)
app.include_router(decisions.router, prefix=API_PREFIX)
app.include_router(traces.router, prefix=API_PREFIX)
app.include_router(proofs.router, prefix=API_PREFIX)
app.include_router(webhooks.router, prefix=API_PREFIX)
app.include_router(demo.router, prefix=API_PREFIX)
