import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import gym

from fle.env.session_manager import GameSessionManager
from fle.env.session import GameSession
from fle.env.game.config import GameConfig
from fle.services.docker.config import DockerConfig

from fle.env.environment import FactorioGymEnv
from fle.env.tasks import TaskFactory
from fle.services.docker.docker_manager import FactorioHeadlessClusterManager


@dataclass
class GymEnvironmentSpec:
    """Specification for a registered gym environment"""

    env_id: str
    task_key: str
    task_config_path: str
    description: str
    num_agents: int = 1
    model: str = "gpt-4"
    version: Optional[int] = None
    exit_on_task_success: bool = True
    # Configs are populated by the registry defaults unless explicitly provided
    game_config: Optional[GameConfig] = None
    docker_config: Optional[DockerConfig] = None

class FactorioGymRegistry:
    """Registry for Factorio gym environments"""

    def __init__(self):
        self._environments: Dict[str, GymEnvironmentSpec] = {}
        # Use the same path construction as TaskFactory for consistency
        from fle.env.tasks.task_factory import TASK_FOLDER

        self._task_definitions_path = TASK_FOLDER
        self._discovered = False
        # Defaults that can be overridden by callers (e.g., run_eval)
        self._default_game_config: GameConfig = GameConfig()
        self._default_docker_config: DockerConfig = DockerConfig()

    def set_defaults(
        self,
        game_config: Optional[GameConfig] = None,
        docker_config: Optional[DockerConfig] = None,
    ) -> None:
        if game_config is not None:
            self._default_game_config = game_config
        if docker_config is not None:
            self._default_docker_config = docker_config
        # Apply to already-registered specs that didn't customize
        for spec in self._environments.values():
            if spec.game_config is None:
                spec.game_config = self._default_game_config
            if spec.docker_config is None:
                spec.docker_config = self._default_docker_config

    def discover_tasks(self) -> None:
        """Automatically discover all task definitions and register them as gym environments"""
        if self._discovered:
            return

        if not self._task_definitions_path.exists():
            raise FileNotFoundError(
                f"Task definitions path not found: {self._task_definitions_path}"
            )

        # Discover all JSON task definition files
        for task_file in self._task_definitions_path.rglob("*.json"):
            try:
                with open(task_file, "r") as f:
                    task_data = json.load(f)

                task_key = task_data.get("config", {}).get("task_key", task_file.stem)
                task_type = task_data.get("task_type", "default")
                goal_description = task_data.get("config", {}).get(
                    "goal_description", f"Task: {task_key}"
                )
                # Register the environment
                self.register_environment(
                    env_id=task_key,
                    task_key=task_key,
                    task_config_path=str(task_file),
                    description=goal_description,
                    task_type=task_type,
                )

            except Exception as e:
                print(f"Warning: Failed to load task definition {task_file}: {e}")

        self._discovered = True

    def register_environment(
        self,
        env_id: str,
        task_key: str,
        task_config_path: str,
        description: str,
        task_type: str = "default",
        num_agents: int = 1,
        model: str = "gpt-4",
        version: Optional[int] = None,
        exit_on_task_success: bool = True,
        game_config: Optional[GameConfig] = None,
        docker_config: Optional[DockerConfig] = None,
    ) -> None:
        """Register a new gym environment"""

        spec = GymEnvironmentSpec(
            env_id=env_id,
            task_key=task_key,
            task_config_path=task_config_path,
            description=description,
            num_agents=num_agents,
            model=model,
            version=version,
            exit_on_task_success=exit_on_task_success,
            game_config=game_config or self._default_game_config,
            docker_config=docker_config or self._default_docker_config,
        )

        self._environments[env_id] = spec

        # Register with gym
        gym.register(
            id=env_id,
            entry_point="fle.env.registry:make_factorio_env",
            kwargs={"env_spec": spec},
        )

    def list_environments(self) -> List[str]:
        """List all registered environment IDs"""
        self.discover_tasks()
        return list(self._environments.keys())

    def get_environment_spec(self, env_id: str) -> Optional[GymEnvironmentSpec]:
        """Get the specification for a registered environment"""
        self.discover_tasks()
        return self._environments.get(env_id)

    def get_all_specs(self) -> Dict[str, GymEnvironmentSpec]:
        """Get all environment specifications"""
        self.discover_tasks()
        return self._environments.copy()


# Global registry instance
_registry = FactorioGymRegistry()


def make_factorio_env(env_spec: GymEnvironmentSpec) -> FactorioGymEnv:
    """Factory function to create a Factorio gym environment"""
    # Create task from the task definition
    task = TaskFactory.create_task(env_spec.task_config_path)

    # Resolve configs from spec or defaults
    game_config = env_spec.game_config or _registry._default_game_config
    docker_config = env_spec.docker_config or _registry._default_docker_config

    # Create a lightweight cluster manager pointing at expected ports/volumes
    docker_platform = "linux/arm64" if docker_config.arch in ("arm64", "aarch64") else "linux/amd64"
    cluster = FactorioHeadlessClusterManager(
        config=docker_config,
        docker_platform=docker_platform,
        num_instances=docker_config.num_instances,
        dry_run=False,
    )

    # Create session manager bound to configs/cluster
    session_manager = GameSessionManager(
        game_config=game_config,
        docker_config=docker_config,
        server_manager=cluster,
    )

    # Create a single GameSession targeting instance 0
    game_session: GameSession = session_manager._make_session(instance_id=0, task=task)

    # Return the gym environment
    return FactorioGymEnv(game_session=game_session)


def register_all_environments() -> None:
    """Register all discovered environments with gym"""
    _registry.discover_tasks()


def list_available_environments() -> List[str]:
    """List all available gym environment IDs"""
    return _registry.list_environments()


def get_environment_info(env_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a specific environment"""
    spec = _registry.get_environment_spec(env_id)
    if spec is None:
        return None

    return {
        "env_id": spec.env_id,
        "task_key": spec.task_key,
        "description": spec.description,
        "task_config_path": spec.task_config_path,
        "num_agents": spec.num_agents,
        "model": spec.model,
        "version": spec.version,
        "exit_on_task_success": spec.exit_on_task_success,
    }


# Auto-register environments when module is imported
register_all_environments()


# Convenience functions for gym.make() compatibility
def make(env_id: str, **kwargs) -> FactorioGymEnv:
    """Create a gym environment by ID"""
    return gym.make(env_id, **kwargs)


def configure_registry(
    game_config: Optional[GameConfig] = None,
    docker_config: Optional[DockerConfig] = None,
) -> None:
    """Configure default Game/Docker configs for all gym environments.

    Call this early from entrypoints (e.g., run_eval) to set defaults that
    will be attached to environments created via gym.make().
    """
    _registry.set_defaults(game_config=game_config, docker_config=docker_config)


# Example usage and documentation
if __name__ == "__main__":
    # List all available environments
    print("Available Factorio Gym Environments:")
    for env_id in list_available_environments():
        info = get_environment_info(env_id)
        print(f"  {env_id}: {info['description']}")

    # Example of creating an environment
    # env = gym.make("Factorio-iron_ore_throughput_16-v0")
    # obs = env.reset()
    # action = {'agent_idx': 0, 'code': 'print("Hello Factorio!")'}
    # obs, reward, done, info = env.step(action)
    # env.close()
