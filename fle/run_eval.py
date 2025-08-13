import argparse
import asyncio
import json
import multiprocessing
import os
from pathlib import Path

import gym
from dotenv import load_dotenv

from fle.agents.gym_agent import GymAgent
from fle.commons.cluster_ips import get_local_container_ips
from fle.env.environment import FactorioGymEnv
from fle.env.gym_env.config import GymEvalConfig, GymRunConfig
from fle.env.gym_env.observation_formatter import BasicObservationFormatter
from fle.env.gym_env.system_prompt_formatter import SystemPromptFormatter
from fle.env.trajectory_runner import GymTrajectoryRunner
from fle.env.registry import (
    get_environment_info,
    list_available_environments,
    configure_registry,
)
from fle.env.game.config import GameConfig
from fle.services.docker.config import DockerConfig
from fle.services.db.db_client import create_db_client, get_next_version

load_dotenv()


def get_validated_run_configs(run_config_location: str) -> list[GymRunConfig]:
    """Read and validate run configurations from file"""
    # Read run config
    with open(run_config_location, "r") as f:
        run_configs_raw = json.load(f)
        run_configs = [GymRunConfig(**config) for config in run_configs_raw]

    # Validate config
    num_agents_in_configs = [run_config.num_agents for run_config in run_configs]
    if any(num_agents == 1 for num_agents in num_agents_in_configs) and any(
        num_agents > 1 for num_agents in num_agents_in_configs
    ):
        raise ValueError(
            "Cannot mix single agent and multi agent runs in the same run config file. Please split into separate files."
        )

    # Validate that all environment IDs exist in the registry
    available_envs = list_available_environments()
    for run_config in run_configs:
        if run_config.env_id not in available_envs:
            raise ValueError(
                f"Environment ID '{run_config.env_id}' not found in registry. Available environments: {available_envs}"
            )

    # Check if we have enough containers
    ips, udp_ports, tcp_ports = get_local_container_ips()
    if len(tcp_ports) < len(run_configs):
        raise ValueError(
            f"Not enough containers for {len(run_configs)} runs. Only {len(ips)} containers available."
        )

    return run_configs


def run_process(run_idx: int, config: GymEvalConfig):
    """Run a single gym evaluation process"""
    asyncio.run(run_trajectory(run_idx, config))


async def run_trajectory(run_idx: int, config: GymEvalConfig):
    """Run a single gym evaluation process"""

    # Create gym environment using gym.make()
    gym_env = gym.make(config.env_id)

    log_dir = os.path.join(".fle", "trajectory_logs", f"v{config.version}")
    runner = GymTrajectoryRunner(
        config=config,
        gym_env=gym_env,
        log_dir=log_dir,
        process_id=run_idx,
    )
    await runner.run_sequential()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run_config",
        type=str,
        help="Path of the run config file",
        default=Path("eval", "open", "independent_runs", "gym_run_config.json"),
    )
    args = parser.parse_args()

    # Read and validate run configurations
    run_configs = get_validated_run_configs(args.run_config)

    # Configure gym registry defaults for Game/Docker configs
    # Note: We validated that all runs have the same num_agents above
    num_agents = run_configs[0].num_agents if len(run_configs) > 0 else 1
    game_config = GameConfig(num_agents=num_agents)
    docker_config = DockerConfig()
    configure_registry(game_config=game_config, docker_config=docker_config)

    # Get starting version number for new runs
    base_version = await get_next_version()
    version_offset = 0

    # Create and start processes
    processes = []
    for run_idx, run_config in enumerate(run_configs):
        # Get environment info from registry
        env_info = get_environment_info(run_config.env_id)
        if env_info is None:
            raise ValueError(f"Could not get environment info for {run_config.env_id}")

        # Create gym environment to get task and instance
        gym_env: FactorioGymEnv = gym.make(run_config.env_id)
        await gym_env.game_session.initialise()
        task = gym_env.game_session.task
        instance = gym_env.game_session.instance

        # Create agents and their agent cards
        agents = dict()
        agent_cards = []
        num_agents = run_config.num_agents
        for agent_idx in range(num_agents):
            system_prompt = instance.agent_instances[agent_idx].get_system_prompt(num_agents=num_agents)
            agent = GymAgent(
                model=run_config.model,
                system_prompt=system_prompt,
                task=task,
                agent_idx=agent_idx,
                observation_formatter=BasicObservationFormatter(include_research=False),
                system_prompt_formatter=SystemPromptFormatter(),
            )
            agents[agent_idx] = agent

            # Create agent card for a2a support
            agent_card = agent.get_agent_card()
            agent_cards.append(agent_card)

        # Set version
        version = (
            run_config.version
            if run_config.version is not None
            else base_version + version_offset
        )
        version_offset += 1

        # Create eval config with agent cards for a2a support
        config = GymEvalConfig(
            agents=agents,
            version=version,
            version_description=f"model:{run_config.model}\ntype:{task.task_key}\nnum_agents:{run_config.num_agents}",
            exit_on_task_success=run_config.exit_on_task_success,
            task=task,
            agent_cards=agent_cards,
            env_id=run_config.env_id,
        )

        # Ensure agent cards are properly set for a2a functionality
        assert config.agent_cards is not None

        # Start process
        p = multiprocessing.Process(target=run_process, args=(run_idx, config))
        p.start()
        processes.append(p)

    # Wait for all processes to complete
    for p in processes:
        p.join()


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    asyncio.run(main())
