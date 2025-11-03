Creating Custom Tools
=====================

FLE allows you to create custom tools for extending agent capabilities. Tools provide a narrow API into the game and enable agents to perform specific actions.

Tool Architecture
-----------------

Tools require 3 files:

1. **agent.md**: Documentation for the agent
2. **client.py**: Client-side Python implementation
3. **server.lua**: Server-side Lua implementation

Tool Structure
--------------

Create a new directory in `fle/env/tools/agent/`:

.. code-block:: bash

   mkdir fle/env/tools/agent/my_tool
   cd fle/env/tools/agent/my_tool

**client.py** - Client-side implementation:

.. code-block:: python

   from fle.env.tools.base import Tool
   from typing import List, Optional
   
   class MyTool(Tool):
       def __call__(self, param1: str, param2: int, param3: Optional[bool] = None) -> dict:
           """
           My custom tool for doing something useful.
           
           Args:
               param1: Description of param1
               param2: Description of param2
               param3: Optional parameter
           
           Returns:
               Dictionary with results
           """
           return self.execute({
               'param1': param1,
               'param2': param2,
               'param3': param3
           })

**server.lua** - Server-side implementation:

.. code-block:: lua

   global.actions.my_tool = function(param1, param2, param3)
       -- Validate parameters
       if not param1 or type(param1) ~= "string" then
           return {error = "param1 must be a string"}
       end
       
       if not param2 or type(param2) ~= "number" then
           return {error = "param2 must be a number"}
       end
       
       -- Perform the action
       local result = {}
       
       -- Your custom logic here
       -- Use Factorio API: https://lua-api.factorio.com/1.1.110/
       
       return result
   end

**agent.md** - Agent documentation:

.. code-block:: markdown

   # My Tool
   
   ## Overview
   My custom tool for doing something useful in the game.
   
   ## Parameters
   - `param1` (str): Description of param1
   - `param2` (int): Description of param2
   - `param3` (bool, optional): Optional parameter
   
   ## Returns
   Dictionary with results including:
   - `success` (bool): Whether the action succeeded
   - `data` (dict): Additional data
   
   ## Examples
   
   ```python
   # Basic usage
   result = my_tool("value1", 42)
   print(result['success'])
   
   # With optional parameter
   result = my_tool("value1", 42, True)
   ```
   
   ## Best Practices
   - Always check the return value for success
   - Handle errors gracefully
   - Use appropriate parameter types
   
   ## Failure Modes
   - Invalid parameter types
   - Game state conflicts
   - Resource limitations

Tool Development Process
------------------------

1. **Design the Interface**
   - Define parameters and return types
   - Consider error handling
   - Plan for edge cases

2. **Implement Client Side**
   - Create Python class inheriting from Tool
   - Implement __call__ method with type hints
   - Call self.execute() with parameters

3. **Implement Server Side**
   - Create Lua function in global.actions
   - Validate parameters
   - Use Factorio API to perform actions
   - Return structured results

4. **Write Documentation**
   - Document parameters and return values
   - Provide usage examples
   - Describe failure modes
   - Include best practices

5. **Test the Tool**
   - Create test cases
   - Verify error handling
   - Test edge cases
   - Validate performance

Example Tool: Resource Scanner
------------------------------

Here's a complete example of a custom tool for scanning resources:

**client.py**:

.. code-block:: python

   from fle.env.tools.base import Tool
   from typing import List, Dict, Optional
   from fle.env.game_types import Position
   
   class ResourceScanner(Tool):
       def __call__(self, center: Position, radius: int = 100, resource_type: Optional[str] = None) -> Dict:
           """
           Scan for resources in a circular area.
           
           Args:
               center: Center position for scanning
               radius: Scan radius in tiles
               resource_type: Specific resource type to scan for (optional)
           
           Returns:
               Dictionary with scan results
           """
           return self.execute({
               'center': center,
               'radius': radius,
               'resource_type': resource_type
           })

**server.lua**:

