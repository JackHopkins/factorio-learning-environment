Gym Environment Registry
========================

The Factorio Learning Environment uses a gym environment registry to automatically discover and register all available tasks. This allows you to use ``gym.make()`` to create environments and reference them by their environment IDs.

Overview
--------

The registry system automatically discovers all task definitions in ``fle/eval/tasks/task_definitions/`` and registers them as gym environments. This means you can create any Factorio environment using the familiar ``gym.make()`` pattern.

Features
--------

- **Automatic Discovery**: Automatically discovers all task definitions in ``fle/eval/tasks/task_definitions/``
- **Gym Integration**: All environments are registered with ``gym`` and can be created using ``gym.make()``
- **Task Metadata**: Provides access to task descriptions, configurations, and metadata
- **Multi-agent Support**: Supports both single-agent and multi-agent environments
- **Command-line Tools**: Built-in tools for exploring and testing environments

Quick Start
-----------

1. List Available Environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from fle.env.gym_env.registry import list_available_environments

   # Get all available environment IDs
   env_ids = list_available_environments()
   print(f"Available environments: {env_ids}")

Or use the command-line tool:

.. code-block:: bash

   python fle/env/gym_env/example_usage.py --list

2. Create an Environment
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import gym

   # Create any available environment
   env = gym.make("iron_ore_throughput")

3. Use the Environment
~~~~~~~~~~~~~~~~~~~~~~

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
----------------------

Throughput Tasks (Lab Play)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All throughput tasks are defined in ``fle/eval/tasks/task_definitions/lab_play/throughput_tasks.py``. The 24 available tasks are:

**Circuits**

- ``advanced_circuit_throughput``
- ``electronic_circuit_throughput``
- ``processing_unit_throughput``

**Science Packs**

- ``automation_science_pack_throughput``
- ``logistics_science_pack_throughput``
- ``chemical_science_pack_throughput``
- ``military_science_pack_throughput``
- ``production_science_pack_throughput``
- ``utility_science_pack_throughput``

**Components**

- ``battery_throughput``
- ``engine_unit_throughput``
- ``inserter_throughput``
- ``iron_gear_wheel_throughput``
- ``low_density_structure_throughput``

**Raw Materials**

- ``iron_ore_throughput``
- ``iron_plate_throughput``
- ``steel_plate_throughput``
- ``plastic_bar_throughput``

**Oil & Chemicals**

- ``crude_oil_throughput``
- ``petroleum_gas_throughput``
- ``sulfuric_acid_throughput``
- ``sulfur_throughput``

**Military**

- ``piercing_round_throughput``
- ``stone_wall_throughput``

.. note::
   Most tasks require 16 items per 60 seconds; fluid tasks require 250 units per 60 seconds.

Open Play Environment
~~~~~~~~~~~~~~~~~~~~~

- ``open_play`` - An unbounded task of building the largest possible factory

Example Usage
~~~~~~~~~~~~~

.. code-block:: python

   import gym

   # Create throughput environments
   env = gym.make("iron_plate_throughput")
   env = gym.make("automation_science_pack_throughput")
   env = gym.make("crude_oil_throughput")

   # Create open play environment
   env = gym.make("open_play")

Command-Line Tools
------------------

The ``example_usage.py`` script provides both interactive examples and command-line tools:

.. code-block:: bash

   # Run interactive examples
   python fle/env/gym_env/example_usage.py

   # List all environments
   python fle/env/gym_env/example_usage.py --list

   # Show detailed information
   python fle/env/gym_env/example_usage.py --detail

   # Search for specific environments
   python fle/env/gym_env/example_usage.py --search iron

   # Output in gym.make() format
   python fle/env/gym_env/example_usage.py --gym-format

Environment Interface
---------------------

Action Space
~~~~~~~~~~~~

.. code-block:: python

   {
       'agent_idx': Discrete(instance.num_agents),  # Index of the agent taking the action
       'game_state': Text(max_length=1000000),      # Optional: game state to reset to
       'code': Text(max_length=10000)               # Python code to execute
   }

Observation Space
~~~~~~~~~~~~~~~~~

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
~~~~~~~

.. code-block:: python

   # Reset the environment
   reset(options: Dict[str, Any], seed: Optional[int] = None) -> Dict[str, Any]

   # Take a step
   step(action: Action) -> Tuple[Dict[str, Any], float, bool, bool, Dict[str, Any]]

   # Clean up
   close() -> None

API Reference
-------------

Registry Functions
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Returns a list of all registered environment IDs
   list_available_environments() -> List[str]

   # Returns detailed information about a specific environment
   get_environment_info(env_id: str) -> Optional[Dict[str, Any]]

   # Manually trigger environment discovery and registration
   register_all_environments() -> None

Environment Creation
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Creates a Factorio gym environment
   gym.make(env_id: str, **kwargs) -> FactorioGymEnv

Complete Example
----------------

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

Error Handling
--------------

The registry includes error handling for:

- Missing task definition files
- Invalid JSON configurations
- Missing Factorio containers
- Environment creation failures

If an environment fails to load, a warning will be printed but the registry will continue to load other environments.

Troubleshooting
---------------

Environment Creation Fails
~~~~~~~~~~~~~~~~~~~~~~~~~~

If ``gym.make()`` fails with connection errors:

1. Ensure Factorio containers are running
2. Check that the cluster setup is working
3. Verify network connectivity

No Environments Found
~~~~~~~~~~~~~~~~~~~~~

If no environments are listed:

1. Check that the task definitions directory exists
2. Verify JSON files are valid
3. Check file permissions

Import Errors
~~~~~~~~~~~~~

If you get import errors:

1. Ensure you're running from the correct directory
2. Check that all dependencies are installed
3. Verify the Python path includes the project root

Testing
-------

Run the test suite to verify the registry is working correctly:

.. code-block:: bash

   python fle/env/tests/gym_env/test_registry.py

This registry system provides a clean, standardized interface for working with Factorio gym environments, making it easy to experiment with different tasks and integrate with existing gym-based frameworks.
