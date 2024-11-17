import concurrent
import os
from typing import Tuple, List

from dotenv import load_dotenv

from cluster.local.cluster_ips import get_local_container_ips
from datasetgen.mcts.conversation_formatter import OutputOnlyFormatter
from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.factorio_evaluator import FactorioEvaluator
from datasetgen.mcts.game_state import GameState
from datasetgen.mcts.mcts import MCTS
from factorio_instance import FactorioInstance
from llm_factory import LLMFactory

load_dotenv()

def create_instance(params: Tuple[str, int, int]) -> FactorioInstance:
    """Create a single Factorio instance with the given parameters"""
    ip, udp_port, tcp_port = params
    return FactorioInstance(
        address=ip,
        tcp_port=tcp_port,
        bounding_box=200,
        fast=True,
        cache_scripts=False,
        inventory={}
    )


def create_parallel_instances() -> List[FactorioInstance]:
    """Create Factorio instances in parallel using ThreadPoolExecutor from local servers"""
    ips, udp_ports, tcp_ports = get_local_container_ips()
    params = list(zip(ips, udp_ports, tcp_ports))

    with concurrent.futures.ThreadPoolExecutor() as executor:
        instances = list(executor.map(create_instance, params))

    return instances

async def main():
    # Initialize components
    llm = LLMFactory("ft:gpt-4o-2024-08-06:paperplane-ai:fact-self-gen-planning:AQzcPI91")
    db_client = DBClient(host=os.getenv("SKILLS_DB_HOST"),
                         port=os.getenv("SKILLS_DB_PORT"),
                         dbname=os.getenv("SKILLS_DB_NAME"),
                         user=os.getenv("SKILLS_DB_USER"),
                         password=os.getenv("SKILLS_DB_PASSWORD"))

    instances = create_parallel_instances()
    # Initialize FactorioEvaluator with the list of instances
    evaluator = FactorioEvaluator(db_client, instances)
    initial_state = GameState.from_instance(instances[0])

    # Get execution directory from __file__ or other source
    execution_dir = os.path.dirname(os.path.realpath(__file__))
    # load from prompts/bottoms_up_prompts/system_message_policy_self_gen into string
    with open("../../prompts/bottoms_up_prompts/finetuning_prompts/system_message_policy_self_gen.md", "r") as f:
        system_prompt = f.read().format(schema=instances[0].get_system_prompt())

    print("Initializing MCTS...")
    mcts = MCTS(llm, db_client, evaluator, system_prompt, initial_state, version=2, formatter=OutputOnlyFormatter(planning=True))

    print("Starting MCTS search...")
    best_programs = await mcts.search(
        n_iterations=100,
        samples_per_iteration=5,
        skip_failures=False,
    )

    print("\nBest programs found:")
    for i, prog in enumerate(best_programs, 1):
        print(f"\nProgram {i} (reward: {prog.value:.2f}):")
        print(f"```python\n{prog.code}\n```")
        print("\nConversation history:")
        for msg in prog.conversation.messages:
            print(f"\n{msg['role'].upper()}:")
            print(msg['content'])

if __name__ == '__main__':
    # run asynchronously
    import asyncio
    asyncio.run(main())
