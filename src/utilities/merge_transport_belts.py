from collections import defaultdict
from typing import List

from factorio_entities import TransportBelt, BeltGroup, Position


def agglomerate_transport_belts(belts: List[TransportBelt]) -> List[BeltGroup]:
    """
    Group contiguous transport belts into BeltGroup objects.

    Args:
        belts: List of TransportBelt objects to group

    Returns:
        List of BeltGroup objects, each containing connected belts
    """
    # Create position-to-belt mapping for quick lookups
    position_to_belt = {}
    for belt in belts:
        position_to_belt[(belt.position.x, belt.position.y)] = belt

    # Keep track of which belts we've processed
    processed_belts = set()
    belt_groups = []

    def find_connected_belts(start_belt: TransportBelt) -> List[TransportBelt]:
        """Find all belts connected to the starting belt using DFS"""
        connected = []
        to_process = [start_belt]
        seen = set()

        while to_process:
            current_belt = to_process.pop()
            if (current_belt.position.x, current_belt.position.y) in seen:
                continue

            seen.add((current_belt.position.x, current_belt.position.y))
            connected.append(current_belt)

            # Check input position connection
            input_pos = current_belt.input_position
            if (input_pos.x, input_pos.y) in position_to_belt:
                input_belt = position_to_belt[(input_pos.x, input_pos.y)]
                if input_belt.output_position == current_belt.position:
                    to_process.append(input_belt)

            # Check output position connection
            output_pos = current_belt.output_position
            if (output_pos.x, output_pos.y) in position_to_belt:
                output_belt = position_to_belt[(output_pos.x, output_pos.y)]
                if output_belt.input_position == current_belt.position:
                    to_process.append(output_belt)

        return connected

    # Process each unprocessed belt
    for belt in belts:
        if (belt.position.x, belt.position.y) in processed_belts:
            continue

        # Find all belts connected to this one
        connected_belts = find_connected_belts(belt)

        # Mark all these belts as processed
        processed_belts.update((belt.position.x, belt.position.y) for belt in connected_belts)

        # Create a new belt group
        input_positions, output_positions = _calculate_endpoints(connected_belts)
        belt_groups.append(
            BeltGroup(belts=connected_belts,
                      input_positions=input_positions,
                      output_positions=output_positions,
                      position=connected_belts[0].position))

        # Merge belt groups that should be connected
        merged = True
        while merged:
            merged = False
            for i, group1 in enumerate(belt_groups):
                if merged:
                    break

                for j, group2 in enumerate(belt_groups[i + 1:], i + 1):
                    should_merge = False

                    # Check if any output position of group1 matches a belt position in group2
                    for belt in group2.belts:
                        belt_pos = (belt.position.x, belt.position.y)
                        for out_pos in group1.output_positions:
                            if (out_pos.x, out_pos.y) == belt_pos:
                                should_merge = True
                                break

                    # Check if any input position of group2 matches a belt position in group1
                    if not should_merge:
                        for belt in group1.belts:
                            belt_pos = (belt.position.x, belt.position.y)
                            for in_pos in group2.input_positions:
                                if (in_pos.x, in_pos.y) == belt_pos:
                                    should_merge = True
                                    break

                    if should_merge:
                        # Merge the groups
                        merged_belts = group1.belts + group2.belts
                        input_positions, output_positions = _calculate_endpoints(merged_belts)
                        merged_group = BeltGroup(belts=merged_belts,
                                                 input_positions=input_positions,
                                                 output_positions=output_positions,
                                                 position=group1.position)

                        # Replace group1 with merged group and remove group2
                        belt_groups[i] = merged_group
                        belt_groups.pop(j)
                        merged = True
                        break

    return belt_groups


def _calculate_endpoints(belt_group):
    """
    Calculate the input and output positions that connect to other belt groups.
    Ensures single output and proper input handling based on belt flow.
    """
    position_counts = defaultdict(int)
    input_positions = set()
    output_positions = set()

    # Create a map of positions to belts for quick lookup
    pos_to_belt = {(belt.position.x, belt.position.y): belt for belt in belt_group}

    # Count how many times each position appears as input or output
    for belt in belt_group:
        position_counts[(belt.input_position.x, belt.input_position.y)] += 1
        position_counts[(belt.output_position.x, belt.output_position.y)] += 1

    # Find potential endpoints (positions that appear only once)
    for belt in belt_group:
        input_pos = (belt.input_position.x, belt.input_position.y)
        output_pos = (belt.output_position.x, belt.output_position.y)

        # If input position is not the position of any belt in the group
        # and it appears only once, it's a true input
        if input_pos not in pos_to_belt and position_counts[input_pos] == 1:
            input_positions.add(input_pos)

        # If output position is not the position of any belt in the group
        # and it appears only once, it's a potential output
        if output_pos not in pos_to_belt and position_counts[output_pos] == 1:
            output_positions.add(output_pos)

    # From the potential outputs, find the one that's furthest downstream
    # An output is furthest downstream if no belt in the group can connect to it
    final_output = None
    for output_pos in output_positions:
        is_final = True
        for belt in belt_group:
            if (belt.input_position.x, belt.input_position.y) == output_pos:
                is_final = False
                break
        if is_final:
            final_output = output_pos
            break

    final_input = None
    for input_pos in input_positions:
        is_final = True
        for belt in belt_group:
            if (belt.output_position.x, belt.output_position.y) == input_pos:
                is_final = False
                break
        if is_final:
            final_input = input_pos
            break

    # Convert back into Position objects
    if final_input:
        input_positions = [Position(x=x, y=y) for x, y in [final_input]]
    else:
        input_positions = [Position(x=x, y=y) for x, y in [input_positions]]
    output_positions = [Position(x=x, y=y) for x, y in [final_output]] if final_output else []

    return input_positions, output_positions