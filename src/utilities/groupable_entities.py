from collections import defaultdict
from typing import List

from factorio_entities import TransportBelt, BeltGroup, Position, Entity, EntityGroup, PipeGroup, Inventory, \
    EntityStatus
from factorio_types import Prototype


def _deduplicate_entities(entities: List[Entity]) -> List[Entity]:
    """
    Remove duplicate entities while maintaining the original order.
    Later entities with the same position override earlier ones.
    """
    unique_entities = []
    seen = set()
    for entity in reversed(entities):
        position = (entity.position.x, entity.position.y)
        if position not in seen:
            unique_entities.append(entity)
            seen.add(position)
    return list(reversed(unique_entities))


def _construct_group(entities: List[Entity],
                     prototype: Prototype,
                     input_positions: List[Position],
                     output_positions: List[Position],
                     position: Position) -> EntityGroup:
    if prototype == Prototype.TransportBelt or entities[0].prototype == Prototype.TransportBelt:
        inventory = Inventory()
        for entity in entities:
            if hasattr(entity, 'inventory') and entity.inventory:  # Check if inventory exists and is not empty
                entity_inventory = entity.inventory
                for item, value in entity_inventory.items():
                    current_value = inventory.get(item, 0)  # Get current value or 0 if not exists
                    inventory[item] = current_value + value  # Add new value

        if any(entity.warnings and entity.warnings[0] == 'full' for entity in entities):
            status = EntityStatus.FULL_OUTPUT
        else:
            status = EntityStatus.WORKING

        if not inventory:
            status = EntityStatus.EMPTY

        return BeltGroup(belts=entities,
                         inventory=inventory,
                         input_positions=input_positions,
                         output_positions=output_positions,
                         status = status,
                         position=position)
    elif prototype == Prototype.Pipe or entities[0].prototype == Prototype.Pipe:
        return PipeGroup(pipes=entities,
                         input_positions=input_positions,
                         position=position)



# def agglomerate_groupable_entities(belts: List[Entity]) -> List[BeltGroup]:
#     """
#     Group contiguous transport belts into BeltGroup objects by finding end belts
#     and tracing backwards through their inputs.
#
#     Args:
#         belts: List of TransportBelt objects to group
#
#     Returns:
#         List of BeltGroup objects, each containing connected belts
#     """
#     if not belts:
#         return []
#
#     prototype = belts[0].prototype if isinstance(belts[0], Entity) else Prototype.TransportBelt
#
#     # Create position-to-belt mapping for quick lookups
#     position_to_belt = {(belt.position.x, belt.position.y): belt for belt in belts}
#     processed_belts = set()
#     belt_groups = []
#
#     def trace_belt_chain(start_belt: TransportBelt) -> List[TransportBelt]:
#         """
#         Trace both backwards and forwards from a belt to find all connected belts
#         """
#         chain = []
#         to_process = [start_belt]
#         seen_positions = set()
#
#         while to_process:
#             current_belt = to_process.pop(0)
#             current_pos = (current_belt.position.x, current_belt.position.y)
#
#             if current_pos in seen_positions:
#                 continue
#
#             chain.append(current_belt)
#             seen_positions.add(current_pos)
#
#             # Look for belts that output to current belt's input
#             input_pos = (current_belt.input_position.x, current_belt.input_position.y)
#             if input_pos in position_to_belt:
#                 feeding_belt = position_to_belt[input_pos]
#                 # Verify it actually connects
#                 if (feeding_belt.output_position.x == current_belt.position.x and
#                         feeding_belt.output_position.y == current_belt.position.y):
#                     to_process.append(feeding_belt)
#
#             # Look for belts that take input from current belt's output
#             output_pos = (current_belt.output_position.x, current_belt.output_position.y)
#             if output_pos in position_to_belt:
#                 receiving_belt = position_to_belt[output_pos]
#                 # Verify it actually connects
#                 if (receiving_belt.input_position.x == current_belt.output_position.x and
#                         receiving_belt.input_position.y == current_belt.output_position.y):
#                     to_process.append(receiving_belt)
#
#         return chain
#
#     def find_end_belts(belts_dict: dict) -> List[TransportBelt]:
#         """Find all belts that don't output to another belt"""
#         end_belts = []
#         for belt in belts_dict.values():
#             output_pos = (belt.output_position.x, belt.output_position.y)
#             # If output position isn't another belt's position, it's an end belt
#             if output_pos not in position_to_belt:
#                 end_belts.append(belt)
#         return end_belts
#
#     if prototype == Prototype.TransportBelt or prototype == Prototype.TransportBelt.name:
#         # Find all end belts
#         end_belts = find_end_belts(position_to_belt)
#
#         # Process each end belt that hasn't been handled yet
#         for end_belt in end_belts:
#             if (end_belt.position.x, end_belt.position.y) in processed_belts:
#                 continue
#
#             # Trace back through the chain of belts
#             belt_chain = trace_belt_chain(end_belt)
#
#             # Mark all these belts as processed
#             processed_belts.update((belt.position.x, belt.position.y) for belt in belt_chain)
#
#             # Calculate input/output positions for the group
#             input_pos = belt_chain[0].input_position
#             output_pos = belt_chain[-1].output_position
#
#             # Create inventory for the group
#             inventory = Inventory()
#             for belt in belt_chain:
#                 if hasattr(belt, 'inventory') and belt.inventory:
#                     for item, value in belt.inventory.items():
#                         current_value = inventory.get(item, 0)
#                         inventory[item] = current_value + value
#
#             # Determine status
#             if any(belt.warnings and belt.warnings[0] == 'full' for belt in belt_chain):
#                 status = EntityStatus.FULL_OUTPUT
#             elif not inventory:
#                 status = EntityStatus.EMPTY
#             else:
#                 status = EntityStatus.WORKING
#
#             # Create the belt group
#             group = BeltGroup(
#                 belts=belt_chain,
#                 inventory=inventory,
#                 input_positions=[input_pos],
#                 output_positions=[output_pos],
#                 status=status,
#                 position=belt_chain[0].position
#             )
#             belt_groups.append(group)
#
#     elif prototype == Prototype.Pipe:
#         # Handle pipe grouping using existing logic
#         return [] #_construct_pipe_groups(belts)
#
#     return belt_groups

