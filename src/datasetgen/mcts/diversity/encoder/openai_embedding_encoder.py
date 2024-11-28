import asyncio
import logging
from typing import List, Dict, Any

import numpy as np
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm_asyncio

from datasetgen.mcts.diversity.trace import Trace
from datasetgen.mcts.diversity.encoder.trace_encoder import TraceEncoder

logger = logging.getLogger(__name__)


class OpenAIEmbeddingEncoder(TraceEncoder):
    def __init__(self,
                 model: str = "text-embedding-3-small",
                 batch_size: int = 32,
                 max_parallel_requests: int = 5):
        """
        Args:
            model: OpenAI embedding model to use
            batch_size: Number of texts to batch in single API call
            max_parallel_requests: Maximum number of concurrent API requests
        """
        self.client = AsyncOpenAI()
        self.model = model
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(max_parallel_requests)

    async def _get_batch_embedding(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a batch of texts using rate limiting."""
        async with self.semaphore:
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )
                return [data.embedding for data in response.data]
            except Exception as e:
                logger.error(f"Error getting embeddings: {e}")
                # Return zero embeddings as fallback
                return [[0.0] * 1536] * len(texts)  # 1536 is dimension for text-embedding-3-small

    async def _process_all_batches(self, traces: List[Trace]) -> np.ndarray:
        """Process all traces in parallel batches."""
        embeddings = []

        # Create batches
        batches = [
            traces[i:i + self.batch_size]
            for i in range(0, len(traces), self.batch_size)
        ]

        async for batch_embeddings in tqdm_asyncio(
                [self._get_batch_embedding([t.text for t in batch]) for batch in batches],
                total=len(batches),
                desc="Getting embeddings"
        ):
            embeddings.extend(batch_embeddings)

        return np.array(embeddings)

    def encode_traces(self, traces: List[Trace]) -> np.ndarray:
        """Encode all traces to embeddings using parallel processing."""
        logger.debug(f"Encoding {len(traces)} traces with batch size {self.batch_size}")

        # Run async processing in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        embeddings = loop.run_until_complete(self._process_all_batches(traces))

        return embeddings