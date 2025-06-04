from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
import numpy as np
import pickle

from env.src.models.technology_state import TechnologyState
from env.src.models.research_state import ResearchState
from env.src.models.achievements import ProductionFlows
from agents import TaskResponse
from env.src.entities import Entity, Direction, Position, EntityStatus, TileDimensions, Dimensions, Inventory

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
class EntityChange:
    """Represents a change in entity state"""
    entity: str
    change: int  # positive for added, negative for removed


@dataclass
class StateChanges:
    """Represents changes in game state since last observation"""
    entity_changes: List[EntityChange]
    inventory_changes: List[InventoryChange]


@dataclass
class Achievement:
    """Represents achievement progress"""
    static: Dict[str, float]  # Static achievements (crafted/harvested items)
    dynamic: Dict[str, float]  # Dynamic achievements (ongoing production)

    @classmethod
    def from_dict(cls, data: Dict[str, Dict[str, float]]) -> 'Achievement':
        """Create an Achievement from a dictionary"""
        return cls(
            static=data.get('static', {}),
            dynamic=data.get('dynamic', {})
        )

    def to_dict(self) -> Dict[str, Dict[str, float]]:
        """Convert Achievement to dictionary"""
        return {
            'static': self.static,
            'dynamic': self.dynamic
        }


@dataclass
class AgentMessage:
    """Represents a message from another agent"""
    sender: str
    content: str
    timestamp: float


