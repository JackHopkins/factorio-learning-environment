Multi-Agent Example
===================

This example demonstrates how to create and coordinate multiple agents in the Factorio Learning Environment.

Multi-Agent Overview
-------------------

Multi-agent systems in FLE enable:

1. **Agent Coordination**: Multiple agents working together
2. **Task Distribution**: Dividing tasks among agents
3. **Communication**: Inter-agent message passing
4. **Collaborative Planning**: Joint decision making

Agent Architecture
------------------

**Agent Roles**
   - **Coordinator**: Manages overall strategy
   - **Resource Specialist**: Handles resource collection
   - **Construction Specialist**: Manages building operations
   - **Research Specialist**: Handles technology advancement

**Communication Protocol**
   - Message passing between agents
   - Shared state information
   - Task assignment and reporting
   - Conflict resolution

Multi-Agent Implementation
-------------------------

.. code-block:: python

   from fle.agents.agent_abc import Agent
   from fle.env.gym_env.action import Action
   from fle.env.game_types import Position, Direction
   from typing import Dict, Any, List
   import json
   
   class MultiAgentCoordinator(Agent):
       def __init__(self, config: Dict[str, Any]):
           super().__init__(config)
           self.name = "MultiAgentCoordinator"
           self.agent_count = config.get('agent_count', 3)
           self.agents = self._initialize_agents(config)
           self.shared_state = {}
           self.task_queue = []
           self.step_count = 0
       
       def _initialize_agents(self, config: Dict[str, Any]) -> List[Agent]:
           """Initialize specialized agents"""
           agents = []
           
           # Resource specialist
           agents.append(ResourceSpecialist({
               'role': 'resource_specialist',
               'target_resources': ['iron-ore', 'copper-ore', 'coal']
           }))
           
           # Construction specialist
           agents.append(ConstructionSpecialist({
               'role': 'construction_specialist',
               'building_types': ['assembling-machine', 'furnace', 'lab']
           }))
           
           # Research specialist
           agents.append(ResearchSpecialist({
               'role': 'research_specialist',
               'research_priorities': ['automation', 'logistics', 'production']
           }))
           
           return agents
       
       def act(self, observation: Dict[str, Any]) -> Action:
           """Coordinate multi-agent actions"""
           self.step_count += 1
           
           # Get messages from other agents
           messages = observation.get('messages', [])
           
           # Process messages and update shared state
           self._process_messages(messages)
           
           # Coordinate agent actions
           if self.step_count == 1:
               code = self._initial_coordination()
           elif self.step_count <= 20:
               code = self._task_distribution()
           else:
               code = self._monitoring_and_optimization()
           
           return Action(
               agent_idx=0,
               code=code,
               game_state=None
           )
       
       def _process_messages(self, messages: List[Dict[str, Any]]):
           """Process messages from other agents"""
           for message in messages:
               if message['type'] == 'task_completion':
                   self._handle_task_completion(message)
               elif message['type'] == 'resource_request':
                   self._handle_resource_request(message)
               elif message['type'] == 'coordination_request':
                   self._handle_coordination_request(message)
       
       def _initial_coordination(self) -> str:
           """Initial coordination and planning"""
           return '''
   # Initial multi-agent coordination
   print("Starting multi-agent coordination")
   
   # Send initial messages to all agents
   send_message({
       'type': 'coordination_start',
       'content': 'Beginning multi-agent coordination',
       'target_agents': 'all'
   })
   
   # Analyze current state
   entities = get_entities()
   inventory = inspect_inventory()
   
   print(f"Current state: {len(entities)} entities, {sum(inventory.values())} items")
   
   # Plan initial tasks
   tasks = [
       {'type': 'resource_collection', 'priority': 'high', 'agent': 'resource_specialist'},
       {'type': 'basic_setup', 'priority': 'medium', 'agent': 'construction_specialist'},
       {'type': 'research_planning', 'priority': 'low', 'agent': 'research_specialist'}
   ]
   
   print(f"Planned tasks: {tasks}")
   '''
       
       def _task_distribution(self) -> str:
           """Distribute tasks among agents"""
           return '''
   # Task distribution and coordination
   print("Distributing tasks among agents")
   
   # Check for available resources
   iron_pos = nearest(Resource.IRON_ORE)
   copper_pos = nearest(Resource.COPPER_ORE)
   
   if iron_pos:
       # Assign resource collection task
       send_message({
           'type': 'task_assignment',
           'content': {
               'task': 'collect_iron_ore',
               'location': str(iron_pos),
               'priority': 'high'
           },
           'target_agents': ['resource_specialist']
       })
   
   if copper_pos:
       # Assign copper collection task
       send_message({
           'type': 'task_assignment',
           'content': {
               'task': 'collect_copper_ore',
               'location': str(copper_pos),
               'priority': 'medium'
           },
           'target_agents': ['resource_specialist']
       })
   
   # Check construction needs
   entities = get_entities()
   if len(entities) < 5:
       send_message({
           'type': 'task_assignment',
           'content': {
               'task': 'build_infrastructure',
               'requirements': ['mining_drill', 'chest', 'furnace'],
               'priority': 'high'
           },
           'target_agents': ['construction_specialist']
       })
   '''
       
       def _monitoring_and_optimization(self) -> str:
           """Monitor and optimize multi-agent operations"""
           return '''
   # Multi-agent monitoring and optimization
   print("Monitoring multi-agent operations")
   
   # Check agent status
   entities = get_entities()
   inventory = inspect_inventory()
   
   print(f"Current state: {len(entities)} entities, {sum(inventory.values())} items")
   
   # Check for coordination issues
   working_entities = [e for e in entities if hasattr(e, 'status') and e.status == EntityStatus.WORKING]
   print(f"Working entities: {len(working_entities)}")
   
   # Send status updates
   send_message({
       'type': 'status_update',
       'content': {
           'entities': len(entities),
           'inventory': sum(inventory.values()),
           'working_entities': len(working_entities)
       },
       'target_agents': 'all'
   })
   
   # Check for optimization opportunities
   if len(working_entities) < len(entities) * 0.8:
       send_message({
           'type': 'optimization_request',
           'content': 'System efficiency below 80%',
           'target_agents': 'all'
       })
   '''

