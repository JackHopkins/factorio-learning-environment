import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from fle.agents.basic_agent import BasicAgent
from fle.commons.db_client import PostgresDBClient
from fle.commons.models.conversation import Conversation
from fle.commons.models.message import Message
from fle.env.a2a_instance import A2AFactorioInstance
from fle.eval.algorithms.independent import SimpleFactorioEvaluator, TrajectoryRunner
from fle.eval.tasks.default_task import DefaultTask


@pytest.fixture
def multi_instance(instance):
    """Creates a second FactorioInstance with a different player_index"""
    # First instance is already created by the base fixture
    single_instance = instance
    inventory = single_instance.initial_inventory

    multi_instance = asyncio.run(
        A2AFactorioInstance.create(
            address="localhost",
            bounding_box=200,
            tcp_port=single_instance.tcp_port,
            cache_scripts=False,
            fast=True,
            inventory=inventory,
            num_agents=2,
        )
    )

    yield multi_instance

    # Cleanup
    multi_instance.reset()


@pytest.fixture
def mock_db_client():
    """Create a mock database client"""
    client = MagicMock(spec=PostgresDBClient)
    client.get_resume_state.return_value = (None, None, None, 0)
    client.create_program.return_value = MagicMock(id=1)
    return client


@pytest.fixture
def mock_config(multi_instance):
    """Create a mock configuration"""
    # Create a real task
    task = DefaultTask(
        trajectory_length=2,
        goal_description="Test task for agent messaging",
        task_key="test_task",
    )

    # Create agents
    agents = [
        BasicAgent(model="test-model-1", system_prompt="You are Agent 1", task=task),
        BasicAgent(model="test-model-2", system_prompt="You are Agent 2", task=task),
    ]

    # Create config
    config = MagicMock()
    config.agents = agents
    config.version = 0
    config.version_description = "test"
    config.exit_on_task_success = False
    config.task = task

    return config


@pytest.fixture
def trajectory_runner(multi_instance, mock_db_client, mock_config):
    """Create a real TrajectoryRunner with actual instances"""
    # Create evaluators
    evaluator = SimpleFactorioEvaluator(
        db_client=mock_db_client,
        instance=multi_instance,
        value_accrual_time=1,
        error_penalty=0,
    )

    # Create trajectory runner
    runner = TrajectoryRunner(
        mock_config.agents, mock_db_client, evaluator, mock_config, process_id=1
    )

    yield runner

    runner.evaluator.instance.reset()


def test_collaborative_scenario(trajectory_runner, mock_config):
    """Test a collaborative scenario with multiple agents"""
    # Mock the _generate_program method to avoid actual program generation
    with patch.object(TrajectoryRunner, "_generate_program", return_value=MagicMock()):
        # Start the run
        try:
            trajectory_runner.run()
        except RuntimeError:
            # Expected since we're not actually running async code
            pass

        # Simulate a collaborative scenario:
        # Agent 0: Resource gatherer
        # Agent 1: Builder
        instance = trajectory_runner.evaluator.instance

        # Agent 0 (resource gatherer) reports progress
        instance.namespaces[0].send_message(
            "I've gathered 100 iron plates and 50 copper plates.", recipient=1
        )

        # Agent 1 (builder) asks for specific resources
        instance.namespaces[1].send_message(
            "I need 20 steel plates to start building. Can you provide these?",
            recipient=0,
        )

        # Agent 0 (resource gatherer) responds
        instance.namespaces[0].send_message(
            "I'll start producing steel plates right away. Will have them ready in 5 minutes.",
            recipient=1,
        )

        # Give it a moment to process
        time.sleep(0.1)

        trajectory_runner._collect_new_messages(0)
        new_messages_text = trajectory_runner._collect_new_messages(1)
        # Check that messages were delivered correctly
        # Agent 0 should have received messages from Agent 1
        # Check Agent 0 received messages from Agent 1
        assert any(
            msg.sender == "1" and "need 20 steel plates" in msg.content
            for msg in trajectory_runner.agent_messages[0]
        )

        # Check Agent 1 received messages from Agent 0
        assert any(
            msg.sender == "0" and "gathered 100 iron plates" in msg.content
            for msg in trajectory_runner.agent_messages[1]
        )

        assert any(
            msg.sender == "0" and "steel plates" in msg.content
            for msg in trajectory_runner.agent_messages[1]
        )

        # Check message formatting
        assert "Agent 0" in new_messages_text
        assert "gathered 100 iron plates" in new_messages_text
        assert "steel plates" in new_messages_text


