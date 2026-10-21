"""Unit tests for agent.py — MyAgent class and supporting functions.

Tests cover the say_hello tool, MissingEnvError, MyAgent property accessors,
agent card generation for local and non-local environments, and supported
content types.  LLM construction is mocked so no API calls are made.

Acceptance Criteria (ANE-3476): unit checks that already exist for the
repository pass, and representative request paths behave as expected.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestSayHelloTool:
    """Tests for the say_hello tool function."""

    def test_returns_greeting_with_name(self):
        """say_hello returns 'Hello, {name}!' for the provided name."""
        from src.cotality.agent.agent import say_hello

        tool_context = MagicMock()
        assert say_hello("Alice", tool_context) == "Hello, Alice!"

    def test_works_with_multilingual_names(self):
        """say_hello handles names in non-ASCII languages."""
        from src.cotality.agent.agent import say_hello

        tool_context = MagicMock()
        assert say_hello("Priya", tool_context) == "Hello, Priya!"
        assert say_hello("Zhang Wei", tool_context) == "Hello, Zhang Wei!"
        assert say_hello("Alejandro", tool_context) == "Hello, Alejandro!"

    def test_return_type_is_str(self):
        """say_hello always returns a plain string."""
        from src.cotality.agent.agent import say_hello

        result = say_hello("World", MagicMock())
        assert isinstance(result, str)


class TestMissingEnvError:
    """Tests for the MissingEnvError exception class."""

    def test_is_subclass_of_exception(self):
        """MissingEnvError must derive from Exception."""
        from src.cotality.agent.agent import MissingEnvError

        assert issubclass(MissingEnvError, Exception)

    def test_can_be_raised_with_message(self):
        """MissingEnvError can be raised and carries the provided message."""
        from src.cotality.agent.agent import MissingEnvError

        with pytest.raises(MissingEnvError, match="ORG environment variable not set"):
            raise MissingEnvError("ORG environment variable not set")


@pytest.fixture()
def mock_agent_deps():
    """Patch all LLM construction in agent.py so no API calls are made."""
    with (
        patch("src.cotality.agent.agent.create_litellm_with_retry", return_value=MagicMock()),
        patch("src.cotality.agent.agent.LlmAgent", return_value=MagicMock()),
        patch("src.cotality.agent.agent.Agent", return_value=MagicMock()),
        patch("src.cotality.agent.agent.Runner", return_value=MagicMock()),
    ):
        yield


class TestMyAgentProperties:
    """Tests for MyAgent property accessors that do not require LLM calls."""

    @pytest.fixture()
    def agent(self, mock_agent_deps):
        """Return a MyAgent instance with mocked LLM dependencies."""
        from src.cotality.agent.agent import MyAgent

        return MyAgent()

    def test_get_agent_name_returns_greeting_agent(self, agent):
        """get_agent_name returns 'GreetingAgent'."""
        assert agent.get_agent_name() == "GreetingAgent"

    def test_agent_name_property_is_str(self, agent):
        """agent_name property returns a non-empty string."""
        name = agent.agent_name
        assert isinstance(name, str) and len(name) > 0

    def test_get_instruction_prompt_is_non_empty(self, agent):
        """get_instruction_prompt returns a non-empty string."""
        prompt = agent.get_instruction_prompt()
        assert isinstance(prompt, str) and len(prompt.strip()) > 0

    def test_get_processing_message_is_non_empty(self, agent):
        """get_processing_message returns a non-empty string."""
        msg = agent.get_processing_message()
        assert isinstance(msg, str) and len(msg) > 0

    def test_agent_property_not_none(self, agent):
        """agent property exposes the underlying LlmAgent."""
        assert agent.agent is not None

    def test_runner_property_not_none(self, agent):
        """runner property exposes the Runner instance."""
        assert agent.runner is not None

    @pytest.mark.parametrize("mime_type", ["text/plain", "application/json"])
    def test_supported_content_types_includes_common_mime(self, mime_type):
        """SUPPORTED_CONTENT_TYPES includes text/plain and application/json."""
        from src.cotality.agent.agent import MyAgent

        assert mime_type in MyAgent.SUPPORTED_CONTENT_TYPES


class TestMyAgentCard:
    """Tests for MyAgent.get_agent_card in local and non-local environments."""

    @pytest.fixture()
    def agent(self, mock_agent_deps):
        """Return a MyAgent instance with LLM/session construction mocked."""
        from src.cotality.agent.agent import MyAgent

        yield MyAgent()

    def test_local_env_returns_agent_card(self, agent):
        """get_agent_card returns an AgentCard object in local environment."""
        from a2a.types import AgentCard

        with patch.dict(os.environ, {"ENV": "local"}):
            card = agent.get_agent_card("localhost", 8000)
        assert isinstance(card, AgentCard)

    def test_local_env_card_url_contains_host_and_port(self, agent):
        """Agent card URL includes the supplied host and port for local env."""
        with patch.dict(os.environ, {"ENV": "local"}):
            card = agent.get_agent_card("localhost", 8000)
        card_url = card.supported_interfaces[0].url
        assert "localhost" in card_url
        assert "8000" in card_url

    def test_card_has_at_least_one_skill(self, agent):
        """Agent card must declare at least one skill."""
        with patch.dict(os.environ, {"ENV": "local"}):
            card = agent.get_agent_card("localhost", 8000)
        assert len(card.skills) > 0

    def test_card_name_is_non_empty(self, agent):
        """Agent card name is a non-empty string."""
        with patch.dict(os.environ, {"ENV": "local"}):
            card = agent.get_agent_card("localhost", 8000)
        assert card.name and len(card.name) > 0

    def test_non_local_env_raises_when_org_missing(self, agent):
        """get_agent_card raises MissingEnvError when ORG is absent in non-local env."""
        from src.cotality.agent.agent import MissingEnvError

        # Include ORG and APPLICATION_NAME in patch.dict so they are tracked and
        # restored on exit — keys deleted via os.environ.pop() inside the block
        # are only auto-restored if they appear in the patch.dict values dict.
        env_overrides = {"ENV": "uat", "ORG": "", "APPLICATION_NAME": ""}
        with patch.dict(os.environ, env_overrides):
            os.environ.pop("ORG", None)
            os.environ.pop("APPLICATION_NAME", None)
            with pytest.raises(MissingEnvError):
                agent.get_agent_card("0.0.0.0", 8000)
