from dataclasses import dataclass
from typing import Dict, List


@dataclass
class TechnologyState:
    """Represents the state of a technology"""

    name: str
    researched: bool
    enabled: bool
    level: int
    research_unit_count: int
    research_unit_energy: float
    prerequisites: List[str]
    ingredients: List[Dict[str, int]]
