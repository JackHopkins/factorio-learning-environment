import json
import math
from pathlib import Path
from typing import List, Dict, Any, Union


def get_time_from_record(record: Dict[str, Any]) -> int:
    """
    Extract time from a record, checking both 't' and 'tick' fields.
    Returns the maximum of the two if both exist.

    Args:
        record: Dictionary that should contain time information

    Returns:
        Time value as integer

    Raises:
        ValueError: If neither 't' nor 'tick' fields exist or are valid
    """
    t_val = record.get("t")
    tick_val = record.get("tick")

    # Convert to int if they exist and are not None
    valid_times = []
    if t_val is not None:
        try:
            valid_times.append(int(t_val))
        except (ValueError, TypeError):
            pass

    if tick_val is not None:
        try:
            valid_times.append(int(tick_val))
        except (ValueError, TypeError):
            pass

    if not valid_times:
        raise ValueError(f"Record has no valid time field ('t' or 'tick'): {record}")

    return max(valid_times)


def is_standard_factorio_resource(entity_name: str) -> bool:
    """
    Check if an entity name represents a standard Factorio resource that can be harvested.

    Args:
        entity_name: The name of the entity

    Returns:
        True if it's a standard harvestable resource, False otherwise
    """
    # Standard resources
    standard_resources = {
        "coal",
        "iron-ore",
        "copper-ore",
        "stone",
        "uranium-ore",
        "crude-oil",
    }

    # Trees (various types)
    tree_prefixes = ["tree-", "dead-tree-"]

    # Rocks (various types)
    rock_names = {"rock-big", "rock-huge", "sand-rock-big"}

    # Check exact matches for standard resources and rocks
    if entity_name in standard_resources or entity_name in rock_names:
        return True

    # Check tree prefixes
    if any(entity_name.startswith(prefix) for prefix in tree_prefixes):
        return True

    # Check for generic tree names
    if entity_name == "tree" or "tree" in entity_name:
        return True

    return False


def decompose_move_to_call(
    start_tick: int,
    end_tick: int,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
) -> List[Dict[str, Any]]:
    """
    Decompose a long move_to call into smaller chunks based on character movement speed.
    Character moves at 8.9 tiles per second (60 ticks per second).

    Args:
        start_tick: Starting tick
        end_tick: Ending tick
        start_x, start_y: Starting position
        end_x, end_y: Ending position

    Returns:
        List of move_to call dictionaries, each representing a 0.5-second (30 tick) movement
    """
    MAX_DISTANCE_PER_HALF_SECOND = 4.45  # tiles per 0.5 seconds (8.9 / 2)
    TICKS_PER_HALF_SECOND = 30

    # Convert coordinates to float to handle string inputs
    start_x = round(float(start_x), 1)
    start_y = round(float(start_y), 1)
    end_x = round(float(end_x), 1)
    end_y = round(float(end_y), 1)
    start_tick = int(start_tick)
    end_tick = int(end_tick)

    # Calculate total distance
    total_distance = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)

    # If distance is small enough for one move, return single call
    if total_distance <= MAX_DISTANCE_PER_HALF_SECOND:
        call = f"move_to(start_tick={start_tick}, end_tick={end_tick}, start_x={start_x}, start_y={start_y}, end_x={end_x}, end_y={end_y})"
        return [{"call": call, "sort_tick": start_tick}]

    # Calculate how many segments we need
    num_segments = math.ceil(total_distance / MAX_DISTANCE_PER_HALF_SECOND)

    # Calculate direction vector
    dx = end_x - start_x
    dy = end_y - start_y

    # Normalize to get unit vector
    unit_dx = dx / total_distance
    unit_dy = dy / total_distance

    calls = []
    current_x = start_x
    current_y = start_y
    current_tick = start_tick

    for i in range(num_segments):
        # Calculate next position
        if i == num_segments - 1:
            # Last segment - go to exact end position
            next_x = end_x
            next_y = end_y
            next_tick = min(current_tick + TICKS_PER_HALF_SECOND, end_tick)
        else:
            # Intermediate segment - move MAX_DISTANCE_PER_HALF_SECOND
            next_x = round(current_x + (unit_dx * MAX_DISTANCE_PER_HALF_SECOND), 1)
            next_y = round(current_y + (unit_dy * MAX_DISTANCE_PER_HALF_SECOND), 1)
            next_tick = current_tick + TICKS_PER_HALF_SECOND

        # Create the call
        call = f"move_to(start_tick={current_tick}, end_tick={next_tick}, start_x={current_x}, start_y={current_y}, end_x={next_x}, end_y={next_y})"
        calls.append({"call": call, "sort_tick": current_tick})

        # Update for next iteration
        current_x = next_x
        current_y = next_y
        current_tick = next_tick

        # If we've reached the end position or end tick, stop
        if (
            abs(current_x - end_x) < 0.1 and abs(current_y - end_y) < 0.1
        ) or current_tick >= end_tick:
            break

    return calls