Specialized Agents
------------------

**Resource Specialist**
   .. code-block:: python

      class ResourceSpecialist(Agent):
          def __init__(self, config: Dict[str, Any]):
              super().__init__(config)
              self.name = "ResourceSpecialist"
              self.target_resources = config.get('target_resources', [])
              self.mining_setups = []
          
          def act(self, observation: Dict[str, Any]) -> Action:
              """Handle resource collection tasks"""
              messages = observation.get('messages', [])
              
              # Process task assignments
              for message in messages:
                  if message['type'] == 'task_assignment':
                      task = message['content']
                      if task['task'].startswith('collect_'):
                          return self._handle_collection_task(task)
              
              # Default resource collection behavior
              return self._default_resource_behavior()
          
          def _handle_collection_task(self, task: Dict[str, Any]) -> Action:
              """Handle specific collection tasks"""
              resource_type = task['task'].split('_')[1]
              location = task.get('location')
              
              code = f'''
   # Handle collection task: {task['task']}
   print("Resource specialist handling collection task")
   
   # Find and collect {resource_type}
   resource_pos = nearest(Resource.{resource_type.upper().replace('-', '_')})
   if resource_pos:
       drill = place_entity(
           entity=Prototype.MiningDrill,
           position=resource_pos,
           direction=Direction.NORTH
       )
       print(f"Placed mining drill for {resource_type} at {resource_pos}")
       
       # Report task completion
       send_message({{
           'type': 'task_completion',
           'content': {{
               'task': '{task['task']}',
               'status': 'completed',
               'location': str(resource_pos)
           }},
           'target_agents': ['coordinator']
       }})
   '''
              
              return Action(agent_idx=1, code=code, game_state=None)

