"""
Simplified Continuous Cinematographer - Redesigned around meaningful agent movements.

This module implements the redesigned cinematographer that focuses on a single principle:
the camera should stay fixed where the action is happening.

Key principles:
- Camera stays locked where agent is active until agent moves away
- Only reposition camera when agent moves out of current camera bounds
- Confirm agent has taken action in new location before splicing shots
- Special case: Connect Entities gets bird's-eye view of bounding box
- Avoid high-fidelity tracking - focus on meaningful movements with actions
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from fle.eval.analysis.simplified_camera_tracker import (
    SimplifiedCameraTracker,
    create_action_context,
)


class ShotType(Enum):
    """Types of camera shots."""

    LOCKED = "locked"  # Camera is locked to current action area
    TRACKING = "tracking"  # Camera is following agent movement
    CONNECT_ENTITIES = "connect_entities"  # Bird's-eye view for connections


@dataclass
class SimplifiedShot:
    """Represents a simplified camera shot."""

    id: str
    shot_type: ShotType
    position: Tuple[float, float]
    zoom: float = 1.0
    dwell_ticks: int = 180  # 3 seconds default
    pan_ticks: int = 60  # 1 second default
    bounding_box: Optional[List[List[float]]] = None
    tags: List[str] = field(default_factory=list)


class SimplifiedContinuousCinematographer:
    """
    Simplified continuous cinematographer focused on meaningful agent movements.

    This cinematographer implements the new principle: camera stays fixed where
    action is happening, only moving when agent moves out of bounds.
    """

    def __init__(self, player: int = 1, camera_radius: float = 15.0):
        self.player = player
        self.tracker = SimplifiedCameraTracker(
            player=player, camera_radius=camera_radius
        )
        self.shots: List[SimplifiedShot] = []
        self.current_program_id: Optional[str] = None

    def process_program(
        self,
        program_id: str,
        actions: List[Dict[str, Any]],
        world_context: Dict[str, Any],
    ) -> None:
        """Process a program with simplified camera tracking."""

        self.current_program_id = program_id
        print(f"Processing program {program_id} with simplified tracking")

        # Get initial player position from world context
        player_pos = world_context.get("player_position", [0, 0])
        current_position = (float(player_pos[0]), float(player_pos[1]))
        print(f"Initial player position: {current_position}")

        # Get current tick for timing calculations
        current_tick = world_context.get("current_tick", 0)

        # Track initial position
        self._track_agent_position(current_position, program_id, current_tick)

        # Process each action
        for i, action in enumerate(actions):
            action_type = action.get("type", "unknown")
            action_pos = self._extract_action_position(action, world_context)

            if action_pos:
                # Check if this is a Connect Entities action
                if action_type == "connect_entities":
                    bounding_box = self._calculate_connect_entities_bbox(
                        action, world_context
                    )
                    self._track_connect_entities_action(
                        program_id, action_pos, bounding_box, action, current_tick
                    )
                else:
                    # Regular action tracking
                    self._track_regular_action(
                        program_id, action_type, action_pos, action, current_tick
                    )

    def _track_agent_position(
        self, position: Tuple[float, float], program_id: str, current_tick: int = 0
    ) -> None:
        """Track agent position and potentially create shots."""

        shot = self.tracker.track_agent_movement(position, None, current_tick)
        if shot:
            self._add_shot_from_tracker(shot)

    def _track_regular_action(
        self,
        program_id: str,
        action_type: str,
        position: Tuple[float, float],
        action: Dict[str, Any],
        current_tick: int = 0,
    ) -> None:
        """Track a regular action (not Connect Entities)."""

        action_context = create_action_context(
            program_id=program_id, action_type=action_type, position=position
        )

        shot = self.tracker.track_agent_movement(position, action_context, current_tick)
        if shot:
            self._add_shot_from_tracker(shot)

    def _track_connect_entities_action(
        self,
        program_id: str,
        position: Tuple[float, float],
        bounding_box: Optional[List[List[float]]],
        action: Dict[str, Any],
        current_tick: int = 0,
    ) -> None:
        """Track a Connect Entities action with special bird's-eye view."""

        action_context = create_action_context(
            program_id=program_id,
            action_type="connect_entities",
            position=position,
            bounding_box=bounding_box,
        )

        shot = self.tracker.track_agent_movement(position, action_context, current_tick)
        if shot:
            self._add_shot_from_tracker(shot)

    def _add_shot_from_tracker(self, tracker_shot: Dict[str, Any]) -> None:
        """Add a shot from the tracker to our shot list."""

        shot_type = ShotType.TRACKING
        if "connect_entities" in tracker_shot.get("tags", []):
            shot_type = ShotType.CONNECT_ENTITIES
        elif "tracking" in tracker_shot.get("tags", []):
            shot_type = ShotType.TRACKING

        # Extract position from shot kind
        position = (0.0, 0.0)
        if tracker_shot["kind"]["type"] == "focus_position":
            pos = tracker_shot["kind"]["pos"]
            position = (float(pos[0]), float(pos[1]))
        elif tracker_shot["kind"]["type"] == "zoom_to_fit":
            bbox = tracker_shot["kind"]["bbox"]
            center_x = (bbox[0][0] + bbox[1][0]) / 2
            center_y = (bbox[0][1] + bbox[1][1]) / 2
            position = (center_x, center_y)

        shot = SimplifiedShot(
            id=tracker_shot["id"],
            shot_type=shot_type,
            position=position,
            zoom=tracker_shot.get("zoom", 1.0),
            dwell_ticks=tracker_shot.get("dwell_ticks", 180),
            pan_ticks=tracker_shot.get("pan_ticks", 60),
            bounding_box=tracker_shot["kind"].get("bbox")
            if tracker_shot["kind"]["type"] == "zoom_to_fit"
            else None,
            tags=tracker_shot.get("tags", []),
        )

        self.shots.append(shot)
        print(f"Added {shot_type.value} shot at {position}")

    def _extract_action_position(
        self, action: Dict[str, Any], world_context: Dict[str, Any]
    ) -> Optional[Tuple[float, float]]:
        """Extract position from action using world context resolvers."""

        action_type = action.get("type")
        args = action.get("args", {})

        # Try to resolve position based on action type
        if action_type == "move_to":
            pos_expr = args.get("destination") or args.get("pos_src")
        elif action_type in ["place_entity", "place_entity_next_to"]:
            pos_expr = args.get("position")
        elif action_type == "insert_item":
            pos_expr = args.get("position")
        elif action_type == "connect_entities":
            # For connect_entities, return the midpoint of the two entities
            a_expr = args.get("a_expr")
            b_expr = args.get("b_expr")
            if a_expr and b_expr:
                resolve_pos = world_context.get("resolve_position")
                if callable(resolve_pos):
                    try:
                        pos_a = resolve_pos(a_expr)
                        pos_b = resolve_pos(b_expr)
                        if (
                            isinstance(pos_a, (list, tuple))
                            and len(pos_a) >= 2
                            and isinstance(pos_b, (list, tuple))
                            and len(pos_b) >= 2
                        ):
                            # Return midpoint of the two positions
                            mid_x = (float(pos_a[0]) + float(pos_b[0])) / 2
                            mid_y = (float(pos_a[1]) + float(pos_b[1])) / 2
                            return (mid_x, mid_y)
                    except Exception:
                        pass
            return None
        else:
            return None

        if not pos_expr:
            return None

        # Use world context resolver
        resolve_pos = world_context.get("resolve_position")
        if callable(resolve_pos):
            try:
                resolved = resolve_pos(pos_expr)
                if isinstance(resolved, (list, tuple)) and len(resolved) >= 2:
                    return (float(resolved[0]), float(resolved[1]))
            except Exception:
                pass

        # Fallback to player position
        player_pos = world_context.get("player_position", [0, 0])
        return (float(player_pos[0]), float(player_pos[1]))

    def _calculate_connect_entities_bbox(
        self, action: Dict[str, Any], world_context: Dict[str, Any]
    ) -> Optional[List[List[float]]]:
        """Calculate bounding box for Connect Entities action."""

        args = action.get("args", {})
        a_expr = args.get("a_expr")
        b_expr = args.get("b_expr")

        if not a_expr or not b_expr:
            return None

        resolve_pos = world_context.get("resolve_position")
        if not callable(resolve_pos):
            return None

        try:
            pos_a = resolve_pos(a_expr)
            pos_b = resolve_pos(b_expr)

            if (
                isinstance(pos_a, (list, tuple))
                and len(pos_a) >= 2
                and isinstance(pos_b, (list, tuple))
                and len(pos_b) >= 2
            ):
                # Create bounding box around both entities
                padding = 10.0  # Add some padding
                min_x = min(pos_a[0], pos_b[0]) - padding
                max_x = max(pos_a[0], pos_b[0]) + padding
                min_y = min(pos_a[1], pos_b[1]) - padding
                max_y = max(pos_a[1], pos_b[1]) + padding

                return [[min_x, min_y], [max_x, max_y]]
        except Exception:
            pass

        return None

    def build_plan(self) -> Dict[str, Any]:
        """Build the final shot plan for execution."""

        # Convert simplified shots to the expected format
        shot_plan = []
        for i, shot in enumerate(self.shots):
            if shot.bounding_box:
                # Connect Entities shot with bounding box
                shot_dict = {
                    "id": shot.id,
                    "seq": i,
                    "kind": {"type": "zoom_to_fit", "bbox": shot.bounding_box},
                    "pan_ticks": shot.pan_ticks,
                    "dwell_ticks": shot.dwell_ticks,
                    "zoom": shot.zoom,
                    "tags": shot.tags + [shot.shot_type.value],
                }
            else:
                # Regular position shot
                shot_dict = {
                    "id": shot.id,
                    "seq": i,
                    "kind": {"type": "focus_position", "pos": list(shot.position)},
                    "pan_ticks": shot.pan_ticks,
                    "dwell_ticks": shot.dwell_ticks,
                    "zoom": shot.zoom,
                    "tags": shot.tags + [shot.shot_type.value],
                }

            shot_plan.append(shot_dict)

        # Use the zoom from the first shot as start_zoom, or default to 1.0
        start_zoom = 1.0
        if self.shots and self.shots[0].zoom is not None:
            start_zoom = self.shots[0].zoom

        return {
            "player": self.player,
            "start_zoom": start_zoom,
            "shots": shot_plan,
            "plan_id": f"simplified-{uuid.uuid4().hex[:8]}",
            "capture": True,
            "capture_dir": "cinema_seq",
        }

    def reset(self) -> None:
        """Reset the cinematographer for a new session."""
        self.tracker.reset()
        self.shots.clear()
        self.current_program_id = None

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about generated shots."""
        if not self.shots:
            return {"total_shots": 0, "total_duration": 0}

        total_duration = sum(shot.pan_ticks + shot.dwell_ticks for shot in self.shots)
        shot_type_counts = {}
        for shot in self.shots:
            shot_type = shot.shot_type.value
            shot_type_counts[shot_type] = shot_type_counts.get(shot_type, 0) + 1

        tracker_stats = self.tracker.get_stats()

        return {
            "total_shots": len(self.shots),
            "total_duration": total_duration,
            "shot_type_counts": shot_type_counts,
            "tracker_stats": tracker_stats,
            "current_program_id": self.current_program_id,
        }


def create_simplified_continuous_cinematographer(
    player: int = 1, camera_radius: float = 15.0
) -> SimplifiedContinuousCinematographer:
    """Create a new simplified continuous cinematographer instance."""
    return SimplifiedContinuousCinematographer(
        player=player, camera_radius=camera_radius
    )
