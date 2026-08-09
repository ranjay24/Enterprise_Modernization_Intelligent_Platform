"""Security utilities and middleware configuration."""

import hmac

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core import local_auth
from app.core.constants import AUTH_PUBLIC_PATHS, HEALTH_CHECK_PATHS
from app.core.dependencies import get_aws_clients
from app.core.settings import Settings, get_settings


def validate_cognito_token(token: str, settings: Settings) -> dict | None:
    """Validate a Cognito access token via cognito-idp GetUser.

    GetUser with an access token is a real, user-scoped validation against the
    configured user pool (rejects expired/invalid tokens). Returns a minimal
    user dict, or None when the token is invalid/expired or Cognito is
    unreachable.
    """
    if not settings.cognito_enabled or not settings.cognito_user_pool_id:
        return None
    try:
        client = get_aws_clients().cognito_idp
        response = client.get_user(AccessToken=token)
    except Exception:
        return None

    attributes = {a.get("Name"): a.get("Value") for a in response.get("UserAttributes", [])}
    username = response.get("Username", "")
    email = attributes.get("email", "")
    name = attributes.get("name") or email or username
    return {
        "username": username,
        "email": email,
        "name": name,
        "attributes": attributes,
    }


def validate_bearer_token(token: str, settings: Settings) -> dict | None:
    """Validate a bearer token against whichever provider is configured.

    Cognito (production) takes precedence; otherwise the built-in local provider
    validates its HMAC-signed tokens. Returns a minimal user dict or None.
    """
    if settings.cognito_enabled and settings.cognito_user_pool_id:
        return validate_cognito_token(token, settings)
    if settings.local_auth_enabled:
        return local_auth.validate_token(settings, token)
    return None


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware for API key and bearer-token authentication.

    Auth is enforced only when at least one mechanism is configured:
    - Cognito (production): ``Authorization: Bearer <access token>`` validated
      against the configured user pool via cognito-idp GetUser.
    - Local provider (dev/self-hosted): ``Authorization: Bearer <token>``
      validated via the HMAC-signed local auth store.
    - API key: ``X-API-Key`` header compared against settings.api_key.

    Health endpoints and the unauthenticated auth endpoints
    (login/signup/confirm/refresh) are always reachable.
    """

    def __init__(self, app, header_name: str = "X-API-Key"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()

        auth_configured = settings.api_key or settings.cognito_enabled or settings.local_auth_enabled
        if not auth_configured:
            return await call_next(request)

        if request.url.path in HEALTH_CHECK_PATHS or request.url.path in AUTH_PUBLIC_PATHS:
            return await call_next(request)

        # 1) Bearer token (Cognito, or the local provider when Cognito is off)
        auth_header = request.headers.get("Authorization") or ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            user = validate_bearer_token(token, settings)
            if user is None:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or expired session"},
                )
            request.state.user = user
            return await call_next(request)

        # 2) API key fallback
        api_key = request.headers.get(self.header_name) or ""
        if settings.api_key and hmac.compare_digest(api_key, settings.api_key):
            return await call_next(request)

        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing credentials"},
        )
