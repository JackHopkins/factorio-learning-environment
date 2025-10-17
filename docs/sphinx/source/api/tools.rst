Tools
=====

Agents interact with the game using *tools*, which represent a narrow API into the game. Tools are functions that perform a game action and return a typed object, which can be stored as a named variable in the Python namespace for later use.

Anatomy of a Tool
-----------------

Tools live in ``env/src/tools``, and are either ``admin`` tools (non-agent accessible) or ``agent`` tools (used by the agent).

A tool requires 3 files:

1. ``agent.md``: The agent documentation for the tool, including usage patterns, best practices and failure modes.
2. ``client.py``: The client-side implementation, which is a Python class that can be invoked by the agent.
3. ``server.lua``: The server-side implementation, which handles most of the logic and heavy lifting.

.. mermaid::

   flowchart LR
       A["fa:fa-comment-dots Agent"]
       subgraph s1["Learning Environment"]
           B["fa:fa-code Interpreter"]
           n1["client.py"]
       end
       subgraph s2["Factorio Server"]
           E1["fa:fa-shapes server.lua"]
           F["fa:fa-cog Factorio Engine"]
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
^^^^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   tools/inspect_inventory
   tools/insert_item
   tools/extract_item

Entity Management
^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   tools/place_entity
   tools/place_entity_next_to
   tools/pickup_entity
   tools/rotate_entity
   tools/get_entity
   tools/get_entities

Resource Management
^^^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   tools/nearest
   tools/nearest_buildable
   tools/get_resource_patch
   tools/harvest_resource

Connection Management
^^^^^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   tools/connect_entities
   tools/get_connection_amount

Production Management
^^^^^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   tools/set_entity_recipe
   tools/get_prototype_recipe
   tools/craft_item

Research Management
^^^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   tools/set_research
   tools/get_research_progress

Movement and Navigation
^^^^^^^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   tools/move_to

Utility Tools
^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   tools/sleep
   tools/launch_rocket
   tools/print

Communication Tools
^^^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1

   tools/send_message
   tools/get_messages

Tool Categories Overview
------------------------

