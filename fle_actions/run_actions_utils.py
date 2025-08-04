import json
import re
import ast
import time
from pathlib import Path
from typing import Dict, Any, List
from fle.env import FactorioInstance
from fle.env.entities import Direction, Position


class TickScheduler:
    """Handles real-time tick scheduling at 60 ticks per second."""

    def __init__(self, speed: float = 1.0):
        self.start_time = None
        self.tick_duration = 1.0 / 60.0 / speed  # 60 ticks per second

    def start(self):
        """Start the tick timer."""
        self.start_time = time.time()

    def wait_for_tick(self, target_tick: int):
        """Wait until the specified tick time has arrived."""
        if self.start_time is None:
            raise ValueError("Scheduler not started. Call start() first.")

        target_time = self.start_time + (target_tick * self.tick_duration)
        current_time = time.time()

        if target_time > current_time:
            sleep_duration = target_time - current_time
            print(
                f"\033[92mWaiting {sleep_duration:.3f}s for tick {target_tick}\033[0m"
            )
            time.sleep(sleep_duration)
        else:
            # If we're behind schedule, note it but don't wait
            delay = current_time - target_time
            print(
                f"\033[94mWarning: Tick {target_tick} is {delay:.3f}s behind schedule\033[0m"
            )

    def get_current_tick(self) -> int:
        """Get the current tick based on elapsed time."""
        if self.start_time is None:
            return 0
        elapsed = time.time() - self.start_time
        return int(elapsed / self.tick_duration)


# Global file handles for logging
entities_log_file = None
inventory_log_file = None


def initialize_logging(log_dir: str = "logs"):
    """Initialize logging files for entities and inventory data."""
    global entities_log_file, inventory_log_file

    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Initialize log files
    entities_log_file = open(log_path / "entities_log.jsonl", "w")
    inventory_log_file = open(log_path / "inventory_log.jsonl", "w")

    print(
        f"Initialized logging to {log_path}/entities_log.jsonl and {log_path}/inventory_log.jsonl"
    )


def cleanup_logging():
    """Close logging files."""
    global entities_log_file, inventory_log_file

    if entities_log_file:
        entities_log_file.close()
        entities_log_file = None

    if inventory_log_file:
        inventory_log_file.close()
        inventory_log_file = None


def log_data(log_file, tick: int, data: Any):
    """Log data to a file in JSONL format for pandas reading."""
    if log_file:
        log_entry = {"tick": tick, "data": data}
        log_file.write(json.dumps(log_entry) + "\n")
        log_file.flush()  # Ensure data is written immediately


def parse_function_call(call_string: str) -> tuple[str, Dict[str, Any]]:
    """Parse a function call string into function name and arguments."""
    # Extract function name and arguments using regex
    match = re.match(r"(\w+)\((.*)\)", call_string)
    if not match:
        raise ValueError(f"Invalid function call format: {call_string}")

    func_name = match.group(1)
    args_string = match.group(2)

    # Parse arguments
    args = {}
    if args_string.strip():
        # Split arguments by comma, but handle nested structures
        arg_pairs = []
        paren_count = 0
        bracket_count = 0
        brace_count = 0
        current_arg = ""

        for char in args_string:
            if char in "([{":
                if char == "(":
                    paren_count += 1
                elif char == "[":
                    bracket_count += 1
                elif char == "{":
                    brace_count += 1
            elif char in ")]}":
                if char == ")":
                    paren_count -= 1
                elif char == "]":
                    bracket_count -= 1
                elif char == "}":
                    brace_count -= 1
            elif (
                char == ","
                and paren_count == 0
                and bracket_count == 0
                and brace_count == 0
            ):
                arg_pairs.append(current_arg.strip())
                current_arg = ""
                continue

            current_arg += char

        if current_arg.strip():
            arg_pairs.append(current_arg.strip())

        # Parse each argument pair
        for arg_pair in arg_pairs:
            if "=" in arg_pair:
                key, value = arg_pair.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Try to evaluate the value safely
                try:
                    # Handle string literals
                    if value.startswith("'") and value.endswith("'"):
                        args[key] = value[1:-1]
                    elif value.startswith('"') and value.endswith('"'):
                        args[key] = value[1:-1]
                    # Handle lists and dicts (for items parameter)
                    elif value.startswith("[") or value.startswith("{"):
                        args[key] = ast.literal_eval(value)
                    # Handle numbers
                    elif value.replace(".", "").replace("-", "").isdigit():
                        if "." in value:
                            args[key] = float(value)
                        else:
                            args[key] = int(value)
                    else:
                        # Default to string
                        args[key] = value
                except (ValueError, SyntaxError):
                    # If evaluation fails, keep as string
                    args[key] = value

    return func_name, args


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
        },
        max_concurrent_batches=max_concurrent_batches,
    )


def convert_run_actions_args_to_tool_args(
    func_name: str, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Convert run_actions.py argument format to tool argument format."""

    if func_name == "harvest_resource":
        return {
            "position": Position(args["x"], args["y"]),
            "quantity": args.get("quantity", 1),
        }

    elif func_name == "move_to":
        return {"position": Position(args["end_x"], args["end_y"])}

    elif func_name == "extract_item":
        # Parse the items JSON and get the first item
        items_str = args["items"].replace("'", '"')
        items_list = json.loads(items_str)
        if items_list:
            item_info = items_list[0]
            from fle.env.game_types import prototype_by_name

            entity = prototype_by_name.get(item_info["item"], item_info["item"])

            return {
                "entity": entity,
                "source": Position(args["entity_x"], args["entity_y"]),
                "quantity": item_info.get("count", 1),
            }

    elif func_name == "place_entity":
        # For place_entity, convert item to entity and create Position
        from fle.env.game_types import prototype_by_name

        item_name = args["item"]
        entity = prototype_by_name.get(item_name, item_name)

        result = {"entity": entity, "position": Position(args["x"], args["y"])}

        if "direction" in args:
            result["direction"] = Direction.from_int(int(args["direction"]))

        return result

    elif func_name == "craft_item":
        result = {}
        if "recipe" in args:
            result["entity"] = args["recipe"]
        if "count" in args:
            result["quantity"] = args["count"]
        return result

    elif func_name == "insert_item":
        # Parse the items JSON and get the first item
        items_str = args["items"].replace("'", '"')
        items_list = json.loads(items_str)
        if items_list:
            item_info = items_list[0]
            from fle.env.game_types import prototype_by_name

            entity = prototype_by_name.get(item_info["item"], item_info["item"])

            return {
                "entity": entity,
                "target": Position(args["entity_x"], args["entity_y"]),
                "quantity": item_info.get("count", 1),
            }

    elif func_name == "pickup_entity":
        from fle.env.game_types import prototype_by_name

        entity_name = args["entity"]
        entity = prototype_by_name.get(entity_name, entity_name)

        return {"entity": entity, "position": Position(args["x"], args["y"])}

    elif func_name == "set_research":
        from fle.env.game_types import Technology

        technology_name = args["technology"]

        try:
            if hasattr(technology_name, "value"):
                technology = technology_name
            else:
                technology = Technology(technology_name)
        except (ValueError, AttributeError):
            technology = technology_name

        return {"technology": technology}

    # Default: return args as-is
    return args


def wait_for_tick_completion(instance: FactorioInstance, target_tick: int):
    """Wait for the server to reach a specific tick."""
    current_tick = instance.get_elapsed_ticks()
    while current_tick < target_tick:
        time.sleep(0.1)  # Poll every 100ms
        current_tick = instance.get_elapsed_ticks()
