from dataclasses import dataclass
from typing import List, Optional

from fle.agents.gym_agent import GymAgent
from fle.env.gym_env.observation_formatter import BasicObservationFormatter
from fle.eval.tasks import TaskABC
from a2a.types import AgentCard


@dataclass
class GymRunConfig:
    """Configuration for a single gym environment evaluation run"""

    env_id: str  # Gym environment ID from registry (e.g., "Factorio-iron_ore_throughput_16-v0")
    model: str
    version: Optional[int] = None
    observation_formatter: Optional[BasicObservationFormatter] = None


@dataclass
class GymEvalConfig:
    """Configuration for gym evaluation"""

    agents: List[GymAgent]
    version: int
    version_description: str
    task: Optional[TaskABC] = None
    agent_cards: Optional[List[AgentCard]] = None
    env_id: Optional[str] = None  # Gym environment ID for registry-based creation
    instance_id: Optional[int] = None  # Which container to use for this evaluation

    def __post_init__(self):
        if self.task is None and hasattr(self.agents[0], "task"):
            self.task = self.agents[0].task