| Tool                    | Description                                      | Key Features                                                                                                                               |
| ----------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| ``inspect_inventory``   | Checks contents of player or entity inventories  | - Supports various inventory types (chests, furnaces, etc.)<br>- Returns Inventory object with count methods<br>- Can query specific items |
| ``insert_item``         | Places items from player inventory into entities | - Works with machines, chests, belts<br>- Validates item compatibility<br>- Returns updated entity                                         |
| ``extract_item``        | Removes items from entity inventories            | - Supports all inventory types<br>- Auto-transfers to player inventory<br>- Returns quantity extracted                                     |
| ``place_entity``        | Places entities in the world                     | - Handles direction and positioning<br>- Validates placement requirements<br>- Returns placed Entity object                                |
| ``place_entity_next_to``| Places entities relative to others               | - Automatic spacing/alignment<br>- Handles entity dimensions<br>- Supports all entity types                                                |
| ``pickup_entity``       | Removes entities from the world                  | - Returns items to inventory<br>- Handles entity groups<br>- Supports all placeable items                                                  |
| ``rotate_entity``       | Changes entity orientation                       | - Affects entity behavior (e.g., inserter direction)<br>- Validates rotation rules<br>- Returns updated entity                             |
| ``get_entity``          | Retrieves entity objects at positions            | - Updates stale references<br>- Returns typed Entity objects<br>- Handles all entity types                                                 |
| ``get_entities``        | Finds multiple entities in an area               | - Supports filtering by type<br>- Returns List[Entity]<br>- Groups connected entities                                                      |
| ``nearest``             | Locates closest resources/entities               | - Finds ores, water, trees<br>- Returns Position object<br>- 500 tile search radius                                                        |
| ``get_resource_patch``  | Analyzes resource deposits                       | - Returns size and boundaries<br>- Supports all resource types<br>- Includes total resource amount                                         |
| ``harvest_resource``    | Gathers resources from the world                 | - Supports ores, trees, rocks<br>- Auto-collects to inventory<br>- Returns amount harvested                                                |
| ``connect_entities``    | Creates connections between entities             | - Handles belts, pipes, power<br>- Automatic pathfinding<br>- Returns connection group                                                     |
| ``get_connection_amount``| Calculates required connection items             | - Pre-planning tool<br>- Works with all connection types<br>- Returns item count needed                                                    |
| ``set_entity_recipe``   | Configures machine crafting recipes              | - Works with assemblers/chemical plants<br>- Validates recipe requirements<br>- Returns updated entity                                     |
| ``get_prototype_recipe``| Retrieves crafting requirements                  | - Shows ingredients/products<br>- Includes crafting time<br>- Returns Recipe object                                                        |
| ``craft_item``          | Creates items from components                    | - Handles recursive crafting<br>- Validates technology requirements<br>- Returns crafted amount                                            |
| ``set_research``        | Initiates technology research                    | - Validates prerequisites<br>- Returns required ingredients<br>- Handles research queue                                                    |
| ``get_research_progress``| Monitors research status                         | - Shows remaining requirements<br>- Tracks progress percentage<br>- Returns ingredient list                                                |
| ``move_to``             | Moves player to position                         | - Pathfinds around obstacles<br>- Can place items while moving<br>- Returns final position                                                 |
| ``nearest_buildable``   | Finds valid building locations                   | - Respects entity dimensions<br>- Handles resource requirements<br>- Returns buildable position                                            |
| ``sleep``               | Pauses execution                                 | - Waits for actions to complete<br>- Adapts to game speed<br>- Maximum 15 second duration                                                  |
| ``launch_rocket``       | Controls rocket silo launches                    | - Validates launch requirements<br>- Handles launch sequence<br>- Returns updated silo state                                               |
| ``print``               | Outputs debug information to stdout              | - Supports various object types<br>- Useful for monitoring state<br>- Returns formatted string                                             |

Creating Custom Tools
---------------------

When adding new tools to the environment:

1. Follow the structure outlined in the :doc:`customization/tools` section
2. Include comprehensive docstrings and type hints
3. Add examples in the tool's ``agent.md`` file
4. Create appropriate test cases
5. Update the core tools table above if applicable

Tool Usage Patterns
-------------------

Basic Usage
^^^^^^^^^^^

.. code-block:: python

   # Get current inventory
   inventory = inspect_inventory()
   print(f"Current inventory: {inventory}")

   # Place an entity
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=nearest(Resource.IronOre),
       direction=Direction.NORTH
   )

   # Check entity status
   print(f"Drill status: {drill.status}")

Error Handling
^^^^^^^^^^^^^^

.. code-block:: python

   try:
       # Attempt to place entity
       drill = place_entity(
           entity=Prototype.MiningDrill,
           position=invalid_position,
           direction=Direction.NORTH
       )
   except Exception as e:
       print(f"Failed to place drill: {e}")
       # Try alternative approach
       valid_pos = nearest_buildable(Prototype.MiningDrill)
       drill = place_entity(
           entity=Prototype.MiningDrill,
           position=valid_pos,
           direction=Direction.NORTH
       )

State Management
^^^^^^^^^^^^^^^^

.. code-block:: python

   # Store entity references for later use
   entities = get_entities()
   drills = [e for e in entities if e.name == 'mining-drill']
   
   # Check status of stored entities
   for drill in drills:
       if drill.status != EntityStatus.WORKING:
           print(f"Drill at {drill.position} is not working")
           # Take corrective action

Best Practices
--------------

1. **Always check return values**: Tools return objects that should be stored and used
2. **Handle errors gracefully**: Use try-except blocks for robust error handling
3. **Store entity references**: Keep references to placed entities for later use
4. **Validate before acting**: Check prerequisites before performing actions
5. **Use appropriate tools**: Choose the right tool for the task
6. **Monitor state changes**: Check entity status and inventory changes
7. **Plan ahead**: Use planning tools like ``get_connection_amount`` before building
