"""
Simplified Camera Tracker - Focus on meaningful agent movements.

This module implements a clean, simple camera tracking system based on a single principle:
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


class CameraState(Enum):
    """Camera tracking states."""

    LOCKED = "locked"  # Camera is locked to current action area
    TRACKING = "tracking"  # Camera is following agent movement
    TRANSITIONING = "transitioning"  # Camera is moving to new position


@dataclass
class CameraBounds:
    """Represents camera view bounds."""

    center: Tuple[float, float]
    radius: float  # Approximate radius of visible area
    zoom: float

    def contains_position(self, pos: Tuple[float, float], margin: float = 10.0) -> bool:
        """Check if position is within camera bounds with margin."""
        distance = (
            (pos[0] - self.center[0]) ** 2 + (pos[1] - self.center[1]) ** 2
        ) ** 0.5
        return distance <= (self.radius - margin)

    def distance_to_position(self, pos: Tuple[float, float]) -> float:
        """Calculate distance from camera center to position."""
        return ((pos[0] - self.center[0]) ** 2 + (pos[1] - self.center[1]) ** 2) ** 0.5


@dataclass
class ActionContext:
    """Context for tracking agent actions and camera positioning."""

    program_id: str
    action_type: str
    position: Tuple[float, float]
    entities_involved: List[Dict[str, Any]] = field(default_factory=list)
    is_connect_entities: bool = False
    bounding_box: Optional[List[List[float]]] = None


class SimplifiedCameraTracker:
    """
    Simplified camera tracker that focuses on meaningful agent movements.

    Philosophy:
    - Camera stays fixed where action is happening
    - Only move camera when agent moves out of current bounds
    - Confirm action taken in new location before repositioning
    - Special handling for Connect Entities with bird's-eye view
    - Keep-alive mechanism to prevent premature camera movement
    """

    def __init__(self, player: int = 1, camera_radius: float = 15.0):
        self.player = player
        self.camera_radius = camera_radius
        self.current_bounds: Optional[CameraBounds] = None
        self.state = CameraState.TRACKING
        self.last_agent_position: Optional[Tuple[float, float]] = None
        self.action_history: List[ActionContext] = []
        self.shots: List[Dict[str, Any]] = []

        # Configuration
        self.min_movement_threshold = 20.0  # Minimum distance to trigger camera move
        self.action_confirmation_ticks = 30  # Ticks to wait for action confirmation
        self.pending_action: Optional[ActionContext] = None

        # Keep-alive mechanism
        self.current_action_start_tick: Optional[int] = None
        self.action_keep_alive_ticks = 60  # 1 second to keep camera on current action
        self.is_action_in_progress = False

    def track_agent_movement(
        self,
        current_position: Tuple[float, float],
        action_context: Optional[ActionContext] = None,
        current_tick: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Track agent movement and determine if camera should be repositioned.

        Args:
            current_position: Current agent position
            action_context: Context about current action being performed
            current_tick: Current game tick for timing calculations

        Returns:
            Camera shot plan if repositioning is needed, None otherwise
        """

        # Initialize camera bounds if this is the first call
        if self.current_bounds is None:
            self._initialize_camera_bounds(current_position)
            return None

        # Handle action start/end tracking
        if action_context:
            self._handle_action_timing(action_context, current_tick)

        # Special case: Connect Entities always triggers bird's-eye view
        if action_context and action_context.is_connect_entities:
            return self._create_connect_entities_shot(action_context)

        # Check if we should keep camera on current action (keep-alive mechanism)
        if self._should_keep_camera_on_current_action(current_tick):
            print("Keeping camera on current action (keep-alive active)")
            return None

        # Check if agent has moved out of current camera bounds
        if self.last_agent_position is not None:
            # Check if agent moved out of camera bounds (more important than distance threshold)
            if not self.current_bounds.contains_position(current_position):
                print(
                    f"Agent moved out of camera bounds: {self.last_agent_position} -> {current_position}"
                )
                return self._handle_agent_movement(current_position, action_context)

            # Also check for significant movement (backup check)
            distance_moved = self._calculate_distance(
                self.last_agent_position, current_position
            )

            if distance_moved > self.min_movement_threshold:
                print(f"Agent moved significantly: {distance_moved:.1f} tiles")
                return self._handle_agent_movement(current_position, action_context)

        # Update last known position
        self.last_agent_position = current_position

        # If we have a pending action, check if it's been confirmed
        if self.pending_action and action_context:
            if self._is_action_confirmed(action_context):
                self._finalize_pending_action()
                self.pending_action = None

        return None

    def _initialize_camera_bounds(self, position: Tuple[float, float]) -> None:
        """Initialize camera bounds at agent position."""
        self.current_bounds = CameraBounds(
            center=position, radius=self.camera_radius, zoom=1.0
        )
        self.last_agent_position = position
        self.state = CameraState.LOCKED

    def _handle_agent_movement(
        self, new_position: Tuple[float, float], action_context: Optional[ActionContext]
    ) -> Optional[Dict[str, Any]]:
        """Handle agent movement and determine camera repositioning."""

        # Special case: Connect Entities always triggers bird's-eye view
        if action_context and action_context.is_connect_entities:
            return self._create_connect_entities_shot(action_context)

        # Check if new position is outside current camera bounds
        if self.current_bounds and not self.current_bounds.contains_position(
            new_position
        ):
            # Agent has moved out of current camera view
            return self._create_tracking_shot(new_position, action_context)

        return None

    def _create_connect_entities_shot(
        self, action_context: ActionContext
    ) -> Dict[str, Any]:
        """Create bird's-eye view shot for Connect Entities action."""

        if not action_context.bounding_box:
            # Fallback to regular tracking if no bounding box
            return self._create_tracking_shot(action_context.position, action_context)

        # Create zoom_to_fit shot that frames the bounding box
        shot = {
            "id": f"connect-entities-{action_context.program_id}",
            "kind": {"type": "zoom_to_fit", "bbox": action_context.bounding_box},
            "pan_ticks": 120,  # 2 second transition (smoother)
            "dwell_ticks": 480,  # 8 seconds to see the connection
            "zoom": None,  # Let server calculate optimal zoom
            "tags": ["connect_entities", "bird_eye", "bounding_box"],
        }

        # Update camera bounds to cover the bounding box area
        bbox = action_context.bounding_box
        center_x = (bbox[0][0] + bbox[1][0]) / 2
        center_y = (bbox[0][1] + bbox[1][1]) / 2
        width = abs(bbox[1][0] - bbox[0][0])
        height = abs(bbox[1][1] - bbox[0][1])
        radius = max(width, height) / 2 + 10  # Add padding

        self.current_bounds = CameraBounds(
            center=(center_x, center_y),
            radius=radius,
            zoom=0.5,  # Zoomed out for bird's-eye view
        )

        self.shots.append(shot)
        return shot

    def _create_tracking_shot(
        self, position: Tuple[float, float], action_context: Optional[ActionContext]
    ) -> Dict[str, Any]:
        """Create tracking shot for regular agent movement."""

        # Set up pending action if we have context
        if action_context:
            self.pending_action = action_context

        # Calculate smart zoom level based on action type and distance
        zoom_level = self._calculate_smart_zoom(position, action_context)
        print(
            f"  Smart zoom calculated: {zoom_level:.2f} for {action_context.action_type if action_context else 'unknown'} at {position}"
        )

        shot = {
            "id": f"track-{action_context.program_id if action_context else 'unknown'}",
            "kind": {"type": "focus_position", "pos": list(position)},
            "pan_ticks": 90,  # 1.5 second transition (smoother)
            "dwell_ticks": 240,  # 4 seconds to capture action
            "zoom": zoom_level,  # Smart zoom level
            "tags": ["tracking", "agent_movement", "focus_position"],
        }

        # Update camera bounds
        self.current_bounds = CameraBounds(
            center=position, radius=self.camera_radius, zoom=zoom_level
        )

        self.shots.append(shot)
        return shot

    def _is_action_confirmed(self, action_context: ActionContext) -> bool:
        """Check if the pending action has been confirmed."""
        # Simple confirmation: if we have the same action type and position
        if not self.pending_action:
            return False

        return (
            action_context.action_type == self.pending_action.action_type
            and self._calculate_distance(
                action_context.position, self.pending_action.position
            )
            < 5.0
        )

    def _finalize_pending_action(self) -> None:
        """Finalize the pending action and update state."""
        if self.pending_action:
            self.action_history.append(self.pending_action)
            self.state = CameraState.LOCKED

    def _handle_action_timing(
        self, action_context: ActionContext, current_tick: Optional[int]
    ) -> None:
        """Handle action timing for keep-alive mechanism."""
        if not current_tick:
            return

        # If this is a new action type or position, start tracking
        if (
            not self.is_action_in_progress
            or action_context.action_type != self.pending_action.action_type
            or self._calculate_distance(
                action_context.position, self.pending_action.position
            )
            > 5.0
        ):
            self.current_action_start_tick = current_tick
            self.is_action_in_progress = True
            self.pending_action = action_context
            print(
                f"Started tracking action: {action_context.action_type} at {action_context.position}"
            )

    def _should_keep_camera_on_current_action(
        self, current_tick: Optional[int]
    ) -> bool:
        """Check if camera should stay on current action due to keep-alive mechanism."""
        if (
            not self.is_action_in_progress
            or not self.current_action_start_tick
            or not current_tick
        ):
            return False

        elapsed_ticks = current_tick - self.current_action_start_tick
        return elapsed_ticks < self.action_keep_alive_ticks

    def _calculate_distance(
        self, pos1: Tuple[float, float], pos2: Tuple[float, float]
    ) -> float:
        """Calculate Euclidean distance between two positions."""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

    def _calculate_smart_zoom(
        self, position: Tuple[float, float], action_context: Optional[ActionContext]
    ) -> float:
        """Calculate smart zoom level based on action type and position."""

        # Base zoom level
        base_zoom = 1.0

        # Adjust zoom based on action type
        if action_context:
            action_type = action_context.action_type

            if action_type in ["place_entity", "place_entity_next_to"]:
                # For building actions, zoom in to see details
                base_zoom = 1.5
            elif action_type == "move_to":
                # For movement, use medium zoom
                base_zoom = 1.0
            elif action_type == "insert_item":
                # For item insertion, zoom in to see the action
                base_zoom = 1.3
            elif action_type == "connect_entities":
                # For connections, zoom out to see both entities
                base_zoom = 0.8

        # Adjust zoom based on distance from origin (0,0)
        distance_from_origin = self._calculate_distance(position, (0, 0))
        if distance_from_origin > 50:
            # Far from origin, zoom out to see more context
            base_zoom *= 0.7
        elif distance_from_origin > 20:
            # Medium distance, slight zoom out
            base_zoom *= 0.9

        # Clamp zoom to reasonable bounds
        return max(0.3, min(2.0, base_zoom))

    def create_shot_plan(self) -> Dict[str, Any]:
        """Create a shot plan from the current shots."""
        if not self.shots:
            return {
                "player": self.player,
                "shots": [],
                "plan_id": f"tracker-{uuid.uuid4().hex[:8]}",
                "capture": True,
            }

        return {
            "player": self.player,
            "start_zoom": self.current_bounds.zoom if self.current_bounds else 1.0,
            "shots": [
                {
                    "id": shot["id"],
                    "seq": i,
                    "kind": shot["kind"],
                    "pan_ticks": shot["pan_ticks"],
                    "dwell_ticks": shot["dwell_ticks"],
                    "zoom": shot["zoom"],
                    "tags": shot["tags"],
                }
                for i, shot in enumerate(self.shots)
            ],
            "plan_id": f"tracker-{uuid.uuid4().hex[:8]}",
            "capture": True,
            "capture_dir": "cinema_seq",
        }

    def reset(self) -> None:
        """Reset the camera tracker for a new session."""
        self.current_bounds = None
        self.state = CameraState.TRACKING
        self.last_agent_position = None
        self.action_history.clear()
        self.shots.clear()
        self.pending_action = None
        self.current_action_start_tick = None
        self.is_action_in_progress = False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about camera tracking."""
        return {
            "total_shots": len(self.shots),
            "current_state": self.state.value,
            "has_bounds": self.current_bounds is not None,
            "actions_tracked": len(self.action_history),
            "pending_action": self.pending_action is not None,
            "is_action_in_progress": self.is_action_in_progress,
            "action_start_tick": self.current_action_start_tick,
        }


def create_action_context(
    program_id: str,
    action_type: str,
    position: Tuple[float, float],
    entities: Optional[List[Dict[str, Any]]] = None,
    bounding_box: Optional[List[List[float]]] = None,
) -> ActionContext:
    """Create an ActionContext from action data."""
    return ActionContext(
        program_id=program_id,
        action_type=action_type,
        position=position,
        entities_involved=entities or [],
        is_connect_entities=(action_type == "connect_entities"),
        bounding_box=bounding_box,
    )
