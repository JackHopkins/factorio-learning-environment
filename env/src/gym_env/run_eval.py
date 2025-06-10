import asyncio
import argparse
import multiprocessing
from dotenv import load_dotenv
from pathlib import Path
import json

from agents.gym_agent import GymAgent
from gym_env.trajectory_runner import GymTrajectoryRunner
from gym_env.config import GymRunConfig, GymEvalConfig
from gym_env.observation_formatter import BasicObservationFormatter
from eval.tasks.task_factory import TaskFactory
from cluster.local.cluster_ips import get_local_container_ips
from eval.open.independent_runs.trajectory_runner import get_next_version, create_factorio_instance, create_db_client

load_dotenv()

def run_process(run_idx: int, config: GymEvalConfig):
    """Run a single gym evaluation process"""
    asyncio.run(run_trajectory(run_idx, config))


async def run_trajectory(run_idx: int, config: GymEvalConfig):
    """Run a single gym evaluation process"""
    # Create db client
    db_client = await create_db_client()
    
    # Create trajectory runner
    instance = await create_factorio_instance(run_idx, len(config.agents))
    config.task.setup(instance)
    runner = GymTrajectoryRunner(
        config=config,
        instance=instance,
        db_client=db_client,
        process_id=run_idx
    )
    await runner.run()
    await db_client.cleanup()

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run_config', type=str, 
                       help='Path of the run config file', 
                       default=Path("eval", "open", "independent_runs", "gym_run_config.json"))
    args = parser.parse_args()

    # Read run config
    run_config_location = args.run_config
    with open(run_config_location, 'r') as f:
        run_configs_raw = json.load(f)
        run_configs = [GymRunConfig(**config) for config in run_configs_raw]

    # Validate config
    num_agents_in_configs = [run_config.num_agents for run_config in run_configs]
    if any(num_agents == 1 for num_agents in num_agents_in_configs) and any(num_agents > 1 for num_agents in num_agents_in_configs):
        raise ValueError("Cannot mix single agent and multi agent runs in the same run config file. Please split into separate files.")

    try:
        # TODO: the server currently has only default agent cards. 
        # But we aren't doing anything with them yet anyway.
        num_agents = run_configs[0].num_agents
        instance = await create_factorio_instance(0, num_agents)
        system_prompt = instance.get_system_prompt()
    except Exception as e:
        raise Exception(f"Error creating factorio instance: {e}")

    # Check if we have enough containers
    ips, udp_ports, tcp_ports = get_local_container_ips()
    if len(tcp_ports) < len(run_configs):
        raise ValueError(f"Not enough containers for {len(run_configs)} runs. Only {len(ips)} containers available.")

    # Get starting version number for new runs
    base_version = await get_next_version()
    version_offset = 0

    # Create and start processes
    processes = []
    for run_idx, run_config in enumerate(run_configs):
        # Create task
        task = TaskFactory.create_task(run_config.task)

        # Create agents and their agent cards
        agents = []
        agent_cards = []
        for agent_idx in range(run_config.num_agents):
            system_prompt = instance.get_system_prompt(agent_idx)
            agent = GymAgent(
                model=run_config.model,
                system_prompt=system_prompt,
                task=task,
                agent_idx=agent_idx,
                observation_formatter=BasicObservationFormatter(include_research=False)
            )
            agents.append(agent)
            
            # Create agent card for a2a support
            agent_card = agent.get_agent_card()
            agent_cards.append(agent_card)

        # Set version
        version = run_config.version if run_config.version is not None else base_version + version_offset
        version_offset += 1

        # Create eval config with agent cards for a2a support
        config = GymEvalConfig(
            agents=agents,
            version=version,
            version_description=f"model:{run_config.model}\ntype:{task.task_key}\nnum_agents:{run_config.num_agents}",
            exit_on_task_success=run_config.exit_on_task_success,
            task=task,
            agent_cards=agent_cards
        )
        
        # Ensure agent cards are properly set for a2a functionality
        assert config.agent_cards is not None

        # Start process
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
    asyncio.run(main())
