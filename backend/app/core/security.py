"""Security utilities and middleware configuration."""

import hmac

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.constants import HEALTH_CHECK_PATHS
from app.core.settings import get_settings


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication."""

    def __init__(self, app, header_name: str = "X-API-Key"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()

        if not settings.api_key:
            return await call_next(request)

        if request.url.path in HEALTH_CHECK_PATHS:
            return await call_next(request)

        api_key = request.headers.get(self.header_name) or ""
        if not hmac.compare_digest(api_key, settings.api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)
