#!/usr/bin/env python3

import sys
import os
import time
from typing import Dict, Any, List

# Add parent directory to path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.factorio_helper import create_factorio_instance, initialize_logging
from shared.parsing_utils import load_events, parse_function_call
from shared.run_actions_utils import convert_run_actions_args_to_tool_args


def convert_tool_args_to_server_args(
    func_name: str, tool_args: Dict[str, Any]
) -> List[Any]:
    """Convert tool keyword arguments back to positional server arguments."""
    # This is the same conversion function from the original batched script
    # [Implementation would be the same as in run_actions_batched.py]
    return list(tool_args.values())


def submit_batch_to_server_streaming(instance, batch: List[Dict], start_tick: int):
    """Submit a batch of actions and stream results as they become available."""

    print(
        f"Submitting streaming batch of {len(batch)} actions starting at tick {start_tick}"
    )

    # Convert batch actions to server format
    for action in batch:
        tick = action["tick"]
        func_name = action["func_name"]
        args = action["args"]

        # Process arguments using the conversion function
        processed_args = convert_run_actions_args_to_tool_args(func_name, args)

        # Add to batch manager
        if hasattr(instance.batch_manager, "add_tool_command"):
            server_args = convert_tool_args_to_server_args(func_name, processed_args)
            instance.batch_manager.add_tool_command(tick, func_name, 1, *server_args)

    # Stream results as they become available
    results_processed = 0
    action_results = []

    print("Streaming results as they complete...")

    try:
        for result in instance.batch_manager.submit_batch_and_stream(
            timeout_seconds=60, poll_interval=0.1
        ):
            results_processed += 1
            action_results.append(result)

            # Process result immediately
            command_name = result["command"]
            success = result["success"]
            tick = result["tick"]

            print(
                f"  ✓ [{results_processed}/{len(batch)}] {command_name} at tick {tick}: {'✓' if success else '✗'}"
            )

            # You can add custom processing logic here for each result
            if not success:
                print(f"    Error: {result['result']}")

            # Example: Save successful results to a file or database
            # Example: Update progress bars or send notifications
            # Example: Start dependent operations based on completed results

    except Exception as e:
        print(f"Error during streaming batch execution: {e}")
        raise

    print(f"Completed streaming processing of {results_processed} results")
    return action_results


def execute_events_from_file_streaming(
    events_file_path: str,
    enable_logging: bool = False,
    speed: float = 1.0,
    batch_size: int = 50,
):
    """Execute events using streaming batch processing for real-time result processing."""

    events = load_events(events_file_path)
    events.sort(key=lambda x: x.get("tick", 0))

    instance = create_factorio_instance()
    instance.reset()

    # Initialize logging only if enabled
    if enable_logging:
        initialize_logging()
        print("Logging enabled - data will be saved to logs/")
    else:
        print("Logging disabled - no data will be saved")

    # Activate batch mode
    instance.batch_manager.activate()

    try:
        print(f"Starting streaming batch execution with batch size {batch_size}")
        print(f"Total events to process: {len(events)}")

        all_results = []

        # Process events in batches
        for i in range(0, len(events), batch_size):
            batch = events[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(events) + batch_size - 1) // batch_size

            print(f"\n=== Processing Batch {batch_num}/{total_batches} ===")

            # Process each event and add to batch
            batch_actions = []
            for event in batch:
                tick = event.get("tick", 0)
                call = event.get("call", "")

                try:
                    func_name, args = parse_function_call(call)
                    batch_actions.append(
                        {"tick": tick, "func_name": func_name, "args": args}
                    )
                except Exception as e:
                    print(f"Warning: Failed to parse event {call}: {e}")
                    continue

            # Submit batch and stream results
            if batch_actions:
                batch_results = submit_batch_to_server_streaming(
                    instance, batch_actions, batch_actions[0]["tick"]
                )
                all_results.extend(batch_results)

                # Optional: Process batch-level analytics
                successful_commands = sum(1 for r in batch_results if r["success"])
                print(
                    f"Batch {batch_num} completed: {successful_commands}/{len(batch_results)} successful"
                )

        print("\n=== Final Summary ===")
        print(f"Total events processed: {len(events)}")
        print(f"Total results received: {len(all_results)}")

        successful_results = sum(1 for r in all_results if r["success"])
        print(
            f"Successful operations: {successful_results}/{len(all_results)} ({100 * successful_results / len(all_results):.1f}%)"
        )

        # Optional: Save results summary
        # save_results_summary(all_results, events_file_path)

    except KeyboardInterrupt:
        print("\nExecution interrupted by user")
    except Exception as e:
        print(f"Error during streaming batch execution: {e}")
        raise
    finally:
        instance.batch_manager.deactivate()
        instance.cleanup()


