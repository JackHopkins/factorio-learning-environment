from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
import numpy as np

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

