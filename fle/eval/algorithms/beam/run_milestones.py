import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from fle.agents.llm.api_factory import APIFactory
from fle.commons.cluster_ips import get_local_container_ips
from dotenv import load_dotenv

from fle.agents.formatters import RecursiveReportFormatter
from fle.commons.db_client import DBClient
from fle.env import FactorioInstance, GameState
from fle.eval.algorithms.beam import MilestonesBeamSearchExecutor
from fle.eval.algorithms.mcts import SupervisedExecutorConfig
from fle.eval.tasks.throughput_task import (
    LAB_PLAY_POPULATED_STARTING_INVENTORY,
    ThroughputTask,
)

os.environ.update({"FORCE_COLOR": "1", "TERM": "xterm-256color"})
load_dotenv()


def plot_throughput_timeseries_mean(input_data, file_path, task):
    throughput_entity = task.throughput_entity
    input_data = input_data["results"][0]
    data = {}
    for key, value in input_data.items():
        values = [
            x["holdout_achievements"]["dynamic"].get(f"{throughput_entity}", 0)
            for x in value
        ]
        data[key] = values

    # Convert the data into a numpy array for easier calculation
    values = np.array(list(data.values()))

    # Calculate mean and standard deviation across series
    mean = np.mean(values, axis=0)
    std = np.std(values, axis=0)

    # Create time points (x-axis)
    time_points = np.arange(len(mean))

    # Create the plot
    plt.figure(figsize=(10, 6))

    # Plot individual series
    # for series_name, series_data in data.items():
    #    plt.plot(time_points, series_data, 'o-', alpha=0.3, label=series_name)

    # Plot mean
    plt.plot(time_points, mean, "k-", linewidth=2, label="Mean")

    # Plot confidence bands (mean ± 2*std)
    plt.fill_between(
        time_points,
        mean - 2 * std,
        mean + 2 * std,
        color="gray",
        alpha=0.2,
        label="±2 STD",
    )

    # Customize the plot
    plt.title(f"{throughput_entity} throughput ")
    plt.xlabel("Steps")
    plt.ylabel(f"{throughput_entity}/20s")
    plt.grid(True, alpha=0.3)

    # Set y-axis to start at 0
    plt.ylim(bottom=0)

    # Show the plot
    plt.tight_layout()
    plt.savefig(file_path)


def plot_throughput_timeseries(data, file_path, task):
    throughput_entity = task.throughput_entity
    data = data["results"][0]
    data_to_plot = {}
    for key, value in data.items():
        values = [
            x["holdout_achievements"]["dynamic"].get(throughput_entity, 0)
            for x in value
        ]
        data_to_plot[key] = values

    # Create a figure and axis
    plt.figure(figsize=(10, 6))

    # Plot each series
    for series_name, values in data_to_plot.items():
        plt.plot(values, label=series_name, marker="o")

    # Customize the plot
    plt.title(f"{throughput_entity} throughput ")
    plt.xlabel("Steps")
    plt.ylabel(f"{throughput_entity}/20s")
    plt.legend()
    plt.grid(True)

    # save the plot to the file path
    plt.savefig(file_path)


def initiate_executor(
    config, instances, version, db_client, version_description, api_factory, formatter
):
    executor = config["executor"](
        instances=instances,
        version=version,
        db_client=db_client,
        version_description=version_description,
        api_factory=api_factory,
        config=config["config"],
        formatter=formatter,
    )
    return executor


def initiate_task_configs(input_task):
    if input_task["task_type"] == "populated_lab_play":
        input_task["config"]["starting_inventory"] = (
            LAB_PLAY_POPULATED_STARTING_INVENTORY
        )
        return ThroughputTask(**input_task["config"])
    task_config = ThroughputTask(**input_task["config"])
    return task_config


def initialise_starting_state(instance, task, reset_game_state):
    # reset the instance
    instance.reset(reset_game_state)
    # reset the game state but with the new inventory
    task.setup(instance)
    return task


def create_factorio_instance(instance_id: int) -> FactorioInstance:
    """Create a single Factorio instance"""
    ips, udp_ports, tcp_ports = get_local_container_ips()

    instance = FactorioInstance(
        address=ips[instance_id],
        tcp_port=tcp_ports[instance_id],
        bounding_box=200,
        fast=True,
        cache_scripts=True,
        inventory={},
        all_technologies_researched=True,
    )
    instance.speed(10)
    return instance


