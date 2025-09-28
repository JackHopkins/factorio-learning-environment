#!/usr/bin/env python3
"""
MCP Server entry point for Factorio Learning Environment
Run with: python -m fle.env.protocols._mcp
"""

import sys
import os

# Add parent directory to Python path to ensure imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from fle.env.protocols._mcp import mcp
# Import all tools to register them with decorators
from fle.env.protocols._mcp.tools import *
from fle.env.protocols._mcp.resources import *
from fle.env.protocols._mcp.version_control import *
from fle.env.protocols._mcp.unix_tools import *

# Import the lifespan setup
from fle.env.protocols._mcp import *

if __name__ == "__main__":

    mcp.run()

