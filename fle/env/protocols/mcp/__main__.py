#!/usr/bin/env python3
"""
MCP Server entry point for Factorio Learning Environment
Run with: python -m fle.env.protocols.mcp
"""

import sys
import os

# Add parent directory to Python path to ensure imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from fle.env.protocols.mcp import mcp

# Import all tools to register them
from fle.env.protocols.mcp.tools import *
from fle.env.protocols.mcp.resources import *
from fle.env.protocols.mcp.version_control import *
from fle.env.protocols.mcp.unix_tools import *

if __name__ == "__main__":
    # Run the MCP server using stdio transport
    mcp.run()