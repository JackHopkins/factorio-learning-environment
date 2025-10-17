Multi-Agent Coordination Example
=================================

This example demonstrates how to create multiple agents that coordinate with each other in the Factorio Learning Environment using inter-agent communication and shared state.

Agent Implementation
--------------------

Coordinating Agent
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from fle.agents.agent_abc import AgentABC
   from fle.agents.models import Conversation, Response, Policy
   from fle.agents.models import CompletionState
   from typing import Optional, Dict, List
   import json

   class CoordinatingAgent(AgentABC):
       def __init__(self, agent_id: int, **kwargs):
           super().__init__(**kwargs)
           self.agent_id = agent_id
           self.name = f"CoordinatingAgent_{agent_id}"
           self.other_agents = []
           self.shared_state = {}
           self.message_history = []
           
       def step(self, conversation: Conversation, response: Response) -> Policy:
           """Multi-agent coordination step"""
           # Check for messages from other agents
           messages = self._get_messages_from_other_agents(response)
           
           # Process coordination logic
           coordination_action = self._coordinate_with_other_agents(messages)
           
           # Generate policy
           policy = Policy(
               action=coordination_action,
               reasoning=f"Multi-agent coordination (Agent {self.agent_id})"
           )
           return policy
           
       def _get_messages_from_other_agents(self, response: Response) -> List[Dict]:
           """Get messages from other agents"""
           messages = []
           
           # Extract messages from response
           if hasattr(response, 'messages') and response.messages:
               for msg in response.messages:
                   if msg.get('sender') != self.agent_id:
                       messages.append(msg)
           
           return messages
           
       def _coordinate_with_other_agents(self, messages: List[Dict]) -> str:
           """Coordinate with other agents"""
           if not messages:
               # No messages, take initial action
               return self._take_initial_action()
           
           # Process messages
           for msg in messages:
               self.message_history.append(msg)
               action = self._process_message(msg)
               if action:
                   return action
           
           # Default action
           return self._take_default_action()
           
       def _process_message(self, msg: Dict) -> Optional[str]:
           """Process a message from another agent"""
           message_text = msg.get('message', '')
           sender = msg.get('sender', -1)
           
           # Parse message type
           if message_text.startswith('REQUEST:'):
               return self._handle_request(message_text, sender)
           elif message_text.startswith('RESPONSE:'):
               return self._handle_response(message_text, sender)
           elif message_text.startswith('STATUS:'):
               return self._handle_status(message_text, sender)
           elif message_text.startswith('COORDINATE:'):
               return self._handle_coordination(message_text, sender)
           
           return None
           
       def _handle_request(self, message: str, sender: int) -> str:
           """Handle a request from another agent"""
           parts = message.split(':')
           if len(parts) >= 3:
               request_type = parts[1]
               request_data = parts[2]
               
               if request_type == 'RESOURCES':
                   return self._handle_resource_request(request_data, sender)
               elif request_type == 'HELP':
                   return self._handle_help_request(request_data, sender)
               elif request_type == 'COORDINATION':
                   return self._handle_coordination_request(request_data, sender)
           
           return self._send_response(sender, "UNKNOWN_REQUEST", "Unknown request type")
           
       def _handle_resource_request(self, request_data: str, sender: int) -> str:
           """Handle a resource request"""
           try:
               # Parse resource request
               resource_data = json.loads(request_data)
               resource_type = resource_data.get('type')
               quantity = resource_data.get('quantity', 1)
               
               # Check if we can provide the resource
               if self._can_provide_resource(resource_type, quantity):
                   return self._send_response(sender, "RESOURCE_AVAILABLE", 
                                            json.dumps({'type': resource_type, 'quantity': quantity}))
               else:
                   return self._send_response(sender, "RESOURCE_UNAVAILABLE", 
                                            json.dumps({'type': resource_type, 'quantity': 0}))
                   
           except Exception as e:
               return self._send_response(sender, "ERROR", str(e))
           
       def _handle_help_request(self, request_data: str, sender: int) -> str:
           """Handle a help request"""
           try:
               help_data = json.loads(request_data)
               help_type = help_data.get('type')
               
               if help_type == 'BUILDING':
                   return self._send_response(sender, "HELP_AVAILABLE", 
                                            json.dumps({'type': 'BUILDING', 'status': 'ready'}))
               elif help_type == 'RESOURCES':
                   return self._send_response(sender, "HELP_AVAILABLE", 
                                            json.dumps({'type': 'RESOURCES', 'status': 'ready'}))
               
               return self._send_response(sender, "HELP_UNAVAILABLE", "Cannot help with this request")
               
           except Exception as e:
               return self._send_response(sender, "ERROR", str(e))
           
       def _handle_coordination_request(self, request_data: str, sender: int) -> str:
           """Handle a coordination request"""
           try:
               coord_data = json.loads(request_data)
               coord_type = coord_data.get('type')
               
               if coord_type == 'MEET':
                   meeting_point = coord_data.get('location')
                   return self._send_response(sender, "COORDINATION_ACCEPTED", 
                                            json.dumps({'type': 'MEET', 'location': meeting_point}))
               elif coord_type == 'DIVIDE_WORK':
                   work_items = coord_data.get('items', [])
                   return self._handle_work_division(work_items, sender)
               
               return self._send_response(sender, "COORDINATION_REJECTED", "Unknown coordination type")
               
           except Exception as e:
               return self._send_response(sender, "ERROR", str(e))
           
       def _handle_work_division(self, work_items: List[str], sender: int) -> str:
           """Handle work division"""
           # Assign work items to agents
           assigned_work = {}
           for i, item in enumerate(work_items):
               assigned_work[f"agent_{i % 2}"] = item
           
           return self._send_response(sender, "WORK_DIVISION", json.dumps(assigned_work))
           
       def _handle_response(self, message: str, sender: int) -> str:
           """Handle a response from another agent"""
           parts = message.split(':')
           if len(parts) >= 3:
               response_type = parts[1]
               response_data = parts[2]
               
               # Update shared state based on response
               self.shared_state[f"response_from_{sender}"] = {
                   'type': response_type,
                   'data': response_data,
                   'timestamp': self._get_current_timestamp()
               }
               
               # Take action based on response
               return self._act_on_response(response_type, response_data, sender)
           
           return self._take_default_action()
           
       def _handle_status(self, message: str, sender: int) -> str:
           """Handle a status update from another agent"""
           parts = message.split(':')
           if len(parts) >= 3:
               status_type = parts[1]
               status_data = parts[2]
               
               # Update shared state
               self.shared_state[f"status_from_{sender}"] = {
                   'type': status_type,
                   'data': status_data,
                   'timestamp': self._get_current_timestamp()
               }
               
               # Take action based on status
               return self._act_on_status(status_type, status_data, sender)
           
           return self._take_default_action()
           
       def _handle_coordination(self, message: str, sender: int) -> str:
           """Handle coordination message"""
           parts = message.split(':')
           if len(parts) >= 3:
               coord_type = parts[1]
               coord_data = parts[2]
               
               # Update shared state
               self.shared_state[f"coordination_from_{sender}"] = {
                   'type': coord_type,
                   'data': coord_data,
                   'timestamp': self._get_current_timestamp()
               }
               
               # Take coordinated action
               return self._act_on_coordination(coord_type, coord_data, sender)
           
           return self._take_default_action()
           
       def _can_provide_resource(self, resource_type: str, quantity: int) -> bool:
           """Check if we can provide a resource"""
           # This is a placeholder - implement actual resource checking
           return True
           
       def _send_response(self, recipient: int, response_type: str, response_data: str) -> str:
           """Send a response to another agent"""
           return f"""
   # Send response to agent {recipient}
   send_message("RESPONSE:{response_type}:{response_data}", recipient={recipient})
   print(f"Sent {response_type} response to agent {recipient}")
   """
           
       def _send_request(self, recipient: int, request_type: str, request_data: str) -> str:
           """Send a request to another agent"""
           return f"""
   # Send request to agent {recipient}
   send_message("REQUEST:{request_type}:{request_data}", recipient={recipient})
   print(f"Sent {request_type} request to agent {recipient}")
   """
           
       def _send_status(self, status_type: str, status_data: str) -> str:
           """Send status update to all agents"""
           return f"""
   # Send status update
   send_message("STATUS:{status_type}:{status_data}")
   print(f"Sent {status_type} status update")
   """
           
       def _send_coordination(self, coord_type: str, coord_data: str) -> str:
           """Send coordination message to all agents"""
           return f"""
   # Send coordination message
   send_message("COORDINATE:{coord_type}:{coord_data}")
   print(f"Sent {coord_type} coordination message")
   """
           
       def _take_initial_action(self) -> str:
           """Take initial action when no messages"""
           if self.agent_id == 0:
               # Agent 0: Start coordination
               return self._send_coordination("DIVIDE_WORK", 
                                            json.dumps({'items': ['mining', 'building', 'crafting']}))
           elif self.agent_id == 1:
               # Agent 1: Wait for coordination
               return "print('Waiting for coordination from other agents')"
           else:
               # Other agents: Take default action
               return self._take_default_action()
           
       def _take_default_action(self) -> str:
           """Take default action"""
           if self.agent_id == 0:
               return """
   # Agent 0: Place mining drill
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=nearest(Resource.IronOre),
       direction=Direction.NORTH
   )
   print(f'Agent 0 placed mining drill at {drill.position}')
   """
           elif self.agent_id == 1:
               return """
   # Agent 1: Place chest
   chest = place_entity(
       entity=Prototype.IronChest,
       position=Position(x=0, y=1),
       direction=Direction.NORTH
   )
   print(f'Agent 1 placed chest at {chest.position}')
   """
           else:
               return f"print('Agent {self.agent_id} taking default action')"
           
       def _act_on_response(self, response_type: str, response_data: str, sender: int) -> str:
           """Act on a response from another agent"""
           if response_type == "RESOURCE_AVAILABLE":
               return f"""
   # Resource available from agent {sender}
   print(f"Agent {sender} has resources available: {response_data}")
   # Take action to get resources
   """
           elif response_type == "HELP_AVAILABLE":
               return f"""
   # Help available from agent {sender}
   print(f"Agent {sender} is ready to help: {response_data}")
   # Request help
   """
           else:
               return self._take_default_action()
           
       def _act_on_status(self, status_type: str, status_data: str, sender: int) -> str:
           """Act on a status update from another agent"""
           if status_type == "WORKING":
               return f"""
   # Agent {sender} is working
   print(f"Agent {sender} status: {status_data}")
   # Continue with own work
   """
           elif status_type == "IDLE":
               return f"""
   # Agent {sender} is idle
   print(f"Agent {sender} is idle: {status_data}")
   # Assign work if possible
   """
           else:
               return self._take_default_action()
           
       def _act_on_coordination(self, coord_type: str, coord_data: str, sender: int) -> str:
           """Act on coordination message from another agent"""
           if coord_type == "DIVIDE_WORK":
               return f"""
   # Work division from agent {sender}
   print(f"Work division: {coord_data}")
   # Accept assigned work
   """
           elif coord_type == "MEET":
               return f"""
   # Meeting request from agent {sender}
   print(f"Meeting request: {coord_data}")
   # Move to meeting point
   """
           else:
               return self._take_default_action()
           
       def _get_current_timestamp(self) -> str:
           """Get current timestamp"""
           import time
           return str(int(time.time()))
           
       def end(self, conversation: Conversation, completion: CompletionState) -> None:
           """Handle conversation end"""
           print(f"Coordinating agent {self.agent_id} completed")
           print(f"Shared state: {self.shared_state}")
           print(f"Message history: {len(self.message_history)} messages")

