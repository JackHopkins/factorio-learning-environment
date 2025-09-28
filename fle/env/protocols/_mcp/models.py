from dataclasses import dataclass
from typing import Dict, List, Union


@dataclass
class FactorioServer:
    """Represents a Factorio server instance"""

    address: str
    tcp_port: int
    instance_id: int
    name: str = None
    connected: bool = False
    last_checked: float = 0
    is_active: bool = False
    system_response: str = None


@dataclass
class Recipe:
    """Represents a crafting recipe in Factorio"""

    name: str
    ingredients: List[Dict[str, Union[str, int]]]
    results: List[Dict[str, Union[str, int]]]
    energy_required: float


@dataclass
class ResourcePatch:
    """Represents a resource patch in the Factorio world"""

    name: str
    position: Dict[str, float]
    amount: int
    size: Dict[str, float]
