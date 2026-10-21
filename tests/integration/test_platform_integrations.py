"""Integration tests for Cotality platform integrations.

Validates that session/memory defaults, LiteLLM configuration, A2A executor
setup, MCP tool factory functions, observability instrumentation, and the
lifespan registry all behave as expected.

Acceptance Criteria (ANE-3476): authentication bypass/public paths,
authenticated request context propagation, A2A/MCP tool configuration,
LiteLLM configuration, observability initialization, and session/memory
defaults behave as expected.
"""

import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_AGENT_SRC = Path(__file__).parent.parent.parent / "src" / "cotality" / "agent"


class TestSessionMemoryDefaults:
    """Verify that in-memory services are declared in agent.py.

    Using source-code analysis (same pattern as test_fastapi_server.py) to
    confirm the template does not accidentally introduce disk-backed services
    that break on GKE.
    """

    @pytest.fixture(scope="class")
    def agent_source(self) -> str:
        """Return agent.py source text."""
        return (_AGENT_SRC / "agent.py").read_text()

    def test_in_memory_session_service_used(self, agent_source):
        """agent.py must use InMemorySessionService for session storage."""
        assert "InMemorySessionService()" in agent_source, (
            "agent.py must use InMemorySessionService — disk-backed services "
            "cause PermissionError on GKE."
        )

    def test_in_memory_artifact_service_used(self, agent_source):
        """agent.py must use InMemoryArtifactService for artifact storage."""
        assert "InMemoryArtifactService()" in agent_source, (
            "agent.py must use InMemoryArtifactService — disk-backed services "
            "cause PermissionError on GKE."
        )

    def test_in_memory_memory_service_used(self, agent_source):
        """agent.py must use InMemoryMemoryService for conversation memory."""
        assert "InMemoryMemoryService()" in agent_source, (
            "agent.py must use InMemoryMemoryService — disk-backed services "
            "cause PermissionError on GKE."
        )

    def test_fastapi_server_session_uri_is_in_memory_sqlite(self):
        """fastapi_server.py must set session_service_uri to the in-memory SQLite URI."""
        source = (_AGENT_SRC / "fastapi_server.py").read_text()
        assert 'session_service_uri="sqlite+aiosqlite:///:memory:"' in source, (
            "fastapi_server.py must use sqlite+aiosqlite:///:memory: to avoid "
            "filesystem operations on GKE."
        )

    def test_fastapi_server_artifact_uri_is_in_memory(self):
        """fastapi_server.py must set artifact_service_uri to in-memory scheme."""
        source = (_AGENT_SRC / "fastapi_server.py").read_text()
        assert 'artifact_service_uri="memory://"' in source, (
            "fastapi_server.py must use memory:// artifact URI to avoid "
            "filesystem operations on GKE."
        )


