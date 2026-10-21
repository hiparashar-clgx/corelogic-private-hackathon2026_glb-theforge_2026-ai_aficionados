"""Configuration for pytest agent card validation tests."""

import os

import pytest


@pytest.fixture
def agent_configs() -> list[dict[str, str]]:
    """Get the list of agent configurations for validation tests.

    This fixture provides agent configurations dynamically based on environment variables.

    **DEFAULT BEHAVIOR:** Uses local agent card (no server required).

    Environment variables:
    - USE_LOCAL_AGENT_CARD (optional, default="true"): Set to "false" to use remote agents
    - AGENT_URL (required only if USE_LOCAL_AGENT_CARD=false): URL of the primary agent
    - ADDITIONAL_AGENT_URLS (optional): Comma-separated list of additional agent URLs
      for portfolio coherence tests

    The default behavior makes the template pass tests out of the box without needing
    to start a server. The tests import MyAgent from src.cotality.agent.agent and use
    its get_agent_card() method.

    Example usage:
        # Default: Local agent card (no environment variables needed!)
        # Just run: pytest tests/integration/agent_card/

        # Explicit local mode
        export USE_LOCAL_AGENT_CARD=true

        # Remote agent mode
        export USE_LOCAL_AGENT_CARD=false
        export AGENT_URL=http://localhost:8000

        # Multiple remote agents (full portfolio validation)
        export USE_LOCAL_AGENT_CARD=false
        export AGENT_URL=http://localhost:8000
        export ADDITIONAL_AGENT_URLS=http://agent2:8000,http://agent3:8000

        # Mixed: local primary + remote agents for portfolio testing
        export USE_LOCAL_AGENT_CARD=true
        export ADDITIONAL_AGENT_URLS=http://agent2:8000

    For production use with multiple known agents, you can override this fixture
    in your project's conftest.py with a hardcoded list:

        AGENT_CONFIGS = [
            {"name": "documentation_agent", "env_var": "DOCUMENTATION_AGENT_URL"},
            {"name": "search_agent", "env_var": "SEARCH_AGENT_URL"},
        ]

        @pytest.fixture
        def agent_configs():
            return AGENT_CONFIGS

    Returns:
        List of dicts with 'name' and 'env_var' keys for each agent.
    """
    configs = []

    # Check if using local agent card (default to true for template)
    use_local = os.getenv("USE_LOCAL_AGENT_CARD", "true").lower() == "true"

    if use_local:
        # Use local agent card - set env var to "local" as a special marker
        local_env_var = "LOCAL_AGENT_CARD"
        os.environ[local_env_var] = "local"
        configs.append({"name": "local_agent", "env_var": local_env_var})
    else:
        # Primary agent (required for description quality tests)
        primary_url_var = "AGENT_URL"
        if os.getenv(primary_url_var):
            configs.append({"name": "primary_agent", "env_var": primary_url_var})

    # Additional agents for portfolio coherence tests (optional)
    additional_urls_str = os.getenv("ADDITIONAL_AGENT_URLS", "")
    if additional_urls_str:
        additional_urls = [url.strip() for url in additional_urls_str.split(",") if url.strip()]
        for idx, url in enumerate(additional_urls):
            env_var = f"ADDITIONAL_AGENT_URL_{idx + 1}"
            os.environ[env_var] = url
            configs.append({"name": f"agent_{idx + 2}", "env_var": env_var})

    return configs
