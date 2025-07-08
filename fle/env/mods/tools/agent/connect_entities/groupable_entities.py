from statistics import mean
from typing import List, Union
from typing_extensions import cast

from fle.env import (
    TransportBelt,
    BeltGroup,
    Position,
    Entity,
    EntityGroup,
    PipeGroup,
    Inventory,
    EntityStatus,
    Pipe,
    ElectricityGroup,
    UndergroundBelt,
    Direction,
    WallGroup,
)
from fle.env.game_types import Prototype


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


def _construct_group(
    id: int, entities: List[Entity], prototype: Prototype, position: Position
) -> EntityGroup:
    if prototype == Prototype.TransportBelt or isinstance(entities[0], TransportBelt):
        if len(entities) == 1:
            return entities[0]
        inputs = [c for c in entities if c.is_source]
        outputs = [c for c in entities if c.is_terminus]
        inventory = Inventory()
        for entity in entities:
            if (
                hasattr(entity, "inventory") and entity.inventory
            ):  # Check if inventory exists and is not empty
                entity_inventory = entity.inventory
                for item, value in entity_inventory.items():
                    current_value = inventory.get(
                        item, 0
                    )  # Get current value or 0 if not exists
                    inventory[item] = current_value + value  # Add new value

        if any(entity.warnings and entity.warnings[0] == "full" for entity in entities):
            status = EntityStatus.FULL_OUTPUT
        else:
            status = EntityStatus.WORKING

        if not inventory:
            status = EntityStatus.EMPTY

        return BeltGroup(
            id=0,
            belts=entities,
            inventory=inventory,
            inputs=inputs,
            outputs=outputs,
            status=status,
            position=position,
        )
    elif prototype in (Prototype.Pipe, Prototype.UndergroundPipe) or isinstance(
        entities[0], Pipe
    ):
        entities = _deduplicate_entities(entities)
        if any([pipe.contents > 0 and pipe.flow_rate > 0 for pipe in entities]):
            status = EntityStatus.WORKING
        elif all([pipe.contents == 0 for pipe in entities]):
            status = EntityStatus.EMPTY
        elif all([pipe.flow_rate == 0 for pipe in entities]):
            status = EntityStatus.FULL_OUTPUT

        return PipeGroup(pipes=entities, id=id, status=status, position=position)
    elif prototype in (
        Prototype.SmallElectricPole,
        Prototype.BigElectricPole,
        Prototype.MediumElectricPole,
    ):
        if any([pole.flow_rate > 0 for pole in entities]):
            status = EntityStatus.WORKING
        else:
            status = EntityStatus.NOT_PLUGGED_IN_ELECTRIC_NETWORK
        mean_x = mean([pole.position.x for pole in entities])
        mean_y = mean([pole.position.y for pole in entities])

        return ElectricityGroup(
            id=entities[0].electrical_id,
            poles=list(set(entities)),
            status=status,
            position=Position(x=mean_x, y=mean_y),
        )
    else:
        return WallGroup(
            id=sum([hash(entity.position) for entity in entities]) % 1024,
            entities=entities,
            position=entities[0].position,
        )


