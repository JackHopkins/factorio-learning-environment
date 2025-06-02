from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import numpy as np
import pickle

@dataclass
class Entity:
    """Represents an entity in the game world"""
    type: str
    position: np.ndarray  # shape (2,)
    direction: int  # 0-7 for 8 possible directions
    health: float  # 0-1


@dataclass
class InventoryItem:
    """Represents an item in the inventory"""
    type: str
    quantity: int


@dataclass
class Technology:
    """Represents a researched technology"""
    name: str
    level: int


@dataclass
class GameInfo:
    """Represents game timing and speed information"""
    tick: int
    time: float
    speed: float


@dataclass
class InventoryChange:
    """Represents a change in inventory quantity"""
    item: str
    change: int


@dataclass
class StateChanges:
    """Represents changes in game state since last observation"""
    entities_added: List[str]
    entities_removed: List[str]
    inventory_changes: List[InventoryChange]


@dataclass
class Achievement:
    """Represents achievement progress"""
    name: str
    progress: float


@dataclass
class Flow:
    """Represents a production flow rate"""
    type: str
    rate: float


@dataclass
class ProductionFlows:
    """Represents input and output production flows"""
    inputs: List[Flow]
    outputs: List[Flow]


@dataclass
class TaskCriterion:
    """Represents a task completion criterion"""
    name: str
    met: bool


@dataclass
class TaskVerification:
    """Represents task verification status"""
    success: bool
    message: str
    criteria: List[TaskCriterion]


@dataclass
class Message:
    """Represents a message from another agent"""
    sender: str
    content: str
    timestamp: float


@dataclass
class Research:
    """Represents the current research state"""
    technologies: List[Technology]
    current_research: str
    research_progress: float


