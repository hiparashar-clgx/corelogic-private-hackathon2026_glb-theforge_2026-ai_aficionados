# Example: Agent Connecting to MCP Template

This example demonstrates how to connect the ADK agent template to the MCP server template (https://github.com/corelogic-private/idap_agents_glb-ag_foundation-python_mcp_template).

This example works with both deployed MCP servers and locally-run MCP servers that use SSE (Server-Side Events) transport.

## Setup
From the root of this repository, sync dependencies.
```bash
uv sync --all-packages --extra dev
```
Navigate to src directory of this example.
```bash
cd examples/agent_with_mcp_template/src
```
Run agent and open chat UI.
```bash
uv run adk web
```

## Configure MCP Server URL
In ```agent.py```, under the ```_get_tools_list``` function, there is a TODO to update the URL of the MCP server.

### Remote MCP Server Template
The default URL in the example is the deployed MCP server template URL in dev: ```https://dev-usw1-cotality-mcp-starter.cntvusw1dev.solutions.corelogic.com/sse```.
This is a simple template server that has a single tool that echoes back the input it receives.

### Local MCP Server Template
If you are using a local MCP server, first follow the instructions in the MCP template repo to run that server on your machine.
Copy the localhost URL (e.g. ```http://localhost:8001/sse```) of the running local server and replace the URL in the TODO.

You might have to edit the port of the MCP server so that it doesn't conflict with the ```adk web``` UI (which runs on port 8000).