def consolidate_underground_belts(belt_groups):
    """
    Process belt groups to consolidate underground belt pairs into single instances.
    """

    def process_group(group):
        # Map to track underground belt pairs by their id
        underground_pairs = {}
        new_belts = []
        removed_indices = set()

        # First pass: identify underground belt pairs
        for i, belt in enumerate(group.belts):
            if isinstance(belt, UndergroundBelt):
                if belt.id not in underground_pairs:
                    underground_pairs[belt.id] = {
                        "entrance": None,
                        "exit": None,
                        "index": i,
                    }

        for i, belt in enumerate(group.belts):
            if isinstance(belt, UndergroundBelt):
                if belt.connected_to:
                    underground_pairs[belt.connected_to]["exit"] = belt
                    underground_pairs[belt.id]["entrance"] = belt

        # Third pass: create consolidated underground belts and build new belt list
        for i, belt in enumerate(group.belts):
            if i in removed_indices:
                continue

            if isinstance(belt, UndergroundBelt):
                pair_data = underground_pairs.get(belt.id, None)
                if pair_data and pair_data["entrance"] and pair_data["exit"]:
                    # if i == pair_data['index']:  # Only process at first occurrence
                    # Create consolidated underground belt
                    entrance = cast(UndergroundBelt, pair_data["entrance"])
                    exit = cast(UndergroundBelt, pair_data["exit"])

                    # Create new underground belt representing the whole section
                    try:
                        consolidated = UndergroundBelt(
                            name=entrance.name,
                            id=entrance.id,
                            position=entrance.position,
                            direction=entrance.direction,
                            is_input=True,  # Marking as input since it represents the entrance
                            is_source=entrance.is_source,
                            is_terminus=exit.is_terminus,
                            input_position=entrance.input_position,
                            output_position=exit.position,
                            connected_to=exit.id,
                            energy=entrance.energy + exit.energy,
                            dimensions=entrance.dimensions,
                            tile_dimensions=entrance.tile_dimensions,
                            status=entrance.status,
                            prototype=entrance.prototype,
                            health=min(entrance.health, exit.health),
                            inventory=Inventory(
                                **{
                                    **entrance.inventory.__dict__,
                                    **exit.inventory.__dict__,
                                }
                            ),
                        )
                        new_belts.append(consolidated)
                    except Exception:
                        pass

                    # Mark both entrance and exit for removal
                    exit_idx = group.belts.index(exit)
                    removed_indices.add(i)
                    removed_indices.add(exit_idx)
                # continue

            if i not in removed_indices:
                new_belts.append(belt)

        # Update group's belt list
        group.belts = new_belts

        # Update inputs and outputs
        group.inputs = [belt for belt in group.inputs if belt not in group.belts]
        group.outputs = [belt for belt in group.outputs if belt not in group.belts]

        position_dict = {}
        for belt in group.belts:
            position_dict[belt.position] = belt

        for belt in new_belts:
            if belt.is_source and (
                belt.input_position not in position_dict
                or position_dict[belt.input_position].output_position != belt.position
            ):
                group.inputs.append(belt)
            if belt.is_terminus and (
                belt.output_position not in position_dict
                or position_dict[belt.output_position].input_position != belt.position
            ):
                group.outputs.append(belt)

        return group

    # Process each belt group
    return [
        process_group(group) for group in belt_groups if isinstance(group, BeltGroup)
    ] + [group for group in belt_groups if not isinstance(group, BeltGroup)]