@dataclass
class Observation:
    """Complete observation of the game state"""
    raw_text: str
    errors: List[str]
    entities: List[Entity]
    inventory: List[InventoryItem]
    research: Research
    game_info: GameInfo
    state_changes: StateChanges
    score: float
    achievements: Optional[Achievement]
    flows: ProductionFlows
    task_verification: Optional[TaskVerification]
    messages: List[Message]
    serialized_functions: List[Dict[str, Any]]  # List of serialized functions

    @classmethod
    def from_dict(cls, obs_dict: Dict[str, Any]) -> 'Observation':
        """Create an Observation from a dictionary matching the gym observation space"""
        # Convert entities
        entities = [
            Entity(
                type=e['type'],
                position=np.array(e['position']),
                direction=e['direction'],
                health=e['health']
            )
            for e in obs_dict.get('entities', [])
        ]

        # Convert inventory
        inventory = [
            InventoryItem(
                type=item['type'],
                quantity=item['quantity']
            )
            for item in obs_dict.get('inventory', [])
        ]

        # Convert research
        research = Research(
            technologies=[
                Technology(
                    name=tech['name'],
                    level=tech['level']
                )
                for tech in obs_dict.get('research', {}).get('technologies', [])
            ],
            current_research=obs_dict.get('research', {}).get('current_research', ''),
            research_progress=obs_dict.get('research', {}).get('research_progress', 0.0)
        )

        # Convert game info
        game_info = GameInfo(
            tick=obs_dict.get('game_info', {}).get('tick', 0),
            time=obs_dict.get('game_info', {}).get('time', 0.0),
            speed=obs_dict.get('game_info', {}).get('speed', 0.0)
        )

        # Convert state changes
        state_changes = StateChanges(
            entities_added=obs_dict.get('state_changes', {}).get('entities_added', []),
            entities_removed=obs_dict.get('state_changes', {}).get('entities_removed', []),
            inventory_changes=[
                InventoryChange(
                    item=change['item'],
                    change=change['change']
                )
                for change in obs_dict.get('state_changes', {}).get('inventory_changes', [])
            ]
        )

        # Convert achievements if present
        achievements = None
        if obs_dict.get('achievements'):
            achievements = Achievement(
                name=obs_dict['achievements']['name'],
                progress=obs_dict['achievements']['progress']
            )

        # Convert flows
        flows = ProductionFlows(
            inputs=[
                Flow(type=f['type'], rate=f['rate'])
                for f in obs_dict.get('flows', {}).get('inputs', [])
            ],
            outputs=[
                Flow(type=f['type'], rate=f['rate'])
                for f in obs_dict.get('flows', {}).get('outputs', [])
            ]
        )

        # Convert task verification if present
        task_verification = None
        if obs_dict.get('task_verification'):
            task_verification = TaskVerification(
                success=bool(obs_dict['task_verification']['success']),
                message=obs_dict['task_verification']['message'],
                criteria=[
                    TaskCriterion(
                        name=c['name'],
                        met=bool(c['met'])
                    )
                    for c in obs_dict['task_verification']['criteria']
                ]
            )

        # Convert messages
        messages = [
            Message(
                sender=msg['sender'],
                content=msg['content'],
                timestamp=msg['timestamp']
            )
            for msg in obs_dict.get('messages', [])
        ]

        # Get serialized functions
        serialized_functions = obs_dict.get('serialized_functions', [])

        return cls(
            raw_text=obs_dict.get('raw_text', ''),
            errors=obs_dict.get('errors', []),
            entities=entities,
            inventory=inventory,
            research=research,
            game_info=game_info,
            state_changes=state_changes,
            score=obs_dict.get('score', 0.0),
            achievements=achievements,
            flows=flows,
            task_verification=task_verification,
            messages=messages,
            serialized_functions=serialized_functions
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Observation to a dictionary matching the gym observation space"""
        return {
            'raw_text': self.raw_text,
            'errors': self.errors,
            'entities': [
                {
                    'type': e.type,
                    'position': e.position.tolist(),
                    'direction': e.direction,
                    'health': e.health
                }
                for e in self.entities
            ],
            'inventory': [
                {
                    'type': item.type,
                    'quantity': item.quantity
                }
                for item in self.inventory
            ],
            'research': {
                'technologies': [
                    {
                        'name': tech.name,
                        'level': tech.level
                    }
                    for tech in self.research.technologies
                ],
                'current_research': self.research.current_research,
                'research_progress': self.research.research_progress
            },
            'game_info': {
                'tick': self.game_info.tick,
                'time': self.game_info.time,
                'speed': self.game_info.speed
            },
            'state_changes': {
                'entities_added': self.state_changes.entities_added,
                'entities_removed': self.state_changes.entities_removed,
                'inventory_changes': [
                    {
                        'item': change.item,
                        'change': change.change
                    }
                    for change in self.state_changes.inventory_changes
                ]
            },
            'score': self.score,
            'achievements': {
                'name': self.achievements.name,
                'progress': self.achievements.progress
            } if self.achievements else None,
            'flows': {
                'inputs': [
                    {
                        'type': flow.type,
                        'rate': flow.rate
                    }
                    for flow in self.flows.inputs
                ],
                'outputs': [
                    {
                        'type': flow.type,
                        'rate': flow.rate
                    }
                    for flow in self.flows.outputs
                ]
            },
            'task_verification': {
                'success': int(self.task_verification.success),
                'message': self.task_verification.message,
                'criteria': [
                    {
                        'name': c.name,
                        'met': int(c.met)
                    }
                    for c in self.task_verification.criteria
                ]
            } if self.task_verification else None,
            'messages': [
                {
                    'sender': msg.sender,
                    'content': msg.content,
                    'timestamp': msg.timestamp
                }
                for msg in self.messages
            ],
            'serialized_functions': self.serialized_functions
        }

@dataclass
class FormattedObservation:
    """Container for formatted observation strings"""
    inventory_str: str  # Format: "Inventory: {item1: quantity1, item2: quantity2, ...}"
    """Formatted string showing current inventory contents.
    Example: "Inventory: {iron-ore: 100, coal: 50, transport-belt: 10}"
    Items are sorted by quantity in descending order."""

    entities_str: str  # Format: "Entities: {type1: count1, type2: count2, ...}"
    """Formatted string showing entities on the map grouped by type.
    Example: "Entities: {burner-mining-drill: 2, transport-belt: 5, inserter: 3}"
    Entities are grouped and counted by their type."""

    errors_str: str  # Format: "Error: error1\nError: error2\n..."
    """Formatted string containing any error messages from the last action.
    Example: "Error: Invalid position for entity placement\nError: Not enough resources"
    Empty string if no errors occurred."""

    flows_str: str  # Format: "Production Flows: {inputs: {item1: rate1/s, ...}, outputs: {item1: rate1/s, ...}}"
    """Formatted string showing current production flow rates.
    Example: "Production Flows: {inputs: {coal: 1.50/s}, outputs: {iron-ore: 0.75/s}}"
    Shows both input consumption and output production rates per second."""

    achievements_str: str  # Format: "Achievement Progress: name - XX.X%"
    """Formatted string showing achievement progress.
    Example: "Achievement Progress: Automated Mining - 75.0%"
    Empty string if no achievements are being tracked."""

    task_str: str  # Format: "Task Status: SUCCESS/IN PROGRESS\nMessage: ...\nCriteria:\n  ✓/✗ criterion1\n  ✓/✗ criterion2"
    """Formatted string showing task verification status and criteria.
    Example: "Task Status: IN PROGRESS\nMessage: Need more iron plates\nCriteria:\n  ✓ Place mining drill\n  ✗ Produce 100 iron plates"
    Empty string if no task is being tracked."""

    messages_str: str  # Format: "Messages received:\n[Agent X]: message1\n[Agent Y]: message2\n..."
    """Formatted string showing messages received from other agents.
    Example: "Messages received:\n[Agent 1]: Need more iron plates\n[Agent 2]: I'll help with that"
    Empty string if no messages were received."""

    functions_str: str  # Format: "Available Functions:\ndef func1(param1: type1) -> return_type\n  \"\"\"docstring\"\"\""
    """Formatted string showing available functions with their signatures and docstrings.
    Example: "Available Functions:\ndef find_idle_furnaces(entities: List[Entity]) -> List[Entity]\n  \"\"\"Find all furnaces that are not currently working.\"\"\""
    Shows function names, parameter types, return types, and docstrings."""

    raw_str: str  # Combined format of all above strings with newlines
    """Complete formatted observation combining all components.
    Example:
    Inventory: {iron-ore: 100, coal: 50}
    Entities: {burner-mining-drill: 2, transport-belt: 5}
    Production Flows: {inputs: {coal: 1.50/s}, outputs: {iron-ore: 0.75/s}}
    Available Functions:
    def find_idle_furnaces(entities: List[Entity]) -> List[Entity]
      \"\"\"Find all furnaces that are not currently working.\"\"\"
    Task Status: IN PROGRESS
    Message: Need more iron plates
    Criteria:
      ✓ Place mining drill
      ✗ Produce 100 iron plates
    Messages received:
    [Agent 1]: Need more iron plates
    [Agent 2]: I'll help with that
    Raw Output:
    [Any raw output from the last action]"""


class BasicObservationFormatter:
    """Formats gym environment observations into helpful strings"""
    
    @staticmethod
    def format_inventory(inventory: List[Dict[str, Any]]) -> str:
        """Format inventory information"""
        if not inventory:
            return "Inventory: {}"
            
        # Sort items by quantity for consistent output
        sorted_items = sorted(inventory, key=lambda x: x['quantity'], reverse=True)
        
        # Format each item
        item_strs = []
        for item in sorted_items:
            if item['quantity'] > 0:
                item_strs.append(f"{item['type']}: {item['quantity']}")
                
        return f"Inventory: {{{', '.join(item_strs)}}}"
    
    @staticmethod
    def format_entities(entities: List[Dict[str, Any]]) -> str:
        """Format entity information"""
        if not entities:
            return "Entities: []"
            
        # Group entities by type
        entity_groups = {}
        for entity in entities:
            entity_type = entity['type']
            if entity_type not in entity_groups:
                entity_groups[entity_type] = []
            entity_groups[entity_type].append(entity)
            
        # Format each entity group
        group_strs = []
        for entity_type, group in sorted(entity_groups.items()):
            count = len(group)
            group_strs.append(f"{entity_type}: {count}")
            
        return f"Entities: {{{', '.join(group_strs)}}}"
    
    @staticmethod
    def format_errors(errors: List[str]) -> str:
        """Format error information"""
        if not errors:
            return ""
            
        return "\n".join(f"Error: {error}" for error in errors)
    
    @staticmethod
    def format_flows(flows: Dict[str, Any]) -> str:
        """Format production flow information"""
        if not flows:
            return "Production Flows: {}"
            
        input_strs = []
        output_strs = []
        
        # Format input flows
        if flows.get('inputs'):
            for flow in flows['inputs']:
                if flow['rate'] > 0:
                    input_strs.append(f"{flow['type']}: {flow['rate']:.2f}/s")
                    
        # Format output flows
        if flows.get('outputs'):
            for flow in flows['outputs']:
                if flow['rate'] > 0:
                    output_strs.append(f"{flow['type']}: {flow['rate']:.2f}/s")
                    
        flow_str = "Production Flows: {"
        if input_strs:
            flow_str += f"inputs: {{{', '.join(input_strs)}}}"
        if input_strs and output_strs:
            flow_str += ", "
        if output_strs:
            flow_str += f"outputs: {{{', '.join(output_strs)}}}"
        flow_str += "}"
        
        return flow_str
    
    @staticmethod
    def format_achievements(achievements: Optional[Dict[str, Any]]) -> str:
        """Format achievement information"""
        if not achievements:
            return ""
            
        return f"Achievement Progress: {achievements['name']} - {achievements['progress']*100:.1f}%"
    
    @staticmethod
    def format_task(task: Optional[Dict[str, Any]]) -> str:
        """Format task verification information"""
        if not task:
            return ""
            
        status = "SUCCESS" if task['success'] else "IN PROGRESS"
        task_str = f"Task Status: {status}\n"
        
        if task.get('message'):
            task_str += f"Message: {task['message']}\n"
            
        if task.get('criteria'):
            task_str += "Criteria:\n"
            for criterion in task['criteria']:
                status = "✓" if criterion['met'] else "✗"
                task_str += f"  {status} {criterion['name']}\n"
                
        return task_str
    
    @staticmethod
    def format_messages(messages: List[Dict[str, Any]], last_timestamp: float = 0.0) -> str:
        """Format messages from other agents"""
        if not messages:
            return ""
            
        # Filter messages newer than last timestamp
        new_messages = [
            msg for msg in messages 
            if msg['timestamp'] > last_timestamp
        ]
        
        if not new_messages:
            return ""
            
        # Format messages
        message_strs = ["Messages received:"]
        for msg in new_messages:
            sender_info = f"Agent {msg['sender']}" if msg['sender'] != "-1" else "Leader"
            message_strs.append(f"[{sender_info}]: {msg['content']}")
            
        return "\n".join(message_strs)
    
    @staticmethod
    def format_state_changes(changes: Dict[str, Any]) -> str:
        """Format state change information"""
        if not changes:
            return ""
            
        change_strs = []
        
        # Format entity changes
        if changes.get('entities_added'):
            change_strs.append(f"Added: {', '.join(changes['entities_added'])}")
        if changes.get('entities_removed'):
            change_strs.append(f"Removed: {', '.join(changes['entities_removed'])}")
            
        # Format inventory changes
        if changes.get('inventory_changes'):
            inv_changes = []
            for change in changes['inventory_changes']:
                sign = "+" if change['change'] > 0 else ""
                inv_changes.append(f"{change['item']}: {sign}{change['change']}")
            if inv_changes:
                change_strs.append(f"Inventory Changes: {', '.join(inv_changes)}")
                
        return "\n".join(change_strs)
    
    @staticmethod
    def format_functions(serialized_functions: List[Dict[str, Any]]) -> str:
        """Format serialized functions into readable descriptions"""
        if not serialized_functions:
            return "Available Functions: None"
            
        # Unpickle and format each function
        function_strs = ["Available Functions:"]
        for func_data in serialized_functions:
            try:
                # Unpickle the function
                pickled_data = bytes.fromhex(func_data['pickled_function'])
                func = pickle.loads(pickled_data)
                
                # Get formatted string representation
                function_strs.append(f"\n{func}")
            except Exception as e:
                function_strs.append(f"\n{func_data['name']}: [Error unpickling function: {str(e)}]")
                
        return "\n".join(function_strs)

    def format(self, observation: Union[Dict[str, Any], Observation], last_message_timestamp: float = 0.0) -> FormattedObservation:
        """Format a complete observation into helpful strings"""
        # Convert Observation to dict if needed
        if isinstance(observation, Observation):
            obs_dict = observation.to_dict()
        else:
            obs_dict = observation

        # Format each component
        inventory_str = self.format_inventory(obs_dict.get('inventory', []))
        entities_str = self.format_entities(obs_dict.get('entities', []))
        errors_str = self.format_errors(obs_dict.get('errors', []))
        flows_str = self.format_flows(obs_dict.get('flows', {}))
        achievements_str = self.format_achievements(obs_dict.get('achievements'))
        task_str = self.format_task(obs_dict.get('task_verification'))
        messages_str = self.format_messages(obs_dict.get('messages', []), last_message_timestamp)
        functions_str = self.format_functions(obs_dict.get('serialized_functions', []))
        
        # Combine all formatted strings
        formatted_parts = [
            inventory_str,
            entities_str,
            flows_str,
            functions_str 
        ]
        
        # Add optional components if they exist
        if errors_str:
            formatted_parts.append(errors_str)
        if achievements_str:
            formatted_parts.append(achievements_str)
        if task_str:
            formatted_parts.append(task_str)
        if messages_str:
            formatted_parts.append(messages_str)
            
        # Add state changes if they exist
        state_changes = self.format_state_changes(obs_dict.get('state_changes', {}))
        if state_changes:
            formatted_parts.append(state_changes)
            
        # Add raw text if it exists
        raw_str = obs_dict.get('raw_text', '')
        if raw_str:
            formatted_parts.append(f"\nRaw Output:\n{raw_str}")
            
        # Combine all parts with newlines
        raw_str = "\n".join(formatted_parts)
        
        return FormattedObservation(
            inventory_str=inventory_str,
            entities_str=entities_str,
            errors_str=errors_str,
            flows_str=flows_str,
            achievements_str=achievements_str,
            task_str=task_str,
            messages_str=messages_str,
            functions_str=functions_str,
            raw_str=raw_str
        )
