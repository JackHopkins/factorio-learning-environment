import argparse
import asyncio
import concurrent.futures
import os
from typing import List, Tuple

from fle.commons.cluster_ips import get_local_container_ips
from dotenv import load_dotenv

from fle.agents.formatters import RecursiveFormatter
from fle.agents.llm.api_factory import APIFactory
from fle.commons.db_client import DBClient
from fle.commons.models import GameState
from fle.env import FactorioInstance

from .beam_search import ParallelBeamConfig, ParallelBeamSearch

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
            all_technologies_researched=False,
        )

    ips, udp_ports, tcp_ports = get_local_container_ips()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return list(executor.map(init_instance, zip(ips, udp_ports, tcp_ports)))


SYSTEM_PROMPT_OLD = """
    You are an agent designed to operate within FactoryEnv, a novel evaluation framework built on the game Factorio, with capabilities in long-horizon planning, spatial reasoning, and systematic automation. 
    
    You interact with the environment through Python program synthesis, using any of the API's 28 core methods below.
    
    The environment behaves like an interactive shell, with the user responses representing the STDOUT of the REPL, and your messages acting as the Python programs to be executed. 
    
    To play the game, consider the conversation history to better understand the changes that are happening to the environment and your inventory. 
    
    Think extensively step-by-step (in Python docstrings / comments ONLY) to first plan your algorithm, reasoning over available entities and your inventory, before writing clean code to execute it. Everything you write MUST be valid Python - either as code or as docstring comments. Any text that is not syntactically valid Python will be rejected.
    
    Use assert statements to self-verify your beliefs against the environment, with specific and parameterised assertion messages.
    
    Your reward in the environment is proportional to the resources you create. This means you should focus on generating items through automation, as this allows greater scale than getting them manually.
    
    Always consider the most profitable next task, what entities are needed for the task, what entities exist in the game (in different entity inventories or in your inventory), what entities are you missing for the task. Fix errors as they occur, and set yourself NEW objectives when you finish your existing one.
    
    DON'T REPEAT YOUR PREVIOUS STEPS - just continue from where you left off to build the largest automated system possible. If there was a error previously, do not repeat your last lines - as this will alter the game state unnecessarily.
    
    Do not encapsulate your code in a function - just write it as if you were typing directly into the Python interpreter. NEVER write <LINES X-Y CUT/> - as this is a processing step applied to the conversational history - it represents code.
    
    You are now ready to begin playing FactoryEnv! Good luck!
    """

SYSTEM_PROMPT = """
You are an agent designed to operate within FactoryEnv, a novel evaluation framework built on the game Factorio, with capabilities in long-horizon planning, spatial reasoning, and systematic automation. 
You interact with the environment through Python program synthesis, using any of the API's 28 core methods below.
The environment behaves like an interactive shell, with the user responses representing the STDOUT of the REPL, and your messages acting as the Python programs to be executed. 
To play the game, consider the conversation history to better understand the changes that are happening to the environment and your inventory. You must identify the best and most useful and profitable next step in the game that advances you in the game and carry it out. Fix errors as they occur, and set yourself NEW objectives when you finish your existing one.
Follow this structure: The first stage is PLANNING: Think extensively step-by-step in natural language to first plan your next step, reasoning over available entities and your inventory.
In the planning stage, follow this structure: 1) Was there an error? If yes, then what was the problem 2) What is the best and most useful next step that is of reasonable size, 3) What actions do I need to take for this step 
The second stage is POLICY: create the python policy that carries out the steps you want in the game. Your policy MUST be between two python tags like this: ```python\nYOUR_POLICY_HERE\n```
For example: "I should move to position 0, 0 ```python move_to(Position(x=0, y=0))```"
IMPORTANT: Always create small and modular policies that are easy to debug. Small and modular policies are easy to carry out, debug when they arent working and understand. They also allow you to make small changes to the factory without breaking the entire system.
Always log the important areas when using small policies as this will help to use this information when creating the next policy
Use assert statements to self-verify your beliefs against the environment, with specific and parameterised assertion messages.
If you dont know what an entity is for in the map, assume it is part of a working automatic structure. Be careful not to break any working automatic structures
Think what entities are needed for the step, what entities exist in the game (in different entity inventories or in your inventory), what entities are you missing for the task.
DON'T REPEAT YOUR PREVIOUS STEPS - just continue from where you left off. Take into account what was the lasdt action that was executed and continue from there. If there was a error previously, do not repeat your last lines - as this will alter the game state unnecessarily. Fix errors as they occur.
Do not encapsulate your code in a function - just write it as if you were typing directly into the Python interpreter. NEVER write <LINES X-Y CUT/> - as this is a processing step applied to the conversational history - it represents code.
You are now ready to begin playing FactoryEnv! Good luck!
"""

