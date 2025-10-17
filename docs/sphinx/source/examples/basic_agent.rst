Basic Agent Example
===================

This example demonstrates how to create a basic agent that interacts with the Factorio Learning Environment.

Agent Overview
--------------

The basic agent performs simple resource collection and automation tasks:

1. **Resource Discovery**: Find and identify available resources
2. **Mining Setup**: Place mining drills on resource patches
3. **Storage Management**: Create storage for collected resources
4. **Automation**: Set up basic automation chains

Agent Implementation
--------------------

.. code-block:: python

   from fle.agents.agent_abc import Agent
   from fle.env.gym_env.action import Action
   from fle.env.game_types import Position, Direction
   from typing import Dict, Any, List
   
   class BasicAgent(Agent):
       def __init__(self, config: Dict[str, Any]):
           super().__init__(config)
           self.name = "BasicAgent"
           self.target_resources = ['iron-ore', 'copper-ore', 'coal']
           self.mining_setups = []
           self.step_count = 0
       
       def act(self, observation: Dict[str, Any]) -> Action:
           """Generate action based on current observation"""
           self.step_count += 1
           
           # Get current state
           entities = observation.get('entities', [])
           inventory = observation.get('inventory', {})
           game_info = observation.get('game_info', {})
           
           # Generate action code
           if self.step_count == 1:
               code = self._initial_setup()
           elif self.step_count <= 10:
               code = self._setup_mining()
           else:
               code = self._monitor_and_optimize(entities, inventory)
           
           return Action(
               agent_idx=0,
               code=code,
               game_state=None
           )
       
       def _initial_setup(self) -> str:
           """Initial setup and exploration"""
           return '''
   # Initial setup and exploration
   print("Starting BasicAgent exploration")
   
   # Get current position
   position = get_position()
   print(f"Starting position: {position}")
   
   # Explore the area
   entities = get_entities()
   print(f"Found {len(entities)} entities")
   
   # Look for resources
   iron_pos = nearest(Resource.IRON_ORE)
   copper_pos = nearest(Resource.COPPER_ORE)
   coal_pos = nearest(Resource.COAL)
   
   print(f"Iron ore at: {iron_pos}")
   print(f"Copper ore at: {copper_pos}")
   print(f"Coal at: {coal_pos}")
   '''
       
       def _setup_mining(self) -> str:
           """Set up mining operations"""
           return '''
   # Set up mining operations
   print("Setting up mining operations")
   
   # Find and place mining drills
   iron_pos = nearest(Resource.IRON_ORE)
   if iron_pos:
       drill = place_entity(
           entity=Prototype.MiningDrill,
           position=iron_pos,
           direction=Direction.NORTH
       )
       print(f"Placed mining drill at {iron_pos}")
       
       # Add storage chest
       chest = place_entity_next_to(
           entity=Prototype.IronChest,
           reference_position=drill.drop_position,
           direction=Direction.SOUTH
       )
       print(f"Placed chest at {chest.position}")
   
   # Check inventory
   inventory = inspect_inventory()
   print(f"Current inventory: {inventory}")
   '''
       
       def _monitor_and_optimize(self, entities: List, inventory: Dict) -> str:
           """Monitor and optimize operations"""
           return '''
   # Monitor and optimize operations
   print("Monitoring operations")
   
   # Check all entities
   entities = get_entities()
   working_entities = [e for e in entities if hasattr(e, 'status') and e.status == EntityStatus.WORKING]
   print(f"Working entities: {len(working_entities)}")
   
   # Check inventory
   inventory = inspect_inventory()
   total_items = sum(inventory.values())
   print(f"Total items in inventory: {total_items}")
   
   # Print detailed inventory
   for item, count in inventory.items():
       if count > 0:
           print(f"  {item}: {count}")
   
   # Check for any issues
   for entity in entities:
       if hasattr(entity, 'status') and entity.status == EntityStatus.NO_POWER:
           print(f"Entity {entity.name} needs power")
       elif hasattr(entity, 'status') and entity.status == EntityStatus.NO_FUEL:
           print(f"Entity {entity.name} needs fuel")
   '''

Running the Agent
-----------------

**Environment Setup**
   .. code-block:: python

      import gym
      from fle.agents.basic_agent import BasicAgent
      
      # Create environment
      env = gym.make("iron_ore_throughput")
      
      # Create agent
      agent = BasicAgent({})
      
      # Run episode
      obs = env.reset()
      done = False
      step = 0
      
      while not done and step < 100:
          action = agent.act(obs)
          obs, reward, terminated, truncated, info = env.step(action)
          done = terminated or truncated
          step += 1
          print(f"Step {step}: Reward = {reward}")
      
      env.close()