def construct_belt_groups(
    belts: List[Union[TransportBelt, UndergroundBelt]], prototype
):
    belts_by_position = {}
    source_belts = []
    terminal_belts = []
    visited = set()
    initial_groups = []

    # Maps to store underground connections
    underground_entrances = []  # List of (position, direction) for entrances
    underground_exits = []  # List of (position, direction) for exits

    # First pass: organize belts and identify underground entrances/exits
    for belt in belts:
        pos = (belt.position.x, belt.position.y)
        belts_by_position[pos] = belt

        if isinstance(belt, UndergroundBelt):
            if belt.is_input:
                underground_entrances.append((pos, belt.direction))
            else:
                underground_exits.append((pos, belt.direction))

        if belt.is_source:
            source_belts.append(belt)
        if belt.is_terminus:
            terminal_belts.append(belt)

    def find_matching_exit(entrance_pos, direction):
        entrance_x, entrance_y = entrance_pos
        closest_exit = None
        min_distance = float("inf")

        for exit_pos, exit_dir in underground_exits:
            exit_x, exit_y = exit_pos
            if exit_dir != direction:
                continue

            dx = exit_x - entrance_x
            dy = exit_y - entrance_y
            max_range = 4  # Default underground belt range

            # Check if they're in line and in the correct direction
            match direction.value:
                case Direction.EAST.value:  # Looking right
                    if dy == 0 and 0 < dx <= max_range:
                        distance = dx
                        if distance < min_distance:
                            min_distance = distance
                            closest_exit = exit_pos
                case Direction.WEST.value:  # Looking left
                    if dy == 0 and -max_range <= dx < 0:
                        distance = abs(dx)
                        if distance < min_distance:
                            min_distance = distance
                            closest_exit = exit_pos
                case Direction.SOUTH.value:  # Looking down
                    if dx == 0 and 0 < dy <= max_range:
                        distance = dy
                        if distance < min_distance:
                            min_distance = distance
                            closest_exit = exit_pos
                case Direction.NORTH.value:  # Looking up
                    if dx == 0 and -max_range <= dy < 0:
                        distance = abs(dy)
                        if distance < min_distance:
                            min_distance = distance
                            closest_exit = exit_pos

        return closest_exit

    def get_next_belt_position(belt):
        pos = (belt.position.x, belt.position.y)

        # If this is an underground entrance, find its matching exit
        if isinstance(belt, UndergroundBelt) and belt.is_input:
            exit_pos = find_matching_exit(pos, belt.direction)
            if exit_pos:
                return exit_pos

        # Otherwise use normal output position
        output = belt.output_position
        return (output.x, output.y)

    def get_prev_belt_position(belt):
        pos = (belt.position.x, belt.position.y)

        # If this is an underground exit, find its matching entrance
        if isinstance(belt, UndergroundBelt) and not belt.is_input:
            for entrance_pos, direction in underground_entrances:
                if find_matching_exit(entrance_pos, direction) == pos:
                    return entrance_pos

        # Otherwise use normal input position
        input = belt.input_position
        return (input.x, input.y)

    def walk_forward(belt, group):
        pos = (belt.position.x, belt.position.y)
        if pos in visited:
            return group

        if not group:
            belt.is_source = True
            group.append(belt)
        elif belt not in group:
            group.append(belt)

        visited.add(pos)
        next_pos = get_next_belt_position(belt)

        if next_pos in belts_by_position:
            next_belt = belts_by_position[next_pos]
            walk_forward(next_belt, group)
        else:
            if group and group[-1] not in terminal_belts:
                group[-1].is_terminus = True
        return group

    def walk_backward(belt, group):
        pos = (belt.position.x, belt.position.y)
        if pos in visited:
            return group

        if not group:
            belt.is_terminus = True
            group.append(belt)
        elif belt not in group:
            group.insert(0, belt)

        visited.add(pos)
        prev_pos = get_prev_belt_position(belt)

        if prev_pos in belts_by_position:
            prev_belt = belts_by_position[prev_pos]
            walk_backward(prev_belt, group)
        else:
            if group and group[0] not in source_belts:
                group[0].is_source = True
        return group

    # Build initial groups starting from sources
    for source in source_belts:
        if (source.position.x, source.position.y) not in visited:
            group = walk_forward(source, [])
            if group:
                initial_groups.append(group)

    # Then try terminals if we missed any
    for terminal in terminal_belts:
        if (terminal.position.x, terminal.position.y) not in visited:
            group = walk_backward(terminal, [])
            if group:
                initial_groups.append(group)

    # If still no groups, try starting from any underground entrance
    if not initial_groups:
        for entrance_pos, _ in underground_entrances:
            if entrance_pos not in visited:
                belt = belts_by_position[entrance_pos]
                group = walk_forward(belt, [])
                if group:
                    initial_groups.append(group)

    # Finally, if still no groups, start from any belt
    if not initial_groups and belts:
        start_belt = belts[0]
        group = walk_forward(start_belt, [])
        if group:
            initial_groups.append(group)

    # Merge overlapping groups
    final_groups = []

    for group in initial_groups:
        merged = False
        for final_group in final_groups:
            # Check if this group should be merged with an existing group
            if any(
                (belt.output_position.x, belt.output_position.y)
                in {(b.position.x, b.position.y) for b in final_group}
                for belt in group
            ):
                # Merge groups
                for belt in group:
                    if belt not in final_group:
                        final_group.append(belt)
                merged = True
                break

        if not merged:
            final_groups.append(group)

    groups = [
        _construct_group(
            id=i,
            entities=list(
                dict.fromkeys(group)
            ),  # Remove any duplicates while preserving order
            prototype=prototype,
            position=group[0].position,
        )
        for i, group in enumerate(final_groups)
    ]

    try:
        return consolidate_underground_belts(
            groups
        )  # We want to merge conjoined pairs of underground belts for clarity
    except Exception as e:
        raise e


