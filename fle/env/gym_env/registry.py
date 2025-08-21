import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from fle.env.a2a_instance import A2AFactorioInstance
import gym
import json

from fle.commons.cluster_ips import get_local_container_ips
from fle.commons.asyncio_utils import run_async_safely
from fle.env import FactorioInstance
from fle.env.gym_env.environment import FactorioGymEnv
from fle.eval.tasks import TaskFactory, TASK_FOLDER

PORT_OFFSET = int(os.environ["PORT_OFFSET"])


@dataclass
class GymEnvironmentSpec:
    """Specification for a registered gym environment"""

    task_key: str
    task_config_path: str
    description: str
    num_agents: int


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
                    num_agents=task_data["num_agents"],
                )
            except Exception as e:
                print(f"Warning: Failed to load task definition {task_file}: {e}")

        self._discovered = True

    def register_environment(
        self,
        task_key: str,
        task_config_path: str,
        description: str,
        num_agents: int,
    ) -> None:
        """Register a new gym environment"""
        spec = GymEnvironmentSpec(
            task_key=task_key,
            task_config_path=task_config_path,
            description=description,
            num_agents=num_agents,
        )

        self._environments[task_key] = spec

        # Register with gym
        gym.register(
            id=task_key,
            entry_point="fle.env.gym_env.registry:make_factorio_env",
            kwargs={"spec": spec},
        )

    def list_environments(self) -> List[str]:
        """List all registered environment IDs"""
        return list(self._environments.keys())

    def get_environment_spec(self, env_id: str) -> Optional[GymEnvironmentSpec]:
        """Get environment specification by ID"""
        return self._environments.get(env_id)


# Global registry instance
_registry = FactorioGymRegistry()


def make_factorio_env(spec: GymEnvironmentSpec, run_idx: int) -> FactorioGymEnv:
    """Factory function to create a Factorio gym environment"""
    # Create task from the task definition
    task = TaskFactory.create_task(spec.task_config_path)

    # Create Factorio instance
    try:
        # Check for external server configuration via environment variables
        address = os.getenv("FACTORIO_SERVER_ADDRESS")
        tcp_port = os.getenv("FACTORIO_SERVER_PORT")

        if not address and not tcp_port:
            ips, udp_ports, tcp_ports = get_local_container_ips()
            if len(tcp_ports) == 0:
                raise RuntimeError("No Factorio containers available")

            # Apply port offset for multiple terminal sessions
            container_idx = PORT_OFFSET + run_idx
            if container_idx >= len(tcp_ports):
                raise RuntimeError(
                    f"Container index {container_idx} (PORT_OFFSET={PORT_OFFSET} + run_idx={run_idx}) exceeds available containers ({len(tcp_ports)})"
                )

            address = ips[container_idx]
            tcp_port = tcp_ports[container_idx]

        common_kwargs = {
            "address": address,
            "tcp_port": int(tcp_port),
            "num_agents": spec.num_agents,
            "fast": True,
            "cache_scripts": True,
            "inventory": {},
            "all_technologies_researched": True,
        }

        print(f"Using local Factorio container at {address}:{tcp_port}")
        if spec.num_agents > 1:
            instance = run_async_safely(A2AFactorioInstance.create(**common_kwargs))
        else:
            instance = FactorioInstance(**common_kwargs)

        instance.set_speed(10)

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


def get_environment_info(task_key: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a specific environment"""
    spec = _registry.get_environment_spec(task_key)
    if spec is None:
        return None
    return asdict(spec)


# Auto-register environments when module is imported
register_all_environments()

# Example usage and documentation
if __name__ == "__main__":
    # List all available environments
    print("Available Factorio Gym Environments:")
    for env_id in list_available_environments():
        info = get_environment_info(env_id)
        print(f"  {env_id}: {info['description']}")