class TestLiteLLMConfiguration:
    """Verify LiteLLM model configuration is driven by environment variables."""

    def test_create_litellm_with_retry_is_callable(self):
        """create_litellm_with_retry factory is importable and callable."""
        from cotality_agent_sdk.config.litellm_retry import create_litellm_with_retry

        assert callable(create_litellm_with_retry)

    def test_agent_build_passes_litellm_api_key_from_env(self):
        """_build_agent passes LITELLM_API_KEY env var to create_litellm_with_retry."""
        with (
            patch.dict(
                os.environ,
                {"LITELLM_API_KEY": "sentinel-api-key", "LITELLM_API_BASE": "https://test.base"},
            ),
            patch("src.cotality.agent.agent.create_litellm_with_retry") as mock_factory,
            patch("src.cotality.agent.agent.LlmAgent", return_value=MagicMock()),
            patch("src.cotality.agent.agent.Agent", return_value=MagicMock()),
            patch("src.cotality.agent.agent.Runner", return_value=MagicMock()),
        ):
            mock_factory.return_value = MagicMock()
            from src.cotality.agent.agent import MyAgent

            MyAgent()
            api_keys_used = [call.kwargs.get("api_key") for call in mock_factory.call_args_list]
            assert "sentinel-api-key" in api_keys_used, (
                "LITELLM_API_KEY env var was not forwarded to create_litellm_with_retry."
            )

    def test_agent_build_passes_litellm_api_base_from_env(self):
        """_build_agent passes LITELLM_API_BASE env var to create_litellm_with_retry."""
        with (
            patch.dict(
                os.environ,
                {"LITELLM_API_KEY": "test-key", "LITELLM_API_BASE": "https://sentinel.base"},
            ),
            patch("src.cotality.agent.agent.create_litellm_with_retry") as mock_factory,
            patch("src.cotality.agent.agent.LlmAgent", return_value=MagicMock()),
            patch("src.cotality.agent.agent.Agent", return_value=MagicMock()),
            patch("src.cotality.agent.agent.Runner", return_value=MagicMock()),
        ):
            mock_factory.return_value = MagicMock()
            from src.cotality.agent.agent import MyAgent

            MyAgent()
            api_bases_used = [call.kwargs.get("api_base") for call in mock_factory.call_args_list]
            assert "https://sentinel.base" in api_bases_used, (
                "LITELLM_API_BASE env var was not forwarded to create_litellm_with_retry."
            )

    def test_server_guards_against_missing_litellm_api_key(self):
        """server.py must raise MissingAPIKeyError when LITELLM_API_KEY is absent."""
        source = (_AGENT_SRC / "server.py").read_text()
        assert "LITELLM_API_KEY" in source and "MissingAPIKeyError" in source, (
            "server.py must validate LITELLM_API_KEY before starting."
        )

    def test_fastapi_server_guards_against_missing_litellm_api_key(self):
        """fastapi_server.py must raise MissingAPIKeyError when LITELLM_API_KEY is absent."""
        source = (_AGENT_SRC / "fastapi_server.py").read_text()
        assert "LITELLM_API_KEY" in source and "MissingAPIKeyError" in source, (
            "fastapi_server.py must validate LITELLM_API_KEY before starting."
        )


class TestA2AConfiguration:
    """Verify A2A protocol executor and task store configuration."""

    def test_server_uses_a2a_agent_executor_v2_path(self):
        """server.py imports A2aAgentExecutor from the ADK v2 module path."""
        source = (_AGENT_SRC / "server.py").read_text()
        assert (
            "from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor" in source
        ), "server.py must use A2aAgentExecutor from the ADK v2 import path."

    def test_server_passes_runner_to_a2a_executor(self):
        """server.py instantiates A2aAgentExecutor with runner=agent.runner."""
        source = (_AGENT_SRC / "server.py").read_text()
        assert "A2aAgentExecutor(runner=agent.runner)" in source, (
            "server.py must pass runner=agent.runner to A2aAgentExecutor."
        )

    def test_fastapi_server_uses_cotality_agent_executor(self):
        """fastapi_server.py uses CotalityAgentExecutor for A2A task execution."""
        source = (_AGENT_SRC / "fastapi_server.py").read_text()
        assert "CotalityAgentExecutor" in source, (
            "fastapi_server.py must use CotalityAgentExecutor."
        )

    def test_both_servers_use_in_memory_task_store(self):
        """Both server implementations must use InMemoryTaskStore."""
        for server_file in ("server.py", "fastapi_server.py"):
            source = (_AGENT_SRC / server_file).read_text()
            assert "InMemoryTaskStore" in source, (
                f"{server_file} must use InMemoryTaskStore for A2A task management."
            )

    def test_agent_card_well_known_path_in_public_paths(self):
        """OAuth2Middleware must whitelist the agent card path as a public path."""
        source = (_AGENT_SRC / "utils" / "oauth2_middleware.py").read_text()
        assert "/.well-known/agent-card.json" in source, (
            "OAuth2Middleware must treat /.well-known/agent-card.json as a public path."
        )


