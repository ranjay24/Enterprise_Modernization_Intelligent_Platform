import os

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

API_KEY = os.getenv("EMIP_API_KEY", "")


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not API_KEY:
            return await call_next(request)

        if request.url.path in ("/health", "/api/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        key = request.headers.get("X-API-Key", "")
        if key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

        return await call_next(request)