.. code-block:: lua

   global.actions.resource_scanner = function(center, radius, resource_type)
       -- Validate parameters
       if not center or not center.x or not center.y then
           return {error = "center must be a position with x and y"}
       end
       
       if not radius or type(radius) ~= "number" or radius <= 0 then
           return {error = "radius must be a positive number"}
       end
       
       -- Get surface
       local surface = game.surfaces[1]
       if not surface then
           return {error = "No surface available"}
       end
       
       -- Scan for resources
       local resources = {}
       local center_pos = {x = center.x, y = center.y}
       
       for _, entity in pairs(surface.find_entities_filtered{
           area = {{center_pos.x - radius, center_pos.y - radius}, 
                   {center_pos.x + radius, center_pos.y + radius}},
           type = "resource"
       }) do
           if not resource_type or entity.name == resource_type then
               table.insert(resources, {
                   name = entity.name,
                   position = {x = entity.position.x, y = entity.position.y},
                   amount = entity.amount
               })
           end
       end
       
       return {
           success = true,
           resources = resources,
           count = #resources
       }
   end

**agent.md**:

.. code-block:: markdown

   # Resource Scanner
   
   ## Overview
   Scans for resources in a circular area around a center position.
   
   ## Parameters
   - `center` (Position): Center position for scanning
   - `radius` (int): Scan radius in tiles (default: 100)
   - `resource_type` (str, optional): Specific resource type to scan for
   
   ## Returns
   Dictionary with:
   - `success` (bool): Whether the scan succeeded
   - `resources` (list): List of found resources
   - `count` (int): Number of resources found
   
   ## Examples
   
   ```python
   # Scan all resources in area
   result = resource_scanner(Position(0, 0), 200)
   print(f"Found {result['count']} resources")
   
   # Scan for specific resource
   result = resource_scanner(Position(0, 0), 100, "iron-ore")
   for resource in result['resources']:
       print(f"{resource['name']} at {resource['position']}")
   ```
   
   ## Best Practices
   - Use appropriate radius for your needs
   - Filter by resource type when possible
   - Handle empty results gracefully
   
   ## Failure Modes
   - Invalid position coordinates
   - Negative or zero radius
   - Surface not available
   - Resource type not found

Testing Tools
--------------

Create test cases for your custom tools:

.. code-block:: python

   import pytest
   from fle.env.tools.agent.my_tool import MyTool
   from fle.env.game_types import Position
   
   def test_tool_creation():
       tool = MyTool()
       assert tool is not None
   
   def test_tool_execution():
       tool = MyTool()
       result = tool("test", 42, True)
       assert 'success' in result
   
   def test_tool_error_handling():
       tool = MyTool()
       result = tool("", -1)  # Invalid parameters
       assert 'error' in result
   
   def test_tool_with_position():
       tool = MyTool()
       position = Position(10, 20)
       result = tool("test", 42, position=position)
       assert result['success']

Tool Registration
-----------------

Tools are automatically discovered and registered:

1. **File Discovery**: The system scans `fle/env/tools/agent/`
2. **Import Loading**: Python classes are imported
3. **Lua Loading**: Server-side functions are loaded
4. **Documentation**: Agent documentation is parsed
5. **Registration**: Tools are made available to agents

Advanced Features
----------------

**Tool Dependencies**
   Tools can depend on other tools

**Tool Caching**
   Cache expensive operations

**Tool Validation**
   Validate tool usage and parameters

**Tool Metrics**
   Collect usage statistics

**Tool Versioning**
   Handle tool updates and compatibility

Best Practices
--------------

1. **Clear Interface**: Design simple, intuitive interfaces
2. **Error Handling**: Provide meaningful error messages
3. **Documentation**: Write comprehensive documentation
4. **Testing**: Test all scenarios and edge cases
5. **Performance**: Optimize for efficiency
6. **Compatibility**: Ensure backward compatibility
7. **Security**: Validate all inputs and outputs
