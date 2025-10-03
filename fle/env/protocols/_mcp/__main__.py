#!/usr/bin/env python3
"""
MCP Server entry point for Factorio Learning Environment
Run with: python -m fle.env.protocols._mcp
"""

import sys
import os

# Add parent directory to Python path to ensure imports work
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    ),
)

# NOW import all modules that define tools - this registers them
from fle.env.protocols._mcp import tools  # Core tools
from fle.env.protocols._mcp import version_control  # VCS tools
from fle.env.protocols._mcp import resources  # Resources
from fle.env.protocols._mcp import prompts  # Prompts

# Import the lifespan setup
from fle.env.protocols._mcp import mcp


if __name__ == "__main__":
    a = tools  # Added these so the
    b = version_control
    c = resources
    d = prompts
    mcp.run()
