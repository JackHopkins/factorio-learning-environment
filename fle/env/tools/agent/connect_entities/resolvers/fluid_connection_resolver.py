from typing import Union, Tuple, List, Optional

from fle.env import (
    FluidHandler,
    Position,
    Entity,
    Generator,
    Boiler,
    OffshorePump,
    Pipe,
    IndexedPosition,
    MultiFluidHandler,
    PipeGroup,
    PumpJack,
)
from fle.env.game_types import Prototype, prototype_by_name
from fle.env.tools.agent.connect_entities.resolver import Resolver


class FluidConnectionResolver(Resolver):
    def __init__(self, *args):
        super().__init__(*args)

    def _adjust_connection_point(
        self, point: Union[Position, IndexedPosition], entity: Union[Entity, Position]
    ) -> Position:
        if not isinstance(entity, Entity):
            return point
        x, y = point.x, point.y

        if x % 1 == 0:
            x += 0.5 if x > entity.position.x else -0.5 if x < entity.position.x else 0
        if y % 1 == 0:
            y += 0.5 if y > entity.position.y else -0.5 if y < entity.position.y else 0
        point.x = x
        point.y = y
        return point

    def _is_blocked(self, pos: Position, entity=None) -> bool:
        # if isinstance(entity, Pipe) or isinstance(entity, PipeGroup):
        #    return False
        entities = self.get_entities(position=pos, radius=0.5)
        return bool(entities)

    def _refresh_entity(self, entity: Entity):
        entity = self.get_entities(
            {prototype_by_name[entity.name]}, position=entity.position, radius=0.5
        )[0]
        return entity

    def _get_source_fluid(self, entity: FluidHandler) -> str:
        # update the source entity
        updated_source_entity = self.get_entities(position=entity.position, radius=0)
        if len(updated_source_entity) == 1:
            entity = updated_source_entity[0]

        # If the entity is producing an output liquid (i.e in a chemical plant or oil refinery, go through the output
        if hasattr(entity, "output_connection_points"):
            if entity.output_connection_points:
                return [x.type for x in entity.output_connection_points]

        if entity.fluid_box:
            fluids = [fluid["name"] for fluid in entity.fluid_box]
            return fluids
        if isinstance(entity, PumpJack):
            return ["crude-oil"]
        if isinstance(entity, OffshorePump):
            return ["water"]
        return None

    def resolve(
        self, source: Union[Position, Entity], target: Union[Position, Entity]
    ) -> List[Tuple[Position, Position]]:
        """Returns prioritized list of source/target position pairs to attempt connections."""

        # if isinstance(target, Entity):
        #    updated_targets = self.get_entities(position = target.position, radius=0)
        #    if len(updated_targets) == 1:
        #        target = updated_targets[0]
        #
        # if isinstance(source, Entity):
        #    updated_sources = self.get_entities(position = source.position, radius=0)
        #    if len(updated_sources) == 1:
        #        source = updated_sources[0]
        #
        source_fluid_positions = self.get_source_fluid_positions(source)
        target_fluid_positions = self.get_target_fluid_positions(target)
        source_fluid_positions, target_fluid_positions = self.deal_with_edge_cases(
            source, source_fluid_positions, target, target_fluid_positions
        )

        if isinstance(target, MultiFluidHandler):
            self.check_for_recipe_requirement(target, source_fluid_positions)

        # Generate all possible combinations, sorted by combined distance
        connection_pairs = []
        for target_position in target_fluid_positions:
            adjusted_target_position = self._adjust_connection_point(
                target_position, target
            )
            if self._is_blocked(adjusted_target_position, target):
                continue
            # if we expect a type of fluid, search for that type of fluid in the source
            if target_position.type:
                valid_source_positions = [
                    self._adjust_connection_point(x, source)
                    for x in source_fluid_positions
                    if (x.type == target_position.type or x.type == "all")
                ]
                for source_position in valid_source_positions:
                    if not self._is_blocked(source_position, source):
                        connection_pairs.append(
                            (source_position, adjusted_target_position)
                        )
            # else we can connect any type of fluid
            else:
                adjusted_source_positions = [
                    self._adjust_connection_point(x, source)
                    for x in source_fluid_positions
                ]
                for source_position in adjusted_source_positions:
                    # check for blocking
                    # If source is pipe or pipegroup, then dont need to check for blocking
                    if not self._is_blocked(source_position, source):
                        connection_pairs.append(
                            (source_position, adjusted_target_position)
                        )
        if not connection_pairs:
            source_location = (
                f"{source.prototype} at {source.position}"
                if isinstance(source, Entity)
                else f"{source}"
            )
            target_location = (
                f"{target.prototype} at {target.position}"
                if isinstance(target, Entity)
                else f"{target}"
            )

            # first check if target expects fluids but source does not have them
            target_fluids = [x.type for x in target_fluid_positions if x.type]
            source_fluids = [x.type for x in source_fluid_positions if x.type]
            intersection = set(target_fluids).intersection(set(source_fluids))
            # if target expects fluids but source does not have them
            if target_fluids and not intersection:
                raise Exception(
                    f"Fluids currently at source {source_location}: {source_fluids} not needed and expected by the target {target_location}"
                )
            # generate a generic error message
            raise Exception(
                f"Did not find any valid connections between source {source_location} and target {target_location}. Make sure none of the source or target connections points are blocked and the target is able to receive the fluid from the source"
            )
        # Sort pairs by total Manhattan distance
        return sorted(
            connection_pairs,
            key=lambda pair: (abs(pair[0].x - pair[1].x) + abs(pair[0].y - pair[1].y)),
        )

    def _get_all_connection_points(
        self,
        fluid_handler: FluidHandler,
        reference_pos: Position,
        connection_points,
        source_fluids: Optional[List[str]] = None,
    ) -> List[Position]:
        """Get all possible connection points sorted by distance."""
        if len(connection_points) == 0:
            return []

        if source_fluids and isinstance(connection_points[0], IndexedPosition):
            connection_points = list(
                filter(lambda x: x.type in source_fluids, connection_points)
            )

        # Sort all connection points by distance to reference position
        sorted_points = sorted(
            connection_points,
            key=lambda point: abs(point.x - reference_pos.x)
            + abs(point.y - reference_pos.y),
        )

        # Adjust each point and filter out blocked ones
        valid_points = []
        for point in sorted_points:
            adjusted = self._adjust_connection_point(point, fluid_handler)
            if not self._is_blocked(adjusted):
                valid_points.append(adjusted)

        return valid_points

    def check_for_recipe_requirement(self, target_entity, source_fluid_positions):
        source_fluids = [x.type for x in source_fluid_positions if x.type]
        if not source_fluids:
            raise Exception(
                f"The source does not have fluid in it. Cannot connect an empty source to a {target_entity.prototype}. The {target_entity.prototype} input handlers are fluid specific so source entity needs to have fluid in it"
            )
        if not target_entity.recipe:
            raise Exception(
                f"Cannot connect to a {target_entity.prototype} until a recipe has been set."
            )
        input_connections = [x.type for x in target_entity.input_connection_points]
        # get the overlap between source fluids and input connections
        fluid_intersections = set(source_fluids).intersection(set(input_connections))
        if not fluid_intersections:
            raise Exception(
                f"Fluids currently at source entity {source_fluids} not needed and expected by the recipe at {target_entity.name} at {target_entity.position}"
            )
        return True

    def get_source_fluid_positions(self, source):
        match source:
            case OffshorePump():
                source_positions = [
                    IndexedPosition(x=pos.x, y=pos.y, type="water")
                    for pos in source.connection_points
                ]
            case Boiler():
                source_steam_positions = [
                    IndexedPosition(
                        x=source.steam_output_point.x,
                        y=source.steam_output_point.y,
                        type="steam",
                    )
                ]
                source_water_positions = [
                    IndexedPosition(x=pos.x, y=pos.y, type="water")
                    for pos in source.connection_points
                ]
                source_positions = source_steam_positions + source_water_positions
            case Generator():
                source_positions = [
                    IndexedPosition(x=pos.x, y=pos.y, type="steam")
                    for pos in source.connection_points
                ]
            case MultiFluidHandler():
                source_positions = source.output_connection_points
            case PumpJack():
                source_positions = [
                    IndexedPosition(x=pos.x, y=pos.y, type="crude-oil")
                    for pos in source.connection_points
                ]

            case FluidHandler():
                liquid = [fluid["name"] for fluid in source.fluid_box]
                source_liquid = liquid[0] if liquid else ""
                source_positions = [
                    IndexedPosition(x=pos.x, y=pos.y, type=source_liquid)
                    for pos in source.connection_points
                ]

            case Pipe():
                fluid = source.fluid if source.fluid else ""
                source_positions = self.get_pipe_connection_positions(
                    source, set(), fluid
                )
            case Position():
                # allow all connections from this source
                source_positions = [IndexedPosition(x=source.x, y=source.y, type="all")]

            case Entity():
                source_positions = [
                    IndexedPosition(x=source.position.x, y=source.position.y, type="")
                ]

            case PipeGroup():
                pipes = [
                    pipe for pipe in source.pipes if pipe.prototype == Prototype.Pipe
                ]
                source_positions = []
                underground_positions = set(
                    [
                        pipe.position
                        for pipe in source.pipes
                        if pipe.prototype == Prototype.UndergroundPipe
                    ]
                )
                for pipe in pipes:
                    fluid = pipe.fluid if pipe.fluid else ""
                    surrounding_positions = self.get_pipe_connection_positions(
                        pipe, underground_positions, fluid
                    )
                    source_positions += surrounding_positions
            case _:
                raise Exception(
                    f"{type(source)} is not a supported source object for fluid connection"
                )
        return source_positions

    def get_pipe_connection_positions(self, pipe, underground_positions, fluid):
        positions = [IndexedPosition(x=pipe.position.x, y=pipe.position.y, type=fluid)]
        if pipe.position.up() not in underground_positions:
            positions.append(
                IndexedPosition(
                    x=pipe.position.up().x, y=pipe.position.up().y, type=fluid
                )
            )
        if pipe.position.down() not in underground_positions:
            positions.append(
                IndexedPosition(
                    x=pipe.position.down().x, y=pipe.position.down().y, type=fluid
                )
            )
        if pipe.position.left() not in underground_positions:
            positions.append(
                IndexedPosition(
                    x=pipe.position.left().x, y=pipe.position.left().y, type=fluid
                )
            )
        if pipe.position.right() not in underground_positions:
            positions.append(
                IndexedPosition(
                    x=pipe.position.right().x, y=pipe.position.right().y, type=fluid
                )
            )
        return positions

    def get_target_fluid_positions(self, target):
        """
        Get the target fluid positions
        if type is "", then any input fluid connection is allowed to that position
        """
        match target:
            # offshore pump does not expect anything, only provides water
            case OffshorePump():
                target_positions = [
                    IndexedPosition(x=pos.x, y=pos.y, type="")
                    for pos in target.connection_points
                ]
            # boiler can also receive steam because you can do engine-to-boiler connections
            case Boiler():
                target_steam_positions = [
                    IndexedPosition(
                        x=target.steam_output_point.x,
                        y=target.steam_output_point.y,
                        type="steam",
                    )
                ]
                target_water_positions = [
                    IndexedPosition(x=pos.x, y=pos.y, type="water")
                    for pos in target.connection_points
                ]
                target_positions = target_steam_positions + target_water_positions
            case Generator():
                target_positions = [
                    IndexedPosition(x=pos.x, y=pos.y, type="steam")
                    for pos in target.connection_points
                ]
            case MultiFluidHandler():
                target_positions = target.input_connection_points
            case FluidHandler():
                target_positions = [
                    IndexedPosition(x=pos.x, y=pos.y, type="")
                    for pos in target.connection_points
                ]
            case Pipe():
                target_positions = self.get_pipe_connection_positions(target, set(), "")
            case Position():
                target_positions = [IndexedPosition(x=target.x, y=target.y, type="")]

            case Entity():
                target_positions = [
                    IndexedPosition(x=target.position.x, y=target.position.y, type="")
                ]
            case PipeGroup():
                pipes = [
                    pipe for pipe in target.pipes if pipe.prototype == Prototype.Pipe
                ]
                target_positions = []
                underground_positions = set(
                    [
                        pipe.position
                        for pipe in target.pipes
                        if pipe.prototype == Prototype.UndergroundPipe
                    ]
                )
                for pipe in pipes:
                    pipe_positions = self.get_pipe_connection_positions(
                        pipe, underground_positions, ""
                    )
                    target_positions += pipe_positions
            case _:
                raise Exception(
                    f"{type(target)} is not a supported target object for fluid connection"
                )
        return target_positions

    def deal_with_edge_cases(self, source, source_positions, target, target_positions):
        """
        To allow for source-target mixing, we add some additional logic
        """
        # boiler to boiler only move water
        if isinstance(source, Boiler) and isinstance(target, Boiler):
            source_positions = [x for x in source_positions if x.type == "water"]
            target_positions = [x for x in target_positions if x.type == "water"]
        # boiler to pump only move water
        if isinstance(source, Boiler) and isinstance(target, OffshorePump):
            source_positions = [x for x in source_positions if x.type == "water"]
        return source_positions, target_positions
