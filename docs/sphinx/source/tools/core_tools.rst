Core Tools Reference
====================

This page provides a comprehensive reference for all core tools available to agents.

Inventory Management
--------------------

inspect_inventory
~~~~~~~~~~~~~~~~~

Checks contents of player or entity inventories.

**Features:**

- Supports various inventory types (chests, furnaces, etc.)
- Returns ``Inventory`` object with count methods
- Can query specific items

**Example:**

.. code-block:: python

   # Check player inventory
   inventory = inspect_inventory()
   print(f"Iron plates: {inventory['iron-plate']}")

   # Check entity inventory
   chest = get_entity(Prototype.IronChest, position)
   inventory = inspect_inventory(chest)

insert_item
~~~~~~~~~~~

Places items from player inventory into entities.

**Features:**

- Works with machines, chests, belts
- Validates item compatibility
- Returns updated entity

**Example:**

.. code-block:: python

   # Insert coal into a furnace
   furnace = get_entity(Prototype.StoneFurnace, furnace_position)
   insert_item(Prototype.Coal, furnace, quantity=10)

extract_item
~~~~~~~~~~~~

Removes items from entity inventories.

**Features:**

- Supports all inventory types
- Auto-transfers to player inventory
- Returns quantity extracted

**Example:**

.. code-block:: python

   # Extract iron plates from a chest
   chest = get_entity(Prototype.IronChest, chest_position)
   extracted = extract_item(Prototype.IronPlate, chest, quantity=50)
   print(f"Extracted {extracted} iron plates")

Entity Manipulation
-------------------

place_entity
~~~~~~~~~~~~

Places entities in the world.

**Features:**

- Handles direction and positioning
- Validates placement requirements
- Returns placed ``Entity`` object

**Example:**

.. code-block:: python

   # Place a mining drill
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=Position(x=10, y=20),
       direction=Direction.NORTH
   )

place_entity_next_to
~~~~~~~~~~~~~~~~~~~~

Places entities relative to others.

**Features:**

- Automatic spacing/alignment
- Handles entity dimensions
- Supports all entity types

**Example:**

.. code-block:: python

   # Place a chest next to a drill
   chest = place_entity_next_to(
       entity=Prototype.IronChest,
       reference_position=drill.drop_position,
       direction=Direction.SOUTH
   )

pickup_entity
~~~~~~~~~~~~~

Removes entities from the world.

**Features:**

- Returns items to inventory
- Handles entity groups
- Supports all placeable items

**Example:**

.. code-block:: python

   # Pick up a mining drill
   drill = get_entity(Prototype.BurnerMiningDrill, position)
   pickup_entity(drill)

rotate_entity
~~~~~~~~~~~~~

Changes entity orientation.

**Features:**

- Affects entity behavior (e.g., inserter direction)
- Validates rotation rules
- Returns updated entity

**Example:**

.. code-block:: python

   # Rotate an inserter to face a different direction
   inserter = get_entity(Prototype.Inserter, position)
   rotate_entity(inserter, Direction.EAST)

get_entity
~~~~~~~~~~

Retrieves entity objects at positions.

**Features:**

- Updates stale references
- Returns typed ``Entity`` objects
- Handles all entity types

**Example:**

.. code-block:: python

   # Get a chest at a specific position
   chest = get_entity(Prototype.IronChest, Position(x=10, y=20))

get_entities
~~~~~~~~~~~~

Finds multiple entities in an area.

**Features:**

- Supports filtering by type
- Returns ``List[Entity]``
- Groups connected entities

**Example:**

.. code-block:: python

   # Get all entities
   entities = get_entities()

   # Get entities by type
   drills = get_entities(prototype=Prototype.BurnerMiningDrill)

Resource Operations
-------------------

nearest
~~~~~~~

Locates closest resources/entities.

**Features:**

- Finds ores, water, trees
- Returns ``Position`` object
- 500 tile search radius

**Example:**

.. code-block:: python

   # Find nearest iron ore
   iron_position = nearest(Resource.IronOre)

   # Find nearest water
   water_position = nearest(Resource.Water)

get_resource_patch
~~~~~~~~~~~~~~~~~~

Analyzes resource deposits.

**Features:**

- Returns size and boundaries
- Supports all resource types
- Includes total resource amount

**Example:**

.. code-block:: python

   # Get information about an iron ore patch
   patch = get_resource_patch(Resource.IronOre, position)
   print(f"Patch size: {patch.size}")
   print(f"Total iron: {patch.amount}")

harvest_resource
~~~~~~~~~~~~~~~~

Gathers resources from the world.

**Features:**

- Supports ores, trees, rocks
- Auto-collects to inventory
- Returns amount harvested

**Example:**

.. code-block:: python

   # Harvest iron ore manually
   iron_position = nearest(Resource.IronOre)
   harvested = harvest_resource(iron_position, quantity=50)

Connections
-----------

connect_entities
~~~~~~~~~~~~~~~~

Creates connections between entities.

**Features:**

- Handles belts, pipes, power
- Automatic pathfinding
- Returns connection group

**Example:**

.. code-block:: python

   # Connect a drill to a chest with a transport belt
   connection = connect_entities(
       drill.drop_position,
       chest.position,
       connection_type=Prototype.TransportBelt
   )

get_connection_amount
~~~~~~~~~~~~~~~~~~~~~

