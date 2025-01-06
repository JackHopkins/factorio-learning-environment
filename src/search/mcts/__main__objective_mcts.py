import json
import os
import random
import asyncio
import concurrent.futures
from typing import List, Tuple, Dict
from pathlib import Path

from dotenv import load_dotenv
from rich import print

from search.auto_curriculum.plan_sampler import PlanSampler
from search.mcts.blueprint_scenario_sampler import BlueprintScenarioSampler
from search.mcts.chunked_mcts import ChunkedMCTS
from search.model.conversation import Conversation, Message
from search.mcts.objective_mcts import ObjectiveMCTS
from search.mcts.parallel_mcts import ParallelMCTS
from search.mcts.parallel_mcts_config import ParallelMCTSConfig
from search.mcts.conversation_formatter import StructurePreservingFormatter, PLANNING_ADDITION_PROMPT
from search.mcts.db_client import DBClient
from search.model.game_state import GameState
from search.model.program import Program
from search.mcts.samplers.kld_achievement_sampler import KLDiversityAchievementSampler
from factorio_instance import FactorioInstance
from llm_factory import LLMFactory
from cluster.local.cluster_ips import get_local_container_ips

# Configure environment
os.environ.update({
    "FORCE_COLOR": "1",
    "TERM": "xterm-256color"
})

load_dotenv()
#MODEL = "ft:gpt-4o-mini-2024-07-18:paperplane-ai:mcts-pruned-unmasked:AYH6LsSe"
MODEL = "ft:gpt-4o-mini-2024-07-18:paperplane-ai:mcts-pruned-masked:AYIViDdb"

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
            inventory={}
        )

    ips, udp_ports, tcp_ports = get_local_container_ips()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return list(executor.map(init_instance, zip(ips, udp_ports, tcp_ports)))

async def create_seed_programs(
    mcts: ChunkedMCTS,
    plan_sampler: PlanSampler,
    n_seeds: int = 100,
) -> List[Program]:
    """Generate seed programs from scenarios"""
    # Calculate default reward from existing programs
    rewards = await mcts.db.get_all_program_rewards(version=mcts.version)
    rewards = [r for r in rewards if r >= 0]
    default_reward = 10.0

    # Select random scenarios
    scenario_dir = Path(plan_sampler.starting_scenarios_folder)
    scenarios = [f for f in scenario_dir.iterdir() if f.is_dir()]
    selected_scenarios = random.sample(scenarios, min(n_seeds, len(scenarios)))

    seeded_programs = []
    instance = mcts.evaluator.instances[0]

    for scenario in selected_scenarios:
        # Get game state and generate plan
        game_state = plan_sampler.get_game_state(instance, scenario)
        if not game_state:
            continue

        objective, response = plan_sampler(instance, game_state)
        if len(objective) < 100:
            continue

        # Format objective as proper docstring
        objective = f'"""\n{objective.strip()}\n"""'

        # Create conversation context
        conversation = Conversation(messages=[
            Message(role="system", content=mcts.system_prompt),
            Message(role="user", content=f"Starting Inventory: {game_state.inventory.dict()}"),
            Message(role="assistant", content=objective)
        ])

        # Extract token usage
        try:
            token_usage = getattr(response.usage, 'total_tokens', None)
            completion_tokens = getattr(response.usage, 'completion_tokens', response.usage.output_tokens)
            prompt_tokens = getattr(response.usage, 'prompt_tokens', response.usage.input_tokens)
        except AttributeError:
            completion_tokens = response.usage.completion_tokens
            prompt_tokens = response.usage.prompt_tokens
            token_usage = prompt_tokens + completion_tokens

        # Create program
        program = Program(
            id=hash((objective, str(conversation.messages))),
            code=objective,
            conversation=conversation,
            value=default_reward,
            state=game_state,
            version=mcts.version,
            version_description=mcts.version_description,
            token_usage=token_usage,
            completion_token_usage=completion_tokens,
            prompt_token_usage=prompt_tokens,
            model=MODEL
        )
        seeded_programs.append(program)

    return seeded_programs


