import logging
import os
from contextlib import AsyncExitStack, asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

import sys

import click
import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from cotality_agent_sdk.lifespans import tracing_lifespan
from cotality_agent_sdk.observability.tracing import instrument_starlette_app
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from starlette.applications import Starlette
from starlette.responses import JSONResponse

from src.cotality.agent.agent import MyAgent
from src.cotality.agent.utils.lifespan_registry import get_lifespan_handlers, register_lifespan
from src.cotality.agent.utils.oauth2_middleware import OAuth2Middleware

logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception raised when the required API key environment variable is missing."""


class MissingEnvError(Exception):
    """Exception raised when a required environment variable is missing."""


async def health_check(request):
    """
    Handles GET requests for server health checks.

    Args:
        request: The incoming HTTP request object.

    Returns:
        A simple JSON response indicating that the server status is healthy.
    """
    return JSONResponse({"status": "ok"})


@asynccontextmanager
async def lifespan(app: Starlette):
    """
    Manages the application lifespan (startup and shutdown events).

    Composes all registered lifespan handlers.
    Startup occurs in registration order, shutdown in reverse order.

    Args:
        app: The Starlette application instance.
    """
    async with AsyncExitStack() as stack:
        for handler in get_lifespan_handlers():
            await stack.enter_async_context(handler(app))
        logger.info("Application started successfully")
        yield
        logger.info("Application shutting down...")


@click.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=8000)
def main(host: str, port: int):
    """
    Entry point for starting the agent server.
    Builds a Starlette server that compliant with A2A protocol, using the agent card from your MyAgent class in agent.py
    Auth middleware, logging middleware, and a health check endpoint are included in the server.

    For local environments, starts the server on the specified local host and port.
    For non-local environments, starts the server at https://<ORG>-<AGENT-NAME>.cntvusw1<ENV>.solutions.corelogic.com

    The server will expose the agent card at <AGENT-URL>/.well-known/agent-card.json

    Args:
        host: Host address to bind the server.
        port: Port number to bind the server.
    """
    try:
        if os.getenv("LITELLM_API_KEY") is None:
            raise MissingAPIKeyError("LITELLM_API_KEY environment variable not set.")

        if os.getenv("LITELLM_API_BASE") is None:
            raise MissingAPIKeyError("LITELLM_API_BASE environment variable not set.")
        agent = MyAgent()
        task_store = InMemoryTaskStore()
        agent_card = agent.get_agent_card(host, port)
        request_handler = DefaultRequestHandler(
            agent_executor=A2aAgentExecutor(runner=agent.runner),
            task_store=task_store,
            agent_card=agent_card,
        )

        app = Starlette(lifespan=lifespan)
        app.routes.extend(
            [
                *create_agent_card_routes(agent_card, card_url=AGENT_CARD_WELL_KNOWN_PATH),
                *create_jsonrpc_routes(request_handler, "/"),
            ]
        )
        instrument_starlette_app(app)

        # Register lifespans
        register_lifespan(tracing_lifespan)

        app.add_route("/health", health_check, methods=["GET"])
        app.add_middleware(OAuth2Middleware)

        uvicorn.run(app, host=host, port=port)

    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except (OSError, RuntimeError, ValueError, TypeError) as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
