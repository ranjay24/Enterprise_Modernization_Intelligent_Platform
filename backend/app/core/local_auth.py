"""Built-in local authentication provider (dev/self-hosted fallback).

When Cognito is not configured, EMIP still provides a fully working auth
experience so login/signup are real, not a 503 wall: users are persisted to a
local JSON store, passwords are hashed with PBKDF2-HMAC-SHA256, and sessions use
HMAC-SHA256 signed tokens that the ``APIKeyMiddleware`` validates on every
request. Production deployments should keep ``local_auth_enabled=false`` and use
the Cognito path instead.

This module intentionally depends only on the Python standard library so it runs
anywhere (uvicorn locally, Lambda in AWS).
"""

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from pathlib import Path

from app.core.settings import Settings

_PBKDF2_ITERATIONS = 120_000
_ACCESS_TYPE = "access"
_REFRESH_TYPE = "refresh"
_REFRESH_TTL = 7 * 24 * 3600
_VERIFY_TTL = 30 * 60

_LOCK = threading.Lock()


class LocalAuthError(Exception):
    """Raised with an HTTP status code + detail for the auth routes."""

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _store_path(settings: Settings) -> Path:
    return Path(settings.local_auth_data_dir) / "users.json"


def _load_users(settings: Settings) -> dict:
    path = _store_path(settings)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_users(settings: Settings, users: dict) -> None:
    path = _store_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(users, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2${_PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_b64, digest_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(actual, expected)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    data += "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data)


def _sign_token(settings: Settings, header_payload: str) -> str:
    return hmac.new(
        settings.local_auth_secret.encode("utf-8"),
        header_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _issue_token(settings: Settings, user: dict, token_type: str) -> str:
    now = int(time.time())
    ttl = settings.local_auth_token_ttl if token_type == _ACCESS_TYPE else _REFRESH_TTL
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(
        json.dumps(
            {
                "sub": user["username"],
                "email": user["email"],
                "name": user["name"],
                "type": token_type,
                "iat": now,
                "exp": now + ttl,
            }
        ).encode()
    )
    signing_input = f"{header}.{payload}"
    return f"{signing_input}.{_sign_token(settings, signing_input)}"


def issue_tokens(settings: Settings, user: dict) -> dict:
    """Issue a matching access/id/refresh token triple (same response shape as Cognito)."""
    access = _issue_token(settings, user, _ACCESS_TYPE)
    return {
        "access_token": access,
        "id_token": access,
        "refresh_token": _issue_token(settings, user, _REFRESH_TYPE),
        "expires_in": settings.local_auth_token_ttl,
    }


def validate_token(settings: Settings, token: str, token_type: str = _ACCESS_TYPE) -> dict | None:
    """Validate an HMAC-signed local token; return its user claims or None."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    signing_input, signature = f"{parts[0]}.{parts[1]}", parts[2]
    expected = _sign_token(settings, signing_input)
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        claims = json.loads(_b64url_decode(parts[1]))
    except (ValueError, json.JSONDecodeError):
        return None
    if claims.get("type") != token_type:
        return None
    if int(claims.get("exp", 0)) < int(time.time()):
        return None
    return {
        "username": claims.get("sub", ""),
        "email": claims.get("email", ""),
        "name": claims.get("name", ""),
    }


def _find_user(users: dict, identifier: str) -> tuple[str | None, dict | None]:
    """Resolve a login identifier to a user — by username or by email.

    The login form asks for an email, but the account is keyed by username, so
    we accept either. Identifiers are normalized (trim + lowercase).
    """
    identifier = identifier.strip().lower()
    if identifier in users:
        return identifier, users[identifier]
    for username, user in users.items():
        if str(user.get("email", "")).strip().lower() == identifier:
            return username, user
    return None, None


def create_user(settings: Settings, username: str, email: str, password: str) -> dict:
    """Create an unconfirmed user and return it with its verification code."""
    if len(password) < 8:
        raise LocalAuthError("Password must be at least 8 characters", 400)
    username = username.strip().lower()
    email = email.strip().lower()
    if not username or not email:
        raise LocalAuthError("Username and email are required", 400)

    with _LOCK:
        users = _load_users(settings)
        existing = users.get(username)
        if existing:
            raise LocalAuthError("Username already exists", 409)
        for user in users.values():
            if str(user.get("email", "")).strip().lower() == email:
                raise LocalAuthError("An account with this email already exists", 409)
        code = f"{secrets.randbelow(1_000_000):06d}"
        users[username] = {
            "username": username,
            "email": email,
            "name": username,
            "password_hash": _hash_password(password),
            "confirmed": False,
            "verification_code": code,
            "verification_expires": int(time.time()) + _VERIFY_TTL,
            "created_at": int(time.time()),
        }
        _save_users(settings, users)
    return {"username": username, "email": email, "name": username, "verification_code": code}


def confirm_user(settings: Settings, username: str, code: str) -> dict:
    identifier = username.strip().lower()
    with _LOCK:
        users = _load_users(settings)
        key, user = _find_user(users, identifier)
        if user is None:
            raise LocalAuthError("User not found", 404)
        if user.get("confirmed"):
            raise LocalAuthError("User is already confirmed", 400)
        if code.strip() != user.get("verification_code", ""):
            raise LocalAuthError("Invalid verification code", 400)
        if int(user.get("verification_expires", 0)) < int(time.time()):
            raise LocalAuthError("Verification code expired", 400)
        user["confirmed"] = True
        user["verification_code"] = ""
        _save_users(settings, users)
    return {"username": user["username"], "email": user["email"], "name": user["name"]}


def authenticate(settings: Settings, username: str, password: str) -> dict:
    """Verify credentials; return the confirmed user or raise LocalAuthError."""
    with _LOCK:
        users = _load_users(settings)
        _, user = _find_user(users, username)
    if user is None:
        raise LocalAuthError("Invalid username or password", 401)
    if not _verify_password(password, user.get("password_hash", "")):
        raise LocalAuthError("Invalid username or password", 401)
    if not user.get("confirmed"):
        raise LocalAuthError("User is not confirmed yet", 403)
    return {"username": user["username"], "email": user["email"], "name": user["name"]}


def refresh_session(settings: Settings, refresh_token: str) -> tuple[dict, dict]:
    user = validate_token(settings, refresh_token, _REFRESH_TYPE)
    if user is None:
        raise LocalAuthError("Invalid or expired refresh token", 401)
    return issue_tokens(settings, user), user
