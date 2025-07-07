import os
import asyncio
from dotenv import load_dotenv
from fle.commons.cluster_ips import get_local_container_ips
from fle.commons.db_client import DBClient
from fle.eval.algorithms.mcts import MCTSFactory
from fle.eval.open.plots.run_results import RunResults
from fle.env import FactorioInstance
import concurrent.futures
from typing import List, Tuple

os.environ.update({"FORCE_COLOR": "1", "TERM": "xterm-256color"})
load_dotenv()


def create_factorio_instances() -> List[FactorioInstance]:
    def init_instance(params: Tuple[str, int, int]) -> FactorioInstance:
        ip, udp_port, tcp_port = params
        return FactorioInstance(
            address=ip,
            tcp_port=tcp_port,
            bounding_box=200,
            fast=True,
            cache_scripts=False,
            inventory={},
        )

    ips, udp_ports, tcp_ports = get_local_container_ips()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return list(executor.map(init_instance, zip(ips, udp_ports, tcp_ports)))


SYSTEM_PROMPT = """
You are an agent designed to operate within FactoryEnv, a novel evaluation framework built on the game Factorio, with capabilities in long-horizon planning, spatial reasoning, and systematic automation. 

You interact with the environment through Python program synthesis, using any of the API's 28 core methods below.

The environment behaves like an interactive shell, with the user responses representing the STDOUT of the REPL, and your messages acting as the Python programs to be executed. 

To play the game, consider the conversation history to better understand the changes that are happening to the environment and your inventory. 

Think extensively step-by-step (in Python docstrings / comments ONLY) to first plan your algorithm, reasoning over available entities and your inventory, before writing clean code to execute it. Everything you write MUST be valid Python - either as code or as docstring comments. Any text that is not syntactically valid Python will be rejected.

Leave empty spaces (double \\n) between steps in your program:
```
# comment goes here
code_goes_here...

...
```
 
Use assert statements to self-verify your beliefs against the environment, with specific and parameterised assertion messages.

Your reward in the environment is proportional to the resources you create. This means you should focus on generating items through automation, as this allows greater scale than getting them manually.

Always consider the most profitable next task, what entities are needed for the task, what entities exist in the game (in different entity inventories or in your inventory), what entities are you missing for the task. Fix errors as they occur, and set yourself NEW objectives when you finish your existing one.

Don't repeat your previous steps - just continue from where you left off to build the largest automated system possible.

Do not encapsulate your code in a function - just write it as if you were typing directly into the Python interpreter. NEVER write <LINES X-Y CUT/> - as this is a processing step applied to the conversational history - it represents code.

You are now ready to begin playing FactoryEnv! Good luck!
"""

with open("../TEST_PROMPT.md", "r") as f:
    TEST_PROMPT = f.read()


async def main():
    try:
        db_client = DBClient(
            max_conversation_length=40,
            host=os.getenv("SKILLS_DB_HOST"),
            port=os.getenv("SKILLS_DB_PORT"),
            dbname=os.getenv("SKILLS_DB_NAME"),
            user=os.getenv("SKILLS_DB_USER"),
            password=os.getenv("SKILLS_DB_PASSWORD"),
        )
    except Exception:
        print(
            "\033[91mError connecting to the database. Please check your credentials and try again.\033[91m"
        )
        return

    # Get largest version from DB for initialisation purposes. If no versions exist, start at 0.
    largest_version_to_date = await db_client.get_largest_version()

    # Initialize components
    try:
        instances = create_factorio_instances()
        for instance in instances:
            instance.speed(10)  # Speed up the game for faster evaluation
    except Exception:
        print(
            "\033[91mError initialising Factorio instances. Are the docker containers running, and have they been activated?\033[91m"
        )
        return

    prompt = (
        SYSTEM_PROMPT
        + "\n\n"
        + instances[0].get_system_prompt()
        + "\n\nExamples:\n```\n"
        + TEST_PROMPT
        + "\n```"
    )

    # Get configuration from CLI/interactive prompts
    factory = MCTSFactory()
    mcts_config, sampler_config = factory.get_config_from_cli(
        default_version=largest_version_to_date + 1
    )

    mcts_config.system_prompt = prompt

    # Initialize factory singleton
    factory.initialize(
        instances, db_client, mcts_config, sampler_config
    )  # api_factory, config)

    # Create MCTS instance
    mcts = factory.create_mcts(mcts_config)

    # Run search
    print("Starting MCTS search...")
    await mcts.search(n_iterations=1000, skip_failures=mcts_config.skip_failures)

    run = RunResults(version=mcts_config.version, db_client=db_client)
    run.save_plots()


if __name__ == "__main__":
    asyncio.get_event_loop().set_debug(True)
    asyncio.run(main())
