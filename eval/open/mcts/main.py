#!/usr/bin/env python3
"""
Main entry point for running MCTS sampling with Factorio environments.
"""

import os
import sys
import asyncio
import argparse
import multiprocessing
import json
from pathlib import Path
from dotenv import load_dotenv

from eval.open.mcts.mcts_run import MCTSRunParameters, process_mcts_run

# Ensure paths are set up correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

from instance import FactorioInstance
from cluster.local.cluster_ips import get_local_container_ips

# Load environment variables
load_dotenv()


async def create_db_client():
    """Create database client with connection pool"""
    from eval.open.db_client import PostgresDBClient

    return PostgresDBClient(
        max_conversation_length=40,
        min_connections=2,
        max_connections=5,
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD")
    )


async def get_next_version() -> int:
    """Get next available version number"""
    db_client = await create_db_client()
    version = await db_client.get_largest_version()
    await db_client.cleanup()
    return version + 1


def main():
    parser = argparse.ArgumentParser(description="Run MCTS sampling with Factorio environments.")
    parser.add_argument('--run_config', type=str,
                        help='Path of the run config file',
                        default=os.path.join("mcts_run_config.json"))
    parser.add_argument('--workers_per_run', type=int,
                        help='Number of worker processes per MCTS run',
                        default=4)
    args = parser.parse_args()

    # Print some startup information
    print(f"Starting MCTS with configuration from: {args.run_config}")
    print(f"Using {args.workers_per_run} workers per run")

    # Read run config
    run_config_location = args.run_config
    current_dir = Path(__file__).resolve().parent
    with open(current_dir / run_config_location, 'r') as f:
        run_configs = json.load(f)

    print(f"Loaded {len(run_configs)} run configurations")

    # Get system prompt from a temporary Factorio instance
    try:
        # Create a temporary instance just to get the system prompt
        ips, udp_ports, tcp_ports = get_local_container_ips()
        print(f"Found {len(ips)} Factorio containers available")

        temp_instance = FactorioInstance(
            address=ips[0],
            tcp_port=tcp_ports[0],
            bounding_box=200,
            fast=True,
            cache_scripts=True,
            inventory={},
            all_technologies_researched=True
        )
        system_prompt = temp_instance.get_system_prompt()
        print("Successfully obtained system prompt")
        #temp_instance.cleanup()  # Clean up the temporary instance
    except Exception as e:
        print(f"Error creating temporary Factorio instance: {e}")
        return

    # Check if we have enough containers
    ips, udp_ports, tcp_ports = get_local_container_ips()
    total_workers_needed = len(run_configs) * args.workers_per_run
    if len(tcp_ports) < total_workers_needed:
        print(
            f"Warning: Not enough containers. Need {total_workers_needed} workers but only {len(ips)} containers available.")
        print(f"Will run with {len(ips) // len(run_configs)} workers per run instead")
        args.workers_per_run = max(1, len(ips) // len(run_configs))

    # Get starting version number for new runs
    try:
        version_offset = 0
        base_version = asyncio.run(get_next_version())
        print(f"Starting with base version: {base_version}")
    except Exception as e:
        print(f"Error getting next version: {e}")
        return

    # Allocate container IPs and ports for each run
    worker_allocations = []
    for run_idx, _ in enumerate(run_configs):
        start_idx = run_idx * args.workers_per_run
        end_idx = min(start_idx + args.workers_per_run, len(ips))

        # Extract the subset of containers for this run
        run_ips = ips[start_idx:end_idx]
        run_tcp_ports = tcp_ports[start_idx:end_idx]

        worker_allocations.append((run_ips, run_tcp_ports))

    # Start processes for each MCTS run
    processes = []
    for run_idx, run_config in enumerate(run_configs):
        # Get allocated containers for this run
        run_ips, run_tcp_ports = worker_allocations[run_idx]

        # Determine version
        if "version" in run_config:
            version = run_config["version"]
        else:
            version = base_version + version_offset
            version_offset += 1

        # Create a descriptive name for this run
        run_name = f"MCTS-{run_config['task']}-{run_config['model']}-v{version}"
        print(f"Starting run: {run_name} with {len(run_ips)} workers")

        # Prepare run parameters
        run_params = MCTSRunParameters(
            agent_model=run_config["model"],
            agent_system_prompt=system_prompt,
            task_key=run_config["task"],
            task_data={},  # Any additional task data if needed
            version=version,
            version_description=f"model:{run_config['model']}\ntype:{run_config['task']}\nmcts:True",
            num_workers=len(run_ips),
            mcts_config=run_config.get("mcts", {}),
            sampler_config=run_config.get("sampler", {}),
            container_ips=run_ips,
            container_tcp_ports=run_tcp_ports
        )

        # Start MCTS process
        p = multiprocessing.Process(
            target=process_mcts_run,
            args=(run_params,),
            name=run_name
        )
        p.start()
        processes.append(p)

    # Wait for all processes to complete
    for p in processes:
        print(f"Waiting for {p.name} to complete...")
        p.join()
        print(f"{p.name} completed with exit code {p.exitcode}")

    print("All MCTS runs completed!")


if __name__ == "__main__":
    # Set start method for multiprocessing
    multiprocessing.set_start_method('spawn')
    main()