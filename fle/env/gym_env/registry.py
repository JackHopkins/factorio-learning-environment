import gym
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from fle.env.gym_env.environment import FactorioGymEnv
from fle.eval.tasks import TaskFactory
from fle.env import FactorioInstance
from fle.commons.cluster_ips import get_local_container_ips


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


class FactorioGymRegistry:
    """Registry for Factorio gym environments"""

    def __init__(self):
        self._environments: Dict[str, GymEnvironmentSpec] = {}
        # Use the same path construction as TaskFactory for consistency
        from fle.eval.tasks.task_factory import TASK_FOLDER

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
        for task_file in self._task_definitions_path.glob("*.json"):
            try:
                with open(task_file, "r") as f:
                    task_data = json.load(f)

                task_key = task_data.get("config", {}).get("task_key", task_file.stem)
                task_type = task_data.get("task_type", "default")
                goal_description = task_data.get("config", {}).get(
                    "goal_description", f"Task: {task_key}"
                )

                # Create environment ID
                env_id = f"Factorio-{task_key}-v0"

                # Register the environment
                self.register_environment(
                    env_id=env_id,
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
        )

        self._environments[env_id] = spec

        # Register with gym
        gym.register(
            id=env_id,
            entry_point="fle.env.gym_env.registry:make_factorio_env",
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

    # Create Factorio instance
    # Note: This assumes you have containers available
    try:
        ips, udp_ports, tcp_ports = get_local_container_ips()
        if len(tcp_ports) == 0:
            raise RuntimeError("No Factorio containers available")

        # Use the first available container
        instance = FactorioInstance(
            address=ips[0],
            container_id=0,  # Use first container
            num_agents=env_spec.num_agents,
        )
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
