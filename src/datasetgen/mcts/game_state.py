import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any

@dataclass
class GameState:
    """Serializable Factorio game state"""
    entities: str # Serialized list of entities
    inventory: Dict[str, int]
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def from_instance(cls, instance: 'FactorioInstance') -> 'GameState':
        """Capture current game state from Factorio instance"""
        entities = instance._save_entity_state(compress=True, encode=True)
        return cls(
            entities=entities,
            inventory=instance.inspect_inventory(),
        )

    @classmethod
    def parse_raw(cls, json_str: str) -> 'GameState':
        data = json.loads(json_str)
        return cls(entities=data['entities'], inventory=data['inventory'], timestamp=data['timestamp'] if 'timestamp' in data else time.time())

    @classmethod
    def parse(cls, data) -> 'GameState':
        return cls(entities=data['entities'], inventory=data['inventory'],
                   timestamp=data['timestamp'] if 'timestamp' in data else time.time())

    def to_raw(self) -> str:
        """Convert state to JSON string"""
        return json.dumps({
            'entities': self.entities,
            'inventory': self.inventory.__dict__,
            'timestamp': self.timestamp
        })

    def to_instance(self, instance: 'FactorioInstance'):
        """Restore game state to Factorio instance"""
        instance._load_entity_state(self.entities, decode=True)
        instance.set_inventory(**self.inventory)