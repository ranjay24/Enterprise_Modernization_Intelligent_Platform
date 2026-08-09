"""Local auth provider — real signup/confirm/login/refresh/me without Cognito.

Covers: user persistence to a JSON store, PBKDF2 password verification, 6-digit
verification codes, HMAC-signed tokens validated by the middleware, the full
signup → confirm → login → /me happy path, and 503 when every provider is off.
"""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.core import security as security_mod
from app.core.security import APIKeyMiddleware
from app.core.settings import Settings
from app.routes import auth as auth_mod
from app.routes.auth import router as auth_router


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        local_auth_enabled=True,
        local_auth_data_dir=str(tmp_path / "auth"),
    )


@pytest.fixture
def client(monkeypatch, settings):
    monkeypatch.setattr(auth_mod, "get_settings", lambda: settings)
    monkeypatch.setattr(security_mod, "get_settings", lambda: settings)
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    app.include_router(auth_router, prefix="/api")
    app.add_middleware(APIKeyMiddleware)
    return TestClient(app)


def _signup(client, username="ranjay", email="ran@emip.io", password="Password1!"):
    return client.post(
        "/api/auth/signup",
        json={"username": username, "email": email, "password": password},
    )


class TestLocalSignup:
    def test_signup_creates_unconfirmed_user(self, client, settings):
        resp = _signup(client)
        assert resp.status_code == 200
        body = resp.json()
        assert "verification code" in body["message"].lower()
        code = body.get("verification_code")
        assert code and len(code) == 6 and code.isdigit()

    def test_signup_duplicate_409(self, client):
        assert _signup(client).status_code == 200
        assert _signup(client).status_code == 409

    def test_signup_duplicate_email_409(self, client):
        assert _signup(client, username="ranjay", email="ran@emip.io").status_code == 200
        resp = _signup(client, username="ranjay2", email="ran@emip.io")
        assert resp.status_code == 409
        assert "email" in resp.json()["detail"].lower()

    def test_signup_weak_password_400(self, client):
        resp = _signup(client, password="shortpw")
        assert resp.status_code == 400
        assert "8 characters" in resp.json()["detail"]


class TestLocalConfirmAndLogin:
    def test_login_before_confirm_403(self, client):
        _signup(client)
        resp = client.post("/api/auth/login", json={"username": "ranjay", "password": "Password1!"})
        assert resp.status_code == 403

    def test_confirm_wrong_code_400(self, client):
        _signup(client)
        resp = client.post("/api/auth/confirm", json={"username": "ranjay", "code": "000000"})
        assert resp.status_code == 400

    def test_login_by_email(self, client):
        """Login form only sends an email — resolve to the username account."""
        code = client.post("/api/auth/signup", json={"username": "ranjay", "email": "ran@emip.io", "password": "Password1!"}).json()["verification_code"]
        client.post("/api/auth/confirm", json={"username": "ran@emip.io", "code": code})
        resp = client.post("/api/auth/login", json={"username": "ran@emip.io", "password": "Password1!"})
        assert resp.status_code == 200
        assert resp.json()["user"]["email"] == "ran@emip.io"

    def test_full_flow(self, client):
        code = _signup(client).json()["verification_code"]
        assert client.post("/api/auth/confirm", json={"username": "ranjay", "code": code}).status_code == 200

        resp = client.post("/api/auth/login", json={"username": "ranjay", "password": "Password1!"})
        assert resp.status_code == 200
        tokens = resp.json()
        assert tokens["access_token"] and tokens["id_token"] and tokens["refresh_token"]
        assert tokens["user"]["username"] == "ranjay"
        assert tokens["user"]["email"] == "ran@emip.io"

        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tokens['id_token']}"})
        assert me.status_code == 200
        assert me.json()["username"] == "ranjay"

    def test_login_wrong_password_401(self, client):
        _signup(client)
        resp = client.post("/api/auth/login", json={"username": "ranjay", "password": "WrongPass1!"})
        assert resp.status_code == 401

    def test_me_unauthenticated_401(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_refresh_round_trip(self, client):
        code = _signup(client).json()["verification_code"]
        client.post("/api/auth/confirm", json={"username": "ranjay", "code": code})
        tokens = client.post(
            "/api/auth/login", json={"username": "ranjay", "password": "Password1!"}
        ).json()
        resp = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert resp.status_code == 200
        assert resp.json()["access_token"]
        assert resp.json()["user"]["username"] == "ranjay"

    def test_refresh_bad_token_401(self, client):
        resp = client.post("/api/auth/refresh", json={"refresh_token": "garbage"})
        assert resp.status_code == 401


class TestLocalMiddleware:
    def test_protected_route_401_without_credentials(self, client):
        assert client.get("/api/ping").status_code == 401

    def test_valid_token_passes_middleware(self, client):
        code = _signup(client).json()["verification_code"]
        client.post("/api/auth/confirm", json={"username": "ranjay", "code": code})
        token = client.post(
            "/api/auth/login", json={"username": "ranjay", "password": "Password1!"}
        ).json()["id_token"]
        resp = client.get("/api/ping", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_tampered_token_rejected(self, client, settings):
        from app.core import local_auth as la

        user = {"username": "x", "email": "x@emip.io", "name": "x"}
        token = la.issue_tokens(settings, user)["id_token"]
        tampered = token[:-1] + ("0" if token[-1] != "0" else "1")
        resp = client.get("/api/ping", headers={"Authorization": f"Bearer {tampered}"})
        assert resp.status_code == 401


class TestLocalDisabled:
    def test_503_when_no_provider(self, monkeypatch, tmp_path):
        disabled = Settings(
            _env_file=None,
            local_auth_enabled=False,
            cognito_enabled=False,
        )
        monkeypatch.setattr(auth_mod, "get_settings", lambda: disabled)
        monkeypatch.setattr(security_mod, "get_settings", lambda: disabled)

        app = FastAPI()

        @app.get("/api/ping")
        def ping():
            return {"ok": True}

        app.include_router(auth_router, prefix="/api")
        app.add_middleware(APIKeyMiddleware)
        tc = TestClient(app)

        assert tc.post("/api/auth/login", json={"username": "a", "password": "b"}).status_code == 503
        assert tc.post("/api/auth/signup", json={"username": "a", "email": "a@b.c", "password": "password1"}).status_code == 503
        assert tc.get("/api/auth/me").status_code == 503
        assert tc.get("/api/ping").status_code == 200
