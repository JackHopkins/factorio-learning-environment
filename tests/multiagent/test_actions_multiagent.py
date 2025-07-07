import pytest

from fle.commons.models.program import Program
from fle.commons.models.conversation import Conversation
from fle.commons.models.message import Message


@pytest.fixture
def basic_conversation():
    """Create a basic conversation object for testing"""
    return Conversation(
        messages=[
            Message(role="system", content="You are a helpful assistant"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]
    )


@pytest.mark.asyncio
async def test_concurrent_agent_actions_with_messages(
    trajectory_runner, mock_config, basic_conversation
):
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
        conversation=basic_conversation,
    )

    agent0_program2 = Program(
        code="""
# Use the persisted function to place another inserter
inserter2 = place_inserter_at(0, 0)

# Send message to Agent 1 about second placement
send_message("I've placed another burner inserter at (0, 0)", recipient=1)
""",
        conversation=basic_conversation,
    )

    agent1_program1 = Program(
        code="""
# Agent 1 defines a utility function for placing stone furnaces
def place_furnace_at(x, y):
    return place_entity(
        Prototype.StoneFurnace,
        direction=Direction.RIGHT,
        position=Position(x=x, y=y)
    )

# Place first furnace
furnace1 = place_furnace_at(5, 5)

# Send message to Agent 0 about placement
send_message("I've placed a stone furnace at (5, 5)", recipient=0)
""",
        conversation=basic_conversation,
    )

    agent1_program2 = Program(
        code="""
# Use the persisted function to place another furnace
furnace2 = place_furnace_at(5, -5)

# Send message to Agent 0 about second placement
send_message("I've placed another stone furnace at (5, -5)", recipient=0)

# Check if Agent 0's inserters are in the expected positions
entities = get_entities()
inserter_positions = [(e.position.x, e.position.y) for e in entities if e.type == "inserter"]
print(f"Found inserters at positions: {inserter_positions}")
""",
        conversation=basic_conversation,
    )

    programs = [agent0_program1, agent1_program1, agent0_program2, agent1_program2]
    current_state = mock_config.task.starting_game_state

    # Execute programs in sequence
    instance = trajectory_runner.evaluator.instance
    for step in range(4):
        i = step % 2
        instance.reset(current_state)
        evaluated_program, _ = await trajectory_runner.evaluator.evaluate(
            programs[step], current_state, mock_config.task, i
        )
        current_state = evaluated_program.state

    # Get instances
    namespace0 = instance.namespaces[0]
    namespace1 = instance.namespaces[1]

    # Check agent 0's namespace for persisted functions
    assert "place_inserter_at" in namespace0.persistent_vars
    assert "place_furnace_at" not in namespace0.persistent_vars
    assert callable(namespace0.persistent_vars["place_inserter_at"])

    # Check agent 1's namespace for persisted functions
    assert "place_furnace_at" in namespace1.persistent_vars
    assert "place_inserter_at" not in namespace1.persistent_vars
    assert callable(namespace1.persistent_vars["place_furnace_at"])

    # Check entities
    entities0 = namespace0.get_entities()
    entities1 = namespace1.get_entities()

    print(entities0)
    print(entities1)

    # Verify both agents have the expected entities
    inserter_count0 = sum(1 for e in entities0 if e.type == "inserter")
    inserter_count1 = sum(1 for e in entities1 if e.type == "inserter")
    furnace_count0 = sum(1 for e in entities0 if e.type == "furnace")
    furnace_count1 = sum(1 for e in entities1 if e.type == "furnace")

    assert inserter_count0 == 2, (
        f"Expected 2 inserters for agent 0, found {inserter_count0}"
    )
    assert inserter_count1 == 2, (
        f"Expected 2 inserters for agent 1, found {inserter_count1}"
    )
    assert furnace_count0 == 2, (
        f"Expected 2 stone furnaces for agent 0, found {furnace_count0}"
    )
    assert furnace_count1 == 2, (
        f"Expected 2 stone furnaces for agent 1, found {furnace_count1}"
    )

    # Check messages
    trajectory_runner._collect_new_messages(0)
    trajectory_runner._collect_new_messages(1)

    # Verify messages were received
    assert len(trajectory_runner.agent_messages[1]) == 2, (
        "Agent 1 should have received 2 messages"
    )
    assert len(trajectory_runner.agent_messages[0]) == 2, (
        "Agent 0 should have received 2 messages"
    )

    # Check message content
    agent0_messages = [msg.content for msg in trajectory_runner.agent_messages[0]]
    agent1_messages = [msg.content for msg in trajectory_runner.agent_messages[1]]

    assert any("stone furnace at (5, 5)" in msg for msg in agent0_messages)
    assert any("stone furnace at (5, -5)" in msg for msg in agent0_messages)
    assert any("burner inserter at (-5, -5)" in msg for msg in agent1_messages)
    assert any("burner inserter at (0, 0)" in msg for msg in agent1_messages)
