from time import sleep
from typing import Union, Optional, List, Dict, cast

import numpy

from controllers.__action import Action
from controllers._clear_collision_boxes import ClearCollisionBoxes
from controllers._extend_collision_boxes import ExtendCollisionBoxes
from controllers._get_path import GetPath
from controllers._request_path import RequestPath
from controllers.get_entities import GetEntities
from controllers.get_entity import GetEntity
from controllers.inspect_inventory import InspectInventory
from controllers.pickup_entity import PickupEntity
from controllers.rotate_entity import RotateEntity
from factorio_entities import EntityGroup, Entity, Position, BeltGroup, PipeGroup, ElectricityGroup, TransportBelt, \
    Pipe, FluidHandler, MiningDrill, Inserter
from factorio_instance import PLAYER, Direction
from factorio_types import Prototype
from utilities.connection.path_result import PathResult
from utilities.connection.resolver import ConnectionType
from utilities.connection.resolvers.fluid_connection_resolver import FluidConnectionResolver
from utilities.connection.resolvers.power_connection_resolver import PowerConnectionResolver
from utilities.connection.resolvers.transport_connection_resolver import TransportConnectionResolver
from utilities.groupable_entities import _deduplicate_entities, agglomerate_groupable_entities


class ConnectEntities(Action):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        #self.game_state = game_state
        #self.connection = connection
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
            ConnectionType.POWER: PowerConnectionResolver()
        }

    def _get_connection_type(self, prototype: Prototype) -> ConnectionType:
        match prototype:
            case Prototype.Pipe:
                return ConnectionType.FLUID
            case Prototype.TransportBelt:
                return ConnectionType.TRANSPORT
            case Prototype.SmallElectricPole | Prototype.MediumElectricPole | Prototype.BigElectricPole:
                return ConnectionType.POWER
            case _:
                raise ValueError(f"Unsupported connection type: {prototype}")

    def __call__(self,
                 source: Union[Position, Entity, EntityGroup],
                 target: Union[Position, Entity, EntityGroup],
                 connection_type: Optional[Prototype] = None,
                 dry_run: bool = False) -> List[Union[Entity, EntityGroup]]:
        """Connect two entities or positions."""

        # Resolve connection type if not provided
        if not connection_type:
            connection_type = self._infer_connection_type(source, target)

        # Resolve positions into entities if they exist
        if isinstance(source, Position):
            source = self._resolve_position_into_entity(source)
        if isinstance(target, Position):
            target = self._resolve_position_into_entity(target)

        # Get resolver for this connection type
        resolver = self.resolvers[self._get_connection_type(connection_type)]

        # Resolve source and target positions
        prioritised_list_of_position_pairs = resolver.resolve(source, target)

        last_exception = None
        for source_pos, target_pos in prioritised_list_of_position_pairs:
            # Handle the actual connection
            try:
                return self._create_connection(
                    source_pos, target_pos,
                    connection_type, False,
                    source_entity=source if isinstance(source, (Entity, EntityGroup)) else None,
                    target_entity=target if isinstance(target, (Entity, EntityGroup)) else None
                )
            except Exception as e:
                last_exception = e

        raise Exception(
            f"Failed to connect {connection_type} from {source} to {target}. "
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
                              connection_prototype: str,
                              num_available: int,
                              pathing_radius: float = 1,
                              dry_run: bool = False,
                              allow_paths_through_own: bool = False) -> PathResult:
        """Attempt to find a path between two positions"""
        entity_sizes = [2, 1, 0.5, 0.25]  # Ordered from largest to smallest

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
                connection_prototype,
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
                           connection_type: Prototype,
                           dry_run: bool,
                           source_entity: Optional[Entity] = None,
                           target_entity: Optional[Entity] = None) -> List[Union[Entity, EntityGroup]]:
        """Create a connection between two positions"""
        connection_prototype, metaclass = connection_type.value
        inventory = self.inspect_inventory()
        num_available = inventory.get(connection_prototype, 0)

        # Determine connection strategy based on type
        match connection_type:
            case Prototype.Pipe:
                pathing_radius = 0.5
                self._extend_collision_boxes(source_pos, target_pos)
                try:
                    result = self._attempt_path_finding(
                        source_pos, target_pos,
                        connection_prototype, num_available,
                        pathing_radius, dry_run
                    )
                finally:
                    self._clear_collision_boxes()

            case Prototype.TransportBelt:
                pathing_radius = 0.5
                result = self._attempt_path_finding(
                    source_pos, target_pos,
                    connection_prototype, num_available,
                    pathing_radius, dry_run
                )

                if not result.is_success:
                    # Retry with modified parameters for belts
                    source_pos_adjusted = self._adjust_belt_position(source_pos, source_entity)
                    target_pos_adjusted = self._adjust_belt_position(target_pos, target_entity)
                    result = self._attempt_path_finding(
                        source_pos_adjusted, target_pos_adjusted,
                        connection_prototype, num_available,
                        2, dry_run, False
                    )
                    pass

            case _:  # Power poles
                pathing_radius = 4  # Larger radius for poles
                self._extend_collision_boxes(source_pos, target_pos)
                try:
                    result = self._attempt_path_finding(
                        source_pos, target_pos,
                        connection_prototype, num_available,
                        pathing_radius, dry_run, True
                    )
                finally:
                    self._clear_collision_boxes()

        if not result.is_success:
            raise Exception(
                f"Failed to connect {connection_prototype} from {source_pos} to {target_pos}. "
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
                entity = metaclass(prototype=connection_type, **entity_data)

                if entity.prototype in (Prototype.TransportBelt, Prototype.Pipe,
                                        Prototype.SmallElectricPole, Prototype.BigElectricPole,
                                        Prototype.MediumElectricPole):
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
            case Prototype.ExpressTransportBelt | Prototype.FastTransportBelt | Prototype.TransportBelt:
                return self._process_belt_groups(
                    groupable_entities, source_entity,
                    target_entity, source_pos
                )

            case Prototype.Pipe:
                return self._process_pipe_groups(
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
            {Prototype.TransportBelt, Prototype.ExpressTransportBelt, Prototype.FastTransportBelt},
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
        entity_groups = self.get_entities({Prototype.Pipe}, source_pos)

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