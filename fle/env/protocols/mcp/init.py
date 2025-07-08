"""
Initialization module for the Factorio MCP server with automatic connection
"""

import asyncio
import sys
from fle.env.protocols.mcp.state import FactorioMCPState

# Initialize server state
state = FactorioMCPState()
_initialization_lock = asyncio.Lock()
_initialized = False


# Safe logging function that never writes to stdout
def log_info(message):
    """Log a message to stderr to avoid MCP protocol corruption"""
    print(message, file=sys.stderr)


# async def initialize_servers_if_needed():
#     """Make sure we've initialized servers at least once"""
#     global _initialized
#     async with _initialization_lock:
#         if not _initialized:
#             await state.scan_for_servers()
#             _initialized = True
#


# Handle initialization at session start
async def initialize_session(ctx=None):
    """Automatically initializes the Factorio server when a session begins"""
    log_info("Initializing Factorio session...")

    # Scan for available servers
    servers = await state.scan_for_servers(ctx)
    log_info(str(servers))

    # Automatically connect to the first active server
    active_servers = [s for s in servers if s.is_active]
    if active_servers:
        server = active_servers[0]
        log_info(f"Auto-connecting to server {server.instance_id}: {server.name}")
        await state.connect_to_server(server.instance_id)
        # Return message but don't print it directly to stdout
        return f"Connected to Factorio server {server.name} ({server.address}:{server.tcp_port})"
    else:
        return "No active Factorio servers available for connection"


async def shutdown_session():
    """Clean up when session ends"""
    # Close any active connections
    if state.active_server:
        log_info("Disconnecting from Factorio server...")
        state.active_server.reset()
        state.active_server = None

    # Clear any temporary state
    state.vcs_repos.clear()
