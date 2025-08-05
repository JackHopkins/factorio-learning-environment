import json
from typing import Dict, Any, List
from fle.env import FactorioInstance

# Import moved functionality from specialized modules
from fle.data.replays.action_converter import ActionConverter


def load_events(file_path: str) -> List[Dict[str, Any]]:
    """Load events from a JSONL file."""
    events = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def create_factorio_instance(max_concurrent_batches=1):
    """Create and return a FactorioInstance with support for concurrent batch processing."""
    return FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        cache_scripts=True,
        fast=True,
        regenerate="map",
        inventory={
            "iron-plate": 8,
            "stone-furnace": 1,
            "burner-mining-drill": 1,
            "wood": 1,
            "iron-ore": 1,
        },
        max_concurrent_batches=max_concurrent_batches,
    )


# Legacy function aliases for backward compatibility
def parse_function_call(call_string: str) -> tuple[str, Dict[str, Any]]:
    """Parse a function call string into function name and arguments.

    This function has been moved to ActionConverter.parse_function_call().
    This alias is provided for backward compatibility.
    """
    return ActionConverter.parse_function_call(call_string)


def convert_run_actions_args_to_tool_args(
    func_name: str, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Convert run_actions.py argument format to tool argument format.

    This function has been moved to ActionConverter.convert_legacy_args_to_tool_args().
    This alias is provided for backward compatibility.
    """
    return ActionConverter.convert_legacy_args_to_tool_args(func_name, args)
