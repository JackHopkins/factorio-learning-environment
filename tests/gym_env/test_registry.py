#!/usr/bin/env python3
"""
Test script for the Factorio Gym Registry

This script demonstrates the complete workflow of:
1. Importing the registry (which auto-registers environments)
2. Listing available environments
3. Creating an environment with gym.make()
4. Basic interaction with the environment
"""

import gym
import sys
import os

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fle.env.gym_env.registry import list_available_environments, get_environment_info
from fle.env.gym_env.action import Action


def test_registry_discovery():
    """Test that the registry can discover and list environments"""
    print("=== Testing Registry Discovery ===")

    env_ids = list_available_environments()
    print(f"Found {len(env_ids)} environments:")

    for env_id in env_ids[:5]:  # Show first 5 for brevity
        info = get_environment_info(env_id)
        print(f"  {env_id}")
        print(f"    Description: {info['description'][:60]}...")
        print(f"    Task Key: {info['task_key']}")
        print(f"    Agents: {info['num_agents']}")

    if len(env_ids) > 5:
        print(f"  ... and {len(env_ids) - 5} more environments")

    print()
    return env_ids


def test_environment_creation():
    """Test creating an environment (without actually running it)"""
    print("=== Testing Environment Creation ===")

    env_ids = list_available_environments()
    if not env_ids:
        print("No environments available to test")
        return

    # Try to create the first environment
    test_env_id = env_ids[0]
    print(f"Attempting to create environment: {test_env_id}")

    try:
        # This will fail if Factorio containers aren't running, but that's expected
        env = gym.make(test_env_id)
        print("✓ Environment created successfully!")

        # Test basic environment properties
        print(f"  Action space: {env.action_space}")
        print(f"  Observation space: {type(env.observation_space)}")
        print(f"  Number of agents: {env.instance.num_agents}")

        # Test reset
        print("  Testing reset...")
        obs, info = env.reset()
        print(f"  Reset successful, observation keys: {list(obs.keys())}")

        # Test a simple action
        print("  Testing simple action...")
        action = Action(
            agent_idx=0,
            code='print("Hello from Factorio Gym Registry!")',
            game_state=None,
        )
        obs, reward, terminated, truncated, info = env.step(action)
        print("  Action successful!")
        print(f"    Reward: {reward}")
        print(f"    Done: {terminated}")
        print(f"    Truncated: {truncated}")
        print(f"    Info keys: {list(info.keys())}")

        # Clean up
        env.close()
        print("  Environment closed successfully")

    except Exception as e:
        print(
            f"✗ Environment creation failed (expected if containers not running): {e}"
        )
        print("  This is normal if Factorio containers aren't available")

    print()


def test_gym_integration():
    """Test that environments are properly registered with gym"""
    print("=== Testing Gym Integration ===")

    # Check if our environments are in gym's registry
    from gym.envs.registration import registry

    factorio_envs = [
        env_id for env_id in registry.keys() if env_id.startswith("Factorio-")
    ]

    print(f"Found {len(factorio_envs)} Factorio environments in gym registry:")
    for env_id in factorio_envs[:3]:  # Show first 3
        print(f"  {env_id}")

    if len(factorio_envs) > 3:
        print(f"  ... and {len(factorio_envs) - 3} more")

    print()


def test_registry_functions():
    """Test the registry utility functions"""
    print("=== Testing Registry Functions ===")

    # Test list_available_environments
    env_ids = list_available_environments()
    assert isinstance(env_ids, list)
    assert len(env_ids) > 0
    print(f"✓ list_available_environments() returned {len(env_ids)} environments")

    # Test get_environment_info
    if env_ids:
        info = get_environment_info(env_ids[0])
        assert info is not None
        assert "env_id" in info
        assert "description" in info
        assert "task_key" in info
        print(f"✓ get_environment_info() returned valid info for {env_ids[0]}")

    print()


def main():
    """Run all tests"""
    print("Factorio Gym Registry Test Suite")
    print("=" * 40)
    print()

    # Test 1: Registry discovery
    env_ids = test_registry_discovery()

    # Test 2: Registry functions
    test_registry_functions()

    # Test 3: Gym integration
    test_gym_integration()

    # Test 4: Environment creation (will fail gracefully if containers not available)
    test_environment_creation(env_ids)

    print("Test suite completed!")
    print("\nTo use the registry in your code:")
    print("```python")
    print("import gym")
    print("from gym_env.registry import list_available_environments")
    print()
    print("# List available environments")
    print("env_ids = list_available_environments()")
    print()
    print("# Create an environment")
    print("env = gym.make('Factorio-iron_ore_throughput_16-v0')")
    print("```")


if __name__ == "__main__":
    main()
