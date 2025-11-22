Quickstart
==========

This guide will get you up and running with FLE in minutes.

CLI Commands
------------

Starting the Factorio Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Start Factorio cluster
   fle cluster start

Running Evaluations
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run evaluation trajectories (requires [eval] dependencies)
   fle eval --config configs/gym_run_config.json

.. note::
   When you run ``fle init`` or ``fle eval`` for the first time, an ``.env`` file and a ``configs/`` directory with example configurations are created automatically.

Basic Usage Example
-------------------

Here's a complete example demonstrating how to use FLE with the Gym interface:

.. code-block:: python

   import gym
   from fle.env.gym_env.action import Action

   # Create an environment
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

Understanding the REPL Pattern
-------------------------------

Agents interact with FLE through a **REPL** (Read-Eval-Print-Loop) pattern:

1. **Observation**: The agent observes the world through the output streams (stderr/stdout) of their last program
2. **Action**: The agent generates a Python program to perform their desired action
3. **Feedback**: The environment executes the program and provides an output stream

Example Action-Feedback Cycle
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Listing Available Environments
-------------------------------

.. code-block:: python

   from fle.env.gym_env.registry import list_available_environments

   # Get all available environment IDs
   env_ids = list_available_environments()
   print(f"Available environments: {env_ids}")

Or use the command-line tool:

.. code-block:: bash

   python fle/env/gym_env/example_usage.py --list

Creating Different Environments
--------------------------------

.. code-block:: python

   import gym

   # Create throughput environments
   env = gym.make("iron_plate_throughput")
   env = gym.make("automation_science_pack_throughput")
   env = gym.make("crude_oil_throughput")

   # Create open play environment
   env = gym.make("open_play")

Complete Workflow Example
--------------------------

Here's a complete example demonstrating the full workflow:

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

Next Steps
----------

- Learn about the :doc:`../environment/overview` and how agents interact with it
- Explore the :doc:`../tools/overview` available to agents
- Check out the :doc:`../environment/gym_registry` for available tasks
