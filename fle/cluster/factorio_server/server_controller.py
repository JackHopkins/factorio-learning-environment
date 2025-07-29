

import asyncio
from typing import Protocol, Literal

from .run_envs import FactorioClusterManager, PlatformConfig, Mode


class ServerController(Protocol):
    """
    Protocol defining the interface for managing a Factorio server instance.
    """
    mode: Literal["scenario", "save-based"]

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def restart(self) -> None:
        ...

    def hot_reload(self) -> None:
        ...


class DockerServerController:
    """
    Concrete ServerController wrapping the Docker-based FactorioClusterManager.
    """
    def __init__(
        self,
        docker_platform: str,
        config: PlatformConfig,
        num_instances: int,
        dry_run: bool = False,
    ):
        # Mirror the mode so consumers can branch behavior
        self.mode = config.mode
        # Underlying cluster manager handles actual Docker orchestration
        self._mgr = FactorioClusterManager(docker_platform, config, num_instances, dry_run)

    def start(self) -> None:
        """Ensure image is available and launch all Factorio containers."""
        asyncio.run(self._mgr.start())

    def stop(self) -> None:
        """Gracefully stop and remove all Factorio containers."""
        asyncio.run(self._mgr.stop())

    def restart(self) -> None:
        """Restart all running Factorio containers."""
        asyncio.run(self._mgr.restart())

    def hot_reload(self) -> None:
        """
        Sync scenario files into running containers for a hot-reload.
        Only available in "scenario" mode.
        """
        if self.mode != Mode.SCENARIO.value:
            raise RuntimeError("Hot-reload only supported in scenario mode")
        asyncio.run(self._mgr.hot_reload_scenario())