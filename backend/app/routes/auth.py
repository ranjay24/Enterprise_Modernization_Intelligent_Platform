"""Authentication routes (login, signup, confirm, refresh, me).

Two providers share the same API contract (same request/response models):

- **Cognito** (production): proxies the Cognito user pool auth APIs so the
  frontend never handles Cognito SDK/CORS concerns.
- **Local** (dev/self-hosted, when ``local_auth_enabled=true`` and Cognito is not
  configured): real signup/login backed by ``app.core.local_auth`` with
  persisted users, PBKDF2 password hashing and HMAC-signed tokens.

Token validation on protected routes happens in the FastAPI middleware
(``app.core.security``).
"""

import base64
import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core import local_auth
from app.core.dependencies import get_aws_clients
from app.core.settings import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class SignupRequest(BaseModel):
    username: str = Field(min_length=1)
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)


class ConfirmRequest(BaseModel):
    username: str = Field(min_length=1)
    code: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    id_token: str
    refresh_token: str
    expires_in: int
    user: dict


class MessageResponse(BaseModel):
    message: str
    verification_code: str | None = Field(
        default=None,
        description=(
            "Local-provider dev hint: the email verification code, so local signup "
            "is usable without a mail service. Never returned by the Cognito path."
        ),
    )


def _auth_provider(settings: Settings) -> str | None:
    if settings.cognito_enabled and settings.cognito_client_id:
        return "cognito"
    if settings.local_auth_enabled:
        return "local"
    return None


def _require_provider() -> Settings:
    settings = get_settings()
    if _auth_provider(settings) is None:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured on this deployment",
        )
    return settings


def _parse_id_token_claims(id_token: str) -> dict:
    """Decode the JWT payload (claims) without external crypto dependencies."""
    try:
        payload = id_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        if isinstance(claims, dict):
            return claims
    except Exception:
        pass
    return {}


def _user_from_claims(claims: dict) -> dict:
    username = claims.get("cognito:username") or claims.get("sub") or ""
    email = claims.get("email", "") or ""
    name = claims.get("name") or email or username
    return {"username": username, "email": email, "name": name}


def _cognito_login(settings: Settings, username: str, password: str) -> TokenResponse:
    client = get_aws_clients().cognito_idp
    try:
        response = client.initiate_auth(
            ClientId=settings.cognito_client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
    except client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    except client.exceptions.UserNotFoundException:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    except client.exceptions.UserNotConfirmedException:
        raise HTTPException(status_code=403, detail="User is not confirmed yet")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Cognito error: {exc}")

    result = response["AuthenticationResult"]
    claims = _parse_id_token_claims(result["IdToken"])
    return TokenResponse(
        access_token=result["AccessToken"],
        id_token=result["IdToken"],
        refresh_token=result.get("RefreshToken", ""),
        expires_in=result.get("ExpiresIn", 3600),
        user=_user_from_claims(claims),
    )


def _cognito_signup(settings: Settings, username: str, email: str, password: str) -> MessageResponse:
    client = get_aws_clients().cognito_idp
    try:
        client.sign_up(
            ClientId=settings.cognito_client_id,
            Username=username,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}],
        )
    except client.exceptions.UsernameExistsException:
        raise HTTPException(status_code=409, detail="Username already exists")
    except client.exceptions.InvalidPasswordException:
        raise HTTPException(
            status_code=400,
            detail="Password does not meet the pool password policy",
        )
    except client.exceptions.InvalidParameterException as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Cognito error: {exc}")

    return MessageResponse(
        message="Account created. Check your email for a verification code."
    )


def _cognito_confirm(settings: Settings, username: str, code: str) -> MessageResponse:
    client = get_aws_clients().cognito_idp
    try:
        client.confirm_sign_up(
            ClientId=settings.cognito_client_id,
            Username=username,
            ConfirmationCode=code,
        )
    except client.exceptions.CodeMismatchException:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    except client.exceptions.ExpiredCodeException:
        raise HTTPException(status_code=400, detail="Verification code expired")
    except client.exceptions.UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Cognito error: {exc}")

    return MessageResponse(message="Account confirmed. You can now sign in.")


def _cognito_refresh(settings: Settings, refresh_token: str) -> TokenResponse:
    client = get_aws_clients().cognito_idp
    try:
        response = client.initiate_auth(
            ClientId=settings.cognito_client_id,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={"REFRESH_TOKEN": refresh_token},
        )
    except client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Cognito error: {exc}")

    result = response["AuthenticationResult"]
    claims = _parse_id_token_claims(result["IdToken"])
    return TokenResponse(
        access_token=result["AccessToken"],
        id_token=result["IdToken"],
        refresh_token=refresh_token,
        expires_in=result.get("ExpiresIn", 3600),
        user=_user_from_claims(claims),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    settings = _require_provider()
    if _auth_provider(settings) == "local":
        try:
            user = local_auth.authenticate(settings, payload.username, payload.password)
            tokens = local_auth.issue_tokens(settings, user)
        except local_auth.LocalAuthError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail)
        return TokenResponse(**tokens, user=user)
    return _cognito_login(settings, payload.username, payload.password)


@router.post("/signup", response_model=MessageResponse)
def signup(payload: SignupRequest):
    settings = _require_provider()
    if _auth_provider(settings) == "local":
        try:
            user = local_auth.create_user(settings, payload.username, payload.email, payload.password)
        except local_auth.LocalAuthError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail)
        return MessageResponse(
            message="Account created. Check your email for a verification code.",
            verification_code=user.get("verification_code"),
        )
    return _cognito_signup(settings, payload.username, payload.email, payload.password)


@router.post("/confirm", response_model=MessageResponse)
def confirm(payload: ConfirmRequest):
    settings = _require_provider()
    if _auth_provider(settings) == "local":
        try:
            local_auth.confirm_user(settings, payload.username, payload.code)
        except local_auth.LocalAuthError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail)
        return MessageResponse(message="Account confirmed. You can now sign in.")
    return _cognito_confirm(settings, payload.username, payload.code)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest):
    settings = _require_provider()
    if _auth_provider(settings) == "local":
        try:
            tokens, user = local_auth.refresh_session(settings, payload.refresh_token)
        except local_auth.LocalAuthError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail)
        return TokenResponse(**tokens, user=user)
    return _cognito_refresh(settings, payload.refresh_token)


@router.get("/me")
def me(request: Request):
    """Return the authenticated user (validated by the auth middleware)."""
    settings = get_settings()
    if _auth_provider(settings) is None:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured on this deployment",
        )
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