Calculates required connection items.

**Features:**

- Pre-planning tool
- Works with all connection types
- Returns item count needed

**Example:**

.. code-block:: python

   # Calculate how many belts are needed
   amount = get_connection_amount(
       start_position=drill.drop_position,
       end_position=chest.position,
       connection_type=Prototype.TransportBelt
   )
   print(f"Need {amount} belts")

Crafting & Research
-------------------

craft_item
~~~~~~~~~~

Creates items from components.

**Features:**

- Handles recursive crafting
- Validates technology requirements
- Returns crafted amount

**Example:**

.. code-block:: python

   # Craft 10 iron gear wheels
   crafted = craft_item(Prototype.IronGearWheel, quantity=10)

get_prototype_recipe
~~~~~~~~~~~~~~~~~~~~

Retrieves crafting requirements.

**Features:**

- Shows ingredients/products
- Includes crafting time
- Returns ``Recipe`` object

**Example:**

.. code-block:: python

   # Get recipe for electronic circuits
   recipe = get_prototype_recipe(Prototype.ElectronicCircuit)
   print(f"Ingredients: {recipe.ingredients}")
   print(f"Crafting time: {recipe.energy}")

set_entity_recipe
~~~~~~~~~~~~~~~~~

Configures machine crafting recipes.

**Features:**

- Works with assemblers/chemical plants
- Validates recipe requirements
- Returns updated entity

**Example:**

.. code-block:: python

   # Set an assembling machine to craft iron gear wheels
   assembler = get_entity(Prototype.AssemblingMachine1, position)
   set_entity_recipe(assembler, Prototype.IronGearWheel)

set_research
~~~~~~~~~~~~

Initiates technology research.

**Features:**

- Validates prerequisites
- Returns required ingredients
- Handles research queue

**Example:**

.. code-block:: python

   # Start researching automation
   research = set_research(Technology.Automation)

get_research_progress
~~~~~~~~~~~~~~~~~~~~~

Monitors research status.

**Features:**

- Shows remaining requirements
- Tracks progress percentage
- Returns ingredient list

**Example:**

.. code-block:: python

   # Check research progress
   progress = get_research_progress()
   print(f"Current research: {progress.name}")
   print(f"Progress: {progress.level}%")

Movement & Utility
------------------

move_to
~~~~~~~

Moves player to position.

**Features:**

- Pathfinds around obstacles
- Can place items while moving
- Returns final position

**Example:**

.. code-block:: python

   # Move to iron ore patch
   iron_position = nearest(Resource.IronOre)
   move_to(iron_position)

nearest_buildable
~~~~~~~~~~~~~~~~~

Finds valid building locations.

**Features:**

- Respects entity dimensions
- Handles resource requirements
- Returns buildable position

**Example:**

.. code-block:: python

   # Find a buildable position near iron ore
   buildable_pos = nearest_buildable(
       resource=Resource.IronOre,
       entity=Prototype.BurnerMiningDrill
   )

sleep
~~~~~

Pauses execution.

**Features:**

- Waits for actions to complete
- Adapts to game speed
- Maximum 15 second duration

**Example:**

.. code-block:: python

   # Wait for 5 seconds for production to occur
   sleep(5)

   # Check drill status after waiting
   drill = get_entity(Prototype.BurnerMiningDrill, drill_position)
   print(f"Drill status: {drill.status}")

launch_rocket
~~~~~~~~~~~~~

Controls rocket silo launches.

**Features:**

- Validates launch requirements
- Handles launch sequence
- Returns updated silo state

**Example:**

.. code-block:: python

   # Launch a rocket
   silo = get_entity(Prototype.RocketSilo, silo_position)
   launch_rocket(silo)

Output
------

print
~~~~~

Outputs debug information to stdout.

**Features:**

- Supports various object types
- Useful for monitoring state
- Returns formatted string

**Example:**

.. code-block:: python

   # Print entity information
   drill = get_entity(Prototype.BurnerMiningDrill, position)
   print(f"Drill: {drill}")
   print(f"Status: {drill.status}")
   print(f"Position: {drill.position}")

   # Print inventory
   inventory = inspect_inventory()
   print(f"Inventory: {inventory}")

Best Practices
--------------

1. **Store Results**: Save tool results as variables for later reference

   .. code-block:: python

      my_drill = place_entity(...)
      # Later...
      print(my_drill.status)

2. **Check Status**: Verify entity status after operations

   .. code-block:: python

      drill = place_entity(...)
      sleep(5)
      assert drill.status == EntityStatus.WORKING

3. **Handle Errors**: Use try-except for error handling

   .. code-block:: python

      try:
          drill = place_entity(...)
      except InvalidEntityPlacementException as e:
          print(f"Placement failed: {e}")

4. **Print for Debugging**: Use ``print()`` to observe state

   .. code-block:: python

      print(f"Entities: {get_entities()}")
      print(f"Inventory: {inspect_inventory()}")

5. **Wait for Actions**: Use ``sleep()`` to allow time for completion

   .. code-block:: python

      place_entity(...)
      sleep(10)  # Wait for production

Next Steps
----------

- Learn how to :doc:`custom_tools` for specialized functionality
- Review :doc:`overview` for architectural details
- See :doc:`../getting_started/quickstart` for usage examples
