import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any

from eval.open.mcts.mcts_trajectory_runner import MCTSTrajectoryRunner
from eval.open.mcts.mcts_worker import MCTSConfig


@dataclass
class MCTSRunParameters:
    """Parameters needed to start an MCTS run in a separate process"""
    agent_model: str
    agent_system_prompt: str
    task_key: str
    task_data: Dict[str, Any]
    version: int
    version_description: str
    num_workers: int
    mcts_config: Dict[str, Any]
    sampler_config: Dict[str, Any]
    container_ips: List[str]
    container_tcp_ports: List[int]


async def run_mcts(params: MCTSRunParameters):
    """Entry point for running MCTS search inside a process"""
    import os
    from dotenv import load_dotenv
    from eval.open.db_client import PostgresDBClient
    from eval.tasks.task_factory import TaskFactory
    from agents.basic_agent import BasicAgent
    from eval.open.mcts.dynamic_reward_weighted_sampler import DynamicRewardWeightedSampler

    load_dotenv()

    # Create database client
    db_client = PostgresDBClient(
        max_conversation_length=40,
        min_connections=2,
        max_connections=5,
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD")
    )

    # Create task
    task = TaskFactory.create_task(params.task_key)

    # Create agent
    agent = BasicAgent(
        model=params.agent_model,
        system_prompt=params.agent_system_prompt,
        task=task
    )

    # Create sampler
    sampler = DynamicRewardWeightedSampler(
        db_client=db_client,
        compression_strength=params.sampler_config.get("compression_strength"),
        adaptive_period=params.sampler_config.get("adaptive_period", 200),
        maximum_lookback=params.sampler_config.get("maximum_lookback", 20)
    )

    # Create MCTS config
    config = MCTSConfig(
        agent=agent,
        sampler=sampler,
        version=params.version,
        version_description=params.version_description,
        max_iterations=params.mcts_config.get("max_iterations", 200),
        exploration_weight=params.mcts_config.get("exploration_weight", 1.41),
        batch_size=params.mcts_config.get("batch_size", params.num_workers),
        max_depth=params.mcts_config.get("max_depth", 50)
    )

    # Create and run MCTS
    runner = MCTSTrajectoryRunner(
        db_client=db_client,
        config=config,
        num_workers=params.num_workers
    )

    await runner.run()
    await db_client.cleanup()


def process_mcts_run(params: MCTSRunParameters):
    """Process entry point for multiprocessing"""
    asyncio.run(run_mcts(params))