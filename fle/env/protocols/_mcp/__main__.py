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


# Import all tools to register them with decorators

# Import the lifespan setup
from fle.env.protocols._mcp import mcp

if __name__ == "__main__":
    mcp.run()
