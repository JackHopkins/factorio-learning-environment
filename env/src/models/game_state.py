import json
import pickle
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Optional, Any


from models.research_state import ResearchState
from models.technology_state import TechnologyState

@dataclass
class GameState:
    """Serializable Factorio game state"""
    entities: str # Serialized list of entities
    inventory: Dict[str, int]
    research: Optional[ResearchState] = field()
    timestamp: float = field(default_factory=time.time)
    namespace: bytes = field(default_factory=bytes)

    @property
    def is_multiagent(self) -> bool:
        return False
    
    @property
    def num_agents(self) -> int:
        return 1

    @classmethod
    def from_instance(cls, instance: 'FactorioInstance') -> 'GameState':

        """Capture current game state from Factorio instance"""
        entities = instance.namespace._save_entity_state(compress=True, encode=True)

        # Get research state
        research_state = instance.namespace._save_research_state()

        # Filter and pickle only serializable variables
        if hasattr(instance.namespace, 'persistent_vars'):
            serializable_vars = filter_serializable_vars(instance.namespace.persistent_vars)
            namespace = pickle.dumps(serializable_vars)
        else:
            namespace = bytes()

        return cls(
            entities=entities,
            inventory=instance.namespace.inspect_inventory(),
            namespace=namespace,
            research=research_state,
        )

    def __repr__(self):
        readable_namespace=pickle.loads(self.namespace)
        return f"GameState(entities={self.entities}, inventory={self.inventory}, timestamp={self.timestamp}, namespace={{{readable_namespace}}})"

    @classmethod
    def parse_raw(cls, json_str: str) -> 'GameState':
        data = json.loads(json_str)
        namespace = bytes.fromhex(data['namespace']) if 'namespace' in data else bytes()
        # Parse research state if present
        research = None
        if 'research' in data:
            research = ResearchState(
                technologies={
                    name: TechnologyState(**tech)
                    for name, tech in data['research']['technologies'].items()
                },
                current_research=data['research']['current_research'],
                research_progress=data['research']['research_progress'],
                research_queue=data['research']['research_queue'],
                progress=data['research']['progress'] if 'progress' in data['research'] else {}
            )

        return cls(
            entities=data['entities'],
            inventory=data['inventory'],
            timestamp=data['timestamp'] if 'timestamp' in data else time.time(),
            namespace=namespace,
            research=research
        )

    @classmethod
    def parse(cls, data) -> 'GameState':
        namespace = bytes.fromhex(data['namespace']) if 'namespace' in data else bytes()

        # Parse research state if present
        research = None
        if 'research' in data:
            research = ResearchState(
                technologies={
                    name: TechnologyState(**tech)
                    for name, tech in data['research']['technologies'].items()
                },
                current_research=data['research']['current_research'],
                research_progress=data['research']['research_progress'],
                research_queue=data['research']['research_queue'],
                progress=data['research']['progress'] if 'progress' in data['research'] else {}
            )

        return cls(
            entities=data['entities'],
            inventory=data['inventory'],
            timestamp=data['timestamp'] if 'timestamp' in data else time.time(),
            namespace=namespace,
            research=research
        )

    def to_raw(self) -> str:
        """Convert state to JSON string"""
        data = {
            'entities': self.entities,
            'inventory': self.inventory.__dict__ if hasattr(self.inventory, '__dict__') else self.inventory,
            'timestamp': self.timestamp,
            'namespace': self.namespace.hex() if self.namespace else ''
        }

        # Add research state if present
        if self.research:
            data['research'] = {
                'technologies': {
                    name: asdict(tech)
                    for name, tech in self.research.technologies.items()
                },
                'current_research': self.research.current_research,
                'research_progress': self.research.research_progress,
                'research_queue': self.research.research_queue,
                'progress': self.research.progress
            }

        return json.dumps(data)

    # def to_raw(self) -> str:
    #     """Convert state to JSON string"""
    #     return json.dumps({
    #         'entities': self.entities,
    #         'inventory': self.inventory.__dict__ if hasattr(self.inventory, '__dict__') else self.inventory,
    #         'timestamp': self.timestamp,
    #         'namespace': self.namespace.hex() if self.namespace else ''
    #     })

#    @deprecated(reason="we don't use this anymore.")
    def to_instance(self, instance: 'FactorioInstance'):
        """Restore game state to Factorio instance"""
        instance.namespace._load_entity_state(self.entities, decode=True)
        instance.set_inventory(self.inventory)

        # Restore research state if present
        if self.research:
            instance.namespace._load_research_state(self.research)

        # Merge pickled namespace with existing persistent_vars
        if self.namespace:
            restored_vars = pickle.loads(self.namespace)
            if not hasattr(instance, 'persistent_vars') or instance.persistent_vars is None:
                instance.persistent_vars = {}
            instance.persistent_vars.update(restored_vars)

def filter_serializable_vars(vars_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Filter dictionary to only include serializable items"""
    return {
        key: value for key, value in vars_dict.items()
        if is_serializable(value)
    }


def is_serializable(obj: Any) -> bool:
    """Test if an object can be serialized with pickle"""
    try:
        if obj == True or obj == False:
            return True


        # Skip type objects
        if isinstance(obj, type):
            return False

        # Skip builtin types
        if obj.__module__ == 'builtins':
            return False

        if isinstance(obj, Enum):
            return True

        if isinstance(obj, (list, dict)):
            return all(is_serializable(item) for item in obj)

        # Common built-in types that are always serializable
        if isinstance(obj, (int, float, str, bool, list, dict, tuple, set)):
            return True


        pickle.dumps(obj)
        return True
    except (pickle.PicklingError, TypeError, AttributeError) as e:
        v = obj
        return False
