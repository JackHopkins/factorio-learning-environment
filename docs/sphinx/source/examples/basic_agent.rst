Basic Agent Example
====================

This example demonstrates how to create a simple agent that interacts with the Factorio Learning Environment using basic tools and logic.

Agent Implementation
--------------------

.. code-block:: python

   from fle.agents.agent_abc import AgentABC
   from fle.agents.models import Conversation, Response, Policy
   from fle.agents.models import CompletionState
   from typing import Optional
   import random

   class BasicAgent(AgentABC):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.name = "BasicAgent"
           self.step_count = 0
           
       def step(self, conversation: Conversation, response: Response) -> Policy:
           """Basic step implementation"""
           self.step_count += 1
           
           # Simple logic based on step count
           if self.step_count == 1:
               action = "print('Starting basic agent')"
               reasoning = "Initial step"
           elif self.step_count == 2:
               action = "print('Moving to iron ore patch')"
               reasoning = "Find resources"
           elif self.step_count == 3:
               action = """
   # Move to iron ore patch
   iron_pos = nearest(Resource.IronOre)
   move_to(iron_pos)
   print(f'Moved to iron ore at {iron_pos}')
   """
               reasoning = "Navigate to resources"
           elif self.step_count == 4:
               action = """
   # Place mining drill
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=nearest(Resource.IronOre),
       direction=Direction.NORTH
   )
   print(f'Placed mining drill at {drill.position}')
   """
               reasoning = "Set up mining"
           elif self.step_count == 5:
               action = """
   # Place chest for output
   drill = get_entities()[0]  # Get the first entity (our drill)
   chest = place_entity_next_to(
       entity=Prototype.IronChest,
       reference_position=drill.drop_position,
       direction=Direction.SOUTH
   )
   print(f'Placed chest at {chest.position}')
   """
               reasoning = "Add storage"
           else:
               action = "print('Basic agent task complete')"
               reasoning = "Task finished"
           
           return Policy(
               action=action,
               reasoning=reasoning
           )
           
       def end(self, conversation: Conversation, completion: CompletionState) -> None:
           """Handle conversation end"""
           print(f"Basic agent completed {self.step_count} steps")
           print(f"Completion state: {completion}")

Running the Agent
-----------------

Environment Setup
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import gym
   from fle.env.gym_env.action import Action

   # Create environment
   env = gym.make("iron_ore_throughput")
   
   # Create agent
   agent = BasicAgent()
   
   # Reset environment
   obs = env.reset(options={'game_state': None})

Agent Execution Loop
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Run agent for multiple steps
   for step in range(10):
       # Generate action from agent
       policy = agent.step(obs, None)
       
       # Create action for environment
       action = Action(
           agent_idx=0,
           game_state=None,
           code=policy.action
       )
       
       # Execute action
       obs, reward, terminated, truncated, info = env.step(action)
       
       # Check if done
       if terminated or truncated:
           break
       
       print(f"Step {step}: {policy.reasoning}")
       print(f"Reward: {reward}")

   # Clean up
   env.close()

Expected Output
---------------

The basic agent will perform the following sequence of actions:

1. **Step 1**: Print "Starting basic agent"
2. **Step 2**: Print "Moving to iron ore patch"
3. **Step 3**: Move to the nearest iron ore patch
4. **Step 4**: Place a mining drill on the iron ore patch
5. **Step 5**: Place a chest next to the mining drill for output
6. **Step 6+**: Print "Basic agent task complete"

Example Output
^^^^^^^^^^^^^^

.. code-block:: bash

   Step 0: Initial step
   Reward: 0.0
   Step 1: Find resources
   Reward: 0.0
   Step 2: Navigate to resources
   Reward: 0.0
   >>> Moved to iron ore at Position(x=10.0, y=5.0)
   Step 3: Set up mining
   Reward: 0.0
   >>> Placed mining drill at Position(x=10.0, y=5.0)
   Step 4: Add storage
   Reward: 0.0
   >>> Placed chest at Position(x=10.0, y=6.0)
   Step 5: Task finished
   Reward: 0.0
   >>> Basic agent task complete

Agent Variations
----------------

Random Action Agent
^^^^^^^^^^^^^^^^^^^

A variation that takes random actions:

.. code-block:: python

   class RandomAgent(AgentABC):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.name = "RandomAgent"
           self.actions = [
               "print('Random action 1')",
               "print('Random action 2')",
               "print('Random action 3')",
           ]
           
       def step(self, conversation: Conversation, response: Response) -> Policy:
           """Random step implementation"""
           action = random.choice(self.actions)
           reasoning = "Random action selection"
           
           return Policy(
               action=action,
               reasoning=reasoning
           )
           
       def end(self, conversation: Conversation, completion: CompletionState) -> None:
           """Handle conversation end"""
           print("Random agent completed")