def advanced_streaming_example():
    """Example showing advanced streaming features like progress tracking and early termination."""

    instance = create_factorio_instance()
    instance.reset()

    try:
        print("=== Advanced Streaming Example ===")
        instance.batch_manager.activate()

        # Add a larger batch of commands
        commands = [
            ("move", (5, 5)),
            ("place_entity", ("transport-belt", 5, 6)),
            ("place_entity", ("inserter", 6, 6)),
            ("move", (10, 10)),
            ("inspect_inventory", ()),
            ("place_entity", ("assembling-machine-1", 15, 15)),
            ("move", (20, 20)),
            ("inspect_entities", (20, 20, 5)),
        ]

        namespace = instance.namespace

        for cmd_name, args in commands:
            if hasattr(namespace, cmd_name):
                getattr(namespace, cmd_name)(*args)

        print(f"Submitted {len(commands)} commands for streaming execution...")

        # Stream with progress tracking and conditional processing
        results_by_type = {}
        start_time = time.time()

        for i, result in enumerate(
            instance.batch_manager.submit_batch_and_stream(poll_interval=0.05)
        ):
            elapsed = time.time() - start_time
            progress = (i + 1) / len(commands) * 100

            print(
                f"[{progress:5.1f}% | {elapsed:5.2f}s] {result['command']}: {'✓' if result['success'] else '✗'}"
            )

            # Categorize results
            cmd_type = result["command"]
            if cmd_type not in results_by_type:
                results_by_type[cmd_type] = {"success": 0, "failed": 0}

            if result["success"]:
                results_by_type[cmd_type]["success"] += 1
            else:
                results_by_type[cmd_type]["failed"] += 1

            # Example: Early termination on critical failures
            if result["command"] == "move" and not result["success"]:
                print("⚠️  Movement failed - this might indicate a critical issue")

            # Example: Trigger dependent actions based on specific results
            if result["command"] == "place_entity" and result["success"]:
                print("   ➜ Entity placed successfully, ready for next operations")

        print("\n=== Results Summary by Command Type ===")
        for cmd_type, stats in results_by_type.items():
            total = stats["success"] + stats["failed"]
            success_rate = stats["success"] / total * 100 if total > 0 else 0
            print(
                f"{cmd_type:20}: {stats['success']:2}/{total:2} successful ({success_rate:5.1f}%)"
            )

    except Exception as e:
        print(f"Error in advanced streaming example: {e}")
        raise
    finally:
        instance.batch_manager.deactivate()
        instance.cleanup()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Execute Factorio actions using streaming batch processing"
    )
    parser.add_argument("--events-file", help="Path to events JSON file")
    parser.add_argument(
        "--enable-logging", action="store_true", help="Enable logging to save data"
    )
    parser.add_argument(
        "--speed", type=float, default=1.0, help="Game speed multiplier"
    )
    parser.add_argument(
        "--batch-size", type=int, default=50, help="Number of events per batch"
    )
    parser.add_argument(
        "--example", choices=["basic", "advanced"], help="Run example instead of file"
    )

    args = parser.parse_args()

    if args.example == "basic":
        # Run the basic example from the other file
        from example_batch_streaming import example_batch_streaming

        example_batch_streaming()
    elif args.example == "advanced":
        advanced_streaming_example()
    elif args.events_file:
        execute_events_from_file_streaming(
            args.events_file,
            enable_logging=args.enable_logging,
            speed=args.speed,
            batch_size=args.batch_size,
        )
    else:
        print("Please specify either --events-file or --example")
        parser.print_help()