**Construction Specialist**
   .. code-block:: python

      class ConstructionSpecialist(Agent):
          def __init__(self, config: Dict[str, Any]):
              super().__init__(config)
              self.name = "ConstructionSpecialist"
              self.building_types = config.get('building_types', [])
              self.construction_queue = []
          
          def act(self, observation: Dict[str, Any]) -> Action:
              """Handle construction tasks"""
              messages = observation.get('messages', [])
              
              # Process construction requests
              for message in messages:
                  if message['type'] == 'task_assignment':
                      task = message['content']
                      if task['task'] == 'build_infrastructure':
                          return self._handle_infrastructure_task(task)
              
              # Default construction behavior
              return self._default_construction_behavior()
          
          def _handle_infrastructure_task(self, task: Dict[str, Any]) -> Action:
              """Handle infrastructure construction"""
              requirements = task.get('requirements', [])
              
              code = f'''
   # Handle infrastructure construction
   print("Construction specialist building infrastructure")
   
   # Build required entities
   entities = get_entities()
   current_types = [e.name for e in entities]
   
   for requirement in {requirements}:
       if requirement not in current_types:
           # Build the required entity
           if requirement == 'mining_drill':
               resource_pos = nearest(Resource.IRON_ORE)
               if resource_pos:
                   drill = place_entity(
                       entity=Prototype.MiningDrill,
                       position=resource_pos,
                       direction=Direction.NORTH
                   )
                   print(f"Built {requirement} at {resource_pos}")
           
           elif requirement == 'chest':
               # Place chest near existing entities
               if entities:
                   reference = entities[0]
                   chest = place_entity_next_to(
                       entity=Prototype.IronChest,
                       reference_position=reference.position,
                       direction=Direction.SOUTH
                   )
                   print(f"Built {requirement} at {chest.position}")
   
   # Report construction completion
   send_message({{
       'type': 'task_completion',
       'content': {{
           'task': 'build_infrastructure',
           'status': 'completed',
           'entities_built': len(get_entities())
       }},
       'target_agents': ['coordinator']
   }})
   '''
              
              return Action(agent_idx=2, code=code, game_state=None)

**Research Specialist**
   .. code-block:: python

      class ResearchSpecialist(Agent):
          def __init__(self, config: Dict[str, Any]):
              super().__init__(config)
              self.name = "ResearchSpecialist"
              self.research_priorities = config.get('research_priorities', [])
              self.research_queue = []
          
          def act(self, observation: Dict[str, Any]) -> Action:
              """Handle research tasks"""
              messages = observation.get('messages', [])
              
              # Process research requests
              for message in messages:
                  if message['type'] == 'task_assignment':
                      task = message['content']
                      if task['task'] == 'research_planning':
                          return self._handle_research_planning(task)
              
              # Default research behavior
              return self._default_research_behavior()
          
          def _handle_research_planning(self, task: Dict[str, Any]) -> Action:
              """Handle research planning tasks"""
              code = '''
   # Handle research planning
   print("Research specialist planning research")
   
   # Check current research status
   research = get_research_progress()
   print(f"Current research: {research}")
   
   # Plan research priorities
   priorities = ['automation', 'logistics', 'production']
   for priority in priorities:
       if priority not in research.get('completed', []):
           # Start research
           result = set_research(priority)
           if result:
               print(f"Started research: {priority}")
               break
   
   # Report research status
   send_message({
       'type': 'task_completion',
       'content': {
           'task': 'research_planning',
           'status': 'completed',
           'research_started': priority
       },
       'target_agents': ['coordinator']
   })
   '''
              
              return Action(agent_idx=3, code=code, game_state=None)

Running Multi-Agent Systems
---------------------------

