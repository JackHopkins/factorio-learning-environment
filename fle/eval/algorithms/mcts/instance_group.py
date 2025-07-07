from dataclasses import dataclass
from typing import List

from fle.eval.evaluator import Evaluator
from fle.eval.algorithms.mcts.mcts import MCTS
from fle.env.instance import FactorioInstance


@dataclass
class InstanceGroup:
    """Represents a group of instances for parallel MCTS execution"""

    group_id: int
    mcts: MCTS
    evaluator: Evaluator
    active_instances: List["FactorioInstance"]
    # holdout_instance: 'FactorioInstance'

    @property
    def total_instances(self) -> int:
        return len(self.active_instances) + 1  # Including holdout