#
# @deprecated("Doesn't support underground belts")
# def construct_belt_groups_old(belts: List[TransportBelt], prototype):
#     belts_by_position = {}
#     source_belts = []
#     terminal_belts = []
#     visited = {}
#     initial_groups = []
#
#     for belt in belts:
#         belts_by_position[(belt.position.x, belt.position.y)] = belt
#         if belt.is_source:
#             source_belts.append(belt)
#         if belt.is_terminus:
#             terminal_belts.append(belt)
#
#     if len(terminal_belts) == 0 and len(source_belts) == 0:
#         return [_construct_group(
#             id=0,
#             entities=belts,
#             prototype=prototype,
#             position=belts[0].position
#         )]
#
#     def walk_forward(belt, group):
#         if (belt.position.x, belt.position.y) in visited:
#             return group
#         if not group:
#             belt.is_source = True
#             group.append(belt)
#         visited[(belt.position.x, belt.position.y)] = True
#         output = belt.output_position
#         if (output.x, output.y) in belts_by_position:
#             next_belt = belts_by_position[(output.x, output.y)]
#             group.append(next_belt)
#             walk_forward(next_belt, group)
#         else:
#             group[-1].is_terminus = True
#         return group
#
#     def walk_backward(belt, group):
#         if (belt.position.x, belt.position.y) in visited:
#             return group
#         if not group:
#             belt.is_terminus = True
#             group.append(belt)
#         visited[(belt.position.x, belt.position.y)] = True
#         input = belt.input_position
#         if (input.x, input.y) in belts_by_position:
#             prev_belt = belts_by_position[(input.x, input.y)]
#             group.insert(0, prev_belt)
#             walk_backward(prev_belt, group)
#         else:
#             group[0].is_source = True
#         return group
#
#     for source in source_belts:
#         group = walk_forward(source, [])
#         if group:
#             initial_groups.append(group)
#
#     for terminal in terminal_belts:
#         group = walk_backward(terminal, [])
#         if group:
#             initial_groups.append(group)
#
#     final_groups = []
#     while initial_groups:
#         current = initial_groups.pop(0)
#         restart = True
#
#         while restart:
#             restart = False
#             i = 0
#             while i < len(initial_groups):
#                 if any(belt in current for belt in initial_groups[i]):
#                     current.extend([b for b in initial_groups[i] if b not in current])
#                     initial_groups.pop(i)
#                     restart = True
#                 else:
#                     i += 1
#
#         final_groups.append(current)
#
#     return [_construct_group(
#         id=i,
#         entities=group,
#         prototype=prototype,
#         position=group[0].position
#     ) for i, group in enumerate(final_groups)]


def agglomerate_groupable_entities(
    connected_entities: List[Entity],
) -> List[EntityGroup]:
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

    if hasattr(connected_entities[0], "prototype"):
        prototype = connected_entities[0].prototype

    if prototype in (
        Prototype.SmallElectricPole,
        Prototype.BigElectricPole,
        Prototype.MediumElectricPole,
    ):
        electricity_ids = {}
        for entity in connected_entities:
            if entity.electrical_id in electricity_ids:
                electricity_ids[entity.electrical_id].append(entity)
            else:
                electricity_ids[entity.electrical_id] = [entity]

        return [
            _construct_group(
                id=id,
                entities=entities,
                prototype=prototype,
                position=entities[0].position,
            )
            for id, entities in electricity_ids.items()
        ]
    elif prototype in (Prototype.Pipe, Prototype.UndergroundPipe):
        fluidbox_ids = {}
        for entity in connected_entities:
            if entity.fluidbox_id in fluidbox_ids:
                fluidbox_ids[entity.fluidbox_id].append(entity)
            else:
                fluidbox_ids[entity.fluidbox_id] = [entity]

        return [
            _construct_group(
                id=id,
                entities=entities,
                prototype=prototype,
                position=entities[0].position,
            )
            for id, entities in fluidbox_ids.items()
        ]
    elif prototype == Prototype.StoneWall:
        return [
            _construct_group(
                id=0,
                entities=connected_entities,
                prototype=prototype,
                position=connected_entities[0].position,
            )
        ]
    elif prototype in (
        Prototype.TransportBelt,
        Prototype.FastTransportBelt,
        Prototype.ExpressTransportBelt,
        Prototype.UndergroundBelt,
        Prototype.FastUndergroundBelt,
        Prototype.ExpressUndergroundBelt,
    ):
        groups = construct_belt_groups(connected_entities, prototype)
        return groups

    raise RuntimeError(
        "Failed to group an entity with prototype: {}".format(prototype.name)
    )
