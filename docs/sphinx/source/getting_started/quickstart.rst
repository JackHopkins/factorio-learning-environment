First Agent in FLE
==================

This guide will walk you through creating your first agent in the Factorio Learning Environment.

Basic Observation and Action Spaces
------------------------------------

FLE agents interact with the game through a **REPL** (Read-Eval-Print-Loop) pattern:

1. **Observation**: The agent observes the world through the output streams (stderr/stdout) of their last program.
2. **Action**: The agent generates a Python program to perform their desired action.
3. **Feedback**: The environment executes the program, assigns variables, add classes/functions to the namespace, and provides an output stream.

Basic Example
^^^^^^^^^^^^^

Here's a simple example of an agent placing a mining drill and chest:

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

The environment will execute this code and return feedback showing the entities that were created.

Gym Environment Usage
---------------------

The Factorio Learning Environment uses a gym environment registry to automatically discover and register all available tasks. This allows you to use ``gym.make()`` to create environments and reference them by their environment IDs.

List Available Environments
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from gym_env.registry import list_available_environments

   # Get all available environment IDs
   env_ids = list_available_environments()
   print(f"Available environments: {env_ids}")

Or use the command-line tool:

.. code-block:: bash

   python fle/env/gym_env/example_usage.py --list

Create an Environment
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import gym

   # Create any available environment
   env = gym.make("iron_ore_throughput")

Use the Environment
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from fle.env.gym_env.action import Action

   # Reset the environment
   obs = env.reset(options={'game_state': None})

   # Take an action
   action = Action(
       agent_idx=0,  # Which agent takes the action
       code='print("Hello Factorio!")',  # Python code to execute
       game_state=None  # Optional: game state to reset to before running code
   )

   # Execute the action
   obs, reward, terminated, truncated, info = env.step(action)

   # Clean up
   env.close()

Available Environments
^^^^^^^^^^^^^^^^^^^^^^

The registry automatically discovers all task definitions and creates corresponding gym environments using the task key as the environment ID.

Throughput Tasks (Lab Play)
""""""""""""""""""""""""""""

All throughput tasks are defined in ``fle/eval/tasks/task_definitions/lab_play/throughput_tasks.py``. The 24 available tasks are:

- **Circuits**: ``advanced_circuit_throughput``, ``electronic_circuit_throughput``, ``processing_unit_throughput``
- **Science Packs**: ``automation_science_pack_throughput``, ``logistics_science_pack_throughput``, ``chemical_science_pack_throughput``, ``military_science_pack_throughput``, ``production_science_pack_throughput``, ``utility_science_pack_throughput``
- **Components**: ``battery_throughput``, ``engine_unit_throughput``, ``inserter_throughput``, ``iron_gear_wheel_throughput``, ``low_density_structure_throughput``
- **Raw Materials**: ``iron_ore_throughput``, ``iron_plate_throughput``, ``steel_plate_throughput``, ``plastic_bar_throughput``
- **Oil & Chemicals**: ``crude_oil_throughput``, ``petroleum_gas_throughput``, ``sufuric_acid_throughput``, ``sulfur_throughput``
- **Military**: ``piercing_round_throughput``, ``stone_wall_throughput``

Most tasks require 16 items per 60 seconds; fluid tasks require 250 units per 60 seconds.

Example Usage
"""""""""""""

.. code-block:: python

   # Create a throughput environment
   env = gym.make("iron_plate_throughput")
   env = gym.make("automation_science_pack_throughput")
   env = gym.make("crude_oil_throughput")

   # Create open play environment
   env = gym.make("open_play")

Environment Interface
^^^^^^^^^^^^^^^^^^^^^

All environments follow the standard gym interface:

Action Space
""""""""""""

.. code-block:: python

   {
       'agent_idx': Discrete(instance.num_agents),  # Index of the agent taking the action
       'game_state': Text(max_length=1000000),      # Optional: game state to reset to before running code
       'code': Text(max_length=10000)               # Python code to execute
   }

Observation Space
"""""""""""""""""

The observation space includes:

- ``raw_text``: Output from the last action
- ``entities``: List of entities on the map
- ``inventory``: Current inventory state
- ``research``: Research progress and technologies
- ``game_info``: Game state (tick, time, speed)
- ``score``: Current score
- ``flows``: Production statistics
- ``task_verification``: Task completion status
- ``messages``: Inter-agent messages
- ``serialized_functions``: Available functions
- ``task_info``: Information about the task
- ``map_image``: Base64 encoded PNG image

Methods
"""""""

- ``reset(options: Dict[str, Any], seed: Optional[int] = None) -> Dict[str, Any]``
- ``step(action: Action) -> Tuple[Dict[str, Any], float, bool, bool, Dict[str, Any]]``
- ``close() -> None``

Complete Example
^^^^^^^^^^^^^^^^

Here's a complete example that demonstrates the full workflow:

.. code-block:: python

   import gym
   from fle.env.gym_env.registry import list_available_environments, get_environment_info
   from fle.env.gym_env.action import Action

   # 1. List available environments
   env_ids = list_available_environments()
   print(f"Found {len(env_ids)} environments")

   # 2. Get information about a specific environment
   info = get_environment_info("iron_ore_throughput")
   print(f"Description: {info['description']}")

   # 3. Create the environment
   env = gym.make("iron_ore_throughput")

   # 4. Use the environment
   obs = env.reset(options={'game_state': None})
   print(f"Initial observation keys: {list(obs.keys())}")

   # 5. Take actions
   current_state = None
   for step in range(5):
       action = Action(
           agent_idx=0,
           game_state=current_state,
           code=f'print("Step {step}: Hello Factorio!")'
       )
       obs, reward, terminated, truncated, info = env.step(action)
       done = terminated or truncated
       current_state = info['output_game_state']
       print(f"Step {step}: Reward={reward}, Done={done}")

       if done:
           break

   # 6. Clean up
   env.close()
