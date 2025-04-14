import asyncio
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from eval.open.independent_runs.trajectory_runner import TrajectoryRunner
from models.program import Program
from models.game_state import GameState
from models.conversation import Conversation
from models.message import Message
from agents.basic_agent import BasicAgent
from eval.open.db_client import PostgresDBClient
from eval.open.independent_runs.simple_evaluator import SimpleFactorioEvaluator
from eval.tasks.default_task import DefaultTask

from env.tests.multiagent.test_setup_multiagent import multi_instance
from env.tests.multiagent.test_messages import mock_db_client, mock_config, trajectory_runner


@pytest.fixture
def basic_conversation():
    """Create a basic conversation object for testing"""
    return Conversation(
        messages=[
            Message(role='system', content='You are a helpful assistant'),
            Message(role='user', content='Hello'),
            Message(role='assistant', content='Hi there!')
        ]
    )

@pytest.mark.asyncio
async def test_concurrent_agent_actions(trajectory_runner, mock_config, basic_conversation):
    """Test that agents can move and mine independently"""
    # Create programs for each agent
    agent0_program1 = Program(
        code="""
# Agent 0 places a burner inserter
inserter = place_entity(
    Prototype.BurnerInserter,
    direction=Direction.RIGHT,
    position=Position(x=-5, y=-5)
)
""",
        conversation=basic_conversation
    )

    agent0_program2 = Program(
        code="""
# Agent 0 places a burner inserter
inserter = place_entity(
    Prototype.BurnerInserter,
    direction=Direction.RIGHT,
    position=Position(x=0, y=0)
)
""",
        conversation=basic_conversation
    )

    
    agent1_program1 = Program(
        code="""
# Agent 1 places a steam engine
steam_engine = place_entity(
    Prototype.SteamEngine,
    direction=Direction.RIGHT,
    position=Position(x=5, y=5)
)
""",
        conversation=basic_conversation
    )
    agent1_program2 = Program(
        code="""
# Agent 1 places a steam engine
steam_engine = place_entity(
    Prototype.SteamEngine,
    direction=Direction.RIGHT,
    position=Position(x=2, y=-2)
)
""",
        conversation=basic_conversation
    )
    programs = [agent0_program1, agent1_program1, agent0_program2, agent1_program2]
    current_state = mock_config.task.starting_game_state
    
    for j in range(4):
        i = j % 2
        instance = trajectory_runner.evaluators[i].instance
        instance.reset(current_state)
        evaluated_program, _ = await trajectory_runner.evaluators[i].evaluate(
            programs[j], current_state, mock_config.task
        )
        print(f'agent {i} program response : {evaluated_program.response}')
        current_state = evaluated_program.state
    trajectory_runner.evaluators[0].instance.reset(current_state)

        
    # Get instances
    instance0 = trajectory_runner.evaluators[0].instance
    instance1 = trajectory_runner.evaluators[1].instance
    
    # Check agent 0's position and mining
    entities0 = instance0.namespace.get_entities()
    inventory0 = instance0.namespace.inspect_inventory()
    
    # Check agent 1's position and mining
    entities1 = instance1.namespace.get_entities()
    inventory1 = instance1.namespace.inspect_inventory()
    
    # Verify that both agents have moved to their respective positions
    # Print agent positions for debugging
    print("\nAgent positions:")
    print("Agent 0 entities:", [(e.type, e.position) for e in entities0])
    print("Agent 1 entities:", [(e.type, e.position) for e in entities1])
    
    # Print inventory contents
    print("\nInventory contents:")
    print("Agent 0 inventory:", inventory0.__dict__)
    print("Agent 1 inventory:", inventory1.__dict__)
    # Verify both agents have the expected entities
    inserter_count0 = sum(1 for e in entities0 if e.type == "inserter")
    inserter_count1 = sum(1 for e in entities1 if e.type == "inserter")
    generator_count0 = sum(1 for e in entities0 if e.type == "generator") 
    generator_count1 = sum(1 for e in entities1 if e.type == "generator")

    assert inserter_count0 == 2, f"Expected 2 inserters for agent 0, found {inserter_count0}"
    assert inserter_count1 == 2, f"Expected 2 inserters for agent 1, found {inserter_count1}"
    assert generator_count0 == 2, f"Expected 2 generators for agent 0, found {generator_count0}"
    assert generator_count1 == 2, f"Expected 2 generators for agent 1, found {generator_count1}"

