"""Cognito authentication — middleware token validation + auth routes.

Covers: settings binding, bearer-token validation via cognito-idp GetUser,
invalid-token 401, API-key fallback coexistence, public auth endpoints, and the
login/signup/confirm/refresh/me route handlers against a fake Cognito client.
"""

import base64
import json

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.core import security as security_mod
from app.core.security import APIKeyMiddleware
from app.core.settings import Settings
from app.routes.auth import router as auth_router


class CognitoException(Exception):
    pass


NotAuthorizedException = type("NotAuthorizedException", (CognitoException,), {})
UserNotFoundException = type("UserNotFoundException", (CognitoException,), {})
UserNotConfirmedException = type("UserNotConfirmedException", (CognitoException,), {})
UsernameExistsException = type("UsernameExistsException", (CognitoException,), {})
InvalidPasswordException = type("InvalidPasswordException", (CognitoException,), {})
InvalidParameterException = type("InvalidParameterException", (CognitoException,), {})
CodeMismatchException = type("CodeMismatchException", (CognitoException,), {})
ExpiredCodeException = type("ExpiredCodeException", (CognitoException,), {})


class FakeIDPExceptions:
    NotAuthorizedException = NotAuthorizedException
    UserNotFoundException = UserNotFoundException
    UserNotConfirmedException = UserNotConfirmedException
    UsernameExistsException = UsernameExistsException
    InvalidPasswordException = InvalidPasswordException
    InvalidParameterException = InvalidParameterException
    CodeMismatchException = CodeMismatchException
    ExpiredCodeException = ExpiredCodeException


class FakeCognitoIDP:
    exceptions = FakeIDPExceptions

    def __init__(self):
        self.get_user_tokens = []
        self.get_user_error = None
        self.initiate_auth_error = None
        self.sign_up_error = None
        self.confirm_error = None

    def get_user(self, AccessToken):
        self.get_user_tokens.append(AccessToken)
        if self.get_user_error:
            raise self.get_user_error
        return {
            "Username": "alice",
            "UserAttributes": [
                {"Name": "email", "Value": "alice@emip.io"},
                {"Name": "name", "Value": "Alice Smith"},
            ],
        }

    def initiate_auth(self, **kwargs):
        if self.initiate_auth_error:
            raise self.initiate_auth_error
        return {
            "AuthenticationResult": {
                "AccessToken": "at-123",
                "IdToken": _make_id_token(
                    **{
                        "cognito:username": "alice",
                        "email": "alice@emip.io",
                        "name": "Alice Smith",
                    }
                ),
                "RefreshToken": "rt-456",
                "ExpiresIn": 3600,
            }
        }

    def sign_up(self, **kwargs):
        if self.sign_up_error:
            raise self.sign_up_error
        return {"UserSub": "sub-123"}

    def confirm_sign_up(self, **kwargs):
        if self.confirm_error:
            raise self.confirm_error
        return {}


def _make_id_token(**claims):
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"header.{payload}.sig"


def _cognito_settings(**overrides):
    defaults = dict(
        cognito_enabled=True,
        cognito_user_pool_id="us-east-1_pool",
        cognito_region="us-east-1",
        cognito_client_id="client123",
    )
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


@pytest.fixture
def fake_clients(monkeypatch):
    fake = FakeCognitoIDP()

    class FakeClients:
        @property
        def cognito_idp(self):
            return fake

    monkeypatch.setattr(security_mod, "get_aws_clients", lambda: FakeClients())
    return fake


@pytest.fixture
def patch_settings(monkeypatch):
    def _set(settings):
        monkeypatch.setattr(security_mod, "get_settings", lambda: settings)

    return _set


def _make_ping_app():
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    app.add_middleware(APIKeyMiddleware)
    return TestClient(app)


class TestSettingsBinding:
    def test_default_disabled(self):
        s = Settings(_env_file=None)
        assert s.cognito_enabled is False
        assert s.cognito_user_pool_id == ""
        # Local provider is the out-of-the-box default when Cognito is off
        assert s.local_auth_enabled is True

    def test_env_binding(self, monkeypatch):
        monkeypatch.setenv("EMIP_COGNITO_ENABLED", "true")
        monkeypatch.setenv("EMIP_COGNITO_USER_POOL_ID", "us-east-1_abc")
        monkeypatch.setenv("EMIP_COGNITO_CLIENT_ID", "client-xyz")
        s = Settings(_env_file=None)
        assert s.cognito_enabled is True
        assert s.cognito_user_pool_id == "us-east-1_abc"
        assert s.cognito_client_id == "client-xyz"


