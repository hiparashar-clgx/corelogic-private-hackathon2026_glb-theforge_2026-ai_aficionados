# Example: Agent Connecting to MCP Template via auth flow

This example demonstrates how to connect the ADK agent template MCP server templates with authentication.

This example works with both deployed MCP servers and locally-run MCP servers that use SSE (Server-Side Events) transport.

## Quick Start

We provide a helper script `run_example.sh` that sets up the environment, installs dependencies, and runs both the MCP server and the Agent.

1.  **Prerequisites**: Ensure you have `uv` installed.
2.  **Configuration**:
    *   Copy `.env.example` to `.env` in this directory.
    *   Fill in `LITELLM_API_BASE` and `LITELLM_API_KEY` in the `.env` file.
    *   (Optional) You can adjust the Basic Auth credentials in `.env` if desired, but the defaults work out of the box with the script.

3.  **Run the example**:

    ```bash
    ./run_example.sh
    ```

    This script will:
    *   Load environment variables from `.env`.
    *   Install dependencies.
    *   Start the MCP server in the background.
    *   Start the Agent (accessible via `adk web`).

## Manual Setup

If you prefer to run things manually:

### 1. Configure Environment Variables

Create a `.env` file in `examples/auth_agent_with_mcp/src/auth_agent_with_mcp_template/` based on `.env.example`.

### 2. Install Dependencies

From the root of the example directory:

```bash
cd examples/auth_agent_with_mcp
uv sync
```

### 3. Run the MCP Server

Navigate to the MCP servers directory and run the server:

```bash
cd src/auth_agent_with_mcp_template/auth_mcp_servers
uv run python cotality_mcp_server.py
```

The server will start on `http://0.0.0.0:8001/sse`.

### 4. Run the Agent

Open a new terminal, navigate to the example source directory, and run the agent:

```bash
cd examples/auth_agent_with_mcp/src
uv run adk web
```

The agent will connect to the local MCP server using the configured Basic Auth credentials.

## Notes

- The `cotality_mcp_server.py` uses `BasicAuthMiddleware` to enforce Basic Authentication.
- The agent is configured to send Basic Auth headers when `BASIC_AUTH_SCHEME` is set to `True`.

