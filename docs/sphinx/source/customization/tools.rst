Creating Custom Tools
======================

When adding new tools to the FLE environment, you need to create three files following the established pattern. This guide walks you through the process.

Tool Structure
--------------

Each tool requires three files in ``env/src/tools/agent/your_tool_name/``:

1. ``agent.md``: Documentation for the agent
2. ``client.py``: Client-side Python implementation
3. ``server.lua``: Server-side Lua implementation

Creating a New Tool
-------------------

Step 1: Create Tool Directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   mkdir -p env/src/tools/agent/my_tool

Step 2: Create Client Implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create ``client.py`` with a class inheriting from ``Tool``:

.. code-block:: python

   from fle.env.tools.base import Tool
   from typing import Optional
   from fle.env.game_types import Prototype
   from fle.env.entities import Position

   class MyTool(Tool):
       def __call__(self, param1: str, param2: Optional[int] = None) -> Dict:
           """
           Description of what this tool does.
           
           Args:
               param1: Description of first parameter
               param2: Description of second parameter (optional)
               
           Returns:
               Dict containing the result
               
           Raises:
               ValueError: If parameters are invalid
           """
           # Validate parameters
           if not param1:
               raise ValueError("param1 cannot be empty")
               
           # Call server-side implementation
           result = self.execute('my_tool', param1, param2)
           
           # Process result if needed
           return result

Step 3: Create Server Implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create ``server.lua`` with the server-side logic:

.. code-block:: lua

   global.actions.my_tool = function(param1, param2)
       -- Validate parameters
       if not param1 then
           error("param1 is required")
       end
       
       -- Perform the action using Factorio API
       local result = {}
       
       -- Example: Get player position
       local player = game.players[1]
       if player and player.valid then
           result.position = {
               x = player.position.x,
               y = player.position.y
           }
           result.success = true
       else
           result.success = false
           result.error = "Player not found"
       end
       
       return result
   end

Step 4: Create Agent Documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create ``agent.md`` with comprehensive documentation:

.. code-block:: markdown

   # my_tool

   The `my_tool` tool performs a specific action in the Factorio world.

   ## Overview

   This tool does X, Y, and Z. It's useful for situations where you need to...

   ## Function Signature

   ```python
   def my_tool(param1: str, param2: Optional[int] = None) -> Dict
   ```

   ### Parameters

   - `param1`: Description of what this parameter does
   - `param2`: Optional parameter with default behavior

   ### Returns

   - Returns a dictionary containing:
     - `success`: Boolean indicating if the action succeeded
     - `result`: The actual result data
     - `error`: Error message if something went wrong

   ## Usage Examples

   ### Basic Usage

   ```python
   # Simple usage
   result = my_tool("example_value")
   if result['success']:
       print(f"Tool succeeded: {result['result']}")
   ```

   ### Advanced Usage

   ```python
   # With optional parameter
   result = my_tool("example_value", 42)
   if result['success']:
       data = result['result']
       print(f"Got data: {data}")
   ```

   ## Error Handling

   The tool will raise exceptions in the following situations:

   - Invalid parameter values
   - Game state errors
   - Network communication issues

   Example error handling:

   ```python
   try:
       result = my_tool("invalid")
   except ValueError as e:
       print(f"Parameter error: {e}")
   except Exception as e:
       print(f"Unexpected error: {e}")
   ```

   ## Best Practices

   1. **Always check return values**: Verify the success flag before using results
   2. **Handle errors gracefully**: Use try-except blocks for robust error handling
   3. **Validate inputs**: Check parameter values before calling the tool
   4. **Store results**: Save important results in variables for later use

   ## Common Pitfalls

   1. **Not checking success**: Always verify the success flag in the return value
   2. **Invalid parameters**: Ensure parameters meet the tool's requirements
   3. **Ignoring errors**: Handle exceptions appropriately
   4. **Resource cleanup**: Some tools may require cleanup after use

Tool Implementation Patterns
----------------------------

Entity Manipulation Tools
^^^^^^^^^^^^^^^^^^^^^^^^^^

Tools that manipulate game entities:

.. code-block:: python

   class PlaceEntityTool(Tool):
       def __call__(self, entity_type: Prototype, position: Position, 
                    direction: Direction = Direction.NORTH) -> Entity:
           """Place an entity in the world"""
           # Validate entity type
           if not isinstance(entity_type, Prototype):
               raise TypeError("entity_type must be a Prototype")
               
           # Validate position
           if not isinstance(position, Position):
               raise TypeError("position must be a Position")
               
           # Call server
           result = self.execute('place_entity', entity_type.value, 
                                position.x, position.y, direction.value)
           
           # Return Entity object
           return Entity.from_dict(result)

Information Gathering Tools
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tools that gather information about the game state:

.. code-block:: python

   class GetEntityInfoTool(Tool):
       def __call__(self, entity_id: int) -> Optional[Entity]:
           """Get information about a specific entity"""
           if not isinstance(entity_id, int):
               raise TypeError("entity_id must be an integer")
               
           result = self.execute('get_entity_info', entity_id)
           
           if result and result.get('success'):
               return Entity.from_dict(result['entity'])
           return None

Resource Management Tools
^^^^^^^^^^^^^^^^^^^^^^^^^^

Tools that manage resources and inventory:

.. code-block:: python

   class ManageInventoryTool(Tool):
       def __call__(self, action: str, item: str, quantity: int) -> Dict:
           """Manage player inventory"""
           valid_actions = ['add', 'remove', 'set', 'get']
           if action not in valid_actions:
               raise ValueError(f"action must be one of {valid_actions}")
               
           result = self.execute('manage_inventory', action, item, quantity)
           return result

Tool Testing
------------

Create test cases for your tool:

.. code-block:: python

   # In tests/actions/test_my_tool.py
   import pytest
   from fle.env.tools.agent.my_tool import MyTool
   from fle.env.instance import FactorioInstance

   def test_my_tool_basic_usage():
       """Test basic tool usage"""
       tool = MyTool()
       instance = FactorioInstance()
       
       # Test successful usage
       result = tool("test_value")
       assert result['success'] is True
       assert 'result' in result

   def test_my_tool_error_handling():
       """Test error handling"""
       tool = MyTool()
       
       # Test invalid parameter
       with pytest.raises(ValueError):
           tool("")

   def test_my_tool_with_optional_param():
       """Test tool with optional parameter"""
       tool = MyTool()
       
       result = tool("test_value", 42)
       assert result['success'] is True
       assert result['result']['param2'] == 42

Tool Registration
-----------------

Tools are automatically discovered and registered. Ensure your tool follows the naming convention:

1. Tool directory name matches the tool name
2. Client class name matches the tool name (PascalCase)
3. Server function name matches the tool name (snake_case)

Example:
- Directory: ``env/src/tools/agent/my_tool/``
- Client class: ``MyTool``
- Server function: ``global.actions.my_tool``

Best Practices
--------------

1. **Type Hints**: Use proper type hints for all parameters and return values
2. **Documentation**: Write comprehensive docstrings and agent.md documentation
3. **Error Handling**: Handle errors gracefully with appropriate exceptions
4. **Validation**: Validate all input parameters
5. **Testing**: Create comprehensive test cases
6. **Performance**: Consider performance implications of server-side operations
7. **Consistency**: Follow established patterns and conventions
8. **Security**: Validate inputs to prevent security issues
9. **Maintainability**: Write clean, readable code
10. **Documentation**: Keep documentation up to date with code changes
