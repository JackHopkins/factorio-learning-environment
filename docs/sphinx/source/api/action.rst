Action Space
============

The Factorio Learning Environment uses a unique action space based on code synthesis. Agents generate Python code that is executed in the game environment.

Action Structure
----------------

The action space consists of three components:

.. code-block:: python

   {
       'agent_idx': int,      # Index of the agent taking the action
       'game_state': str,     # Optional: game state to reset to before running code
       'code': str           # Python code to execute
   }

Agent Index
-----------

The ``agent_idx`` specifies which agent is taking the action. This is important for multi-agent scenarios where multiple agents are operating simultaneously.

Game State
----------

The ``game_state`` parameter is optional and allows agents to reset the game to a specific state before executing their code. This is useful for:

- **Rollback scenarios**: Undoing previous actions
- **State management**: Returning to a known good state
- **Error recovery**: Recovering from failed actions

Code Synthesis
--------------

The ``code`` parameter contains Python code that the agent wants to execute. This code has access to:

1. **Python Standard Library**: All built-in Python functions and modules
2. **FLE Tools**: Specialized functions for interacting with the game
3. **Namespace**: Previously defined variables and functions from earlier actions

Code Execution Environment
--------------------------

When code is executed, it runs in a controlled environment with:

- **Sandboxed execution**: Limited access to system resources
- **Game state access**: Full access to current game state through tools
- **Persistent namespace**: Variables and functions persist between actions
- **Error handling**: Exceptions are captured and returned as observations

Example Actions
---------------

Basic Movement
^^^^^^^^^^^^^^

.. code-block:: python

   action = Action(
       agent_idx=0,
       game_state=None,
       code='''
   # Move to iron ore patch
   iron_pos = nearest(Resource.IronOre)
   final_pos = move_to(iron_pos)
   print(f"Moved to iron ore at {final_pos}")
   '''
   )

Entity Placement
^^^^^^^^^^^^^^^^

.. code-block:: python

   action = Action(
       agent_idx=0,
       game_state=None,
       code='''
   # Place mining drill and chest
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=nearest(Resource.IronOre),
       direction=Direction.NORTH
   )
   chest = place_entity_next_to(
       entity=Prototype.IronChest,
       reference_position=drill.drop_position,
       direction=Direction.SOUTH
   )
   print(f"Placed drill at {drill.position} and chest at {chest.position}")
   '''
   )

Complex Automation
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   action = Action(
       agent_idx=0,
       game_state=None,
       code='''
   # Create automated iron plate production
   def setup_iron_production():
       # Find iron ore patch
       iron_pos = nearest(Resource.IronOre)
       
       # Place mining drill
       drill = place_entity(
           entity=Prototype.MiningDrill,
           position=iron_pos,
           direction=Direction.NORTH
       )
       
       # Place chest for output
       chest = place_entity_next_to(
           entity=Prototype.IronChest,
           reference_position=drill.drop_position,
           direction=Direction.SOUTH
       )
       
       # Place furnace
       furnace = place_entity(
           entity=Prototype.StoneFurnace,
           position=Position(x=iron_pos.x + 5, y=iron_pos.y),
           direction=Direction.NORTH
       )
       
       # Connect with belts
       connect_entities(drill, chest)
       connect_entities(chest, furnace)
       
       return drill, chest, furnace
   
   # Execute the setup
   drill, chest, furnace = setup_iron_production()
   print("Iron production setup complete")
   '''
   )

State Management
^^^^^^^^^^^^^^^^

.. code-block:: python

   action = Action(
       agent_idx=0,
       game_state=previous_state,
       code='''
   # Continue from previous state
   # Check if our previous setup is still working
   entities = get_entities()
   working_drills = [e for e in entities if e.name == 'mining-drill' and e.status == EntityStatus.WORKING]
   print(f"Found {len(working_drills)} working drills")
   
   # If no working drills, rebuild
   if not working_drills:
       print("Rebuilding iron production...")
       # ... rebuild code ...
   '''
   )

Multi-Agent Coordination
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   action = Action(
       agent_idx=0,
       game_state=None,
       code='''
   # Check for messages from other agents
   messages = get_messages()
   for msg in messages:
       if 'iron-plate' in msg['message']:
           # Another agent needs iron plates
           if inventory['iron-plate'] > 50:
               send_message("I can provide 50 iron plates", recipient=msg['sender'])
               # Drop iron plates at meeting point
               meeting_pos = Position(x=0, y=0)
               move_to(meeting_pos)
               # ... drop items code ...
   '''
   )

Action Validation
-----------------

Before execution, actions are validated for:

- **Syntax correctness**: Python code must be syntactically valid
- **Resource limits**: Code execution is limited in time and memory
- **Safety**: Potentially dangerous operations are blocked
- **Game state**: Actions must be valid for the current game state

Error Handling
--------------

When code execution fails, the error is captured and returned as part of the observation:

.. code-block:: python

   # Example error in action
   action = Action(
       agent_idx=0,
       game_state=None,
       code='''
   # This will cause an error - invalid entity placement
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=Position(x=1000, y=1000),  # Invalid position
       direction=Direction.NORTH
   )
   '''
   )

   # The error will be captured and returned in stderr
   # Agent can then react to the error and try a different approach

Best Practices
--------------

1. **Modular Code**: Break complex actions into smaller, reusable functions
2. **Error Handling**: Use try-except blocks for robust error handling
3. **State Checking**: Always verify current state before taking actions
4. **Resource Management**: Check inventory and resource availability
5. **Coordination**: Use messages for multi-agent coordination
6. **Documentation**: Add comments to explain complex logic

Action Space Limitations
------------------------

- **Code length**: Limited to 10,000 characters per action
- **Execution time**: Maximum 15 seconds per action
- **Memory usage**: Limited memory allocation for code execution
- **System access**: No access to file system or network operations
- **Game state**: Cannot directly modify game state outside of provided tools