class TestCognitoMiddleware:
    def test_valid_bearer_token_allowed(self, fake_clients, patch_settings):
        patch_settings(_cognito_settings())
        client = _make_ping_app()
        resp = client.get("/api/ping", headers={"Authorization": "Bearer valid-token"})
        assert resp.status_code == 200
        assert fake_clients.get_user_tokens == ["valid-token"]

    def test_invalid_bearer_token_rejected(self, fake_clients, patch_settings):
        fake_clients.get_user_error = NotAuthorizedException("bad token")
        patch_settings(_cognito_settings())
        client = _make_ping_app()
        resp = client.get("/api/ping", headers={"Authorization": "Bearer bad-token"})
        assert resp.status_code == 401

    def test_no_credentials_rejected_when_cognito_enabled(self, fake_clients, patch_settings):
        patch_settings(_cognito_settings())
        client = _make_ping_app()
        assert client.get("/api/ping").status_code == 401

    def test_api_key_still_works_when_cognito_enabled(self, fake_clients, patch_settings):
        patch_settings(_cognito_settings(api_key="topsecret"))
        client = _make_ping_app()
        resp = client.get("/api/ping", headers={"X-API-Key": "topsecret"})
        assert resp.status_code == 200

    def test_auth_disabled_is_permissive(self, patch_settings):
        patch_settings(Settings(_env_file=None, local_auth_enabled=False))
        client = _make_ping_app()
        assert client.get("/api/ping").status_code == 200

    def test_health_stays_public(self, fake_clients, patch_settings):
        patch_settings(_cognito_settings())
        app = FastAPI()

        @app.get("/api/health")
        def health():
            return {"status": "healthy"}

        app.add_middleware(APIKeyMiddleware)
        resp = TestClient(app).get("/api/health")
        assert resp.status_code == 200


class TestAuthRoutes:
    @pytest.fixture
    def client(self, monkeypatch, fake_clients, patch_settings):
        settings = _cognito_settings()
        patch_settings(settings)
        from app.routes import auth as auth_mod

        monkeypatch.setattr(auth_mod, "get_aws_clients", lambda: _FakeClientsWith(fake_clients))
        monkeypatch.setattr(auth_mod, "get_settings", lambda: settings)

        app = FastAPI()
        app.include_router(auth_router, prefix="/api")
        app.add_middleware(APIKeyMiddleware)
        return TestClient(app)

    def test_login_success(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "Password1!"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] == "at-123"
        assert body["refresh_token"] == "rt-456"
        assert body["user"] == {
            "username": "alice",
            "email": "alice@emip.io",
            "name": "Alice Smith",
        }

    def test_login_wrong_password(self, client, fake_clients):
        fake_clients.initiate_auth_error = NotAuthorizedException("nope")
        resp = client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_login_unconfirmed(self, client, fake_clients):
        fake_clients.initiate_auth_error = UserNotConfirmedException("not confirmed")
        resp = client.post(
            "/api/auth/login",
            json={"username": "bob", "password": "Password1!"},
        )
        assert resp.status_code == 403

    def test_login_not_configured_503(self, monkeypatch, fake_clients):
        disabled = Settings(_env_file=None, local_auth_enabled=False)
        from app.routes import auth as auth_mod

        monkeypatch.setattr(auth_mod, "get_settings", lambda: disabled)
        monkeypatch.setattr(auth_mod, "get_aws_clients", lambda: _FakeClientsWith(fake_clients))
        monkeypatch.setattr(security_mod, "get_settings", lambda: disabled)

        app = FastAPI()
        app.include_router(auth_router, prefix="/api")
        app.add_middleware(APIKeyMiddleware)
        resp = TestClient(app).post("/api/auth/login", json={"username": "a", "password": "b"})
        assert resp.status_code == 503

    def test_signup_success(self, client):
        resp = client.post(
            "/api/auth/signup",
            json={"username": "alice", "email": "alice@emip.io", "password": "Password1!"},
        )
        assert resp.status_code == 200
        assert "verification" in resp.json()["message"]

    def test_signup_duplicate(self, client, fake_clients):
        fake_clients.sign_up_error = UsernameExistsException("exists")
        resp = client.post(
            "/api/auth/signup",
            json={"username": "alice", "email": "alice@emip.io", "password": "Password1!"},
        )
        assert resp.status_code == 409

    def test_confirm_success(self, client):
        resp = client.post(
            "/api/auth/confirm",
            json={"username": "alice", "code": "123456"},
        )
        assert resp.status_code == 200

    def test_confirm_bad_code(self, client, fake_clients):
        fake_clients.confirm_error = CodeMismatchException("bad code")
        resp = client.post(
            "/api/auth/confirm",
            json={"username": "alice", "code": "000000"},
        )
        assert resp.status_code == 400

    def test_refresh_success(self, client):
        resp = client.post("/api/auth/refresh", json={"refresh_token": "rt-456"})
        assert resp.status_code == 200
        assert resp.json()["access_token"] == "at-123"

    def test_me_unauthenticated_401(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_me_with_valid_token_200(self, client):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer access-token-123"},
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "alice"

    def test_me_with_invalid_token_401(self, client, fake_clients):
        fake_clients.get_user_error = NotAuthorizedException()
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer garbage-token"},
        )
        assert resp.status_code == 401

    def test_me_not_configured_503(self, monkeypatch, fake_clients):
        disabled = Settings(_env_file=None, local_auth_enabled=False)
        from app.routes import auth as auth_mod

        monkeypatch.setattr(auth_mod, "get_settings", lambda: disabled)
        monkeypatch.setattr(auth_mod, "get_aws_clients", lambda: _FakeClientsWith(fake_clients))
        monkeypatch.setattr(security_mod, "get_settings", lambda: disabled)

        app = FastAPI()
        app.include_router(auth_router, prefix="/api")
        app.add_middleware(APIKeyMiddleware)
        resp = TestClient(app).get("/api/auth/me")
        assert resp.status_code == 503

    def test_auth_endpoints_public_when_cognito_enabled(self, client):
        # No credentials at all — middleware must NOT 401 the login route
        resp = client.post("/api/auth/login", json={"username": "alice", "password": "x"})
        assert resp.status_code != 401


def _FakeClientsWith(fake):
    class _Inner:
        @property
        def cognito_idp(self):
            return fake

    return _Inner()