class TestMCPToolConfiguration:
    """Verify MCP tool factory functions can be imported and smoke-tested."""

    @pytest.mark.parametrize(
        "func_name",
        ["get_http_mcp_tool", "get_sse_mcp_tool", "get_local_mcp_tool", "get_npx_mcp_tool"],
    )
    def test_mcp_factory_is_callable(self, func_name):
        """Each MCP tool factory function must be callable."""
        import importlib

        module = importlib.import_module("src.cotality.agent.utils.mcp_tools")
        func = getattr(module, func_name)
        assert callable(func), f"{func_name} must be callable."

    def test_get_http_mcp_tool_returns_mcp_toolset(self):
        """get_http_mcp_tool must return an MCPToolset instance."""
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

        from src.cotality.agent.utils.mcp_tools import get_http_mcp_tool

        result = get_http_mcp_tool("https://example.com/mcp/")
        assert isinstance(result, MCPToolset)

    def test_get_sse_mcp_tool_returns_mcp_toolset(self):
        """get_sse_mcp_tool must return an MCPToolset instance."""
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

        from src.cotality.agent.utils.mcp_tools import get_sse_mcp_tool

        result = get_sse_mcp_tool("https://example.com/sse/")
        assert isinstance(result, MCPToolset)


class TestObservabilityInitialization:
    """Verify observability hooks are importable and callable without crashing."""

    def test_instrument_starlette_app_importable(self):
        """instrument_starlette_app is importable from cotality_agent_sdk."""
        from cotality_agent_sdk.observability.tracing import instrument_starlette_app

        assert callable(instrument_starlette_app)

    def test_instrument_fastapi_app_importable(self):
        """instrument_fastapi_app is importable from cotality_agent_sdk.observability."""
        from cotality_agent_sdk.observability import instrument_fastapi_app

        assert callable(instrument_fastapi_app)

    def test_tracing_lifespan_importable(self):
        """tracing_lifespan is importable from cotality_agent_sdk.lifespans."""
        from cotality_agent_sdk.lifespans import tracing_lifespan

        assert callable(tracing_lifespan)

    def test_server_calls_instrument_starlette_app(self):
        """server.py must call instrument_starlette_app for distributed tracing."""
        source = (_AGENT_SRC / "server.py").read_text()
        assert "instrument_starlette_app(app)" in source, (
            "server.py must call instrument_starlette_app(app) to enable tracing."
        )

    def test_fastapi_server_calls_instrument_fastapi_app(self):
        """fastapi_server.py must call instrument_fastapi_app for distributed tracing."""
        source = (_AGENT_SRC / "fastapi_server.py").read_text()
        assert "instrument_fastapi_app(app)" in source, (
            "fastapi_server.py must call instrument_fastapi_app(app) to enable tracing."
        )


class TestLifespanRegistry:
    """Verify the lifespan registry correctly accumulates and exposes handlers."""

    def test_register_and_retrieve_handler(self):
        """register_lifespan adds a handler that get_lifespan_handlers returns."""
        from src.cotality.agent.utils.lifespan_registry import (
            _lifespan_handlers,
            get_lifespan_handlers,
            register_lifespan,
        )

        initial_count = len(get_lifespan_handlers())

        async def _dummy_lifespan(app):  # pragma: no cover
            yield

        register_lifespan(_dummy_lifespan)
        try:
            assert len(get_lifespan_handlers()) == initial_count + 1
            assert _dummy_lifespan in get_lifespan_handlers()
        finally:
            # Always clean up so a failed assertion does not leak state into
            # subsequent tests that read len(get_lifespan_handlers()).
            _lifespan_handlers.remove(_dummy_lifespan)

    def test_register_lifespan_returns_handler(self):
        """register_lifespan returns the handler unchanged (supports decorator use)."""
        from src.cotality.agent.utils.lifespan_registry import (
            _lifespan_handlers,
            register_lifespan,
        )

        async def _another_lifespan(app):  # pragma: no cover
            yield

        result = register_lifespan(_another_lifespan)
        try:
            assert result is _another_lifespan
        finally:
            _lifespan_handlers.remove(_another_lifespan)

    def test_tracing_lifespan_is_registered_in_server(self):
        """server.py must call register_lifespan(tracing_lifespan)."""
        source = (_AGENT_SRC / "server.py").read_text()
        assert "register_lifespan(tracing_lifespan)" in source, (
            "server.py must register tracing_lifespan for observability startup."
        )
