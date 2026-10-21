"""ADK v2 SDK compatibility regression tests.

These tests verify that the ADK v2 API contracts required by this template are
in place. Any test failure here indicates an SDK regression — either a downgrade
to v1 or a breaking change in v2 — that would break the template at runtime.

Acceptance Criteria (ANE-3476): ADK v2-specific regressions in SDK integration
behaviour fail the build.
"""

import inspect

import pytest


class TestAdkV2ImportPaths:
    """Verify ADK v2 module import paths are accessible.

    ADK v1 used different import paths for several core classes. Failure here
    means the installed SDK is v1 or a breaking refactor has occurred.
    """

    def test_get_fast_api_app_importable(self):
        """get_fast_api_app must be importable from google.adk.cli.fast_api (v2 path)."""
        from google.adk.cli.fast_api import get_fast_api_app

        assert callable(get_fast_api_app)

    def test_a2a_agent_executor_importable(self):
        """A2aAgentExecutor must exist at the ADK v2 module path."""
        from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor

        assert A2aAgentExecutor is not None

    def test_in_memory_session_service_importable(self):
        """InMemorySessionService must be importable from google.adk.sessions."""
        from google.adk.sessions import InMemorySessionService

        assert InMemorySessionService is not None

    def test_in_memory_artifact_service_importable(self):
        """InMemoryArtifactService must be importable from google.adk.artifacts."""
        from google.adk.artifacts import InMemoryArtifactService

        assert InMemoryArtifactService is not None

    def test_in_memory_memory_service_importable(self):
        """InMemoryMemoryService must be importable from google.adk.memory."""
        from google.adk.memory import InMemoryMemoryService

        assert InMemoryMemoryService is not None

    def test_runner_importable(self):
        """Runner must be importable from google.adk.runners."""
        from google.adk.runners import Runner

        assert Runner is not None

    def test_llm_agent_importable(self):
        """LlmAgent must be importable from google.adk.agents."""
        from google.adk.agents import LlmAgent

        assert LlmAgent is not None

    def test_agent_importable(self):
        """Agent must be importable from google.adk.agents."""
        from google.adk.agents import Agent

        assert Agent is not None

    def test_lite_llm_importable(self):
        """LiteLlm must be importable from google.adk.models.lite_llm."""
        from google.adk.models.lite_llm import LiteLlm

        assert LiteLlm is not None

    def test_tool_context_importable(self):
        """ToolContext must be importable from google.adk.tools."""
        from google.adk.tools import ToolContext

        assert ToolContext is not None

    def test_agent_tool_importable(self):
        """agent_tool.AgentTool must be importable from google.adk.tools."""
        from google.adk.tools import agent_tool

        assert hasattr(agent_tool, "AgentTool")

    def test_mcp_toolset_importable(self):
        """MCPToolset must be importable from google.adk.tools.mcp_tool.mcp_toolset."""
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

        assert MCPToolset is not None


class TestAdkV2FastApiSignature:
    """Verify get_fast_api_app accepts the v2 keyword arguments.

    ADK v2 added session_service_uri and artifact_service_uri to
    get_fast_api_app. These parameters are required for in-memory storage
    on GKE where filesystem access causes PermissionError.
    """

    @pytest.fixture(scope="class")
    def fast_api_sig(self):
        """Return the signature of get_fast_api_app once per class."""
        from google.adk.cli.fast_api import get_fast_api_app

        return inspect.signature(get_fast_api_app)

    def test_accepts_session_service_uri(self, fast_api_sig):
        """get_fast_api_app must accept session_service_uri (in-memory SQLite on GKE)."""
        assert "session_service_uri" in fast_api_sig.parameters, (
            "ADK v2 regression: get_fast_api_app no longer accepts session_service_uri. "
            "Required for in-memory session storage on GKE."
        )

    def test_accepts_artifact_service_uri(self, fast_api_sig):
        """get_fast_api_app must accept artifact_service_uri (in-memory artifacts on GKE)."""
        assert "artifact_service_uri" in fast_api_sig.parameters, (
            "ADK v2 regression: get_fast_api_app no longer accepts artifact_service_uri. "
            "Required for in-memory artifact storage on GKE."
        )

    def test_accepts_lifespan(self, fast_api_sig):
        """get_fast_api_app must accept lifespan to hook startup/shutdown events."""
        assert "lifespan" in fast_api_sig.parameters, (
            "ADK v2 regression: get_fast_api_app no longer accepts a lifespan parameter."
        )

    def test_accepts_allow_origins(self, fast_api_sig):
        """get_fast_api_app must accept allow_origins for CORS configuration."""
        assert "allow_origins" in fast_api_sig.parameters, (
            "ADK v2 regression: get_fast_api_app no longer accepts allow_origins."
        )


class TestAdkV2RunnerApi:
    """Verify ADK v2 Runner constructor and streaming API."""

    @pytest.fixture(scope="class")
    def runner_init_sig(self):
        """Return the signature of Runner.__init__ once per class."""
        from google.adk.runners import Runner

        return inspect.signature(Runner.__init__)

    def test_runner_has_run_async(self):
        """Runner must expose run_async for async streaming agent execution."""
        from google.adk.runners import Runner

        assert hasattr(Runner, "run_async"), (
            "ADK v2 regression: Runner.run_async is missing. "
            "MyAgent.stream() depends on this method."
        )

    def test_runner_accepts_session_service(self, runner_init_sig):
        """Runner.__init__ must accept session_service parameter."""
        assert "session_service" in runner_init_sig.parameters, (
            "ADK v2 regression: Runner.__init__ no longer accepts session_service."
        )

    def test_runner_accepts_artifact_service(self, runner_init_sig):
        """Runner.__init__ must accept artifact_service parameter."""
        assert "artifact_service" in runner_init_sig.parameters, (
            "ADK v2 regression: Runner.__init__ no longer accepts artifact_service."
        )

    def test_runner_accepts_memory_service(self, runner_init_sig):
        """Runner.__init__ must accept memory_service parameter."""
        assert "memory_service" in runner_init_sig.parameters, (
            "ADK v2 regression: Runner.__init__ no longer accepts memory_service."
        )


class TestAdkV2AgentEvaluator:
    """Verify the ADK v2 AgentEvaluator API used in CI evaluation tests."""

    def test_agent_evaluator_importable(self):
        """AgentEvaluator must be importable from google.adk.evaluation."""
        from google.adk.evaluation.agent_evaluator import AgentEvaluator

        assert AgentEvaluator is not None

    def test_agent_evaluator_has_evaluate(self):
        """AgentEvaluator must expose an async evaluate class method."""
        from google.adk.evaluation.agent_evaluator import AgentEvaluator

        assert hasattr(AgentEvaluator, "evaluate"), (
            "ADK v2 regression: AgentEvaluator.evaluate is missing. "
            "test_adk_evaluation.py depends on this method."
        )
