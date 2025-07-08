import asyncio
import argparse
import multiprocessing
from dotenv import load_dotenv
from fle.agents.basic_agent import BasicAgent
from fle.eval.algorithms.independent import (
    run_process,
    get_next_version,
    create_factorio_instance,
    EvalConfig,
)
from fle.eval.tasks.task_factory import TaskFactory
from pathlib import Path
import json
from dataclasses import dataclass
from fle.commons.cluster_ips import get_local_container_ips

load_dotenv()


@dataclass
class RunConfig:
    task: str
    model: str
    version: int = None
    num_agents: int = 1
    exit_on_task_success: bool = True


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run_config",
        type=str,
        help="Path of the run config file",
        default=Path("eval", "open", "independent_runs", "run_config.json"),
    )
    args = parser.parse_args()
    run_config_location = args.run_config
    with open(run_config_location, "r") as f:
        run_configs_raw = json.load(f)
        run_configs = [RunConfig(**config) for config in run_configs_raw]

    if not run_configs:
        print("No run configurations found. Exiting.")
        return

    num_agents = run_configs[0].num_agents
    if any(run_config.num_agents != num_agents for run_config in run_configs):
        raise ValueError(
            "Cannot mix single agent and multi agent runs in the same run config file. Please split into separate files."
        )
    try:
        # TODO: the server currently has only default agent cards.
        # But we aren't doing anything with them yet anyway.
        instance = await create_factorio_instance(0, num_agents)
    except Exception as e:
        raise Exception(f"Error creating initial Factorio instance: {e}")

    ips, udp_ports, tcp_ports = get_local_container_ips()
    if len(tcp_ports) < len(run_configs):
        raise ValueError(
            f"Not enough containers for {len(run_configs)} runs. Only {len(ips)} containers available."
        )

    version_offset = 0
    base_version = await get_next_version()
    processes = []

    for run_idx, run_config_item in enumerate(run_configs):
        task = TaskFactory.create_task(run_config_item.task)

        # Create actual agents and their agent cards for this specific run
        current_run_agents = []
        current_run_agent_cards = []
        for agent_idx in range(run_config_item.num_agents):
            # System prompt can be fetched from the shared initial instance for consistency, or per-agent if it varies
            system_prompt = instance.get_system_prompt(agent_idx=agent_idx)
            agent = BasicAgent(
                model=run_config_item.model,
                system_prompt=system_prompt,
                task=task,
                agent_idx=agent_idx,
            )
            current_run_agents.append(agent)

            agent_card = agent.get_agent_card()
            current_run_agent_cards.append(agent_card)

        version = (
            run_config_item.version
            if run_config_item.version is not None
            else base_version + version_offset
        )
        version_offset += 1

        eval_conf = EvalConfig(
            agents=current_run_agents,
            version=version,
            version_description=f"model:{run_config_item.model}\ntype:{task.task_key}\nnum_agents:{run_config_item.num_agents}",
            exit_on_task_success=run_config_item.exit_on_task_success,
            task=task,
            agent_cards=current_run_agent_cards,
        )
        assert eval_conf.agent_cards is not None

        p = multiprocessing.Process(target=run_process, args=(run_idx, eval_conf))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    asyncio.run(main())
