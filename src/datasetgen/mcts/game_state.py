import json
import pickle
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any

def is_serializable(obj: Any) -> bool:
    """Test if an object can be serialized with pickle"""
    try:
        if isinstance(obj, type):
            return False

        # Common built-in types that are always serializable
        if isinstance(obj, (int, float, str, bool, list, dict, tuple, set)):
            return True

        pickle.dumps(obj)
        return True
    except (pickle.PicklingError, TypeError, AttributeError):
        return False

def filter_serializable_vars(vars_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Filter dictionary to only include serializable items"""
    return {
        key: value for key, value in vars_dict.items()
        if is_serializable(value)
    }


@dataclass
class GameState:
    """Serializable Factorio game state"""
    entities: str # Serialized list of entities
    inventory: Dict[str, int]
    timestamp: float = field(default_factory=time.time)
    namespace: bytes = field(default_factory=bytes)

    @classmethod
    def from_instance(cls, instance: 'FactorioInstance') -> 'GameState':

        """Capture current game state from Factorio instance"""
        entities = instance._save_entity_state(compress=True, encode=True)

        # Filter and pickle only serializable variables
        if hasattr(instance, 'persistent_vars'):
            serializable_vars = filter_serializable_vars(instance.persistent_vars)
            namespace = pickle.dumps(serializable_vars) if serializable_vars else bytes()
        else:
            namespace = bytes()

        return cls(
            entities=entities,
            inventory=instance.inspect_inventory(),
            namespace=namespace
        )

    @classmethod
    def parse_raw(cls, json_str: str) -> 'GameState':
        data = json.loads(json_str)
        namespace = bytes.fromhex(data['namespace']) if 'namespace' in data else bytes()
        return cls(
            entities=data['entities'],
            inventory=data['inventory'],
            timestamp=data['timestamp'] if 'timestamp' in data else time.time(),
            namespace=namespace
        )

    @classmethod
    def parse(cls, data) -> 'GameState':
        namespace = bytes.fromhex(data['namespace']) if 'namespace' in data else bytes()
        return cls(
            entities=data['entities'],
            inventory=data['inventory'],
            timestamp=data['timestamp'] if 'timestamp' in data else time.time(),
            namespace=namespace
        )

    def to_raw(self) -> str:
        """Convert state to JSON string"""
        return json.dumps({
            'entities': self.entities,
            'inventory': self.inventory.__dict__,
            'timestamp': self.timestamp,
            'namespace': self.namespace.hex() if self.namespace else ''
        })

    def to_instance(self, instance: 'FactorioInstance'):
        """Restore game state to Factorio instance"""
        instance._load_entity_state(self.entities, decode=True)
        instance.set_inventory(**self.inventory)

        # Merge pickled namespace with existing persistent_vars
        if self.namespace:
            restored_vars = pickle.loads(self.namespace)
            if not hasattr(instance, 'persistent_vars') or instance.persistent_vars is None:
                instance.persistent_vars = {}
            instance.persistent_vars.update(restored_vars)