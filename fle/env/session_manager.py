from typing import Dict, List, Optional

from fle.env.a2a_instance import A2AFactorioInstance
from fle.env.game.config import GameConfig
from fle.env.game.factorio_client import FactorioClient
from fle.env.game.instance import FactorioInstance
from fle.env.session import AgentSession, GameSession
from fle.services.docker.config import DockerConfig
from fle.services.docker.docker_manager import FactorioHeadlessClusterManager


class GameSessionManager:
    """A manager class for creating and managing Factorio game sessions and headless servers.

    This class is responsible for:
    1. Managing the lifecycle of Docker-backed headless server clusters
    2. Creating FactorioClient endpoints for specific instance IDs
    3. Instantiating FactorioInstance or A2AFactorioInstance objects bound to clients
    4. Providing hooks for restarting sessions from saved game states

    Attributes:
        game_config (GameConfig): Configuration for the Factorio game instance
        docker_config (DockerConfig): Configuration for Docker containers
        server_manager (FactorioHeadlessClusterManager): Manager for headless Factorio servers
        sessions (Dict[int, GameSession]): Dictionary mapping instance IDs to GameSession objects
    """

    game_config: GameConfig
    docker_config: DockerConfig
    server_manager: FactorioHeadlessClusterManager
    sessions: Dict[int, GameSession]

    def __init__(
        self,
        game_config: GameConfig,
        docker_config: DockerConfig,
        server_manager: FactorioHeadlessClusterManager,
    ):
        self.game_config = game_config
        self.docker_config = docker_config
        self.server_manager = server_manager

    @property
    def multiagent(self) -> bool:
        return self.game_config.num_agents > 1
    
    def get_agent_sessions(self, instance_id: int) -> Dict[int, AgentSession]:
        return self.sessions[instance_id].agent_sessions
    
    def get_agent_session(self, instance_id: int, agent_idx: int) -> AgentSession:
        return self.sessions[instance_id].agent_sessions[agent_idx]
    
    def _make_client(self, instance_id: int) -> FactorioClient:
        server = self.server_manager.servers[instance_id]
        return FactorioClient(
            instance_id=instance_id,
            rcon_port=server.rcon_port,
            address=server.address,
            rcon_password=server.rcon_password,
            cache_scripts=True,
        )

    def _make_instance(
        self, instance_id: int
    ) -> FactorioInstance | A2AFactorioInstance:
        client = self._make_client(instance_id)
        if self.multiagent:
            return A2AFactorioInstance(
                client=client,
                fast=self.game_config.fast_mode,
            )
        else:
            return FactorioInstance(
                client=client,
                fast=self.game_config.fast_mode,
            )

    def _make_session(self, instance_id: int) -> GameSession:
        instance = self._make_instance(instance_id)
        return GameSession(
            instance_id=instance_id,
            instance=instance,
            server=self.server_manager.servers[instance_id],
        )

    async def start_cluster(self) -> None:
        await self.server_manager.start()

    async def stop_cluster(self) -> None:
        await self.server_manager.stop()

    async def restart_cluster(self) -> None:
        await self.server_manager.restart()

    async def restart_session_with_save(
        self, session: GameSession, save_name: str
    ) -> None:
        await session.restart_with_save(save_name)