SYSTEM_PROMPT = """You are an agent designed to operate within FactoryEnv, a novel evaluation framework built on the game Factorio, with capabilities in long-horizon planning, spatial reasoning, and systematic automation. 
    
    You interact with the environment through Python program synthesis, using any of the API's 28 core methods below.
    
    The environment behaves like an interactive shell, with the user responses representing the STDOUT of the REPL, and your messages acting as the Python programs to be executed. 
    
    You are given a goal by the user. You must create a factory that automatically creates a target entity. You are given the entity for which you need to create a factory for. You are also given the target throughput that the factory must achieve

    To play the game, consider the conversation history to better understand the changes that are happening to the environment and your inventory. 
    
    Follow this structure: The first stage is PLANNING: Think extensively step-by-step in natural language to first plan your next step, reasoning over available entities and your inventory.
    
    In the planning stage, follow this structure: 1) Was there an error? If yes, then what was the problem? Extensively analyse potential causes of the error and bring out in bulletpoints the candidate causes of the error 2) Thoroughly analysing your previous steps, what is the best next step 3) What actions do I need to take for this step 
    
    Be thorough and detailed in your analysis. Think in terms of factory components and topology. Think extensively what entities are needed and how they are set up in a spatial manner.

    Think what entities are needed for the step, what entities exist in the game (in different entity inventories or in your inventory), what entities are you missing for the task.
    
    When you see errors, try out different solutions. Do not repeat the same solution as that is likely going to fail again.The second stage is POLICY: create the python policy that carries out the steps you want in the game. Your policy MUST be between two python tags like this: ```python\nYOUR_POLICY_HERE\n```

    For example: "I should move to position 0, 0 ```python move_to(Position(x=0, y=0))```"
    
    IMPORTANT: Always create small and modular policies that are easy to debug. For instance, if you want to create a resource mine, policy 1) Put down drill line, policy 2) Put down furnace line with inserters, policy 3) Connect drill line with furnace line and check that the factory works

    Small and modular policies are easy to carry out, debug when they arent working and understand. They also allow you to make small changes to the factory without breaking the entire system.

    Always log the important areas when using small policies as this will help to use this information when creating the next policy

    Use assert statements to self-verify your beliefs against the environment, with specific and parameterised assertion messages.
    
    You must create an AUTOMATIC factory that automatically creates a target entity by itself. You are given the entity for which you need to create a factory for. You are also given the target throughput that the factory must achieve
    
    After each step the throughput of the factory is evaluated during 60 seconds of worktime and the results are supplied to you in the response. If you have achieved the target throughput, make sure to fuel the factory and make small improvements but do not break the factory.
    
    DON'T REPEAT YOUR PREVIOUS STEPS - just continue from where you left off. Take into account what was the last action that was executed and continue from there. If there was a error previously, do not repeat your last lines - as this will alter the game state unnecessarily. Fix errors as they occur.
    
    Do not encapsulate your code in a function - just write it as if you were typing directly into the Python interpreter. NEVER write <LINES X-Y CUT/> - as this is a processing step applied to the conversational history - it represents code.
    
    You are now ready to begin playing FactoryEnv! Good luck!"""

OBSERVATION_SPACE = """You observe the STDOUT and STDERR of your program.
   
    ```stderr
    Error: 1: ("Initial Inventory: {'stone-furnace': 2, 'coal': 50, 'stone': 1610, 'iron-ore': 50, 'iron-gear-wheel': 31}",)
    10: ("Error occurred in the following lines:  Line 51: insert_item(Prototype.Coal, pos, 25) AssertionError: The second argument must be an Entity or EntityGroup, you passed in a <class 'factorio_entities.Position'>",)
    ```
    This response indicates that an error has occurred at line 10, and that all preceding lines executed successfully. Attempt to fix the error at line 10, and continue with the next step.
    
    ```stdout
    23: ('Resource collection, smelting, and crafting completed successfully.',)
    78: ('Entities on the map: [Furnace(fuel={'coal': 49}, name='stone-furnace', position=Position(x=0.0, y=0.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=[], status=<EntityStatus.WORKING: 'working'>, furnace_source={'iron-ore': 12}, furnace_result={'iron-plate': 27}), Furnace(fuel={'coal': 49}, name='stone-furnace', position=Position(x=2.0, y=0.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=[], status=<EntityStatus.WORKING: 'working'>, furnace_source={'iron-ore': 12}, furnace_result={'iron-plate': 25}), Furnace(fuel={'coal': 23}, name='stone-furnace', position=Position(x=4.0, y=4.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=['no ingredients to smelt'], status=<EntityStatus.NO_INGREDIENTS: 'no_ingredients'>, furnace_source={}, furnace_result={'iron-plate': 20}), Furnace(fuel={'coal': 23}, name='stone-furnace', position=Position(x=6.0, y=4.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=['no ingredients to smelt'], status=<EntityStatus.NO_INGREDIENTS: 'no_ingredients'>, furnace_source={}, furnace_result={'iron-plate': 20})]',)
    ```
    
    This response indicates that `print(get_entities())` was called at line 78 to get state of the entities on the map. There are four stone furnaces, two of which are working and two of which have no ingredients to smelt. Non-working entities can be determined by checking the `warnings` and `status` fields."""

