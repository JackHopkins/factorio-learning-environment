import asyncio
import argparse
import multiprocessing
from dotenv import load_dotenv
from agents.basic_agent import BasicAgent
from eval.open.independent_runs.agent_factory import AgentFactory
from eval.open.independent_runs.trajectory_runner import run_process, get_next_version, create_factorio_instance, \
    EvalConfig
from eval.tasks.task_factory import TaskFactory
from pathlib import Path
import json
from dataclasses import dataclass
import time

load_dotenv()
from cluster.local.cluster_ips import get_local_container_ips


@dataclass
class RunConfig:
    task: str
    model: str
    version: int = None
    num_agents: int = 1
    exit_on_task_success: bool = True
    agent: str = "BasicAgent"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run_config', type=str, help='Path of the run config file',
                        default=Path("eval", "open", "independent_runs", "run_config.json"))
    args = parser.parse_args()
    # read in run_config
    run_config_location = args.run_config
    with open(run_config_location, 'r') as f:
        run_configs_raw = json.load(f)
        run_configs = [RunConfig(**config) for config in run_configs_raw]
    num_agents_in_configs = [run_config.num_agents for run_config in run_configs]
    if any(num_agents == 1 for num_agents in num_agents_in_configs) and any(
            num_agents > 1 for num_agents in num_agents_in_configs):
        raise ValueError(
            "Cannot mix single agent and multi agent runs in the same run config file. Please split into separate files.")
    # Create initial state and get system prompt
    try:
        num_agents = run_configs[0].num_agents
        instance = create_factorio_instance(0, num_agents)
        system_prompt = instance.get_system_prompt()
    except Exception as e:
        raise (f"Error creating Factorio instance: {e}")

    # check available containers
    ips, udp_ports, tcp_ports = get_local_container_ips()
    num_available_containers = len(tcp_ports)
    print(f"Available containers: {num_available_containers}, Required runs: {len(run_configs)}")

    # Get starting version number for new runs
    base_version = asyncio.run(get_next_version())
    version_offset = 0

    # If we have enough containers, run in parallel
    # Otherwise, run in batches based on available containers
    if num_available_containers >= len(run_configs):
        run_parallel(run_configs, base_version)
    else:
        run_in_batches(run_configs, base_version, num_available_containers)


def run_parallel(run_configs, base_version):
    """Run all configs in parallel"""
    version_offset = 0
    processes = []
    for run_idx, run_config in enumerate(run_configs):
        process = create_and_start_process(run_config, run_idx, base_version, version_offset)
        processes.append(process)
        version_offset += 1

    # Wait for all processes to complete
    for p in processes:
        p.join()


def run_in_batches(run_configs, base_version, num_available_containers):
    """Run configs in batches based on available containers"""
    version_offset = 0
    total_runs = len(run_configs)

    # Split into batches
    for batch_start in range(0, total_runs, num_available_containers):
        batch_end = min(batch_start + num_available_containers, total_runs)
        batch = run_configs[batch_start:batch_end]
        print(f"Running batch {batch_start // num_available_containers + 1}: jobs {batch_start} to {batch_end - 1}")

        # Start processes for this batch
        processes = []
        for batch_idx, run_config in enumerate(batch):
            run_idx = batch_idx
            process = create_and_start_process(run_config, run_idx, base_version, version_offset)
            processes.append(process)
            version_offset += 1

        # Wait for current batch to complete before starting next batch
        for p in processes:
            p.join()


def create_and_start_process(run_config: RunConfig, run_idx, base_version, version_offset):
    """Helper function to create and start a process for a run configuration"""
    task = TaskFactory.create_task(run_config.task, seed=base_version + version_offset)
    agents = []

    # Create factorio instance for this run
    instance = create_factorio_instance(run_idx, run_config.num_agents)

    for agent_idx in range(run_config.num_agents):
        system_prompt = instance.get_system_prompt(agent_idx)

        # Get all available agent types
        available_agents = AgentFactory.get_available_agents()
        print(f"Available agents: {available_agents}")

        # Create a basic agent
        agent = AgentFactory.create_agent(
            agent_type=run_config.agent,
            model=run_config.model,
            system_prompt=system_prompt,
            task=task,
            agent_idx=agent_idx
        )

        #agent = BasicAgent(model=run_config.model, system_prompt=system_prompt, task=task, agent_idx=agent_idx)
        agents.append(agent)

    if run_config.version is not None:
        version = run_config.version
    else:
        version = base_version + version_offset

    config = EvalConfig(
        agents=agents,
        version=version,
        version_description=f"model:{run_config.model}\ntype:{task.task_key}\nnum_agents:{run_config.num_agents}",
        exit_on_task_success=run_config.exit_on_task_success,
    )

    p = multiprocessing.Process(
        target=run_process,
        args=(run_idx, config)
    )
    p.start()
    return p


if __name__ == "__main__":
    multiprocessing.set_start_method('spawn')
    main()