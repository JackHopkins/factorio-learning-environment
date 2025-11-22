Tools Overview
==============

Agents interact with the game using *tools*, which represent a narrow API into the game. Tools are functions that agents can call to perform actions and retrieve information.

What are Tools?
---------------

**Tools** are functions that:

- Perform a game action (e.g., placing an entity, crafting an item)
- Return a typed object (e.g., ``Entity``, ``Inventory``, ``Recipe``)
- Can be stored as named variables in the Python namespace for later use

Tools live in ``fle/env/tools/``, and are either:

- **Admin tools**: Non-agent accessible, used for environment management
- **Agent tools**: Used by agents to interact with the game

Tool Architecture
-----------------

.. code-block:: text

   ┌─────────────────┐
   │     Agent       │
   │  (Synthesizes   │
   │  Python Code)   │
   └────────┬────────┘
            │
   ┌────────▼────────────────────┐
   │  Learning Environment       │
   │  ┌────────────────────┐    │
   │  │   Interpreter      │    │
   │  └─────────┬──────────┘    │
   │            │                 │
   │  ┌─────────▼──────────┐    │
   │  │   client.py        │◄───┼─── Exceptions
   │  │  (Python Interface)│    │
   │  └─────────┬──────────┘    │
   │            │                 │
   │            │ Objects         │
   └────────────┼─────────────────┘
                │
                │ Remote TCP Call
                │
   ┌────────────▼─────────────────┐
   │   Factorio Server            │
   │  ┌─────────────────────┐    │
   │  │   server.lua        │    │
   │  │  (Game Logic)       │    │
   │  └─────────┬───────────┘    │
   │            │                  │
   │  ┌─────────▼───────────┐    │
   │  │  Factorio Engine    │    │
   │  │  (Game Simulation)  │    │
   │  └─────────────────────┘    │
   └──────────────────────────────┘

Anatomy of a Tool
-----------------

A tool requires 3 files:

1. **agent.md**: The agent documentation for the tool, including usage patterns, best practices, and failure modes
2. **client.py**: The client-side implementation - a Python class that can be invoked by the agent
3. **server.lua**: The server-side implementation - handles most of the logic and heavy lifting

Tool Categories
---------------

Tools can be grouped into several categories:

Inventory Management
~~~~~~~~~~~~~~~~~~~~

- ``inspect_inventory``: Check contents of player or entity inventories
- ``insert_item``: Place items from player inventory into entities
- ``extract_item``: Remove items from entity inventories

Entity Manipulation
~~~~~~~~~~~~~~~~~~~

- ``place_entity``: Place entities in the world
- ``place_entity_next_to``: Place entities relative to others
- ``pickup_entity``: Remove entities from the world
- ``rotate_entity``: Change entity orientation
- ``get_entity``: Retrieve entity objects at positions
- ``get_entities``: Find multiple entities in an area

Resource Operations
~~~~~~~~~~~~~~~~~~~

- ``nearest``: Locate closest resources/entities
- ``get_resource_patch``: Analyze resource deposits
- ``harvest_resource``: Gather resources from the world

Connections
~~~~~~~~~~~

- ``connect_entities``: Create connections between entities
- ``get_connection_amount``: Calculate required connection items

Crafting & Research
~~~~~~~~~~~~~~~~~~~

- ``craft_item``: Create items from components
- ``get_prototype_recipe``: Retrieve crafting requirements
- ``set_entity_recipe``: Configure machine crafting recipes
- ``set_research``: Initiate technology research
- ``get_research_progress``: Monitor research status

Movement & Utility
~~~~~~~~~~~~~~~~~~

- ``move_to``: Move player to position
- ``nearest_buildable``: Find valid building locations
- ``sleep``: Pause execution
- ``launch_rocket``: Control rocket silo launches

Output
~~~~~~

- ``print``: Output debug information to stdout

Using Tools
-----------

Tools are called like normal Python functions within agent code:

.. code-block:: python

   # Find nearest iron ore
   iron_position = nearest(Resource.IronOre)

   # Place a mining drill
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=iron_position,
       direction=Direction.NORTH
   )

   # Check the drill's status
   print(f"Drill status: {drill.status}")

   # Store result for later use
   my_first_drill = drill

Return Values
-------------

Tools return typed objects that can be:

- **Inspected**: Access attributes like ``drill.status`` or ``inventory.items``
- **Stored**: Save as variables for future reference
- **Printed**: Display information to stdout for observation

Common Return Types
~~~~~~~~~~~~~~~~~~~

- ``Entity``: Represents a game entity (drill, chest, inserter, etc.)
- ``Inventory``: Contains items and quantities
- ``Recipe``: Describes crafting requirements
- ``Position``: X, Y coordinates
- ``ResourcePatch``: Information about resource deposits

Error Handling
--------------

Tools raise typed exceptions with detailed context when:

- Invalid parameters are provided
- Required resources are unavailable
- Game constraints are violated (e.g., invalid placement)
- Entities don't exist or have been destroyed

Example error:

.. code-block:: python

   InvalidEntityPlacementException: Cannot place burner-mining-drill at
   Position(x=10, y=20) - location is occupied by iron-chest

Next Steps
----------

- See :doc:`core_tools` for detailed documentation on each tool
- Learn how to :doc:`custom_tools` for specialized functionality
- Review the :doc:`../environment/overview` to understand the full context
