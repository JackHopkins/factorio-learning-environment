import logging
from typing import List

import numpy as np
import torch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel

from datasetgen.mcts.diversity.trace import Trace
from datasetgen.mcts.diversity.encoder.trace_encoder import TraceEncoder

logger = logging.getLogger(__name__)

class EmbeddingEncoder(TraceEncoder):
    def __init__(self, model_name="microsoft/codebert-base"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        self.model.eval()

    def _get_embedding(self, code: str, max_length: int = 512) -> np.ndarray:
        """Get embeddings for a single code snippet."""
        with torch.no_grad():
            inputs = self.tokenizer(code,
                                    truncation=True,
                                    max_length=max_length,
                                    return_tensors="pt").to(self.device)
            outputs = self.model(**inputs)
            return outputs.last_hidden_state[:, 0, :].cpu().numpy()

    def encode_traces(self, traces: List[Trace]) -> np.ndarray:
        """Encode all traces to embeddings."""
        embeddings = []
        batch_size = 32  # Process in batches to avoid memory issues
        logger.debug(f"Encoding {len(traces)} traces with batch size {batch_size}")

        # Calculate total number of batches for progress bar
        n_batches = (len(traces) + batch_size - 1) // batch_size

        with tqdm(total=len(traces), desc="Encoding traces") as pbar:
            for i in range(0, len(traces), batch_size):
                batch_traces = traces[i:i + batch_size]
                batch_embeddings = [self._get_embedding(trace.text) for trace in batch_traces]
                embeddings.extend(batch_embeddings)
                pbar.update(len(batch_traces))

        # Stack all embeddings into a single numpy array
        # Each embedding is shape (1, hidden_size), so we need to squeeze out the extra dimension
        return np.vstack([emb.squeeze(0) for emb in embeddings])
