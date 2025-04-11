import asyncio
import argparse
import multiprocessing
from dotenv import load_dotenv
from agents.basic_agent import BasicAgent
from eval.open.independent_runs.trajectory_runner import run_process, get_next_version, create_factorio_instance, EvalConfig
from eval.tasks.task_factory import TaskFactory
from pathlib import Path
import json
from dataclasses import dataclass
load_dotenv()
from cluster.local.cluster_ips import get_local_container_ips


@dataclass  
class RunConfig:
    task: str
    model: str
    version: int = None
    num_agents: int = 1
    exit_on_task_success: bool = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run_config', type=str, help='Path of the run config file', default=Path("eval", "open", "independent_runs","run_config.json"))
    args = parser.parse_args()
    # read in run_config
    run_config_location = args.run_config
    with open(run_config_location, 'r') as f:
        run_configs_raw = json.load(f)
        run_configs = [RunConfig(**config) for config in run_configs_raw]

    # Create initial state and get system prompt
    try:
        instance = create_factorio_instance(0)
        system_prompt = instance.get_system_prompt()
    except Exception as e:
        raise(f"Error creating Factorio instance: {e}")
    
    # check if we have more containers than run_configs
    ips, udp_ports, tcp_ports = get_local_container_ips()
    if len(tcp_ports) < len(run_configs):
        raise ValueError(f"Not enough containers for {len(run_configs)} runs. Only {len(ips)} containers available.")
    version_offset = 0
    # Get starting version number for new runs
    base_version = asyncio.run(get_next_version())
    processes = []
    for run_idx, run_config in enumerate(run_configs):
        task = TaskFactory.create_task(run_config.task)
        agents = []
        for _ in range(run_config.num_agents):
            agent = BasicAgent(model=run_config.model, system_prompt=system_prompt, task=task)
            agents.append(agent)
        if run_config.version is not None:
            version = run_config.version
        else:
            version = base_version + version_offset
            version_offset += 1
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
        processes.append(p)

    # Wait for all processes to complete
    for p in processes:
        p.join()


if __name__ == "__main__":
    multiprocessing.set_start_method('spawn')
    main()