import structlog
import uvicorn
from cotality.mcp.middleware import BasicAuthMiddleware  # type: ignore[import-not-found]
from cotality.mcp.servers.cotality_mcp_server import (  # type: ignore[import-not-found]
    CotalityMCPServer,
)
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = structlog.get_logger()

mcp = CotalityMCPServer(name="Echo Email Service", instructions="Echo service")
mcp.add_middleware(BasicAuthMiddleware())


@mcp.tool(
    name="echo",
    description="Echoes the input string back. Example: 'Hello World!' "
    "will return 'Echo: Hello World!'. ",
)
def echo_tool(input_data: str) -> str:
    return "Echo: " + input_data


# Register health check endpoint directly with FastMCP
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "OK"})


app = mcp.http_app(transport="sse", path="/sse")


def run():
    logger.info("Starting Cotality MCP Server")
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    run()
