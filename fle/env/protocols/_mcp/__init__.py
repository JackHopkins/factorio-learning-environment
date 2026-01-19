"""MCP protocol implementation for Factorio Learning Environment."""

# ruff: noqa: E402
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

try:
    from fastmcp import FastMCP

    # Create the MCP server instance FIRST
    mcp = FastMCP(
        "Factorio Learning Environment",
        dependencies=["dulwich", "numpy", "pillow"],
    )
    _FASTMCP_AVAILABLE = True
except ImportError:
    mcp = None
    _FASTMCP_AVAILABLE = False

# Now import other modules that use mcp
if _FASTMCP_AVAILABLE:
    from fle.env.protocols._mcp.init import initialize_session, shutdown_session, state
    from fle.env.protocols._mcp.state import FactorioMCPState
else:
    initialize_session = None
    shutdown_session = None
    state = None
    FactorioMCPState = None


@dataclass
class FactorioContext:
    """Factorio server context available during MCP session"""

    connection_message: str
    state: FactorioMCPState


@asynccontextmanager
async def fle_lifespan(server) -> AsyncIterator[FactorioContext]:
    """Manage the Factorio server lifecycle within the MCP session"""
    connection_message = await initialize_session()
    context = FactorioContext(connection_message=connection_message, state=state)
    try:
        yield context
    finally:
        await shutdown_session()


# Attach the lifespan to mcp
mcp.lifespan = fle_lifespan


# Export mcp for other modules
__all__ = ["mcp", "FactorioContext", "initialize_session", "shutdown_session", "state"]
