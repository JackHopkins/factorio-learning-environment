import os
import asyncio
from dotenv import load_dotenv
from cluster.local.cluster_ips import get_local_container_ips
from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.mcts_factory import MCTSFactory
from datasetgen.mcts.run_results import RunResults
from datasetgen.mcts.samplers.kld_achievement_sampler import KLDiversityAchievementSampler
from llm_factory import LLMFactory
from factorio_instance import FactorioInstance
import concurrent.futures
from typing import List, Tuple

os.environ.update({"FORCE_COLOR": "1", "TERM": "xterm-256color"})
load_dotenv()


def create_factorio_instances() -> List[FactorioInstance]:
    def init_instance(params: Tuple[str, int, int]) -> FactorioInstance:
        ip, udp_port, tcp_port = params
        return FactorioInstance(address=ip, tcp_port=tcp_port, bounding_box=200,
                                fast=True, cache_scripts=False, inventory={})

    ips, udp_ports, tcp_ports = get_local_container_ips()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return list(executor.map(init_instance, zip(ips, udp_ports, tcp_ports)))


async def main():
    try:
        db_client = DBClient(
            max_conversation_length=40,
            host=os.getenv("SKILLS_DB_HOST"),
            port=os.getenv("SKILLS_DB_PORT"),
            dbname=os.getenv("SKILLS_DB_NAME"),
            user=os.getenv("SKILLS_DB_USER"),
            password=os.getenv("SKILLS_DB_PASSWORD")
        )
    except Exception as e:
        print("\033[91mError connecting to the database. Please check your credentials and try again.\033[91m")
        return

    # Get largest version from DB for initialisation purposes. If no versions exist, start at 0.
    largest_version_to_date = await db_client.get_largest_version()

    # Initialize components
    try:
        instances = create_factorio_instances()
        for instance in instances:
            instance.speed(10) # Speed up the game for faster evaluation
    except Exception as e:
        print("\033[91mError initialising Factorio instances. Are the docker containers running, and have they been activated?\033[91m")
        return

    # Get configuration from CLI/interactive prompts
    factory = MCTSFactory()
    mcts_config, sampler_config = factory.get_config_from_cli(default_version=largest_version_to_date+1)


    mcts_config.system_prompt = instances[0].get_system_prompt()

    # Initialize factory singleton
    factory.initialize(instances, db_client, mcts_config, sampler_config) #llm_factory, config)

    # Create MCTS instance
    mcts = factory.create_mcts(mcts_config)

    # Run search
    print("Starting MCTS search...")
    await mcts.search(n_iterations=2000, skip_failures=False)

    run = RunResults(version=mcts_config.version, db_client=db_client)
    run.save_plots()




if __name__ == '__main__':
    asyncio.run(main())