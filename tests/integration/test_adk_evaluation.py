"""Agent evaluation tests, wired to the internal cotality-agent-eval-sdk.

These tests run through the Cotality evaluation harness (instead of the native
ADK `AgentEvaluator`) so results get standardized Cotality reporting and,
once configured, automatic GCS publishing. See
configs/evaluation/evaluation_config.local.yaml for the harness configuration
and tests/integration/test_config.json for the evaluation criteria/thresholds.
"""

import os
from pathlib import Path

import pytest
from cotality_agent_eval_sdk import evaluation_test

EVALSET_FILES = [str(p) for p in sorted(Path(__file__).parent.glob("*.evalset.json"))]

# These tests make real LLM calls, so they require LiteLLM credentials to be
# configured (see the "Adding Secrets or Environment Specific Variables"
# section of README.md). Skip rather than fail when they're absent, e.g. in
# this template's own CI, which has no real credentials wired up.
requires_litellm_credentials = pytest.mark.skipif(
    not os.getenv("LITELLM_API_KEY"),
    reason="LITELLM_API_KEY is not set; skipping evaluation tests that call the LLM.",
)


@requires_litellm_credentials
@pytest.mark.asyncio
@pytest.mark.parametrize("evalset_file", EVALSET_FILES)
@evaluation_test(
    metrics_to_check=[
        {"name": "tool_trajectory_avg_score", "threshold": 1.0},
        {"name": "response_match_score", "threshold": 0.8},
    ]
)
async def test_with_single_test_file(evalset_file, evaluator_wrapper, test_results):
    """Test the agent's basic ability via each evalset file in tests/integration/."""
