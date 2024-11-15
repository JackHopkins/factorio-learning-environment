from dataclasses import dataclass
from typing import Optional

import numpy as np

from datasetgen.mcts.conversation import Conversation
from datasetgen.mcts.game_state import GameState


@dataclass
class Program:
    code: str
    conversation: Conversation
    value: float = 0.0
    visits: int = 0
    parent: Optional['Program'] = None
    state: Optional[GameState] = None

    def get_uct(self, parent_visits: int, exploration_constant: float = 1.41) -> float:
        if self.visits == 0:
            return float('inf')
        return (self.value / self.visits) + exploration_constant * np.sqrt(
            np.log(parent_visits) / self.visits
        )