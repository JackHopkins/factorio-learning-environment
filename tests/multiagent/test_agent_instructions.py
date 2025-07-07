import pytest
from fle.agents.basic_agent import BasicAgent
from fle.eval.tasks import UnboundedThroughputTask


def test_basic_agent_instructions():
    """Test that agent instructions are properly incorporated into BasicAgent system prompts"""
    # Create a task with agent instructions
    agent_instructions = [
        "You are Agent 1. Your role is to mine coal.",
        "You are Agent 2. Your role is to mine iron.",
    ]

    task = UnboundedThroughputTask(
        trajectory_length=16,
        goal_description="Test task",
        task_key="test_task",
        throughput_entity="iron-plate",
        holdout_wait_period=60,
        agent_instructions=agent_instructions,
    )

    # Create agents with the task
    agent1 = BasicAgent(
        model="test-model", system_prompt="Base prompt", task=task, agent_idx=0
    )
    agent2 = BasicAgent(
        model="test-model", system_prompt="Base prompt", task=task, agent_idx=1
    )

    # Verify agent instructions appear in system prompts
    assert "### Specific Instructions for Agent 1" in agent1.system_prompt
    assert "You are Agent 1. Your role is to mine coal." in agent1.system_prompt

    assert "### Specific Instructions for Agent 2" in agent2.system_prompt
    assert "You are Agent 2. Your role is to mine iron." in agent2.system_prompt


def test_no_agent_instructions():
    """Test that BasicAgent works correctly when no agent instructions are provided"""
    # Create a task without agent instructions
    task = UnboundedThroughputTask(
        trajectory_length=16,
        goal_description="Test task",
        task_key="test_task",
        throughput_entity="iron-plate",
        holdout_wait_period=60,
    )

    # Create agent with the task
    agent = BasicAgent(
        model="test-model", system_prompt="Base prompt", task=task, agent_idx=0
    )

    # Verify no agent instructions section appears
    assert "### Specific Instructions for Agent" not in agent.system_prompt


def test_agent_instructions_index_bounds():
    """Test that agent instructions handle index bounds correctly"""
    # Create a task with agent instructions
    agent_instructions = [
        "You are Agent 1. Your role is to mine coal.",
        "You are Agent 2. Your role is to mine iron.",
    ]

    task = UnboundedThroughputTask(
        trajectory_length=16,
        goal_description="Test task",
        task_key="test_task",
        throughput_entity="iron-plate",
        holdout_wait_period=60,
        agent_instructions=agent_instructions,
    )

    # Test with invalid agent index
    with pytest.raises(IndexError):
        agent = BasicAgent(
            model="test-model", system_prompt="Base prompt", task=task, agent_idx=2
        )
        assert "### Specific Instructions for Agent" not in agent.system_prompt
