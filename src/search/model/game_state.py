import builtins
import json
import marshal
import pickle
import time
import types
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from models.research_state import ResearchState
from models.technology_state import TechnologyState


class SerializableFunction:
    """Wrapper to make function objects serializable and callable"""

    def __init__(self, func, instance=None):
        self.code_bytes = marshal.dumps(func.__code__)
        self.name = func.__name__
        self.defaults = func.__defaults__
        self.closure = None
        # These won't be pickled
        self._instance = instance
        self._cached_func = None

    def __getstate__(self):
        """Control which attributes are pickled"""
        return {
            'code_bytes': self.code_bytes,
            'name': self.name,
            'defaults': self.defaults,
            'closure': self.closure
        }

    def __setstate__(self, state):
        """Restore state after unpickling"""
        self.code_bytes = state['code_bytes']
        self.name = state['name']
        self.defaults = state['defaults']
        self.closure = state['closure']
        self._instance = None
        self._cached_func = None

    def bind(self, instance):
        """Bind this function to an instance after unpickling"""
        self._instance = instance
        self._cached_func = None
        return self

    def __call__(self, *args, **kwargs):
        """Make the serialized function directly callable"""
        if self._cached_func is None:
            if self._instance is None:
                raise RuntimeError("Function must be bound to an instance before calling")
            self._cached_func = self.reconstruct(self._instance, self)
        return self._cached_func(*args, **kwargs)

    @staticmethod
    def reconstruct(instance, func_data):
        """Reconstruct a function with proper globals from the instance"""
        globals_dict = {}
        # Add instance attributes
        for name in dir(instance):
            if not name.startswith('_'):
                globals_dict[name] = getattr(instance, name)
        # Add builtins
        for name in dir(builtins):
            if not name.startswith('_'):
                globals_dict[name] = getattr(builtins, name)

        code = marshal.loads(func_data.code_bytes)

        new_func = types.FunctionType(
            code,
            globals_dict,
            func_data.name,
            func_data.defaults,
            func_data.closure
        )
        return new_func

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

def wrap_for_serialization(value):
    """Wrap values that need special serialization handling"""
    if isinstance(value, types.FunctionType):
        # Skip builtin functions
        if value.__module__ == 'builtins':
            return value

        return SerializableFunction(value)
    return value

def unwrap_after_deserialization(instance, value):
    """Unwrap serialized values back to their original form"""
    if isinstance(value, SerializableFunction):
        return value.bind(instance)
    return value

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
    research: Optional[ResearchState] = field()
    timestamp: float = field(default_factory=time.time)
    namespace: bytes = field(default_factory=bytes)

    @classmethod
    def from_instance(cls, instance: 'FactorioInstance') -> 'GameState':

        """Capture current game state from Factorio instance"""
        entities = instance._save_entity_state(compress=True, encode=True)

        # Get research state
        research_state = instance._save_research_state()

        # Filter and pickle only serializable variables
        if hasattr(instance, 'persistent_vars'):
            serializable_vars = filter_serializable_vars(instance.persistent_vars)
            namespace = pickle.dumps(serializable_vars)
        else:
            namespace = bytes()

        return cls(
            entities=entities,
            inventory=instance.inspect_inventory(),
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
                research_queue=data['research']['research_queue']
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
                research_queue=data['research']['research_queue']
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
                'research_queue': self.research.research_queue
            }

        return json.dumps(data)

    def to_raw(self) -> str:
        """Convert state to JSON string"""
        return json.dumps({
            'entities': self.entities,
            'inventory': self.inventory.__dict__ if hasattr(self.inventory, '__dict__') else self.inventory,
            'timestamp': self.timestamp,
            'namespace': self.namespace.hex() if self.namespace else ''
        })

    def to_instance(self, instance: 'FactorioInstance'):
        """Restore game state to Factorio instance"""
        instance._load_entity_state(self.entities, decode=True)
        instance.set_inventory(**self.inventory)

        # Restore research state if present
        if self.research:
            instance._load_research_state(self.research)

        # Merge pickled namespace with existing persistent_vars
        if self.namespace:
            restored_vars = pickle.loads(self.namespace)
            if not hasattr(instance, 'persistent_vars') or instance.persistent_vars is None:
                instance.persistent_vars = {}
            instance.persistent_vars.update(restored_vars)