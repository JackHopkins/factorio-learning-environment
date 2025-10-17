Environment API
===============

The Factorio Learning Environment provides a comprehensive API for interacting with the game through Python code synthesis.

Core Concepts
-------------

**FactorioInstance**
   The main interface for interacting with a Factorio game instance. Provides access to all game state and tools.

**Namespace Management**
   Python namespace that persists across agent actions, allowing for stateful interactions and code reuse.

**Gym Environment Integration**
   Standard OpenAI Gym interface for reinforcement learning integration.

FactorioInstance
----------------

.. autoclass:: fle.env.instance.FactorioInstance
   :members:
   :undoc-members:
   :show-inheritance:

Key Methods
~~~~~~~~~~~

.. automethod:: fle.env.instance.FactorioInstance.reset
.. automethod:: fle.env.instance.FactorioInstance.step
.. automethod:: fle.env.instance.FactorioInstance.close

Namespace Management
--------------------

.. autoclass:: fle.env.namespace.Namespace
   :members:
   :undoc-members:
   :show-inheritance:

The namespace provides:

- **Variable Storage**: Store and retrieve objects between actions
- **Function Definitions**: Define reusable functions
- **Class Definitions**: Create custom data structures
- **Import Management**: Handle Python imports and modules

Gym Environment
---------------

.. autoclass:: fle.env.gym_env.FactorioGymEnv
   :members:
   :undoc-members:
   :show-inheritance:

The gym environment provides:

- **Standard Interface**: Compatible with OpenAI Gym
- **Action Space**: Structured action space for agent actions
- **Observation Space**: Rich observation space with game state
- **Reward System**: Configurable reward functions

Environment Registry
--------------------

FLE uses a gym environment registry to automatically discover and register all available tasks.

.. autofunction:: fle.env.gym_env.registry.list_available_environments
.. autofunction:: fle.env.gym_env.registry.get_environment_info
.. autofunction:: fle.env.gym_env.registry.register_all_environments

Available Environments
~~~~~~~~~~~~~~~~~~~~~~~

**Throughput Tasks (Lab Play)**
   All throughput tasks are defined in `fle/eval/tasks/task_definitions/lab_play/throughput_tasks.py`. The 24 available tasks are:

   - **Circuits**: `advanced_circuit_throughput`, `electronic_circuit_throughput`, `processing_unit_throughput`
   - **Science Packs**: `automation_science_pack_throughput`, `logistics_science_pack_throughput`, `chemical_science_pack_throughput`, `military_science_pack_throughput`, `production_science_pack_throughput`, `utility_science_pack_throughput`
   - **Components**: `battery_throughput`, `engine_unit_throughput`, `inserter_throughput`, `iron_gear_wheel_throughput`, `low_density_structure_throughput`
   - **Raw Materials**: `iron_ore_throughput`, `iron_plate_throughput`, `steel_plate_throughput`, `plastic_bar_throughput`
   - **Oil & Chemicals**: `crude_oil_throughput`, `petroleum_gas_throughput`, `sufuric_acid_throughput`, `sulfur_throughput`
   - **Military**: `piercing_round_throughput`, `stone_wall_throughput`

   Most tasks require 16 items per 60 seconds; fluid tasks require 250 units per 60 seconds.

**Open Play**
   Unbounded task of building the largest possible factory: `open_play`

Example Usage
-------------

.. code-block:: python

   import gym
   from fle.env.gym_env.action import Action
   
   # Create any available environment
   env = gym.make("iron_ore_throughput")
   
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

Error Handling
--------------

The environment includes comprehensive error handling for:

- Missing task definition files
- Invalid JSON configurations
- Missing Factorio containers
- Environment creation failures
- Network connectivity issues

If an environment fails to load, a warning will be printed but the registry will continue to load other environments.
