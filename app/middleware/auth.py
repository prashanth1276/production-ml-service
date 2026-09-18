"""Optional API-key authentication middleware.

Disabled by default (API_KEY_ENABLED=false). When enabled, all /api/*
endpoints require an X-API-Key header matching the API_KEY env var.

Public endpoints (/health, /ready, /metrics, /docs) never require auth.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.config import get_settings

PUBLIC_PATHS = {
    "/",
    "/health",
    "/ready",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()

        if not settings.api_key_enabled:
            return await call_next(request)

        path = request.url.path

        if path in PUBLIC_PATHS:
            return await call_next(request)
        if path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")

        if not provided or provided != settings.api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Invalid or missing API key",
                    "hint": "Provide a valid X-API-Key header",
                },
            )

        return await call_next(request)