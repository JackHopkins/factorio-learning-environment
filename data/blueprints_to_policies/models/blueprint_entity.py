from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class BlueprintEntity:
    entity_number: int
    name: str
    position: Dict[str, float]
    direction: int = 0
    items: Dict[str, int] = None
    type: str = None
    neighbours: List[int] = None
    input_priority: str = None
    recipe: Optional[str] = None
    output_priority: str = None
    control_behavior: Dict = None
    connections: Dict = None
    filter: Dict = None