def handle_action_based_record(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Handle records that use the new action-based schema.

    Args:
        record: The log record dictionary

    Returns:
        List of dictionaries with 'call' and 'sort_tick' fields, or empty list if not an action-based record
    """
    action = record.get("action")

    if action == "craft_item":
        timing = record.get("timing", {})
        crafting = record.get("crafting", {})

        recipe = crafting.get("recipe", "")
        craft_timings = crafting.get("craft_timings", [])

        # If we have detailed craft timings, create individual calls for each completed item
        if craft_timings:
            calls = []
            for craft_timing in craft_timings:
                if craft_timing.get("status") == "completed":
                    queue_tick = craft_timing.get("queue_tick", 0)
                    completion_tick = craft_timing.get("completion_tick", 0)

                    call = f"craft_item(start_tick={queue_tick}, end_tick={completion_tick}, recipe='{recipe}', count=1)"
                    calls.append({"call": call, "sort_tick": queue_tick})
            return calls
        else:
            # Fall back to the original behavior if craft_timings is not available
            start_tick = timing.get("start_tick", 0)
            end_tick = timing.get("end_tick", 0)
            count = crafting.get("total_crafted", 0)

            call = f"craft_item(start_tick={start_tick}, end_tick={end_tick}, recipe='{recipe}', count={count})"
            return [{"call": call, "sort_tick": start_tick}]

    elif action == "move_to_direction":
        player = record.get("player", {})
        start_movement = player.get("start_movement", {})
        end_movement = player.get("end_movement", {})

        start_tick = start_movement.get("tick", 0)
        end_tick = end_movement.get("tick", 0)
        start_x = start_movement.get("x", 0)
        start_y = start_movement.get("y", 0)
        end_x = end_movement.get("x", 0)
        end_y = end_movement.get("y", 0)

        # Return the move data for further processing (decompose vs single call)
        return [
            {
                "action": "move_to_direction",
                "start_tick": start_tick,
                "end_tick": end_tick,
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
            }
        ]

    elif action == "pickup_entity":
        tick = get_time_from_record(record)
        selected_entity = record.get("selected_entity", {})

        entity = selected_entity.get("name", "")
        x = selected_entity.get("x", 0)
        y = selected_entity.get("y", 0)

        call = f"pickup_entity(tick={tick}, entity='{entity}', x={x}, y={y})"
        return [{"call": call, "sort_tick": tick}]

    elif action == "place_entity":
        tick = get_time_from_record(record)
        item = record.get("item", {})
        entity = record.get("entity", {})

        item_name = item.get("name", "")
        x = entity.get("x", 0)
        y = entity.get("y", 0)
        direction = entity.get("direction", {}).get("value", 0)

        call = f"place_entity(tick={tick}, item='{item_name}', x={x}, y={y}, direction={direction})"
        return [{"call": call, "sort_tick": tick}]

    elif action == "extract_item":
        tick = get_time_from_record(record)
        entity = record.get("entity", {})
        items = record.get("items", [])

        entity_name = entity.get("name", "")
        entity_x = entity.get("x", 0)
        entity_y = entity.get("y", 0)
        items_str = str(items) if items else ""

        call = f"extract_item(tick={tick}, entity='{entity_name}', entity_x={entity_x}, entity_y={entity_y}, items='{items_str}')"
        return [{"call": call, "sort_tick": tick}]

    elif action == "insert_item":
        tick = get_time_from_record(record)
        entity = record.get("entity", {})
        items = record.get("items", [])

        entity_name = entity.get("name", "")
        entity_x = entity.get("x", 0)
        entity_y = entity.get("y", 0)
        items_str = str(items) if items else ""

        call = f"insert_item(tick={tick}, entity='{entity_name}', entity_x={entity_x}, entity_y={entity_y}, items='{items_str}')"
        return [{"call": call, "sort_tick": tick}]

    elif action == "rotate_entity":
        tick = get_time_from_record(record)
        entity = record.get("entity", {})
        direction = entity.get("direction", {})

        entity_name = entity.get("name", "")
        x = entity.get("x", 0)
        y = entity.get("y", 0)
        old_direction = direction.get("previous", {}).get("value", 0)
        new_direction = direction.get("new", {}).get("value", 0)

        call = f"rotate_entity(tick={tick}, entity='{entity_name}', x={x}, y={y}, old_direction={old_direction}, new_direction={new_direction})"
        return [{"call": call, "sort_tick": tick}]

    elif action == "set_entity_recipe":
        tick = get_time_from_record(record)
        entity = record.get("entity", {})
        player = record.get("player", {})

        entity_name = entity.get("name", "")
        new_recipe = entity.get("new_recipe", "")
        x = player.get("x", 0)
        y = player.get("y", 0)

        call = f"set_entity_recipe(tick={tick}, entity='{entity_name}', new_recipe='{new_recipe}', x={x}, y={y})"
        return [{"call": call, "sort_tick": tick}]

    elif action == "research_started":
        tick = get_time_from_record(record)
        research = record.get("research", "")

        call = f"set_research(tick={tick}, research='{research}')"
        return [{"call": call, "sort_tick": tick}]

    # Not an action-based record
    return []


def transform_record_to_python_call(
    record: Dict[str, Any], source_file: str
) -> List[Dict[str, Any]]:
    """
    Transform a log record into Python function call strings based on the source file type.

    Args:
        record: The log record dictionary
        source_file: Name of the source file (without extension)

    Returns:
        List of dictionaries with 'call' and 'sort_tick' fields, or empty list if record should be ignored
    """
    # Get the base filename without extension
    file_type = source_file.replace(".jsonl", "")

    # Skip core-meta files entirely
    if file_type == "core-meta":
        return []

    # Handle new action-based schema
    action_result = handle_action_based_record(record)
    if action_result:
        # Special handling for move_to_direction - needs decomposition
        if action_result[0].get("action") == "move_to_direction":
            move_data = action_result[0]
            return decompose_move_to_call(
                move_data["start_tick"],
                move_data["end_tick"],
                move_data["start_x"],
                move_data["start_y"],
                move_data["end_x"],
                move_data["end_y"],
            )
        return action_result

    tick = get_time_from_record(record)

    if file_type == "harvest_resource_collated":
        start_tick = tick - record.get("duration_ticks", 0)
        entity = record.get("entity", "")
        x = record.get("x", 0)
        y = record.get("y", 0)

        # Check if this is a standard Factorio resource
        if is_standard_factorio_resource(entity):
            call = f"harvest_resource(start_tick={start_tick}, end_tick={tick}, entity='{entity}', x={x}, y={y})"
            return [{"call": call, "sort_tick": start_tick}]
        else:
            # For non-standard resources, treat as pickup_entity
            call = f"pickup_entity(tick={tick}, entity='{entity}', x={x}, y={y})"
            return [{"call": call, "sort_tick": tick}]

    # Unknown file type, skip
    return []


def transform_record_to_python_call_no_decompose(
    record: Dict[str, Any], source_file: str
) -> List[Dict[str, Any]]:
    """
    Transform a log record into Python function call strings based on the source file type.
    This version does NOT decompose move_to calls.

    Args:
        record: The log record dictionary
        source_file: Name of the source file (without extension)

    Returns:
        List of dictionaries with 'call' and 'sort_tick' fields, or empty list if record should be ignored
    """
    # Get the base filename without extension
    file_type = source_file.replace(".jsonl", "")

    # Skip core-meta files entirely
    if file_type == "core-meta":
        return []

    # Handle new action-based schema
    action_result = handle_action_based_record(record)
    if action_result:
        # Special handling for move_to_direction - create single call instead of decomposing
        if action_result[0].get("action") == "move_to_direction":
            move_data = action_result[0]
            call = f"move_to(start_tick={move_data['start_tick']}, end_tick={move_data['end_tick']}, start_x={move_data['start_x']}, start_y={move_data['start_y']}, end_x={move_data['end_x']}, end_y={move_data['end_y']})"
            return [{"call": call, "sort_tick": move_data["start_tick"]}]
        return action_result

    tick = get_time_from_record(record)

    if file_type == "harvest_resource_collated":
        start_tick = tick - record.get("duration_ticks", 0)
        entity = record.get("entity", "")
        x = record.get("x", 0)
        y = record.get("y", 0)

        # Check if this is a standard Factorio resource
        if is_standard_factorio_resource(entity):
            call = f"harvest_resource(start_tick={start_tick}, end_tick={tick}, entity='{entity}', x={x}, y={y})"
        else:
            # For non-standard resources, treat as pickup_entity
            call = f"pickup_entity(tick={tick}, entity='{entity}', x={x}, y={y})"

        return [{"call": call, "sort_tick": start_tick}]

    # Unknown file type, skip
    return []


def read_and_combine_jsonls(
    folder_path: Union[str, Path], max_time: int = None
) -> List[Dict[str, Any]]:
    """
    Read all JSONL files from a folder, combine them, sort by time (t or tick field),
    and optionally filter up to a certain time.

    Args:
        folder_path: Path to the folder containing JSONL files
        max_time: Maximum time threshold (inclusive). If None, no filtering is applied.

    Returns:
        List of dictionaries sorted by time field in ascending order
    """
    folder_path = Path(folder_path)

    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    if not folder_path.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")

    all_records = []
    crash_site_filtered = 0

    # Find all JSONL files in the folder
    jsonl_files = list(folder_path.glob("*.jsonl"))

    if not jsonl_files:
        print(f"Warning: No JSONL files found in {folder_path}")
        return all_records

    # Read each JSONL file
    for jsonl_file in jsonl_files:
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:  # Skip empty lines
                        try:
                            record = json.loads(line)

                            # Skip records containing 'crash-site' anywhere in the data
                            record_str = json.dumps(record, default=str).lower()
                            if "crash-site" in record_str:
                                crash_site_filtered += 1
                                continue

                            # Validate that record has a valid time field
                            try:
                                get_time_from_record(record)
                            except ValueError as e:
                                print(
                                    f"Warning: Skipping record on line {line_num} in {jsonl_file.name}: {e}"
                                )
                                continue

                            # Add source file information for debugging
                            record["_source_file"] = jsonl_file.name
                            all_records.append(record)
                        except json.JSONDecodeError as e:
                            print(
                                f"Warning: Invalid JSON on line {line_num} in {jsonl_file.name}: {e}"
                            )
                            continue
        except Exception as e:
            print(f"Error reading file {jsonl_file.name}: {e}")
            continue

    # Filter by time if max_time is specified
    if max_time is not None:
        all_records = [
            record for record in all_records if get_time_from_record(record) <= max_time
        ]

    # Sort by time field
    all_records.sort(key=get_time_from_record)

    print(f"Loaded {len(all_records)} records from {len(jsonl_files)} JSONL files")
    if crash_site_filtered > 0:
        print(f"Filtered out {crash_site_filtered} records containing 'crash-site'")
    if max_time is not None:
        print(f"Filtered to records with time <= {max_time}")

    return all_records


def save_python_calls(
    records: List[Dict[str, Any]], output_path: Union[str, Path], decompose: bool = True
) -> None:
    """
    Transform records to Python function calls and save to JSONL file.

    Args:
        records: List of record dictionaries
        output_path: Path to the output JSONL file
        decompose: Whether to decompose move_to calls into smaller chunks
    """
    output_path = Path(output_path)

    python_calls = []
    skipped_count = 0

    # Choose which transform function to use
    transform_func = (
        transform_record_to_python_call
        if decompose
        else transform_record_to_python_call_no_decompose
    )

    def get_function_priority(call_string: str) -> int:
        """Get priority for function calls to ensure proper ordering on same tick."""
        if call_string.startswith("pickup_entity("):
            return 0  # Highest priority - execute first
        elif call_string.startswith("place_entity("):
            return 1  # Lower priority - execute after pickup
        else:
            return 2  # Default priority for other functions

    for record in records:
        source_file = record.get("_source_file", "")
        call_data_list = transform_func(record, source_file)

        if call_data_list:  # Check if call_data_list is not empty
            for call_data in call_data_list:
                python_calls.append(
                    {"tick": call_data["sort_tick"], "call": call_data["call"]}
                )
        else:
            skipped_count += 1

    # Sort by tick first, then by function priority to ensure pickup_entity comes before place_entity
    python_calls.sort(key=lambda x: (x["tick"], get_function_priority(x["call"])))

    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for call_record in python_calls:
            f.write(json.dumps(call_record) + "\n")

    decompose_text = (
        "with decomposed move_to" if decompose else "without decomposed move_to"
    )
    print(
        f"Saved {len(python_calls)} Python function calls ({decompose_text}) to {output_path}"
    )
    print(f"Skipped {skipped_count} records (ignored file types or filtered events)")


def get_time_range(records: List[Dict[str, Any]]) -> tuple:
    """
    Get the time range (min, max) from a list of records.

    Args:
        records: List of dictionaries with time fields

    Returns:
        Tuple of (min_time, max_time)
    """
    if not records:
        return (0, 0)

    times = [get_time_from_record(record) for record in records]
    return (min(times), max(times))


def save_combined_jsonl(
    records: List[Dict[str, Any]], output_path: Union[str, Path]
) -> None:
    """
    Save a list of records to a JSONL file.

    Args:
        records: List of dictionaries to save
        output_path: Path to the output JSONL file
    """
    output_path = Path(output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            # Remove the source file metadata before saving
            record_copy = record.copy()
            record_copy.pop("_source_file", None)
            f.write(json.dumps(record_copy) + "\n")

    print(f"Saved {len(records)} records to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-time", type=int, required=True, help="Maximum tick to process"
    )
    args = parser.parse_args()

    # Example usage
    folder_path = "/Users/neel/Desktop/Work/factorio-data-collector/factorio_replays/factorio_replay_20250723_110424"
    max_time = args.max_time

    # Read and combine all JSONL files
    combined_records = read_and_combine_jsonls(folder_path, max_time)

    # Create output directories
    runnable_dir = Path("_runnable_actions")
    extracted_dir = Path("_extracted")
    runnable_dir.mkdir(exist_ok=True)
    extracted_dir.mkdir(exist_ok=True)

    # Save decomposed version to _runnable_actions (for execution)
    runnable_output = runnable_dir / f"combined_events_py_{max_time}.jsonl"
    save_python_calls(combined_records, runnable_output, decompose=True)

    # Save non-decomposed version to _extracted (for analysis)
    extracted_output = extracted_dir / f"combined_events_py_{max_time}.jsonl"
    save_python_calls(combined_records, extracted_output, decompose=False)

    # Print time range
    min_time, max_time_actual = get_time_range(combined_records)
    print(f"Time range: {min_time} to {max_time_actual}")

    # Optionally save the original combined results
    save_combined_jsonl(combined_records, "combined_events.jsonl")
