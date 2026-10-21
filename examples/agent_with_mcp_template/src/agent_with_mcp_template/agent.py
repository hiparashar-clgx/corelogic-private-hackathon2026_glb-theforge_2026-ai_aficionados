"""
This module defines the McpTemplateAgent, an AI agent built using the Google ADK.
It demonstrates the ability to interact with remotely-deployed MCP servers.
"""

import contextlib
import os
from collections.abc import AsyncIterable
from typing import Any, ClassVar

from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .utils.mcp_tools import get_http_mcp_tool


class McpTemplateAgent:
    """
    A basic agent for demonstration purposes.

    This agent utilizes the Google ADK MCP tools to connect to a local MCP server.
    It manages sessions and streams responses.

    Attributes:
        SUPPORTED_CONTENT_TYPES: A list of MIME types supported for user input.
        _agent_name: The name assigned to this agent.
        _user_id: A default user identifier for agent sessions.
        _agent: The underlying LlmAgent instance from Google ADK.
        _runner: The Runner instance responsible for executing agent interactions.
    """

    SUPPORTED_CONTENT_TYPES: ClassVar[list[str]] = ["text/plain", "application/json"]

    def __init__(self) -> None:
        """
        Initializes the McpTemplateAgen.

        Sets up the agent's name, a default user ID, and constructs the
        LlmAgent and Runner instances with in-memory services for artifacts,
        sessions, and memory management.
        """
        self._agent_name: str = "McpTemplateAgent"
        self._user_id: str = "cotality_sample_agent"
        self._agent: LlmAgent = self._build_agent()
        self._runner: Runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def get_instruction_prompt(self) -> str:
        """
        Returns the instruction prompt for the LlmAgent.

        This prompt guides the language model on its role, capabilities,
        and how to use available tools.

        Returns:
            A string containing the instruction prompt.
        """
        return """
        You are a cotality sample agent.

        If asked any prompt, echo the prompt back using the `echo` tool provided by the MCP server.
         """

    def get_agent_name(self) -> str:
        """
        Returns the name of the agent.

        Returns:
            The agent's name as a string.
        """
        return str(self._agent_name)

    def _build_agent(self) -> LlmAgent:
        """
        Builds and configures the LlmAgent instance.

        This method sets up the core LlmAgent with a specified model
        (gemini-2.0-flash-001), its name, a description, the instruction
        prompt, and the list of tools.

        Returns:
            An instance of LlmAgent configured for this agent.
        """

        # TODO Update agent parameters based upon specific requirements for the agent.
        return LlmAgent(
            model=LiteLlm(
                # Update model based on access level - see /models endpoint at https://llm-uat.cotality.com/
                model="openai/gemini-2.5-pro-litellm-usw1",
                api_base=os.getenv("LITELLM_API_BASE"),
                api_key=os.getenv("LITELLM_API_KEY"),
                # For retry support, use cotality_agent_sdk.create_litellm_with_retry instead
            ),
            name=self.get_agent_name(),
            description="A sample agent for demonstration purposes.",
            instruction=self.get_instruction_prompt(),
            tools=self._get_tool_list(),
        )

    def _get_tool_list(self):
        """
        Gathers list of tools from different agents and MCP servers.
        Adds the MCP tool to the agent tool list.
        """

        # TODO: Input the URL of a running MCP server
        return [
            get_http_mcp_tool(
                "https://idap-agents-glb-mcp-template-base.cntvusw1uat.solutions.corelogic.com/mcp"
            )
            # To connect to a local MCP (SSE) running on port 8001
            # get_sse_mcp_tool('http://localhost:8001/sse')
        ]

    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        """
        Processes a user query and streams responses back asynchronously.

        This method handles an incoming user query within a given session.
        It retrieves or creates a session, then uses the ADK Runner to process
        the query with the LlmAgent. It yields events from the agent,
        distinguishing between final responses and intermediate updates.

        Args:
            query: The user's input string.
            session_id: The identifier for the current conversation session.

        Yields:
            Dictionaries representing events from the agent.
            A final event will have `is_task_complete: True` and the agent's
            `content` response. Intermediate events will have
            `is_task_complete: False` and an `updates` message.
        """
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name, user_id=self._user_id, session_id=session_id
        )
        content = types.Content(role="user", parts=[types.Part.from_text(text=query)])
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name, user_id=self._user_id, state={}, session_id=session_id
            )

        # Start Agent Execution Stream
        agent_generator = self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        )

        # Asynchronous Generator Context Management
        # Using aclosing prevents asynchronous context corruption errors
        # by guaranteeing the generator's cleanup runs in the correct execution context upon exiting the loop.
        async with contextlib.aclosing(agent_generator):
            # Process Events
            async for event in agent_generator:
                # Check for Final Response
                if event.is_final_response():
                    response = ""
                    # Extract Text Content
                    if event.content and event.content.parts and event.content.parts[0].text:
                        response = "\n".join([p.text for p in event.content.parts if p.text])
                    # Extract Structured Function/Tool Output
                    elif (
                        event.content
                        and event.content.parts
                        and any(True for p in event.content.parts if p.function_response)
                    ):
                        # Extracts response from a function call
                        response_part = next(
                            (
                                p.function_response
                                for p in event.content.parts
                                if p.function_response
                            ),
                            None,
                        )
                        if response_part:
                            response = response_part.model_dump_json()
                    # Yield Final Payload
                    yield {"is_task_complete": True, "content": response}
                    # Immediate Exit
                    return
                # Yield Status Updates
                else:
                    yield {"is_task_complete": False, "updates": "processing message..."}

    @property
    def agent(self) -> LlmAgent:
        """
        Provides access to the underlying LlmAgent instance.

        Returns:
            The LlmAgent instance configured for this McpTemplateAgent.
        """
        return self._agent


# This exists solely for adk web testing.
root_agent: LlmAgent = (McpTemplateAgent()).agent
