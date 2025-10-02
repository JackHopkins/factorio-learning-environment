"""
Simplified Cinema Integration - Connects the simplified camera tracker with the cutscene API.

This module provides a clean interface for integrating the simplified camera tracker
with the existing Factorio cutscene system, focusing on meaningful agent movements.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
from fle.env.tools.admin.cutscene.client import Cutscene
from fle.eval.analysis.simplified_camera_tracker import (
    SimplifiedCameraTracker,
    create_action_context,
)


class SimplifiedCinemaIntegration:
    """
    Integration layer between simplified camera tracker and cutscene API.

    This class handles the coordination between agent movement tracking
    and camera positioning, ensuring smooth transitions and proper shot timing.
    """

    def __init__(self, cutscene_tool: Cutscene, player: int = 1):
        self.cutscene_tool = cutscene_tool
        self.tracker = SimplifiedCameraTracker(player=player)
        self.player = player
        self.current_plan_id: Optional[str] = None
        self.is_recording = False

    def start_tracking(self) -> None:
        """Start camera tracking session."""
        self.tracker.reset()
        self.is_recording = True
        print(f"Started camera tracking for player {self.player}")

    def stop_tracking(self) -> None:
        """Stop camera tracking session."""
        self.is_recording = False
        print(f"Stopped camera tracking for player {self.player}")

    def track_agent_action(
        self,
        program_id: str,
        action_type: str,
        position: Tuple[float, float],
        entities: Optional[List[Dict[str, Any]]] = None,
        bounding_box: Optional[List[List[float]]] = None,
        world_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Track an agent action and potentially reposition the camera.

        Args:
            program_id: ID of the program being executed
            action_type: Type of action being performed
            position: Current agent position
            entities: List of entities involved in the action
            bounding_box: Bounding box for Connect Entities actions
            world_context: Additional world context

        Returns:
            Cutscene plan if camera should be repositioned, None otherwise
        """

        if not self.is_recording:
            return None

        # Create action context
        action_context = create_action_context(
            program_id=program_id,
            action_type=action_type,
            position=position,
            entities=entities,
            bounding_box=bounding_box,
        )

        # Track agent movement
        shot = self.tracker.track_agent_movement(position, action_context)

        if shot:
            # Create and execute cutscene plan
            plan = self._create_cutscene_plan([shot], program_id)
            result = self._execute_cutscene(plan)
            return result

        return None

    def track_agent_position(
        self, position: Tuple[float, float], program_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Track agent position without specific action context.

        This is useful for continuous position tracking when the agent
        is moving but not performing specific actions.
        """

        if not self.is_recording:
            return None

        # Track movement without action context
        shot = self.tracker.track_agent_movement(position, None)

        if shot:
            plan = self._create_cutscene_plan([shot], program_id)
            result = self._execute_cutscene(plan)
            return result

        return None

    def _create_cutscene_plan(
        self, shots: List[Dict[str, Any]], program_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a cutscene plan from shots."""
        return {
            "player": self.player,
            "start_zoom": self.tracker.current_bounds.zoom
            if self.tracker.current_bounds
            else 1.0,
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
                for i, shot in enumerate(shots)
            ],
            "plan_id": f"simplified-{program_id or 'unknown'}-{int(time.time())}",
            "capture": True,
            "capture_dir": "cinema_seq",
        }

    def _execute_cutscene(self, plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a cutscene plan."""
        try:
            result = self.cutscene_tool(plan)
            self.current_plan_id = plan.get("plan_id")
            print(f"Executed cutscene: {plan['plan_id']}")
            return result
        except Exception as e:
            print(f"Failed to execute cutscene: {e}")
            return None

    def get_current_bounds(self) -> Optional[Dict[str, Any]]:
        """Get current camera bounds information."""
        if not self.tracker.current_bounds:
            return None

        return {
            "center": self.tracker.current_bounds.center,
            "radius": self.tracker.current_bounds.radius,
            "zoom": self.tracker.current_bounds.zoom,
        }

    def is_position_in_view(self, position: Tuple[float, float]) -> bool:
        """Check if a position is currently in camera view."""
        if not self.tracker.current_bounds:
            return False
        return self.tracker.current_bounds.contains_position(position)

    def get_stats(self) -> Dict[str, Any]:
        """Get tracking statistics."""
        stats = self.tracker.get_stats()
        stats.update(
            {
                "is_recording": self.is_recording,
                "current_plan_id": self.current_plan_id,
                "player": self.player,
            }
        )
        return stats


def create_simplified_cinema_integration(
    cutscene_tool: Cutscene, player: int = 1
) -> SimplifiedCinemaIntegration:
    """Create a new simplified cinema integration instance."""
    return SimplifiedCinemaIntegration(cutscene_tool, player)
