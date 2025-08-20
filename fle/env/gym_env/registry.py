import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fle.env.a2a_instance import A2AFactorioInstance
import json

from fle.commons.cluster_ips import get_local_container_ips
from fle.commons.asyncio_utils import run_async_safely
from fle.env import FactorioInstance
from fle.env.gym_env.environment import FactorioGymEnv
from fle.eval.tasks import TaskFactory, TASK_FOLDER


@dataclass
class GymEnvironmentSpec:
    """Specification for a registered gym environment"""

    env_id: str
    task_key: str
    task_config_path: str
    description: str
    num_agents: int
    version: Optional[int]


class FactorioGymRegistry:
    """Registry for Factorio gym environments"""

    def __init__(self):
        self._environments: Dict[str, GymEnvironmentSpec] = {}
        self._task_definitions_path = TASK_FOLDER
        self._discovered = False

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
                self.register_environment(
                    task_key=task_data["task_key"],
                    task_config_path=str(task_file),
                    description=task_data["goal_description"],
                    task_type=task_data["task_type"],
                    num_agents=task_data["num_agents"],
                )
            except Exception as e:
                print(f"Warning: Failed to load task definition {task_file}: {e}")

        self._discovered = True

    def register_environment(
        self,
        env_id: str,
        task_config_path: str,
        description: str,
        task_type: str,
        num_agents: int,
        model: str,
        task_data: Dict[str, Any],
    ) -> None:
        """Register a new gym environment"""

        self._environments[env_id] = {
            "env_id": env_id,
            "task_config_path": task_config_path,
            "task_data": task_data,
        }

        # self._environments[env_id] = spec

        # # Register with gym
        # gym.register(
        #     id=env_id,
        #     entry_point="fle.env.gym_env.registry:make_factorio_env",
        #     kwargs={"env_spec": spec},
        # )

    def list_environments(self) -> List[str]:
        """List all registered environment IDs"""
        return list(self._environments.keys())

    def get_environment_spec(self, env_id: str) -> Optional[Dict[str, Any]]:
        """Get environment specification by ID"""
        return self._environments.get(env_id)


# Global registry instance
_registry = FactorioGymRegistry()


def make_factorio_env(env_spec: Dict[str, Any], instance_id: int = 0) -> FactorioGymEnv:
    """Create a Factorio gym environment from specification"""
    task_config_path = env_spec["task_config_path"]
    task_data = env_spec["task_data"]
    num_agents = task_data["num_agents"]

    # Create task from the task definition
    task = TaskFactory.create_task(task_config_path)

    # Create Factorio instance
    try:
        # Check for external server configuration via environment variables
        address = os.getenv("FACTORIO_SERVER_ADDRESS")
        tcp_port = os.getenv("FACTORIO_SERVER_PORT")

        if not address and not tcp_port:
            ips, udp_ports, tcp_ports = get_local_container_ips()
            if len(tcp_ports) == 0:
                raise RuntimeError("No Factorio containers available")
            address = ips[instance_id]
            tcp_port = tcp_ports[instance_id]

        common_kwargs = {
            "address": address,
            "tcp_port": int(tcp_port),
            "num_agents": num_agents,
            "fast": True,
            "cache_scripts": True,
            "inventory": {},
            "all_technologies_researched": True,
        }

        print(f"Using local Factorio container at {address}:{tcp_port}")
        if num_agents > 1:
            instance = run_async_safely(A2AFactorioInstance.create(**common_kwargs))
        else:
            instance = FactorioInstance(**common_kwargs)

        instance.speed(10)

        # Setup the task
        task.setup(instance)

        # Create and return the gym environment
        env = FactorioGymEnv(instance=instance, task=task)

        return env

    except Exception as e:
        raise RuntimeError(f"Failed to create Factorio environment: {e}")


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

    # Return the task config with additional metadata
    task_data = spec["task_data"]
    return {
        "env_id": spec["env_id"],
        "task_config_path": spec["task_config_path"],
        **task_data,  # Unpack all task data fields
    }


# Auto-register environments when module is imported
register_all_environments()

# Example usage and documentation
if __name__ == "__main__":
    # List all available environments
    print("Available Factorio Gym Environments:")
    for env_id in list_available_environments():
        info = get_environment_info(env_id)
        print(f"  {env_id}: {info['description']}")
