from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

# Registry for lifespan handlers
_lifespan_handlers: list[Callable[[Any], AbstractAsyncContextManager[None]]] = []


def register_lifespan(handler):
    """
    Decorator to register a lifespan handler.

    Handlers are executed in registration order during startup,
    and in reverse order during shutdown.

    Args:
        handler: An async context manager that handles app lifecycle.

    Returns:
        The handler (for use as a decorator).
    """
    _lifespan_handlers.append(handler)
    return handler


def get_lifespan_handlers():
    """Get all registered lifespan handlers."""
    return _lifespan_handlers
