Tools API
=========

Agents interact with the game using _tools_, which represent a narrow API into the game. Tools are functions that perform game actions and return typed objects.

Tool Architecture
-----------------

Tools live in `fle/env/tools/agent/` and require 3 files:

1. **agent.md**: Documentation for the agent, including usage patterns, best practices and failure modes
2. **client.py**: Client-side implementation, a Python class that can be invoked by the agent
3. **server.lua**: Server-side implementation, which handles most of the logic and heavy lifting

.. mermaid::
   :config:
     layout: fixed
     flowchart:
       defaultRenderer:
         elk

   flowchart LR
       A("fa:fa-comment-dots Agent")
       subgraph s1["Learning Environment"]
           B("fa:fa-code Interpreter")
           n1("client.py")
       end
       subgraph s2["Factorio Server"]
           E1["fa:fa-shapes server.lua"]
           F("fa:fa-cog Factorio Engine")
       end
       A -- Synthesises Python --> B
       B -- Invokes --> n1
       n1 -. Exceptions .-> B
       n1 -. Objects .-> B
       n1 --Remote TCP Call--> E1
       E1 -- Execute --> F
       F-. Result .-> E1
       E1 -. TCP Response .-> n1
       B -. Observation .-> A

Core Tools
----------

Inventory Management
~~~~~~~~~~~~~~~~~~~~

**inspect_inventory**
   Checks contents of player or entity inventories

   - Supports various inventory types (chests, furnaces, etc.)
   - Returns Inventory object with count methods
   - Can query specific items

**insert_item**
   Places items from player inventory into entities

   - Works with machines, chests, belts
   - Validates item compatibility
   - Returns updated entity

**extract_item**
   Removes items from entity inventories

   - Supports all inventory types
   - Auto-transfers to player inventory
   - Returns quantity extracted

Entity Management
~~~~~~~~~~~~~~~~~

**place_entity**
   Places entities in the world

   - Handles direction and positioning
   - Validates placement requirements
   - Returns placed Entity object

**place_entity_next_to**
   Places entities relative to others

   - Automatic spacing/alignment
   - Handles entity dimensions
   - Supports all entity types

**pickup_entity**
   Removes entities from the world

   - Returns items to inventory
   - Handles entity groups
   - Supports all placeable items

**rotate_entity**
   Changes entity orientation

   - Affects entity behavior (e.g., inserter direction)
   - Validates rotation rules
   - Returns updated entity

Entity Queries
~~~~~~~~~~~~~~

**get_entity**
   Retrieves entity objects at positions

   - Updates stale references
   - Returns typed Entity objects
   - Handles all entity types

**get_entities**
   Finds multiple entities in an area

   - Supports filtering by type
   - Returns List[Entity]
   - Groups connected entities

**nearest**
   Locates closest resources/entities

   - Finds ores, water, trees
   - Returns Position object
   - 500 tile search radius

**nearest_buildable**
   Finds valid building locations

   - Respects entity dimensions
   - Handles resource requirements
   - Returns buildable position

Resource Management
~~~~~~~~~~~~~~~~~~~

**get_resource_patch**
   Analyzes resource deposits

   - Returns size and boundaries
   - Supports all resource types
   - Includes total resource amount

**harvest_resource**
   Gathers resources from the world

   - Supports ores, trees, rocks
   - Auto-collects to inventory
   - Returns amount harvested

Connection Management
~~~~~~~~~~~~~~~~~~~~~

**connect_entities**
   Creates connections between entities

   - Handles belts, pipes, power
   - Automatic pathfinding
   - Returns connection group

**get_connection_amount**
   Calculates required connection items

   - Pre-planning tool
   - Works with all connection types
   - Returns item count needed

Crafting and Research
~~~~~~~~~~~~~~~~~~~~~

**set_entity_recipe**
   Configures machine crafting recipes

   - Works with assemblers/chemical plants
   - Validates recipe requirements
   - Returns updated entity

**get_prototype_recipe**
   Retrieves crafting requirements

   - Shows ingredients/products
   - Includes crafting time
   - Returns Recipe object

**craft_item**
   Creates items from components

   - Handles recursive crafting
   - Validates technology requirements
   - Returns crafted amount

**set_research**
   Initiates technology research

   - Validates prerequisites
   - Returns required ingredients
   - Handles research queue

**get_research_progress**
   Monitors research status

   - Shows remaining requirements
   - Tracks progress percentage
   - Returns ingredient list

Movement and Control
~~~~~~~~~~~~~~~~~~~~

**move_to**
   Moves player to position

   - Pathfinds around obstacles
   - Can place items while moving
   - Returns final position

**sleep**
   Pauses execution

   - Waits for actions to complete
   - Adapts to game speed
   - Maximum 15 second duration

**launch_rocket**
   Controls rocket silo launches

   - Validates launch requirements
   - Handles launch sequence
   - Returns updated silo state

Debugging and Output
~~~~~~~~~~~~~~~~~~~~

**print**
   Outputs debug information to stdout

   - Supports various object types
   - Useful for monitoring state
   - Returns formatted string

Tool Categories
----------------

**Core Tools**
   Essential tools for basic game interaction

**Advanced Tools**
   Specialized tools for complex operations

**Debugging Tools**
   Tools for monitoring and debugging

**Multi-Agent Tools**
   Tools for coordinated multi-agent operations

Creating Custom Tools
---------------------

1. Create a new directory in `fle/env/tools/agent/`, e.g `fle/env/tools/agent/my_tool`
2. Add a `client.py` file, which should contain a class inheriting `Tool` and implementing a `__call__` function to treat the class as a callable function. The method signature should contain type annotations. This function _must_ call `self.execute` to invoke the server-side logic.
3. Add a `server.lua` file, containing a function structured like `global.actions.my_tool = function(arg1, arg2, ...)`. This file should invoke the `Factorio API <https://lua-api.factorio.com/1.1.110/>`_ to perform the desired action, and return a table that will be serialized and sent back to the client.
4. Add an `agent.md` file, which should contain a markdown description of the tool. This file will be used by the agent to understand how to use the tool

Next time you run an eval, the tool will automatically be available to the agent and documented in the agent context.

5. (Optional) Create a test suite in `fle/tests/actions` for your new tool.

Tool Documentation
------------------

Each tool has comprehensive documentation including:

- **Overview**: What the tool does
- **Parameters**: Input parameters and their types
- **Returns**: What the tool returns
- **Examples**: Usage examples
- **Best Practices**: Recommended usage patterns
- **Failure Modes**: Common errors and how to avoid them

See the :doc:`tools index <../tools/index>` for detailed documentation of each tool.
