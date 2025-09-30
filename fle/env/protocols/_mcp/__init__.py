"""MCP protocol implementation for Factorio Learning Environment."""

# ruff: noqa: E402
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from fastmcp import FastMCP

# Create the MCP server instance FIRST
mcp = FastMCP(
    "Factorio Learning Environment",
    dependencies=["dulwich", "numpy", "pillow"],
)

# Now import other modules that use mcp

from fle.env.protocols._mcp.init import initialize_session, shutdown_session, state
from fle.env.protocols._mcp.state import FactorioMCPState


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
