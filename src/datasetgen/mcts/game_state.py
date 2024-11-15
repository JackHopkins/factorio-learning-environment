import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any


def _entity_serializer(obj: Any) -> Dict:
    """Custom serializer for entity-related objects"""
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items()
                if not k.startswith('_')}
    raise TypeError(f"Object of type {type(obj)} is not serializable")

@dataclass
class GameState:
    """Serializable Factorio game state"""
    entities: List[Dict[str, Any]]
    inventory: Dict[str, int]
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def from_instance(cls, instance: 'FactorioInstance') -> 'GameState':
        """Capture current game state from Factorio instance"""
        entities = instance.get_entities()
        serialized_entities = [_entity_serializer(entity) for entity in entities]
        return cls(
            entities=serialized_entities,
            inventory=instance.inspect_inventory(),
        )

    def serialize(self) -> str:
        """Convert state to JSON string"""
        return json.dumps({
            'entities': self.entities,
            'inventory': self.inventory,
            'timestamp': self.timestamp
        })

    @classmethod
    def deserialize(cls, state_str: str) -> 'GameState':
        """Reconstruct state from JSON string"""
        data = json.loads(state_str)
        return cls(**data)