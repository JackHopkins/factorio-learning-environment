Quickstart
==========

Use the CLI:

.. code-block:: bash

   # Start Factorio cluster
   fle cluster start
   
   # Run evaluation trajectories (requires [eval] dependencies)
   fle eval --config configs/gym_run_config.json

.. note::
   When you run `fle init` or `fle eval` for the first time, an `.env` file and a `configs/` directory with example configurations are created automatically

Environment Overview
--------------------

FLE is an agent evaluation environment built on the game of Factorio, a popular resource management simulation game.

Agents interact with **FLE** by code synthesis through a **REPL** (Read-Eval-Print-Loop) pattern:

1. **Observation**: The agent observes the world through the output streams (stderr/stdout) of their last program.
2. **Action**: The agent generates a Python program to perform their desired action.
3. **Feedback**: The environment executes the program, assigns variables, add classes/functions to the namespace, and provides an output stream.

Example Interaction
------------------

.. code-block:: python

   # 1. Get iron patch and place mining drill
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=nearest(Resource.IronOre),
       direction=Direction.NORTH
   )
   # 2. Add output storage
   chest = place_entity_next_to(
       entity=Prototype.IronChest,
       reference_position=drill.drop_position,
       direction=Direction.SOUTH
   )
   # 3. Verify automation chain and observe entities
   sleep(10) # Sleep for 10 seconds
   assert drill.status == EntityStatus.WORKING
   print(get_entities())

**Feedback:**

.. code-block:: python

   >>> [ BurnerMiningDrill(fuel=Inventory({'coal': 4}), 
   >>>                     name='burner-mining-drill', 
   >>>                     direction=Direction.DOWN, 
   >>>                     position=Position(x=-28.0, y=-61.0), 
   >>>                     energy=2666.6666666667, 
   >>>                     tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), 
   >>>                     status=EntityStatus.WORKING, 
   >>>                     neighbours=[Entity(name='iron-chest', direction=DOWN, position=Position(x=-27.5 y=-59.5)], 
   >>>                     drop_position=Position(x=-27.5, y=-59.5), 
   >>>                     resources=[Ingredient(name='iron-ore', count=30000, type=None)]),
   >>>   Chest(name='iron-chest', 
   >>>         direction=Direction.UP, 
   >>>         position=Position(x=-27.5, y=-59.5), 
   >>>         energy=0.0, 
   >>>         tile_dimensions=TileDimensions(tile_width=1.0, tile_height=1.0), 
   >>>         status=EntityStatus.NORMAL, 
   >>>         inventory=Inventory({'iron-ore': 75}))]

Key Concepts
------------

**Tools and Namespace**
   Agents are provided with the Python standard library, and an API comprising :doc:`tools <../api/tools>` that they can use.

   Tools are functions that perform a game action and return a typed object (e.g an Inventory), which can be stored as a named **variable** in the Python namespace for later use.

   The namespace acts as an episodic symbolic memory system, and saved objects represent an observation of the environment at the moment of query.

   This enables agents to maintain complex state representations and build hierarchical abstractions as the factories scale.

**Observation Streams**
   Agents observe **stdout** and **stderr** - the output streams of their program. Agents may intentionally choose to print relevant objects and computations to the output stream to construct observations.

   Mistakes in the code or invalid operations raise typed **exceptions** with detailed context that is written to stderr.

   This enables agents to reactively debug their programs after execution, and proactively use runtime assertions during execution to self-verify their actions.

**Code Enhancement**
   Agents are able to enhance their internal representation of the game state by defining:

   1. Utility functions for reuse throughout an episode, to encapsulate previously successful logic
   2. Classes in the namespace to better organize the data retrieved from the game.

Next Steps
----------

- Learn about the :doc:`environment API <../api/environment>`
- Explore available :doc:`tools <../api/tools>`
- See :doc:`examples <../examples/basic_agent>` of agent implementations