@dataclass
class Observation:
    """Complete observation of the game state"""
    raw_text: str
    errors: List[str]
    entities: List[Entity]
    inventory: Inventory
    research: ResearchState
    game_info: GameInfo
    state_changes: StateChanges
    score: float
    achievements: List[Achievement]
    flows: ProductionFlows
    task_verification: Optional[TaskResponse]
    messages: List[AgentMessage]
    serialized_functions: List[Dict[str, Any]]  # List of serialized functions
    logging_results: Dict[int, List[Tuple[int, str]]]  # Line number -> list of (line number, value) tuples

    @classmethod
    def from_dict(cls, obs_dict: Dict[str, Any]) -> 'Observation':
        """Create an Observation from a dictionary matching the gym observation space"""
        # Convert entities
        entities = []
        for e in obs_dict.get('entities', []):
            entity = Entity(
                name=e['name'],
                direction=Direction(e['direction']),
                position=Position(x=e['position'][0], y=e['position'][1]),
                energy=e['energy'],
                dimensions=Dimensions(
                    width=e['dimensions']['width'],
                    height=e['dimensions']['height']
                ),
                tile_dimensions=TileDimensions(
                    tile_width=e['tile_dimensions']['tile_width'],
                    tile_height=e['tile_dimensions']['tile_height']
                ),
                prototype=None,  # Default value as it's not in observation space
                health=e['health'],
                status=EntityStatus.from_int(e['status']),
                warnings=e['warnings'],
                id=e['id'],
                type=e['type']
            )
            entities.append(entity)

        # Convert inventory
        inventory = Inventory()
        if isinstance(obs_dict.get('inventory'), dict):
            # Handle direct dictionary format
            for item_type, quantity in obs_dict['inventory'].items():
                inventory[item_type] = quantity
        else:
            # Handle list of dicts format
            for item in obs_dict.get('inventory', []):
                if isinstance(item, dict):
                    inventory[item['type']] = item['quantity']

        # Convert research state
        research = ResearchState(
            technologies={
                name: TechnologyState(
                    name=tech['name'],
                    researched=tech['researched'],
                    enabled=tech['enabled'],
                    level=tech['level'],
                    research_unit_count=tech['research_unit_count'],
                    research_unit_energy=tech['research_unit_energy'],
                    prerequisites=tech['prerequisites'],
                    ingredients=tech['ingredients']
                )
                for name, tech in obs_dict.get('research', {}).get('technologies', {}).items()
            },
            current_research=obs_dict.get('research', {}).get('current_research'),
            research_progress=obs_dict.get('research', {}).get('research_progress', 0.0),
            research_queue=obs_dict.get('research', {}).get('research_queue', []),
            progress=obs_dict.get('research', {}).get('progress', {})
        )

        # Convert game info
        game_info = GameInfo(
            tick=obs_dict.get('game_info', {}).get('tick', 0),
            time=obs_dict.get('game_info', {}).get('time', 0.0),
            speed=obs_dict.get('game_info', {}).get('speed', 0.0)
        )

        # Convert state changes
        # Aggregate entity changes by type
        entity_changes = {}
        for entity in obs_dict.get('state_changes', {}).get('entities_added', []):
            entity_changes[entity] = entity_changes.get(entity, 0) + 1
        for entity in obs_dict.get('state_changes', {}).get('entities_removed', []):
            entity_changes[entity] = entity_changes.get(entity, 0) - 1
            
        state_changes = StateChanges(
            entity_changes=[
                EntityChange(entity=entity, change=change)
                for entity, change in entity_changes.items()
                if change != 0  # Only include non-zero changes
            ],
            inventory_changes=[
                InventoryChange(
                    item=change['item'],
                    change=change['change']
                )
                for change in obs_dict.get('state_changes', {}).get('inventory_changes', [])
            ]
        )

        # Convert achievements if present
        achievements = []
        if obs_dict.get('achievements'):
            for achievement in obs_dict['achievements']:
                achievements.append(Achievement(
                    static=achievement['static'],
                    dynamic=achievement['dynamic']
                ))

        # Convert flows
        flows = ProductionFlows.from_dict(obs_dict.get('flows', {}))

        # Convert task verification if present
        task_verification = None
        if obs_dict.get('task_verification'):
            task_verification = TaskResponse(
                success=bool(obs_dict['task_verification']['success']),
                meta=obs_dict['task_verification'].get('meta', {})
            )

        # Convert messages
        messages = [
            AgentMessage(
                sender=msg['sender'],
                content=msg['content'],
                timestamp=msg['timestamp']
            )
            for msg in obs_dict.get('messages', [])
        ]

        # Get serialized functions
        serialized_functions = obs_dict.get('serialized_functions', [])

        # Get logging results
        logging_results = obs_dict.get('logging_results', {})

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
            serialized_functions=serialized_functions,
            logging_results=logging_results
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Observation to a dictionary matching the gym observation space"""
        return {
            'raw_text': self.raw_text,
            'errors': self.errors,
            'entities': [
                {
                    'name': e.name,
                    'direction': e.direction.value,
                    'position': [e.position.x, e.position.y],
                    'energy': e.energy,
                    'dimensions': {
                        'width': e.dimensions.width,
                        'height': e.dimensions.height
                    },
                    'tile_dimensions': {
                        'tile_width': e.tile_dimensions.tile_width,
                        'tile_height': e.tile_dimensions.tile_height
                    },
                    'health': e.health,
                    'status': list(EntityStatus).index(e.status),
                    'warnings': e.warnings,
                    'id': e.id if e.id is not None else 0,
                    'type': e.type if e.type is not None else e.name
                }
                for e in self.entities
            ],
            'inventory': {
                item: quantity 
                for item, quantity in self.inventory.items() 
                if quantity > 0
            },
            'research': {
                'technologies': {
                    name: {
                        'name': tech.name,
                        'researched': tech.researched,
                        'enabled': tech.enabled,
                        'level': tech.level,
                        'research_unit_count': tech.research_unit_count,
                        'research_unit_energy': tech.research_unit_energy,
                        'prerequisites': tech.prerequisites,
                        'ingredients': tech.ingredients
                    }
                    for name, tech in self.research.technologies.items()
                },
                'current_research': self.research.current_research,
                'research_progress': self.research.research_progress,
                'research_queue': self.research.research_queue,
                'progress': self.research.progress
            },
            'game_info': {
                'tick': self.game_info.tick,
                'time': self.game_info.time,
                'speed': self.game_info.speed
            },
            'state_changes': {
                'entity_changes': [
                    {
                        'entity': change.entity,
                        'change': change.change
                    }
                    for change in self.state_changes.entity_changes
                ],
                'inventory_changes': [
                    {
                        'item': change.item,
                        'change': change.change
                    }
                    for change in self.state_changes.inventory_changes
                ]
            },
            'score': self.score,
            'achievements': [
                {
                    'static': achievement.static,
                    'dynamic': achievement.dynamic
                }
                for achievement in self.achievements
            ],
            'flows': self.flows.to_dict(),
            'task_verification': {
                'success': int(self.task_verification.success),
                'meta': self.task_verification.meta
            } if self.task_verification else None,
            'messages': [
                {
                    'sender': msg.sender,
                    'content': msg.content,
                    'timestamp': msg.timestamp
                }
                for msg in self.messages
            ],
            'serialized_functions': self.serialized_functions,
            'logging_results': self.logging_results
        }

@dataclass
class FormattedObservation:
    """Container for formatted observation strings"""
    inventory_str: str
    """Formatted string showing current inventory contents.
    Example:
    ### Inventory
    - iron-ore: 100
    - coal: 50
    - transport-belt: 10
    Items are sorted by quantity in descending order."""

    entities_str: str
    """Formatted string showing entities on the map grouped by type.
    Example:
    ### Entities
    - burner-mining-drill: 2
    - transport-belt: 5
    - inserter: 3
    Entities are grouped and counted by their type."""

    errors_str: str
    """Formatted string containing any error messages from the last action.
    Example:
    ### Errors
    - Invalid position for entity placement
    - Not enough resources
    Empty string if no errors occurred."""

    flows_str: str
    """Formatted string showing current production flow rates.
    Example:
    ### Production Flows
    #### Inputs
    - coal: 1.50/s
    #### Outputs
    - iron-ore: 0.75/s
    Shows both input consumption and output production rates per second."""

    achievements_str: str
    """Formatted string showing achievement progress.
    Example:
    ### Achievement Progress
    - Automated Mining: 75.0%
    Empty string if no achievements are being tracked."""

    task_str: str
    """Formatted string showing task verification status and criteria.
    Example:
    ### Task Status
    ⏳ IN PROGRESS

    **Message:** Need more iron plates

    **Criteria:**
    - ✅ Place mining drill
    - ❌ Produce 100 iron plates
    Empty string if no task is being tracked."""

    messages_str: str
    """Formatted string showing messages received from other agents.
    Example:
    ### Messages
    - **[Agent 1]**: Need more iron plates
    - **[Agent 2]**: I'll help with that
    Empty string if no messages were received."""

    functions_str: str
    """Formatted string showing available functions with their signatures and docstrings.
    Example:
    ### Available Functions
    ```python
    def find_idle_furnaces(entities: List[Entity]) -> List[Entity]
      \"\"\"Find all furnaces that are not currently working.\"\"\"
    ```
    Shows function names, parameter types, return types, and docstrings."""

    logging_results_str: str
    """Formatted string showing the output from each step of the agent's code execution.
    Example:
    ### Step Output
    - Line 1: Placed mining drill at (10, 10)
    - Line 2: Connected power line
    - Line 3: Started mining operation
    Shows the line number and output value for each step."""

    raw_str: str
    """Complete formatted observation combining all components.
    Example:
    ### Inventory
    - iron-ore: 100
    - coal: 50

    ### Entities
    - burner-mining-drill: 2
    - transport-belt: 5

    ### Production Flows
    #### Inputs
    - coal: 1.50/s
    #### Outputs
    - iron-ore: 0.75/s

    ### Available Functions
    ```python
    def find_idle_furnaces(entities: List[Entity]) -> List[Entity]
      \"\"\"Find all furnaces that are not currently working.\"\"\"
    ```

    ### Task Status
    ⏳ IN PROGRESS

    **Message:** Need more iron plates

    **Criteria:**
    - ✅ Place mining drill
    - ❌ Produce 100 iron plates

    ### Messages
    - **[Agent 1]**: Need more iron plates
    - **[Agent 2]**: I'll help with that

    ### Step Output
    - Line 1: Placed mining drill at (10, 10)
    - Line 2: Connected power line
    - Line 3: Started mining operation

    ### Raw Output
    ```
    [Any raw output from the last action]
    ```"""


class BasicObservationFormatter:
    """Formats gym environment observations into helpful strings"""
    
    def __init__(self,
                 include_inventory: bool = True,
                 include_entities: bool = True,
                 include_errors: bool = True,
                 include_flows: bool = True,
                 include_achievements: bool = True,
                 include_task: bool = True,
                 include_messages: bool = True,
                 include_functions: bool = True,
                 include_logging_results: bool = True,
                 include_state_changes: bool = True,
                 include_raw_output: bool = True,
                 include_research: bool = True):
        """Initialize the formatter with flags for which fields to include"""
        self.include_inventory = include_inventory
        self.include_entities = include_entities
        self.include_errors = include_errors
        self.include_flows = include_flows
        self.include_achievements = include_achievements
        self.include_task = include_task
        self.include_messages = include_messages
        self.include_functions = include_functions
        self.include_logging_results = include_logging_results
        self.include_state_changes = include_state_changes
        self.include_raw_output = include_raw_output
        self.include_research = include_research

    @staticmethod
    def format_inventory(inventory: Dict[str, Any]) -> str:
        """Format inventory information"""
        if not inventory:
            return "### Inventory\nEmpty"
            
        # Sort items by quantity for consistent output
        sorted_items = sorted(inventory.items(), key=lambda x: x[1], reverse=True)
        
        # Format each item
        item_strs = []
        for item_type, quantity in sorted_items:
            if quantity > 0:
                item_strs.append(f"- {item_type}: {quantity}")
                
        return "### Inventory\n" + "\n".join(item_strs)
    
    @staticmethod
    def format_entities(entities: List[Dict[str, Any]]) -> str:
        """Format entity information"""
        if not entities:
            return "### Entities\nNone found"
            
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
            # Get status information for the group
            statuses = {}
            for entity in group:
                status = entity.get('status', 0)
                if status not in statuses:
                    statuses[status] = 0
                statuses[status] += 1
            
            # Format the group with status information
            status_str = ""
            if statuses:
                status_str = " ["
                status_parts = []
                for status, count in statuses.items():
                    status_name = EntityStatus.from_int(status).name
                    status_parts.append(f"{status_name}: {count}")
                status_str += ", ".join(status_parts) + "]"
            
            group_strs.append(f"- {entity_type}: {count}{status_str}")
            
        return "### Entities\n" + "\n".join(group_strs)
    
    @staticmethod
    def format_errors(errors: List[str]) -> str:
        """Format error information"""
        if not errors:
            return ""
            
        return "### Errors\n" + "\n".join(f"- {error}" for error in errors)
    
    @staticmethod
    def format_flows(flows: Dict[str, Any]) -> str:
        """Format production flow information"""
        if not flows:
            return "### Production Flows\nNone"
            
        flow_str = "### Production Flows\n"
        print(flows)
        
        # Format input flows
        if flows.get('input'):
            flow_str += "#### Inputs\n"
            for item, rate in flows['input'].items():
                if rate > 0:
                    flow_str += f"- {item}: {rate:.2f}/s\n"
                    
        # Format output flows
        if flows.get('output'):
            if flows.get('input'):
                flow_str += "\n"
            flow_str += "#### Outputs\n"
            for item, rate in flows['output'].items():
                if rate > 0:
                    flow_str += f"- {item}: {rate:.2f}/s\n"
                    
        # Format crafted items
        if flows.get('crafted'):
            if flows.get('input') or flows.get('output'):
                flow_str += "\n"
            flow_str += "#### Crafted Items\n"
            for item in flows['crafted']:
                # Each item in crafted is a Dict[str, Any]
                item_name = item.get('type', 'unknown')
                count = item.get('count', 1)
                flow_str += f"- {item_name}: {count}\n"
                
        # Format harvested items
        if flows.get('harvested'):
            if flows.get('input') or flows.get('output') or flows.get('crafted'):
                flow_str += "\n"
            flow_str += "#### Harvested Items\n"
            for item, amount in flows['harvested'].items():
                if amount > 0:
                    flow_str += f"- {item}: {amount:.2f}\n"

        # Format price list
        if flows.get('price_list'):
            if any(flows.get(k) for k in ['input', 'output', 'crafted', 'harvested']):
                flow_str += "\n"
            flow_str += "#### Price List\n"
            for item, price in flows['price_list'].items():
                flow_str += f"- {item}: {price:.2f}\n"

        # Format static items
        if flows.get('static_items'):
            if any(flows.get(k) for k in ['input', 'output', 'crafted', 'harvested', 'price_list']):
                flow_str += "\n"
            flow_str += "#### Static Items\n"
            for item, value in flows['static_items'].items():
                flow_str += f"- {item}: {value:.2f}\n"
        
        return flow_str
    
    @staticmethod
    def format_research(research: Dict[str, Any]) -> str:
        """Format research state information"""
        if not research:
            return "### Research\nNone"
            
        research_str = "### Research\n"
        
        # Format current research
        if research.get('current_research'):
            research_str += f"#### Current Research\n- {research['current_research']}: {research['research_progress']*100:.1f}%\n"
            
        # Format research queue
        if research.get('research_queue'):
            if research.get('current_research'):
                research_str += "\n"
            research_str += "#### Research Queue\n"
            for tech in research['research_queue']:
                research_str += f"- {tech}\n"
                
        # Format technologies
        if research.get('technologies'):
            if research.get('current_research') or research.get('research_queue'):
                research_str += "\n"
            research_str += "#### Technologies\n"
            for name, tech in research['technologies'].items():
                status = "✅" if tech['researched'] else "⏳"
                enabled = "🔓" if tech['enabled'] else "🔒"
                research_str += f"- {status} {enabled} {name} (Level {tech['level']})\n"
                if tech['prerequisites']:
                    research_str += f"  Prerequisites: {', '.join(tech['prerequisites'])}\n"
                if tech['ingredients']:
                    # Handle both list of dicts and dict formats
                    if isinstance(tech['ingredients'], list):
                        research_str += f"  Ingredients: {', '.join(f'{ing.get('name', '')} x{ing.get('amount', 0)}' for ing in tech['ingredients'])}\n"
                    else:
                        research_str += f"  Ingredients: {', '.join(f'{item} x{amount}' for item, amount in tech['ingredients'].items())}\n"
                if tech['research_unit_count'] > 0:
                    research_str += f"  Research Units: {tech['research_unit_count']} (Energy: {tech['research_unit_energy']:.1f})\n"
        
        return research_str
    
    @staticmethod
    def format_achievements(achievements: List[Union[Achievement, Dict[str, Any]]]) -> str:
        """Format achievement information"""
        if not achievements:
            return ""
            
        achievement_strs = ["### Achievement Progress"]
        
        for achievement in achievements:
            # Handle both dictionary and Achievement object formats
            static = achievement.get('static', {}) if isinstance(achievement, dict) else achievement.static
            dynamic = achievement.get('dynamic', {}) if isinstance(achievement, dict) else achievement.dynamic
            
            if static:
                achievement_strs.append("\n#### Static Achievements")
                for item, value in static.items():
                    achievement_strs.append(f"- {item}: {value:.1f}")
                    
            if dynamic:
                achievement_strs.append("\n#### Dynamic Achievements")
                for item, value in dynamic.items():
                    achievement_strs.append(f"- {item}: {value:.1f}/s")
        
        return "\n".join(achievement_strs)
    
    @staticmethod
    def format_task(task: Optional[Dict[str, Any]]) -> str:
        """Format task verification information"""
        if not task:
            return ""
            
        status = "✅ SUCCESS" if task['success'] else "⏳ IN PROGRESS"
        task_str = f"### Task Status\n{status}\n"
        
        if task.get('message'):
            task_str += f"\n**Message:** {task['message']}\n"
            
        if task.get('meta'):
            task_str += "\n**Task Details:**\n"
            for key, value in task['meta'].items():
                task_str += f"- {key}: {value}\n"
                
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
        message_strs = ["### Messages"]
        for msg in new_messages:
            sender_info = f"Agent {msg['sender']}" if msg['sender'] != "-1" else "Leader"
            message_strs.append(f"- **[{sender_info}]**: {msg['content']}")
            
        return "\n".join(message_strs)
    
    @staticmethod
    def format_state_changes(changes: Dict[str, Any]) -> str:
        """Format state change information"""
        if not changes:
            return ""
            
        change_strs = ["### State Changes"]
        
        # Format entity changes
        if changes.get('entity_changes'):
            change_strs.append("\n**Entity Changes:**")
            for change in changes['entity_changes']:
                sign = "+" if change['change'] > 0 else ""
                change_strs.append(f"- {change['entity']}: {sign}{change['change']}")
            
        # Format inventory changes
        if changes.get('inventory_changes'):
            change_strs.append("\n**Inventory Changes:**")
            for change in changes['inventory_changes']:
                sign = "+" if change['change'] > 0 else ""
                change_strs.append(f"- {change['item']}: {sign}{change['change']}")
                
        return "\n".join(change_strs)
    
    @staticmethod
    def format_functions(serialized_functions: List[Dict[str, Any]]) -> str:
        """Format serialized functions into readable descriptions"""
        if not serialized_functions:
            return "### Available Functions\nNone"
            
        # Unpickle and format each function
        function_strs = ["### Available Functions"]
        for func_data in serialized_functions:
            try:
                # Unpickle the function
                pickled_data = bytes.fromhex(func_data['pickled_function'])
                func = pickle.loads(pickled_data)
                
                # Get formatted string representation
                function_strs.append(f"\n```python\n{func}\n```")
            except Exception as e:
                function_strs.append(f"\n- {func_data['name']}: [Error unpickling function: {str(e)}]")
                
        return "\n".join(function_strs)

    @staticmethod
    def format_logging_results(logging_results: Dict[int, List[Tuple[int, str]]]) -> str:
        """Format logging results from agent's code execution"""
        if not logging_results:
            return ""
            
        # Sort by line number for consistent output
        sorted_lines = sorted(logging_results.items())
        
        # Format each line's output
        output_lines = ["### Step Output"]
        for line_num, outputs in sorted_lines:
            for _, value in outputs:
                output_lines.append(f"- Line {line_num}: {value}")
                
        return "\n".join(output_lines)

    def format(self, observation: Observation, last_message_timestamp: float = 0.0) -> FormattedObservation:
        """Format a complete observation into helpful strings"""
        # Convert Observation to dict if needed
        obs_dict = observation.to_dict()

        # Format each component based on include flags
        formatted_parts = []
        
        if self.include_inventory:
            assert isinstance(obs_dict.get('inventory', {}), dict), obs_dict.get('inventory', {})
            inventory_str = self.format_inventory(obs_dict.get('inventory', {}))
            formatted_parts.append(inventory_str)
            
        if self.include_entities:
            entities_str = self.format_entities(obs_dict.get('entities', []))
            formatted_parts.append(entities_str)
            
        if self.include_flows:
            flows_str = self.format_flows(obs_dict.get('flows', {}))
            formatted_parts.append(flows_str)
            
        if self.include_functions:
            functions_str = self.format_functions(obs_dict.get('serialized_functions', []))
            formatted_parts.append(functions_str)
            
        # Add research information
        if self.include_research:
            research_str = self.format_research(obs_dict.get('research', {}))
            formatted_parts.append(research_str)
        
        # Add optional components if they exist and are enabled
        if self.include_errors:
            errors_str = self.format_errors(obs_dict.get('errors', []))
            if errors_str:
                formatted_parts.append(errors_str)
                
        if self.include_achievements:
            achievements_str = self.format_achievements(obs_dict.get('achievements', []))
            if achievements_str:
                formatted_parts.append(achievements_str)
                
        if self.include_task:
            task_str = self.format_task(obs_dict.get('task_verification'))
            if task_str:
                formatted_parts.append(task_str)
                
        if self.include_messages:
            messages_str = self.format_messages(obs_dict.get('messages', []), last_message_timestamp)
            if messages_str:
                formatted_parts.append(messages_str)
                
        if self.include_logging_results:
            logging_results_str = self.format_logging_results(obs_dict.get('logging_results', {}))
            if logging_results_str:
                formatted_parts.append(logging_results_str)
            
        if self.include_state_changes:
            state_changes = self.format_state_changes(obs_dict.get('state_changes', {}))
            if state_changes:
                formatted_parts.append(state_changes)
            
        if self.include_raw_output:
            raw_str = obs_dict.get('raw_text', '')
            if raw_str:
                formatted_parts.append(f"### Raw Output\n```\n{raw_str}\n```")
            
        # Combine all parts with newlines
        raw_str = "\n\n".join(formatted_parts)
        
        # Create FormattedObservation with all fields, even if they're empty
        return FormattedObservation(
            inventory_str=self.format_inventory(obs_dict.get('inventory', {})) if self.include_inventory else "",
            entities_str=self.format_entities(obs_dict.get('entities', [])) if self.include_entities else "",
            errors_str=self.format_errors(obs_dict.get('errors', [])) if self.include_errors else "",
            flows_str=self.format_flows(obs_dict.get('flows', {})) if self.include_flows else "",
            achievements_str=self.format_achievements(obs_dict.get('achievements', [])) if self.include_achievements else "",
            task_str=self.format_task(obs_dict.get('task_verification')) if self.include_task else "",
            messages_str=self.format_messages(obs_dict.get('messages', []), last_message_timestamp) if self.include_messages else "",
            functions_str=self.format_functions(obs_dict.get('serialized_functions', [])) if self.include_functions else "",
            logging_results_str=self.format_logging_results(obs_dict.get('logging_results', {})) if self.include_logging_results else "",
            raw_str=raw_str
        )
