"""
Integration tests for the server.py module.

This module contains tests that verify the agent server can start up properly,
handle health checks, serve the agent card, and properly validate required
environment variables.
"""

import os
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def mock_env_vars():
    """
    Fixture that sets up required environment variables for testing.

    Yields:
        dict: Original environment variable values for cleanup.
    """
    original_vars = {}
    required_vars = {
        "LITELLM_API_KEY": "test-api-key-12345",
        "LITELLM_API_BASE": "https://test.litellm.api.base",
        "ENV": "local",
        # Explicitly enable auth so that public-path bypass tests are meaningful.
        # Without this, None.__eq__("False") → NotImplemented (truthy) and auth
        # is globally skipped, making test_health_path_requires_no_auth and
        # test_agent_card_path_requires_no_auth trivially pass against any path.
        "ENABLE_AGENT_AUTH0": "True",
    }

    for key, value in required_vars.items():
        original_vars[key] = os.environ.get(key)
        os.environ[key] = value

    yield original_vars

    # Cleanup: restore original values
    for key, original_value in original_vars.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def test_app(mock_env_vars):
    """
    Fixture that creates a test instance of the server application.

    Mocks uvicorn.run to capture the actual app built by main() without
    starting the server. This ensures we test the real server setup code
    from server.py instead of duplicating it.

    Args:
        mock_env_vars: Fixture that sets up environment variables.

    Yields:
        TestClient: A Starlette test client for making requests.
    """
    from src.cotality.agent.server import main

    captured_app = None

    def mock_uvicorn_run(app, host, port):
        nonlocal captured_app
        captured_app = app

    with patch("uvicorn.run", side_effect=mock_uvicorn_run):
        # Call the actual main() function from server.py
        main.callback(host="localhost", port=8000)

    # Now we have the actual app that main() created
    with TestClient(captured_app) as client:
        yield client


def test_server_startup(test_app):
    """
    Test that the server application starts up properly.

    This test verifies that the server can be instantiated successfully
    with all required dependencies and configuration.

    Args:
        test_app: Test client fixture that builds and starts the server.
    """
    # If we get here without exceptions, the server started successfully
    assert test_app is not None


def test_health_endpoint_returns_ok(test_app):
    """
    Test that GET /health returns HTTP 200 with the expected JSON body.

    Acceptance Criteria (ANE-3476): the health endpoint returns expected responses.

    Args:
        test_app: Test client fixture.
    """
    response = test_app.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok"}, f"Unexpected health response: {body}"


def test_agent_card_endpoint_accessible(test_app):
    """
    Test that GET /.well-known/agent-card.json returns HTTP 200.

    The agent card is a public endpoint (no auth required) that A2A clients
    use to discover agent capabilities.

    Acceptance Criteria (ANE-3476): the agent card endpoint returns expected responses.

    Args:
        test_app: Test client fixture.
    """
    response = test_app.get("/.well-known/agent-card.json")
    assert response.status_code == 200


def test_agent_card_has_required_a2a_fields(test_app):
    """
    Test that the agent card JSON contains required A2A protocol fields.

    An agent card must include name, url, and version to be a valid A2A
    agent descriptor that downstream consumers can parse.

    Acceptance Criteria (ANE-3476): agent card endpoint returns expected responses.

    Args:
        test_app: Test client fixture.
    """
    response = test_app.get("/.well-known/agent-card.json")
    assert response.status_code == 200
    card = response.json()
    for field in ("name", "url", "version"):
        assert field in card, f"Agent card is missing required field '{field}': {card}"


def test_health_path_requires_no_auth(test_app):
    """
    Test that /health is accessible without an Authorization header.

    /health is a public path in OAuth2Middleware and must never require auth
    so that load-balancer health checks always succeed.

    Acceptance Criteria (ANE-3476): authentication bypass/public paths behave
    as expected.

    Args:
        test_app: Test client fixture.
    """
    response = test_app.get("/health", headers={})
    assert response.status_code == 200


def test_agent_card_path_requires_no_auth(test_app):
    """
    Test that /.well-known/agent-card.json is accessible without auth.

    A2A clients fetch the agent card before obtaining tokens, so this path
    must be publicly accessible.

    Acceptance Criteria (ANE-3476): authentication bypass/public paths behave
    as expected.

    Args:
        test_app: Test client fixture.
    """
    response = test_app.get("/.well-known/agent-card.json", headers={})
    assert response.status_code == 200
