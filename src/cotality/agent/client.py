import base64
import logging
import os
from typing import Any

import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.client.card_resolver import parse_agent_card
from a2a.helpers.proto_helpers import new_text_message
from a2a.types import AgentCard, Role, SendMessageRequest
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH, TransportProtocol
from dotenv import load_dotenv

load_dotenv()

# Agent URL - update for remote deployment (e.g., "https://org-agent-name.cntvusw1uat.solutions.corelogic.com")
AGENT_URL = "http://0.0.0.0:8000"

# Sample message to send to the agent
MESSAGE = "How many planets in the solar system?"
access_token = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  # Get a logger instance


class A2ASimpleClient:
    """
    This test client can be used to test A2A communication with a local or remote agent server.
    """

    def __init__(self, default_timeout: float = 240.0):
        """Initializes the A2ASimpleClient."""
        self._agent_info_cache: dict[str, dict[str, Any] | None] = {}  # Cache for agent metadata
        self.default_timeout = default_timeout

    async def create_task(self, agent_url: str, message: str) -> str:
        """
        Sends a message to the specified agent and returns the response.

        Args:
            agent_url (str): The URL of the agent to send the message to.
            message (str): The message to send.

        Returns:
            str: The agent's response or an error message.
        """
        # Configure httpx client with timeout
        timeout_config = httpx.Timeout(
            timeout=self.default_timeout,
            connect=10.0,
            read=self.default_timeout,
            write=10.0,
            pool=5.0,
        )

        # Optional: Add custom headers for distributed tracing
        # Example: headers = {"traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"}
        headers: dict[str, str] = {}

        async with httpx.AsyncClient(timeout=timeout_config, headers=headers) as httpx_client:
            # Check if we have cached agent card data
            if (
                agent_url in self._agent_info_cache
                and self._agent_info_cache[agent_url] is not None
            ):
                agent_card_data = self._agent_info_cache[agent_url]
            else:
                # Fetch the agent card
                logger.info("Attempting to fetch public agent card")
                agent_card_response = await httpx_client.get(
                    f"{agent_url}{AGENT_CARD_WELL_KNOWN_PATH}"
                )
                agent_card_data = self._agent_info_cache[agent_url] = agent_card_response.json()
                logger.info(agent_card_data)

            # Create AgentCard from data
            if agent_card_data is None:
                return "Error: No agent card data available"
            agent_card = parse_agent_card(agent_card_data)

            # Add auth to client
            # httpx_client.auth = AgentAuth(agent_card)

            # Create A2A client with the agent card
            config = ClientConfig(
                httpx_client=httpx_client,
                supported_protocol_bindings=[
                    TransportProtocol.JSONRPC,
                    TransportProtocol.HTTP_JSON,
                ],
                use_client_preference=True,
            )

            factory = ClientFactory(config)
            client = factory.create(agent_card)

            # Create the message object and wrap it in a SendMessageRequest
            message_obj = new_text_message(message, role=Role.ROLE_USER)
            send_request = SendMessageRequest(message=message_obj)

            # Send the message and collect responses
            responses = []
            logger.info(f"Sending message to agent: {message}")
            async for response in client.send_message(send_request):
                logger.info(f"Received response chunk: {response}")
                responses.append(response)

            # The response is a tuple - get the first element (Task object)
            if responses and isinstance(responses[0], tuple) and len(responses[0]) > 0:
                task = responses[0][0]  # First element of the tuple

                # Check for failed task status and surface the error message
                if hasattr(task, "status") and task.status and task.status.state.value == "failed":
                    error_msg = "Agent task failed"
                    if task.status.message and task.status.message.parts:
                        part_root = task.status.message.parts[0].root
                        if hasattr(part_root, "text"):
                            error_msg = part_root.text
                    return f"Error: {error_msg}"

                # Extract text: task.artifacts[0].parts[0].root.text
                try:
                    artifact_part = task.artifacts[0].parts[0].root  # type: ignore[index]
                    return artifact_part.text if hasattr(artifact_part, "text") else str(task)  # type: ignore[union-attr]
                except (AttributeError, IndexError, TypeError):
                    return str(task)

            return "No response received"


class AgentAuth(httpx.Auth):
    """
    OAuth2 authentication handler for httpx requests to A2A agents.
    Handles fetching and attaching access tokens using client credentials flow.
    """

    def __init__(self, agent_card: AgentCard):
        """Initializes the AgentAuth handler."""
        self.agent_card = agent_card
        self._access_token: str | None = None

    async def _get_client_credentials_token(self) -> str:
        """
        Fetches an OAuth2 access token using the client credentials flow.

        Returns:
            str: The access token.
        """
        token_url = os.getenv("A2A_CLIENT_AUTH0_TOKEN_URL")
        client_id = os.getenv("A2A_CLIENT_AUTH0_CLIENT_ID", "")
        client_secret = os.getenv("A2A_CLIENT_AUTH0_CLIENT_SECRET", "")

        payload = {
            "grant_type": "client_credentials",
            "audience": os.getenv("AGENT_AUTH0_AUDIENCE"),
        }

        # Prep the Auth header
        auth_string = f"{client_id}:{client_secret}"
        encoded_auth_bytes = base64.b64encode(auth_string.encode("utf-8"))
        encoded_auth_string = encoded_auth_bytes.decode("utf-8")
        headers = {
            "Authorization": f"Basic {encoded_auth_string}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        if not token_url:
            raise ValueError("A2A_CLIENT_AUTH0_TOKEN_URL environment variable not set.")

        logger.info(f"Fetching access token from {token_url}...")
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=payload, headers=headers)
            response.raise_for_status()
            token_data = response.json()
        if "access_token" not in token_data:
            raise ValueError("'access_token' not found in the response from token endpoint.")
        logger.info("Successfully fetched access token.")
        return str(token_data["access_token"])

    async def async_auth_flow(self, request):
        """
        Attaches the access token to the Authorization header of the request.

        Args:
            request: The outgoing HTTP request.

        Yields:
            The authenticated HTTP request.
        """
        # Fetch token only if we don't have one already
        if not self._access_token:
            try:
                self._access_token = await self._get_client_credentials_token()
            except (ValueError, httpx.HTTPStatusError) as e:
                logger.error(f"Failed to retrieve access token: {e}")
                # Yield the original request without auth so the flow can continue
                # and the server can return a proper "unauthorized" error.
                yield request
                return
        request.headers["Authorization"] = f"Bearer {self._access_token}"
        yield request


async def main() -> None:
    """
    Initializes the A2A client, sends a sample message to the agent,
    and prints the response.
    """
    a2a_client = A2ASimpleClient()
    response = await a2a_client.create_task(AGENT_URL, MESSAGE)
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
