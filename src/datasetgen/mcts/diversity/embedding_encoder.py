from typing import List

import numpy as np

from datasetgen.mcts.diversity.trace import Trace
from datasetgen.mcts.diversity.trace_encoder import TraceEncoder


class EmbeddingEncoder(TraceEncoder):
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model

    def encode_traces(self, traces: List[Trace]) -> np.ndarray:
        # Convert traces to embeddings using the provided model
        return self.embedding_model.encode([trace.text for trace in traces])