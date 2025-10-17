Observation Space
=================

The Factorio Learning Environment provides rich observation spaces that give agents comprehensive information about the game state.

Observation Components
----------------------

Raw Text Output
^^^^^^^^^^^^^^^

The primary observation is the raw text output from the agent's last action:

- **stdout**: Standard output from the executed Python code
- **stderr**: Error messages and debug information

Entities
^^^^^^^^

List of all entities on the map with their current state:

.. code-block:: python

   entities = [
       Entity(
           name='burner-mining-drill',
           position=Position(x=-28.0, y=-61.0),
           status=EntityStatus.WORKING,
           inventory=Inventory({'coal': 4}),
           # ... other properties
       ),
       # ... more entities
   ]

Inventory
^^^^^^^^^

Current player inventory state:

.. code-block:: python

   inventory = Inventory({
       'iron-ore': 100,
       'iron-plate': 50,
       'copper-ore': 75,
       # ... other items
   })

Research
^^^^^^^^

Research progress and available technologies:

.. code-block:: python

   research = {
       'completed': ['automation', 'logistics'],
       'in_progress': 'automation-2',
       'available': ['electronics', 'steel-processing'],
       # ... other research info
   }

Game Info
^^^^^^^^^

General game state information:

.. code-block:: python

   game_info = {
       'tick': 12345,
       'time': '00:12:34',
       'speed': 1.0,
       'evolution_factor': 0.1,
       # ... other game state
   }

Score
^^^^^

Current score and statistics:

.. code-block:: python

   score = {
       'items_produced': {'iron-plate': 1000, 'copper-plate': 500},
       'entities_built': {'mining-drill': 10, 'inserter': 25},
       'research_completed': 5,
       # ... other metrics
   }

Flows
^^^^^

Production statistics and flow rates:

.. code-block:: python

   flows = {
       'iron-ore': {'production': 100, 'consumption': 80, 'net': 20},
       'iron-plate': {'production': 40, 'consumption': 35, 'net': 5},
       # ... other flow data
   }

Task Verification
^^^^^^^^^^^^^^^^^

Task completion status and progress:

.. code-block:: python

   task_verification = {
       'completed': False,
       'progress': 0.75,
       'requirements': {'iron-plate': {'needed': 1000, 'current': 750}},
       # ... other task info
   }

Messages
^^^^^^^^

Inter-agent communication messages:

.. code-block:: python

   messages = [
       {
           'sender': 1,
           'recipient': 0,
           'message': 'I need iron plates',
           'timestamp': 12345,
       },
       # ... other messages
   ]

Serialized Functions
^^^^^^^^^^^^^^^^^^^^

Available functions that can be called:

.. code-block:: python

   serialized_functions = {
       'place_entity': '...',
       'craft_item': '...',
       'move_to': '...',
       # ... other available functions
   }

Task Info
^^^^^^^^^

Information about the current task:

.. code-block:: python

   task_info = {
       'name': 'iron_plate_throughput',
       'description': 'Produce 16 iron plates per 60 seconds',
       'time_limit': 3600,
       'success_criteria': {...},
       # ... other task details
   }

Map Image
^^^^^^^^^

Base64 encoded PNG image of the current map view:

.. code-block:: python

   map_image = 'iVBORw0KGgoAAAANSUhEUgAA...'  # Base64 encoded PNG

Observation Space Structure
---------------------------

The complete observation space follows this structure:

.. code-block:: python

   {
       'raw_text': str,           # Combined stdout/stderr output
       'entities': List[Entity],  # All entities on map
       'inventory': Inventory,    # Player inventory
       'research': Dict,          # Research state
       'game_info': Dict,         # Game state info
       'score': Dict,             # Score and metrics
       'flows': Dict,             # Production flows
       'task_verification': Dict, # Task progress
       'messages': List[Dict],    # Inter-agent messages
       'serialized_functions': Dict, # Available functions
       'task_info': Dict,         # Task information
       'map_image': str,          # Base64 encoded map image
   }

Using Observations
------------------

Agents can use these observations to:

1. **Understand Current State**: Check inventory, entity positions, and game progress
2. **Plan Actions**: Use flow data and task requirements to plan production
3. **Debug Issues**: Use error messages and entity states to identify problems
4. **Coordinate**: Use messages for multi-agent coordination
5. **Monitor Progress**: Track task completion and score metrics

Example Observation Usage
-------------------------

.. code-block:: python

   # Check current inventory
   if obs['inventory']['iron-ore'] < 100:
       # Need more iron ore
       iron_patch = nearest(Resource.IronOre)
       move_to(iron_patch)

   # Check entity status
   for entity in obs['entities']:
       if entity.name == 'mining-drill' and entity.status != EntityStatus.WORKING:
           # Mining drill not working, check fuel
           print(f"Drill at {entity.position} status: {entity.status}")

   # Monitor task progress
   if obs['task_verification']['progress'] > 0.9:
       # Almost done with task
       print("Task nearly complete!")

   # Check for messages from other agents
   for msg in obs['messages']:
       if 'iron-plate' in msg['message']:
           # Another agent needs iron plates
           send_message("I can provide iron plates", recipient=msg['sender'])
