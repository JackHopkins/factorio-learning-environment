"""MCP protocol implementation for Factorio Learning Environment."""

# ruff: noqa: E402
from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

try:
    from fastmcp import FastMCP

    _FASTMCP_AVAILABLE = True
except ImportError:
    FastMCP = None
    _FASTMCP_AVAILABLE = False


@asynccontextmanager
async def fle_lifespan(server) -> AsyncIterator[FactorioContext]:
    """Manage the Factorio server lifecycle within the MCP session"""
    connection_message = await initialize_session()
    context = FactorioContext(connection_message=connection_message, state=state)
    try:
        yield context
    finally:
        await shutdown_session()


# Create the MCP server instance FIRST; the lifespan must be passed to the
# constructor (assigning it as an attribute afterwards is ignored by fastmcp).
if _FASTMCP_AVAILABLE:
    mcp = FastMCP("Factorio Learning Environment", lifespan=fle_lifespan)
else:
    mcp = None

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


# Export mcp for other modules
__all__ = ["mcp", "FactorioContext", "initialize_session", "shutdown_session", "state"]
