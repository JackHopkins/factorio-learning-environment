from collections import defaultdict
from typing import List

from factorio_entities import TransportBelt, BeltGroup, Position, Entity, EntityGroup, PipeGroup, Inventory, \
    EntityStatus
from factorio_instance import Direction
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
                     position: Position) -> EntityGroup:
    if prototype == Prototype.TransportBelt or entities[0].prototype == Prototype.TransportBelt:
        inputs = [c for c in entities if c.is_source]
        outputs = [c for c in entities if c.is_terminus]
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
                         inputs=inputs,
                         outputs=outputs,
                         status = status,
                         position=position)
    elif prototype == Prototype.Pipe or entities[0].prototype == Prototype.Pipe:
        entities = _deduplicate_entities(entities)
        return PipeGroup(pipes=entities,
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

def should_merge_groups(group1, group2, prototype):
    """
    Determine if two groups should be merged based on their output positions and belt positions.
    Returns True if any output position from either group matches a belt position in the other group.
    """


    if prototype == Prototype.TransportBelt:
        # Get all belt positions from each group
        g1_positions = {(belt.position.x, belt.position.y) for belt in group1.belts}
        g2_positions = {(belt.position.x, belt.position.y) for belt in group2.belts}

        # Get all output positions from each group
        g1_outputs = {(out.output_position.x, out.output_position.y) for out in group1.outputs}
        g2_outputs = {(out.output_position.x, out.output_position.y) for out in group2.outputs}

        is_adjacent = False

        for belt1 in group1.belts:
            pos1 = (belt1.position.x, belt1.position.y)
            for belt2 in group2.belts:
                pos2 = (belt2.position.x, belt2.position.y)
                # Check if pipes are orthogonally adjacent
                if ((abs(pos1[0] - pos2[0]) == 1 and pos1[1] == pos2[1]) or
                        (abs(pos1[1] - pos2[1]) == 1 and pos1[0] == pos2[0])):
                    is_adjacent = True
        # Check if any output position from group1 matches any belt position in group2
        # or if any output position from group2 matches any belt position in group1
        return bool(g1_outputs & g2_positions or g2_outputs & g1_positions) or is_adjacent

    elif prototype == Prototype.Pipe:
        # For pipes, use existing orthogonal neighbor checking logic
        for pipe1 in group1.pipes:
            pos1 = (pipe1.position.x, pipe1.position.y)
            for pipe2 in group2.pipes:
                pos2 = (pipe2.position.x, pipe2.position.y)
                # Check if pipes are orthogonally adjacent
                if ((abs(pos1[0] - pos2[0]) == 1 and pos1[1] == pos2[1]) or
                        (abs(pos1[1] - pos2[1]) == 1 and pos1[0] == pos2[0])):
                    return True
        return False

    return False

def agglomerate_groupable_entities(connected_entities: List[Entity]) -> List[BeltGroup]:
    """
    Group contiguous transport belts into BeltGroup objects.

    Args:
        connected_entities: List of TransportBelt / Pipe objects to group

    Returns:
        List of BeltGroup objects, each containing connected belts
    """

    prototype = Prototype.TransportBelt

    if not connected_entities:
        return []

    if isinstance(connected_entities[0], Entity):
        prototype = connected_entities[0].prototype

    return [_construct_group(
        entities=connected_entities,
        prototype=prototype,
        position=connected_entities[0].position
    )]

    # # Create position-to-belt mapping for quick lookups
    # position_to_belt = {}
    # for belt in connected_entities:
    #     position_to_belt[(belt.position.x, belt.position.y)] = belt
    #
    # # Keep track of which belts we've processed
    # processed_belts = set()
    # belt_groups = []
    #
    # def find_connected_belts(start_belt: TransportBelt) -> List[TransportBelt]:
    #     """Find all belts connected to the starting belt using DFS"""
    #     connected = []
    #     to_process = [start_belt]
    #     seen = set()
    #
    #     while to_process:
    #         current_belt = to_process.pop()
    #         if (current_belt.position.x, current_belt.position.y) in seen:
    #             continue
    #
    #         seen.add((current_belt.position.x, current_belt.position.y))
    #         connected.append(current_belt)
    #
    #         # Check input position connection
    #         input_pos = current_belt.input_position
    #         if (input_pos.x, input_pos.y) in position_to_belt:
    #             input_belt = position_to_belt[(input_pos.x, input_pos.y)]
    #             if input_belt.output_position == current_belt.position:
    #                 to_process.append(input_belt)
    #
    #         # Check output position connection
    #         output_pos = current_belt.output_position
    #         if (output_pos.x, output_pos.y) in position_to_belt:
    #             output_belt = position_to_belt[(output_pos.x, output_pos.y)]
    #             if output_belt.input_position == current_belt.position:
    #                 to_process.append(output_belt)
    #
    #     return connected
    #
    # def get_entities_from_positions(positions: List[Position]):
    #     return [position_to_belt[(p.x, p.y)] for p in positions]
    #
    # def find_connected_pipes(start_pipe: Entity) -> List[Entity]:
    #     """Find all pipes connected to the starting pipe using DFS"""
    #     connected = []
    #     to_process = [start_pipe]
    #     seen = set()
    #
    #     while to_process:
    #         current_pipe = to_process.pop()
    #         if (current_pipe.position.x, current_pipe.position.y) in seen:
    #             continue
    #
    #         seen.add((current_pipe.position.x, current_pipe.position.y))
    #         connected.append(current_pipe)
    #
    #         # Check input position connection
    #         input_pos = current_pipe.position
    #         if (input_pos.x+1, input_pos.y) in position_to_belt:
    #             input_pipe = position_to_belt[(input_pos.x+1, input_pos.y)]
    #             to_process.append(input_pipe)
    #         elif (input_pos.x-1, input_pos.y) in position_to_belt:
    #             input_pipe = position_to_belt[(input_pos.x-1, input_pos.y)]
    #             to_process.append(input_pipe)
    #         elif (input_pos.x, input_pos.y+1) in position_to_belt:
    #             input_pipe = position_to_belt[(input_pos.x, input_pos.y+1)]
    #             to_process.append(input_pipe)
    #         elif (input_pos.x, input_pos.y-1) in position_to_belt:
    #             input_pipe = position_to_belt[(input_pos.x, input_pos.y-1)]
    #             to_process.append(input_pipe)
    #
    #     return connected
    #
    # # Process each unprocessed belt
    # for entity in connected_entities:
    #     if (entity.position.x, entity.position.y) in processed_belts:
    #         continue
    #
    #     # Find all belts connected to this one
    #     inputs = []
    #     outputs = []
    #     connected = []
    #     if prototype == Prototype.TransportBelt:
    #         connected = find_connected_belts(entity)
    #         # These represent the positions outside of each end of the belt
    #         # input_positions, output_positions = _calculate_belt_endpoints(connected)
    #         #
    #         # # We need to map them back into the original belt entities to find the correct input/outputss.
    #         # inputs = get_entities_from_positions(input_positions)
    #         # outputs = get_entities_from_positions(output_positions)
    #         inputs, outputs = _get_endpoint_objects(connected)
    #     elif prototype == Prototype.Pipe:
    #         connected = find_connected_pipes(entity)
    #         # Create a new pipe group
    #         # input_positions = _calculate_pipe_endpoints(connected)
    #         # inputs = get_entities_from_positions(input_positions)
    #         inputs = _get_pipe_endpoint_objects(connected)
    #
    #     # Mark all these belts as processed
    #     processed_belts.update((entity.position.x, entity.position.y) for entity in connected)
    #
    #     belt_groups.append(
    #         _construct_group(entities=connected,
    #                          prototype=prototype,
    #                          inputs=inputs,
    #                          outputs=outputs,
    #                          position=connected[0].position))
    #
    #     merged = True
    #     while merged:
    #         merged = False
    #         for i, group1 in enumerate(belt_groups):
    #             if merged:
    #                 break
    #             for j, group2 in enumerate(belt_groups[i + 1:], i + 1):
    #                 if should_merge_groups(group1, group2, prototype):
    #                     # Merge the groups
    #                     if prototype == Prototype.TransportBelt:
    #                         merged_entities = group1.belts + group2.belts
    #                     elif prototype == Prototype.Pipe:
    #                         merged_entities = group1.pipes + group2.pipes
    #
    #                     merged_group = _construct_group(
    #                         entities=merged_entities,
    #                         prototype=prototype,
    #                         inputs=inputs,
    #                         outputs=outputs,
    #                         position=merged_entities[0].position
    #                     )
    #
    #                     # Replace group1 with merged group and remove group2
    #                     belt_groups[i] = merged_group
    #                     belt_groups.pop(j)
    #                     merged = True
    #                     break
    #
    #     for group in belt_groups:
    #         if prototype == Prototype.TransportBelt:
    #             inputs, outputs = _get_endpoint_objects(group.belts)
    #             group.outputs = outputs
    #         elif prototype == Prototype.Pipe:
    #             inputs, outputs = _get_pipe_endpoint_objects(group.pipes)
    #         group.inputs = inputs
    #
    #
    # return belt_groups


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


def _get_endpoint_objects(belt_group):
    """
    Calculate the input and output belt objects that are the endpoints of the belt group.
    Handles both straight and curved belt connections.
    """
    # Create maps using position tuples as keys
    pos_to_belt = {(belt.position.x, belt.position.y): belt for belt in belt_group}

    def can_belts_connect(upstream_belt, downstream_belt):
        """Check if two belts can connect based on their positions and directions"""
        upstream_out = (upstream_belt.output_position.x, upstream_belt.output_position.y)
        downstream_pos = (downstream_belt.position.x, downstream_belt.position.y)
        downstream_in = (downstream_belt.input_position.x, downstream_belt.input_position.y)

        # Direct connection - output matches input
        if upstream_out == downstream_in:
            return True

        # Corner case - check if belts form a valid curve
        # If downstream belt is at the output position of upstream belt
        if upstream_out == downstream_pos:
            # Valid curves: RIGHT->DOWN, DOWN->LEFT, LEFT->UP, UP->RIGHT
            valid_curves = {
                (Direction.RIGHT, Direction.DOWN),
                (Direction.DOWN, Direction.LEFT),
                (Direction.LEFT, Direction.UP),
                (Direction.UP, Direction.RIGHT)
            }
            return (upstream_belt.direction, downstream_belt.direction) in valid_curves

        # If upstream belt is at the input position of downstream belt
        if (upstream_belt.position.x, upstream_belt.position.y) == downstream_in:
            valid_curves = {
                (Direction.RIGHT, Direction.DOWN),
                (Direction.DOWN, Direction.LEFT),
                (Direction.LEFT, Direction.UP),
                (Direction.UP, Direction.RIGHT)
            }
            return (upstream_belt.direction, downstream_belt.direction) in valid_curves

        return False

    # Use positions as dictionary keys to track connections
    input_sources = {}  # position -> position of belt that outputs to it
    for downstream_belt in belt_group:
        downstream_pos = (downstream_belt.position.x, downstream_belt.position.y)
        for upstream_belt in belt_group:
            upstream_pos = (upstream_belt.position.x, upstream_belt.position.y)
            if upstream_pos != downstream_pos and can_belts_connect(upstream_belt, downstream_belt):
                input_sources[downstream_pos] = upstream_pos
                break

    input_belts = []
    output_belts = []

    # Find input belts - belts that have no input source
    for belt in belt_group:
        belt_pos = (belt.position.x, belt.position.y)
        if belt_pos not in input_sources:
            input_belts.append(belt)

    # Find output belts - belts that don't output to any other belt
    for upstream_belt in belt_group:
        is_output = True
        for downstream_belt in belt_group:
            if downstream_belt != upstream_belt and can_belts_connect(upstream_belt, downstream_belt):
                is_output = False
                break
        if is_output:
            output_belts.append(upstream_belt)

    return input_belts, output_belts

def _get_endpoint_objects3(belt_group):
    """
    Calculate the input and output belt objects that are the endpoints of the belt group.
    A belt is an input if nothing outputs to its input position.
    A belt is an output if its output position isn't connected to any other belt's input.
    """
    # Create dictionaries for position lookups
    pos_to_belt = {(belt.position.x, belt.position.y): belt for belt in belt_group}
    belt_outputs = {(belt.output_position.x, belt.output_position.y): belt for belt in belt_group}

    # For each belt, find what belt (if any) outputs to its input position
    input_sources = {}  # belt -> belt that outputs to its input
    for belt in belt_group:
        input_pos = (belt.position.x, belt.position.y)
        if input_pos in belt_outputs:
            input_sources[(belt.position.x, belt.position.y)] = belt_outputs[input_pos]

    input_belts = []
    output_belts = []

    # Find input belts - belts that have no input source
    for belt in belt_group:
        if (belt.position.x, belt.position.y) not in input_sources:
            input_belts.append(belt)

    # Find output belts - belts whose output isn't used as input
    for belt in belt_group:
        output_pos = (belt.output_position.x, belt.output_position.y)
        is_output = True

        # Check if this belt's output connects to another belt's input
        for other_belt in belt_group:
            if (other_belt.position.x, other_belt.position.y) == output_pos:
                is_output = False
                break

        if is_output:
            output_belts.append(belt)

    return input_belts, output_belts

def _get_endpoint_objects2(belt_group):
    """
    Calculate the input and output belt objects that are the endpoints of the belt group.
    """
    positions = {(belt.position.x, belt.position.y) for belt in belt_group}
    outputs = {(belt.output_position.x, belt.output_position.y) for belt in belt_group}
    inputs = {(belt.input_position.x, belt.input_position.y) for belt in belt_group}

    input_belts = []
    output_belts = []

    for belt in belt_group:
        # A belt is an input if its input position isn't any belt's output position
        # AND no belt outputs to its position
        belt_input = (belt.input_position.x, belt.input_position.y)
        belt_pos = (belt.position.x, belt.position.y)
        if belt_input not in outputs and belt_pos not in outputs:
            input_belts.append(belt)

        # A belt is an output if its output position isn't any belt's input position
        # AND no belt's position matches its output position
        belt_output = (belt.output_position.x, belt.output_position.y)
        if belt_output not in inputs and belt_output not in positions:
            output_belts.append(belt)

    return input_belts, output_belts

def _get_pipe_endpoint_objects(pipe_group):
    """
    Calculate the endpoint pipe objects that are members of the pipe group.
    Returns a list of pipes that are endpoints (have only one neighbor within the group).
    """
    neighbor_counts = defaultdict(int)
    endpoint_pipes = []

    # Create a map of positions to pipes for quick lookup
    pos_to_pipe = {(pipe.position.x, pipe.position.y): pipe for pipe in pipe_group}

    # Find how many orthogonal neighbors each pipe has within the group
    for pipe in pipe_group:
        pipe_pos = (pipe.position.x, pipe.position.y)

        # Check all four directions
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor_pos = (pipe_pos[0] + dx, pipe_pos[1] + dy)
            if neighbor_pos in pos_to_pipe:
                neighbor_counts[pipe_pos] += 1

    # Find endpoint pipes (those with at most one neighbor)
    for pipe in pipe_group:
        pipe_pos = (pipe.position.x, pipe.position.y)
        if neighbor_counts[pipe_pos] <= 1:
            endpoint_pipes.append(pipe)

    return endpoint_pipes