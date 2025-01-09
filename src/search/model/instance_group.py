from dataclasses import dataclass
from typing import List

from search.mcts.factorio_evaluator import FactorioEvaluator
from search.mcts.mcts import MCTS


@dataclass
class InstanceGroup:
    """Represents a group of instances for parallel MCTS execution"""
    group_id: int
    mcts: MCTS
    evaluator: FactorioEvaluator
    active_instances: List['FactorioInstance']
    #holdout_instance: 'FactorioInstance'

    @property
    def total_instances(self) -> int:
        return len(self.active_instances) + 1  # Including holdout