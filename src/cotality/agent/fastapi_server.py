import logging
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager

import structlog
import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from cotality_agent_sdk import CotalityAgentExecutor
from cotality_agent_sdk.lifespans import tracing_lifespan
from cotality_agent_sdk.observability import instrument_fastapi_app
from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

from src.cotality.agent.agent import MyAgent
from src.cotality.agent.utils.lifespan_registry import get_lifespan_handlers, register_lifespan
from src.cotality.agent.utils.oauth2_middleware import OAuth2Middleware

load_dotenv()

# =============================================================================
# Configure telemetry FIRST - before logging.basicConfig()
# This ensures LoggingInstrumentor can set the trace context format
# =============================================================================

logger = logging.getLogger(__name__)
struct_logger = structlog.get_logger()


class MissingAPIKeyError(Exception):
    """Exception raised when the required API key environment variable is missing."""


# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Example allowed origins for CORS
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application lifespan (startup and shutdown events).

    Composes all registered lifespan handlers.
    Startup occurs in registration order, shutdown in reverse order.

    Args:
        app: The FastAPI application instance.
    """
    async with AsyncExitStack() as stack:
        for handler in get_lifespan_handlers():
            await stack.enter_async_context(handler(app))
        logger.info("Application started successfully")
        yield
        logger.info("Application shutting down...")


# Register the tracing lifespan
register_lifespan(tracing_lifespan)


# Call the function to get the FastAPI app instance
# Ensure the agent directory name ('capital_agent') matches your agent folder
# Use in-memory services to avoid filesystem operations (required for GKE deployment)
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
    lifespan=lifespan,
    session_service_uri="sqlite+aiosqlite:///:memory:",
    artifact_service_uri="memory://",
)
instrument_fastapi_app(app)

# IMPORTANT: Add middleware BEFORE routes are added and AFTER app creation
# This ensures middleware wraps all request handlers including routes added later
app.add_middleware(OAuth2Middleware)

# Create A2A agent components - BEFORE mounting routes
agent = MyAgent()
agent_card = agent.get_agent_card("0.0.0.0", 8000)
request_handler = DefaultRequestHandler(
    agent_executor=CotalityAgentExecutor(agent),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)

# Mount A2A routes into the main FastAPI app LAST
# This ensures routes are added after middleware and instrumentation
add_a2a_routes_to_fastapi(
    app,
    agent_card_routes=create_agent_card_routes(agent_card, card_url=AGENT_CARD_WELL_KNOWN_PATH),
    jsonrpc_routes=create_jsonrpc_routes(request_handler, "/"),
)


@app.get("/health")
async def health_check():
    """
    Handles GET requests for server health checks.

    Returns:
        A simple JSON response indicating that the server status is healthy.
    """
    return {"status": "ok"}


def main():
    """
    Entry point for starting the agent server.
    Starts a FastAPI server with Google ADK and A2A protocol support.
    The agent card from MyAgent class in agent.py is integrated via A2A routes.
    OAuth2 middleware, logging middleware, and a health check endpoint are included in the server.

    For local environments, it starts the server on the specified local host and port.
    For non-local environments, it starts the server at https://<ORG>-<AGENT-NAME>.cntvusw1<ENV>.solutions.corelogic.com

    The server will expose the agent card at <AGENT-URL>/.well-known/agent-card.json
    """
    try:
        if os.getenv("LITELLM_API_KEY") is None:
            raise MissingAPIKeyError("LITELLM_API_KEY environment variable not set.")

        if os.getenv("LITELLM_API_BASE") is None:
            raise MissingAPIKeyError("LITELLM_API_BASE environment variable not set.")

        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))

    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except (OSError, RuntimeError, ValueError, TypeError) as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
