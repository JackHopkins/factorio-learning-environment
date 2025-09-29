#!/usr/bin/env python3
"""
Standalone MCP Server entry point for Factorio Learning Environment
This file can be used directly with Claude Desktop
"""

import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from fle.env.protocols._mcp.server import mcp

# Import all tools and resources to register them
from fle.env.protocols._mcp.tools import *
from fle.env.protocols._mcp.resources import *
from fle.env.protocols._mcp.version_control import *
from fle.env.protocols._mcp.unix_tools import *

# Import the lifespan setup
from fle.env.protocols._mcp import *

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()