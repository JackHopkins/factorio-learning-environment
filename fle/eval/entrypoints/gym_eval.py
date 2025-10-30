import asyncio
import json
import multiprocessing
import os

import gymnasium as gym
import importlib.resources
from dotenv import load_dotenv
from fle.env.gym_env.observation_formatter import BasicObservationFormatter
from fle.env.gym_env.system_prompt_formatter import SystemPromptFormatter
from fle.env.gym_env.registry import get_environment_info, list_available_environments

from fle.agents.gym_agent import GymAgent
from fle.commons.db_client import create_db_client, get_next_version
from fle.eval.tasks import TaskFactory
from fle.eval.algorithms.independent.trajectory_runner import GymTrajectoryRunner
from fle.eval.algorithms.independent.config import GymEvalConfig, GymRunConfig
from fle.env.utils.controller_loader.system_prompt_generator import (
    SystemPromptGenerator,
)

try:
    from fle.eval.analysis import WandBLogger

    WANDB_ANALYSIS_AVAILABLE = True
except ImportError:
    WANDB_ANALYSIS_AVAILABLE = False

load_dotenv()


def get_validated_run_configs(run_config_location: str) -> list[GymRunConfig]:
    """Read and validate run configurations from file"""
    # Read run config
    with open(run_config_location, "r") as f:
        run_configs_raw = json.load(f)
        run_configs = [GymRunConfig(**config) for config in run_configs_raw]

    # Validate that all environment IDs exist in the registry
    available_envs = list_available_environments()
    for run_config in run_configs:
        if run_config.env_id not in available_envs:
            raise ValueError(
                f"Environment ID '{run_config.env_id}' not found in registry. Available environments: {available_envs}"
            )

    return run_configs


def run_process(run_idx: int, config: GymEvalConfig):
    """Run a single gym evaluation process"""
    asyncio.run(run_trajectory(run_idx, config))


async def run_trajectory(run_idx: int, config: GymEvalConfig):
    """Run a single gym evaluation process"""
    db_client = await create_db_client()

    gym_env = gym.make(config.env_id, run_idx=run_idx)

    log_dir = os.path.join(".fle", "trajectory_logs", f"v{config.version}")

    # Create WandB logger if enabled
    wandb_logger = None
    if WANDB_ANALYSIS_AVAILABLE and os.getenv("ENABLE_WANDB", "").lower() in [
        "true",
        "1",
    ]:
        try:
            # Extract task name from config
            task_name = "unknown_task"
            if config.version_description and "type:" in config.version_description:
                task_name = (
                    config.version_description.split("type:")[1].split("\n")[0].strip()
                )

            # Extract model name
            model_name = "unknown_model"
            if config.agents and len(config.agents) > 0:
                model_name = config.agents[0].model
            elif config.version_description and "model:" in config.version_description:
                model_name = (
                    config.version_description.split("model:")[1].split("\n")[0].strip()
                )

            # Get sweep ID for tagging
            sweep_id = os.getenv("FLE_SWEEP_ID", "unknown_sweep")

            wandb_logger = WandBLogger(
                project=os.getenv("WANDB_PROJECT", "factorio-learning-environment"),
                run_name=f"{model_name}-{task_name}-v{config.version}-trial{run_idx}",
                tags=[
                    "gym_eval",
                    model_name,
                    task_name,
                    f"v{config.version}",
                    f"sweep:{sweep_id}",
                ],
                config={
                    "model": model_name,
                    "task": task_name,
                    "version": config.version,
                    "trial": run_idx,
                    "version_description": config.version_description,
                    "sweep_id": sweep_id,
                },
            )
        except Exception as e:
            print(f"Warning: Failed to initialize WandB logger: {e}")
            wandb_logger = None

    runner = GymTrajectoryRunner(
        config=config,
        gym_env=gym_env,
        db_client=db_client,
        log_dir=log_dir,
        process_id=run_idx,
        wandb_logger=wandb_logger,
    )

    try:
        await runner.run()
    finally:
        await db_client.cleanup()
        if wandb_logger:
            wandb_logger.finish()


async def main(config_path):
    # Read and validate run configurations
    run_configs = get_validated_run_configs(config_path)
    # Get starting version number for new runs
    base_version = await get_next_version()
    version_offset = 0

    # Create and start processes
    processes = []
    for run_idx, run_config in enumerate(run_configs):
        # Get environment info from registry
        env_info = get_environment_info(run_config.env_id)
        if env_info is None:
            raise ValueError(f"Could not get environment info for {run_config.env_id}")
        task = TaskFactory.create_task(env_info["task_config_path"])
        generator = SystemPromptGenerator(str(importlib.resources.files("fle") / "env"))
        # Create agents and their agent cards
        agents = []
        agent_cards = []
        num_agents = env_info["num_agents"]
        for agent_idx in range(num_agents):
            system_prompt = generator.generate_for_agent(
                agent_idx=agent_idx, num_agents=num_agents
            )
            # Get API key config file from environment (set by sweep_manager)
            api_key_config_file = os.getenv("FLE_API_KEY_CONFIG_FILE") or os.getenv(
                "API_KEY_CONFIG_FILE"
            )

            agent = GymAgent(
                model=run_config.model,
                system_prompt=system_prompt,
                task=task,
                agent_idx=agent_idx,
                observation_formatter=BasicObservationFormatter(include_research=False),
                system_prompt_formatter=SystemPromptFormatter(),
                api_key_config_file=api_key_config_file,
            )
            agents.append(agent)

            # Create agent card for a2a support
            agent_card = agent.get_agent_card()
            agent_cards.append(agent_card)

        # Set version
        version = (
            run_config.version
            if run_config.version is not None
            else base_version + version_offset
        )
        version_offset += 1
        # Create eval config with agent cards for a2a support
        config = GymEvalConfig(
            agents=agents,
            version=version,
            version_description=f"model:{run_config.model}\ntype:{task.task_key}\nnum_agents:{num_agents}",
            task=task,
            agent_cards=agent_cards,
            env_id=run_config.env_id,
        )
        # Ensure agent cards are properly set for a2a functionality
        assert config.agent_cards is not None

        # Start process
        p = multiprocessing.Process(target=run_process, args=(run_idx, config))
        p.start()
        processes.append(p)

    # Wait for all processes to complete
    for p in processes:
        p.join()
