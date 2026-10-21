"""Unit tests for OAuth2Middleware authentication behaviour.

Verifies that:
  - public paths (/health, /.well-known/agent-card.json) bypass auth
  - ENABLE_AGENT_AUTH0=False bypasses auth for all paths
  - protected paths without a valid Bearer token return HTTP 401
  - 401 responses carry a machine-readable JSON error body

Acceptance Criteria (ANE-3476): authentication bypass/public paths and
authenticated request context propagation behave as expected.
"""

import os
from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient


def _build_test_app() -> Starlette:
    """Build a minimal Starlette app with OAuth2Middleware attached."""
    from src.cotality.agent.utils.oauth2_middleware import OAuth2Middleware

    async def _endpoint(request: Request) -> JSONResponse:
        return JSONResponse({"message": "authorized"})

    app = Starlette(
        routes=[
            Route("/protected", _endpoint),
            Route("/health", _endpoint),
            Route("/.well-known/agent-card.json", _endpoint),
        ]
    )
    app.add_middleware(OAuth2Middleware)
    return app


@pytest.fixture(autouse=True)
def _reset_jwks_client():
    """Reset the class-level JWKS client cache between tests."""
    from src.cotality.agent.utils.oauth2_middleware import OAuth2Middleware

    OAuth2Middleware._jwks_client = None
    yield
    OAuth2Middleware._jwks_client = None


class TestPublicPaths:
    """Public paths must be reachable without an Authorization header."""

    def test_health_path_bypasses_auth(self):
        """GET /health returns 200 with no Authorization header."""
        with patch.dict(os.environ, {"ENABLE_AGENT_AUTH0": "True"}):
            client = TestClient(_build_test_app(), raise_server_exceptions=False)
            response = client.get("/health")
        assert response.status_code == 200

    def test_agent_card_path_bypasses_auth(self):
        """GET /.well-known/agent-card.json returns 200 without a token."""
        with patch.dict(os.environ, {"ENABLE_AGENT_AUTH0": "True"}):
            client = TestClient(_build_test_app(), raise_server_exceptions=False)
            response = client.get("/.well-known/agent-card.json")
        assert response.status_code == 200


class TestAuthDisabled:
    """When ENABLE_AGENT_AUTH0 is False all paths are accessible without a token."""

    def test_protected_path_accessible_when_auth_disabled(self):
        """With ENABLE_AGENT_AUTH0=False, /protected returns 200 without a token."""
        with patch.dict(os.environ, {"ENABLE_AGENT_AUTH0": "False"}):
            client = TestClient(_build_test_app(), raise_server_exceptions=False)
            response = client.get("/protected")
        assert response.status_code == 200


class TestAuthEnforced:
    """Protected paths must require a valid Bearer token when auth is enabled."""

    def test_missing_authorization_header_returns_401(self):
        """No Authorization header on a protected path → HTTP 401."""
        with patch.dict(os.environ, {"ENABLE_AGENT_AUTH0": "True"}):
            client = TestClient(_build_test_app(), raise_server_exceptions=False)
            response = client.get("/protected")
        assert response.status_code == 401

    def test_non_bearer_scheme_returns_401(self):
        """Authorization header with Basic scheme → HTTP 401."""
        with patch.dict(os.environ, {"ENABLE_AGENT_AUTH0": "True"}):
            client = TestClient(_build_test_app(), raise_server_exceptions=False)
            response = client.get("/protected", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert response.status_code == 401

    def test_invalid_bearer_token_returns_401(self):
        """A syntactically invalid Bearer token → HTTP 401."""
        with patch.dict(
            os.environ,
            {"ENABLE_AGENT_AUTH0": "True"},
            clear=False,
        ):
            # Ensure AGENT_AUTH0_JWK_URL is absent so PyJWKClient raises before
            # making any network call.
            os.environ.pop("AGENT_AUTH0_JWK_URL", None)
            client = TestClient(_build_test_app(), raise_server_exceptions=False)
            response = client.get("/protected", headers={"Authorization": "Bearer not.a.real.jwt"})
        assert response.status_code == 401

    def test_401_response_has_error_field(self):
        """401 response body contains JSON with an 'error' key equal to 'unauthorized'."""
        with patch.dict(os.environ, {"ENABLE_AGENT_AUTH0": "True"}):
            client = TestClient(_build_test_app(), raise_server_exceptions=False)
            response = client.get("/protected")
        assert response.status_code == 401
        body = response.json()
        assert "error" in body
        assert body["error"] == "unauthorized"

    def test_401_response_has_reason_field(self):
        """401 response body contains a 'reason' field describing the failure."""
        with patch.dict(os.environ, {"ENABLE_AGENT_AUTH0": "True"}):
            client = TestClient(_build_test_app(), raise_server_exceptions=False)
            response = client.get("/protected")
        body = response.json()
        assert "reason" in body
