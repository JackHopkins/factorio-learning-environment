import argparse
import asyncio
import concurrent.futures
import multiprocessing
import signal
import sys
from typing import List, Tuple
import os
from dotenv import load_dotenv

from llm_factory import LLMFactory
from search.beam.beam_search import ParallelBeamSearch, ParallelBeamConfig
from cluster.local.cluster_ips import get_local_container_ips
from search.beam.run import OBSERVATION_SPACE, MANUAL, SYSTEM_PROMPT, HISTORY_SUMMARIZATION_INSTRUCTIONS
from search.db_client import DBClient
from factorio_instance import FactorioInstance
from search.mcts.formatters.recursive_formatter import RecursiveFormatter
from search.model.game_state import GameState

os.environ.update({"FORCE_COLOR": "1", "TERM": "xterm-256color"})
load_dotenv()


def create_factorio_instances(start_index: int, count: int) -> List[FactorioInstance]:
    def init_instance(params: Tuple[str, int, int]) -> FactorioInstance:
        ip, udp_port, tcp_port = params
        return FactorioInstance(address=ip, tcp_port=tcp_port, bounding_box=200,
                                fast=True, cache_scripts=False, inventory={}, all_technologies_researched=False)

    ips, udp_ports, tcp_ports = get_local_container_ips()
    # Slice the IPs and ports based on start_index and count
    ips = ips[start_index:start_index + count]
    udp_ports = udp_ports[start_index:start_index + count]
    tcp_ports = tcp_ports[start_index:start_index + count]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        return list(executor.map(init_instance, zip(ips, udp_ports, tcp_ports)))


async def get_version_to_use(resume_version: int = None) -> int:
    """Initialize DB client and get the version to use."""
    db_client = await create_db_client()
    if resume_version is not None:
        return resume_version
    return await db_client.get_largest_version() + 1


async def create_db_client() -> DBClient:
    """Create and return a new database client."""
    try:
        return DBClient(
            max_conversation_length=40,
            host=os.getenv("SKILLS_DB_HOST"),
            port=os.getenv("SKILLS_DB_PORT"),
            dbname=os.getenv("SKILLS_DB_NAME"),
            user=os.getenv("SKILLS_DB_USER"),
            password=os.getenv("SKILLS_DB_PASSWORD")
        )
    except Exception as e:
        print(f"\033[91mError connecting to the database: {e}\033[91m")
        raise


async def run_model_search(model: str, instance_start: int, version: int, resume_version: int = None):
    # Create a new DB client for this process
    db_client = await create_db_client()

    try:
        # Create 4 instances for each model's beam search
        instances = create_factorio_instances(instance_start, 4)
        for instance in instances:
            instance.speed(10)
    except Exception as e:
        print(f"\033[91mError initialising Factorio instances for model {model}: {e}\033[91m")
        return

    initial_state = GameState.from_instance(instances[0])
    API_SCHEMA = instances[0].get_system_prompt()
    prompt = SYSTEM_PROMPT + '\n\n' + API_SCHEMA + '\n\nObservations:\n' + OBSERVATION_SPACE + '\n\n' + MANUAL + '\n```'

    current_depth = 0
    resume_heads = None

    if resume_version is not None:
        if not await db_client.version_exists(resume_version):
            print(f"Version {resume_version} does not exist in database")
            return

        beam_width = 4
        resume_heads = await db_client.get_beam_heads(resume_version, beam_width)
        if not resume_heads:
            print(f"No valid beam heads found for version {resume_version}")
            return

        depth = resume_heads[0].depth
        for prog in resume_heads:
            assert prog.depth == depth, "All beam head depths must be the same in order to resume."

        current_depth = depth

    config = ParallelBeamConfig(
        beam_width=4,
        expansion_factor=1,
        system_prompt=prompt,
        initial_state=initial_state,
        model=model,
        beam_kwargs={'error_penalty': 0}
    )

    llm_factory = LLMFactory(model=model)

    formatter = RecursiveFormatter(
        chunk_size=32,
        llm_factory=llm_factory,
        cache_dir='./summary_cache',
        summary_instructions=API_SCHEMA + HISTORY_SUMMARIZATION_INSTRUCTIONS,
        summarize_history=False
    )

    parallel_beam = ParallelBeamSearch(
        instances=instances,
        db_client=db_client,
        llm_factory=llm_factory,
        config=config,
        version=version,
        version_description=f"model:{model}\ntype:beam",
        current_depth=current_depth,
        formatter=formatter,
        base_port=instances[0].tcp_port,
        resume_version=resume_version,
        resume_heads=resume_heads
    )

    if resume_version:
        await parallel_beam._verify_version_compatibility()

    await parallel_beam.search(n_iterations=1024)


def run_model_in_process(model: str, instance_start: int, version: int, resume_version: int = None):
    """Helper function to run asyncio event loop in a separate process"""
    asyncio.get_event_loop().set_debug(True)
    asyncio.run(run_model_search(model, instance_start, version, resume_version))

def signal_handler(signum, frame):
    print("\nTerminating processes...")
    sys.exit(0)

async def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser()
    parser.add_argument('--resume-version', type=int, help='Version to resume from')
    args = parser.parse_args()
    resume_version = args.resume_version if args.resume_version else None #450

    # List of models to run in parallel
    model_configs = [
        {"model": "gpt-4o"},
        {"model": "claude-3-5-sonnet-20241022"},
        {"model": "gpt-4o-mini"},
        {"model": "meta-llama/Llama-3.1-70B-Instruct-Turbo"}
    ]

    parser = argparse.ArgumentParser()
    parser.add_argument('--resume-versions', type=str, help='Comma-separated list of versions to resume from')
    args = parser.parse_args()

    if args.resume_versions:
        versions = [int(v.strip()) if v.strip() else None for v in args.resume_versions.split(',')]
        for i, version in enumerate(versions[:len(model_configs)]):
            if version is not None:
                model_configs[i]["resume_version"] = version

    base_version = await get_version_to_use(None)
    # Get version to use with a temporary DB client
    version_to_use = await get_version_to_use(resume_version)

    # Create process pool and run models in parallel
    with concurrent.futures.ProcessPoolExecutor(max_workers=len(model_configs)) as executor:
        # Start each model with its own set of 4 instances
        futures = []
        for i, config in enumerate(model_configs):
            instance_start = i * 4  # Each model gets 4 consecutive instances
            resume_version = config.get("resume_version")
            version = resume_version if resume_version else base_version + i

            future = executor.submit(
                run_model_in_process,
                config["model"],
                instance_start,
                version,
                resume_version
            )
            futures.append(future)

        # Wait for all processes to complete
        concurrent.futures.wait(futures)

        # Check for any exceptions
        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"\033[91mError in model process: {e}\033[91m")


if __name__ == '__main__':
    asyncio.run(main())