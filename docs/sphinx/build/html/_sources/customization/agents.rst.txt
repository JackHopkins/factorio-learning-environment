Implementing Custom Agents
==========================

FLE provides a flexible framework for implementing custom agents. Agents interact with the environment through code synthesis and can be designed for various evaluation scenarios.

Agent Architecture
------------------

Agents in FLE follow a specific architecture:

**Base Agent Class**
   Abstract base class defining the agent interface

**Agent Implementation**
   Concrete implementation of agent behavior

**Agent Registration**
   Registration with the evaluation system

Base Agent Class
----------------

All agents inherit from the base agent class:

.. autoclass:: fle.agents.agent_abc.Agent
   :members:
   :undoc-members:
   :show-inheritance:

Key Methods
~~~~~~~~~~~

**act(observation)**
   Generate an action based on the current observation

**reset()**
   Reset the agent state for a new episode

**close()**
   Clean up agent resources

Agent Implementation
--------------------

Create a custom agent by inheriting from the base class:

.. code-block:: python

   from fle.agents.agent_abc import Agent
   from fle.env.gym_env.action import Action
   from typing import Dict, Any
   
   class MyCustomAgent(Agent):
       def __init__(self, config: Dict[str, Any]):
           super().__init__(config)
           self.name = "MyCustomAgent"
           self.episode_count = 0
           self.total_reward = 0.0
       
       def act(self, observation: Dict[str, Any]) -> Action:
           """
           Generate an action based on the current observation.
           
           Args:
               observation: Current game state observation
           
           Returns:
               Action to execute
           """
           # Analyze the observation
           entities = observation.get('entities', [])
           inventory = observation.get('inventory', {})
           game_info = observation.get('game_info', {})
           
           # Generate action code
           code = self._generate_action_code(entities, inventory, game_info)
           
           return Action(
               agent_idx=0,
               code=code,
               game_state=None
           )
       
       def reset(self):
           """Reset agent state for new episode"""
           self.episode_count += 1
           self.total_reward = 0.0
           super().reset()
       
       def close(self):
           """Clean up agent resources"""
           super().close()
       
       def _generate_action_code(self, entities, inventory, game_info):
           """Generate Python code for the action"""
           # Implement your action generation logic
           return 'print("Hello from MyCustomAgent!")'

Agent Types
-----------

**Basic Agents**
   Simple agents with basic decision-making

**Visual Agents**
   Agents that process visual information

**Multi-Agent Systems**
   Agents that coordinate with other agents

**Learning Agents**
   Agents that improve over time

**Specialized Agents**
   Agents designed for specific tasks

Example Agent: Resource Collector
----------------------------------

Here's a complete example of a resource collection agent:

.. code-block:: python

   from fle.agents.agent_abc import Agent
   from fle.env.gym_env.action import Action
   from fle.env.game_types import Position, Direction
   from typing import Dict, Any, List
   
   class ResourceCollectorAgent(Agent):
       def __init__(self, config: Dict[str, Any]):
           super().__init__(config)
           self.name = "ResourceCollectorAgent"
           self.target_resources = config.get('target_resources', ['iron-ore', 'copper-ore'])
           self.collected_resources = {}
           self.mining_setups = []
       
       def act(self, observation: Dict[str, Any]) -> Action:
           """Generate action to collect resources"""
           entities = observation.get('entities', [])
           inventory = observation.get('inventory', {})
           
           # Check if we need to set up mining
           if not self.mining_setups:
               code = self._setup_mining(entities)
           else:
               code = self._monitor_mining(entities, inventory)
           
           return Action(
               agent_idx=0,
               code=code,
               game_state=None
           )
       
       def _setup_mining(self, entities: List) -> str:
           """Set up mining operations for target resources"""
           code_lines = []
           
           for resource in self.target_resources:
               code_lines.append(f'''
# Set up mining for {resource}
resource_pos = nearest(Resource.{resource.replace('-', '_').upper()})
if resource_pos:
    drill = place_entity(
        entity=Prototype.MiningDrill,
        position=resource_pos,
        direction=Direction.NORTH
    )
    chest = place_entity_next_to(
        entity=Prototype.IronChest,
        reference_position=drill.drop_position,
        direction=Direction.SOUTH
    )
    print(f"Set up mining for {{resource}} at {{resource_pos}}")
''')
           
           return '\n'.join(code_lines)
       
       def _monitor_mining(self, entities: List, inventory: Dict) -> str:
           """Monitor and manage existing mining operations"""
           return '''
# Monitor mining operations
entities = get_entities()
for entity in entities:
    if hasattr(entity, 'status') and entity.status == EntityStatus.WORKING:
        print(f"Entity {entity.name} is working")
    elif hasattr(entity, 'status') and entity.status == EntityStatus.NO_POWER:
        print(f"Entity {entity.name} needs power")

# Check inventory
inventory = inspect_inventory()
for item, count in inventory.items():
    if count > 0:
        print(f"Have {count} {item}")
'''

