#!/bin/bash
set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Environment Variables for Basic Auth
# These can be overridden by .env file
export BASIC_AUTH_SCHEME="True"
export A2A_CLIENT_AUTH0_CLIENT_ID="admin"
export A2A_CLIENT_AUTH0_CLIENT_SECRET="secret"
export BASIC_AUTH_USERNAME="admin"
export BASIC_AUTH_PASSWORD="secret"

if [ -f .env ]; then
    echo "Loading .env file..."
    export $(grep -v '^#' .env | xargs)
fi

echo "Installing dependencies..."
uv sync

# Function to cleanup background processes
cleanup() {
    echo "Stopping MCP Server..."
    if [ -n "$MCP_PID" ]; then
        kill $MCP_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Start MCP Server
echo "Starting MCP Server..."
uv run src/auth_agent_with_mcp_template/auth_mcp_servers/cotality_mcp_server.py &
MCP_PID=$!

# Wait for MCP Server to start
echo "Waiting for MCP Server to start..."
sleep 5

# Start Agent
echo "Starting Agent..."
cd src
uv run adk web
