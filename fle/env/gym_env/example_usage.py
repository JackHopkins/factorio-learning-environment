#!/usr/bin/env python3
"""
Factorio Gym Registry - Example Usage and Environment Explorer

This script provides both interactive examples and command-line tools for:
1. Listing and exploring available environments
2. Creating environments using gym.make()
3. Interacting with the environments
4. Searching for specific tasks

Usage:
    python example_usage.py                    # Run interactive examples
    python example_usage.py --list            # List all environments
    python example_usage.py --detail          # Show detailed information
    python example_usage.py --search <term>   # Search for specific environments
    python example_usage.py --gym-format      # Output in gym.make() format
"""

import gym
import argparse
import sys
import os
from typing import List

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fle.env.gym_env.registry import list_available_environments, get_environment_info
from fle.env.gym_env.action import Action
from fle.commons.models.game_state import GameState


def print_environment_list(env_ids: List[str], detailed: bool = False):
    """Print a formatted list of environments"""
    if not env_ids:
        print("No environments found.")
        return

    print(f"Found {len(env_ids)} Factorio gym environments:\n")

    for i, env_id in enumerate(env_ids, 1):
        info = get_environment_info(env_id)
        if not info:
            continue

        print(f"{i:2d}. {env_id}")
        print(f"     Description: {info['description']}")

        if detailed:
            print(f"     Task Key: {info['task_key']}")
            print(f"     Config Path: {info['task_config_path']}")
            print(f"     Agents: {info['num_agents']}")
            print(f"     Model: {info['model']}")
            print(f"     Exit on Success: {info['exit_on_task_success']}")

        print()


def search_environments(search_term: str, detailed: bool = False) -> List[str]:
    """Search for environments containing the given term"""
    all_env_ids = list_available_environments()
    matching_env_ids = []

    search_term_lower = search_term.lower()

    for env_id in all_env_ids:
        info = get_environment_info(env_id)
        if not info:
            continue

        # Search in environment ID, task key, and description
        if (
            search_term_lower in env_id.lower()
            or search_term_lower in info["task_key"].lower()
            or search_term_lower in info["description"].lower()
        ):
            matching_env_ids.append(env_id)

    return matching_env_ids


def run_interactive_examples():
    """Run interactive examples demonstrating the gym registry functionality"""

    print("=== Factorio Gym Registry Interactive Examples ===\n")

    # 1. List all available environments
    print("1. Available Environments:")
    env_ids = list_available_environments()
    for env_id in env_ids[:3]:  # Show first 3 for brevity
        info = get_environment_info(env_id)
        print(f"   {env_id}")
        print(f"     Description: {info['description']}")
        print(f"     Task Key: {info['task_key']}")
        print(f"     Agents: {info['num_agents']}")
        print()

    if len(env_ids) > 3:
        print(f"   ... and {len(env_ids) - 3} more environments")
        print()

    # 2. Example of creating and using an environment
    if env_ids:
        example_env_id = env_ids[0]  # Use the first available environment
        print(f"2. Creating environment: {example_env_id}")

        try:
            # Create the environment using gym.make()
            env = gym.make(example_env_id)

            # Reset the environment with required options parameter
            print("   Resetting environment...")
            obs, info = env.reset(options={"game_state": None})
            print(f"   Initial observation keys: {list(obs.keys())}")

            # Take a simple action
            print("   Taking a simple action...")

            # Get the current game state from the environment
            current_game_state = GameState.from_instance(env.instance)
            action = Action(
                agent_idx=0,
                game_state=current_game_state,
                code='print("Hello from Factorio Gym!")',
            )

            obs, reward, terminated, truncated, info = env.step(action)
            print(f"   Reward: {reward}")
            print(f"   Terminated: {terminated}")
            print(f"   Truncated: {truncated}")
            print(f"   Info keys: {list(info.keys())}")

            # Close the environment
            env.close()
            print("   Environment closed successfully")

        except Exception as e:
            print(f"   Error creating/using environment: {e}")
            print(
                "   Note: This might be due to missing Factorio containers or other setup requirements"
            )

    print("\n3. Usage Examples:")
    print("   # List all environments")
    print("   from gym_env.registry import list_available_environments")
    print("   env_ids = list_available_environments()")
    print()
    print("   # Create an environment")
    print("   import gym")
    print("   env = gym.make('Factorio-iron_ore_throughput_16-v0')")
    print()
    print("   # Use the environment")
    print("   obs, info = env.reset(options={'game_state': None})")
    print(
        "   action = Action(agent_idx=0, game_state='', code='print(\"Hello Factorio!\")')"
    )
    print("   obs, reward, terminated, truncated, info = env.step(action)")
    print("   env.close()")


def run_command_line_mode():
    """Run in command-line mode for listing and searching environments"""
    parser = argparse.ArgumentParser(
        description="Factorio Gym Registry - Environment Explorer and Examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python example_usage.py                    # Run interactive examples
  python example_usage.py --list            # List all environments
  python example_usage.py --detail          # Show detailed information
  python example_usage.py --search iron     # Search for iron-related tasks
  python example_usage.py --search science  # Search for science pack tasks
  python example_usage.py --gym-format      # Output in gym.make() format
        """,
    )

    parser.add_argument(
        "--list", "-l", action="store_true", help="List all available environments"
    )

    parser.add_argument(
        "--detail",
        "-d",
        action="store_true",
        help="Show detailed information for each environment",
    )

    parser.add_argument(
        "--search",
        "-s",
        type=str,
        help="Search for environments containing the given term",
    )

    parser.add_argument(
        "--gym-format",
        "-g",
        action="store_true",
        help="Output in gym.make() format for easy copy-paste",
    )

    args = parser.parse_args()

    # If no arguments provided, run interactive examples
    if not any([args.list, args.detail, args.search, args.gym_format]):
        run_interactive_examples()
        return

    # Get environments
    if args.search:
        env_ids = search_environments(args.search, args.detail)
        if not env_ids:
            print(f"No environments found matching '{args.search}'")
            return
        print(f"Environments matching '{args.search}':\n")
    else:
        env_ids = list_available_environments()

    # Output in gym format if requested
    if args.gym_format:
        print("# Available Factorio gym environments:")
        print("# Copy and paste these lines to create environments:")
        print()
        for env_id in env_ids:
            print(f"env = gym.make('{env_id}')")
        return

    # Print environments
    print_environment_list(env_ids, args.detail)

    # Show usage example
    if env_ids:
        example_env = env_ids[0]
        print("Example usage:")
        print("```python")
        print("import gym")
        print(f"env = gym.make('{example_env}')")
        print("obs, info = env.reset(options={'game_state': None})")
        print(
            "action = Action(agent_idx=0, game_state='', code='print(\"Hello Factorio!\")')"
        )
        print("obs, reward, terminated, truncated, info = env.step(action)")
        print("env.close()")
        print("```")


def main():
    """Main function - determines whether to run interactive examples or command-line mode"""
    if len(sys.argv) > 1:
        # Command-line mode
        run_command_line_mode()
    else:
        # Interactive examples mode
        run_interactive_examples()


if __name__ == "__main__":
    main()