Specialized Agents
------------------

Mining Agent
^^^^^^^^^^^^

.. code-block:: python

   class MiningAgent(CoordinatingAgent):
       def __init__(self, agent_id: int, **kwargs):
           super().__init__(agent_id, **kwargs)
           self.name = f"MiningAgent_{agent_id}"
           self.specialization = "mining"
           
       def _take_default_action(self) -> str:
           """Mining-specific default action"""
           return """
   # Mining agent: Set up mining operation
   iron_pos = nearest(Resource.IronOre)
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=iron_pos,
       direction=Direction.NORTH
   )
   print(f'Mining agent placed drill at {drill.position}')
   """
           
       def _handle_resource_request(self, request_data: str, sender: int) -> str:
           """Handle resource requests as mining agent"""
           try:
               resource_data = json.loads(request_data)
               resource_type = resource_data.get('type')
               
               if resource_type in ['iron-ore', 'copper-ore', 'coal']:
                   return self._send_response(sender, "RESOURCE_AVAILABLE", 
                                            json.dumps({'type': resource_type, 'quantity': 100}))
               else:
                   return self._send_response(sender, "RESOURCE_UNAVAILABLE", 
                                            json.dumps({'type': resource_type, 'quantity': 0}))
                   
           except Exception as e:
               return self._send_response(sender, "ERROR", str(e))

