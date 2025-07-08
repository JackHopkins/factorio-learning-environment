import argparse
import asyncio
import concurrent.futures
import multiprocessing
import os
import signal
import sys
from typing import List

from dotenv import load_dotenv

from fle.agents.formatters import RecursiveReportFormatter
from fle.agents.llm.api_factory import APIFactory
from fle.commons.cluster_ips import get_local_container_ips
from fle.commons.db_client import create_db_client
from fle.commons.models.game_state import GameState
from fle.env import FactorioInstance
from fle.eval.algorithms.beam import ParallelBeamConfig, ParallelBeamSearch
from fle.eval.algorithms.beam.run import MANUAL, OBSERVATION_SPACE, SYSTEM_PROMPT

os.environ.update({"FORCE_COLOR": "1", "TERM": "xterm-256color"})
load_dotenv()


def create_factorio_instances(start_index: int, count: int) -> List[FactorioInstance]:
    """Create Factorio instances with proper resource management"""
    ips, udp_ports, tcp_ports = get_local_container_ips()

    # Slice the IPs and ports based on start_index and count
    ips = ips[start_index : start_index + count]
    udp_ports = udp_ports[start_index : start_index + count]
    tcp_ports = tcp_ports[start_index : start_index + count]

    instances = []
    errors = []

    # Create instances sequentially to avoid race conditions
    for ip, udp_port, tcp_port in zip(ips, udp_ports, tcp_ports):
        try:
            instance = FactorioInstance(
                address=ip,
                tcp_port=tcp_port,
                bounding_box=200,
                fast=True,
                cache_scripts=False,
                inventory={},
                all_technologies_researched=False,
            )
            instance.speed(10)
            instances.append(instance)
        except Exception as e:
            errors.append(f"Failed to create instance at {ip}:{tcp_port} - {str(e)}")

    if errors:
        # Clean up any successfully created instances
        # for instance in instances:
        #     try:
        #         instance.close()
        #     except:
        #         pass
        raise RuntimeError(f"Failed to create all instances: {'; '.join(errors)}")

    if not instances:
        raise RuntimeError("No instances were created successfully")

    return instances


async def get_version_to_use(resume_version: int = None) -> int:
    """Initialize DB client and get the version to use."""
    try:
        db_client = await create_db_client()
    except Exception as e:
        print(f"\033[91mError connecting to the database: {e}\033[91m")
        raise

    if resume_version is not None:
        return resume_version
    return await db_client.get_largest_version() + 1


async def run_model_search(
    model: str, instance_start: int, version: int, resume_version: int = None
):
    # Create a new DB client for this process
    db_client = await create_db_client()

    try:
        # Create 4 instances for each model's beam search
        instances = create_factorio_instances(instance_start, 4)
        for instance in instances:
            instance.speed(10)
    except Exception as e:
        print(
            f"\033[91mError initialising Factorio instances for model {model}: {e}\033[91m"
        )
        return

    initial_state = GameState.from_instance(instances[0])
    API_SCHEMA = instances[0].get_system_prompt()
    prompt = (
        SYSTEM_PROMPT
        + "\n\n"
        + API_SCHEMA
        + "\n\n# Observations:\n"
        + OBSERVATION_SPACE
        + "\n\n"
        + MANUAL
        + "\n```"
    )

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
        # for prog in resume_heads:
        #     assert prog.depth == depth, "All beam head depths must be the same in order to resume."

        current_depth = depth

    config = ParallelBeamConfig(
        beam_width=4,
        expansion_factor=1,
        system_prompt=prompt,
        initial_state=initial_state,
        model=model,
        beam_kwargs={"error_penalty": 0},
    )

    api_factory = APIFactory(model=model)

    # formatter = RecursiveFormatter(
    #     chunk_size=32,
    #     api_factory=api_factory,
    #     cache_dir='./summary_cache',
    #     summary_instructions=API_SCHEMA + HISTORY_SUMMARIZATION_INSTRUCTIONS,
    #     summarize_history=False
    # )
    formatter = RecursiveReportFormatter(
        chunk_size=32,
        llm_call=api_factory.acall,
        cache_dir=".fle/summary_cache",
    )

    parallel_beam = ParallelBeamSearch(
        instances=instances,
        db_client=db_client,
        api_factory=api_factory,
        config=config,
        version=version,
        version_description=f"model:{model}\ntype:beam",
        current_depth=current_depth,
        formatter=formatter,
        base_port=instances[0].tcp_port,
        resume_version=resume_version,
        resume_heads=resume_heads,
    )

    if resume_version:
        await parallel_beam._verify_version_compatibility()

    await parallel_beam.search(n_iterations=1024)


def run_model_in_process(
    model: str, instance_start: int, version: int, resume_version: int = None
):
    """Helper function to run asyncio event loop in a separate process"""
    # Close any existing event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.stop()
        loop.close()
    except:
        pass

    # Create new event loop for this process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Enable debug mode only if needed
        # loop.set_debug(True)
        return loop.run_until_complete(
            run_model_search(model, instance_start, version, resume_version)
        )
    finally:
        try:
            loop.stop()
            loop.close()
        except:
            pass


def signal_handler(signum, frame):
    print("\nTerminating processes...")
    sys.exit(0)


async def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--resume-versions",
        type=str,
        help="Comma-separated list of versions to resume from",
    )
    args = parser.parse_args()

    model_configs = [
        {"model": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "resume_version": 483},
        {"model": "gpt-4o-mini", "resume_version": 484},
        {"model": "gpt-4o", "resume_version": 485},
    ]

    if args.resume_versions:
        versions = [
            int(v.strip()) if v.strip() else None
            for v in args.resume_versions.split(",")
        ]
        for i, version in enumerate(versions[: len(model_configs)]):
            if version is not None:
                model_configs[i]["resume_version"] = version

    base_version = await get_version_to_use(None)

    # Use ProcessPoolExecutor with proper cleanup
    executor = concurrent.futures.ProcessPoolExecutor(
        max_workers=len(model_configs),
        mp_context=multiprocessing.get_context(
            "spawn"
        ),  # Use spawn for better process isolation
    )

    try:
        # Start each model with its own set of instances
        futures = []
        for i, config in enumerate(model_configs):
            instance_start = i * 4
            resume_version = config.get("resume_version")
            version = resume_version if resume_version else base_version + i

            future = executor.submit(
                run_model_in_process,
                config["model"],
                instance_start,
                version,
                resume_version,
            )
            futures.append(future)

        # Monitor futures with timeout
        done, not_done = concurrent.futures.wait(
            futures,
            timeout=3600 * 5,  # 5 hour timeout
            return_when=concurrent.futures.ALL_COMPLETED,
        )

        # Handle timeouts
        if not_done:
            print(f"Some processes did not complete: {len(not_done)} remaining")
            for future in not_done:
                future.cancel()

        # Check results
        for future in done:
            try:
                future.result()
            except Exception as e:
                print(f"\033[91mError in model process: {e}\033[91m")

    finally:
        # Ensure executor is shut down
        executor.shutdown(wait=True, cancel_futures=True)


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    asyncio.run(main())
