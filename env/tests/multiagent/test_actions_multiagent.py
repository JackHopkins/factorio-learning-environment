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
async def test_concurrent_agent_actions_with_messages(trajectory_runner, mock_config, basic_conversation):
    """Test that agents can perform actions, send messages, and maintain namespace state"""
    # Create programs for each agent that include message sending and namespace persistence
    agent0_program1 = Program(
        code="""
# Agent 0 defines a utility function and places a burner inserter
def place_inserter_at(x, y):
    return place_entity(
        Prototype.BurnerInserter,
        direction=Direction.RIGHT,
        position=Position(x=x, y=y)
    )

# Place first inserter
inserter1 = place_inserter_at(-5, -5)

# Send message to Agent 1 about placement
send_message("I've placed a burner inserter at (-5, -5)", recipient=1)
""",
        conversation=basic_conversation
    )

    agent0_program2 = Program(
        code="""
# Use the persisted function to place another inserter
inserter2 = place_inserter_at(0, 0)

# Send message to Agent 1 about second placement
send_message("I've placed another burner inserter at (0, 0)", recipient=1)
""",
        conversation=basic_conversation
    )

    agent1_program1 = Program(
        code="""
# Agent 1 defines a utility function for placing steam engines
def place_steam_engine_at(x, y):
    return place_entity(
        Prototype.SteamEngine,
        direction=Direction.RIGHT,
        position=Position(x=x, y=y)
    )

# Place first steam engine
engine1 = place_steam_engine_at(5, 5)

# Send message to Agent 0 about placement
send_message("I've placed a steam engine at (5, 5)", recipient=0)
""",
        conversation=basic_conversation
    )

    agent1_program2 = Program(
        code="""
# Use the persisted function to place another steam engine
engine2 = place_steam_engine_at(2, -2)

# Send message to Agent 0 about second placement
send_message("I've placed another steam engine at (2, -2)", recipient=0)

# Check if Agent 0's inserters are in the expected positions
entities = get_entities()
inserter_positions = [(e.position.x, e.position.y) for e in entities if e.type == "inserter"]
print(f"Found inserters at positions: {inserter_positions}")
""",
        conversation=basic_conversation
    )

    programs = [agent0_program1, agent1_program1, agent0_program2, agent1_program2]
    current_state = mock_config.task.starting_game_state
    
    # Execute programs in sequence
    for step in range(4):
        i = step % 2
        instance = trajectory_runner.evaluator.instances[i]
        instance.reset(current_state)
        evaluated_program, _ = await trajectory_runner.evaluator.evaluate(
            programs[step], current_state, mock_config.task, i
        )
        current_state = evaluated_program.state
        print(type(current_state))
        print(current_state.agent_messages)

    # Get instances
    instance0 = trajectory_runner.evaluator.instances[0]
    instance1 = trajectory_runner.evaluator.instances[1]
    
    # Check agent 0's namespace for persisted functions
    assert 'place_inserter_at' in instance0.namespace.persistent_vars
    assert not 'place_steam_engine_at' in instance0.namespace.persistent_vars
    assert callable(instance0.namespace.persistent_vars['place_inserter_at'])
    
    # Check agent 1's namespace for persisted functions
    assert 'place_steam_engine_at' in instance1.namespace.persistent_vars
    assert not 'place_inserter_at' in instance1.namespace.persistent_vars
    assert callable(instance1.namespace.persistent_vars['place_steam_engine_at'])
    
    # Check entities
    entities0 = instance0.namespace.get_entities()
    entities1 = instance1.namespace.get_entities()
    
    # Verify both agents have the expected entities
    inserter_count0 = sum(1 for e in entities0 if e.type == "inserter")
    inserter_count1 = sum(1 for e in entities1 if e.type == "inserter")
    engine_count0 = sum(1 for e in entities0 if e.type == "generator")
    engine_count1 = sum(1 for e in entities1 if e.type == "generator")

    assert inserter_count0 == 2, f"Expected 2 inserters for agent 0, found {inserter_count0}"
    assert inserter_count1 == 2, f"Expected 2 inserters for agent 1, found {inserter_count1}"
    assert engine_count0 == 2, f"Expected 2 steam engines for agent 0, found {engine_count0}"
    assert engine_count1 == 2, f"Expected 2 steam engines for agent 1, found {engine_count1}"

    # Check messages
    trajectory_runner._collect_new_messages(0)
    trajectory_runner._collect_new_messages(1)
    
    # Verify messages were received
    assert len(trajectory_runner.agent_messages[0]) == 2, "Agent 0 should have received 2 messages"
    assert len(trajectory_runner.agent_messages[1]) == 2, "Agent 1 should have received 2 messages"
    
    # Check message content
    agent0_messages = [msg.content for msg in trajectory_runner.agent_messages[0]]
    agent1_messages = [msg.content for msg in trajectory_runner.agent_messages[1]]
    
    assert any("steam engine at (5, 5)" in msg for msg in agent0_messages)
    assert any("steam engine at (2, -2)" in msg for msg in agent0_messages)
    assert any("burner inserter at (-5, -5)" in msg for msg in agent1_messages)
    assert any("burner inserter at (0, 0)" in msg for msg in agent1_messages)
    assert False


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
        instance = trajectory_runner.evaluator.instances[i]
        instance.reset(current_state)
        evaluated_program, _ = await trajectory_runner.evaluator.evaluate(
            programs[j], current_state, mock_config.task, i
        )
        current_state = evaluated_program.state
    trajectory_runner.evaluator.instances[0].reset(current_state)

        
    # Get instances
    instance0 = trajectory_runner.evaluator.instances[0]
    instance1 = trajectory_runner.evaluator.instances[1]
    
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