def agglomerate_groupable_entities(belts: List[Entity]) -> List[BeltGroup]:
    """
    Group contiguous transport belts into BeltGroup objects.

    Args:
        belts: List of TransportBelt objects to group

    Returns:
        List of BeltGroup objects, each containing connected belts
    """

    prototype = Prototype.TransportBelt

    if not belts:
        return []

    if isinstance(belts[0], Entity):
        prototype = belts[0].prototype

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

    def find_connected_pipes(start_pipe: Entity) -> List[Entity]:
        """Find all pipes connected to the starting pipe using DFS"""
        connected = []
        to_process = [start_pipe]
        seen = set()

        while to_process:
            current_pipe = to_process.pop()
            if (current_pipe.position.x, current_pipe.position.y) in seen:
                continue

            seen.add((current_pipe.position.x, current_pipe.position.y))
            connected.append(current_pipe)

            # Check input position connection
            input_pos = current_pipe.position
            if (input_pos.x+1, input_pos.y) in position_to_belt:
                input_pipe = position_to_belt[(input_pos.x+1, input_pos.y)]
                to_process.append(input_pipe)
            elif (input_pos.x-1, input_pos.y) in position_to_belt:
                input_pipe = position_to_belt[(input_pos.x-1, input_pos.y)]
                to_process.append(input_pipe)
            elif (input_pos.x, input_pos.y+1) in position_to_belt:
                input_pipe = position_to_belt[(input_pos.x, input_pos.y+1)]
                to_process.append(input_pipe)
            elif (input_pos.x, input_pos.y-1) in position_to_belt:
                input_pipe = position_to_belt[(input_pos.x, input_pos.y-1)]
                to_process.append(input_pipe)

        return connected

    # Process each unprocessed belt
    for belt in belts:
        if (belt.position.x, belt.position.y) in processed_belts:
            continue

        # Find all belts connected to this one
        input_positions = []
        output_positions = []
        if prototype == Prototype.TransportBelt:
            connected_belts = find_connected_belts(belt)
            # Create a new belt group
            input_positions, output_positions = _calculate_belt_endpoints(connected_belts)
        elif prototype == Prototype.Pipe:
            connected_belts = find_connected_pipes(belt)
            # Create a new pipe group
            input_positions = _calculate_pipe_endpoints(connected_belts)

        # Mark all these belts as processed
        processed_belts.update((belt.position.x, belt.position.y) for belt in connected_belts)

        belt_groups.append(
            _construct_group(entities=connected_belts,
                             prototype=prototype,
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

                    if prototype == Prototype.TransportBelt:
                        # Check if any output position of group1 matches a belt position in group2
                        # This only works for transport belts, as they have an output position (being unidirectional)
                        for belt in group2.belts:
                            belt_pos = (belt.position.x, belt.position.y)
                            for out_pos in group1.output_positions:
                                if (out_pos.x, out_pos.y) == belt_pos:
                                    should_merge = True
                                    break

                    # Check if any input position of group2 matches a belt position in group1
                    if not should_merge:
                        if prototype == Prototype.TransportBelt:
                            for belt in group1.belts :
                                belt_pos = (belt.position.x, belt.position.y)
                                for in_pos in group2.input_positions:
                                    if (in_pos.x, in_pos.y) == belt_pos:
                                        should_merge = True
                                        break
                        elif prototype == Prototype.Pipe:
                            for pipe in group1.pipes:
                                pipe_pos = (pipe.position.x, pipe.position.y)
                                for in_pos in group2.input_positions:
                                    if (in_pos.x+1, in_pos.y) == pipe_pos:
                                        should_merge = True
                                        break
                                    elif (in_pos.x-1, in_pos.y) == pipe_pos:
                                        should_merge = True
                                        break
                                    elif (in_pos.x, in_pos.y+1) == pipe_pos:
                                        should_merge = True
                                        break
                                    elif (in_pos.x, in_pos.y-1) == pipe_pos:
                                        should_merge = True
                                        break

                    if should_merge:
                        # Merge the groups
                        input_positions = []
                        output_positions = []
                        if prototype == Prototype.TransportBelt:
                            merged_belts = group1.belts + group2.belts
                            #input_positions, output_positions = _calculate_belt_endpoints(merged_belts)
                            input_positions = [merged_belts[0].input_position]
                            output_positions = [merged_belts[-1].output_position]
                        elif prototype == Prototype.Pipe:
                            merged_belts = group1.pipes + group2.pipes
                            input_positions = _calculate_pipe_endpoints(merged_belts)

                        merged_group = _construct_group(entities=merged_belts,
                                                        prototype=prototype,
                                                        input_positions=input_positions,
                                                        output_positions=output_positions,
                                                        position=connected_belts[0].position)

                        # Replace group1 with merged group and remove group2
                        belt_groups[i] = merged_group
                        belt_groups.pop(j)
                        merged = True
                        break

    return belt_groups


def _calculate_belt_endpoints(belt_group):
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

def _calculate_pipe_endpoints(pipe_group):
    """
    Calculate the input positions of the pipe group, by looking for pipes that have at most
    one neighbor.
    """
    position_counts = defaultdict(int)
    neighbor_counts = defaultdict(int)
    input_positions = set()

    # Create a map of positions to pipes for quick lookup
    pos_to_pipe = {(pipe.position.x, pipe.position.y): pipe for pipe in pipe_group}

    # Count how many times each position appears
    for pipe in pipe_group:
        position_counts[(pipe.position.x, pipe.position.y)] += 1

    # Find how many orthogonal neighbors each pipe has
    for pipe in pipe_group:
        input_pos = (pipe.position.x, pipe.position.y)

        # Check all four directions
        for direction in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor_pos = (input_pos[0] + direction[0], input_pos[1] + direction[1])
            if neighbor_pos in pos_to_pipe:
                neighbor_counts[neighbor_pos] += 1

    # Find potential endpoints (positions have at most one neighbor)
    for pipe in pipe_group:
        input_pos = (pipe.position.x, pipe.position.y)

        if position_counts[input_pos] == 1 and neighbor_counts[input_pos] <= 1:
            input_positions.add(input_pos)

    # Convert back into Position objects
    input_positions = [Position(x=x, y=y) for x, y in input_positions]

    return input_positions