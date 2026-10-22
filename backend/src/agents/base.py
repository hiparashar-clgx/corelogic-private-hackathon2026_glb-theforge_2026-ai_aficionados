"""Shared helpers for building Google ADK agents backed by Gemini.

Every agent in this system is a `google.adk.agents.Agent` configured either with a direct Gemini
model name or a LiteLLM model routed through a configured proxy, run through ADK's `Runner` +
`InMemorySessionService` for a single request/response turn.
Tool-calling (external literature search, similarity lookups, etc.) is wired in via each agent's
`tools=[...]` list, per research.md "Agent Orchestration Approach".
"""
import asyncio
from collections.abc import Callable
from typing import Any

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from src.config import get_settings


class AgentUnavailableError(Exception):
    """Raised when Gemini remains temporarily unavailable after bounded retries."""


class AgentQuotaExceededError(Exception):
    """Raised when the configured Gemini project has exhausted its request quota."""


def build_agent(*, name: str, instruction: str, tools: list[Callable[..., Any]] | None = None) -> Agent:
    """Construct an ADK agent using direct Gemini or the configured LiteLLM proxy."""
    settings = get_settings()
    if settings.litellm_api_key:
        if not settings.litellm_base_url:
            raise ValueError("LITELLM_BASE_URL is required when LITELLM_API_KEY is configured.")
        from google.adk.models.lite_llm import LiteLlm

        model = LiteLlm(
            model=settings.litellm_model,
            api_key=settings.litellm_api_key,
            api_base=settings.litellm_base_url,
        )
    else:
        if not settings.google_api_key:
            raise ValueError(
                "No model API key is configured. Set LITELLM_API_KEY and LITELLM_BASE_URL "
                "for the LiteLLM proxy, or set GOOGLE_API_KEY for direct Gemini access."
            )
        model = settings.gemini_model
    return Agent(
        name=name,
        model=model,
        instruction=instruction,
        tools=tools or [],
    )


async def run_agent_turn(agent: Agent, *, user_id: str, session_id: str, message: str) -> str:
    """Run a single request/response turn against an ADK agent and return the concatenated text."""
    runner = InMemoryRunner(agent=agent, app_name=agent.name)
    await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )

    content = genai_types.Content(role="user", parts=[genai_types.Part(text=message)])
    output_text = ""
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    output_text += part.text
    return output_text


async def run_agent_turn_with_retry(
    agent: Agent, *, user_id: str, session_id: str, message: str, max_retries: int = 2
) -> str:
    """Retry transient Gemini unavailability without hiding permanent agent errors."""
    for attempt in range(max_retries + 1):
        try:
            return await run_agent_turn(agent, user_id=user_id, session_id=session_id, message=message)
        except Exception as exc:
            quota_exhausted = type(exc).__name__ in {"ResourceExhaustedError", "_ResourceExhaustedError"} or any(
                marker in str(exc).upper() for marker in ("429", "RESOURCE_EXHAUSTED", "QUOTA EXCEEDED")
            )
            if quota_exhausted:
                raise AgentQuotaExceededError(
                    "The configured model provider quota is exhausted or rate-limited. Wait and retry, or check the provider's account limits."
                ) from exc
            transient = type(exc).__name__ in {"ServiceUnavailableError", "ServerError"} or any(
                marker in str(exc).upper() for marker in ("503", "UNAVAILABLE")
            )
            if not transient:
                raise
            if attempt == max_retries:
                raise AgentUnavailableError(
                    "The configured model provider is temporarily unavailable. Please retry this section in a moment."
                ) from exc
            await asyncio.sleep(1 << attempt)