OBSERVATION_SPACE = """
You observe the STDOUT and STDERR of your program.

```stderr
Error: 1: ("Initial Inventory: {'stone-furnace': 2, 'coal': 50, 'stone': 1610, 'iron-ore': 50, 'iron-gear-wheel': 31}",)
10: ("Error occurred in the following lines:  Line 51: insert_item(Prototype.Coal, pos, 25) AssertionError: The second argument must be an Entity or EntityGroup, you passed in a <class 'factorio_entities.Position'>",)
```
This response indicates that an error has occurred at line 10, and that all preceding lines executed successfully. Attempt to fix the error at line 10, and continue with the next step.

```stdout
23: ('Resource collection, smelting, and crafting completed successfully.',)
78: ('Entities on the map: [Furnace(fuel={'coal': 49}, name='stone-furnace', position=Position(x=0.0, y=0.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=[], status=<EntityStatus.WORKING: 'working'>, furnace_source={'iron-ore': 12}, furnace_result={'iron-plate': 27}), Furnace(fuel={'coal': 49}, name='stone-furnace', position=Position(x=2.0, y=0.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=[], status=<EntityStatus.WORKING: 'working'>, furnace_source={'iron-ore': 12}, furnace_result={'iron-plate': 25}), Furnace(fuel={'coal': 23}, name='stone-furnace', position=Position(x=4.0, y=4.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=['no ingredients to smelt'], status=<EntityStatus.NO_INGREDIENTS: 'no_ingredients'>, furnace_source={}, furnace_result={'iron-plate': 20}), Furnace(fuel={'coal': 23}, name='stone-furnace', position=Position(x=6.0, y=4.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=['no ingredients to smelt'], status=<EntityStatus.NO_INGREDIENTS: 'no_ingredients'>, furnace_source={}, furnace_result={'iron-plate': 20})]',)
```

This response indicates that `print(get_entities())` was called at line 78 to get state of the entities on the map. There are four stone furnaces, two of which are working and two of which have no ingredients to smelt. Non-working entities can be determined by checking the `warnings` and `status` fields.
"""

with open("../MANUAL_short.md", "r") as f:
    MANUAL = f.read()

HISTORY_SUMMARIZATION_INSTRUCTIONS = f"""
{MANUAL}

# Instructions

We are refreshing the context now.

Review the code interactions you have had with the Factorio REPL Environment, and the responses returned by the environment which are in the user messages.
 
Summarize what you _attempted_ to achieve, any errors that occurred, and the outcomes of your actions.

Provide specific tips and logic patterns (and antipatterns) you think would help you avoid these specific errors in future, using the above manual and API schema as a reference. 
 
Write in markdown. Do NOT include any code snippets in your response.
"""


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
    instances = instances[-4:]
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
    initial_state = GameState.from_instance(instances[0])

    # Add argument parsing for version
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-version", type=int, help="Version to resume from")
    resume_version = 453  # args.resume_version

    # Get version to use
    # Get version to use
    if resume_version is not None:
        version_to_use = resume_version
        if not await db_client.version_exists(version_to_use):
            print(f"Version {version_to_use} does not exist in database")
            return

        # Get beam heads for resuming
        beam_width = 4  # Should match config
        resume_heads = await db_client.get_beam_heads(version_to_use, beam_width)
        if not resume_heads:
            print(f"No valid beam heads found for version {version_to_use}")
            return

        # Ensure all depths are the same for the beam heads
        depth = resume_heads[0].depth
        for prog in resume_heads:
            assert prog.depth == depth, (
                "All beam head depths must be the same in order to resume."
            )

        current_depth = depth
    else:
        version_to_use = await db_client.get_largest_version() + 1
        resume_heads = None
        current_depth = 0

    for model in [
        "gpt-4o",
        "deepseek-chat",
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "gpt-4-turbo",
    ]:  # [ 'gpt-4o', 'claude-3-5-sonnet-20241022', 'gpt-4o-mini']:#['gemini-2.0-flash-exp']: #['gpt-4o-mini']:#['deepseek-chat']:#['gemini-2.0-flash-exp']: #['meta-llama/Llama-3.3-70B-Instruct-Turbo']:#['gemini-2.0-flash-exp']:#['gpt-4o']:#['claude-3-5-sonnet-20241022']:
        config = ParallelBeamConfig(
            beam_width=4,  # 4 parallel groups = beam width of 4
            expansion_factor=1,  # Generate 4 candidates per position
            system_prompt=prompt,
            initial_state=initial_state,
            model=model,
            beam_kwargs={
                "error_penalty": 0,
                #'frequency_penalty': 0.25
            },
        )
        # model = 'claude-3-5-sonnet-20241022'
        # model = 'gpt-4o'
        # current_depth = 0#await db_client.get_largest_depth_in_version(largest_version_to_date)

        api_factory = APIFactory(model=model)

        formatter = RecursiveFormatter(
            chunk_size=32,
            api_factory=api_factory,
            cache_dir=".fle/summary_cache",
            summary_instructions=API_SCHEMA + HISTORY_SUMMARIZATION_INSTRUCTIONS,
            summarize_history=False,  # Summarizing history seems to make it worse. We clip instead.
        )

        parallel_beam = ParallelBeamSearch(
            instances=instances,
            db_client=db_client,
            api_factory=api_factory,
            config=config,
            version=version_to_use,
            version_description=f"model:{model}\ntype:beam",
            current_depth=current_depth,
            formatter=formatter,
            base_port=instances[0].tcp_port,
            resume_version=resume_version,
            resume_heads=resume_heads,
        )

        if resume_version:
            await parallel_beam._verify_version_compatibility()

        # Run search
        await parallel_beam.search(n_iterations=512)


if __name__ == "__main__":
    asyncio.get_event_loop().set_debug(True)
    asyncio.run(main())
