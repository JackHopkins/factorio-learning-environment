Action Space
============

The action space defines how agents interact with the Factorio Learning Environment through Python code synthesis.

Action Structure
----------------

Actions are defined by the Action class:

.. autoclass:: fle.env.gym_env.action.Action
   :members:
   :undoc-members:
   :show-inheritance:

Action Components
-----------------

**agent_idx**
   Index of the agent taking the action (for multi-agent environments)

**code**
   Python code to execute in the game environment

**game_state**
   Optional game state to reset to before running code

Action Space Definition
------------------------

The action space follows this structure:

.. code-block:: python

   {
       'agent_idx': Discrete(instance.num_agents),  # Index of the agent taking the action
       'game_state': Text(max_length=1000000),      # Optional: game state to reset to before running code
       'code': Text(max_length=10000)                # Python code to execute
   }

Code Execution
--------------

The environment executes Python code in a controlled namespace that includes:

**Standard Library**
   Full Python standard library access

**FLE Tools**
   All available tools for game interaction

**Namespace Persistence**
   Variables and functions persist between actions

**Error Handling**
   Comprehensive exception handling with detailed error messages

Example Actions
---------------

**Basic Movement**
   .. code-block:: python

      action = Action(
          agent_idx=0,
          code='position = get_position()',
          game_state=None
      )

**Entity Placement**
   .. code-block:: python

      action = Action(
          agent_idx=0,
          code='''
      drill = place_entity(
          entity=Prototype.MiningDrill,
          position=nearest(Resource.IronOre),
          direction=Direction.NORTH
      )
      ''',
          game_state=None
      )

**Complex Automation**
   .. code-block:: python

      action = Action(
          agent_idx=0,
          code='''
      # Get iron patch and place mining drill
      drill = place_entity(
          entity=Prototype.MiningDrill,
          position=nearest(Resource.IronOre),
          direction=Direction.NORTH
      )
      # Add output storage
      chest = place_entity_next_to(
          entity=Prototype.IronChest,
          reference_position=drill.drop_position,
          direction=Direction.SOUTH
      )
      # Verify automation chain
      sleep(10)
      assert drill.status == EntityStatus.WORKING
      print(get_entities())
      ''',
          game_state=None
      )

**Function Definition**
   .. code-block:: python

      action = Action(
          agent_idx=0,
          code='''
      def place_mining_setup(resource_type, direction):
          drill = place_entity(
              entity=Prototype.MiningDrill,
              position=nearest(resource_type),
              direction=direction
          )
          chest = place_entity_next_to(
              entity=Prototype.IronChest,
              reference_position=drill.drop_position,
              direction=Direction.SOUTH
          )
          return drill, chest
      
      # Use the function
      drill, chest = place_mining_setup(Resource.IronOre, Direction.NORTH)
      ''',
          game_state=None
      )

**Class Definition**
   .. code-block:: python

      action = Action(
          agent_idx=0,
          code='''
      class MiningOperation:
          def __init__(self, resource_type, position):
              self.resource_type = resource_type
              self.position = position
              self.drill = None
              self.chest = None
          
          def setup(self):
              self.drill = place_entity(
                  entity=Prototype.MiningDrill,
                  position=self.position,
                  direction=Direction.NORTH
              )
              self.chest = place_entity_next_to(
                  entity=Prototype.IronChest,
                  reference_position=self.drill.drop_position,
                  direction=Direction.SOUTH
              )
          
          def is_working(self):
              return self.drill.status == EntityStatus.WORKING
      
      # Create and use the class
      mining_op = MiningOperation(Resource.IronOre, nearest(Resource.IronOre))
      mining_op.setup()
      print(f"Mining operation working: {mining_op.is_working()}")
      ''',
          game_state=None
      )

Error Handling
--------------

The environment provides comprehensive error handling:

**Syntax Errors**
   Python syntax errors are caught and reported with line numbers

**Runtime Errors**
   Exceptions during code execution are captured with full stack traces

**Tool Errors**
   Invalid tool usage is reported with detailed error messages

**Assertion Failures**
   Failed assertions provide context about expected vs actual values

Example Error Handling
----------------------

.. code-block:: python

   # Invalid tool usage
   action = Action(
       agent_idx=0,
       code='place_entity(entity="invalid", position=(0, 0))',
       game_state=None
   )
   
   # Results in error message:
   # ValueError: Invalid entity type 'invalid'. Expected Prototype enum value.

**Debugging Support**
   The environment provides debugging information:

   - **Variable Inspection**: Access to all namespace variables
   - **Function Signatures**: Available functions and their parameters
   - **Entity State**: Current state of all game entities
   - **Error Context**: Detailed error information with suggestions

Multi-Agent Actions
-------------------

For multi-agent environments, actions can be coordinated:

.. code-block:: python

   # Agent 0 places a drill
   action_0 = Action(
       agent_idx=0,
       code='drill = place_entity(entity=Prototype.MiningDrill, position=nearest(Resource.IronOre))',
       game_state=None
   )
   
   # Agent 1 places a chest next to it
   action_1 = Action(
       agent_idx=1,
       code='chest = place_entity_next_to(entity=Prototype.IronChest, reference_position=drill.drop_position)',
       game_state=None
   )

Action Validation
-----------------

The environment validates actions before execution:

- **Agent Index**: Ensures valid agent index
- **Code Length**: Limits code to prevent resource exhaustion
- **Game State**: Validates game state format if provided
- **Tool Availability**: Ensures requested tools are available

Best Practices
--------------

1. **Use Descriptive Variable Names**: Make code readable and maintainable
2. **Handle Errors Gracefully**: Use try-except blocks for robust code
3. **Leverage Namespace**: Store useful objects for later reference
4. **Use Functions**: Encapsulate common operations
5. **Debug with Print**: Use print statements to monitor execution
6. **Assert Conditions**: Use assertions to verify expected behavior
