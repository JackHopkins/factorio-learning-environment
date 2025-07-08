"""MCP protocol implementation for Factorio Learning Environment."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from fle.env.protocols.mcp.init import initialize_session, shutdown_session
from fle.env.protocols.mcp.state import FactorioMCPState


@dataclass
class FactorioContext:
    """Factorio server context available during MCP session"""

    connection_message: str
    state: FactorioMCPState


@asynccontextmanager
async def fle_lifespan(server: FastMCP) -> AsyncIterator[FactorioContext]:
    """Manage the Factorio server lifecycle within the MCP session"""

    # Temporarily redirect stdout to stderr or /dev/null to prevent MCP protocol corruption
    # original_stdout = sys.stdout
    # sys.stdout = open(os.devnull, 'w')

    # try:
    connection_message = await initialize_session()
    from fle.env.protocols.mcp.init import state
    # finally:
    #     # Restore stdout
    #     sys.stdout.close()
    #     sys.stdout = original_stdout

    # Create context with connection message and state
    context = FactorioContext(connection_message=connection_message, state=state)

    try:
        yield context
    finally:
        # Clean up when the session ends
        await shutdown_session()


# Initialize FastMCP FLE server with automatic lifecycle management
mcp = FastMCP(
    "Factorio Learning Environment",
    lifespan=fle_lifespan,
    dependencies=["dulwich", "numpy", "pillow"],
)
