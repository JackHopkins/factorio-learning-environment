import json
import os

from eval.algorithms.mcts import (
    KLDiversityAchievementSampler,
    ParallelMCTSConfig,
    ParallelPlanningMCTS,
    PlanningMCTS,
)
from eval.open.auto_curriculum.plan_sampler import PlanSampler

from fle.commons.models.conversation import Conversation
from fle.commons.models.message import Message
from fle.commons.models.program import Program

os.environ["FORCE_COLOR"] = "1"
os.environ["TERM"] = "xterm-256color"

import concurrent
import os
from typing import List, Tuple

from fle.agents.formatters.conversation_formatter_abc import PLANNING_ADDITION_PROMPT
from fle.agents.llm.api_factory import APIFactory
from fle.commons.cluster_ips import get_local_container_ips
from dotenv import load_dotenv
from rich import print

from fle.commons.db_client import DBClient
from fle.commons.models.game_state import GameState
from fle.env import FactorioInstance

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
        inventory={},
    )


def create_factorio_instances() -> List[FactorioInstance]:
    """Create Factorio instances in parallel from local servers"""

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


async def get_seed_programs(
    mcts: PlanningMCTS,
    plan_sampler: "PlanSampler",
    n_seeds: int = 100,
) -> List[Program]:
    existing_rewards = await mcts.db.get_all_program_rewards(version=mcts.version)
    # filter out rewards < 0
    existing_rewards = list(filter(lambda x: x >= 0, existing_rewards))
    default_reward = (
        (max(existing_rewards) - min(existing_rewards)) / 2
        if existing_rewards
        else 10.0
    )
    seeded_programs: List[Program] = []
    instance = mcts.evaluator.instances[0]

    # Get all available scenarios
    scenarios = [
        f
        for f in os.listdir(plan_sampler.starting_scenarios_folder)
        if os.path.isdir(os.path.join(plan_sampler.starting_scenarios_folder, f))
    ]

    seeds_per_scenario = n_seeds // len(scenarios)
    remaining_seeds = n_seeds % len(scenarios)

    for scenario in scenarios:
        num_samples = seeds_per_scenario + (1 if remaining_seeds > 0 else 0)
        remaining_seeds -= 1

        for _ in range(num_samples):
            game_state = plan_sampler.get_game_state(instance, scenario)
            if not game_state:
                continue

            objective, response = plan_sampler(instance, game_state)

            if len(objective) < 100:
                continue

            conversation = Conversation(
                messages=[
                    Message(role="system", content=mcts.system_prompt),
                    Message(
                        role="user",
                        content=f"Inventory: {json.dumps(game_state.inventories[0].__dict__)}\n\n{PLANNING_ADDITION_PROMPT}",
                    ),
                    Message(role="assistant", content=objective),
                ]
            )
            try:
                messages = conversation.model_dump()["messages"]
            except:
                messages = conversation.dict()["messages"]
            if not objective.strip().startswith('"""'):
                objective = '"""\n' + objective

            program = Program(
                id=hash((objective, json.dumps(messages))),
                code=objective,
                conversation=conversation,
                value=default_reward,
                state=game_state,
                version=mcts.version,
                version_description=mcts.version_description,
                token_usage=response.usage.total_tokens
                if hasattr(response, "usage")
                else None,
                completion_token_usage=response.usage.completion_tokens
                if hasattr(response, "usage")
                else None,
                prompt_token_usage=response.usage.prompt_tokens
                if hasattr(response, "usage")
                else None,
            )
            seeded_programs.append(program)

    return seeded_programs


async def main():
    step_executor_model_path = (
        "ft:gpt-4o-2024-08-06:paperplane-ai:fact-instruct-1:ATSVGf4d:ckpt-step-214"
    )
    planner_model = "claude-3-5-sonnet-20241022"
    objective_model = (
        "ft:gpt-4o-2024-08-06:paperplane-ai:fact-self-gen-planning:AQzcPI91"
    )
    step_executor_prompt_path = (
        r"../../../data/prompts/bottoms_up_prompts/finetuning_prompts/step_supervised"
    )
    step_generator_prompt_path = (
        r"../../../data/prompts/bottoms_up_prompts/finetuning_prompts/step_generator"
    )
    executor_plan_prompt_path = (
        r"../../../data/prompts/bottoms_up_prompts/finetuning_prompts/executor_plan"
    )
    step_judge_prompt_path = (
        r"../../../data/prompts/bottoms_up_prompts/finetuning_prompts/step_judge"
    )
    objective_model_prompt_path = r"../../../data/prompts/bottoms_up_prompts/finetuning_prompts/system_message_policy_self_gen.md"
    version = 101
    version = 43
    version_description = (
        "KLD Diversity Sampling / Scratch / Planning MCTS / Errors not saved"
    )

    # Initialize components
    llm = APIFactory(step_executor_model_path)
    db_client = DBClient(
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD"),
    )

    instances = create_factorio_instances()
    for instance in instances:
        instance.speed(10)  # Set the game speed to 10x normal speed for faster testing

    # Initialize FactorioEvaluator with the list of instances

    initial_state = GameState.from_instance(instances[0])

    # load from prompts/bottoms_up_prompts/system_message_policy_self_gen into string
    with open(objective_model_prompt_path, "r") as f:
        system_prompt = f.read().format(schema=instances[0].get_system_prompt())

    print("Initializing MCTS...")
    # Sampler
    sampler = KLDiversityAchievementSampler(db_client)

    config = ParallelMCTSConfig(
        n_parallel=8,
        mcts_class=PlanningMCTS,
        sampler=sampler,
        system_prompt=system_prompt,
        initial_state=initial_state,
        max_steps_per_objective=8,
        number_of_steps_for_judge=3,
        mcts_kwargs={
            "planning_model": planner_model,
            "executor_model": step_executor_model_path,
            "objective_model": objective_model,
            "step_executor_prompt_path": step_executor_prompt_path,
            "step_generator_prompt_path": step_generator_prompt_path,
            "step_judge_prompt_path": step_judge_prompt_path,
            "example_plan_prompt_path": executor_plan_prompt_path,
            "system_prompt": system_prompt,
            "initial_state": initial_state,
        },
    )

    mcts = ParallelPlanningMCTS(
        instances,
        db_client,
        llm,
        config,
        version=version,
        version_description=version_description,
    )

    # sampler = PlanSampler(objective_model, objective_model_prompt_path, starting_scenario_folder)

    # print("Sampling seed scenarios...")
    # seeded_programs = await get_seed_programs(mcts, sampler, n_seeds=nr_of_seeded_programs)
    # for program in seeded_programs:
    #    await db_client.create_program(program)

    print("Starting MCTS search...")
    await mcts.search(
        n_iterations=1000,
        skip_failures=False,
    )


if __name__ == "__main__":
    # run asynchronously
    import asyncio

    asyncio.run(main())
