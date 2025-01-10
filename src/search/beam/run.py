from llm_factory import LLMFactory
from search.beam.beam_search import ParallelBeamSearch, ParallelBeamConfig

import os
import asyncio
from dotenv import load_dotenv
from cluster.local.cluster_ips import get_local_container_ips
from search.db_client import DBClient
from factorio_instance import FactorioInstance
import concurrent.futures
from typing import List, Tuple

from search.model.game_state import GameState

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


SYSTEM_PROMPT = \
    """
    You are an agent designed to operate within FactoryEnv, a novel evaluation framework built on the game Factorio, with capabilities in long-horizon planning, spatial reasoning, and systematic automation. 
    
    You interact with the environment through Python program synthesis, using any of the API's 28 core methods below.
    
    The environment behaves like an interactive shell, with the user responses representing the STDOUT of the REPL, and your messages acting as the Python programs to be executed. 
    
    To play the game, consider the conversation history to better understand the changes that are happening to the environment and your inventory. 
    
    Think extensively step-by-step (in Python docstrings / comments ONLY) to first plan your algorithm, reasoning over available entities and your inventory, before writing clean code to execute it. Everything you write MUST be valid Python - either as code or as docstring comments. Any text that is not syntactically valid Python will be rejected.
    
    Use assert statements to self-verify your beliefs against the environment, with specific and parameterised assertion messages.
    
    Your reward in the environment is proportional to the resources you create. This means you should focus on generating items through automation, as this allows greater scale than getting them manually.
    
    Always consider the most profitable next task, what entities are needed for the task, what entities exist in the game (in different entity inventories or in your inventory), what entities are you missing for the task. Fix errors as they occur, and set yourself NEW objectives when you finish your existing one.
    
    Don't repeat your previous steps - just continue from where you left off to build the largest automated system possible.
    
    Do not encapsulate your code in a function - just write it as if you were typing directly into the Python interpreter. NEVER write <LINES X-Y CUT/> - as this is a processing step applied to the conversational history - it represents code.
    
    You are now ready to begin playing FactoryEnv! Good luck!
    """

OBSERVATION_SPACE = \
   """
    ```errors
    Error: 1: ("Initial Inventory: {'stone-furnace': 2, 'coal': 50, 'stone': 1610, 'iron-ore': 50, 'iron-gear-wheel': 31}",)
    10: ("Error occurred in the following lines:  Line 51: insert_item(Prototype.Coal, pos, 25) AssertionError: The second argument must be an Entity or EntityGroup, you passed in a <class 'factorio_entities.Position'>",)
    ```
    
    This response indicates that an error has occurred at line 10, and that all preceding lines executed successfully. 
    
    ```entities
    23: ('Resource collection, smelting, and crafting completed successfully.',)
    78: ('Entities on the map: [Furnace(fuel={'coal': 49}, name='stone-furnace', position=Position(x=0.0, y=0.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=[], status=<EntityStatus.WORKING: 'working'>, furnace_source={'iron-ore': 12}, furnace_result={'iron-plate': 27}), Furnace(fuel={'coal': 49}, name='stone-furnace', position=Position(x=2.0, y=0.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=[], status=<EntityStatus.WORKING: 'working'>, furnace_source={'iron-ore': 12}, furnace_result={'iron-plate': 25}), Furnace(fuel={'coal': 23}, name='stone-furnace', position=Position(x=4.0, y=4.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=['no ingredients to smelt'], status=<EntityStatus.NO_INGREDIENTS: 'no_ingredients'>, furnace_source={}, furnace_result={'iron-plate': 20}), Furnace(fuel={'coal': 23}, name='stone-furnace', position=Position(x=6.0, y=4.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=['no ingredients to smelt'], status=<EntityStatus.NO_INGREDIENTS: 'no_ingredients'>, furnace_source={}, furnace_result={'iron-plate': 20})]',)
    ```
    
    This response indicates that `print(get_entities())` was called at line 78 to get state of the entities on the map. There are four stone furnaces, two of which are working and two of which have no ingredients to smelt. Non-working entities can be determined by checking the `warnings` and `status` fields.
    
   """

with open("../MANUAL.md", "r") as f:
    MANUAL = f.read()


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



    # Initialize components
    try:
        instances = create_factorio_instances()
        for instance in instances:
            instance.speed(10)  # Speed up the game for faster evaluation
    except Exception as e:
        print(
            "\033[91mError initialising Factorio instances. Are the docker containers running, and have they been activated?\033[91m")
        return
    API_SCHEMA = instances[0].get_system_prompt()
    prompt = SYSTEM_PROMPT + '\n\n' + API_SCHEMA + '\n\nObservations:\n' + OBSERVATION_SPACE + '\n\n' + MANUAL + '\n```'
    initial_state = GameState.from_instance(instances[0])

    for model in ['claude-3-5-sonnet-20241022']:
        # Get largest version from DB for initialisation purposes. If no versions exist, start at 0.
        largest_version_to_date = await db_client.get_largest_version()

        config = ParallelBeamConfig(
            beam_width=4,  # 4 parallel groups = beam width of 4
            expansion_factor=4,  # Generate 4 candidates per position
            system_prompt=prompt,
            initial_state=initial_state,
            model=model,  # Claude model
            beam_kwargs={
                'error_penalty': 10,
                'logit_bias': {
                    "15714": -100,  # 'LINE'
                    "193595": -100,  # 'LINES'
                    "145968": -100,  # ' CUT'
                    "27": -100,  # '<'
                    "20225": -100,  # '/>'
                    "7032": -100  # 'while'
                }
            }
        )
        #model = 'claude-3-5-sonnet-20241022'
        #model = 'gpt-4o'
        llm_factory = LLMFactory(model=model)
        parallel_beam = ParallelBeamSearch(
            instances=instances,
            db_client=db_client,
            llm_factory=llm_factory,
            config=config,
            version=largest_version_to_date+1,
            version_description=f"model:{model}\ntype:beam"
        )

        # Run search
        await parallel_beam.search(n_iterations=32)


if __name__ == '__main__':
    asyncio.get_event_loop().set_debug(True)
    asyncio.run(main())
