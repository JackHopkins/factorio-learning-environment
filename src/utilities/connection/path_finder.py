from time import sleep
from typing import Dict, Optional

from factorio_instance import PLAYER
from .types import Position, PathResult, ConnectionError


class ConnectionPathFinder:
    """Handles finding valid paths between connection points"""

    def __init__(self, request_path, get_path, extend_collision_boxes, clear_collision_boxes):
        self.request_path = request_path
        self.get_path = get_path
        self.extend_collision_boxes = extend_collision_boxes
        self.clear_collision_boxes = clear_collision_boxes

    def find_path(
            self,
            source_pos: Position,
            target_pos: Position,
            connection_prototype: str,
            inventory_count: int,
            is_fluid_connection: bool = False,
            pathing_radius: float = 1,
            dry_run: bool = False
    ) -> PathResult:
        """
        Find a valid path between two points for the given connection type

        Args:
            source_pos: Starting position
            target_pos: Ending position
            connection_prototype: Type of connection to create
            inventory_count: Number of connection items available
            is_fluid_connection: Whether this is a fluid connection
            pathing_radius: Radius to use for path finding
            dry_run: Whether to actually create the connection

        Returns:
            PathResult containing success status and created entities
        """
        if is_fluid_connection:
            self.extend_collision_boxes(source_pos.to_bounding_box(target_pos))

        try:
            path_result = self._attempt_path_finding(
                source_pos,
                target_pos,
                connection_prototype,
                inventory_count,
                pathing_radius,
                dry_run
            )
        except Exception:
            # Retry with paths through entities allowed
            path_result = self._attempt_path_finding(
                source_pos,
                target_pos,
                connection_prototype,
                inventory_count,
                pathing_radius,
                dry_run,
                allow_paths_through_entities=True
            )
        finally:
            if is_fluid_connection:
                self.clear_collision_boxes()

        return path_result

    def _attempt_path_finding(
            self,
            source_pos: Position,
            target_pos: Position,
            connection_prototype: str,
            inventory_count: int,
            pathing_radius: float,
            dry_run: bool,
            allow_paths_through_entities: bool = False
    ) -> PathResult:
        """Attempt to find a path with the given parameters"""
        # Try different entity sizes for better pathing
        for entity_size in [2, 1.5, 1, 0.5]:
            path_handle = self.request_path(
                finish=Position(x=target_pos.x, y=target_pos.y),
                start=source_pos,
                allow_paths_through_own_entities=allow_paths_through_entities,
                radius=pathing_radius,
                entity_size=entity_size
            )

            # Give pathing system time to compute
            sleep(0.05)

            response = self._execute_path_request(
                source_pos,
                target_pos,
                path_handle,
                connection_prototype,
                dry_run,
                inventory_count
            )

            if isinstance(response, dict):
                return PathResult(
                    success=True,
                    entities=response.get('entities', []),
                    warnings=response.get('warnings', []),
                    number_of_entities=response.get('number_of_entities', 0)
                )

        raise ConnectionError(
            f"Could not find valid path from {source_pos} to {target_pos}"
        )

    def _execute_path_request(
            self,
            source_pos: Position,
            target_pos: Position,
            path_handle: str,
            connection_prototype: str,
            dry_run: bool,
            inventory_count: int
    ) -> Dict:
        """Execute the path request and return the response"""
        return self.get_path(
            path_handle
            # source_pos.x,
            # source_pos.y,
            # target_pos.x,
            # target_pos.y,
            #path_handle,
            # connection_prototype,
            # dry_run,
            # inventory_count
        )