Agent Configuration
-------------------

Agents can be configured with various parameters:

**Behavior Parameters**
   - Decision-making algorithms
   - Action generation strategies
   - State management approaches

**Performance Parameters**
   - Memory usage limits
   - Processing time limits
   - Resource consumption limits

**Evaluation Parameters**
   - Success criteria
   - Performance metrics
   - Evaluation scenarios

Example Configuration
--------------------

.. code-block:: json

   {
       "agent_type": "ResourceCollectorAgent",
       "config": {
           "target_resources": ["iron-ore", "copper-ore", "coal"],
           "max_mining_setups": 5,
           "mining_radius": 100,
           "inventory_threshold": 1000
       },
       "evaluation": {
           "episodes": 10,
           "max_steps": 1000,
           "success_threshold": 0.8
       }
   }

Agent Testing
-------------

Create test cases for your custom agents:

.. code-block:: python

   import pytest
   from fle.agents.my_custom_agent import MyCustomAgent
   from fle.env.gym_env.action import Action
   
   def test_agent_creation():
       config = {'param1': 'value1'}
       agent = MyCustomAgent(config)
       assert agent.name == "MyCustomAgent"
   
   def test_agent_action():
       config = {}
       agent = MyCustomAgent(config)
       
       observation = {
           'entities': [],
           'inventory': {},
           'game_info': {}
       }
       
       action = agent.act(observation)
       assert isinstance(action, Action)
       assert action.agent_idx == 0
   
   def test_agent_reset():
       config = {}
       agent = MyCustomAgent(config)
       agent.reset()
       assert agent.episode_count == 1

Advanced Agent Features
-----------------------

**State Management**
   - Persistent state across episodes
   - State serialization and loading
   - State sharing between agents

**Learning Capabilities**
   - Experience replay
   - Policy updates
   - Performance tracking

**Multi-Agent Coordination**
   - Communication protocols
   - Task distribution
   - Conflict resolution

**Adaptive Behavior**
   - Dynamic strategy adjustment
   - Environment adaptation
   - Performance optimization

Agent Registration
------------------

Agents are registered with the evaluation system:

1. **Agent Discovery**: The system scans for agent implementations
2. **Configuration Loading**: Agent configurations are loaded
3. **Initialization**: Agents are initialized with their configurations
4. **Registration**: Agents are registered with the evaluation system

Example Registration
----------------------

.. code-block:: python

   from fle.agents.registry import register_agent
   from fle.agents.my_custom_agent import MyCustomAgent
   
   # Register the agent
   register_agent('my_custom_agent', MyCustomAgent)
   
   # Use in evaluation
   config = {
       'agent_type': 'my_custom_agent',
       'config': {'param1': 'value1'}
   }

Best Practices
--------------

1. **Clear Interface**: Design simple, intuitive interfaces
2. **Error Handling**: Handle errors gracefully
3. **State Management**: Manage agent state properly
4. **Performance**: Optimize for efficiency
5. **Testing**: Test all scenarios and edge cases
6. **Documentation**: Document agent behavior and configuration
7. **Modularity**: Design for reusability and extensibility
