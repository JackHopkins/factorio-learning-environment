Model Context Protocol (MCP)
============================

FLE supports the `Model Context Protocol <https://github.com/modelcontextprotocol>`_ (MCP) to enable LLM reasoning models to invoke tools directly.

Overview
--------

The Model Context Protocol is a standardized interface that allows AI models to interact with external tools and services. FLE's MCP integration enables:

- Direct tool invocation from LLM reasoning models
- Standardized request/response formats
- Seamless integration with MCP-compatible clients

What is MCP?
------------

MCP provides a universal interface for:

1. **Tool Discovery**: Models can discover available tools and their capabilities
2. **Tool Invocation**: Models can call tools with structured parameters
3. **Result Handling**: Models receive typed responses from tool calls

Benefits
--------

Using MCP with FLE provides:

- **Standardization**: Works with any MCP-compatible client
- **Type Safety**: Structured tool definitions with parameter types
- **Extensibility**: Easy to add new tools to the MCP interface
- **Interoperability**: Compatible with the broader MCP ecosystem

Installation
------------

To use MCP features, install FLE with MCP support:

.. code-block:: bash

   pip install factorio-learning-environment[mcp]

   # Or with uv
   uv add factorio-learning-environment[mcp]

Configuration
-------------

MCP configuration is located in ``fle/env/protocols/_mcp/``. The MCP server automatically exposes all agent-accessible tools.

Using MCP
---------

Starting the MCP Server
~~~~~~~~~~~~~~~~~~~~~~~

The MCP server can be started alongside the FLE environment:

.. code-block:: python

   from fle.env.protocols.mcp import MCPServer

   # Initialize MCP server
   server = MCPServer()
   server.start()

Tool Discovery
~~~~~~~~~~~~~~

MCP clients can discover available tools:

.. code-block:: python

   # List all available tools
   tools = server.list_tools()

   for tool in tools:
       print(f"Tool: {tool.name}")
       print(f"Description: {tool.description}")
       print(f"Parameters: {tool.parameters}")

Invoking Tools
~~~~~~~~~~~~~~

Tools can be invoked through the MCP interface:

.. code-block:: python

   # Invoke a tool
   result = server.invoke_tool(
       tool_name="place_entity",
       parameters={
           "entity": "burner-mining-drill",
           "position": {"x": 10, "y": 20},
           "direction": "north"
       }
   )

   print(f"Result: {result}")

Integration with LLM Clients
-----------------------------

MCP-Compatible Clients
~~~~~~~~~~~~~~~~~~~~~~

FLE's MCP implementation works with:

- Claude Desktop
- Other MCP-compatible AI assistants
- Custom MCP clients

Example Integration
~~~~~~~~~~~~~~~~~~~

Here's how to integrate FLE with an MCP-compatible client:

.. code-block:: json

   {
     "mcpServers": {
       "factorio": {
         "command": "python",
         "args": ["-m", "fle.env.protocols.mcp.server"],
         "env": {
           "FLE_CLUSTER_HOST": "localhost",
           "FLE_CLUSTER_PORT": "34197"
         }
       }
     }
   }

Tool Definitions
----------------

MCP tools are automatically generated from FLE's tool definitions. Each tool includes:

- **Name**: The tool identifier
- **Description**: What the tool does (from ``agent.md``)
- **Parameters**: Typed parameter schema
- **Return Type**: Expected response format

Example Tool Definition
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "name": "place_entity",
     "description": "Places an entity in the world at a specified position",
     "parameters": {
       "type": "object",
       "properties": {
         "entity": {
           "type": "string",
           "description": "The entity prototype to place"
         },
         "position": {
           "type": "object",
           "properties": {
             "x": {"type": "number"},
             "y": {"type": "number"}
           }
         },
         "direction": {
           "type": "string",
           "enum": ["north", "south", "east", "west"]
         }
       },
       "required": ["entity", "position"]
     }
   }

Advanced Usage
--------------

Custom MCP Tools
~~~~~~~~~~~~~~~~

You can create custom MCP-specific tools by following the :doc:`../tools/custom_tools` guide. Tools created this way are automatically exposed via MCP.

Error Handling
~~~~~~~~~~~~~~

MCP calls return structured errors:

.. code-block:: json

   {
     "error": {
       "code": "InvalidParameters",
       "message": "Entity 'invalid-entity' not found",
       "details": {
         "entity": "invalid-entity",
         "available_entities": ["burner-mining-drill", "iron-chest", ...]
       }
     }
   }

State Management
~~~~~~~~~~~~~~~~

MCP maintains state between tool calls:

- Variables persist in the namespace
- Entities remain referenced across calls
- Game state is preserved

Architecture
------------

.. code-block:: text

   ┌─────────────────────┐
   │   MCP Client        │
   │  (Claude, etc.)     │
   └──────────┬──────────┘
              │
              │ MCP Protocol
              │
   ┌──────────▼──────────┐
   │   MCP Server        │
   │  (FLE Protocol)     │
   └──────────┬──────────┘
              │
              │ Tool Calls
              │
   ┌──────────▼──────────┐
   │   FLE Environment   │
   │  (Game Instance)    │
   └─────────────────────┘

Documentation
-------------

For detailed MCP documentation, see:

- `Official MCP Documentation <https://github.com/modelcontextprotocol>`_
- ``fle/env/protocols/_mcp/README.md`` in the repository

Troubleshooting
---------------

Connection Issues
~~~~~~~~~~~~~~~~~

If MCP clients can't connect:

1. Verify the MCP server is running
2. Check port configuration
3. Ensure Factorio cluster is started

Tool Not Found
~~~~~~~~~~~~~~

If a tool is not available via MCP:

1. Verify the tool exists in ``fle/env/tools/agent/``
2. Check that the tool has all required files (``client.py``, ``server.lua``, ``agent.md``)
3. Restart the MCP server

Invalid Parameters
~~~~~~~~~~~~~~~~~~

If tool calls fail with parameter errors:

1. Check the tool's parameter schema
2. Verify parameter types match the schema
3. Ensure required parameters are provided

Next Steps
----------

- Review :doc:`../tools/overview` to understand available tools
- See :doc:`../tools/custom_tools` to create MCP-compatible tools
- Check the official MCP documentation for client integration