Building Agent
^^^^^^^^^^^^^^

.. code-block:: python

   class BuildingAgent(CoordinatingAgent):
       def __init__(self, agent_id: int, **kwargs):
           super().__init__(agent_id, **kwargs)
           self.name = f"BuildingAgent_{agent_id}"
           self.specialization = "building"
           
       def _take_default_action(self) -> str:
           """Building-specific default action"""
           return """
   # Building agent: Set up building operation
   chest = place_entity(
       entity=Prototype.IronChest,
       position=Position(x=0, y=1),
       direction=Direction.NORTH
   )
   print(f'Building agent placed chest at {chest.position}')
   """
           
       def _handle_help_request(self, request_data: str, sender: int) -> str:
           """Handle help requests as building agent"""
           try:
               help_data = json.loads(request_data)
               help_type = help_data.get('type')
               
               if help_type == 'BUILDING':
                   return self._send_response(sender, "HELP_AVAILABLE", 
                                            json.dumps({'type': 'BUILDING', 'status': 'ready'}))
               else:
                   return self._send_response(sender, "HELP_UNAVAILABLE", "Cannot help with this request")
                   
           except Exception as e:
               return self._send_response(sender, "ERROR", str(e))

Running Multi-Agent System
--------------------------

Environment Setup
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import gym
   from fle.env.gym_env.action import Action

   # Create multi-agent environment
   env = gym.make("multiagent_iron_ore")
   
   # Create coordinating agents
   agents = [
       CoordinatingAgent(0),
       CoordinatingAgent(1),
       MiningAgent(2),
       BuildingAgent(3)
   ]
   
   # Reset environment
   obs = env.reset(options={'game_state': None})

