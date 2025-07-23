import argparse
import asyncio
import json
import multiprocessing
import os
from pathlib import Path

import gym
from dotenv import load_dotenv
from fle.env.gym_env.config import GymEvalConfig, GymRunConfig
from fle.env.gym_env.observation_formatter import BasicObservationFormatter
from fle.env.gym_env.system_prompt_formatter import SystemPromptFormatter
from fle.env.gym_env.registry import get_environment_info, list_available_environments
from fle.env.gym_env.trajectory_runner import GymTrajectoryRunner

from fle.agents.gym_agent import GymAgent
from fle.commons.cluster_ips import get_local_container_ips
from fle.commons.db_client import create_db_client
from fle.eval.algorithms.independent import get_next_version

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
    db_client = await create_db_client()

    # Create gym environment using gym.make()
    gym_env = gym.make(config.env_id)

    log_dir = os.path.join(".fle", "trajectory_logs", f"v{config.version}")
    runner = GymTrajectoryRunner(
        config=config,
        gym_env=gym_env,
        db_client=db_client,
        log_dir=log_dir,
        process_id=run_idx,
    )
    await runner.run()
    await db_client.cleanup()


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

    # Get starting version number for new runs
    base_version = await get_next_version()
    version_offset = 0

    # Get available containers
    ips, udp_ports, tcp_ports = get_local_container_ips()
    num_available = len(tcp_ports)
    total_runs = len(run_configs)

    def create_process(run_idx, run_config, version_offset):
        env_info = get_environment_info(run_config.env_id)
        if env_info is None:
            raise ValueError(f"Could not get environment info for {run_config.env_id}")
        gym_env = gym.make(run_config.env_id)
        task = gym_env.unwrapped.task
        instance = gym_env.unwrapped.instance
        agents = []
        agent_cards = []
        for agent_idx in range(run_config.num_agents):
            system_prompt = instance.get_system_prompt(agent_idx)
            agent = GymAgent(
                model=run_config.model,
                system_prompt=system_prompt,
                task=task,
                agent_idx=agent_idx,
                observation_formatter=BasicObservationFormatter(include_research=False),
                system_prompt_formatter=SystemPromptFormatter(),
            )
            agents.append(agent)
            agent_card = agent.get_agent_card()
            agent_cards.append(agent_card)
        version = (
            run_config.version
            if run_config.version is not None
            else base_version + version_offset
        )
        config = GymEvalConfig(
            agents=agents,
            version=version,
            version_description=f"model:{run_config.model}\ntype:{task.task_key}\nnum_agents:{run_config.num_agents}",
            exit_on_task_success=run_config.exit_on_task_success,
            task=task,
            agent_cards=agent_cards,
            env_id=run_config.env_id,
        )
        assert config.agent_cards is not None
        p = multiprocessing.Process(target=run_process, args=(run_idx, config))
        p.start()
        return p

    if num_available >= total_runs:
        # Run all in parallel
        processes = []
        for run_idx, run_config in enumerate(run_configs):
            p = create_process(run_idx, run_config, version_offset)
            processes.append(p)
            version_offset += 1
        for p in processes:
            p.join()
    else:
        # Run in batches
        for batch_start in range(0, total_runs, num_available):
            batch_end = min(batch_start + num_available, total_runs)
            batch = run_configs[batch_start:batch_end]
            print(
                f"Running batch {batch_start // num_available + 1}: jobs {batch_start} to {batch_end - 1}"
            )
            processes = []
            for batch_idx, run_config in enumerate(batch):
                run_idx = batch_start + batch_idx
                p = create_process(run_idx, run_config, version_offset)
                processes.append(p)
                version_offset += 1
            for p in processes:
                p.join()


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    asyncio.run(main())
