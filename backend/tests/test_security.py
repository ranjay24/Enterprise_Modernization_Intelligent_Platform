"""P4.1 — API key authentication wiring.

Ensures the API key can be configured via EMIP_API_KEY or API_KEY (previously
the middleware read EMIP_API_KEY while pydantic bound api_key to API_KEY, so the
key silently never matched), and that the middleware enforces 401 when a key is
configured while staying disabled (permissive) when no key is set.
"""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.core import security as security_mod
from app.core.security import APIKeyMiddleware
from app.core.settings import Settings


class TestApiKeySettingsBinding:
    def test_kwarg_binding(self):
        s = Settings(_env_file=None, api_key="abc123")
        assert s.api_key == "abc123"

    def test_emip_api_key_env_binding(self, monkeypatch):
        monkeypatch.setenv("EMIP_API_KEY", "secret-123")
        s = Settings(_env_file=None)
        assert s.api_key == "secret-123"

    def test_legacy_api_key_env_binding(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "legacy-456")
        s = Settings(_env_file=None)
        assert s.api_key == "legacy-456"

    def test_emip_takes_precedence_over_api_key(self, monkeypatch):
        monkeypatch.setenv("EMIP_API_KEY", "emip-777")
        monkeypatch.setenv("API_KEY", "plain-888")
        s = Settings(_env_file=None)
        assert s.api_key == "emip-777"

    def test_default_disabled(self):
        assert Settings(_env_file=None).api_key == ""


class TestCorsOriginsParsing:
    def test_comma_separated_env(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "http://a.com,http://b.com")
        assert Settings(_env_file=None).cors_origins == ["http://a.com", "http://b.com"]

    def test_json_array_env(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", '["http://x.com","http://y.com"]')
        assert Settings(_env_file=None).cors_origins == ["http://x.com", "http://y.com"]

    def test_empty_env_uses_default(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "")
        assert Settings(_env_file=None).cors_origins == ["http://localhost:5173", "http://localhost:3000"]

    def test_kwarg_list_unchanged(self):
        s = Settings(_env_file=None, cors_origins=["http://localhost:9999"])
        assert s.cors_origins == ["http://localhost:9999"]


@pytest.fixture
def _patch_settings(monkeypatch):
    """Fixture factory — call _patch_settings(api_key=...) to set the value."""
    def _set(api_key: str):
        monkeypatch.setattr(security_mod, "get_settings", lambda: Settings(_env_file=None, api_key=api_key))
    return _set


def _make_client():
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    app.add_middleware(APIKeyMiddleware)
    return TestClient(app)


class TestAPIKeyMiddleware:
    def test_rejects_missing_key(self, _patch_settings):
        _patch_settings("topsecret")
        client = _make_client()
        resp = client.get("/api/ping")
        assert resp.status_code == 401

    def test_rejects_wrong_key(self, _patch_settings):
        _patch_settings("topsecret")
        client = _make_client()
        resp = client.get("/api/ping", headers={"X-API-Key": "nope"})
        assert resp.status_code == 401

    def test_accepts_correct_key(self, _patch_settings):
        _patch_settings("topsecret")
        client = _make_client()
        resp = client.get("/api/ping", headers={"X-API-Key": "topsecret"})
        assert resp.status_code == 200

    def test_disabled_when_no_key(self, _patch_settings):
        _patch_settings("")
        client = _make_client()
        resp = client.get("/api/ping")
        assert resp.status_code == 200
