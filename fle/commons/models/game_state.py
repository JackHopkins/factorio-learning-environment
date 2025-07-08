import json
import pickle
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from fle.commons.models.research_state import ResearchState
from fle.commons.models.technology_state import TechnologyState


@dataclass
class GameState:
    """Serializable Factorio game state"""

    entities: str  # Serialized list of entities
    inventories: List[Dict[str, int]]  # List of inventories for all players
    research: Optional[ResearchState] = field()
    timestamp: float = field(default_factory=time.time)
    namespaces: List[bytes] = field(default_factory=list)
    agent_messages: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_multiagent(self) -> bool:
        return len(self.inventories) > 1

    @property
    def num_agents(self) -> int:
        return len(self.inventories)

    def parse_agent_messages(data: dict) -> List[Dict[str, Any]]:
        agent_messages = data.get("agent_messages", [])
        if not isinstance(agent_messages, list):
            raise ValueError("agent_messages must be a list")
        if agent_messages and not all(isinstance(msg, dict) for msg in agent_messages):
            for idx, message in enumerate(agent_messages):
                if isinstance(message, dict):
                    continue
                elif isinstance(message, list):
                    if len(message) > 0:
                        if isinstance(message[0], dict):
                            agent_messages[idx] = message[0]
                        else:
                            raise ValueError(
                                f"agent_messages[{idx}] must be a dictionary or a list of dictionaries, but got {type(message[0])}"
                            )
                    else:
                        agent_messages[idx] = {}
                else:
                    raise ValueError(
                        f"agent_messages[{idx}] must be a dictionary or a list of dictionaries, but got {type(message)}"
                    )
        return agent_messages

    @classmethod
    def from_instance(cls, instance) -> "GameState":
        """Capture current game state from Factorio instances"""
        entities = instance.first_namespace._save_entity_state(
            compress=True, encode=True
        )

        # Get research state
        research_state = instance.first_namespace._save_research_state()

        # Filter and pickle only serializable variables
        namespaces = []
        for namespace in instance.namespaces:
            if hasattr(namespace, "persistent_vars"):
                serializable_vars = filter_serializable_vars(namespace.persistent_vars)
                namespaces.append(pickle.dumps(serializable_vars))
            else:
                namespaces.append(bytes())

        # Get inventories for all players
        inventories = [
            namespace.inspect_inventory() for namespace in instance.namespaces
        ]
        agent_messages = [namespace.get_messages() for namespace in instance.namespaces]

        return cls(
            entities=entities,
            inventories=inventories,
            namespaces=namespaces,
            research=research_state,
            agent_messages=agent_messages,
        )

    def __repr__(self):
        readable_namespaces = [pickle.loads(namespace) for namespace in self.namespaces]
        return f"GameState(entities={self.entities}, inventories={self.inventories}, timestamp={self.timestamp}, namespace={{{readable_namespaces}}}, agent_messages={self.agent_messages})"

    @classmethod
    def parse_raw(cls, json_str: str) -> "GameState":
        data = json.loads(json_str)
        namespaces = []
        if "namespaces" in data:
            namespaces = [
                bytes.fromhex(ns) if ns else bytes() for ns in data["namespaces"]
            ]

        # Parse research state if present
        research = None
        if "research" in data:
            research = ResearchState(
                technologies={
                    name: TechnologyState(**tech)
                    for name, tech in data["research"]["technologies"].items()
                },
                current_research=data["research"]["current_research"],
                research_progress=data["research"]["research_progress"],
                research_queue=data["research"]["research_queue"],
                progress=data["research"]["progress"]
                if "progress" in data["research"]
                else {},
            )

        return cls(
            entities=data["entities"],
            inventories=data["inventories"],
            timestamp=data["timestamp"] if "timestamp" in data else time.time(),
            namespaces=namespaces,
            research=research,
            agent_messages=cls.parse_agent_messages(data),
        )

    @classmethod
    def parse(cls, data) -> "GameState":
        if "namespace" in data:
            data["namespaces"] = [data["namespace"]]
            data["inventories"] = [data["inventory"]]
            data["agent_messages"] = []

        namespaces = []
        if "namespaces" in data:
            namespaces = [
                bytes.fromhex(ns) if ns else bytes() for ns in data["namespaces"]
            ]

        # Parse research state if present
        research = None
        if "research" in data:
            research = ResearchState(
                technologies={
                    name: TechnologyState(**tech)
                    for name, tech in data["research"]["technologies"].items()
                },
                current_research=data["research"]["current_research"],
                research_progress=data["research"]["research_progress"],
                research_queue=data["research"]["research_queue"],
                progress=data["research"]["progress"]
                if "progress" in data["research"]
                else {},
            )

        return cls(
            entities=data["entities"],
            inventories=data["inventories"],
            timestamp=data["timestamp"] if "timestamp" in data else time.time(),
            namespaces=namespaces,
            research=research,
            agent_messages=cls.parse_agent_messages(data),
        )

    def to_raw(self) -> str:
        """Convert state to JSON string"""
        data = {
            "entities": self.entities,
            "inventories": [inventory.__dict__ for inventory in self.inventories],
            "timestamp": self.timestamp,
            "namespaces": [ns.hex() if ns else "" for ns in self.namespaces],
            "agent_messages": self.agent_messages,
        }

        # Add research state if present
        if self.research:
            data["research"] = {
                "technologies": {
                    name: asdict(tech)
                    for name, tech in self.research.technologies.items()
                },
                "current_research": self.research.current_research,
                "research_progress": self.research.research_progress,
                "research_queue": self.research.research_queue,
                "progress": self.research.progress,
            }

        return json.dumps(data)

    def to_instance(self, instance):
        """Restore game state to a Factorio instance"""
        # Load entity state to all instances (since it's shared)
        assert instance.num_agents == self.num_agents, (
            f"GameState can only be restored to a multiagent instance with the same number of agents (num_agents={self.num_agents})"
        )
        instance.first_namespace._load_entity_state(self.entities, decompress=True)

        # Set inventory for each player
        if self.inventories:
            for i in range(instance.num_agents):
                instance.set_inventory(self.inventories[i], i)

        # Restore research state if present (only need to do this once)
        if self.research:  # Only do this for the first instance
            instance.first_namespace._load_research_state(self.research)

        # Load messages for each player
        if self.agent_messages:
            for i in range(instance.num_agents):
                if i < len(self.agent_messages):
                    instance.namespaces[i].load_messages(self.agent_messages[i])

        # Merge pickled namespace with existing persistent_vars for each player
        if self.namespaces:
            for i in range(instance.num_agents):
                namespace = self.namespaces[i]
                if namespace:
                    restored_vars = pickle.loads(namespace)
                if (
                    not hasattr(instance, "persistent_vars")
                    or instance.persistent_vars is None
                ):
                    instance.persistent_vars = {}
                instance.persistent_vars.update(restored_vars)


def filter_serializable_vars(vars_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Filter dictionary to only include serializable items"""
    return {key: value for key, value in vars_dict.items() if is_serializable(value)}


def is_serializable(obj: Any) -> bool:
    """Test if an object can be serialized with pickle"""
    try:
        if obj == True or obj == False:  # noqa
            return True

        # Skip type objects
        if isinstance(obj, type):
            return False

        # Skip builtin types
        if obj.__module__ == "builtins":
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
    except (pickle.PicklingError, TypeError, AttributeError):
        return False