**Environment Setup**
   .. code-block:: python

      import gym
      from fle.agents.multiagent_coordinator import MultiAgentCoordinator
      
      # Create environment
      env = gym.make("iron_ore_throughput")
      
      # Create multi-agent coordinator
      coordinator = MultiAgentCoordinator({
          'agent_count': 3,
          'coordination_enabled': True,
          'communication_enabled': True
      })
      
      # Run episode
      obs = env.reset()
      done = False
      step = 0
      
      while not done and step < 100:
          action = coordinator.act(obs)
          obs, reward, terminated, truncated, info = env.step(action)
          done = terminated or truncated
          step += 1
          print(f"Step {step}: Reward = {reward}")
      
      env.close()

**Command Line Usage**
   .. code-block:: bash

      # Run multi-agent evaluation
      fle eval --agent multiagent_coordinator --config configs/multiagent_config.json

Multi-Agent Configuration
-------------------------

**Basic Configuration**
   .. code-block:: json

      {
          "agent_type": "MultiAgentCoordinator",
          "config": {
              "agent_count": 3,
              "coordination_enabled": true,
              "communication_enabled": true,
              "task_distribution": "round_robin"
          },
          "evaluation": {
              "episodes": 5,
              "max_steps": 1000,
              "success_threshold": 0.7
          }
      }

**Advanced Configuration**
   .. code-block:: json

      {
          "agent_type": "MultiAgentCoordinator",
          "config": {
              "agent_count": 5,
              "coordination_enabled": true,
              "communication_enabled": true,
              "task_distribution": "priority_based",
              "conflict_resolution": "voting",
              "shared_state_size": 1000,
              "message_timeout": 30
          },
          "evaluation": {
              "episodes": 10,
              "max_steps": 2000,
              "success_threshold": 0.8,
              "metrics": ["coordination_effectiveness", "communication_efficiency", "task_completion_rate"]
          }
      }

Performance Metrics
-------------------

**Coordination Effectiveness**
   - Task completion rate
   - Coordination efficiency
   - Conflict resolution success

**Communication Efficiency**
   - Message delivery rate
   - Communication latency
   - Message processing time

**Multi-Agent Performance**
   - Overall system performance
   - Agent specialization effectiveness
   - Collaborative planning success

Example Metrics
~~~~~~~~~~~~~~~

.. code-block:: python

   {
       "coordination_effectiveness": {
           "task_completion_rate": 0.85,  # fraction of tasks completed
           "coordination_efficiency": 0.75,  # fraction of coordinated actions
           "conflict_resolution_success": 0.90  # fraction of conflicts resolved
       },
       "communication_efficiency": {
           "message_delivery_rate": 0.95,  # fraction of messages delivered
           "communication_latency": 0.1,  # average latency in seconds
           "message_processing_time": 0.05  # average processing time in seconds
       },
       "multi_agent_performance": {
           "overall_system_performance": 0.80,  # overall system effectiveness
           "agent_specialization_effectiveness": 0.85,  # effectiveness of specialization
           "collaborative_planning_success": 0.70  # success rate of collaborative plans
       }
   }

Troubleshooting
---------------

**Coordination Issues**
   - **Task conflicts**: Implement conflict resolution
   - **Communication failures**: Check message delivery
   - **Coordination breakdown**: Monitor coordination effectiveness

**Performance Issues**
   - **Slow coordination**: Optimize coordination algorithms
   - **High communication overhead**: Reduce message frequency
   - **Memory issues**: Limit shared state size

**Agent Issues**
   - **Agent failures**: Implement agent recovery
   - **Specialization problems**: Adjust agent roles
   - **Communication errors**: Handle message errors

Best Practices
--------------

1. **Clear Roles**: Define clear agent roles and responsibilities
2. **Effective Communication**: Implement efficient communication protocols
3. **Conflict Resolution**: Handle conflicts between agents
4. **Performance Monitoring**: Monitor multi-agent performance
5. **Scalability**: Design for different numbers of agents
6. **Error Handling**: Implement robust error recovery
7. **Testing**: Test multi-agent coordination thoroughly
