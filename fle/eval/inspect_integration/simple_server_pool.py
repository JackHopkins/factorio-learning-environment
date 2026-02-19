"""Simple server pool that manages run_idx allocation without Docker client.

Also handles round-robin API key assignment for Anthropic API keys.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ServerAllocation:
    """Result of server allocation including run_idx and API key."""

    run_idx: int
    api_key: Optional[str] = None
    api_key_index: Optional[int] = None


class SimpleServerPool:
    """Simple server pool that manages run_idx allocation for existing Factorio containers.

    Also manages round-robin distribution of Anthropic API keys across allocations.

    Server range can be configured via environment variables:
    - FLE_SERVER_START: Starting server index (default: 0)
    - FLE_SERVER_END: Ending server index exclusive (default: max_servers)

    Example: FLE_SERVER_START=0 FLE_SERVER_END=8 uses servers 0-7
             FLE_SERVER_START=8 FLE_SERVER_END=16 uses servers 8-15
    """

    def __init__(self, max_servers: int = 8, start_idx: int = 0, end_idx: int = None):
        self.start_idx = start_idx
        self.end_idx = end_idx if end_idx is not None else max_servers
        self.max_servers = self.end_idx - self.start_idx
        self.available_indices: asyncio.Queue = asyncio.Queue()
        self.allocated_indices: set = set()
        self._initialized = False

        # API key management
        self._api_keys: List[str] = []
        self._api_key_counter: int = 0
        self._api_key_lock = asyncio.Lock()

    def _load_api_keys(self):
        """Load Anthropic API keys from environment variables.

        Supports:
        - ANTHROPIC_API_KEYS: Comma-separated list of keys (preferred)
        - ANTHROPIC_API_KEY: Single key fallback
        """
        # Try multiple keys first
        keys_str = os.getenv("ANTHROPIC_API_KEYS", "")
        if keys_str:
            self._api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
            logger.info(
                f"Loaded {len(self._api_keys)} Anthropic API keys from ANTHROPIC_API_KEYS"
            )
        else:
            # Fall back to single key
            single_key = os.getenv("ANTHROPIC_API_KEY", "")
            if single_key:
                self._api_keys = [single_key]
                logger.info("Loaded 1 Anthropic API key from ANTHROPIC_API_KEY")
            else:
                logger.warning(
                    "No Anthropic API keys found. Set ANTHROPIC_API_KEYS or ANTHROPIC_API_KEY"
                )

    async def initialize(self):
        """Initialize the pool with available run_idx values"""
        if self._initialized:
            return

        # Load API keys
        self._load_api_keys()

        # Populate queue with available run_idx values in the configured range
        for i in range(self.start_idx, self.end_idx):
            await self.available_indices.put(i)

        logger.info(
            f"Initialized SimpleServerPool with servers {self.start_idx}-{self.end_idx - 1} "
            f"({self.max_servers} total) and {len(self._api_keys)} API keys"
        )
        self._initialized = True

    async def _get_next_api_key(self) -> Tuple[Optional[str], Optional[int]]:
        """Get the next API key using round-robin selection.

        Returns:
            Tuple of (api_key, key_index) or (None, None) if no keys available
        """
        if not self._api_keys:
            return None, None

        async with self._api_key_lock:
            key_index = self._api_key_counter % len(self._api_keys)
            self._api_key_counter += 1
            return self._api_keys[key_index], key_index

    async def get_run_idx(self) -> int:
        """Get an available run_idx for connecting to Factorio server.

        Note: For API key assignment, use get_server_allocation() instead.
        """
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

    async def get_server_allocation(self) -> ServerAllocation:
        """Get a server allocation with run_idx and API key.

        This method:
        1. Allocates an available run_idx
        2. Assigns an API key using round-robin
        3. Sets ANTHROPIC_API_KEY env var for the current process

        Returns:
            ServerAllocation with run_idx and assigned API key
        """
        await self.initialize()

        if self.available_indices.empty():
            raise RuntimeError(
                f"All {self.max_servers} servers are in use. "
                f"Consider reducing --max-connections or starting more containers with 'fle cluster start -n N'"
            )

        run_idx = await self.available_indices.get()
        self.allocated_indices.add(run_idx)

        # Get next API key
        api_key, key_index = await self._get_next_api_key()

        # Set the API key in environment for this allocation
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
            logger.info(
                f"Allocated run_idx {run_idx} with API key index {key_index} "
                f"(key: {api_key[:12]}...{api_key[-4:]})"
            )
        else:
            logger.info(f"Allocated run_idx {run_idx} (no API key assigned)")

        return ServerAllocation(
            run_idx=run_idx, api_key=api_key, api_key_index=key_index
        )

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
    """Get or create the global simple server pool.

    Server range can be configured via environment variables:
    - FLE_SERVER_START: Starting server index (default: 0)
    - FLE_SERVER_END: Ending server index exclusive (default: max_servers)

    Example usage for partitioning 32 servers across 4 solver runs:
        # Terminal 1: servers 0-7
        FLE_SERVER_START=0 FLE_SERVER_END=8 fle inspect-eval --solver unbounded ...

        # Terminal 2: servers 8-15
        FLE_SERVER_START=8 FLE_SERVER_END=16 fle inspect-eval --solver reasoning_only ...

        # Terminal 3: servers 16-23
        FLE_SERVER_START=16 FLE_SERVER_END=24 fle inspect-eval --solver text_only ...

        # Terminal 4: servers 24-31
        FLE_SERVER_START=24 FLE_SERVER_END=32 fle inspect-eval --solver hud ...
    """
    global _simple_server_pool
    if _simple_server_pool is None:
        # Check for server range environment variables
        start_idx = int(os.getenv("FLE_SERVER_START", "0"))
        end_idx = int(os.getenv("FLE_SERVER_END", str(max_servers)))

        _simple_server_pool = SimpleServerPool(
            max_servers=max_servers, start_idx=start_idx, end_idx=end_idx
        )
        await _simple_server_pool.initialize()
    return _simple_server_pool
