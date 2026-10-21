"""
This module defines the MyAgent, an AI agent built using the Google ADK.

The MyAgent is designed to interact with users by responding to greetings
using a simple tool. It demonstrates basic agent setup, including session
management and streaming responses.
"""

import base64
import os
from collections.abc import AsyncIterable
from typing import Any, ClassVar

from dotenv import load_dotenv
from google.adk.agents import Agent, LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext, agent_tool
from google.genai import types

from .utils.mcp_tools import get_sse_mcp_tool

load_dotenv()


def say_hello(name: str, tool_context: ToolContext) -> str:
    """
    Greets the given name.

    Args:
        name: The name of the person to greet.
        tool_context: The context for the tool, providing access to shared
            resources or configurations if needed. Not used in this simple tool.

    Returns:
        A greeting string, e.g., "Hello, {name}!".
    """
    return f"Hello, {name}!"


# TODO: Rename class to reflect the actual name of the agent.
class MyAgent:
    """
    A basic agent for demonstration purposes, capable of greeting users.

    This agent utilizes the Google ADK to process user greetings and respond
    using the `say_hello` tool. It manages sessions and streams responses. Using
    sub-agents, it can also perform web searches and execute code.

    Attributes:
        SUPPORTED_CONTENT_TYPES: A list of MIME types supported for user input.
        _agent_name: The name assigned to this agent.
        _user_id: A default user identifier for agent sessions.
        _agent: The underlying LlmAgent instance from Google ADK.
        _runner: The Runner instance responsible for executing agent interactions.
    """

    # TODO: Update class docstring with appropriate description for this agent.

    SUPPORTED_CONTENT_TYPES: ClassVar[list[str]] = [
        "text/plain",
        "application/json",
    ]  # TODO: Update supported content types with the actual supported content types of the agent.

    def __init__(self) -> None:
        """
        Initializes the MyAgent.

        Sets up the agent's name, a default user ID, and constructs the
        LlmAgent and Runner instances with in-memory services for artifacts,
        sessions, and memory management.
        """
        self._agent_name: str = "MyAgent"
        self._user_id: str = "cotality_sample_agent"
        self._agent: LlmAgent = self._build_agent()
        self._runner: Runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def get_processing_message(self) -> str:
        """
        Returns a message indicating that the agent is processing a request.

        Returns:
            A string message, e.g., "processing message...".
        """
        return "processing message..."

    def get_instruction_prompt(self) -> str:
        """
        Returns the instruction prompt for the LlmAgent.

        This prompt guides the language model on its role, capabilities,
        and how to use available tools. It specifies using "User" as a
        default name if none is provided and directs the use of the
        `say_hello` function for greetings.

        Returns:
            A string containing the instruction prompt.
        """
        # TODO Update the instruction prompt with appropriate instructions for the agent.
        return """
        You are a sample agent.
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
        Builds and configures the LlmAgent instance, as well as a search agent.

        This method sets up the core LlmAgent with a specified model
        (gemini-2.0-flash-001), its name, a description, the instruction
        prompt, and the list of tools.

        Returns:
            An instance of LlmAgent configured for this agent.
        """

        # TODO Update agent parameters based upon specific requirements for the agent.
        return LlmAgent(
            # model="gemini-2.0-flash-001",
            model=LiteLlm(
                model="openai/gemini-2.5-pro-litellm-usw1",
                api_base=os.getenv("LITELLM_API_BASE"),
                api_key=os.getenv("LITELLM_API_KEY"),
            ),
            name=self.get_agent_name(),
            description="A sample agent for demonstration purposes.",
            instruction=self.get_instruction_prompt(),
            tools=self._get_tool_list(),
        )

    def _get_tool_list(self):
        """
        Gathers list of tools from different agents and MCP servers.
        Adds the say_hello tool, search agent, and code agent to the agent tools.
        """
        if os.getenv("BASIC_AUTH_SCHEME") == "True":
            client_id = os.getenv("A2A_CLIENT_AUTH0_CLIENT_ID")
            client_secret = os.getenv("A2A_CLIENT_AUTH0_CLIENT_SECRET")

            auth_string = f"{client_id}:{client_secret}"
            encoded_auth_bytes = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
            headers = {
                "Authorization": f"Basic {encoded_auth_bytes}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        elif os.getenv("BASIC_AUTH_SCHEME") == "False":
            # TODO: Input the URL of a running MCP server
            secret = os.getenv("AGENT_TO_MCP_TOKEN")

            auth_string = f"{secret}"
            # encoded_auth_bytes = base64.b64encode(auth_string.encode("utf-8"))
            headers = {
                "Authorization": f"Bearer {auth_string}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
        else:
            # token_url = os.getenv("A2A_CLIENT_AUTH0_TOKEN_URL")
            client_id = os.getenv("A2A_CLIENT_AUTH0_CLIENT_ID")
            client_secret = os.getenv("A2A_CLIENT_AUTH0_CLIENT_SECRET")

            # payload = {
            #     "grant_type": "client_credentials",
            #     "audience": os.getenv("AGENT_AUTH0_AUDIENCE")
            # }

            # Prep the Auth header
            auth_string = f"{client_id}:{client_secret}"
            encoded_auth_bytes = base64.b64encode(auth_string.encode("utf-8"))
            # encoded_auth_string = encoded_auth_bytes.decode("utf-8")
            headers = {
                "Authorization": f"Basic {encoded_auth_bytes}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            # logger.info(f"Fetching access token from {token_url}...")
            # async with httpx.AsyncClient() as client:
            #    response = await client.post(token_url, data=payload, headers=headers)
            #    response.raise_for_status()
            #    token_data = response.json()
            # if "access_token" not in token_data:
            #    raise ValueError("'access_token' not found in the response from token endpoint.")
            print("RETRIEVING TOOL LIST")
        search_agent = self._build_search_agent()
        code_agent = self._build_code_agent()

        # TODO Add MCP servers and additional agent tools needed for this agent
        return [
            ## Example Tool
            say_hello,
            ## Example Subagents
            agent_tool.AgentTool(agent=search_agent),
            agent_tool.AgentTool(agent=code_agent),
            ## Example A2A Connection
            # agent_tool.AgentTool(agent=RemoteA2aAgent(
            #     name="AgentExpert",
            #     description="Real Estate Expert",
            #     agent_card=(
            #         "<AGENT_URL>/.well-known/agent-card.json"
            #     ))),
            ## Example MCP Connection
            get_sse_mcp_tool("http://localhost:8001/sse", headers=headers),
        ]

    def _build_search_agent(self) -> LlmAgent:
        """Builds the search agent."""
        return LlmAgent(
            # model="gemini-2.0-flash-001",
            model=LiteLlm(
                model="openai/gemini-2.5-pro-litellm-usw1",
                api_base=os.getenv("LITELLM_API_BASE"),
                api_key=os.getenv("LITELLM_API_KEY"),
            ),
            name="search_agent",
            description="This agent can be used to search the web for information.",
            instruction="You are a search agent. You have general information about the world, and can answer questions to the best of your knowledge.",
        )

    def _build_code_agent(self) -> LlmAgent:
        """Builds the code agent."""
        return Agent(
            # model='gemini-2.0-flash',
            model=LiteLlm(
                model="openai/gemini-2.5-pro-litellm-usw1",
                api_base=os.getenv("LITELLM_API_BASE"),
                api_key=os.getenv("LITELLM_API_KEY"),
            ),
            name="CodeAgent",
            instruction="""
            You're a specialist in Code Execution, when asked, you generate code, or explain code.
            You can execute code, and return the result.
            """,
        )

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
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                response = ""
                if event.content and event.content.parts and event.content.parts[0].text:
                    response = "\n".join([p.text for p in event.content.parts if p.text])
                elif (
                    event.content
                    and event.content.parts
                    and any(True for p in event.content.parts if p.function_response)
                ):
                    # Extracts response from a function call
                    response_part = next(
                        (p.function_response for p in event.content.parts if p.function_response),
                        None,
                    )
                    if response_part:
                        response = response_part.model_dump_json()
                yield {"is_task_complete": True, "content": response}
            else:
                yield {"is_task_complete": False, "updates": self.get_processing_message()}

    @property
    def agent(self) -> LlmAgent:
        """
        Provides access to the underlying LlmAgent instance.

        Returns:
            The LlmAgent instance configured for this MyAgent.
        """
        return self._agent


# This exists solely for adk web testing.
# TODO Replace it with the actual agent implementation.
root_agent: LlmAgent = (MyAgent()).agent