Stateful Agent
^^^^^^^^^^^^^^

A variation that maintains state:

.. code-block:: python

   class StatefulAgent(AgentABC):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.name = "StatefulAgent"
           self.state = {
               'has_drill': False,
               'has_chest': False,
               'iron_ore_count': 0
           }
           
       def step(self, conversation: Conversation, response: Response) -> Policy:
           """Stateful step implementation"""
           if not self.state['has_drill']:
               action = """
   # Place mining drill
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=nearest(Resource.IronOre),
       direction=Direction.NORTH
   )
   print(f'Placed drill: {drill.position}')
   """
               self.state['has_drill'] = True
               reasoning = "Place mining drill"
               
           elif not self.state['has_chest']:
               action = """
   # Place chest
   chest = place_entity(
       entity=Prototype.IronChest,
       position=Position(x=0, y=1),
       direction=Direction.NORTH
   )
   print(f'Placed chest: {chest.position}')
   """
               self.state['has_chest'] = True
               reasoning = "Place chest"
               
           else:
               action = "print('Stateful agent task complete')"
               reasoning = "Task finished"
           
           return Policy(
               action=action,
               reasoning=reasoning
           )
           
       def end(self, conversation: Conversation, completion: CompletionState) -> None:
           """Handle conversation end"""
           print(f"Stateful agent final state: {self.state}")

Error Handling Agent
^^^^^^^^^^^^^^^^^^^^

A variation with error handling:

.. code-block:: python

   class ErrorHandlingAgent(AgentABC):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.name = "ErrorHandlingAgent"
           self.error_count = 0
           
       def step(self, conversation: Conversation, response: Response) -> Policy:
           """Error handling step implementation"""
           try:
               # Attempt to place entity
               action = """
   # Place mining drill with error handling
   try:
       drill = place_entity(
           entity=Prototype.MiningDrill,
           position=nearest(Resource.IronOre),
           direction=Direction.NORTH
       )
       print(f'Successfully placed drill: {drill.position}')
   except Exception as e:
       print(f'Failed to place drill: {e}')
       print('Trying alternative approach...')
   """
               reasoning = "Place entity with error handling"
               
           except Exception as e:
               self.error_count += 1
               action = f"print('Error occurred: {e}')"
               reasoning = "Error recovery"
           
           return Policy(
               action=action,
               reasoning=reasoning
           )
           
       def end(self, conversation: Conversation, completion: CompletionState) -> None:
           """Handle conversation end"""
           print(f"Error handling agent completed with {self.error_count} errors")

Testing the Agent
-----------------

Unit Tests
^^^^^^^^^^^

.. code-block:: python

   # In tests/agents/test_basic_agent.py
   import pytest
   from fle.agents.agent_abc import AgentABC
   from fle.agents.models import Conversation, Response, Policy, CompletionState

   def test_basic_agent_step():
       """Test basic agent step method"""
       agent = BasicAgent()
       conversation = Conversation()
       response = Response()
       
       policy = agent.step(conversation, response)
       assert isinstance(policy, Policy)
       assert policy.action is not None
       assert policy.reasoning is not None

   def test_basic_agent_end():
       """Test basic agent end method"""
       agent = BasicAgent()
       conversation = Conversation()
       completion = CompletionState()
       
       # Should not raise exceptions
       agent.end(conversation, completion)

   def test_basic_agent_step_count():
       """Test basic agent step counting"""
       agent = BasicAgent()
       conversation = Conversation()
       response = Response()
       
       # First step
       policy1 = agent.step(conversation, response)
       assert agent.step_count == 1
       
       # Second step
       policy2 = agent.step(conversation, response)
       assert agent.step_count == 2

Integration Tests
^^^^^^^^^^^^^^^^^

.. code-block:: python

   def test_basic_agent_integration():
       """Test basic agent integration with environment"""
       agent = BasicAgent()
       env = gym.make("iron_ore_throughput")
       
       try:
           obs = env.reset()
           
           # Run agent for a few steps
           for step in range(3):
               policy = agent.step(obs, None)
               action = Action(
                   agent_idx=0,
                   game_state=None,
                   code=policy.action
               )
               obs, reward, terminated, truncated, info = env.step(action)
               
               if terminated or truncated:
                   break
           
           assert agent.step_count > 0
           
       finally:
           env.close()

Best Practices
--------------

1. **Simple Logic**: Start with simple, predictable logic
2. **State Management**: Keep track of important state information
3. **Error Handling**: Handle errors gracefully
4. **Testing**: Create comprehensive test cases
5. **Documentation**: Document your agent's behavior
6. **Incremental Development**: Build complexity gradually
7. **Validation**: Validate inputs and outputs
8. **Logging**: Log important events and decisions
9. **Performance**: Consider performance implications
10. **Maintainability**: Write clean, readable code
