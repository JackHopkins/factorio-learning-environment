from typing import List

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer

from datasetgen.mcts.diversity.trace import Trace
from datasetgen.mcts.diversity.trace_encoder import TraceEncoder
from tiktoken import get_encoding

class NGramEncoder(TraceEncoder):
    def __init__(self, tokenizer_name: str = "cl100k_base"):
        self.tokenizer = get_encoding(tokenizer_name)

    def encode_traces(self, traces: List[Trace]) -> np.ndarray:
        vectorizer = CountVectorizer(
            tokenizer=lambda x: [str(token) for token in self.tokenizer.encode(x)],
            ngram_range=(1, 3)
        )
        return vectorizer.fit_transform([trace.text for trace in traces])