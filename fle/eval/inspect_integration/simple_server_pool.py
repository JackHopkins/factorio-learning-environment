"""Simple server pool that manages run_idx allocation without Docker client."""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SimpleServerPool:
    """Simple server pool that manages run_idx allocation for existing Factorio containers"""

    def __init__(self, max_servers: int = 8):
        self.max_servers = max_servers
        self.available_indices: asyncio.Queue = asyncio.Queue()
        self.allocated_indices: set = set()
        self._initialized = False

    async def initialize(self):
        """Initialize the pool with available run_idx values"""
        if self._initialized:
            return

        # Populate queue with available run_idx values (0, 1, 2, ... max_servers-1)
        for i in range(self.max_servers):
            await self.available_indices.put(i)

        logger.info(
            f"Initialized SimpleServerPool with {self.max_servers} server indices"
        )
        self._initialized = True

    async def get_run_idx(self) -> int:
        """Get an available run_idx for connecting to Factorio server"""
        await self.initialize()

        if self.available_indices.empty():
            raise RuntimeError(
                f"All {self.max_servers} servers are in use. "
                f"Consider reducing --max-connections or starting more containers with 'fle cluster start -n N'"
            )

        run_idx = await self.available_indices.get()
        self.allocated_indices.add(run_idx)

        logger.info(f"Allocated run_idx {run_idx} (server factorio_{run_idx})")
        return run_idx

    async def release_run_idx(self, run_idx: int):
        """Return run_idx to the pool"""
        try:
            if run_idx in self.allocated_indices:
                self.allocated_indices.remove(run_idx)

            await self.available_indices.put(run_idx)
            logger.info(f"Released run_idx {run_idx} back to pool")

        except Exception as e:
            logger.error(f"Error releasing run_idx {run_idx}: {e}")

    def get_allocated_count(self) -> int:
        """Get number of currently allocated servers"""
        return len(self.allocated_indices)

    def get_available_count(self) -> int:
        """Get number of available servers"""
        return self.available_indices.qsize()


# Global server pool instance
_simple_server_pool: Optional[SimpleServerPool] = None


async def get_simple_server_pool(max_servers: int = 32) -> SimpleServerPool:
    """Get or create the global simple server pool"""
    global _simple_server_pool
    if _simple_server_pool is None:
        _simple_server_pool = SimpleServerPool(max_servers=max_servers)
        await _simple_server_pool.initialize()
    return _simple_server_pool
