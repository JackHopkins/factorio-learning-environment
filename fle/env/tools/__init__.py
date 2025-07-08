"""Tools for Factorio environment interaction."""

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
