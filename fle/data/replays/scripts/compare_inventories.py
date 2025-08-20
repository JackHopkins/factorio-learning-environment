#!/usr/bin/env python3
"""
Compare inventories between fle_actions_events and replay_inventory datasets at common tick times.
"""

import json
import re
from typing import Dict


def parse_lua_inventory(lua_string: str) -> Dict[str, int]:
    """Parse Lua table string into Python dictionary."""
    if not lua_string or lua_string.strip() == "":
        return {}

    # Remove outer braces and split by commas
    content = lua_string.strip()
    if content.startswith("{") and content.endswith("}"):
        content = content[1:-1]

    items = {}
    # Use regex to find [key] = value pairs
    pattern = r'\["([^"]+)"\]\s*=\s*(\d+)'
    matches = re.findall(pattern, content)

    for item_name, quantity in matches:
        items[item_name] = int(quantity)

    return items


def load_fle_actions_events(filename: str) -> Dict[int, Dict[str, int]]:
    """Load fle_actions_events data and extract tick -> inventory mapping."""
    tick_to_inventory = {}

    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            data = json.loads(line)
            tick = data.get("tick")
            inventory = data.get("inventory", {})

            if tick is not None and inventory:
                tick_to_inventory[tick] = inventory

    return tick_to_inventory


def load_replay_inventory(filename: str) -> Dict[int, Dict[str, int]]:
    """Load replay_inventory data and extract tick -> inventory mapping."""
    tick_to_inventory = {}

    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            data = json.loads(line)
            tick = data.get("t")

            # Skip if there's an inventory error or no inventory_raw
            if "inventory_error" in data or "inventory_raw" not in data:
                continue

            inventory_raw = data.get("inventory_raw", "")
            inventory = parse_lua_inventory(inventory_raw)

            if tick is not None and inventory:
                tick_to_inventory[tick] = inventory

    return tick_to_inventory


def compare_inventories(
    fle_actions_inv: Dict[str, int], replay_inv: Dict[str, int]
) -> Dict[str, tuple[str, str]]:
    """Compare two inventories and return differences.

    Returns:
        dict: {item_name: (fle_actions_display, replay_display)} for items that differ
    """
    differences = {}
    all_items = set(fle_actions_inv.keys()) | set(replay_inv.keys())

    for item in all_items:
        fle_actions_qty = fle_actions_inv.get(item, 0)
        replay_qty = replay_inv.get(item, 0)

        if fle_actions_qty != replay_qty:
            if fle_actions_qty > replay_qty:
                fle_actions_display = f"+{fle_actions_qty - replay_qty}"
                replay_display = "."
            else:
                fle_actions_display = "."
                replay_display = f"+{replay_qty - fle_actions_qty}"

            differences[item] = (fle_actions_display, replay_display)

    return differences


def main():
    # Load both datasets
    print("Loading fle_actions_events data...")
    fle_actions_events = load_fle_actions_events(
        "_runnable_actions/combined_events_py_10027_periodic_data.jsonl"
    )

    print("Loading replay_inventory data...")
    replay_inventory = load_replay_inventory(
        "replay_observations/inspect_inventory.jsonl"
    )

    # Find common ticks
    common_ticks = set(fle_actions_events.keys()) & set(replay_inventory.keys())
    common_ticks = sorted(common_ticks)

    print(f"Found {len(common_ticks)} common tick times")
    print(f"Common ticks: {common_ticks}")

    # Compare inventories at common ticks and group consecutive identical differences
    differences_found = 0
    current_differences = None
    current_tick_range = []

    def print_differences_group(tick_range, differences):
        """Print a group of ticks with the same differences."""
        nonlocal differences_found
        differences_found += 1

        if len(tick_range) == 1:
            print(f"\n=== DIFFERENCES AT TICK {tick_range[0]} ===")
        else:
            print(
                f"\n=== DIFFERENCES AT TICK(S) {tick_range[0]} - {tick_range[-1]} ==="
            )

        print("Item                    FLE_Actions Replay")
        print("-" * 45)

        for item in sorted(differences.keys()):
            fle_actions_display, replay_display = differences[item]
            print(f"{item:<20}    {fle_actions_display:>11}    {replay_display:>6}")

    for tick in common_ticks:
        fle_actions_inv = fle_actions_events[tick]
        replay_inv = replay_inventory[tick]

        differences = compare_inventories(fle_actions_inv, replay_inv)

        if differences:
            # Check if differences are the same as the previous tick
            if current_differences == differences:
                # Same differences, add to current range
                current_tick_range.append(tick)
            else:
                # Different differences, print previous group if it exists
                if current_differences is not None and current_tick_range:
                    print_differences_group(current_tick_range, current_differences)

                # Start new group
                current_differences = differences
                current_tick_range = [tick]
        else:
            # No differences, print previous group if it exists
            if current_differences is not None and current_tick_range:
                print_differences_group(current_tick_range, current_differences)
                current_differences = None
                current_tick_range = []

    # Print the final group if it exists
    if current_differences is not None and current_tick_range:
        print_differences_group(current_tick_range, current_differences)

    if differences_found == 0:
        print("\n✅ No differences found! All inventories match at common tick times.")
    else:
        print(f"\n❌ Found differences at {differences_found} group(s) of tick times.")


if __name__ == "__main__":
    main()
