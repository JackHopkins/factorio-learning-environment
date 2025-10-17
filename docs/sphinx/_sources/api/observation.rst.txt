Observation Space
==================

The observation space provides rich information about the current game state, allowing agents to make informed decisions.

Observation Structure
--------------------

The observation space includes the following components:

**raw_text**
   Output from the last action (stdout/stderr)

**entities**
   List of entities on the map with their current state

**inventory**
   Current inventory state of the player

**research**
   Research progress and available technologies

**game_info**
   Game state information (tick, time, speed)

**score**
   Current score and performance metrics

**flows**
   Production statistics and resource flows

**task_verification**
   Task completion status and progress

**messages**
   Inter-agent communication messages

**serialized_functions**
   Available functions and their signatures

**task_info**
   Information about the current task

**map_image**
   Base64 encoded PNG image of the current map

Entity Information
------------------

Entities provide detailed information about game objects:

.. autoclass:: fle.env.entities.Entity
   :members:
   :undoc-members:
   :show-inheritance:

Entity Types
~~~~~~~~~~~~

**MiningDrill**
   Mining drills for extracting resources

**Chest**
   Storage containers for items

**AssemblingMachine**
   Machines for crafting items

**Inserter**
   Transport devices for moving items

**TransportBelt**
   Conveyor belts for item transport

**Pipe**
   Fluid transport systems

**PowerPole**
   Electrical distribution

**Lab**
   Research facilities

Position and Direction
----------------------

.. autoclass:: fle.env.game_types.Position
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: fle.env.game_types.Direction
   :members:
   :undoc-members:
   :show-inheritance:

Inventory Management
--------------------

.. autoclass:: fle.env.game_types.Inventory
   :members:
   :undoc-members:
   :show-inheritance:

The inventory system provides:

- **Item Storage**: Store and retrieve items
- **Count Methods**: Query item quantities
- **Type Validation**: Ensure item compatibility
- **Transfer Operations**: Move items between inventories

Research System
---------------

.. autoclass:: fle.env.game_types.Research
   :members:
   :undoc-members:
   :show-inheritance:

Research provides:

- **Technology Tree**: Available technologies
- **Prerequisites**: Required research
- **Progress Tracking**: Current research status
- **Unlock Management**: New technologies and recipes

Game State Information
----------------------

.. autoclass:: fle.env.game_types.GameInfo
   :members:
   :undoc-members:
   :show-inheritance:

Game info includes:

- **Tick Information**: Current game tick
- **Time Data**: Game time and speed
- **Performance Metrics**: FPS and UPS
- **Map Information**: World size and generation

Task Verification
----------------

.. autoclass:: fle.env.game_types.TaskVerification
   :members:
   :undoc-members:
   :show-inheritance:

Task verification provides:

- **Completion Status**: Whether the task is complete
- **Progress Metrics**: Current progress toward goals
- **Objective Tracking**: Individual objective status
- **Performance Data**: Efficiency and throughput metrics

Example Observation
-------------------

.. code-block:: python

   {
       'raw_text': 'Hello Factorio!',
       'entities': [
           Entity(name='burner-mining-drill', position=Position(x=-28.0, y=-61.0), ...),
           Entity(name='iron-chest', position=Position(x=-27.5, y=-59.5), ...)
       ],
       'inventory': Inventory({'iron-ore': 75, 'coal': 4}),
       'research': Research(technologies=['automation'], progress=0.5),
       'game_info': GameInfo(tick=1000, time=16.67, speed=1.0),
       'score': 150,
       'flows': {'iron-ore': 2.5, 'iron-plate': 1.2},
       'task_verification': TaskVerification(complete=False, progress=0.3),
       'messages': [],
       'serialized_functions': ['place_entity', 'get_entities', ...],
       'task_info': {'name': 'iron_ore_throughput', 'target': 16},
       'map_image': 'iVBORw0KGgoAAAANSUhEUgAA...'
   }
