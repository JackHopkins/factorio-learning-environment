from pathlib import Path
from typing import Dict, Any, List
from fle.env import FactorioInstance

from run_actions_utils import (
    load_events,
    create_factorio_instance,
    parse_function_call,
    convert_run_actions_args_to_tool_args,
    wait_for_tick_completion,
    initialize_logging,
    cleanup_logging,
)
from log_analyzer import analyze_logs_example


def convert_tool_args_to_server_args(
    func_name: str, tool_args: Dict[str, Any]
) -> List[Any]:
    """Convert tool arguments back to server argument format."""

    if func_name == "harvest_resource":
        position = tool_args["position"]
        quantity = tool_args.get("quantity", 1)
        radius = tool_args.get("radius", 10)
        return [position.x, position.y, quantity, radius]

    elif func_name == "move_to":
        position = tool_args["position"]
        # For now, we'll simplify and just pass coordinates
        # In reality, move_to needs path_handle, etc.
        return [position.x, position.y]

    elif func_name == "extract_item":
        entity = tool_args["entity"]
        source = tool_args["source"]
        quantity = tool_args.get("quantity", 5)

        if hasattr(entity, "value"):
            entity_name = entity.value[0]
        else:
            entity_name = str(entity)

        return [entity_name, quantity, source.x, source.y, None]

    elif func_name == "place_entity":
        entity = tool_args["entity"]
        position = tool_args["position"]
        direction = tool_args.get("direction")

        if hasattr(entity, "value"):
            entity_name = entity.value[0]
        else:
            entity_name = str(entity)

        direction_int = direction.value if direction else 0
        return [entity_name, position.x, position.y, direction_int]

    # Default: try to extract values from tool_args
    return list(tool_args.values())


def submit_batch_to_server(
    instance: FactorioInstance, batch: List[Dict], start_tick: int
):
    """Submit a batch of actions to the server for scheduled execution."""

    # Convert batch actions to server format
    for action in batch:
        tick = action["tick"]
        func_name = action["func_name"]
        args = action["args"]

        # Process arguments using the conversion function
        processed_args = convert_run_actions_args_to_tool_args(func_name, args)

        # Get the actual tool and call it with batch tick (this would be done when tools support _tick parameter)
        namespace = instance.namespace
        if hasattr(namespace, func_name):
            tool = getattr(namespace, func_name)
            assert tool
            # For now, we'll simulate what would happen when tools support batch mode
            # In the future: tool(**processed_args, _tick=tick)
            print(f"Would batch: {func_name} at tick {tick} with args {processed_args}")

        # For now, directly add to batch manager (this will work once tools support batch mode)
        if hasattr(instance.batch_manager, "add_tool_command"):
            # Convert tool args back to server args format (this is temporary)
            server_args = convert_tool_args_to_server_args(func_name, processed_args)
            instance.batch_manager.add_tool_command(tick, func_name, 1, *server_args)

    # Submit the batch
    print(f"Submitting batch of {len(batch)} actions starting at tick {start_tick}")
    results = instance.batch_manager.submit_batch()

    # Wait for batch completion
    max_tick = max(action["tick"] for action in batch)
    wait_for_tick_completion(instance, max_tick)

    return results


def execute_events_from_file_batched(
    events_file_path: str,
    enable_logging: bool = False,
    speed: float = 1.0,
    batch_size: int = 50,
):
    """Execute events using batch processing for better performance."""

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
        print(f"Starting batch execution with batch size {batch_size}")
        print(f"Total events to process: {len(events)}")

        # Process events in batches
        for i in range(0, len(events), batch_size):
            batch = events[i : i + batch_size]

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

            # Submit batch to server
            if batch_actions:
                submit_batch_to_server(
                    instance, batch_actions, batch_actions[0]["tick"]
                )

        print(f"\nCompleted batch execution of {len(events)} events")

    except KeyboardInterrupt:
        print("\nExecution interrupted by user")
    except Exception as e:
        print(f"Error during batch execution: {e}")
        raise
    finally:
        # Always deactivate batch mode and cleanup
        instance.batch_manager.deactivate()
        if enable_logging:
            cleanup_logging()
        instance.cleanup()
        print("Instance and logging cleaned up")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Execute Factorio events using batch processing"
    )
    parser.add_argument(
        "--max-time",
        type=int,
        default=10000,
        help="Maximum tick time to include in events file",
    )
    parser.add_argument(
        "--analyze-logs",
        action="store_true",
        help="Analyze existing log files instead of running simulation",
    )
    parser.add_argument(
        "--enable-logging",
        action="store_true",
        help="Enable logging of entities and inventory data to files",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Game speed multiplier (default: 1.0, higher = faster)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of events to process in each batch (default: 50)",
    )
    args = parser.parse_args()

    if args.analyze_logs:
        analyze_logs_example()
    else:
        # Default to the combined_events_py.jsonl file in the same directory
        current_dir = Path(__file__).parent
        events_file = (
            current_dir
            / "_runnable_actions"
            / f"combined_events_py_{args.max_time}.jsonl"
        )

        if events_file.exists():
            execute_events_from_file_batched(
                str(events_file),
                enable_logging=args.enable_logging,
                speed=args.speed,
                batch_size=args.batch_size,
            )
        else:
            print(f"Events file not found: {events_file}")
            print("Please provide the path to your events JSONL file")