path = Path(__file__).parent.parent / "MANUAL_short.md"
with open(path, "r") as f:
    MANUAL = f.read()


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
        instances = [create_factorio_instance(i) for i in range(4)]
        # for instance in instances:
        #    instance.speed(10)  # Speed up the game for faster evaluation
    except Exception:
        print(
            "\033[91mError initialising Factorio instances. Are the docker containers running, and have they been activated?\033[91m"
        )
        return

    API_SCHEMA = instances[0].get_system_prompt()
    prompt = (
        SYSTEM_PROMPT
        + "\n\n"
        + API_SCHEMA
        + "\n\nObservations:\n"
        + OBSERVATION_SPACE
        + "\n\n"
        + MANUAL
        + "\n```"
    )
    zero_state = GameState.from_instance(instances[0])

    model_to_evaluate = "claude-3-5-sonnet-20241022"
    # model_to_evaluate = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    # model_to_evaluate = "Qwen/Qwen2.5-72B-Instruct-Turbo"
    # model_to_evaluate = "gpt-4o"
    # model_to_evaluate = 'gpt-4o-mini-2024-07-18'
    # model_to_evaluate = "o1-mini-2024-09-12"
    # model_to_evaluate = 'deepseek-chat'
    version = 332  # 120 and 121 was the last version before this change
    api_factory = APIFactory(model=model_to_evaluate)
    version_description = "eval_agentic_supervised"

    task_folder = Path(__file__).parent.parent.parent / "tasks" / "task_definitions"
    result_path = Path(__file__).parent.parent.parent / "tasks" / "supervised_results"

    tasks = ["steel_plate_throughput_16"]
    search_type = "beam_supervised"
    search_iterations = 1

    formatter = RecursiveReportFormatter(
        chunk_size=128,
        llm_call=api_factory.acall,
        cache_dir="./summary_cache",
    )
    configs = {
        "beam_supervised": {
            "config": SupervisedExecutorConfig(
                n_parallel=1,
                model_to_evaluate=model_to_evaluate,
                supervised_kwargs={"system_prompt": prompt},
            ),
            "executor": MilestonesBeamSearchExecutor,
        }
    }

    # get the current date and time
    now = datetime.now()
    dt_string = now.strftime("%Y%m%d_%H%M%S")

    save_path = os.path.join(result_path, search_type, model_to_evaluate, dt_string)
    # check if the path exists
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    executor = initiate_executor(
        configs[search_type],
        instances,
        version,
        db_client,
        version_description,
        api_factory,
        formatter,
    )

    for task_key in tasks:
        # read in the input task
        with open(os.path.join(task_folder, f"{task_key}.json"), "r") as f:
            input_task = json.load(f)
        task = initiate_task_configs(input_task)
        task = initialise_starting_state(instances[0], task, zero_state)
        config_dict = {
            "iterations": search_iterations,
            "executor_kwargs": executor.config._to_dict(),
            "task_config": task._to_dict(),
        }
        # save the config dict
        with open(os.path.join(save_path, f"{task_key}_config.json"), "w") as f:
            json.dump(config_dict, f)
        print(f"Starting MCTS search for task {task.task}")
        results = await executor.search_supervised(
            n_iterations=search_iterations,
            skip_failures=False,
            task=task,
            run_id=f"{task_key}_{dt_string}",
        )
        print(f"Task: {task.task} has been completed")
        result_dict = {
            "results": results,
            "starting_inventory": task.starting_inventory,
            "target_entity": task.throughput_entity,
        }
        with open(os.path.join(save_path, f"{task_key}.json"), "w") as f:
            json.dump(result_dict, f)
        plot_throughput_timeseries(
            result_dict, os.path.join(save_path, f"{task_key}_individual.png"), task
        )
        plot_throughput_timeseries_mean(
            result_dict, os.path.join(save_path, f"{task_key}_mean.png"), task
        )
    print("All tasks completed")


if __name__ == "__main__":
    asyncio.get_event_loop().set_debug(True)
    asyncio.run(main())
