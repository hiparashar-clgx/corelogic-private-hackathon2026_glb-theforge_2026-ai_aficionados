"""
This module defines the MyAgent, an AI agent built using the Google ADK.

The MyAgent is designed to interact with users by responding to greetings
using a simple tool. It demonstrates basic agent setup, including session
management and streaming responses.
"""

import contextlib
import os
from collections.abc import AsyncIterable
from typing import Any, ClassVar

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from a2a.utils.constants import TransportProtocol
from cotality_agent_sdk.config.litellm_retry import create_litellm_with_retry
from dotenv import load_dotenv
from google.adk.agents import Agent, LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext, agent_tool
from google.genai import types

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


class MissingEnvError(Exception):
    """Exception raised when a required environment variable is missing."""


# TODO: Rename class to reflect the actual name of the agent.
class MyAgent:
    """
    A basic agent for demonstration purposes, capable of greeting users.

    This agent utilizes the Google ADK to process user greetings and respond
    using the `say_hello` tool. It manages sessions and streams responses.

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
        self._agent_name: str = "GreetingAgent"
        self._user_id: str = "cotality_sample_agent"
        self._agent: LlmAgent = self._build_agent()
        self._runner: Runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def get_agent_card(self, host: str, port: int):
        capabilities = AgentCapabilities(streaming=True)
        skill = AgentSkill(
            id="greeting_skill",
            name="Greeting Assistant",
            description="Greets users by name with personalized welcome messages",
            tags=["greeting", "conversation", "social"],
            examples=["Say hello to John", "Greet Alice", "Welcome the new user Bob"],
        )

        if os.getenv("ENV") is None or os.getenv("ENV") == "local":
            agent_card_url = f"http://{host}:{port}/"
        else:
            org = os.getenv("ORG")
            app_name = os.getenv("APPLICATION_NAME")
            env = os.getenv("ENV")

            if org is None:
                raise MissingEnvError("ORG environment variable not set.")
            if app_name is None:
                raise MissingEnvError("APPLICATION_NAME environment variable not set.")
            if env is None:
                raise MissingEnvError("ENV environment variable not set.")

            agent_card_url = (
                "https://"
                + org.replace("_", "-")
                + "-"
                + app_name
                + ".cntvusw1"
                + env.split("-")[0]
                + ".solutions.corelogic.com"
            )

        agent_card = AgentCard(
            name="GreetingAgent",
            description=(
                "A conversational agent that provides personalized greetings, "
                "generates and explains code, and answers general knowledge questions. "
                "Use this agent when users need: (1) personalized welcome messages or greetings, "
                "(2) help writing, reviewing, or understanding code in various programming languages, "
                "or (3) answers to general knowledge questions across multiple domains. "
                "Ideal for onboarding interactions, code assistance, and general Q&A support."
            ),
            version="1.0.0",
            supported_interfaces=[
                AgentInterface(url=agent_card_url, protocol_binding=TransportProtocol.JSONRPC)
            ],
            default_input_modes=MyAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=MyAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )
        return agent_card

    def _get_tool_list(self):
        """
        Gathers list of tools from different agents and MCP servers.
        """
        code_agent = self._build_code_agent()
        general_agent = self._build_general_agent()

        # TODO Add MCP servers and additional agent tools needed for this agent
        return [
            ## Example Tool
            say_hello,
            ## Example Subagents
            agent_tool.AgentTool(agent=code_agent),
            agent_tool.AgentTool(agent=general_agent),
            ## Example A2A Connection
            # agent_tool.AgentTool(agent=RemoteA2aAgent(
            #     name="AgentExpert",
            #     timeout=6000,
            #     description="Real Estate Expert",
            #     agent_card=(
            #         "<AGENT_URL>/.well-known/agent-card.json"
            #     ))),
            ## Example MCP Connection
            # get_http_mcp_tool("<MCP_URL>/mcp/")
        ]

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
        You are a helpful agent. Answer all questions to the best of your ability even if you don't have a specific tool for it.
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
        Builds and configures the LlmAgent instance

        This method sets up the core LlmAgent with a specified model
        its name, a description, the instruction
        prompt, and the list of tools.

        Returns:
            An instance of LlmAgent configured for this agent.
        """

        # TODO Update agent parameters based upon specific requirements for the agent.
        return LlmAgent(
            # model="gemini-2.0-flash-001",
            # Retry configuration (defaults: num_retries=3, timeout=60)
            model=create_litellm_with_retry(
                model="openai/gemini-2.5-pro-llmservices-usw1",
                api_base=os.getenv("LITELLM_API_BASE"),
                api_key=os.getenv("LITELLM_API_KEY"),
            ),
            name=self.get_agent_name(),
            description=(
                "A conversational agent that provides personalized greetings, "
                "generates and explains code, and answers general knowledge questions."
            ),
            instruction=self.get_instruction_prompt(),
            tools=self._get_tool_list(),
        )

    def _build_search_agent(self) -> LlmAgent:
        """Builds the search agent."""
        return LlmAgent(
            # model="gemini-2.0-flash-001",
            model=create_litellm_with_retry(
                model="openai/gemini-2.5-pro-llmservices-usw1",
                api_base=os.getenv("LITELLM_API_BASE"),
                api_key=os.getenv("LITELLM_API_KEY"),
            ),
            name="search_agent",
            description="This agent can be used to search the web for information.",
            instruction="You are a search agent. You have general information about the world, and can answer questions to the best of your knowledge.",
        )

    def _build_code_agent(self) -> LlmAgent:
        """
        Builds the code agent. Note that this is just an example of a sub-agent.
        This sub agent does not execute code.
        """
        return Agent(
            # model='gemini-2.0-flash',
            model=create_litellm_with_retry(
                model="openai/gemini-2.5-pro-llmservices-usw1",
                api_base=os.getenv("LITELLM_API_BASE"),
                api_key=os.getenv("LITELLM_API_KEY"),
            ),
            name="CodeAgent",
            instruction="""
            You're a specialist in Code, when asked, you generate code, or explain code.
            """,
        )

    def _build_general_agent(self) -> LlmAgent:
        """
        Builds the general agent. Note that this is just an example of a sub-agent.
        """
        return Agent(
            model=create_litellm_with_retry(
                model="openai/gemini-2.5-flash-llmservices-usw1",
                api_base=os.getenv("LITELLM_API_BASE"),
                api_key=os.getenv("LITELLM_API_KEY"),
            ),
            name="GeneralAgent",
            instruction="""
            You're a generalist with knowledge in many areas, you can answer questions on a variety of topics.
            """,
        )

    def get_processing_message(self) -> str:
        """
        Returns a message indicating that the agent is processing a request.

        Returns:
            A string message, e.g., "processing message...".
        """
        return "processing message..."

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
                    yield {"is_task_complete": False, "updates": self.get_processing_message()}

    @property
    def agent(self) -> LlmAgent:
        """
        Provides access to the underlying LlmAgent instance.

        Returns:
            The LlmAgent instance configured for this MyAgent.
        """
        return self._agent

    @property
    def runner(self) -> Runner:
        """
        Provides access to the Runner instance.
        Returns:
            The Runner instance responsible for executing agent interactions.
        """
        return self._runner

    @property
    def agent_name(self) -> str:
        """
        Provides access to the agent's name.
        Returns:
            The name of the agent as a string.
        """
        return self._agent_name


# This exists solely for adk web testing.
# TODO Replace it with the actual agent implementation.
root_agent: LlmAgent = (MyAgent()).agent
