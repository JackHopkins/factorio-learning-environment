from typing import Any, Dict, Type

from datasetgen.mcts.game_state import GameState
from datasetgen.mcts.mcts import MCTS
from datasetgen.mcts.samplers.db_sampler import DBSampler
from datasetgen.mcts.samplers.dynamic_reward_weighted_sampler import DynamicRewardWeightedSampler


class ParallelMCTSConfig:
    """Configuration for ParallelMCTS"""
    def __init__(self,
                 n_parallel: int,
                 system_prompt: str,
                 initial_state: GameState,
                 mcts_class: Type[MCTS],
                 sampler: DBSampler,
                 mcts_kwargs: Dict[str, Any] = None,
                 **kwargs):
        self.n_parallel = n_parallel
        self.system_prompt = system_prompt
        self.initial_state = initial_state
        self.mcts_class = mcts_class
        self.sampler = sampler
        self.mcts_kwargs = mcts_kwargs or {}

        for key, value in kwargs.items():
            setattr(self, key, value)
