"""
Factorio Learning Environment Tools

This module provides the base classes and utilities for interacting with the Factorio game.
Tools are organized into two main categories:
- agent: Tools available to agents for game interaction
- admin: Administrative tools for game management and debugging

Base Classes:
- Controller: Base class for all game controllers
- Tool: Base class for all tools that interact with the game
- Init: Initialization tool for setting up the game environment
"""

from fle.env.tools.controller import Controller
from fle.env.tools.init import Init
from fle.env.tools.tool import Tool

# Version info
__version__ = "1.0.0"

# Public API - expose the main base classes
__all__ = [
    # Base classes
    "Controller",
    "Tool",
    "Init",
]


# Tool discovery utilities
def get_agent_tools():
    """Get list of available agent tools"""
    from pathlib import Path

    agent_dir = Path(__file__).parent / "agent"
    if not agent_dir.exists():
        return []

    tools = []
    for item in agent_dir.iterdir():
        if item.is_dir() and (item / "client.py").exists():
            tools.append(item.name)

    return sorted(tools)


def get_admin_tools():
    """Get list of available admin tools"""
    from pathlib import Path

    admin_dir = Path(__file__).parent / "admin"
    if not admin_dir.exists():
        return []

    tools = []
    for item in admin_dir.iterdir():
        if item.is_dir() and (item / "client.py").exists():
            tools.append(item.name)

    return sorted(tools)


def get_all_tools():
    """Get dictionary of all available tools organized by category"""
    return {"agent": get_agent_tools(), "admin": get_admin_tools()}


# Add utility functions to __all__
__all__.extend(["get_agent_tools", "get_admin_tools", "get_all_tools"])
