from time import sleep
from typing import Union, Optional, List, Dict, cast, Set

import numpy

from entities import EntityGroup, Entity, Position, BeltGroup, PipeGroup, ElectricityGroup, TransportBelt, \
    Pipe, FluidHandler, MiningDrill, Inserter
from instance import PLAYER, Direction
from game_types import Prototype, prototype_by_name
from tools.admin.clear_collision_boxes.client import ClearCollisionBoxes
from tools.admin.extend_collision_boxes.client import ExtendCollisionBoxes
from tools.admin.get_path.client import GetPath
from tools.admin.request_path.client import RequestPath
from tools.agent.connect_entities.path_result import PathResult
from tools.agent.connect_entities.resolver import ConnectionType, Resolver
from tools.agent.connect_entities.resolvers.fluid_connection_resolver import FluidConnectionResolver
from tools.agent.connect_entities.resolvers.power_connection_resolver import PowerConnectionResolver
from tools.agent.connect_entities.resolvers.transport_connection_resolver import TransportConnectionResolver
from tools.agent.connect_entities.groupable_entities import _deduplicate_entities, agglomerate_groupable_entities
from tools.agent.get_entities.client import GetEntities
from tools.agent.get_entity.client import GetEntity
from tools.agent.inspect_inventory.client import InspectInventory
from tools.agent.pickup_entity.client import PickupEntity
from tools.agent.rotate_entity.client import RotateEntity
from tools.tool import Tool
from collections.abc import Set as AbstractSet