async def get_seed_programs(
        mcts: ChunkedMCTS,
        plan_sampler: 'PlanSampler',
        n_seeds: int = 100,
) -> List[Program]:
    existing_rewards = await mcts.db.get_all_program_rewards(version=mcts.version)
    # filter out rewards < 0
    existing_rewards = list(filter(lambda x: x >= 0, existing_rewards))
    default_reward = (max(existing_rewards)-min(existing_rewards))/2 if existing_rewards else 10.0
    seeded_programs: List[Program] = []
    instance = mcts.evaluator.instances[0]

    # Get all available scenarios
    scenarios = [f for f in os.listdir(plan_sampler.starting_scenarios_folder)
                 if os.path.isdir(os.path.join(plan_sampler.starting_scenarios_folder, f))]

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

            conversation = Conversation(messages=[
                Message(role="system", content=mcts.system_prompt),
                Message(role="user",
                        content=f"Inventory: {json.dumps(game_state.inventory.__dict__)}\n\n{PLANNING_ADDITION_PROMPT}"),
                Message(role="assistant", content=objective)
            ])
            messages = conversation.model_dump()['messages']
            if not objective.strip().startswith('"""'):
                objective = '"""\n'+objective

            program = Program(
                id=hash((objective, json.dumps(messages))),
                code=objective,
                conversation=conversation,
                value=default_reward,
                state=game_state,
                version=mcts.version,
                version_description=mcts.version_description,
                token_usage=response.usage.total_tokens if hasattr(response, 'usage') else None,
                completion_token_usage=response.usage.completion_tokens if hasattr(response, 'usage') else None,
                prompt_token_usage=response.usage.prompt_tokens if hasattr(response, 'usage') else None,
                model=MODEL
            )
            seeded_programs.append(program)

    return seeded_programs


async def create_blueprint_seeds(
        mcts: ChunkedMCTS,
        db_config: Dict[str, str],
        n_seeds: int = 10
) -> List[Program]:
    """Generate seed programs from blueprint scenarios"""
    sampler = BlueprintScenarioSampler(
        db_config=db_config,
        system_prompt=mcts.system_prompt
    )
    return await sampler.sample_scenarios(
        instance=mcts.evaluator.instances[0],
        n_samples=n_seeds
    )


async def main():
    # Configuration
    CONFIG = {
        #'model': "ft:gpt-4o-2024-08-06:paperplane-ai:fact-self-gen-planning:AQzcPI91",
        "model": MODEL,
        'prompt_path': "../../prompts/bottoms_up_prompts/finetuning_prompts/system_message_policy_refined.md",
        'version': 54,
        'version_desc': "Objective Model / Chunked / KLD Diversity Sampling / Tick based sleep / Step-wise evaluation",
        'max_conv_len': 30,
        'logit_bias': { # We add these logit biases to prevent sampling the truncated code of previous messages.
            "15714": -100,  # 'LINE'
            "145968": -100, # ' CUT'
            "27": -100,     # '<'
            "20225": -100,   # '/>'
            "7032": -100 # while (we don't like while loops)
        }
    }


    # Initialize components
    llm = LLMFactory(CONFIG['model'])
    db_client = DBClient(
        max_conversation_length=CONFIG['max_conv_len'],
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD")
    )

    # Sampler
    sampler = KLDiversityAchievementSampler(db_client)

    # Set up Factorio instances
    instances = create_factorio_instances()
    for instance in instances:
        instance.speed(10)

    initial_state = GameState.from_instance(instances[0])

    system_prompt = instances[0].get_system_prompt()

    # Initialize MCTS
    print("Initializing MCTS...")
    mcts_config = ParallelMCTSConfig(
        n_parallel=4,
        system_prompt=system_prompt,
        initial_state=initial_state,
        mcts_class=ObjectiveMCTS,
        sampler=sampler,
        mcts_kwargs={
            'logit_bias': CONFIG['logit_bias'],
            'version': CONFIG['version'],
            'version_description': CONFIG['version_desc'],
            'formatter': StructurePreservingFormatter(planning=True)
        }
    )

    parallel_mcts = ParallelMCTS(
        instances=instances,
        db_client=db_client,
        llm_factory=llm,
        config=mcts_config,
        version_description="Objective MCTS",
        version=54
    )

    # Run search
    print("Starting MCTS search...")
    await parallel_mcts.search(n_iterations=1000, skip_failures=False)

if __name__ == '__main__':
    asyncio.run(main())