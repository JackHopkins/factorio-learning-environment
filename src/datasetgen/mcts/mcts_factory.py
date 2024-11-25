from abc import ABC, abstractmethod

from datasetgen.mcts.factorio_evaluator import FactorioEvaluator
from datasetgen.mcts.mcts import MCTS


class MCTSFactory(ABC):
    """Abstract factory for creating MCTS instances"""

    @abstractmethod
    def create_mcts(self,
                    group_id: int,
                    evaluator: FactorioEvaluator,
                    **kwargs) -> MCTS:
        """Create and configure an MCTS instance"""
        pass