class ConnectEntities(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

        self._setup_actions()
        self._setup_resolvers()

    def _setup_actions(self):
        self.request_path = RequestPath(self.connection, self.game_state)
        self.get_path = GetPath(self.connection, self.game_state)
        self.rotate_entity = RotateEntity(self.connection, self.game_state)
        self.pickup_entity = PickupEntity(self.connection, self.game_state)
        self.inspect_inventory = InspectInventory(self.connection, self.game_state)
        self.get_entities = GetEntities(self.connection, self.game_state)
        self.get_entity = GetEntity(self.connection, self.game_state)
        self._extend_collision_boxes = ExtendCollisionBoxes(self.connection, self.game_state)
        self._clear_collision_boxes = ClearCollisionBoxes(self.connection, self.game_state)

    def _setup_resolvers(self):
        self.resolvers = {
            ConnectionType.FLUID: FluidConnectionResolver(self.get_entities),
            ConnectionType.TRANSPORT: TransportConnectionResolver(),
            ConnectionType.POWER: PowerConnectionResolver(),
            ConnectionType.WALL: Resolver(self.get_entities)
        }

    def _get_connection_type(self, prototype: Prototype) -> ConnectionType:
        match prototype:
            case Prototype.Pipe | Prototype.UndergroundPipe:
                return ConnectionType.FLUID
            case Prototype.TransportBelt | Prototype.ExpressUndergroundBelt | Prototype.FastTransportBelt | Prototype.UndergroundBelt | Prototype.ExpressTransportBelt | Prototype.FastUndergroundBelt:
                return ConnectionType.TRANSPORT
            case Prototype.SmallElectricPole | Prototype.MediumElectricPole | Prototype.BigElectricPole:
                return ConnectionType.POWER
            case Prototype.StoneWall:
                return ConnectionType.WALL
            case _:
                raise ValueError(f"Unsupported connection type: {prototype}")

    def is_set_of_prototype(self, arg) -> bool:
        return (
                isinstance(arg, AbstractSet) and
                all(isinstance(item, Prototype) for item in arg)
        )


    def __call__(self, *args, **kwargs):
        connection_types = set()
        waypoints = []
        if 'connection_type' in kwargs:
            waypoints = args
            connection_types = kwargs['connection_type']
            if isinstance(connection_types, Prototype):
                connection_types = {connection_types}
            elif self.is_set_of_prototype(connection_types):
                connection_types = connection_types


        if 'target' in kwargs and 'source' in kwargs:
            waypoints = []
            waypoints.append(kwargs['source'])
            waypoints.append(kwargs['target'])

        if not waypoints:
            for arg in args:
                if isinstance(arg, Prototype):
                    connection_types = { arg }
                elif self.is_set_of_prototype(arg):
                    connection_types = arg
                else:
                    waypoints.append(arg)


        assert len(waypoints) > 1, "Need more than one waypoint"
        connection = waypoints[0]
        for _, target in zip(waypoints[:-1], waypoints[1:]):
            connection = self._connect_pair_of_waypoints(connection, target, connection_types=connection_types)
            #sleep(0.01) # Sleep for 250ms to ensure that the game updates
        return connection

    def _validate_connection_types(self, connection_types: Set[Prototype]):
        """
        Ensure that all connection_types handle the same contents - either FLUID, TRANSPORT or POWER
        """
        types = [self._get_connection_type(connection_type) for connection_type in connection_types]
        return len(set(types)) == 1

    def _connect_pair_of_waypoints(self,
                                   source: Union[Position, Entity, EntityGroup],
                                   target: Union[Position, Entity, EntityGroup],
                                   connection_types: Set[Prototype] = {}) -> Union[Entity, EntityGroup]:
        """Connect two entities or positions."""

        # Resolve connection type if not provided
        if not connection_types:
            connection_type = self._infer_connection_type(source, target)
        else:
            valid = self._validate_connection_types(connection_types)
            if not valid:
                raise Exception(f"All connection types must handle the sort of contents: either fluid, power or items. "
                                f"Your types are incompatible {set(['Prototype.'+type.name for type in connection_types])}")

        # Resolve positions into entities if they exist
        if isinstance(source, Position):
            source = self._resolve_position_into_entity(source)

        if isinstance(target, Position):
            target = self._resolve_position_into_entity(target)

        # Get resolver for this connection type
        resolver = self.resolvers[self._get_connection_type(list(connection_types)[0])]

        # Resolve source and target positions
        prioritised_list_of_position_pairs = resolver.resolve(source, target)

        last_exception = None
        for source_pos, target_pos in prioritised_list_of_position_pairs:
            # Handle the actual connection
            try:
                connection = self._create_connection(
                    source_pos, target_pos,
                    connection_types, False,
                    source_entity=source if isinstance(source, (Entity, EntityGroup)) else None,
                    target_entity=target if isinstance(target, (Entity, EntityGroup)) else None
                )
                return connection[0]
            except Exception as e:
                last_exception = e
                trace_back = e.__traceback__
                pass

        source_pos = source.position if not isinstance(source, Position) else source
        target_pos = target.position if not isinstance(target, Position) else target


        source_error_message_addition = f"{source}" if isinstance(source, Position) else f"{source.name} at {source.position}"
        target_error_message_addition = f"{target}" if isinstance(target, Position) else f"{target.name} at {target.position}"
        raise Exception(
            f"Failed to connect {set([type.name for type in connection_types])} from {source_error_message_addition} to {target_error_message_addition}. "
            f"{self.get_error_message(str(last_exception))}"
        )


    def _resolve_position_into_entity(self, position: Position):
        entities = self.get_entities(position=position, radius=0.5)
        if not entities:
            return position
        if isinstance(entities[0], EntityGroup):
            if isinstance(entities[0], PipeGroup):
                for pipe in entities[0].pipes:
                    if pipe.position.is_close(position, tolerance=0.707):
                        return pipe
            elif isinstance(entities[0], ElectricityGroup):
                for pole in entities[0].poles:
                    if pole.position.is_close(position, tolerance=0.707):
                        return pole
            elif isinstance(entities[0], BeltGroup):
                for belt in entities[0].belts:
                    if belt.position.is_close(position, tolerance=0.707):
                        return belt
        return entities[0]

    def _infer_connection_type(self,
                               source: Union[Position, Entity, EntityGroup],
                               target: Union[Position, Entity, EntityGroup]) -> Prototype:
        """
        Infers the appropriate connection type based on source and target entities.

        Args:
            source: Source entity, position or group
            target: Target entity, position or group

        Returns:
            The appropriate Prototype for the connection

        Raises:
            ValueError: If connection type cannot be determined or entities are incompatible
        """
        # If both are positions, we can't infer the type
        if isinstance(source, Position) and isinstance(target, Position):
            raise ValueError("Cannot infer connection type when both source and target are positions. "
                             "Please specify connection_type explicitly.")

        # Handle fluid connections
        if isinstance(source, FluidHandler) and isinstance(target, FluidHandler):
            return Prototype.Pipe

        # Handle belt connections
        is_source_belt = isinstance(source, (TransportBelt, BeltGroup))
        is_target_belt = isinstance(target, (TransportBelt, BeltGroup))
        if is_source_belt or is_target_belt:
            return Prototype.TransportBelt

        # Handle mining and insertion
        is_source_miner = isinstance(source, MiningDrill)
        is_target_inserter = isinstance(target, Inserter)
        is_source_inserter = isinstance(source, Inserter)
        if (is_source_miner and is_target_inserter) or (is_source_inserter and is_target_belt):
            return Prototype.TransportBelt

        # If we can't determine the type, we need explicit specification
        raise ValueError("Could not infer connection type. Please specify connection_type explicitly.")

    def _attempt_path_finding(self,
                              source_pos: Position,
                              target_pos: Position,
                              connection_prototypes: List[str],
                              num_available: int,
                              pathing_radius: float = 1,
                              dry_run: bool = False,
                              allow_paths_through_own: bool = False) -> PathResult:
        """Attempt to find a path between two positions"""
        entity_sizes = [1.5, 1, 0.5, 0.25]  # Ordered from largest to smallest

        for size in entity_sizes:
            path_handle = self.request_path(
                finish=target_pos,
                start=source_pos,
                allow_paths_through_own_entities=allow_paths_through_own,
                radius=pathing_radius,
                entity_size=size
            )

            sleep(0.05)  # Allow pathing system time to compute

            response, _ = self.execute(
                PLAYER,
                source_pos.x,
                source_pos.y,
                target_pos.x,
                target_pos.y,
                path_handle,
                ",".join(connection_prototypes),
                dry_run,
                num_available
            )

            result = PathResult(response)
            if result.is_success:
                return result

        return result  # Return last failed result if all attempts fail

    def _create_connection(self,
                           source_pos: Position,
                           target_pos: Position,
                           connection_types: Set[Prototype],
                           dry_run: bool,
                           source_entity: Optional[Entity] = None,
                           target_entity: Optional[Entity] = None) -> List[Union[Entity, EntityGroup]]:
        """Create a connection between two positions"""

        connection_type_names = {}
        names_to_type = {}
        metaclasses = {}

        for connection_type in connection_types:
            connection_prototype, metaclass = connection_type.value
            metaclasses[connection_prototype] = metaclass
            connection_type_names[connection_type] = connection_prototype
            names_to_type[connection_prototype] = connection_type

        inventory = self.inspect_inventory()
        num_available = inventory.get(connection_prototype, 0)

        connection_type_names_values = list(connection_type_names.values())
        # Determine connection strategy based on type
        match connection_types:
            case _ if connection_types & {Prototype.Pipe, Prototype.UndergroundPipe}:
                pathing_radius = 0.5
                self._extend_collision_boxes(source_pos, target_pos)
                try:
                    result = self._attempt_path_finding(
                        source_pos, target_pos,
                        connection_type_names_values, num_available,
                        pathing_radius, dry_run
                    )
                finally:
                    self._clear_collision_boxes()

            case _ if (connection_types & {Prototype.TransportBelt, Prototype.UndergroundBelt}) \
                      or (connection_types & {Prototype.FastTransportBelt, Prototype.FastUndergroundBelt}) \
                      or (connection_types & {Prototype.ExpressTransportBelt, Prototype.ExpressUndergroundBelt}):
                pathing_radius = 0.5
                result = self._attempt_path_finding(
                    source_pos, target_pos,
                    connection_type_names_values, num_available,
                    pathing_radius, dry_run
                )

                if not result.is_success:
                    # Retry with modified parameters for belts
                    source_pos_adjusted = self._adjust_belt_position(source_pos, source_entity)
                    target_pos_adjusted = self._adjust_belt_position(target_pos, target_entity)
                    result = self._attempt_path_finding(
                        source_pos_adjusted, target_pos_adjusted,
                        connection_type_names_values, num_available,
                        2, dry_run, False
                    )
                    pass

            case _:  # Power poles
                pathing_radius = 4  # Larger radius for poles
                self._extend_collision_boxes(source_pos, target_pos)
                try:
                    result = self._attempt_path_finding(
                        source_pos, target_pos,
                        connection_type_names_values, num_available,
                        pathing_radius, dry_run, True
                    )
                finally:
                    self._clear_collision_boxes()

        if not result.is_success:
            raise Exception(
               # f"Failed to connect {connection_prototype} from {source_pos} to {target_pos}. "
                f"{self.get_error_message(result.error_message.lstrip())}"
            )

        if dry_run:
            return {
                "number_of_entities_required": result.required_entities,
                "number_of_entities_available": num_available
            }

        # Process created entities
        path = []
        groupable_entities = []

        for entity_data in result.entities.values():
            if not isinstance(entity_data, dict):
                continue

            try:
                self._process_warnings(entity_data)
                entity = metaclasses[entity_data['name']](prototype=names_to_type[entity_data['name']], **entity_data)

                if entity.prototype in (Prototype.TransportBelt, Prototype.UndergroundBelt,
                                        Prototype.FastTransportBelt, Prototype.FastUndergroundBelt,
                                        Prototype.ExpressTransportBelt, Prototype.ExpressUndergroundBelt,
                                        Prototype.StoneWall,
                                        Prototype.Pipe,Prototype.UndergroundPipe,
                                        Prototype.SmallElectricPole, Prototype.BigElectricPole, Prototype.MediumElectricPole):
                    groupable_entities.append(entity)
                else:
                    path.append(entity)
            except Exception as e:
                if entity_data:
                    raise Exception(
                        f"Failed to create {connection_prototype} object from response: {result.raw_response}") from e

        # Process entity groups based on connection type
        entity_groups = self._process_entity_groups(
            connection_type, groupable_entities,
            source_entity, target_entity, source_pos
        )

        return _deduplicate_entities(path) + entity_groups

    def _process_warnings(self, entity_data: Dict):
        """Process warnings in entity data"""
        if not entity_data.get('warnings'):
            entity_data['warnings'] = []
        else:
            warnings = entity_data['warnings']
            entity_data['warnings'] = list(warnings.values()) if isinstance(warnings, dict) else [warnings]

    def _process_entity_groups(self,
                               connection_type: Prototype,
                               groupable_entities: List[Entity],
                               source_entity: Optional[Entity],
                               target_entity: Optional[Entity],
                               source_pos: Position) -> List[EntityGroup]:
        """Process and create entity groups based on connection type"""
        match connection_type:
            case Prototype.ExpressTransportBelt | Prototype.FastTransportBelt | Prototype.TransportBelt | Prototype.UndergroundBelt | Prototype.FastUndergroundBelt | Prototype.ExpressUndergroundBelt:
                return self._process_belt_groups(
                    groupable_entities, source_entity,
                    target_entity, source_pos
                )

            case Prototype.Pipe | Prototype.UndergroundPipe:
                return self._process_pipe_groups(
                    groupable_entities, source_pos
                )

            case Prototype.StoneWall:
                return self._process_groups(Prototype.StoneWall,
                    groupable_entities, source_pos
                )

            case _:  # Power poles
                return self._process_power_groups(
                    groupable_entities, source_pos
                )

    def _process_belt_groups(self,
                             groupable_entities: List[Entity],
                             source_entity: Optional[Entity],
                             target_entity: Optional[Entity],
                             source_pos: Position) -> List[BeltGroup]:
        """Process transport belt groups"""
        if isinstance(source_entity, BeltGroup):
            entity_groups = agglomerate_groupable_entities(groupable_entities)
        elif isinstance(target_entity, BeltGroup):
            entity_groups = agglomerate_groupable_entities(groupable_entities + target_entity.belts)
        else:
            entity_groups = agglomerate_groupable_entities(groupable_entities)

        # Deduplicate belts in groups
        for group in entity_groups:
            if hasattr(group,'belts'):
                group.belts = _deduplicate_entities(group.belts)

        # Handle belt rotation for group connections
        if isinstance(source_entity, BeltGroup) and entity_groups: #isinstance(target_entity, BeltGroup):
            self.rotate_end_belt_to_face(source_entity, entity_groups[0])
            #self.rotate_final_belt_when_connecting_groups(source_entity, entity_groups[0])

        if isinstance(target_entity, BeltGroup) and entity_groups:
            self.rotate_end_belt_to_face(entity_groups[0], target_entity)
            #self.rotate_final_belt_when_connecting_groups(entity_groups[0], source_entity)

        # Get final groups and filter to relevant one
        entity_groups = self.get_entities(
            {Prototype.TransportBelt, Prototype.ExpressTransportBelt, Prototype.FastTransportBelt, Prototype.UndergroundBelt, Prototype.FastUndergroundBelt, Prototype.ExpressUndergroundBelt},
            source_pos
        )

        for group in entity_groups:
            if source_pos in [entity.position for entity in group.belts]:
                return cast(List[BeltGroup], [group])

        return cast(List[BeltGroup], entity_groups)

    def _update_belt_group(self, new_belt: BeltGroup, source_belt: TransportBelt, target_belt: TransportBelt):
        new_belt.outputs[0] = source_belt
        for belt in new_belt.belts:
            if belt.position == source_belt.position:
                belt.input_position = source_belt.input_position
                belt.output_position = source_belt.output_position
                belt.direction = source_belt.direction
                belt.is_source = source_belt.is_source
                belt.is_terminus = source_belt.is_terminus

                if not belt.is_terminus and belt in new_belt.outputs:
                    new_belt.outputs.remove(belt)
                if not belt.is_source and belt in new_belt.inputs:
                    new_belt.inputs.remove(belt)

            if belt.position == target_belt.position:
                belt.is_source = target_belt.is_source
                belt.is_terminus = target_belt.is_terminus

                if not belt.is_terminus and belt in new_belt.outputs:
                    new_belt.outputs.remove(belt)
                if not belt.is_source and belt in new_belt.inputs:
                    new_belt.inputs.remove(belt)

    def rotate_end_belt_to_face(self, source_belt_group: BeltGroup, target: BeltGroup) -> BeltGroup:
        if not source_belt_group.outputs:
            return source_belt_group

        source_belt = source_belt_group.outputs[0]
        target_belt = target.inputs[0]
        source_pos = source_belt.position
        target_pos = target_belt.position

        if not source_pos.is_close(target_pos, 1.001): # epsilon for
            return source_belt_group

        # Calculate relative position
        relative_pos = (
            numpy.sign(source_pos.x - target_pos.x),
            numpy.sign(source_pos.y - target_pos.y)
        )


        # Don't rotate if belt is already facing correct direction
        match relative_pos:
            case(1, 1):
                pass  #raise Exception("Cannot rotate non adjacent belts to face one another")

            case (-1, -1):
                pass #raise Exception("Cannot rotate non adjacent belts to face one another")

            case (1, _) if source_belt.direction.value not in (Direction.LEFT.value, Direction.RIGHT.value):
                # Source is to right of target - point left
                source_belt = self.rotate_entity(source_belt, Direction.LEFT)

            case (-1, _) if source_belt.direction.value not in (Direction.LEFT.value, Direction.RIGHT.value):
                # Source is to left of target - point right
                source_belt = self.rotate_entity(source_belt, Direction.RIGHT)

            case (_, 1) if source_belt.direction.value not in (Direction.UP.value, Direction.DOWN.value):
                # Source is below target - point up
                source_belt = self.rotate_entity(source_belt, Direction.UP)

            case (_, -1) if source_belt.direction.value not in (Direction.UP.value, Direction.DOWN.value):
                # Source is above target - point down
                source_belt = self.rotate_entity(source_belt, Direction.DOWN)

        # Update the belt group connections
        target_belt = self.get_entity(target_belt.prototype, target_belt.position)
        self._update_belt_group(source_belt_group, source_belt, target_belt)

        return source_belt


    # def rotate_final_belt_when_connecting_groups(self, new_belt: BeltGroup, target: BeltGroup) -> BeltGroup:
    #     if not new_belt.outputs:
    #         return new_belt
    #     source_belt = new_belt.outputs[0]
    #     target_belt = target.inputs[0]
    #     source_belt_position = new_belt.outputs[0].position
    #     target_belt_position = target.inputs[0].input_position
    #     if source_belt_position.x > target_belt_position.x and not source_belt.direction.value == Direction.LEFT.value: # We only want to curve the belt, not invert it
    #         # It is necessary to use the direction enums from the game state
    #         source_belt = self.rotate_entity(source_belt, Direction.RIGHT)
    #     elif source_belt_position.x < target_belt_position.x and not source_belt.direction.value == Direction.RIGHT.value:
    #         source_belt = self.rotate_entity(source_belt, Direction.LEFT)
    #     elif source_belt_position.y > target_belt_position.y and not source_belt.direction.value == Direction.UP.value:
    #         source_belt = self.rotate_entity(source_belt, Direction.DOWN)
    #     elif source_belt_position.y < target_belt_position.y and not source_belt.direction.value == Direction.DOWN.value:
    #         source_belt = self.rotate_entity(source_belt, Direction.UP)
    #
    #     # Check to see if this is still a source / terminus
    #     target_belt = self.get_entity(target_belt.prototype, target_belt.position)
    #     self._update_belt_group(new_belt, source_belt, target_belt)  # Update the belt group with the new direction of the source belt.)
    #
    #     return new_belt

    def _process_pipe_groups(self,
                             groupable_entities: List[Entity],
                             source_pos: Position) -> List[PipeGroup]:
        """Process pipe groups"""
        entity_groups = self.get_entities({Prototype.Pipe, Prototype.UndergroundPipe}, source_pos)

        for group in entity_groups:
            group.pipes = _deduplicate_entities(group.pipes)
            if source_pos in [entity.position for entity in group.pipes]:
                return [group]

        return entity_groups

    def _process_groups(self,
                        prototype: Prototype,
                        groupable_entities: List[Entity],
                        source_pos: Position) -> List[PipeGroup]:
        """Process other groups"""
        entity_groups = self.get_entities(prototype, source_pos)

        for group in entity_groups:
            group.entities = _deduplicate_entities(group.entities)
            if source_pos in [entity.position for entity in group.entities]:
                return [group]

        return entity_groups

    def _process_pipe_groups(self,
                             groupable_entities: List[Entity],
                             source_pos: Position) -> List[PipeGroup]:
        """Process pipe groups"""
        entity_groups = self.get_entities({Prototype.Pipe, Prototype.UndergroundPipe}, source_pos)

        for group in entity_groups:
            group.pipes = _deduplicate_entities(group.pipes)
            if source_pos in [entity.position for entity in group.pipes]:
                return [group]

        return entity_groups

    def _attempt_to_get_entity(self,
                               position: Position,
                               get_connectors: bool = False) -> Union[Position, Entity, EntityGroup]:
        """
        Attempts to find an entity at the given position.

        Args:
            position: The position to check
            get_connectors: If True, returns connector entities (belts, pipes) instead of treating them as positions

        Returns:
            - The original position if no entity is found
            - The position if a connector entity is found and get_connectors is False
            - The entity or entity group if found and either get_connectors is True or it's not a connector
        """
        entities = self.get_entities(position=position, radius=0.1)

        if not entities:
            return position

        entity = entities[0]

        # If we found a connector entity (belt/pipe) and don't want connectors,
        # just return the position
        if not get_connectors and isinstance(entity, (BeltGroup, TransportBelt, PipeGroup, Pipe)):
            return position

        return entity

    def _process_power_groups(self,
                              groupable_entities: List[Entity],
                              source_pos: Position) -> List[ElectricityGroup]:
        """Process power pole groups"""
        return cast(List[ElectricityGroup], self.get_entities(
            {Prototype.SmallElectricPole, Prototype.BigElectricPole, Prototype.MediumElectricPole},
            source_pos
        ))

    def _adjust_belt_position(self,
                              pos: Position,
                              entity: Optional[Entity]) -> Position:
        """Adjust belt position for better path finding"""
        if not entity or isinstance(entity, Position):
            entity = self._attempt_to_get_entity(pos, get_connectors=True)
            if entity and isinstance(entity, BeltGroup):
                return entity.outputs[0].output_position
        return pos