def test_send_message_to_specific_agent(trajectory_runner, mock_config):
    """Test sending a message to a specific agent"""
    # Agent 0 sends a message to Agent 1
    instance = trajectory_runner.evaluator.instance
    instance.namespaces[0].send_message("Hello Agent 1", recipient=1)
    trajectory_runner._collect_new_messages(0)
    trajectory_runner._collect_new_messages(1)

    # Check that Agent 1 received the message
    assert len(trajectory_runner.agent_messages[1]) == 1
    assert trajectory_runner.agent_messages[1][0].sender == "0"
    assert trajectory_runner.agent_messages[1][0].recipient == "1"
    assert trajectory_runner.agent_messages[1][0].content == "Hello Agent 1"

    # Agent 0 should not have received the message (sender is excluded)
    assert len(trajectory_runner.agent_messages[0]) == 0


def test_send_message_to_all_agents(trajectory_runner, mock_config):
    """Test sending a message to all agents"""
    # Agent 0 sends a message to all agents
    instance = trajectory_runner.evaluator.instance
    instance.namespaces[0].send_message("Hello everyone")
    trajectory_runner._collect_new_messages(0)
    trajectory_runner._collect_new_messages(1)

    print(f"trajectory_runner.agent_messages: {trajectory_runner.agent_messages}")
    # Check that Agent 1 received the message
    assert len(trajectory_runner.agent_messages[1]) == 1
    assert trajectory_runner.agent_messages[1][0].content == "Hello everyone"

    # Agent 0 should not have received the message (sender is excluded)
    assert len(trajectory_runner.agent_messages[0]) == 0


def test_message_collection_in_conversation(trajectory_runner, mock_config):
    """Test that messages are collected in the conversation"""
    # Agent 0 sends a message to Agent 1
    instance = trajectory_runner.evaluator.instance
    instance.namespaces[0].send_message("Hello Agent 1", recipient=1)

    # Collect new messages for Agent 1
    new_messages_text = trajectory_runner._collect_new_messages(1)

    # Check that the message was formatted correctly
    # assert "Agent 0" in new_messages_text
    assert "Hello Agent 1" in new_messages_text

    # Update the conversation with new messages
    base_conversation = Conversation(
        messages=[
            Message(role="assistant", content="wow what a game"),
            Message(role="user", content="indeed."),
        ]
    )
    mock_config.agents[1].set_conversation(base_conversation)
    last_user_message = mock_config.agents[1].conversation.messages[-1]
    last_user_message.content += new_messages_text

    # Check that the message was added to the conversation
    assert "Hello Agent 1" in last_user_message.content


def test_only_new_messages_are_collected(trajectory_runner, mock_config):
    """Test that only new messages are collected"""
    # Agent 0 sends a message to Agent 1
    instance = trajectory_runner.evaluator.instance
    instance.namespaces[0].send_message("Hello Agent 1", recipient=1)

    # Collect new messages for Agent 1
    new_messages_text1 = trajectory_runner._collect_new_messages(1)

    # Check that the message was collected
    assert "Hello Agent 1" in new_messages_text1

    # Collect new messages again
    new_messages_text2 = trajectory_runner._collect_new_messages(1)

    # Check that no new messages were collected (empty string)
    assert new_messages_text2 == ""


def test_multiple_messages(trajectory_runner, mock_config):
    """Test handling multiple messages"""
    # Agent 0 sends a message to Agent 1
    instance = trajectory_runner.evaluator.instance
    instance.namespaces[0].send_message("Hello Agent 1", recipient=1)

    # Agent 1 sends a message to Agent 0
    instance.namespaces[1].send_message("Hello from Agent 1", recipient=0)

    # Collect new messages for Agent 0
    new_messages_text = trajectory_runner._collect_new_messages(0)

    # Check that the message was collected
    assert "Hello from Agent 1" in new_messages_text

    # Collect new messages for Agent 1
    new_messages_text = trajectory_runner._collect_new_messages(1)

    # Check that the message was collected
    assert "Hello Agent 1" in new_messages_text