**Command Line Usage**
   .. code-block:: bash

      # Run basic agent evaluation
      fle eval --agent basic_agent --config configs/basic_agent_config.json

Agent Configuration
-------------------

**Basic Configuration**
   .. code-block:: json

      {
          "agent_type": "BasicAgent",
          "config": {
              "target_resources": ["iron-ore", "copper-ore", "coal"],
              "max_mining_setups": 5,
              "monitoring_interval": 10
          },
          "evaluation": {
              "episodes": 5,
              "max_steps": 1000,
              "success_threshold": 0.5
          }
      }

**Advanced Configuration**
   .. code-block:: json

      {
          "agent_type": "BasicAgent",
          "config": {
              "target_resources": ["iron-ore", "copper-ore", "coal", "stone"],
              "max_mining_setups": 10,
              "monitoring_interval": 5,
              "optimization_enabled": true,
              "debug_mode": true
          },
          "evaluation": {
              "episodes": 10,
              "max_steps": 2000,
              "success_threshold": 0.8,
              "metrics": ["throughput", "efficiency", "resource_utilization"]
          }
      }

Agent Behavior
--------------

**Phase 1: Exploration (Steps 1-5)**
   - Explore the starting area
   - Identify available resources
   - Plan mining operations

**Phase 2: Setup (Steps 6-15)**
   - Place mining drills on resource patches
   - Create storage chests
   - Set up basic automation

**Phase 3: Monitoring (Steps 16+)**
   - Monitor entity status
   - Check inventory levels
   - Optimize operations

Example Output
--------------

**Step 1: Initial Setup**
   .. code-block::

      Starting BasicAgent exploration
      Starting position: Position(x=0.0, y=0.0)
      Found 0 entities
      Iron ore at: Position(x=-28.0, y=-61.0)
      Copper ore at: Position(x=45.0, y=-30.0)
      Coal at: Position(x=-15.0, y=20.0)

**Step 5: Mining Setup**
   .. code-block::

      Setting up mining operations
      Placed mining drill at Position(x=-28.0, y=-61.0)
      Placed chest at Position(x=-27.5, y=-59.5)
      Current inventory: {'iron-ore': 0, 'coal': 4}

**Step 20: Monitoring**
   .. code-block::

      Monitoring operations
      Working entities: 1
      Total items in inventory: 75
        iron-ore: 75
        coal: 4

Performance Metrics
-------------------

**Throughput**
   - Items produced per minute
   - Resource utilization efficiency
   - Automation chain performance

**Efficiency**
   - Power consumption per item
   - Entity utilization rate
   - Resource waste minimization

**Reliability**
   - System uptime
   - Error rate
   - Recovery time

Example Metrics
~~~~~~~~~~~~~~~

.. code-block:: python

   {
       "throughput": {
           "iron_ore": 2.5,  # items per minute
           "copper_ore": 1.8,
           "coal": 3.2
       },
       "efficiency": {
           "power_usage": 0.8,  # normalized power usage
           "entity_utilization": 0.75,  # fraction of entities working
           "resource_waste": 0.05  # fraction of resources wasted
       },
       "reliability": {
           "uptime": 0.95,  # fraction of time system is working
           "error_rate": 0.02,  # errors per step
           "recovery_time": 5.0  # average recovery time in steps
       }
   }

Troubleshooting
---------------

**Common Issues**
   - **No resources found**: Check map generation and resource placement
   - **Mining drills not working**: Verify power and fuel supply
   - **Inventory full**: Add more storage or optimize collection

**Debug Mode**
   Enable debug mode for detailed logging:

   .. code-block:: json

      {
          "config": {
              "debug_mode": true,
              "log_level": "DEBUG"
          }
      }

**Performance Issues**
   - Monitor entity count and performance
   - Check for resource bottlenecks
   - Optimize automation chains

Best Practices
--------------

1. **Start Simple**: Begin with basic operations
2. **Monitor Progress**: Track performance metrics
3. **Handle Errors**: Implement error recovery
4. **Optimize Gradually**: Improve efficiency over time
5. **Test Thoroughly**: Validate all scenarios
6. **Document Behavior**: Record agent decisions
