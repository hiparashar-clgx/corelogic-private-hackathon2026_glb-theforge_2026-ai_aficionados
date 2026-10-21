"""
Unit tests for the fastapi_server.py module.

This module verifies that the FastAPI application in fastapi_server.py is configured
correctly with in-memory services to avoid filesystem operations, which is required
for GKE deployment where filesystem access causes PermissionError.

=== Why These Tests Use String-Based Validation ===

These tests read the source file as a string rather than importing the module.
This is intentional for the following reasons:

1. MODULE-LEVEL SIDE EFFECTS: fastapi_server.py creates a FastAPI app at module
   level when imported. This is a common FastAPI pattern but makes traditional
   unit testing impractical without extensive mocking.

2. CONFIGURATION VALIDATION: We're validating a configuration requirement (that
   in-memory services are used for GKE compatibility), not testing business logic.
   String-based validation is appropriate for ensuring specific configuration
   values are present.

3. AVOIDING MOCK ANTI-PATTERNS: Mock-based tests that verify "function X was
   called with parameter Y" test implementation details, not behavior. Such tests
   are fragile and break during refactoring even when the code still works correctly.

For behavior testing, rely on integration tests (tests/integration/test_server_startup.py)
that actually start the server and verify it works end-to-end.

If code coverage is required for this file, consider:
- Excluding fastapi_server.py from coverage requirements (it's wiring/configuration code)
- Achieving coverage through integration tests that import and run the actual server
"""

from pathlib import Path

import pytest


class TestFastApiServerConfiguration:
    """
    Tests for fastapi_server.py get_fast_api_app configuration.

    These tests verify our application's configuration by reading the source file
    and checking that the correct parameters are passed to get_fast_api_app().
    """

    @pytest.fixture
    def fastapi_server_source(self) -> str:
        """
        Fixture that reads the fastapi_server.py source code.

        Returns:
            str: The source code content.
        """
        fastapi_server_path = (
            Path(__file__).parent.parent.parent / "src" / "cotality" / "agent" / "fastapi_server.py"
        )
        return fastapi_server_path.read_text()

    def test_session_service_uses_in_memory_sqlite(self, fastapi_server_source: str):
        """
        Verify that session_service_uri is configured to use in-memory SQLite.

        The ':memory:' SQLite URI ensures sessions are stored in RAM, not on disk,
        preventing PermissionError on GKE where filesystem access is restricted.
        """
        expected_uri = 'session_service_uri="sqlite+aiosqlite:///:memory:"'
        assert expected_uri in fastapi_server_source, (
            f"Expected {expected_uri} in fastapi_server.py to avoid filesystem operations on GKE"
        )

    def test_artifact_service_uses_in_memory(self, fastapi_server_source: str):
        """
        Verify that artifact_service_uri is configured to use in-memory storage.

        The 'memory://' URI ensures artifacts are stored in RAM, not on disk,
        preventing PermissionError on GKE where filesystem access is restricted.

        Note: The 'memory' scheme is registered in google.adk.cli.service_registry
        (ADK v1.18.0+) and creates an InMemoryArtifactService instance.
        """
        expected_uri = 'artifact_service_uri="memory://"'
        assert expected_uri in fastapi_server_source, (
            f"Expected {expected_uri} in fastapi_server.py to avoid filesystem operations on GKE"
        )

    def test_get_fast_api_app_is_called(self, fastapi_server_source: str):
        """
        Verify that get_fast_api_app is imported and called.

        This is a basic sanity check to ensure the module uses the ADK's
        FastAPI app factory function.
        """
        assert "from google.adk.cli.fast_api import get_fast_api_app" in fastapi_server_source, (
            "get_fast_api_app should be imported from google.adk.cli.fast_api"
        )
        assert "get_fast_api_app(" in fastapi_server_source, (
            "get_fast_api_app() should be called to create the FastAPI app"
        )
