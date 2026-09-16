"""FastAPI application entrypoint."""

import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.routes import chat, describe, recommend
from app.utils.cache import cache_ping, get_redis
from app.utils.config import get_settings
from app.utils.db import db
from app.utils.logging_config import configure_logging
from app.utils.metrics import (
    ACTIVE_REQUESTS,
    REQUEST_COUNT,
    REQUEST_LATENCY,
)

settings = get_settings()

# Use JSON logs by default; human-readable in dev
import os

configure_logging(
    level=settings.log_level,
    json_output=os.getenv("LOG_JSON", "true").lower() == "true",
)

import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="AI-powered retail backend.",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def instrument_request(request: Request, call_next):
    """Track request ID, latency, and Prometheus metrics."""
    # Skip Prometheus endpoint from its own metrics
    path = request.url.path
    if path == "/metrics":
        return await call_next(request)

    request_id = str(uuid.uuid4())[:8]
    start = time.perf_counter()
    ACTIVE_REQUESTS.inc()

    try:
        response = await call_next(request)
    except Exception:
        ACTIVE_REQUESTS.dec()
        REQUEST_COUNT.labels(method=request.method, endpoint=path, status="500").inc()
        raise

    ACTIVE_REQUESTS.dec()
    elapsed = time.perf_counter() - start
    elapsed_ms = elapsed * 1000

    REQUEST_COUNT.labels(
        method=request.method, endpoint=path, status=str(response.status_code)
    ).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=path).observe(elapsed)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.2f}"

    logger.info(
        f"{request.method} {path} {response.status_code}",
        extra={
            "req_id": request_id,
            "method": request.method,
            "path": path,
            "status": response.status_code,
            "latency_ms": round(elapsed_ms, 2),
        },
    )
    return response


@app.on_event("startup")
async def startup():
    if settings.rate_limit_enabled:
        try:
            await FastAPILimiter.init(get_redis())
            logger.info("Rate limiter initialized")
        except Exception as e:
            logger.error(f"Rate limiter init failed: {e}")
    else:
        logger.info("Rate limiter disabled")


@app.get("/", summary="Welcome endpoint")
def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "llm_backend": settings.llm_backend,
    }


@app.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok"}


@app.get("/ready", summary="Readiness probe")
async def ready():
    checks = {
        "mongodb": db.ping(),
        "redis": await cache_ping(),
    }
    status = "ok" if all(checks.values()) else "degraded"
    return {"status": status, "checks": checks}


@app.get("/metrics", summary="Prometheus metrics")
def metrics():
    """Expose Prometheus metrics in text format."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---- Routes ----
if settings.rate_limit_enabled:
    rl = [
        Depends(
            RateLimiter(
                times=settings.rate_limit_times,
                seconds=settings.rate_limit_seconds,
            )
        )
    ]
else:
    rl = []

app.include_router(recommend.router, prefix="/api", dependencies=rl)
app.include_router(chat.router, prefix="/api", dependencies=rl)
app.include_router(describe.router, prefix="/api", dependencies=rl)