Multi-Agent Execution Loop
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Run multi-agent system
   for step in range(20):
       # Each agent takes a step
       for agent_idx, agent in enumerate(agents):
           # Generate action from agent
           policy = agent.step(obs, None)
           
           # Create action for environment
           action = Action(
               agent_idx=agent_idx,
               game_state=None,
               code=policy.action
           )
           
           # Execute action
           obs, reward, terminated, truncated, info = env.step(action)
           
           # Check if done
           if terminated or truncated:
               break
       
       if terminated or truncated:
           break
       
       print(f"Step {step} completed")

   # Clean up
   env.close()

Expected Output
---------------

The multi-agent system will coordinate through messages:

1. **Step 1**: Agent 0 sends work division coordination
2. **Step 2**: Other agents respond to coordination
3. **Step 3**: Agents take specialized actions based on coordination
4. **Step 4**: Agents send status updates and requests
5. **Step 5+**: Continued coordination and collaboration

Example Output
^^^^^^^^^^^^^^

.. code-block:: bash

   Step 0: Multi-agent coordination (Agent 0)
   >>> Sent DIVIDE_WORK coordination message
   Step 1: Multi-agent coordination (Agent 1)
   >>> Waiting for coordination from other agents
   Step 2: Multi-agent coordination (Agent 2)
   >>> Mining agent placed drill at Position(x=10.0, y=5.0)
   Step 3: Multi-agent coordination (Agent 3)
   >>> Building agent placed chest at Position(x=0.0, y=1.0)
   Step 4: Multi-agent coordination (Agent 0)
   >>> Sent STATUS:WORKING status update

Best Practices
--------------

1. **Message Protocol**: Define clear message protocols for communication
2. **State Management**: Maintain shared state across agents
3. **Error Handling**: Handle communication failures gracefully
4. **Coordination**: Implement effective coordination mechanisms
5. **Specialization**: Create specialized agents for different tasks
6. **Testing**: Test multi-agent interactions thoroughly
7. **Documentation**: Document communication protocols and coordination logic
8. **Performance**: Optimize for multi-agent performance
9. **Scalability**: Design for scalability with more agents
10. **Monitoring**: Monitor agent interactions and performance
