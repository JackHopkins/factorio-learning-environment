from statistics import mean
from typing import List

from factorio_entities import TransportBelt, BeltGroup, Position, Entity, EntityGroup, PipeGroup, Inventory, \
    EntityStatus, Pipe, ElectricityGroup
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


def _construct_group(id: int,
                     entities: List[Entity],
                     prototype: Prototype,
                     position: Position) -> EntityGroup:
    if prototype == Prototype.TransportBelt or isinstance(entities[0], TransportBelt):
        if len(entities) == 1:
            return entities[0]
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

        return BeltGroup(id=0,
                         belts=entities,
                         inventory=inventory,
                         inputs=inputs,
                         outputs=outputs,
                         status = status,
                         position=position)
    elif prototype == Prototype.Pipe or isinstance(entities[0], Pipe):
        entities = _deduplicate_entities(entities)
        if any([pipe.contents > 0 and pipe.flow_rate > 0 for pipe in entities]):
            status = EntityStatus.WORKING
        elif all([pipe.contents == 0 for pipe in entities]):
            status = EntityStatus.EMPTY
        elif all([pipe.flow_rate == 0 for pipe in entities]):
            status = EntityStatus.FULL_OUTPUT

        return PipeGroup(pipes=entities,
                         id=id,
                         status=status,
                         position=position)
    elif prototype in (Prototype.SmallElectricPole, Prototype.BigElectricPole, Prototype.MediumElectricPole):

        if any([pole.flow_rate > 0 for pole in entities]):
            status = EntityStatus.WORKING
        else:
            status = EntityStatus.NOT_PLUGGED_IN_ELECTRIC_NETWORK
        mean_x = mean([pole.position.x for pole in entities])
        mean_y = mean([pole.position.y for pole in entities])

        return ElectricityGroup(id=entities[0].electrical_id, poles=list(set(entities)), status=status, position=Position(x=mean_x, y=mean_y))


def construct_belt_groups(belts: List[TransportBelt], prototype):
    belts_by_position = {}
    source_belts = []
    terminal_belts = []
    visited = {}
    initial_groups = []

    for belt in belts:
        belts_by_position[(belt.position.x, belt.position.y)] = belt
        if belt.is_source:
            source_belts.append(belt)
        if belt.is_terminus:
            terminal_belts.append(belt)

    if len(terminal_belts) == 0 and len(source_belts) == 0:
        return [_construct_group(
            id=0,
            entities=belts,
            prototype=prototype,
            position=belts[0].position
        )]

    def walk_forward(belt, group):
        if (belt.position.x, belt.position.y) in visited:
            return group
        if not group:
            belt.is_source = True
            group.append(belt)
        visited[(belt.position.x, belt.position.y)] = True
        output = belt.output_position
        if (output.x, output.y) in belts_by_position:
            next_belt = belts_by_position[(output.x, output.y)]
            group.append(next_belt)
            walk_forward(next_belt, group)
        else:
            group[-1].is_terminus = True
        return group

    def walk_backward(belt, group):
        if (belt.position.x, belt.position.y) in visited:
            return group
        if not group:
            belt.is_terminus = True
            group.append(belt)
        visited[(belt.position.x, belt.position.y)] = True
        input = belt.input_position
        if (input.x, input.y) in belts_by_position:
            prev_belt = belts_by_position[(input.x, input.y)]
            group.insert(0, prev_belt)
            walk_backward(prev_belt, group)
        else:
            group[0].is_source = True
        return group

    for source in source_belts:
        group = walk_forward(source, [])
        if group:
            initial_groups.append(group)

    for terminal in terminal_belts:
        group = walk_backward(terminal, [])
        if group:
            initial_groups.append(group)

    final_groups = []
    while initial_groups:
        current = initial_groups.pop(0)
        restart = True

        while restart:
            restart = False
            i = 0
            while i < len(initial_groups):
                if any(belt in current for belt in initial_groups[i]):
                    current.extend([b for b in initial_groups[i] if b not in current])
                    initial_groups.pop(i)
                    restart = True
                else:
                    i += 1

        final_groups.append(current)

    return [_construct_group(
        id=i,
        entities=group,
        prototype=prototype,
        position=group[0].position
    ) for i, group in enumerate(final_groups)]



def agglomerate_groupable_entities(connected_entities: List[Entity]) -> List[EntityGroup]:
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

    if prototype in (Prototype.SmallElectricPole, Prototype.BigElectricPole, Prototype.MediumElectricPole):
        electricity_ids = {}
        for entity in connected_entities:
            if entity.electrical_id in electricity_ids:
                electricity_ids[entity.electrical_id].append(entity)
            else:
                electricity_ids[entity.electrical_id] = [entity]

        return [_construct_group(
            id=id,
            entities=entities,
            prototype=prototype,
            position=entities[0].position
        ) for id, entities in electricity_ids.items()]
    elif prototype == Prototype.Pipe:
        fluidbox_ids = {}
        for entity in connected_entities:
            if entity.fluidbox_id in fluidbox_ids:
                fluidbox_ids[entity.fluidbox_id].append(entity)
            else:
                fluidbox_ids[entity.fluidbox_id] = [entity]

        return [_construct_group(
            id=id,
            entities=entities,
            prototype=prototype,
            position=entities[0].position
        ) for id, entities in fluidbox_ids.items()]

    return construct_belt_groups(connected_entities, prototype)