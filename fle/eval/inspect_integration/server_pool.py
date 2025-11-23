"""Server pool management for Factorio Docker containers."""

import asyncio
import docker
import logging
from typing import Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FactorioServer:
    """Represents a Factorio Docker container server"""

    container_id: str
    port_offset: int
    tcp_port: int
    udp_port: int
    container_name: str
    is_available: bool = True


class FactorioServerPool:
    """Manages pool of existing Docker Factorio servers with intelligent allocation"""

    def __init__(self, max_servers: int = 16, scenario: str = "default_lab_scenario"):
        self.max_servers = max_servers
        self.scenario = scenario
        self.available_servers: asyncio.Queue = asyncio.Queue()
        self.active_servers: Dict[str, FactorioServer] = {}
        self.allocated_servers: Dict[
            str, FactorioServer
        ] = {}  # Track allocated servers
        self.docker_client = None
        self._initialized = False

    async def initialize(self):
        """Initialize the server pool by discovering existing containers"""
        if self._initialized:
            return

        try:
            self.docker_client = docker.from_env()

            # Discover existing Factorio containers from cluster
            await self._discover_existing_containers()

            logger.info(
                f"Initialized FactorioServerPool with {len(self.active_servers)} existing containers"
            )
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise

    async def _discover_existing_containers(self):
        """Discover existing Factorio containers from the cluster"""
        try:
            # Find all running containers with factorio_ prefix
            containers = self.docker_client.containers.list(
                filters={"status": "running", "name": "factorio_"}
            )

            for container in containers:
                # Parse container name to get index (e.g., factorio_0 -> 0)
                container_name = container.name
                if not container_name.startswith("factorio_"):
                    continue

                try:
                    index = int(container_name.split("_")[1])
                    tcp_port = 27000 + index
                    udp_port = 34197 + index

                    server = FactorioServer(
                        container_id=container.id,
                        port_offset=index,
                        tcp_port=tcp_port,
                        udp_port=udp_port,
                        container_name=container_name,
                        is_available=True,
                    )

                    self.active_servers[server.container_id] = server
                    await self.available_servers.put(server)

                    logger.info(
                        f"Discovered container: {container_name} (TCP:{tcp_port}, UDP:{udp_port})"
                    )

                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse container {container_name}: {e}")
                    continue

            if not self.active_servers:
                logger.warning(
                    "No existing Factorio containers found. Use 'fle cluster start' to create them."
                )

        except Exception as e:
            logger.error(f"Error discovering containers: {e}")
            raise

    async def get_server(self) -> FactorioServer:
        """Get available server from existing containers"""
        await self.initialize()

        if not self.active_servers:
            raise RuntimeError(
                "No Factorio containers available. Please start the cluster first with: fle cluster start -n 8"
            )

        # Get an available server from the queue
        if self.available_servers.empty():
            raise RuntimeError(
                f"All {len(self.active_servers)} servers are currently in use. "
                f"Consider reducing --max-connections or starting more containers."
            )

        server = await self.available_servers.get()
        self.allocated_servers[server.container_id] = server
        logger.info(f"Allocated server {server.container_name} (TCP:{server.tcp_port})")
        return server

    async def release_server(self, server: FactorioServer):
        """Return server to pool after cleanup"""
        try:
            # Remove from allocated tracking
            if server.container_id in self.allocated_servers:
                del self.allocated_servers[server.container_id]

            # For now, we'll skip resetting server state to avoid restarts
            # In production, you might want to reset the game state
            # await self._reset_server_state(server)

            # Return to available pool
            await self.available_servers.put(server)
            logger.info(f"Released server {server.container_name} back to pool")

        except Exception as e:
            logger.error(f"Error releasing server {server.container_name}: {e}")
            # Still try to put it back in the pool
            try:
                await self.available_servers.put(server)
            except Exception:
                logger.error(f"Failed to return {server.container_name} to pool")

    def get_allocated_count(self) -> int:
        """Get number of currently allocated servers"""
        return len(self.allocated_servers)

    def get_available_count(self) -> int:
        """Get number of available servers"""
        return self.available_servers.qsize()

    def get_total_count(self) -> int:
        """Get total number of discovered servers"""
        return len(self.active_servers)

    async def _wait_for_server_ready(self, server: FactorioServer):
        """Wait for Factorio server to be ready for connections"""
        # Simple wait - in production might want to check server status
        await asyncio.sleep(5)
        logger.info(f"Server {server.container_name} is ready")

    async def _reset_server_state(self, server: FactorioServer):
        """Reset server state for reuse"""
        try:
            # Restart the container to reset game state
            container = self.docker_client.containers.get(server.container_id)
            container.restart()
            await self._wait_for_server_ready(server)
        except Exception as e:
            logger.error(f"Failed to reset server {server.container_name}: {e}")
            raise

    async def _remove_server(self, server: FactorioServer):
        """Remove server from pool and stop container"""
        try:
            container = self.docker_client.containers.get(server.container_id)
            container.stop()
            container.remove()

            if server.container_id in self.active_servers:
                del self.active_servers[server.container_id]

            logger.info(f"Removed server {server.container_name}")
        except Exception as e:
            logger.error(f"Failed to remove server {server.container_name}: {e}")

    async def cleanup(self):
        """Cleanup all servers in the pool"""
        logger.info("Cleaning up server pool...")

        for server in list(self.active_servers.values()):
            await self._remove_server(server)

        self.active_servers.clear()

        # Clear the queue
        while not self.available_servers.empty():
            try:
                self.available_servers.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("Server pool cleanup complete")


# Global server pool instance
_server_pool: Optional[FactorioServerPool] = None


async def get_server_pool(
    max_servers: int = 16, scenario: str = "default_lab_scenario"
) -> FactorioServerPool:
    """Get or create the global server pool"""
    global _server_pool
    if _server_pool is None:
        _server_pool = FactorioServerPool(max_servers=max_servers, scenario=scenario)
        await _server_pool.initialize()
    return _server_pool


async def cleanup_server_pool():
    """Cleanup the global server pool"""
    global _server_pool
    if _server_pool:
        await _server_pool.cleanup()
        _server_pool = None
