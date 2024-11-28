from abc import ABC, abstractmethod
from typing import List

import numpy as np

from datasetgen.mcts.diversity.trace import Trace


class TraceEncoder(ABC):
    @abstractmethod
    def encode_traces(self, traces: List[Trace]) -> np.ndarray:
        """Convert traces to feature vectors for clustering"""
        pass