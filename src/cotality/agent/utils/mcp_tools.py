import os
import sys

from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    SseConnectionParams,
    StdioConnectionParams,
    StdioServerParameters,
    StreamableHTTPConnectionParams,
)


def get_local_mcp_tool(
    local_path: str,
    *args,
    python_command: str = sys.executable,
    timeout: float = 60.0,
    tool_filter: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> MCPToolset:
    """
    Returns a MCPToolset used for setting up a connection to a local Python MCP server
    via standard input/output (stdio) transport.

    Args:
        local_path: Absolute path to server.py or main file of MCP server on local machine
        python_command: [Optional] Absolute path to python executable of venv. Uses sys.executable by default
        timeout: [Optional] Timeout for the connection to the MCP server
        tool_filter: [Optional] Filter on list of tools to be registered with the MCP server
        env: [Optional] Environment variables to pass to the subprocess. Uses current process environment by default
        args: [Optional] Additional arguments to be passed to the CLI command

    Returns:
        MCPToolset to be added to the agent tool list
    """
    subprocess_env = dict(os.environ) if env is None else dict(env)
    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=python_command, args=[local_path, *args], env=subprocess_env
            ),
            timeout=timeout,
        ),
        tool_filter=tool_filter,
    )


def get_sse_mcp_tool(
    url: str, timeout: float = 60.0, tool_filter: list[str] | None = None, headers=None
) -> MCPToolset:
    """
    Returns a MCPToolset used for setting up a connection to a remote Python MCP server
    via Server-Side Events (SSE) transport.

    Args:
        url: URL of running MCP server
        timeout: [Optional] Timeout for the connection to the MCP server
        tool_filter: [Optional] Filter on list of tools to be registered with the MCP server
        headers: [Optional] Additional headers to be passed to the connection request

    Returns:
        MCPToolset to be added to the agent tool list
    """
    if headers is None:
        headers = {"Accept": "text/event-stream"}
    return MCPToolset(
        connection_params=SseConnectionParams(
            url=url, headers=headers, timeout=timeout, sse_read_timeout=60 * timeout
        ),
        tool_filter=tool_filter,
    )


def get_http_mcp_tool(
    url: str, timeout: float = 60.0, tool_filter: list[str] | None = None, headers=None
) -> MCPToolset:
    """
    Returns a MCPToolset used for setting up a connection to a remote Python MCP server
    via Streamable HTTP transport.

    Args:
        url: URL of running MCP server
        timeout: [Optional] Timeout for the connection to the MCP server
        tool_filter: [Optional] Filter on list of tools to be registered with the MCP server
        headers: [Optional] Additional headers to be passed to the connection request

    Returns:
        MCPToolset to be added to the agent tool list
    """
    if headers is None:
        headers = {}
    return MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=url, headers=headers, timeout=timeout, sse_read_timeout=60 * timeout
        ),
        tool_filter=tool_filter,
    )


def get_npx_mcp_tool(
    package_name: str,
    *args,
    timeout: float = 60.0,
    tool_filter: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> MCPToolset:
    """
    Returns a MCPToolset used for setting up a connection to a reference MCP server
    via standard input/output (stdio) transport. MCP server package is downloaded through npx.

    Args:
        package_name: Name of npx package e.g. "@modelcontextprotocol/server-filesystem"
        timeout: [Optional] Timeout for the connection to the MCP server
        tool_filter: [Optional] Filter on list of tools to be registered with the MCP server
        env: [Optional] Environment variables to pass to the subprocess. Uses current process environment by default
        args: [Optional] Additional arguments to be passed to the CLI command

    Returns:
        MCPToolset to be added to the agent tool list
    """
    subprocess_env = dict(os.environ) if env is None else dict(env)
    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx", args=["-y", package_name, *args], env=subprocess_env
            ),
            timeout=timeout,
        ),
        tool_filter=tool_filter,
    )
