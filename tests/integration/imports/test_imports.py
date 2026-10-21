"""Verify all application modules can be imported without errors.

Catches broken import paths, missing dependencies, and circular imports
by actually importing each module at test time.
"""

import importlib

import pytest

MODULES = [
    "src.cotality.agent.agent",
    "src.cotality.agent.server",
    "src.cotality.agent.fastapi_server",
    "src.cotality.agent.client",
    "src.cotality.agent.utils.mcp_tools",
    "src.cotality.agent.utils.oauth2_middleware",
    "src.cotality.agent.utils.lifespan_registry",
]


@pytest.mark.parametrize("module_path", MODULES, ids=lambda m: m.rsplit(".", 1)[-1])
def test_module_imports(module_path: str):
    """Each source module should import without raising.

    Args:
        module_path: Fully qualified dotted module path to import.
    """
    importlib.import_module(module_path)
