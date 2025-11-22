Environment Overview
====================

FLE is an agent evaluation environment built on the game of Factorio, a popular resource management simulation game.

The REPL Pattern
-----------------

Agents interact with FLE through code synthesis using a **REPL** (Read-Eval-Print-Loop) pattern:

1. **Observation**: The agent observes the world through the output streams (stderr/stdout) of their last program
2. **Action**: The agent generates a Python program to perform their desired action
3. **Feedback**: The environment executes the program, assigns variables, adds classes/functions to the namespace, and provides an output stream

Example Interaction
~~~~~~~~~~~~~~~~~~~

**Action:**

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

Available Tools
---------------

Agents are provided with the Python standard library and an API comprising :doc:`../tools/overview` that they can use.

**Tools** are functions that:

- Perform a game action
- Return a typed object (e.g. an ``Inventory``)
- Can be stored as a named **variable** in the Python namespace for later use

The Namespace
-------------

The namespace acts as an **episodic symbolic memory system**. Saved objects represent an observation of the environment at the moment of query.

This enables agents to:

- Maintain complex state representations
- Build hierarchical abstractions as factories scale
- Reference previous observations and computations

Observations
------------

Agents observe **stdout** and **stderr** - the output streams of their program.

Agents may intentionally:

- Print relevant objects to construct observations
- Print computations and intermediate results
- Use ``print()`` strategically to monitor state

Error Handling
--------------

Mistakes in code or invalid operations raise typed **exceptions** with detailed context that is written to stderr.

This enables agents to:

- **Reactively debug** their programs after execution
- **Proactively use** runtime assertions during execution to self-verify actions
- Learn from detailed error messages

Custom Functions and Classes
-----------------------------

Agents can enhance their internal representation of the game state by defining:

1. **Utility functions** for reuse throughout an episode, to encapsulate previously successful logic
2. **Classes** in the namespace to better organize the data retrieved from the game

These definitions persist in the namespace across actions within an episode.

Action Space
------------

The action space is defined as:

.. code-block:: python

   {
       'agent_idx': Discrete(instance.num_agents),  # Index of the agent taking the action
       'game_state': Text(max_length=1000000),      # Optional: game state to reset to
       'code': Text(max_length=10000)               # Python code to execute
   }

Observation Space
-----------------

The observation space includes:

- ``raw_text``: Output from the last action
- ``entities``: List of entities on the map
- ``inventory``: Current inventory state
- ``research``: Research progress and technologies
- ``game_info``: Game state (tick, time, speed)
- ``score``: Current score
- ``flows``: Production statistics
- ``task_verification``: Task completion status
- ``messages``: Inter-agent messages (for multi-agent scenarios)
- ``serialized_functions``: Available functions
- ``task_info``: Information about the task
- ``map_image``: Base64 encoded PNG image

Environment Methods
-------------------

Standard Gym Interface
~~~~~~~~~~~~~~~~~~~~~~

All FLE environments follow the standard OpenAI Gym interface:

.. code-block:: python

   # Reset the environment
   obs = env.reset(options: Dict[str, Any], seed: Optional[int] = None) -> Dict[str, Any]

   # Take a step
   obs, reward, terminated, truncated, info = env.step(action: Action)

   # Clean up
   env.close()

Architecture
------------

.. code-block:: text

   ┌─────────────────┐
   │     Agent       │
   │ (Synthesizes    │
   │  Python Code)   │
   └────────┬────────┘
            │
            ▼
   ┌─────────────────────────────┐
   │  Learning Environment       │
   │  ┌─────────────────────┐   │
   │  │   Interpreter       │   │
   │  │   - Executes code   │   │
   │  │   - Manages         │   │
   │  │     namespace       │   │
   │  └──────┬──────────────┘   │
   │         │                   │
   │  ┌──────▼──────────────┐   │
   │  │   client.py         │   │
   │  │   (Tool Interface)  │   │
   │  └──────┬──────────────┘   │
   └─────────┼──────────────────┘
             │ Remote TCP Call
             ▼
   ┌─────────────────────────────┐
   │   Factorio Server           │
   │  ┌─────────────────────┐   │
   │  │   server.lua        │   │
   │  │   (Game Logic)      │   │
   │  └──────┬──────────────┘   │
   │         │                   │
   │  ┌──────▼──────────────┐   │
   │  │  Factorio Engine    │   │
   │  │  (Game Simulation)  │   │
   │  └─────────────────────┘   │
   └─────────────────────────────┘

Task Types
----------

FLE provides two main evaluation settings:

Lab-Play
~~~~~~~~

24 structured tasks with fixed resources, testing specific capabilities:

- **Circuits**: Advanced circuits, electronic circuits, processing units
- **Science Packs**: Automation, logistics, chemical, military, production, utility
- **Components**: Batteries, engines, inserters, gears, low density structures
- **Raw Materials**: Iron ore, iron plates, steel plates, plastic bars
- **Oil & Chemicals**: Crude oil, petroleum gas, sulfuric acid, sulfur
- **Military**: Piercing rounds, stone walls

Most tasks require 16 items per 60 seconds; fluid tasks require 250 units per 60 seconds.

Open-Play
~~~~~~~~~

An unbounded task of building the largest possible factory on a procedurally generated map. This tests:

- Long-term planning
- Resource optimization
- Scaling strategies
- Error recovery

Next Steps
----------

- Explore the :doc:`gym_registry` to see all available tasks
- Learn about :doc:`../tools/overview` available to agents
- See :doc:`../getting_started/quickstart` for usage examples
